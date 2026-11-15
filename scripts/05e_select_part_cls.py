"""Chọn hình học ảnh cắt và ngưỡng của bộ phân loại bộ phận (phương án 2) trên val. Không đụng test, video.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv, có outputs/train/yolo11n_cls_parts/weights/best.pt):
    python scripts/05e_select_part_cls.py
    python scripts/05e_select_part_cls.py --weights outputs/train/yolo11n_cls_parts_v4/weights/best.pt --out val_select_v4.json
    (--weights mặc định part_cls.weights; --out là tên file trong outputs/results/parts_cls/, mặc định val_select.json)
    python scripts/05e_select_part_cls.py --helmet-veto   # bước C, D: chọn face_conf (V-C1, V-C2), kiểm quy ước quay lưng
    (ghi outputs/results/parts_cls/helmet_veto_val.json; không sửa cấu hình)
    python scripts/05e_select_part_cls.py --helmet-veto2  # bước C2: t_veto x face_conf, thêm mũ CHV val
    (ghi outputs/results/parts_cls/helmet_veto2_val.json; không sửa cấu hình)

1. Lấy các hộp bộ phận của val như 03y (collect_items, only val): găng/tay trần, ủng/giày thường, kính BH/kính thường/không kính.
2. Tìm người bằng YOLO11n-pose trên cả ảnh, rồi chạy PoseEstimator của pipeline trên ảnh cắt từng người (như khi chạy thật).
3. Mỗi hộp nhãn ghép với điểm gốc gần tâm hộp nhất (cổ tay có khuỷu, mắt cá có gối, trung điểm hai mắt), cách tâm
   không quá cạnh dài của hộp. Không ghép được: ghi vào độ phủ, không vào phần chọn.
4. Với từng hình học trong `calibration.part_geom_grid`: cắt theo parts.py, phân loại, tính độ chính xác cân bằng
   (trung bình độ nhạy lớp có PPE và lớp không có PPE, ngưỡng 0,5). Chọn hình học cao nhất.
5. Với hình học đã chọn: t_pos = ngưỡng nhỏ nhất trong `part_thr_grid` mà p >= t_pos đạt độ chính xác
   `part_cls.precision_target.pos`; t_neg tương tự cho 1 - p với mục tiêu `neg`. Không đạt: null.
Ghi outputs/results/parts_cls/val_select.json; in khối YAML gợi ý, người chép vào configs/pipeline.yaml mục part_cls.
"""

import argparse
import importlib.util
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe import load_config  # noqa: E402
from ppe.parts import PART_CLASSES, cut, match_anchor, people_keypoints, ppe_prob  # noqa: E402
from ppe.pose import PoseEstimator  # noqa: E402

OUT_DIR = ROOT / "outputs" / "results" / "parts_cls"
CLS2PPE = {c: ppe for ppe, (pos, negs) in PART_CLASSES.items() for c in (pos, *negs)}


