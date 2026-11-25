"""Bước 3: chọn trên val ảnh các tham số của chuỗi xử lý (docs/spec.md mục 3, 5.2, 7.5). Không đụng test.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05a_calibrate_val.py --regions     # vùng cơ thể + max_distance từ nhãn val (không cần mô hình)
    python scripts/05a_calibrate_val.py --conf        # conf từng lớp + NMS IoU từ dự đoán của detector trên val
    python scripts/05a_calibrate_val.py --crop        # so sánh PPE dò cả khung / trên ảnh cắt từng người (cần conf, nms)
    python scripts/05a_calibrate_val.py --pose        # tâm găng nhãn thật trong elip cổ tay, so với vùng tay
    python scripts/05a_calibrate_val.py --torso       # vùng thân theo khung xương cho áo (bước B), ghép đúng người
    python scripts/05a_calibrate_val.py --torso-strict  # bước B2: tham số torso_strict, V1-V4, chẩn đoán G5
    python scripts/05a_calibrate_val.py --assoc-pose  # bước F: kính theo mắt, áo theo vai, găng dự phòng (assoc_pose.json)
    python scripts/05a_calibrate_val.py --assoc-close # F1 tầm gần: ủng theo mắt cá, găng theo cổ tay (assoc_close.json)
    (dự đoán được lưu cache; --rerun để dự đoán lại)

Tham số đầu vào: configs/pipeline.yaml (detector, ppe, calibration). Chỉ in và ghi đề xuất vào
outputs/results/pipeline_calib_val/; người chép giá trị đã duyệt vào configs/pipeline.yaml kèm ngày.
    regions.json   vùng (x0, x1, y0, y1) và max_distance từng PPE, số PPE dùng để tính
    preds.npz      cache dự đoán (conf rất thấp, gần như không NMS)
    conf_f1.csv    P/R/F1 theo NMS IoU × lớp × conf
    conf.json      đề xuất conf từng lớp và nms_iou
    crop_preds.npz cache dự đoán PPE trên ảnh cắt từng người, mỗi cỡ ảnh cắt
    crop.json      F1 từng lớp, conf cho F1 lớn nhất, thời gian/người của từng chế độ (full, crop<cỡ>)
    pose.json      tỉ lệ găng nằm trong elip cổ tay theo wrist_conf, rho, cỡ người; thời gian pose/người
    torso.json     tham số association.torso_pose và tỉ lệ áo ghép đúng / sai người, người đủ thân và bị cắt giả lập
    torso_strict.json  bước B2: tham số đề xuất association.torso_strict, V1-V3 (bản 4, B1, B2, B2 không G5),
                   V4 hai phần theo nhóm, chẩn đoán G5, kết luận tiêu chí
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe import load_config  # noqa: E402
from ppe.association import SIDES, norm_distance, region_box  # noqa: E402

DATASET = ROOT / "data" / "ppe4" / "dataset"
PPE6_DATASET = ROOT / "data" / "ppe6" / "dataset"
OUT = ROOT / "outputs" / "results" / "pipeline_calib_val"


def val_new_items():
    """Danh sách (img_path, label_path) của val_new (6 lớp) nếu có."""
    vn = PPE6_DATASET / "val_new.txt"
    if not vn.exists():
        return []
    out = []
    for line in vn.read_text(encoding="utf-8").splitlines():
        rel = line.strip().lstrip("./")
        if not rel:
            continue
        img = PPE6_DATASET / rel
        lab = (PPE6_DATASET / rel.replace("images/", "labels/")).with_suffix(".txt")
        if img.exists() and lab.exists():
            out.append((img, lab))
    return out


def label_sources(by_cls):
    """Nguồn file nhãn cho từng nhóm lớp: lớp < 4 từ ppe4 val, lớp >= 4 từ ppe6 val_new."""
    sources = [(sorted((DATASET / "labels" / "val").glob("*.txt")), {c for c in by_cls if c < 4})]
    if any(c >= 4 for c in by_cls):
        sources.append(([lab for _, lab in val_new_items()], {c for c in by_cls if c >= 4}))
    return [(files, cls_set) for files, cls_set in sources if files and cls_set]


def load_ignore_boxes():
    """{stem: {cls: [(cx, cy, w, h)]}} từ data/ppe6/dataset/ignore.csv."""
    p = PPE6_DATASET / "ignore.csv"
    out = {}
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            stem = Path(r["file"]).stem
            out.setdefault(stem, {}).setdefault(int(r["cls"]), []).append(
                (float(r["cx"]), float(r["cy"]), float(r["w"]), float(r["h"]))
            )
    return out


def is_ignored(box, ig_boxes):
    """Dự đoán không khớp GT nhưng trùng vùng ignore (IoU >= 0.5 hoặc IoA >= 0.5) thì bỏ qua."""
    if not len(ig_boxes):
        return False
    b = box.reshape(1, 4)
    ix = np.clip(np.minimum(b[:, None, 2], ig_boxes[None, :, 2]) - np.maximum(b[:, None, 0], ig_boxes[None, :, 0]), 0, None)
    iy = np.clip(np.minimum(b[:, None, 3], ig_boxes[None, :, 3]) - np.maximum(b[:, None, 1], ig_boxes[None, :, 1]), 0, None)
    inter = (ix * iy)[0]
    area_b = max((box[2] - box[0]) * (box[3] - box[1]), 1e-9)
    area_ig = (ig_boxes[:, 2] - ig_boxes[:, 0]) * (ig_boxes[:, 3] - ig_boxes[:, 1])
    iou = inter / (area_b + area_ig - inter + 1e-9)
    ioa = inter / area_b
    return bool(np.any((iou >= 0.5) | (ioa >= 0.5)))


def read_labels(path):
    rows = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [(int(r[0]), *map(float, r[1:])) for r in rows]


def to_xyxy(cx, cy, w, h):
    return np.array([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])


def regions(cfg):
    """Vùng cơ thể từ vị trí tương đối của tâm PPE (nhãn thật) trong hộp người chứa nó (chỉ PPE có đúng 1 người chứa)."""
    cal = cfg["calibration"]
    cov, margin = cal["region_coverage"], cal["inside_margin"]
    lo, hi = (1 - cov) / 2 * 100, (1 + cov) / 2 * 100
    rel = {name: [] for name in cfg["ppe"]}
    count = {name: dict(total=0, no_person=0, ambiguous=0, used=0) for name in cfg["ppe"]}
    by_cls = {p["cls"]: name for name, p in cfg["ppe"].items()}
    items = []
    for files, cls_set in label_sources(by_cls):
        for f in files:
            lab = read_labels(f)
            persons = [to_xyxy(*r[1:]) for r in lab if r[0] == cfg["person_cls"]]
            for r in lab:
                if r[0] not in cls_set:
                    continue
                name = by_cls.get(r[0])
                if name is None:
                    continue
                count[name]["total"] += 1
                cx, cy = r[1], r[2]
                owners = [p for p in persons
                          if p[0] - margin * (p[2] - p[0]) <= cx <= p[2] + margin * (p[2] - p[0])
                          and p[1] - margin * (p[3] - p[1]) <= cy <= p[3] + margin * (p[3] - p[1])]
                if not owners:
                    count[name]["no_person"] += 1
                    continue
                if len(owners) > 1:
                    count[name]["ambiguous"] += 1
                    continue
                p = owners[0]
                count[name]["used"] += 1
                rel[name].append(((cx - p[0]) / (p[2] - p[0]), (cy - p[1]) / (p[3] - p[1])))
                items.append((name, (cx, cy), p))

    region_cfg, by_region = {}, {}
    for name, p in cfg["ppe"].items():
        by_region.setdefault(p["region"], []).extend(rel[name])
    for reg, pts in by_region.items():
        a = np.array(pts)
        region_cfg[reg] = dict(x0=float(np.percentile(a[:, 0], lo)), x1=float(np.percentile(a[:, 0], hi)),
                               y0=float(np.percentile(a[:, 1], lo)), y1=float(np.percentile(a[:, 1], hi)))
        region_cfg[reg] = {k: round(v, 3) for k, v in region_cfg[reg].items()}

    # max_distance: khoảng cách (3.4) tới tâm vùng, tính trên PPE nằm trong vùng; lấy phân vị `coverage`.
    dist = {name: [] for name in cfg["ppe"]}
    for name, c, p in items:
        reg = region_cfg[cfg["ppe"][name]["region"]]
        for side in (SIDES if cfg["ppe"][name]["sides"] else (None,)):
            r = region_box(p, reg, side)
            if r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3]:
                dist[name].append(norm_distance(c, p, r))
    max_distance = {name: round(float(np.percentile(d, cov * 100)), 3) for name, d in dist.items()}
    inside = {name: f"{len(dist[name])}/{count[name]['used']}" for name in cfg["ppe"]}
    res = dict(regions=region_cfg, max_distance=max_distance, counts=count, inside_region=inside,
               coverage=cov, inside_margin=margin)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "regions.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))


def all_val_images():
    """Map stem -> (img_path, ppe4_label_or_None, valnew_label_or_None)."""
    by_stem = {}
    for img in sorted((DATASET / "images" / "val").iterdir()):
        by_stem[img.stem] = [img, DATASET / "labels" / "val" / f"{img.stem}.txt", None]
    for img, lab in val_new_items():
        if img.stem in by_stem:
            by_stem[img.stem][2] = lab
        else:
            by_stem[img.stem] = [img, None, lab]
    return by_stem


def predict(cfg, rerun):
    """Dự đoán trên val với conf rất thấp và NMS IoU 0.95 (gần như không NMS), lưu cache."""
    by_stem = all_val_images()
    cache = OUT / "preds.npz"
    if cache.exists() and not rerun:
        cached = dict(np.load(cache, allow_pickle=True))["data"].item()
        if set(by_stem).issubset(cached):
            return cached
    from ultralytics import YOLO

    d = cfg["detector"]
    model = YOLO(ROOT / d["weights"])
    data = {}
    val_dir = DATASET / "images" / "val"
    extra = [str(v[0]) for v in by_stem.values() if v[0].parent != val_dir]
    n = len(by_stem)
    i = 0
    for src in ([str(val_dir)] + ([extra] if extra else [])):
        for r in model.predict(src, imgsz=d["imgsz"], conf=0.01, iou=0.95,
                               max_det=1000, device=d["device"], stream=True, verbose=False):
            i += 1
            b = r.boxes.cpu().numpy()
            data[Path(r.path).stem] = dict(xyxy=b.xyxy, conf=b.conf, cls=b.cls.astype(int), shape=r.orig_shape)
            if i % 200 == 0 or i == n:
                print(f"  dự đoán {i}/{n}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, data=np.array(data, dtype=object))
    return data


def iou_matrix(a, b):
    ix = np.clip(np.minimum(a[:, None, 2], b[None, :, 2]) - np.maximum(a[:, None, 0], b[None, :, 0]), 0, None)
    iy = np.clip(np.minimum(a[:, None, 3], b[None, :, 3]) - np.maximum(a[:, None, 1], b[None, :, 1]), 0, None)
    inter = ix * iy
    area = lambda x: (x[:, 2] - x[:, 0]) * (x[:, 3] - x[:, 1])
    return inter / (area(a)[:, None] + area(b)[None, :] - inter + 1e-9)


def conf_nms(cfg, rerun):
    import torch
    from torchvision.ops import nms

    cal = cfg["calibration"]
    data = predict(cfg, rerun)
    names = {cfg["person_cls"]: "person", **{p["cls"]: n for n, p in cfg["ppe"].items()}}
    g = cal["conf_grid"]
    grid = np.round(np.arange(g["start"], g["stop"] + 1e-9, g["step"]), 4)
    by_stem = all_val_images()
    ig_raw = load_ignore_boxes()
    gt, ig = {}, {}
    for stem, p in data.items():
        if stem not in by_stem:
            continue
        h, w = p["shape"]
        _, lab4, lab6 = by_stem[stem]
        boxes = []
        if lab4 is not None and lab4.exists():
            boxes += [(r[0], to_xyxy(r[1] * w, r[2] * h, r[3] * w, r[4] * h)) for r in read_labels(lab4) if r[0] < 4]
        if lab6 is not None and lab6.exists():
            boxes += [(r[0], to_xyxy(r[1] * w, r[2] * h, r[3] * w, r[4] * h)) for r in read_labels(lab6) if r[0] >= 4]
        gt[stem] = boxes
        ig[stem] = {c: np.array([to_xyxy(x * w, y * h, bw * w, bh * h) for x, y, bw, bh in b_list]).reshape(-1, 4)
                    for c, b_list in ig_raw.get(stem, {}).items()}

    rows, best = [], {}
    for nms_iou in cal["nms_iou_grid"]:
        scores = {c: [] for c in names}       # (conf, khớp?) của mọi dự đoán sau NMS
        n_gt = {c: 0 for c in names}
        for stem, p in data.items():
            if stem not in by_stem:
                continue
            _, lab4, lab6 = by_stem[stem]
            for c in names:
                if (c < 4 and lab4 is None) or (c >= 4 and lab6 is None):
                    continue
                m = p["cls"] == c
                boxes, conf = p["xyxy"][m], p["conf"][m]
                if len(boxes):
                    keep = nms(torch.tensor(boxes), torch.tensor(conf), nms_iou).numpy()
                    boxes, conf = boxes[keep], conf[keep]
                g_boxes = np.array([b for k, b in gt[stem] if k == c]).reshape(-1, 4)
                n_gt[c] += len(g_boxes)
                # Ghép tham lam theo conf giảm dần: trạng thái khớp của một dự đoán không phụ thuộc ngưỡng conf.
                order = np.argsort(-conf)
                used = np.zeros(len(g_boxes), dtype=bool)
                ious = iou_matrix(boxes[order], g_boxes) if len(g_boxes) and len(boxes) else None
                for j, k in enumerate(order):
                    hit = False
                    if ious is not None:
                        cand = np.where(~used & (ious[j] >= cal["match_iou"]))[0]
                        if len(cand):
                            used[cand[np.argmax(ious[j][cand])]] = True
                            hit = True
                    if not hit and c >= 4 and is_ignored(boxes[k], ig[stem].get(c, ())):
                        continue
                    scores[c].append((float(conf[k]), hit))
        for c, name in names.items():
            s = np.array(scores[c]) if scores[c] else np.zeros((0, 2))
            for th in grid:
                sel = s[s[:, 0] >= th] if len(s) else s
                tp = int(sel[:, 1].sum()) if len(sel) else 0
                fp = len(sel) - tp
                fn = n_gt[c] - tp
                prec = tp / (tp + fp) if tp + fp else 0.0
                rec = tp / (tp + fn) if tp + fn else 0.0
                f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
                rows.append(dict(nms_iou=nms_iou, cls=name, conf=float(th), tp=tp, fp=fp, fn=fn,
                                 P=round(prec, 4), R=round(rec, 4), F1=round(f1, 4)))
                key = (nms_iou, name)
                if key not in best or f1 > best[key]["F1"]:
                    best[key] = rows[-1]
    with open(OUT / "conf_f1.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)

    print("\nconf cho F1 lớn nhất theo từng NMS IoU:")
    macro = {}
    for nms_iou in cal["nms_iou_grid"]:
        per = [best[(nms_iou, n)] for n in names.values()]
        macro[nms_iou] = float(np.mean([r["F1"] for r in per]))
        print(f"  NMS IoU {nms_iou}: F1 trung bình {macro[nms_iou]:.4f}")
        for r in per:
            print(f"    {r['cls']:<7} conf {r['conf']:.2f}  P {r['P']:.3f}  R {r['R']:.3f}  F1 {r['F1']:.3f}  "
                  f"(TP {r['tp']}, FP {r['fp']}, FN {r['fn']})")
    pick = max(macro, key=macro.get)
    res = dict(nms_iou=pick, conf={n: best[(pick, n)]["conf"] for n in names.values()},
               detail={n: best[(pick, n)] for n in names.values()}, macro_f1=macro)
    (OUT / "conf.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐề xuất: nms_iou {pick}, conf {res['conf']}")


def match_scores(boxes, conf, g_boxes, match_iou):
    """[(conf, khớp?)] sau ghép tham lam theo conf giảm dần (trạng thái khớp không phụ thuộc ngưỡng conf)."""
    order = np.argsort(-conf)
    used = np.zeros(len(g_boxes), dtype=bool)
    ious = iou_matrix(boxes[order], g_boxes) if len(g_boxes) and len(boxes) else None
    out = []
    for j, k in enumerate(order):
        hit = False
        if ious is not None:
            cand = np.where(~used & (ious[j] >= match_iou))[0]
            if len(cand):
                used[cand[np.argmax(ious[j][cand])]] = True
                hit = True
        out.append((float(conf[k]), hit))
    return out


def best_f1(scores, n_gt, grid):
    s = np.array(scores) if scores else np.zeros((0, 2))
    best = None
    for th in grid:
        sel = s[s[:, 0] >= th] if len(s) else s
        tp = int(sel[:, 1].sum()) if len(sel) else 0
        fp, fn = len(sel) - tp, n_gt - tp
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        if best is None or f1 > best["F1"]:
            best = dict(conf=float(th), tp=tp, fp=fp, fn=fn, P=round(p, 4), R=round(r, 4), F1=round(f1, 4))
    return best


def inside_any(cx, cy, persons, margin):
    return any(p[0] - margin * (p[2] - p[0]) <= cx <= p[2] + margin * (p[2] - p[0]) and
               p[1] - margin * (p[3] - p[1]) <= cy <= p[3] + margin * (p[3] - p[1]) for p in persons)


def crop_eval(cfg, rerun):
    """So sánh dò PPE trên cả khung với dò trên ảnh cắt từng người (đạt conf person) ở các cỡ ảnh cắt.

    Chỉ chấm PPE (nhãn và dự đoán) có tâm nằm trong một người detector tìm được (nới inside_margin):
    đó là phần chuỗi xử lý dùng được; PPE của người không được phát hiện thì không gán được cho ai.
    """
    import time

    import cv2
    import torch
    from torchvision.ops import nms
    from ultralytics import YOLO

    cal, d = cfg["calibration"], cfg["detector"]
    full = predict(cfg, False)
    person_conf, nms_iou, margin = d["conf"]["person"], d["nms_iou"], d["crop"]["margin"]
    ppe_cls = {p["cls"]: n for n, p in cfg["ppe"].items()}
    g = cal["conf_grid"]
    grid = np.round(np.arange(g["start"], g["stop"] + 1e-9, g["step"]), 4)
    by_stem = all_val_images()
    cache = OUT / "crop_preds.npz"
    if cache.exists() and not rerun:
        crop_preds, timing = np.load(cache, allow_pickle=True)["data"]
    else:
        model = YOLO(ROOT / d["weights"])
        crop_preds = {s: {} for s in cal["crop_imgsz_grid"]}
        timing = {s: [] for s in cal["crop_imgsz_grid"]}
        stems = sorted(by_stem)
        for i, stem in enumerate(stems, 1):
            p = full[stem]
            m = p["cls"] == cfg["person_cls"]
            boxes, conf = p["xyxy"][m], p["conf"][m]
            persons = []
            if len(boxes):
                keep = nms(torch.tensor(boxes), torch.tensor(conf), nms_iou).numpy()
                persons = [b for b, s in zip(boxes[keep], conf[keep]) if s >= person_conf]
            img = cv2.imread(str(by_stem[stem][0]))
            H, W = img.shape[:2]
            crops, offs = [], []
            for b in persons:
                w, h = b[2] - b[0], b[3] - b[1]
                x1, y1 = int(max(0, b[0] - margin * w)), int(max(0, b[1] - margin * h))
                x2, y2 = int(min(W, b[2] + margin * w)), int(min(H, b[3] + margin * h))
                if x2 - x1 >= 2 and y2 - y1 >= 2:
                    crops.append(img[y1:y2, x1:x2])
                    offs.append((x1, y1))
            for s in cal["crop_imgsz_grid"]:
                xy, cf, cl = [], [], []
                if crops:
                    t0 = time.perf_counter()
                    res = model.predict(crops, imgsz=s, conf=0.01, iou=0.95, max_det=300, device=d["device"],
                                        verbose=False)
                    timing[s].append((time.perf_counter() - t0) * 1000 / len(crops))
                    for (ox, oy), r in zip(offs, res):
                        b = r.boxes.cpu().numpy()
                        keep = b.cls.astype(int) != cfg["person_cls"]
                        xy.append(b.xyxy[keep] + np.array([ox, oy, ox, oy]))
                        cf.append(b.conf[keep])
                        cl.append(b.cls.astype(int)[keep])
                crop_preds[s][stem] = dict(
                    xyxy=np.concatenate(xy) if xy else np.zeros((0, 4)), conf=np.concatenate(cf) if cf else np.zeros(0),
                    cls=np.concatenate(cl) if cl else np.zeros(0, int), persons=np.array(persons).reshape(-1, 4),
                    shape=(H, W))
            if i % 200 == 0 or i == len(stems):
                print(f"  ảnh cắt {i}/{len(stems)}", flush=True)
        np.savez_compressed(cache, data=np.array((crop_preds, timing), dtype=object))

    s0 = cal["crop_imgsz_grid"][0]
    modes = {"full": full, **{f"crop{s}": crop_preds[s] for s in cal["crop_imgsz_grid"]}}
    results = {}
    for mode, preds in modes.items():
        scores = {c: [] for c in ppe_cls}
        n_gt = {c: 0 for c in ppe_cls}
        for stem, p in preds.items():
            if stem not in by_stem:
                continue
            _, lab4, lab6 = by_stem[stem]
            persons = crop_preds[s0][stem]["persons"]
            H, W = crop_preds[s0][stem]["shape"]
            lab_4 = read_labels(lab4) if lab4 is not None and lab4.exists() else []
            lab_6 = read_labels(lab6) if lab6 is not None and lab6.exists() else []
            for c in ppe_cls:
                if (c < 4 and lab4 is None) or (c >= 4 and lab6 is None):
                    continue
                lab = lab_4 if c < 4 else lab_6
                g_boxes = np.array([to_xyxy(r[1] * W, r[2] * H, r[3] * W, r[4] * H) for r in lab
                                    if r[0] == c and inside_any(r[1] * W, r[2] * H, persons, margin)]).reshape(-1, 4)
                n_gt[c] += len(g_boxes)
                m = p["cls"] == c
                boxes, conf = p["xyxy"][m], p["conf"][m]
                if len(boxes):
                    keep = nms(torch.tensor(boxes, dtype=torch.float32), torch.tensor(conf, dtype=torch.float32),
                               nms_iou).numpy()
                    boxes, conf = boxes[keep], conf[keep]
                    ok = np.array([inside_any((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, persons, margin) for b in boxes],
                                  dtype=bool)
                    boxes, conf = boxes[ok], conf[ok]
                scores[c] += match_scores(boxes, conf, g_boxes, cal["match_iou"])
        per = {ppe_cls[c]: best_f1(scores[c], n_gt[c], grid) for c in ppe_cls}
        size = int(mode[4:]) if mode.startswith("crop") else None
        results[mode] = dict(per_class=per, macro_f1=round(float(np.mean([v["F1"] for v in per.values()])), 4),
                             ms_per_person=round(float(np.median(timing[size])), 2) if size else None)
    print(f"\nPPE trong người đã phát hiện (conf person >= {person_conf}), NMS {nms_iou}, conf cho F1 lớn nhất:")
    for mode, r in results.items():
        t = f", {r['ms_per_person']} ms/người" if r["ms_per_person"] else ""
        print(f"  {mode:<8} F1 trung bình {r['macro_f1']:.4f}{t}")
        for name, v in r["per_class"].items():
            print(f"    {name:<7} conf {v['conf']:.2f}  P {v['P']:.3f}  R {v['R']:.3f}  F1 {v['F1']:.3f}  "
                  f"(TP {v['tp']}, FP {v['fp']}, FN {v['fn']})")
    (OUT / "crop.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


def pose_eval(cfg):
    """Pose trên val: với hộp người và hộp găng nhãn thật, tâm găng có nằm trong elip cổ tay không; so với vùng tay.

    Chỉ dùng người có ít nhất một găng trong nhãn (val không có nhãn tay trần). Kết quả theo cỡ người và lưới ngưỡng.
    """
    import time

    import cv2

    from ppe import Track
    from ppe.association import ellipse_value
    from ppe.pose import PoseEstimator

    cal = cfg["calibration"]
    margin, g_cls = cal["inside_margin"], cfg["ppe"]["gloves"]["cls"]
    hands = cfg["association"]["regions"]["hands"]
    pose = PoseEstimator(cfg, ROOT)
    rows, elapsed, n_people = [], 0.0, 0
    for f in sorted((DATASET / "labels" / "val").glob("*.txt")):
        lab = read_labels(f)
        gloves = [r for r in lab if r[0] == g_cls]
        if not gloves:
            continue
        img = next(iter((DATASET / "images" / "val").glob(f.stem + ".*")))
        im = cv2.imread(str(img))
        h, w = im.shape[:2]
        scale = np.array([w, h, w, h])
        persons = [to_xyxy(*r[1:]) * scale for r in lab if r[0] == cfg["person_cls"]]
        owned = {}
        for g in gloves:
            c = (g[1] * w, g[2] * h)
            own = [i for i, q in enumerate(persons)
                   if q[0] - margin * (q[2] - q[0]) <= c[0] <= q[2] + margin * (q[2] - q[0])
                   and q[1] - margin * (q[3] - q[1]) <= c[1] <= q[3] + margin * (q[3] - q[1])]
            if len(own) == 1:
                owned.setdefault(own[0], []).append(c)
        tracks = [Track(i, persons[i], 1.0, True) for i in owned]
        if not tracks:
            continue
        t0 = time.perf_counter()
        pose(im, tracks)
        elapsed += time.perf_counter() - t0
        n_people += len(tracks)
        for t in tracks:
            wr = t.extra.get("wrists", {})
            for c in owned[t.track_id]:
                rows.append(dict(h=(t.xyxy[3] - t.xyxy[1]) * cfg["detector"]["imgsz"] / max(h, w), c=c, box=t.xyxy, wr=wr,
                                 region=bool(region_box(t.xyxy, hands)[0] <= c[0] <= region_box(t.xyxy, hands)[2]
                                             and region_box(t.xyxy, hands)[1] <= c[1] <= region_box(t.xyxy, hands)[3])))

    def rate(sel, wc, rho):
        par = dict(rho_x=rho, rho_y=rho)
        hit = sum(any(q[2] >= wc and ellipse_value(r["c"], r["box"], q, par) <= 1 for q in r["wr"].values()) for r in sel)
        seen = sum(any(q[2] >= wc for q in r["wr"].values()) for r in sel)
        return round(hit / max(len(sel), 1), 3), round(seen / max(len(sel), 1), 3)

    bands = {"tat_ca": rows, "<120": [r for r in rows if r["h"] < 120],
             "120-240": [r for r in rows if 120 <= r["h"] < 240], ">=240": [r for r in rows if r["h"] >= 240]}
    res = dict(ms_per_person=round(elapsed / max(n_people, 1) * 1000, 1), people=n_people, gloves=len(rows),
               region_hit={k: round(sum(r["region"] for r in v) / max(len(v), 1), 3) for k, v in bands.items()},
               n={k: len(v) for k, v in bands.items()}, grid={})
    for wc in cal["pose_wrist_grid"]:
        for rho in cal["pose_rho_grid"]:
            res["grid"][f"wrist_conf {wc}, rho {rho}"] = {k: rate(v, wc, rho) for k, v in bands.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pose.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{n_people} người, {len(rows)} găng, {res['ms_per_person']} ms/người; trong vùng tay: {res['region_hit']}; n {res['n']}")
    for k, v in res["grid"].items():
        print(k, "(găng trong elip, găng có cổ tay đạt ngưỡng):", v)


def torso_eval(cfg):
    """Bước B: vùng thân theo khung xương cho áo, chọn và kiểm trên ppe4 val (nhãn áo, người thật; pose như pipeline).

    1. Áo có đúng một người chứa (inside_margin). Pose (PoseEstimator) chạy trên mọi hộp người của ảnh.
    2. Tham số: với áo có hai vai đạt kp_conf (part_cls.kp_conf): u = (cx - mx) / sw, v = (cy - my) / sw,
       w = (cy - hông) / sw. kx = phân vị cao của |u|; ky0 = -phân vị thấp của v; ky1 = phân vị cao của v;
       kh = phân vị cao của w (khi thấy hông). Phân vị theo calibration.region_coverage như --regions.
    3. Kiểm: Associator với cấu hình hiện tại (không torso_pose) và có torso_pose, hộp áo nhãn thật làm phát hiện;
       đếm áo ghép đúng người chứa, ghép sang người khác, không ghép. Trên ảnh đủ và ảnh cắt ngang ở 55/65/75% chiều
       cao hộp người tính từ đỉnh (giả lập người sát camera bị cắt ở ngực; pose chạy lại trên ảnh đã cắt).
    """
    import copy

    import cv2

    from ppe import Det, Track
    from ppe.association import Associator
    from ppe.pose import PoseEstimator

    cal = cfg["calibration"]
    cov, margin = cal["region_coverage"], cal["inside_margin"]
    lo, hi = (1 - cov) / 2 * 100, (1 + cov) / 2 * 100
    kc = cfg["part_cls"]["kp_conf"]
    v_cls, p_cls = cfg["ppe"]["vest"]["cls"], cfg["person_cls"]
    pose = PoseEstimator(cfg, ROOT)

    def owner(c, persons):
        own = [i for i, q in enumerate(persons)
               if q[0] - margin * (q[2] - q[0]) <= c[0] <= q[2] + margin * (q[2] - q[0])
               and q[1] - margin * (q[3] - q[1]) <= c[1] <= q[3] + margin * (q[3] - q[1])]
        return own[0] if len(own) == 1 else None

    def scene(im, persons, vests):
        """Track (pose đã chạy) cho mọi người, Det cho mọi áo, chủ của từng áo."""
        tracks = [Track(i, q.copy(), 1.0, True) for i, q in enumerate(persons)]
        if tracks:
            pose(im, tracks)
        dets = [Det(v_cls, b.copy(), 1.0) for b in vests]
        own = [owner(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), persons) for b in vests]
        return tracks, dets, own

    images = []
    for f in sorted((DATASET / "labels" / "val").glob("*.txt")):
        lab = read_labels(f)
        if not any(r[0] == v_cls for r in lab):
            continue
        img = next(iter((DATASET / "images" / "val").glob(f.stem + ".*")))
        im = cv2.imread(str(img))
        h, w = im.shape[:2]
        sc = np.array([w, h, w, h])
        persons = [to_xyxy(*r[1:]) * sc for r in lab if r[0] == p_cls]
        vests = [to_xyxy(*r[1:]) * sc for r in lab if r[0] == v_cls]
        if persons:
            images.append((img.name, im, persons, vests))
    print(f"ppe4 val: {len(images)} ảnh có áo và người", flush=True)

    U, V, W = [], [], []
    full = []
    for name, im, persons, vests in images:
        tracks, dets, own = scene(im, persons, vests)
        full.append((tracks, dets, own))
        for d, o in zip(dets, own):
            if o is None:
                continue
            k = tracks[o].extra.get("kps")
            if not k or k[5][2] < kc or k[6][2] < kc:
                continue
            sw = float(np.hypot(k[5][0] - k[6][0], k[5][1] - k[6][1]))
            if sw < 1:
                continue
            mx, my = (k[5][0] + k[6][0]) / 2, (k[5][1] + k[6][1]) / 2
            cx, cy = d.center
            U.append((cx - mx) / sw)
            V.append((cy - my) / sw)
            if k[11][2] >= kc and k[12][2] >= kc:
                W.append((cy - (k[11][1] + k[12][1]) / 2) / sw)
    U, V, W = np.array(U), np.array(V), np.array(W)
    tp = dict(kp_conf=kc, kx=round(float(max(-np.percentile(U, lo), np.percentile(U, hi))), 3),
              ky0=round(float(-np.percentile(V, lo)), 3), ky1=round(float(np.percentile(V, hi)), 3),
              kh=round(float(np.percentile(W, hi)), 3))
    print(f"áo có hai vai: {len(U)}, có hông: {len(W)}; torso_pose đề xuất: {tp}", flush=True)

    cfg_old = copy.deepcopy(cfg)
    cfg_old["association"].pop("torso_pose", None)
    cfg_new = copy.deepcopy(cfg)
    cfg_new["association"]["torso_pose"] = tp
    assoc = {"ban_cu": Associator(cfg_old), "torso_pose": Associator(cfg_new)}

    def score(scenes):
        out = {k: dict(dung=0, sai_nguoi=0, khong_ghep=0, n=0) for k in assoc}
        for tracks, dets, own in scenes:
            for k, a in assoc.items():
                res = a(tracks, dets)
                where = {id(d): tid for tid, items in res.owned.items() for ds in items.values() for d in ds}
                for d, o in zip(dets, own):
                    if o is None:
                        continue
                    out[k]["n"] += 1
                    t = where.get(id(d))
                    out[k]["dung" if t == o else ("khong_ghep" if t is None else "sai_nguoi")] += 1
        for k, x in out.items():
            n = max(x["n"], 1)
            x.update(ti_le_dung=round(x["dung"] / n, 4), ti_le_sai_nguoi=round(x["sai_nguoi"] / n, 4))
        return out

    res = dict(params=tp, n_shoulders=len(U), n_hips=len(W), coverage=cov, full=score(full), cut={})
    for frac in (0.55, 0.65, 0.75):
        scenes = []
        for name, im, persons, vests in images:
            for vb in vests:
                o = owner(((vb[0] + vb[2]) / 2, (vb[1] + vb[3]) / 2), persons)
                if o is None:
                    continue
                q = persons[o]
                yc = int(q[1] + frac * (q[3] - q[1]))
                if yc >= im.shape[0] - 2 or yc <= vb[1] + 0.3 * (vb[3] - vb[1]):
                    continue        # không bị cắt, hoặc áo còn quá ít (dưới 30% chiều cao)
                ps = [np.array([p[0], p[1], p[2], min(p[3], yc)]) for p in persons if p[1] < yc - 2]
                vs = [np.array([b[0], b[1], b[2], min(b[3], yc)]) for b in vests if b[1] < yc - 2]
                tracks, dets, own = scene(im[:yc].copy(), ps, vs)
                # chỉ chấm áo đang xét; áo khác trong ảnh vẫn là phát hiện để kiểm ghép nhầm
                tgt = [i for i, b in enumerate(vs) if abs(b[0] - vb[0]) < 1e-6 and abs(b[1] - vb[1]) < 1e-6]
                own = [own[i] if i in tgt else None for i in range(len(own))]
                scenes.append((tracks, dets, own))
        res["cut"][str(frac)] = score(scenes)
        print(f"cắt {frac}: {res['cut'][str(frac)]}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "torso.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "cut"}, ensure_ascii=False, indent=1))
    print("Ghi", (OUT / "torso.json").relative_to(ROOT))


def unit_folds(rows, block):
    """Bước B2, V4: chia val hai phần theo đơn vị nhóm (kế hoạch ppe6 mục B2).

    rows: dict có file, image (đường dẫn ảnh gốc), group_id, source, n_vest (như data/ppe4/stats.csv).
    Đơn vị = hợp (union-find) các ảnh cùng group_id và các ảnh cùng nguồn có số thứ tự cuối tên file gốc trong cùng
    khối floor(số / block); ảnh không có số chỉ theo group_id. Mã đơn vị = group_id nhỏ nhất của đơn vị.
    Đơn vị gồm ảnh của nhiều nguồn: tính vào nguồn có nhiều ảnh nhất (bằng nhau: theo thứ tự chữ cái) [chi tiết thiết
    kế chưa ghi, chờ người dùng duyệt]. Trong từng nguồn: sắp đơn vị theo sha1(mã đơn vị), lần lượt đưa vào phần đang
    ít áo hơn trong nguồn đó (bằng nhau: phần 1). Trả về ({file: 1 | 2}, danh sách đơn vị)."""
    import hashlib
    import re
    from collections import Counter, defaultdict

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for r in rows:
        f = ("f", r["file"])
        union(f, ("g", r["group_id"]))
        nums = re.findall(r"\d+", Path(r["image"]).stem)
        if nums:
            union(f, ("b", r["source"], int(nums[-1]) // block))
    members = defaultdict(list)
    for r in rows:
        members[find(("f", r["file"]))].append(r)
    units, by_src = [], defaultdict(list)
    for ms in members.values():
        cnt = Counter(r["source"] for r in ms)
        u = dict(code=min(r["group_id"] for r in ms), source=min(cnt, key=lambda s: (-cnt[s], s)), sources=dict(cnt),
                 files=sorted(r["file"] for r in ms), groups=sorted({r["group_id"] for r in ms}),
                 n_vest=sum(int(r["n_vest"]) for r in ms))
        units.append(u)
        by_src[u["source"]].append(u)
    fold = {}
    for src in sorted(by_src):
        load = {1: 0, 2: 0}
        for u in sorted(by_src[src], key=lambda u: (hashlib.sha1(u["code"].encode()).hexdigest(), u["code"])):
            k = 1 if load[1] <= load[2] else 2
            load[k] += u["n_vest"]
            u["fold"] = k
            for f in u["files"]:
                fold[f] = k
    units.sort(key=lambda u: u["code"])
    return fold, units


def provenance(cache):
    """Hồ sơ tái lập cho 05a --torso-strict: commit nền, file đang sửa, sha256 dữ liệu val, cache, cấu hình, trọng số, code."""
    import datetime
    import hashlib
    import platform
    import subprocess

    def sha(path, text=False):
        b = Path(path).read_bytes()
        return hashlib.sha256(b.replace(b"\r\n", b"\n") if text else b).hexdigest()

    def sha_dir(paths, text=False):
        h = hashlib.sha256()
        for q in sorted(paths, key=lambda x: x.name):
            h.update(q.name.encode() + b"\0" + bytes.fromhex(sha(q, text)))
        return h.hexdigest()

    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    cfg = load_config()
    env = dict(python=platform.python_version())
    try:
        import torch
        import ultralytics
        env.update(torch=torch.__version__, ultralytics=ultralytics.__version__)
    except Exception as e:   # noqa: BLE001
        env["import_error"] = str(e)
    code = ["scripts/05a_calibrate_val.py", "src/ppe/association.py", "src/ppe/pose.py", "src/ppe/__init__.py"]
    return dict(
        thoi_diem=datetime.datetime.now().isoformat(timespec="seconds"), commit_nen=git("rev-parse", "HEAD"),
        file_dang_sua=git("status", "--porcelain").splitlines(), moi_truong=env,
        sha256=dict(
            stats_csv=sha(ROOT / "data" / "ppe4" / "stats.csv", True),
            val_labels=sha_dir(list((DATASET / "labels" / "val").glob("*.txt")), True),
            val_images=sha_dir([q for q in (DATASET / "images" / "val").iterdir() if q.is_file()]),
            preds_cache=sha(cache), pipeline_yaml=sha(ROOT / "configs" / "pipeline.yaml", True),
            pose_weights=sha(ROOT / cfg["pose"]["weights"]), detector_weights_cache=sha(ROOT / cfg["detector"]["weights"]),
            **{c: sha(ROOT / c, True) for c in code}),
        ghi_chu=("Code B2 chưa commit: commit_nen + file_dang_sua; sha256 code ở trên là bản đã chạy. File text tính sau "
                 "khi đổi CRLF thành LF. Cache preds.npz tạo 11/11/2026 bằng 05a --conf (C4), chỉ đọc."))


def torso_strict_eval(cfg):
    """Bước B2 (kế hoạch ppe6 mục B2): chọn association.torso_strict trên ppe4 val, đo V1-V4 và chẩn đoán G5.

    So bản 4 (không torso_pose, torso_strict), B1 (torso_pose = association.torso_pose_b1), B2, B2 không G5 (s_min = 0,
    chỉ để chẩn đoán G5, không phải phương án chọn). Hộp áo nhãn thật làm phát hiện, pose chạy trên hộp người nhãn như
    pipeline. Chỉ ghi outputs/results/pipeline_calib_val/torso_strict.json; không sửa cấu hình.
    1. Tham số (ảnh đủ, áo có đúng một người chứa; phân vị theo region_coverage): mẫu qua G2, G3(a)(c)(d) ->
       slope_max_deg = phân vị cao của góc vai; mẫu qua thêm G3(b) -> kx, ky0, kh, s_min. edge_px: hộp người phát hiện
       (cache preds.npz, lọc conf person và NMS như cấu hình) ghép IoU lớn nhất >= calibration.video.match_iou với hộp
       người nhãn chạm đáy ảnh (y2 >= H - 1); phân vị cao của H - y2, làm tròn lên.
    2. V1 ảnh đủ; V2 cắt ở 55/65/75% chiều cao người chủ áo (như --torso); V3 bỏ hộp người chủ áo (ảnh có từ 2 người),
       áo bị gán cho người còn lại = gán nhầm; ở ảnh đủ và 3 mức cắt.
    3. V4: unit_folds; chọn trên phần này, đo trên phần kia, hai chiều. Tham số đề xuất = chọn trên toàn val.
    """
    import copy
    import math
    from collections import Counter

    import cv2
    import torch
    from torchvision.ops import nms

    from ppe import Det, Track
    from ppe.association import Associator, shoulder_geometry
    from ppe.pose import PoseEstimator

    sys.stdout.reconfigure(encoding="utf-8")
    cal = cfg["calibration"]
    cov, margin = cal["region_coverage"], cal["inside_margin"]
    lo, hi = (1 - cov) / 2 * 100, (1 + cov) / 2 * 100
    kc = cfg["part_cls"]["kp_conf"]
    v_cls, p_cls = cfg["ppe"]["vest"]["cls"], cfg["person_cls"]
    fracs = (0.55, 0.65, 0.75)
    assert cfg["pose"]["enabled"], "B2 cần pose.enabled"
    pose = PoseEstimator(cfg, ROOT)

    stats = [r for r in csv.DictReader((ROOT / "data" / "ppe4" / "stats.csv").open(encoding="utf-8"))
             if r["split"] == "val"]
    fold_file, units = unit_folds(stats, cal["torso_strict_fold_block"])
    fold_of = {Path(f).stem: k for f, k in fold_file.items()}
    src_of = {Path(r["file"]).stem: r["source"] for r in stats}
    grp_of = {Path(r["file"]).stem: r["group_id"] for r in stats}

    def owner(c, persons):
        own = [i for i, q in enumerate(persons)
               if q[0] - margin * (q[2] - q[0]) <= c[0] <= q[2] + margin * (q[2] - q[0])
               and q[1] - margin * (q[3] - q[1]) <= c[1] <= q[3] + margin * (q[3] - q[1])]
        return own[0] if len(own) == 1 else None

    def make_scene(stem, im, persons, vests, target=None):
        tracks = [Track(i, q.copy(), 1.0, True) for i, q in enumerate(persons)]
        if tracks:
            pose(im, tracks)
        dets = [Det(v_cls, b.copy(), 1.0) for b in vests]
        own = [owner(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), persons) for b in vests]
        if target is not None:          # ảnh cắt: chỉ chấm áo đang xét, áo khác vẫn là phát hiện
            own = [o if i == target else None for i, o in enumerate(own)]
        return dict(stem=stem, tracks=tracks, dets=dets, own=own, shape=im.shape)

    # 1. Cảnh: ảnh đủ và ảnh cắt (pose chạy lại trên ảnh cắt)
    full, cut = [], {f: [] for f in fracs}
    files = [f for f in sorted((DATASET / "labels" / "val").glob("*.txt"))
             if any(r[0] == v_cls for r in read_labels(f))]
    for n_img, f in enumerate(files, 1):
        lab = read_labels(f)
        img = next(iter((DATASET / "images" / "val").glob(f.stem + ".*")))
        im = cv2.imread(str(img))
        h, w = im.shape[:2]
        sc = np.array([w, h, w, h])
        persons = [to_xyxy(*r[1:]) * sc for r in lab if r[0] == p_cls]
        vests = [to_xyxy(*r[1:]) * sc for r in lab if r[0] == v_cls]
        if not persons:
            continue
        full.append(make_scene(f.stem, im, persons, vests))
        for frac in fracs:
            for vb in vests:
                o = owner(((vb[0] + vb[2]) / 2, (vb[1] + vb[3]) / 2), persons)
                if o is None:
                    continue
                q = persons[o]
                yc = int(q[1] + frac * (q[3] - q[1]))
                if yc >= h - 2 or yc <= vb[1] + 0.3 * (vb[3] - vb[1]):
                    continue        # không bị cắt, hoặc áo còn dưới 30% chiều cao (như --torso)
                ps = [np.array([p[0], p[1], p[2], min(p[3], yc)]) for p in persons if p[1] < yc - 2]
                vs = [np.array([b[0], b[1], b[2], min(b[3], yc)]) for b in vests if b[1] < yc - 2]
                tgt = [i for i, b in enumerate(vs) if abs(b[0] - vb[0]) < 1e-6 and abs(b[1] - vb[1]) < 1e-6]
                cut[frac].append(make_scene(f.stem, im[:yc].copy(), ps, vs, tgt[0] if tgt else -1))
        if n_img % 50 == 0 or n_img == len(files):
            print(f"  cảnh {n_img}/{len(files)}", flush=True)
    print(f"ppe4 val: {len(full)} ảnh có áo và người; ca cắt: { {f: len(v) for f, v in cut.items()} }", flush=True)

    # 2. Khoảng cách đáy hộp người phát hiện tới đáy ảnh, cho người nhãn chạm đáy (mọi ảnh val)
    # Cache dự đoán của detector (05a --conf, C4) chỉ đọc: không gọi predict() để không thể chạy lại hay ghi đè.
    cache = OUT / "preds.npz"
    preds = dict(np.load(cache, allow_pickle=True))["data"].item()
    d = cfg["detector"]
    edge_vals, miss = {}, 0
    for f in sorted((DATASET / "labels" / "val").glob("*.txt")):
        p = preds.get(f.stem)
        if p is None:
            miss += 1
            continue
        H, W = p["shape"]
        touch = [to_xyxy(*r[1:]) * np.array([W, H, W, H]) for r in read_labels(f) if r[0] == p_cls]
        touch = [q for q in touch if q[3] >= H - 1]
        m = (p["cls"] == p_cls) & (p["conf"] >= d["conf"]["person"])
        boxes, confs = p["xyxy"][m], p["conf"][m]
        if not touch or not len(boxes):
            continue
        keep = nms(torch.tensor(boxes, dtype=torch.float32), torch.tensor(confs, dtype=torch.float32),
                   d["nms_iou"]).numpy()
        boxes = boxes[keep]
        iou = iou_matrix(np.array(touch), boxes)
        for i in range(len(touch)):
            j = int(np.argmax(iou[i]))
            if iou[i, j] >= cal["video"]["match_iou"]:
                edge_vals.setdefault(f.stem, []).append(max(0.0, float(H - boxes[j][3])))
    assert miss == 0, f"preds.npz thiếu {miss} ảnh val: chạy lại --conf --rerun trước"

    def pct(x, q):
        assert len(x), "không đủ mẫu để chọn tham số"
        return float(np.percentile(np.array(x, dtype=float), q))

    def choose(stems):
        rec = []
        for s in full:
            if s["stem"] not in stems:
                continue
            for dd, o in zip(s["dets"], s["own"]):
                if o is None:
                    continue
                g = shoulder_geometry(s["tracks"][o], kc)
                if g is not None:
                    rec.append((g, *dd.center, dd.xyxy[2] - dd.xyxy[0]))
        slope = pct([g["angle"] for g, *_ in rec], hi)
        sel = [x for x in rec if x[0]["angle"] <= slope]
        U = [(cx - g["mx"]) / g["sw"] for g, cx, cy, wd in sel]
        V = [(cy - g["my"]) / g["sw"] for g, cx, cy, wd in sel]
        Wh = [(cy - g["hy"]) / g["sw"] for g, cx, cy, wd in sel if g["hy"] is not None]
        R = [wd / g["sw"] for g, cx, cy, wd in sel]
        E = [e for st in stems for e in edge_vals.get(st, [])]
        params = dict(kp_conf=kc, kx=round(max(-pct(U, lo), pct(U, hi)), 3), ky0=round(-pct(V, lo), 3),
                      kh=round(pct(Wh, hi), 3), slope_max_deg=round(slope, 2), s_min=round(pct(R, lo), 3),
                      edge_px=int(math.ceil(pct(E, hi))))
        counts = dict(ao_qua_G2_G3acd=len(rec), ao_qua_G2_G3=len(sel), ao_co_hong=len(Wh), nguoi_nhan_cham_day=len(E))
        return params, counts

    def make_assoc(params):
        base = copy.deepcopy(cfg)
        base["association"].pop("torso_pose", None)
        base["association"].pop("torso_strict", None)
        b1, b2, b2n = copy.deepcopy(base), copy.deepcopy(base), copy.deepcopy(base)
        b1["association"]["torso_pose"] = dict(cfg["association"]["torso_pose_b1"])
        b2["association"]["torso_strict"] = dict(params)
        b2n["association"]["torso_strict"] = {**params, "s_min": 0.0}
        return {"ban_4": Associator(base), "B1": Associator(b1), "B2": Associator(b2),
                "B2_khong_G5": Associator(b2n)}

    def where(a, sc, tracks):
        res = a(tracks, sc["dets"], sc["shape"])
        return {id(x): tid for tid, items in res.owned.items() for ds in items.values() for x in ds}

    def outcomes(a, scenes):
        """(V1/V2) kết quả từng áo có chủ: dung / sai_nguoi / khong_ghep; (V3) áo bị gán sau khi bỏ chủ: True/False."""
        o12, o3 = {}, {}
        for si, sc in scenes:
            wh = where(a, sc, sc["tracks"])
            for vi, (dd, o) in enumerate(zip(sc["dets"], sc["own"])):
                if o is None:
                    continue
                t = wh.get(id(dd))
                o12[(si, vi)] = "dung" if t == o else ("khong_ghep" if t is None else "sai_nguoi")
                if len(sc["tracks"]) >= 2:
                    rest = [tr for tr in sc["tracks"] if tr.track_id != o]
                    o3[(si, vi)] = id(dd) in where(a, sc, rest)
        return o12, o3

    def evaluate(params, stems):
        assoc = make_assoc(params)
        sets = {"du": [(i, s) for i, s in enumerate(full) if s["stem"] in stems]}
        sets.update({str(f): [(i, s) for i, s in enumerate(cut[f]) if s["stem"] in stems] for f in fracs})
        out, raw = {}, {}
        for name, a in assoc.items():
            out[name], raw[name] = {"V1": None, "V2": {}, "V3": {}}, {}
            for k, scenes in sets.items():
                o12, o3 = outcomes(a, scenes)
                raw[name][k] = (o12, o3)
                c = Counter(o12.values())
                x = dict(n=len(o12), dung=c["dung"], sai_nguoi=c["sai_nguoi"], khong_ghep=c["khong_ghep"],
                         ti_le_dung=round(c["dung"] / max(len(o12), 1), 4))
                if k == "du":
                    out[name]["V1"] = x
                else:
                    out[name]["V2"][k] = x
                out[name]["V3"][k] = dict(n=len(o3), gan_nham=sum(o3.values()))
                stem_of = {si: sc["stem"] for si, sc in scenes}
                by = out[name].setdefault("theo_nguon", {}).setdefault(k, {})
                for (si, vi), v in o12.items():
                    x = by.setdefault(src_of[stem_of[si]], dict(n=0, dung=0, sai_nguoi=0, khong_ghep=0, V3_n=0, V3_gan_nham=0))
                    x["n"] += 1
                    x[v] += 1
                for (si, vi), v in o3.items():
                    x = by.setdefault(src_of[stem_of[si]], dict(n=0, dung=0, sai_nguoi=0, khong_ghep=0, V3_n=0, V3_gan_nham=0))
                    x["V3_n"] += 1
                    x["V3_gan_nham"] += int(v)
        g5 = {"ao_hop_le_bi_G5_loai": {}, "ao_G5_chan_duoc": {}}
        for k in sets:
            (a12, a3), (b12, b3) = raw["B2"][k], raw["B2_khong_G5"][k]
            g5["ao_hop_le_bi_G5_loai"][k] = sum(1 for key, v in b12.items() if v == "dung" and a12[key] == "khong_ghep")
            g5["ao_G5_chan_duoc"][k] = sum(1 for key, v in b3.items() if v and not a3[key])
        g5["ao_nguoi_sau_gan_nham"] = {n: {k: v["gan_nham"] for k, v in out[n]["V3"].items()} for n in out}
        return out, g5

    def check(res):
        """Tiêu chí V1-V3 (kế hoạch mục B2). Cùng tập ca cho mọi bản nên so số áo ghép đúng thay cho tỉ lệ."""
        b, v = res["B2"], res["ban_4"]
        return dict(
            V1=b["V1"]["dung"] >= v["V1"]["dung"] and b["V1"]["sai_nguoi"] <= v["V1"]["sai_nguoi"],
            V2=all(b["V2"][k]["dung"] > v["V2"][k]["dung"] and b["V2"][k]["sai_nguoi"] <= v["V2"][k]["sai_nguoi"]
                   for k in v["V2"]),
            V3=all(b["V3"][k]["gan_nham"] <= v["V3"][k]["gan_nham"] for k in v["V3"]))

    def fold_stats(k, stems, res):
        F = [s for s in full if s["stem"] in stems]
        _, mau = choose(stems)
        n_ao = Counter()
        for s in F:
            n_ao[src_of[s["stem"]]] += len(s["dets"])
        return dict(don_vi=sum(1 for u in units if u["fold"] == k), anh_val=len(stems), anh_co_ao_nguoi=len(F),
                    nguoi=sum(len(s["tracks"]) for s in F), ao=sum(len(s["dets"]) for s in F),
                    ao_chu_duy_nhat=res["ban_4"]["V1"]["n"], ao_theo_nguon=dict(n_ao),
                    ca_V2={kk: x["n"] for kk, x in res["ban_4"]["V2"].items()},
                    ca_V3={kk: x["n"] for kk, x in res["ban_4"]["V3"].items()}, mau_G2_G3=mau)

    all_stems = {s["stem"] for s in full} | set(edge_vals) | set(fold_of)
    parts = {k: {st for st, kk in fold_of.items() if kk == k} for k in (1, 2)}
    overlap = sorted({grp_of[s] for s in parts[1]} & {grp_of[s] for s in parts[2]})
    assert not overlap, f"group_id ở cả hai phần: {overlap[:5]}"

    result = dict(ho_so=provenance(cache), fold_block=cal["torso_strict_fold_block"], coverage=cov,
                  nhom_o_ca_hai_phan=overlap, don_vi_nhieu_nguon=sum(1 for u in units if len(u["sources"]) > 1),
                  ly_do_chon=("Phân vị theo calibration.region_coverage (thấp = (1-cov)/2, cao = (1+cov)/2): mẫu ảnh đủ, áo "
                              "có đúng một người chứa, qua G2, G3(a)(c)(d) -> slope_max_deg = phân vị cao của góc vai; qua "
                              "thêm G3(b) -> kx = max(-thấp, cao) của u, ky0 = -thấp của v, kh = cao của w, s_min = thấp "
                              "của r; edge_px = phân vị cao của H - y2 (người nhãn chạm đáy ghép người phát hiện), làm "
                              "tròn lên. kp_conf = part_cls.kp_conf. Kế hoạch ppe6 mục B2."),
                  thiet_lap=dict(fracs=list(fracs), kp_conf=kc, inside_margin=margin, match_iou=cal["video"]["match_iou"],
                                 conf_person=d["conf"]["person"], nms_iou=d["nms_iou"], cache_conf_min=0.01,
                                 cache_nms_iou=0.95, cache_max_det=1000), V4={})
    with (OUT / "torso_strict_folds.csv").open("w", encoding="utf-8", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["file", "source", "group_id", "unit_code", "unit_source", "fold"])
        for u in units:
            for f in u["files"]:
                wr.writerow([f, src_of[Path(f).stem], grp_of[Path(f).stem], u["code"], u["source"], u["fold"]])
    verdict = {}
    for a_k, b_k in ((1, 2), (2, 1)):
        params, counts = choose(parts[a_k])
        res, g5 = evaluate(params, parts[b_k])
        ck = check(res)
        name = f"chon_phan{a_k}_do_phan{b_k}"
        result["V4"][name] = dict(tham_so=params, mau_chon=counts, ket_qua=res, chan_doan_G5=g5, tieu_chi=ck,
                                  phan_chon=fold_stats(a_k, parts[a_k], evaluate(params, parts[a_k])[0]),
                                  phan_do=fold_stats(b_k, parts[b_k], res))
        verdict[f"V4_{name}"] = all(ck.values())
        print(name, params, ck, flush=True)
    params, counts = choose(all_stems)
    res, g5 = evaluate(params, all_stems)
    ck = check(res)
    result.update(tham_so_de_xuat=params, mau_chon=counts, toan_val_trong_mau=dict(ket_qua=res, chan_doan_G5=g5,
                  tieu_chi=ck))
    verdict.update({k: v for k, v in ck.items()})
    result["dat"] = dict(verdict, tat_ca=all(verdict.values()))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "torso_strict.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("toàn val (trong mẫu):", params, ck)
    print("kết luận tiêu chí V1-V4:", result["dat"])
    print("Ghi", (OUT / "torso_strict.json").relative_to(ROOT), "(chưa ghi cấu hình; người dùng duyệt trước)")


def assoc_pose_eval(cfg):
    """Bước F (kế hoạch ppe6 mục F, 16/11/2026): vùng theo khung xương, chọn và kiểm trên val. Không đụng test, holdout, video.

    Áo, găng: ppe4 val; kính: val_new (nhãn 6 lớp). Người, PPE nhãn thật làm phát hiện; pose như pipeline. So bản chính
    (configs/pipeline.yaml hiện tại) với F1 (eye_anchor, kính), F2 (torso_strict + edge_frac, áo), F3
    (gloves_region_fallback, găng). Ảnh đủ, cắt 55/65/75% chiều cao người chủ (pose chạy lại trên ảnh cắt), V3b chồng hộp
    (bỏ người chủ, nới hộp người gần nhất cho bao hộp PPE). Tham số: k_eye = phân vị cao (region_coverage) của khoảng cách
    tâm kính - trung điểm mắt / khoảng cách hai mắt; edge_frac = phân vị cao của (H - y2) / H (người nhãn chạm đáy ghép
    người phát hiện, cache preds.npz chỉ đọc); F2 dùng lại tham số B2 đã chọn trên val (torso_strict.json) trừ edge_px.
    Ghi outputs/results/pipeline_calib_val/assoc_pose.json; không sửa cấu hình."""
    import copy
    import datetime
    import hashlib
    import math
    import subprocess

    import cv2
    import torch
    from torchvision.ops import nms

    from ppe import Det, Track
    from ppe.association import Associator
    from ppe.pose import PoseEstimator

    sys.stdout.reconfigure(encoding="utf-8")
    cal = cfg["calibration"]
    cov, margin = cal["region_coverage"], cal["inside_margin"]
    hi = (1 + cov) / 2 * 100
    kc = cfg["part_cls"]["kp_conf"]
    fracs = (0.55, 0.65, 0.75)
    P = cfg["person_cls"]
    CLS = {n: cfg["ppe"][n]["cls"] for n in ("vest", "gloves", "goggles")}
    NAME = {v: k for k, v in CLS.items()}
    pose = PoseEstimator(cfg, ROOT)

    def owner(c, persons):
        own = [i for i, q in enumerate(persons)
               if q[0] - margin * (q[2] - q[0]) <= c[0] <= q[2] + margin * (q[2] - q[0])
               and q[1] - margin * (q[3] - q[1]) <= c[1] <= q[3] + margin * (q[3] - q[1])]
        return own[0] if len(own) == 1 else None

    def make(stem, im, persons, boxes, only_owner=None):
        """boxes: [(tên, hộp)]. Chấm (own != None) mọi PPE có chủ; only_owner: chỉ PPE của người đó (ảnh cắt)."""
        tracks = [Track(i, q.copy(), 1.0, True) for i, q in enumerate(persons)]
        if tracks:
            pose(im, tracks)
        dets = [Det(CLS[n], b.copy(), 1.0) for n, b in boxes]
        own = [owner(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), persons) for _, b in boxes]
        if only_owner is not None:
            own = [o if o == only_owner else None for o in own]
        return dict(stem=stem, tracks=tracks, dets=dets, names=[n for n, _ in boxes], own=own, shape=im.shape)

    # 1. Cảnh
    srcs = []
    for f in sorted((DATASET / "labels" / "val").glob("*.txt")):
        lab = read_labels(f)
        if any(r[0] in (CLS["vest"], CLS["gloves"]) for r in lab):
            srcs.append((f.stem, next(iter((DATASET / "images" / "val").glob(f.stem + ".*"))), lab, ("vest", "gloves")))
    for img, labp in val_new_items():
        lab = read_labels(labp)
        if any(r[0] == CLS["goggles"] for r in lab):
            srcs.append((img.stem, img, lab, ("goggles",)))
    full, cut = [], {f: [] for f in fracs}
    for n_img, (stem, img, lab, names) in enumerate(srcs, 1):
        im = cv2.imread(str(img))
        h, w = im.shape[:2]
        sc = np.array([w, h, w, h])
        persons = [to_xyxy(*r[1:]) * sc for r in lab if r[0] == P]
        boxes = [(NAME[r[0]], to_xyxy(*r[1:]) * sc) for r in lab if r[0] in NAME and NAME[r[0]] in names]
        if not persons or not boxes:
            continue
        sc0 = make(stem, im, persons, boxes)
        full.append(sc0)
        for o in sorted({x for x in sc0["own"] if x is not None}):
            q = persons[o]
            for frac in fracs:
                yc = int(q[1] + frac * (q[3] - q[1]))
                if yc >= h - 2:
                    continue
                keep = [(n, b) for (n, b), ow in zip(boxes, sc0["own"]) if ow == o and yc > b[1] + 0.3 * (b[3] - b[1])]
                if not keep:
                    continue
                ps = [np.array([p[0], p[1], p[2], min(p[3], yc)]) for p in persons if p[1] < yc - 2]
                bs = [(n, np.array([b[0], b[1], b[2], min(b[3], yc)])) for n, b in boxes if b[1] < yc - 2]
                oi = [i for i, p in enumerate(ps) if abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) < 1e-6]
                if not oi:
                    continue
                cut[frac].append(make(stem, im[:yc].copy(), ps, bs, only_owner=oi[0]))
        if n_img % 100 == 0 or n_img == len(srcs):
            print(f"  cảnh {n_img}/{len(srcs)}", flush=True)
    print(f"val: {len(full)} ảnh; ca cắt:", {f: len(v) for f, v in cut.items()}, flush=True)

    # 2. Tham số: k_eye (kính val_new), edge_frac (người chạm đáy ppe4 val, cache), F2 = B2 (torso_strict.json)
    ratios = []
    for s in full:
        for n, d, o in zip(s["names"], s["dets"], s["own"]):
            if n != "goggles" or o is None:
                continue
            k = s["tracks"][o].extra.get("kps")
            if not k or k[1][2] < kc or k[2][2] < kc:
                continue
            ed = math.hypot(k[1][0] - k[2][0], k[1][1] - k[2][1])
            if ed >= 1:
                cx, cy = d.center
                ratios.append(math.hypot(cx - (k[1][0] + k[2][0]) / 2, cy - (k[1][1] + k[2][1]) / 2) / ed)
    k_eye = round(float(np.percentile(ratios, hi)), 3)
    cache = OUT / "preds.npz"
    preds = dict(np.load(cache, allow_pickle=True))["data"].item()
    dcfg = cfg["detector"]
    fr = []
    for f in sorted((DATASET / "labels" / "val").glob("*.txt")):
        pr = preds.get(f.stem)
        if pr is None:
            continue
        H, W = pr["shape"]
        touch = [to_xyxy(*r[1:]) * np.array([W, H, W, H]) for r in read_labels(f) if r[0] == P]
        touch = [q for q in touch if q[3] >= H - 1]
        m = (pr["cls"] == P) & (pr["conf"] >= dcfg["conf"]["person"])
        b, c = pr["xyxy"][m], pr["conf"][m]
        if not touch or not len(b):
            continue
        b = b[nms(torch.tensor(b, dtype=torch.float32), torch.tensor(c, dtype=torch.float32), dcfg["nms_iou"]).numpy()]
        iou = iou_matrix(np.array(touch), b)
        for i in range(len(touch)):
            j = int(np.argmax(iou[i]))
            if iou[i, j] >= cal["video"]["match_iou"]:
                fr.append(max(0.0, float(H - b[j][3])) / H)
    edge_frac = math.ceil(float(np.percentile(fr, hi)) * 1000) / 1000
    b2 = json.loads((OUT / "torso_strict.json").read_text(encoding="utf-8"))["tham_so_de_xuat"]
    f2 = {k: v for k, v in b2.items() if k != "edge_px"}
    f2["edge_frac"] = edge_frac
    params = dict(F1=dict(kp_conf=kc, k_eye=k_eye), F2=f2, F3=True)
    print("tham số:", params, f"(kính {len(ratios)}, người chạm đáy {len(fr)})", flush=True)

    base = copy.deepcopy(cfg)
    for k in ("eye_anchor", "gloves_region_fallback", "torso_strict", "torso_pose"):
        base["association"].pop(k, None)
    var = {}
    for key, ppe_name, setter in (("F1", "goggles", lambda c: c["association"].__setitem__("eye_anchor", params["F1"])),
                                  ("F2", "vest", lambda c: c["association"].__setitem__("torso_strict", params["F2"])),
                                  ("F3", "gloves", lambda c: c["association"].__setitem__("gloves_region_fallback", True))):
        c = copy.deepcopy(base)
        setter(c)
        var[key] = (ppe_name, Associator(c))
    A0 = Associator(base)

    def where(a, sc, tracks):
        res = a(tracks, sc["dets"], sc["shape"])
        return {id(x): tid for tid, items in res.owned.items() for ds in items.values() for x in ds}

    def score(a, scenes, ppe_name):
        x = dict(n=0, dung=0, sai_nguoi=0, khong_ghep=0, V3b_n=0, V3b_gan_nham=0)
        for sc in scenes:
            idx = [i for i, (n, o) in enumerate(zip(sc["names"], sc["own"])) if n == ppe_name and o is not None]
            if not idx:
                continue
            wh = where(a, sc, sc["tracks"])
            for i in idx:
                t = wh.get(id(sc["dets"][i]))
                o = sc["own"][i]
                x["n"] += 1
                x["dung" if t == o else ("khong_ghep" if t is None else "sai_nguoi")] += 1
                others = [tr for tr in sc["tracks"] if tr.track_id != o]
                if not others:
                    continue
                cx, cy = sc["dets"][i].center
                near = min(others, key=lambda tr: math.hypot((tr.xyxy[0] + tr.xyxy[2]) / 2 - cx, (tr.xyxy[1] + tr.xyxy[3]) / 2 - cy))
                b = sc["dets"][i].xyxy
                big = Track(near.track_id, np.array([min(near.xyxy[0], b[0]), min(near.xyxy[1], b[1]),
                                                     max(near.xyxy[2], b[2]), max(near.xyxy[3], b[3])]),
                            1.0, True, dict(near.extra))
                rest = [big if tr is near else tr for tr in others]
                x["V3b_n"] += 1
                x["V3b_gan_nham"] += int(where(a, sc, rest).get(id(sc["dets"][i])) == near.track_id)
        x["ti_le_dung"] = round(x["dung"] / max(x["n"], 1), 4)
        return x

    result, verdict = {}, {}
    for key, (ppe_name, a) in var.items():
        r = {"ban_chinh": {}, key: {}}
        for lvl, scenes in [("du", full)] + [(str(f), cut[f]) for f in fracs]:
            r["ban_chinh"][lvl] = score(A0, scenes, ppe_name)
            r[key][lvl] = score(a, scenes, ppe_name)
        b0, b1 = r["ban_chinh"], r[key]
        ck = dict(
            du_khong_giam=b1["du"]["dung"] >= b0["du"]["dung"],
            cat_tang_it_nhat_mot_muc=any(b1[str(f)]["dung"] > b0[str(f)]["dung"] for f in fracs),
            sai_nguoi_khong_tang=all(b1[l]["sai_nguoi"] <= b0[l]["sai_nguoi"] for l in b0),
            V3b_khong_tang=all(b1[l]["V3b_gan_nham"] <= b0[l]["V3b_gan_nham"] for l in b0))
        r["tieu_chi"], r["dat"] = ck, all(ck.values())
        result[key] = r
        verdict[key] = r["dat"]
        print(key, ppe_name, json.dumps({l: (b0[l]["dung"], b1[l]["dung"], b0[l]["n"], b0[l]["sai_nguoi"], b1[l]["sai_nguoi"],
                                             b0[l]["V3b_gan_nham"], b1[l]["V3b_gan_nham"]) for l in b0}), ck, flush=True)

    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    res = dict(ho_so=dict(thoi_diem=datetime.datetime.now().isoformat(timespec="seconds"), commit_nen=git("rev-parse", "HEAD"),
                          file_dang_sua=git("status", "--porcelain").splitlines(),
                          sha256=dict(preds_cache=sha(cache), pose_weights=sha(ROOT / cfg["pose"]["weights"]),
                                      torso_strict_json=sha(OUT / "torso_strict.json")),
                          ghi_chu="Val: ppe4 val (áo, găng), val_new (kính). Không dùng test, holdout, video."),
               thiet_lap=dict(coverage=cov, fracs=list(fracs), kp_conf=kc, inside_margin=margin),
               mau=dict(anh=len(full), cat={str(f): len(v) for f, v in cut.items()}, kinh_co_mat=len(ratios),
                        nguoi_cham_day=len(fr)),
               tham_so=params, ket_qua=result, dat=verdict)
    (OUT / "assoc_pose.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("kết luận:", verdict)
    print("Ghi", (OUT / "assoc_pose.json").relative_to(ROOT), "(chưa ghi cấu hình)")


def assoc_close_eval(cfg, edge_gate=False):
    """Bước F1 tầm gần (docs/experiments/2026-11-25_close_range_fixes.md): ủng theo mắt cá (ankle_anchor), găng theo cổ
    tay thang cẳng tay (wrist_anchor). Chỉ val: ủng val_new (6 lớp), găng ppe4 val. Người, PPE nhãn thật làm phát hiện;
    pose như pipeline. Tham số: k = phân vị cao (region_coverage) của khoảng cách tâm PPE - khớp đầu chi / độ dài chi
    (gối - mắt cá, khuỷu - cổ tay), lấy khớp gần hơn trong hai bên, ảnh đủ. Cảnh: ảnh đủ; ủng cắt mép trên giữ phần dưới
    60/45/30% người chủ; găng cắt mép dưới 55/65/75% (như bước F). Tiêu chí (a)-(d) trong kế hoạch.
    edge_gate (--assoc-close-edge, F1 lần 2): chỉ ủng, neo khi hộp người chạm mép trên (edge_px = keypoint_gate.helmet).
    Ghi outputs/results/pipeline_calib_val/assoc_close.json (lần 2: assoc_close_edge.json); không sửa cấu hình."""
    import copy
    import datetime
    import hashlib
    import math
    import subprocess

    import cv2

    from ppe import Det, Track
    from ppe.association import Associator
    from ppe.pose import PoseEstimator

    sys.stdout.reconfigure(encoding="utf-8")
    cal = cfg["calibration"]
    cov, margin = cal["region_coverage"], cal["inside_margin"]
    hi = (1 + cov) / 2 * 100
    kc = cfg["part_cls"]["kp_conf"]
    P = cfg["person_cls"]
    CLS = {n: cfg["ppe"][n]["cls"] for n in ("gloves", "boots")}
    NAME = {v: k for k, v in CLS.items()}
    LIMB = {"boots": ((15, 13), (16, 14)), "gloves": ((9, 7), (10, 8))}     # (đầu chi, khớp gần)
    CUTS = {"boots": ("tren", (0.60, 0.45, 0.30)), "gloves": ("duoi", (0.55, 0.65, 0.75))}
    pose = PoseEstimator(cfg, ROOT)

    def owner(c, persons):
        own = [i for i, q in enumerate(persons)
               if q[0] - margin * (q[2] - q[0]) <= c[0] <= q[2] + margin * (q[2] - q[0])
               and q[1] - margin * (q[3] - q[1]) <= c[1] <= q[3] + margin * (q[3] - q[1])]
        return own[0] if len(own) == 1 else None

    def make(stem, im, persons, boxes, only_owner=None):
        tracks = [Track(i, q.copy(), 1.0, True) for i, q in enumerate(persons)]
        if tracks:
            pose(im, tracks)
        dets = [Det(CLS[n], b.copy(), 1.0) for n, b in boxes]
        own = [owner(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), persons) for _, b in boxes]
        if only_owner is not None:
            own = [o if o == only_owner else None for o in own]
        return dict(stem=stem, tracks=tracks, dets=dets, names=[n for n, _ in boxes], own=own, shape=im.shape)

    def cut_scene(stem, im, persons, boxes, own0, o, ppe_name, mode, frac):
        """mode "duoi": giữ phần trên tới frac chiều cao người chủ; "tren": giữ phần dưới frac chiều cao người chủ."""
        h = im.shape[0]
        q = persons[o]
        if mode == "duoi":
            y0, y1 = 0, int(q[1] + frac * (q[3] - q[1]))
        else:
            y0, y1 = int(q[3] - frac * (q[3] - q[1])), h
        if y1 - y0 < 8 or (mode == "duoi" and y1 >= h - 2) or (mode == "tren" and y0 <= 2):
            return None
        vis = lambda b: (min(b[3], y1) - max(b[1], y0)) / max(b[3] - b[1], 1e-6)
        if not any(n == ppe_name and ow == o and vis(b) >= 0.7 for (n, b), ow in zip(boxes, own0)):
            return None
        sh = np.array([0, y0, 0, y0])
        clip = lambda b: np.array([b[0], max(b[1], y0), b[2], min(b[3], y1)]) - sh
        ps = [(i, clip(p)) for i, p in enumerate(persons) if min(p[3], y1) - max(p[1], y0) > 2]
        oi = [k for k, (i, _) in enumerate(ps) if i == o]
        if not oi:
            return None
        bs = [(n, clip(b)) for (n, b), ow in zip(boxes, own0) if vis(b) >= (0.7 if (n == ppe_name and ow == o) else 0.3)]
        return make(stem, im[y0:y1].copy(), [p for _, p in ps], bs, only_owner=oi[0])

    # 1. Cảnh: ủng val_new, găng ppe4 val
    srcs = [(f.stem, next(iter((DATASET / "images" / "val").glob(f.stem + ".*"))), read_labels(f), "gloves")
            for f in sorted((DATASET / "labels" / "val").glob("*.txt"))
            if any(r[0] == CLS["gloves"] for r in read_labels(f))]
    srcs += [(img.stem, img, read_labels(lab), "boots") for img, lab in val_new_items()
             if any(r[0] == CLS["boots"] for r in read_labels(lab))]
    full = {"boots": [], "gloves": []}
    cut = {n: {f: [] for f in CUTS[n][1]} for n in CUTS}
    for n_img, (stem, img, lab, ppe_name) in enumerate(srcs, 1):
        im = cv2.imread(str(img))
        h, w = im.shape[:2]
        sc = np.array([w, h, w, h])
        persons = [to_xyxy(*r[1:]) * sc for r in lab if r[0] == P]
        boxes = [(ppe_name, to_xyxy(*r[1:]) * sc) for r in lab if r[0] == CLS[ppe_name]]
        if not persons or not boxes:
            continue
        sc0 = make(stem, im, persons, boxes)
        full[ppe_name].append(sc0)
        mode, fracs = CUTS[ppe_name]
        for o in sorted({x for x in sc0["own"] if x is not None}):
            for frac in fracs:
                s = cut_scene(stem, im, persons, boxes, sc0["own"], o, ppe_name, mode, frac)
                if s is not None:
                    cut[ppe_name][frac].append(s)
        if n_img % 100 == 0 or n_img == len(srcs):
            print(f"  cảnh {n_img}/{len(srcs)}", flush=True)
    print("val:", {n: len(v) for n, v in full.items()}, "ca cắt:", {n: {f: len(x) for f, x in v.items()} for n, v in cut.items()},
          flush=True)

    # 2. Tham số trên ảnh đủ
    ratios = {"boots": [], "gloves": []}
    for n in ratios:
        for s in full[n]:
            for d, o in zip(s["dets"], s["own"]):
                k = s["tracks"][o].extra.get("kps") if o is not None else None
                if not k:
                    continue
                cx, cy = d.center
                rr = [math.hypot(cx - k[e][0], cy - k[e][1]) / math.hypot(k[e][0] - k[j][0], k[e][1] - k[j][1])
                      for e, j in LIMB[n] if k[e][2] >= kc and k[j][2] >= kc
                      and math.hypot(k[e][0] - k[j][0], k[e][1] - k[j][1]) >= 1]
                if rr:
                    ratios[n].append(min(rr))
    params = dict(ankle_anchor=dict(kp_conf=kc, k_ankle=round(float(np.percentile(ratios["boots"], hi)), 3)),
                  wrist_anchor=dict(kp_conf=kc, k_wrist=round(float(np.percentile(ratios["gloves"], hi)), 3)))
    if edge_gate:   # F1 lần 2 (kế hoạch): chỉ neo ủng khi hộp người chạm mép trên; găng bỏ
        params = dict(ankle_anchor=dict(params["ankle_anchor"], edge_px=cfg["compliance"]["keypoint_gate"]["helmet"]["edge_px"]))
    print("tham số:", params, {n: len(v) for n, v in ratios.items()}, flush=True)

    A0 = Associator(cfg)
    var = {}
    for key, ppe_name in [x for x in (("ankle_anchor", "boots"), ("wrist_anchor", "gloves")) if x[0] in params]:
        c = copy.deepcopy(cfg)
        c["association"][key] = params[key]
        var[key] = (ppe_name, Associator(c))

    def where(a, sc, tracks):
        res = a(tracks, sc["dets"], sc["shape"])
        return {id(x): tid for tid, items in res.owned.items() for ds in items.values() for x in ds}

    def score(a, scenes, ppe_name):
        x = dict(n=0, dung=0, sai_nguoi=0, khong_ghep=0, V3b_n=0, V3b_gan_nham=0)
        for sc in scenes:
            idx = [i for i, (n, o) in enumerate(zip(sc["names"], sc["own"])) if n == ppe_name and o is not None]
            if not idx:
                continue
            wh = where(a, sc, sc["tracks"])
            for i in idx:
                t = wh.get(id(sc["dets"][i]))
                o = sc["own"][i]
                x["n"] += 1
                x["dung" if t == o else ("khong_ghep" if t is None else "sai_nguoi")] += 1
                others = [tr for tr in sc["tracks"] if tr.track_id != o]
                if not others:
                    continue
                cx, cy = sc["dets"][i].center
                near_ = min(others, key=lambda tr: math.hypot((tr.xyxy[0] + tr.xyxy[2]) / 2 - cx, (tr.xyxy[1] + tr.xyxy[3]) / 2 - cy))
                b = sc["dets"][i].xyxy
                big = Track(near_.track_id, np.array([min(near_.xyxy[0], b[0]), min(near_.xyxy[1], b[1]),
                                                      max(near_.xyxy[2], b[2]), max(near_.xyxy[3], b[3])]),
                            1.0, True, dict(near_.extra))
                rest = [big if tr is near_ else tr for tr in others]
                x["V3b_n"] += 1
                x["V3b_gan_nham"] += int(where(a, sc, rest).get(id(sc["dets"][i])) == near_.track_id)
        x["ti_le_dung"] = round(x["dung"] / max(x["n"], 1), 4)
        return x

    result, verdict = {}, {}
    for key, (ppe_name, a) in var.items():
        r = {"ban_chinh": {}, key: {}}
        for lvl, scenes in [("du", full[ppe_name])] + [(str(f), cut[ppe_name][f]) for f in CUTS[ppe_name][1]]:
            r["ban_chinh"][lvl] = score(A0, scenes, ppe_name)
            r[key][lvl] = score(a, scenes, ppe_name)
        b0, b1 = r["ban_chinh"], r[key]
        cuts = [str(f) for f in CUTS[ppe_name][1]]
        ck = dict(
            a_du_khong_giam=b1["du"]["dung"] >= b0["du"]["dung"],
            b_cat_tang_it_nhat_mot_muc=any(b1[f]["dung"] > b0[f]["dung"] for f in cuts),
            c_sai_nguoi_khong_tang=all(b1[l]["sai_nguoi"] <= b0[l]["sai_nguoi"] for l in b0),
            d_V3b_khong_tang=all(b1[l]["V3b_gan_nham"] <= b0[l]["V3b_gan_nham"] for l in b0))
        r["kieu_cat"], r["tieu_chi"], r["dat"] = CUTS[ppe_name][0], ck, all(ck.values())
        result[key] = r
        verdict[key] = r["dat"]
        print(key, ppe_name, json.dumps({l: dict(dung=(b0[l]["dung"], b1[l]["dung"]), n=b0[l]["n"],
                                                 sai_nguoi=(b0[l]["sai_nguoi"], b1[l]["sai_nguoi"]),
                                                 V3b=(b0[l]["V3b_gan_nham"], b1[l]["V3b_gan_nham"])) for l in b0}), ck, flush=True)

    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    res = dict(ho_so=dict(thoi_diem=datetime.datetime.now().isoformat(timespec="seconds"), commit_nen=git("rev-parse", "HEAD"),
                          file_dang_sua=git("status", "--porcelain").splitlines(),
                          sha256=dict(pose_weights=sha(ROOT / cfg["pose"]["weights"])),
                          ghi_chu="Val: ppe4 val (găng), val_new (ủng). Không dùng test, holdout, video."),
               thiet_lap=dict(coverage=cov, cuts={n: dict(kieu=m, muc=list(f)) for n, (m, f) in CUTS.items()},
                              kp_conf=kc, inside_margin=margin),
               mau=dict(anh={n: len(v) for n, v in full.items()}, cat={n: {str(f): len(x) for f, x in v.items()} for n, v in cut.items()},
                        ti_le_tinh_k={n: len(v) for n, v in ratios.items()}),
               tham_so=params, ket_qua=result, dat=verdict)
    name = "assoc_close_edge.json" if edge_gate else "assoc_close.json"
    (OUT / name).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("kết luận:", verdict)
    print("Ghi", (OUT / name).relative_to(ROOT), "(chưa ghi cấu hình)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regions", action="store_true")
    ap.add_argument("--conf", action="store_true")
    ap.add_argument("--crop", action="store_true", help="so sánh dò PPE cả khung với dò trên ảnh cắt từng người")
    ap.add_argument("--pose", action="store_true", help="tâm găng nhãn thật có nằm trong elip cổ tay không, so với vùng tay")
    ap.add_argument("--torso", action="store_true", help="vùng thân theo khung xương cho áo (bước B)")
    ap.add_argument("--torso-strict", action="store_true", help="vùng thân theo khung xương bản chặt cho áo (bước B2)")
    ap.add_argument("--assoc-pose", action="store_true", help="bước F: vùng theo khung xương cho kính, áo, găng")
    ap.add_argument("--assoc-close", action="store_true", help="bước F1 tầm gần: ủng theo mắt cá, găng theo cổ tay")
    ap.add_argument("--assoc-close-edge", action="store_true", help="F1 lần 2: chỉ ủng, neo khi người chạm mép trên")
    ap.add_argument("--rerun", action="store_true", help="dự đoán lại thay vì dùng cache")
    args = ap.parse_args()
    if not (args.regions or args.conf or args.crop or args.pose or args.torso or args.torso_strict or args.assoc_pose
            or args.assoc_close or args.assoc_close_edge):
        ap.error("chọn --regions, --conf, --crop, --pose, --torso, --torso-strict và/hoặc --assoc-pose")
    cfg = load_config()
    if args.regions:
        regions(cfg)
    if args.conf:
        conf_nms(cfg, args.rerun)
    if args.crop:
        crop_eval(cfg, args.rerun)
    if args.pose:
        pose_eval(cfg)
    if args.torso:
        sys.stdout.reconfigure(encoding="utf-8")
        torso_eval(cfg)
    if args.torso_strict:
        torso_strict_eval(cfg)
    if args.assoc_pose:
        assoc_pose_eval(cfg)
    if args.assoc_close:
        assoc_close_eval(cfg)
    if args.assoc_close_edge:
        assoc_close_eval(cfg, edge_gate=True)


if __name__ == "__main__":
    main()
