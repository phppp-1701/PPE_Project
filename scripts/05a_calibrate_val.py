"""Bước 3: chọn trên val ảnh các tham số của chuỗi xử lý (docs/spec.md mục 3, 5.2, 7.5). Không đụng test.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05a_calibrate_val.py --regions     # vùng cơ thể + max_distance từ nhãn val (không cần mô hình)
    python scripts/05a_calibrate_val.py --conf        # conf từng lớp + NMS IoU từ dự đoán của detector trên val
    (dự đoán được lưu cache; --rerun để dự đoán lại)

Tham số đầu vào: configs/pipeline.yaml (detector, ppe, calibration). Chỉ in và ghi đề xuất vào
outputs/results/pipeline_calib_val/; người chép giá trị đã duyệt vào configs/pipeline.yaml kèm ngày.
    regions.json   vùng (x0, x1, y0, y1) và max_distance từng PPE, số PPE dùng để tính
    preds.npz      cache dự đoán (conf rất thấp, gần như không NMS)
    conf_f1.csv    P/R/F1 theo NMS IoU × lớp × conf
    conf.json      đề xuất conf từng lớp và nms_iou
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regions", action="store_true")
    ap.add_argument("--conf", action="store_true")
    ap.add_argument("--rerun", action="store_true", help="dự đoán lại thay vì dùng cache")
    args = ap.parse_args()
    if not (args.regions or args.conf):
        ap.error("chọn --regions và/hoặc --conf")
    cfg = load_config()
    if args.regions:
        regions(cfg)
    if args.conf:
        conf_nms(cfg, args.rerun)


if __name__ == "__main__":
    main()