def load_03y():
    spec = importlib.util.spec_from_file_location("p03y", ROOT / "scripts" / "03y_ppe6_part_crops.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def geoms(grid, part):
    """Mọi tổ hợp tham số của lưới bộ phận (k, s cho tay chân; s cho mắt; s, h cho thân)."""
    g = grid[part]
    keys = sorted(g)
    return [dict(zip(keys, vals)) for vals in itertools.product(*(g[k] for k in keys))]


def precision_at(p, y, t):
    sel = p >= t
    n = int(sel.sum())
    return (float((y[sel] == 1).mean()) if n else None), n, float(sel[y == 1].mean()) if (y == 1).any() else None


def helmet_veto_eval(cfg, items, person_model, pose, out_name):
    """Bước C, D trên val (kế hoạch ppe6 mục C, D, 16/11/2026). Không đụng test, video, holdout.

    Hộp mũ / không mũ / kính BH val (như khi chọn ngưỡng). Mỗi hộp ghép người qua điểm gốc gần nhất (như match_anchor) để
    lấy keypoint và hộp người. Ảnh cắt vùng đầu theo part_cls.geometry.head, trọng số weights_by_ppe.helmet.
    V-C1: hộp có mũ, người qua cổng nhìn thẳng (frontal_strict) ở từng face_conf của lưới: tỉ lệ phiếu neg (bị phủ quyết
    nhầm). Chọn face_conf thấp nhất có V-C1 <= 2% và >= 100 hộp. V-C2 (chỉ báo): hộp không mũ qua cổng: tỉ lệ neg; hộp mũ
    detector (cache preds.npz, conf >= detector.conf.helmet, NMS) có tâm trong hộp không mũ: số bị phủ quyết.
    D (chỉ báo, quy ước không chọn): tỉ lệ hộp kính BH, mũ, không mũ có người bị back_view_now gắn quay lưng."""
    import datetime
    import hashlib
    import subprocess

    import torch
    from torchvision.ops import nms
    from types import SimpleNamespace

    from ppe.compliance import back_view_now, frontal_strict
    from ultralytics import YOLO

    from ppe.parts import anchors, head_box

    GRID, TARGET, MIN_N = (0.7, 0.8, 0.9), 0.02, 100          # người dùng duyệt 16/11/2026
    DIAG = OUT_DIR / "helmet_veto_diag"
    BV = dict(kp_conf=0.3, min_sep=0.05, face_strong=0.9, hold_s=1.0)
    pc = cfg["part_cls"]
    t_neg = pc["thresholds"]["helmet"]["t_neg"]
    geom = pc["geometry"]["head"]
    w_helmet = pc["weights_by_ppe"]["helmet"]
    clf = YOLO(ROOT / w_helmet)
    names = clf.names
    keep = [it for it in items if CLS2PPE[it[1]] in ("helmet", "goggles")]
    by_img = defaultdict(list)
    for _, cls, img, bx, src in keep:
        by_img[img].append((cls, bx, src))

    def people(im):
        r = person_model.predict(im, imgsz=640, conf=0.25, device=cfg["detector"]["device"], verbose=False)[0]
        tr = [SimpleNamespace(xyxy=b, extra={}) for b in r.boxes.xyxy.cpu().numpy()]
        pose(im, tr)
        return [(t.xyxy, t.extra["kps"]) for t in tr if t.extra.get("kps")]

    def match(ppl, ppe, bx):
        c = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
        lim = max(bx[2] - bx[0], bx[3] - bx[1])
        best = None
        for box, kps in ppl:
            for pt, mk in anchors(kps, ppe, pc["kp_conf"]):
                d = float(np.hypot(pt[0] - c[0], pt[1] - c[1]))
                if d <= lim and (best is None or d < best[0]):
                    best = (d, mk, box, kps)
        return best

    rec, cover = [], defaultdict(lambda: [0, 0])
    for n, (img, objs) in enumerate(sorted(by_img.items())):
        im = cv2.imdecode(np.fromfile(str(ROOT / img), dtype=np.uint8), cv2.IMREAD_COLOR)
        ppl = people(im)
        crops, meta = [], []
        for cls, bx, src in objs:
            ppe = CLS2PPE[cls]
            cover[cls][1] += 1
            m = match(ppl, "helmet" if ppe == "helmet" else "goggles", bx)
            if m is None:
                continue
            cover[cls][0] += 1
            _, mk, box, kps = m
            r = dict(img=img, cls=cls, src=src, bx=[float(v) for v in bx], y=int(cls == PART_CLASSES[ppe][0]),
                     ppe=ppe, back=bool(back_view_now(kps, box, BV)),
                     frontal={str(fc): bool(frontal_strict(kps, fc, pc["kp_conf"])) for fc in GRID}, p=None)
            if ppe == "helmet":
                cr = cut(im, head_box(kps, geom, pc["kp_conf"]), pc["min_px"])
                if cr is not None:
                    crops.append(cr)
                    meta.append(r)
            rec.append(r)
        if crops:
            for r, cr, rr in zip(meta, crops, clf.predict(crops, imgsz=pc["imgsz"], device=cfg["detector"]["device"], verbose=False)):
                r["p"] = ppe_prob(rr.probs.data.cpu().numpy(), names, "helmet")
                if r["y"] == 1 and 1 - r["p"] >= t_neg:
                    # Chẩn đoán (16/11/2026): lưu ảnh cắt bộ phân loại thấy và vùng quanh hộp nhãn cho ca mũ thật bị neg
                    DIAG.mkdir(parents=True, exist_ok=True)
                    i = len(list(DIAG.glob("*_crop.jpg")))
                    x1, y1, x2, y2 = r["bx"]
                    w_, h_ = x2 - x1, y2 - y1
                    ctx = im[int(max(y1 - 1.5 * h_, 0)):int(y2 + 2.5 * h_), int(max(x1 - 1.5 * w_, 0)):int(x2 + 1.5 * w_)]
                    cv2.imwrite(str(DIAG / f"fn{i:02d}_crop.jpg"), cr)
                    cv2.imwrite(str(DIAG / f"fn{i:02d}_context.jpg"), ctx)
                    r["diag"] = f"fn{i:02d}"
        if (n + 1) % 200 == 0:
            print(f"  {n + 1}/{len(by_img)} ảnh", flush=True)

    hel = [r for r in rec if r["ppe"] == "helmet" and r["p"] is not None]
    neg = lambda r: 1 - r["p"] >= t_neg

    # Hộp mũ của detector trên hộp không mũ (Có sai của detector), từ cache 05a --conf (chỉ đọc)
    cache = ROOT / "outputs" / "results" / "pipeline_calib_val" / "preds.npz"
    preds = dict(np.load(cache, allow_pickle=True))["data"].item()
    d = cfg["detector"]
    h_cls = cfg["ppe"]["helmet"]["cls"]
    fp_heads, miss_cache = [], 0
    # Cache lưu theo tên file của bộ dữ liệu (stats.csv cột file), hộp 03y theo đường dẫn ảnh gốc (cột image).
    # Sửa 16/11/2026 sau lần chạy đầu: tra theo tên ảnh gốc làm mọi hộp không mũ "thiếu cache" (V-C2 sai, V-C1 không đổi).
    import csv
    stem_of = {r["image"].replace("\\", "/"): Path(r["file"]).stem
               for r in csv.DictReader((ROOT / "data" / "ppe4" / "stats.csv").open(encoding="utf-8"))}
    for r in hel:
        if r["y"] != 0:
            continue
        key = str(r["img"]).replace("\\", "/")
        q = preds.get(stem_of.get(key, Path(key).stem))
        if q is None:
            miss_cache += 1
            continue
        k = (q["cls"] == h_cls) & (q["conf"] >= d["conf"]["helmet"])
        b, c = q["xyxy"][k], q["conf"][k]
        if not len(b):
            continue
        b = b[nms(torch.tensor(b, dtype=torch.float32), torch.tensor(c, dtype=torch.float32), d["nms_iou"]).numpy()]
        x1, y1, x2, y2 = r["bx"]
        cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
        if ((cx >= x1) & (cx <= x2) & (cy >= y1) & (cy <= y2)).any():
            fp_heads.append(r)

    # Chẩn đoán: độ tin cậy lớn nhất của hộp mũ detector (cache, mọi conf >= 0,01) có tâm trong hộp nhãn, cho mọi hộp
    for r in hel:
        key = str(r["img"]).replace("\\", "/")
        q = preds.get(stem_of.get(key, Path(key).stem))
        r["det_conf"] = None
        if q is not None:
            k = q["cls"] == h_cls
            b, c = q["xyxy"][k], q["conf"][k]
            x1, y1, x2, y2 = r["bx"]
            cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
            ins = (cx >= x1) & (cx <= x2) & (cy >= y1) & (cy <= y2)
            r["det_conf"] = round(float(c[ins].max()), 4) if ins.any() else 0.0
    (OUT_DIR / "helmet_veto_val_records.json").write_text(json.dumps(hel, ensure_ascii=False, indent=1), encoding="utf-8")

    vc = {}
    for fc in GRID:
        k = str(fc)
        pos = [r for r in hel if r["y"] == 1 and r["frontal"][k]]
        ng = [r for r in hel if r["y"] == 0 and r["frontal"][k]]
        fp = [r for r in fp_heads if r["frontal"][k]]
        vc[k] = dict(
            V_C1=dict(n=len(pos), phu_quyet_nham=sum(map(neg, pos)),
                      ti_le=round(sum(map(neg, pos)) / len(pos), 4) if pos else None),
            V_C2=dict(n_khong_mu=len(ng), neg=sum(map(neg, ng)),
                      ti_le_neg=round(sum(map(neg, ng)) / len(ng), 4) if ng else None,
                      hop_mu_detector_tren_dau_khong_mu=len(fp), phu_quyet_duoc=sum(map(neg, fp))))
    ok = [fc for fc in GRID if vc[str(fc)]["V_C1"]["n"] >= MIN_N and vc[str(fc)]["V_C1"]["ti_le"] <= TARGET]
    chosen = min(ok) if ok else None

    def rate(rs):
        return dict(n=len(rs), quay_lung=sum(r["back"] for r in rs),
                    ti_le=round(sum(r["back"] for r in rs) / len(rs), 4) if rs else None)

    gog = [r for r in rec if r["ppe"] == "goggles" and r["cls"] == PART_CLASSES["goggles"][0]]
    dchk = dict(kinh_BH=rate(gog), mu=rate([r for r in hel if r["y"] == 1]), khong_mu=rate([r for r in hel if r["y"] == 0]),
                mu_khong_mu_nhin_thang_bi_gan_quay_lung={k: sum(r["back"] for r in hel if r["frontal"][k]) for k in map(str, GRID)})

    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    res = dict(
        ho_so=dict(thoi_diem=datetime.datetime.now().isoformat(timespec="seconds"), commit_nen=git("rev-parse", "HEAD"),
                   file_dang_sua=git("status", "--porcelain").splitlines(),
                   sha256=dict(helmet_weights=sha(ROOT / w_helmet), pose_weights=sha(ROOT / cfg["pose"]["weights"]),
                               preds_cache=sha(cache),
                               items=hashlib.sha256(json.dumps(sorted((str(a), str(b), str(c), [float(v) for v in e])
                                                                      for a, b, c, e, _ in keep)).encode()).hexdigest()),
                   ghi_chu="Hộp val như 05e (03y collect_items, only val). t_neg mũ chọn trên chính val này (val_select_v4.json)."),
        thiet_lap=dict(grid=list(GRID), target=TARGET, min_n=MIN_N, t_neg=t_neg, kp_conf=pc["kp_conf"], geometry_head=geom,
                       back_view=BV, conf_helmet=d["conf"]["helmet"], nms_iou=d["nms_iou"]),
        do_phu={c: dict(ghep_duoc=a, tong=b) for c, (a, b) in sorted(cover.items())},
        hop_mu_cat_duoc=len(hel), cache_thieu=miss_cache, C=vc, face_conf_chon=chosen, C_dat=chosen is not None, D_kiem=dchk)
    OUT = OUT_DIR / out_name
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "ho_so"}, ensure_ascii=False, indent=1))
    print("Ghi", OUT.relative_to(ROOT), "(chưa ghi cấu hình)")


