"""Bước 3: chọn trên val ảnh các tham số của chuỗi xử lý (docs/spec.md mục 3, 5.2, 7.5). Không đụng test.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05a_calibrate_val.py --regions     # vùng cơ thể + max_distance từ nhãn val (không cần mô hình)
    python scripts/05a_calibrate_val.py --conf        # conf từng lớp + NMS IoU từ dự đoán của detector trên val
    python scripts/05a_calibrate_val.py --crop        # so sánh PPE dò cả khung / trên ảnh cắt từng người (cần conf, nms)
    python scripts/05a_calibrate_val.py --pose        # tâm găng nhãn thật trong elip cổ tay, so với vùng tay
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
OUT = ROOT / "outputs" / "results" / "pipeline_calib_val"


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
    for f in sorted((DATASET / "labels" / "val").glob("*.txt")):
        lab = read_labels(f)
        persons = [to_xyxy(*r[1:]) for r in lab if r[0] == cfg["person_cls"]]
        for r in lab:
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


def predict(cfg, rerun):
    """Dự đoán trên val với conf rất thấp và NMS IoU 0.95 (gần như không NMS), lưu cache."""
    cache = OUT / "preds.npz"
    if cache.exists() and not rerun:
        return dict(np.load(cache, allow_pickle=True))["data"].item()
    from ultralytics import YOLO

    d = cfg["detector"]
    model = YOLO(ROOT / d["weights"])
    data = {}
    n = sum(1 for _ in (DATASET / "images" / "val").iterdir())
    for i, r in enumerate(model.predict(str(DATASET / "images" / "val"), imgsz=d["imgsz"], conf=0.01, iou=0.95,
                                        max_det=1000, device=d["device"], stream=True, verbose=False), 1):
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
    gt = {}
    for stem, p in data.items():
        h, w = p["shape"]
        lab = read_labels(DATASET / "labels" / "val" / f"{stem}.txt")
        gt[stem] = [(r[0], to_xyxy(r[1] * w, r[2] * h, r[3] * w, r[4] * h)) for r in lab]

    rows, best = [], {}
    for nms_iou in cal["nms_iou_grid"]:
        scores = {c: [] for c in names}       # (conf, khớp?) của mọi dự đoán sau NMS
        n_gt = {c: 0 for c in names}
        for stem, p in data.items():
            for c in names:
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
    cache = OUT / "crop_preds.npz"
    if cache.exists() and not rerun:
        crop_preds, timing = np.load(cache, allow_pickle=True)["data"]
    else:
        model = YOLO(ROOT / d["weights"])
        crop_preds = {s: {} for s in cal["crop_imgsz_grid"]}
        timing = {s: [] for s in cal["crop_imgsz_grid"]}
        stems = sorted(full)
        for i, stem in enumerate(stems, 1):
            p = full[stem]
            m = p["cls"] == cfg["person_cls"]
            boxes, conf = p["xyxy"][m], p["conf"][m]
            persons = []
            if len(boxes):
                keep = nms(torch.tensor(boxes), torch.tensor(conf), nms_iou).numpy()
                persons = [b for b, s in zip(boxes[keep], conf[keep]) if s >= person_conf]
            img = cv2.imread(str(next((DATASET / "images" / "val").glob(stem + ".*"))))
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
            persons = crop_preds[s0][stem]["persons"]
            H, W = crop_preds[s0][stem]["shape"]
            lab = read_labels(DATASET / "labels" / "val" / f"{stem}.txt")
            for c in ppe_cls:
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regions", action="store_true")
    ap.add_argument("--conf", action="store_true")
    ap.add_argument("--crop", action="store_true", help="so sánh dò PPE cả khung với dò trên ảnh cắt từng người")
    ap.add_argument("--pose", action="store_true", help="tâm găng nhãn thật có nằm trong elip cổ tay không, so với vùng tay")
    ap.add_argument("--rerun", action="store_true", help="dự đoán lại thay vì dùng cache")
    args = ap.parse_args()
    if not (args.regions or args.conf or args.crop or args.pose):
        ap.error("chọn --regions, --conf, --crop và/hoặc --pose")
    cfg = load_config()
    if args.regions:
        regions(cfg)
    if args.conf:
        conf_nms(cfg, args.rerun)
    if args.crop:
        crop_eval(cfg, args.rerun)
    if args.pose:
        pose_eval(cfg)


if __name__ == "__main__":
    main()