def helmet_veto2_eval(cfg, items, person_model, pose, out_name):
    """Bước C2 trên val (kế hoạch ppe6 mục C2, 16/11/2026). Không đụng test, Pictor, holdout, video.

    Tập: (1) hộp mũ / không mũ val của 03y (như C); (2) hộp mũ (lớp 1) của ảnh CHV thuộc ppe4 val (bộ phân loại chưa từng
    thấy ảnh CHV). Ghép người, cắt vùng đầu, pose như C. Lưới t_veto x face_conf; chọn tổ hợp đầu tiên theo (t_veto,
    face_conf) tăng dần có V-C1 (mũ thật nhìn thẳng, 1 - p >= t_veto) <= 2% với >= 100 hộp và V-C3 (mũ thật nhìn thẳng,
    t_neg <= 1 - p < t_veto) <= 5%."""
    import csv
    import datetime
    import hashlib
    import subprocess
    from types import SimpleNamespace

    from ultralytics import YOLO

    from ppe.compliance import back_view_now, frontal_strict
    from ppe.parts import anchors, head_box

    T_VETO, FACE, V1_MAX, V3_MAX, MIN_N = (0.7, 0.8, 0.9), (0.7, 0.8, 0.9), 0.02, 0.05, 100   # người dùng duyệt 16/11
    DATASET4 = ROOT / "data" / "ppe4" / "dataset"
    pc = cfg["part_cls"]
    t_neg = pc["thresholds"]["helmet"]["t_neg"]
    geom = pc["geometry"]["head"]
    w_helmet = pc["weights_by_ppe"]["helmet"]
    bv = cfg["compliance"]["back_view"]
    clf = YOLO(ROOT / w_helmet)
    names = clf.names
    stats = list(csv.DictReader((ROOT / "data" / "ppe4" / "stats.csv").open(encoding="utf-8")))
    stem_of = {r["image"].replace("\\", "/"): Path(r["file"]).stem for r in stats}

    # (1) 03y val: mũ / không mũ
    by_img = defaultdict(list)
    for _, cls, img, bx, src in items:
        if CLS2PPE[cls] == "helmet":
            by_img[img].append((cls, list(bx), src))
    n03 = sum(len(v) for v in by_img.values())
    # (2) CHV val: hộp mũ (lớp 1) theo nhãn ppe4; ảnh gốc ở data/raw/chv (cột image), nhãn theo tên file bộ dữ liệu
    chv = [r for r in stats if r["source"] == "chv" and r["split"] == "val"]
    nchv = 0
    for r in chv:
        lab = DATASET4 / "labels" / "val" / (Path(r["file"]).stem + ".txt")
        img = r["image"].replace("\\", "/")
        rows = [ln.split() for ln in lab.read_text(encoding="utf-8").splitlines() if ln.strip()] if lab.exists() else []
        for c, cx, cy, bw, bh in ((int(a[0]), *map(float, a[1:5])) for a in rows):
            if c == cfg["ppe"]["helmet"]["cls"]:
                by_img[img].append(("helmet", ["norm", cx, cy, bw, bh], "chv"))
                nchv += 1
    print(f"C2 val: 03y {n03} hộp mũ / không mũ, CHV {nchv} hộp mũ ({len(chv)} ảnh), {len(by_img)} ảnh", flush=True)

    def people(im):
        r = person_model.predict(im, imgsz=640, conf=0.25, device=cfg["detector"]["device"], verbose=False)[0]
        tr = [SimpleNamespace(xyxy=b, extra={}) for b in r.boxes.xyxy.cpu().numpy()]
        pose(im, tr)
        return [(t.xyxy, t.extra["kps"]) for t in tr if t.extra.get("kps")]

    def match(ppl, bx):
        c = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
        lim = max(bx[2] - bx[0], bx[3] - bx[1])
        best = None
        for box, kps in ppl:
            for pt, mk in anchors(kps, "helmet", pc["kp_conf"]):
                d = float(np.hypot(pt[0] - c[0], pt[1] - c[1]))
                if d <= lim and (best is None or d < best[0]):
                    best = (d, box, kps)
        return best

    rec, cover = [], defaultdict(lambda: [0, 0])
    for n, (img, objs) in enumerate(sorted(by_img.items())):
        im = cv2.imdecode(np.fromfile(str(ROOT / img), dtype=np.uint8), cv2.IMREAD_COLOR)
        if im is None:
            continue
        h, w = im.shape[:2]
        ppl = people(im)
        crops, meta = [], []
        for cls, bx, src in objs:
            if bx[0] == "norm":
                _, cx, cy, bw, bh = bx
                bx = [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h]
            key = (src if src == "chv" else "03y", cls)
            cover[key][1] += 1
            m = match(ppl, bx)
            if m is None:
                continue
            _, box, kps = m
            cr = cut(im, head_box(kps, geom, pc["kp_conf"]), pc["min_px"])
            if cr is None:
                continue
            cover[key][0] += 1
            crops.append(cr)
            meta.append(dict(img=img, set=key[0], y=int(cls == "helmet"), bx=[float(v) for v in bx],
                             back=bool(back_view_now(kps, box, bv)),
                             frontal={str(f): bool(frontal_strict(kps, f, pc["kp_conf"])) for f in FACE}))
        if crops:
            for r, rr in zip(meta, clf.predict(crops, imgsz=pc["imgsz"], device=cfg["detector"]["device"], verbose=False)):
                r["p"] = ppe_prob(rr.probs.data.cpu().numpy(), names, "helmet")
            rec.extend(meta)
        if (n + 1) % 200 == 0:
            print(f"  {n + 1}/{len(by_img)} ảnh", flush=True)

    # Hộp mũ detector (cache 05a --conf, chỉ đọc) có tâm trong hộp nhãn: độ tin cậy lớn nhất (mọi conf >= 0,01)
    cache = ROOT / "outputs" / "results" / "pipeline_calib_val" / "preds.npz"
    preds = dict(np.load(cache, allow_pickle=True))["data"].item()
    h_cls = cfg["ppe"]["helmet"]["cls"]
    miss = 0
    for r in rec:
        q = preds.get(stem_of.get(r["img"].replace("\\", "/"), Path(r["img"]).stem))
        r["det_conf"] = None
        if q is None:
            miss += 1
            continue
        k = q["cls"] == h_cls
        b, c = q["xyxy"][k], q["conf"][k]
        x1, y1, x2, y2 = r["bx"]
        cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
        ins = (cx >= x1) & (cx <= x2) & (cy >= y1) & (cy <= y2)
        r["det_conf"] = round(float(c[ins].max()), 4) if ins.any() else 0.0
    conf_h = cfg["detector"]["conf"]["helmet"]

    def level(r, tv):
        q = 1 - r["p"]
        return "thieu" if q >= tv else ("cxd" if q >= t_neg else "giu")

    grid = []
    for tv in T_VETO:
        for fc in FACE:
            k = str(fc)
            pos = [r for r in rec if r["y"] == 1 and r["frontal"][k]]
            ng = [r for r in rec if r["y"] == 0 and r["frontal"][k]]
            fp = [r for r in ng if (r["det_conf"] or 0) >= conf_h]
            cnt = lambda rs, lv: sum(level(r, tv) == lv for r in rs)
            v1 = cnt(pos, "thieu") / len(pos) if pos else None
            v3 = cnt(pos, "cxd") / len(pos) if pos else None
            by_set = {s: dict(n=len([r for r in pos if r["set"] == s]),
                              thieu=cnt([r for r in pos if r["set"] == s], "thieu"),
                              cxd=cnt([r for r in pos if r["set"] == s], "cxd")) for s in ("03y", "chv")}
            pos_det = [r for r in pos if (r["det_conf"] or 0) >= conf_h]
            grid.append(dict(
                t_veto=tv, face_conf=fc, n_mu_nhin_thang=len(pos),
                V_C1=dict(thieu_sai=cnt(pos, "thieu"), ti_le=None if v1 is None else round(v1, 4)),
                V_C3=dict(co_thanh_cxd=cnt(pos, "cxd"), ti_le=None if v3 is None else round(v3, 4)),
                theo_tap=by_set,
                mu_co_hop_detector=dict(n=len(pos_det), thieu=cnt(pos_det, "thieu"), cxd=cnt(pos_det, "cxd")),
                V_C2=dict(n_khong_mu=len(ng), thieu=cnt(ng, "thieu"), cxd=cnt(ng, "cxd"),
                          hop_mu_detector_tren_dau_khong_mu=len(fp), fp_thanh_thieu=cnt(fp, "thieu"),
                          fp_thanh_cxd=cnt(fp, "cxd")),
                dat=bool(pos) and len(pos) >= MIN_N and v1 <= V1_MAX and v3 <= V3_MAX))
    chosen = next((g for g in grid if g["dat"]), None)

    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    res = dict(
        ho_so=dict(thoi_diem=datetime.datetime.now().isoformat(timespec="seconds"), commit_nen=git("rev-parse", "HEAD"),
                   file_dang_sua=git("status", "--porcelain").splitlines(),
                   sha256=dict(helmet_weights=sha(ROOT / w_helmet), pose_weights=sha(ROOT / cfg["pose"]["weights"]),
                               preds_cache=sha(cache),
                               items=hashlib.sha256(json.dumps(sorted((k, str(o)) for k, v in by_img.items()
                                                                      for o in v)).encode()).hexdigest()),
                   ro_ri=("Bộ phân loại chưa từng thấy ảnh CHV (data/ppe6/parts/train: 0 ảnh chv); CHV val không có "
                          "group_id ở train/test; không dùng test, Pictor, holdout, video.")),
        thiet_lap=dict(t_veto=list(T_VETO), face_conf=list(FACE), V_C1_max=V1_MAX, V_C3_max=V3_MAX, min_n=MIN_N,
                       t_neg=t_neg, kp_conf=pc["kp_conf"], geometry_head=geom, back_view=bv, conf_helmet=conf_h,
                       thu_tu_chon="t_veto tăng, rồi face_conf tăng; tổ hợp đầu tiên đạt"),
        do_phu={f"{a}/{b}": dict(cat_duoc=x, tong=y) for (a, b), (x, y) in sorted(cover.items())},
        cache_thieu=miss, luoi=grid, chon=chosen and dict(t_veto=chosen["t_veto"], face_conf=chosen["face_conf"]),
        C2_dat=chosen is not None)
    OUT = OUT_DIR / out_name
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "helmet_veto2_val_records.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    for g in grid:
        print(g["t_veto"], g["face_conf"], "n", g["n_mu_nhin_thang"], "V-C1", g["V_C1"], "V-C3", g["V_C3"],
              "tập", g["theo_tap"], "V-C2", g["V_C2"], "ĐẠT" if g["dat"] else "")
    print("do_phu", res["do_phu"], "cache_thieu", miss)
    print("chọn:", res["chon"], "| C2 đạt:", res["C2_dat"])
    print("Ghi", OUT.relative_to(ROOT), "(chưa ghi cấu hình)")


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=None, help="trọng số bộ phân loại; mặc định part_cls.weights")
    ap.add_argument("--out", default="val_select.json", help="tên file kết quả trong outputs/results/parts_cls/")
    ap.add_argument("--helmet-veto", action="store_true", help="bước C, D: V-C1, V-C2, kiểm quay lưng (helmet_veto_val.json)")
    ap.add_argument("--helmet-veto2", action="store_true", help="bước C2: hai mức, thêm mũ CHV val (helmet_veto2_val.json)")
    args = ap.parse_args()
    OUT = OUT_DIR / args.out
    from ultralytics import YOLO

    cfg = load_config()
    pc = cfg["part_cls"]
    cal = cfg["calibration"]
    ppe6 = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    items = [it for it in load_03y().collect_items(ppe6, only=("val",), chv_torso=True) if it[0] == "val"]
    by_img = defaultdict(list)
    for _, cls, img, bx, src in items:
        by_img[img].append((cls, bx, src))
    print(f"val: {len(items)} hộp bộ phận, {len(by_img)} ảnh")

    person_model = YOLO(ROOT / cfg["pose"]["weights"])
    pose = PoseEstimator(cfg, ROOT)
    if args.helmet_veto:
        helmet_veto_eval(cfg, items, person_model, pose, "helmet_veto_val.json")
        return
    if args.helmet_veto2:
        helmet_veto2_eval(cfg, items, person_model, pose, "helmet_veto2_val.json")
        return
    clf = YOLO(ROOT / (args.weights or pc["weights"]))
    names = clf.names
    part_of = {"gloves": "hand", "boots": "foot", "goggles": "eye"}
    if "vest" in names.values():   # bản 3 có áo
        part_of["vest"] = "torso"
    if "helmet" in names.values():   # bản 4 có mũ
        part_of["helmet"] = "head"
    items = [it for it in items if CLS2PPE[it[1]] in part_of]
    by_img = defaultdict(list)
    for _, cls, img, bx, src in items:
        by_img[img].append((cls, bx, src))
    grid = {part: geoms(cal["part_geom_grid"], part) for part in part_of.values()}
    probs = defaultdict(list)       # (part, chỉ số hình học) -> [(p, y)]
    cover = defaultdict(lambda: [0, 0])  # lớp -> [ghép được, tổng]
    for n, (img, objs) in enumerate(sorted(by_img.items())):
        im = cv2.imdecode(np.fromfile(str(ROOT / img), dtype=np.uint8), cv2.IMREAD_COLOR)
        people = people_keypoints(im, person_model, pose, cfg["detector"]["device"])
        crops, keys = [], []
        for cls, bx, _ in objs:
            ppe = CLS2PPE[cls]
            cover[cls][1] += 1
            mk = match_anchor(people, ppe, bx, pc["kp_conf"])
            if mk is None:
                continue
            cover[cls][0] += 1
            part = part_of[ppe]
            y = int(cls == PART_CLASSES[ppe][0])
            for gi, g in enumerate(grid[part]):
                cr = cut(im, mk(g), pc["min_px"])
                if cr is not None:
                    crops.append(cr)
                    keys.append((part, gi, ppe, y))
        if crops:
            for (part, gi, ppe, y), rr in zip(keys, clf.predict(crops, imgsz=pc["imgsz"], device=cfg["detector"]["device"], verbose=False)):
                probs[(part, gi)].append((ppe_prob(rr.probs.data.cpu().numpy(), names, ppe), y))
        if (n + 1) % 200 == 0:
            print(f"  {n + 1}/{len(by_img)} ảnh")

    res = dict(weights=args.weights or pc["weights"], coverage={c: dict(matched=a, total=b) for c, (a, b) in sorted(cover.items())}, parts={})
    tg = cal["part_thr_grid"]
    ts = np.round(np.arange(tg["start"], tg["stop"] + 1e-9, tg["step"]), 4)
    chosen_geom, chosen_thr = {}, {}
    for ppe, part in part_of.items():
        rows = []
        for gi, g in enumerate(grid[part]):
            v = np.array(probs[(part, gi)]) if probs[(part, gi)] else np.zeros((0, 2))
            if not len(v):
                continue
            p, y = v[:, 0], v[:, 1].astype(int)
            rp = float((p[y == 1] >= 0.5).mean()) if (y == 1).any() else 0.0
            rn = float((p[y == 0] < 0.5).mean()) if (y == 0).any() else 0.0
            rows.append(dict(geom=g, n=len(v), n_pos=int(y.sum()), recall_pos=round(rp, 4), recall_neg=round(rn, 4),
                             bal_acc=round((rp + rn) / 2, 4), gi=gi))
        best = max(rows, key=lambda r: r["bal_acc"])
        v = np.array(probs[(part, best["gi"])])
        p, y = v[:, 0], v[:, 1].astype(int)
        thr = {}
        for kind, score, lab in (("pos", p, 1), ("neg", 1 - p, 0)):
            yy = (y == lab).astype(int)
            pick = None
            for t in ts:
                prec, cnt, rec = precision_at(score, yy, t)
                if prec is not None and prec >= pc["precision_target"][kind]:
                    pick = dict(t=float(t), precision=round(prec, 4), n_selected=cnt, recall=round(rec, 4))
                    break
            thr[kind] = pick
            bm = max(((precision_at(score, yy, t)[0] or 0, float(t)) for t in ts if precision_at(score, yy, t)[1] >= 10), default=None)
            thr[kind + "_max_precision"] = bm and dict(precision=round(bm[0], 4), t=bm[1])   # để biết còn cách mục tiêu bao xa
        res["parts"][ppe] = dict(grid=rows, chosen=best, thresholds=thr)
        chosen_geom[part] = best["geom"]
        chosen_thr[ppe] = {"t_pos": thr["pos"] and thr["pos"]["t"], "t_neg": thr["neg"] and thr["neg"]["t"]}
    res["suggest"] = dict(geometry=chosen_geom, thresholds=chosen_thr, precision_target=pc["precision_target"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res["coverage"], ensure_ascii=False))
    for ppe, d in res["parts"].items():
        print(ppe, "chọn", d["chosen"], "| ngưỡng", d["thresholds"])
    print("Gợi ý cho configs/pipeline.yaml:\n" + yaml.safe_dump(res["suggest"], allow_unicode=True, sort_keys=False))
    print("Ghi", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
