"""So điểm một mô hình 4 lớp trên val gốc của ppe4 và val sạch theo cảnh. Chỉ dùng val, không chạy test.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04c_ppe4_val_clean.py --run yolo11s_ppe4_r2
    python scripts/04c_ppe4_val_clean.py --run yolo11s_ppe4_r3     # khi đã có outputs/train/yolo11s_ppe4_r3/weights/best.pt

Val sạch = ảnh val mà cảnh của nó không có ảnh train (data/ppe6/scene/scene_ids.csv). Đây là "sạch theo ngưỡng hiện tại":
ngưỡng gom cảnh còn bỏ sót, nên phần này chưa chắc hết rò rỉ.
Dự đoán lấy từ model.val (save_json), imgsz theo args.yaml; AP tính lại phải khớp số Ultralytics ghi ở ultralytics_map.json.
Khoảng tin cậy 95%: bootstrap theo cảnh, tham số ở configs/ppe6.yaml mục `clean_val`.
Ghi outputs/results/ppe4_val_clean/<run>/: preds.npz (cache), ultralytics_map.json, result.json.
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import ap_from_tp  # noqa: E402

DATA = ROOT / "data" / "ppe4" / "dataset"
CLASSES = ["person", "helmet", "vest", "gloves"]
IOUS = np.linspace(0.5, 0.95, 10)


def val_images():
    stats = [r for r in csv.DictReader((ROOT / "data" / "ppe4" / "stats.csv").open(encoding="utf-8"))]
    scene = {r["file"]: r["scene_id"] for r in csv.DictReader((ROOT / "data" / "ppe6" / "scene" / "scene_ids.csv").open(encoding="utf-8"))}
    train_scenes = {scene[r["file"]] for r in stats if r["split"] == "train"}
    val = sorted(r["file"] for r in stats if r["split"] == "val")
    return val, {f: scene[f] for f in val}, {f for f in val if scene[f] not in train_scenes}


def read_gt(file, w, h):
    path = DATA / "labels" / "val" / f"{Path(file).stem}.txt"
    rows = [list(map(float, x.split())) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return np.array([[c, (x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h] for c, x, y, bw, bh in rows]).reshape(-1, 5)


def iou_matrix(a, b):
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    inter = np.clip(rb - lt, 0, None).prod(2)
    area = lambda x: (x[:, 2] - x[:, 0]) * (x[:, 3] - x[:, 1])  # noqa: E731
    return inter / np.maximum(area(a)[:, None] + area(b)[None, :] - inter, 1e-9)


def match(gt, det):
    """tp[n_det, 10], chép logic match_predictions của Ultralytics: dự đoán xếp theo conf giảm dần,
    mỗi dự đoán giữ nhãn IoU cao nhất, mỗi nhãn giữ dự đoán có conf cao nhất. Trả về cùng thứ tự với det đã sắp."""
    tp = np.zeros((len(det), len(IOUS)), dtype=bool)
    if not len(gt) or not len(det):
        return tp
    iou = iou_matrix(gt[:, 1:], det[:, :4]) * (gt[:, :1] == det[None, :, 5])
    for k, t in enumerate(IOUS):
        m = np.array(np.nonzero(iou >= t)).T
        if len(m):
            if len(m) > 1:
                m = m[iou[m[:, 0], m[:, 1]].argsort()[::-1]]
                m = m[np.unique(m[:, 1], return_index=True)[1]]
                m = m[np.unique(m[:, 0], return_index=True)[1]]
            tp[m[:, 1], k] = True
    return tp


def image_size(path):
    with Image.open(path) as im:
        w, h = im.size
        if im.getexif().get(274, 1) in (5, 6, 7, 8):
            w, h = h, w
    return w, h


def predict(run, files, imgsz, out):
    """Dự đoán lấy từ chính model.val (save_json), nên cùng thiết lập với số Ultralytics đã báo."""
    cache = out / "preds.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        return {k: z[k] for k in z.files}
    if not (out / "val" / "predictions.json").exists():
        from ultralytics import YOLO

        model = YOLO(str(ROOT / "outputs" / "train" / run / "weights" / "best.pt"))
        m = model.val(data=str(DATA / "data.yaml"), split="val", imgsz=imgsz, batch=4, save_json=True, plots=False, project=str(out), name="val", exist_ok=True, device=0, verbose=False)
        (out / "ultralytics_map.json").write_text(json.dumps(dict(map50=float(m.box.map50), map5095=float(m.box.map), per_class=[float(x) for x in m.box.ap50])), encoding="utf-8")
    det = defaultdict(list)
    rows = json.loads((out / "val" / "predictions.json").read_text(encoding="utf-8"))
    base = min(r["category_id"] for r in rows)
    for r in rows:
        x, y, w, h = r["bbox"]
        det[str(r["image_id"])].append([x, y, x + w, y + h, r["score"], r["category_id"] - base])
    img, conf, cls, tps, gtimg, gtcls = [], [], [], [], [], []
    for i, f in enumerate(files):
        d = np.array(det.get(Path(f).stem, []), dtype=np.float64).reshape(-1, 6)
        d = d[np.argsort(-d[:, 4], kind="stable")]
        w, h = image_size(DATA / "images" / "val" / f)
        gt = read_gt(f, w, h)
        img += [i] * len(d)
        conf += d[:, 4].tolist()
        cls += d[:, 5].astype(int).tolist()
        tps.append(match(gt, d))
        gtimg += [i] * len(gt)
        gtcls += gt[:, 0].astype(int).tolist()
    out_ = dict(img=np.array(img), conf=np.array(conf, dtype=np.float32), cls=np.array(cls), tp=np.concatenate(tps), gtimg=np.array(gtimg), gtcls=np.array(gtcls))
    np.savez_compressed(cache, **out_)
    return out_


def scores(p, weight):
    """AP từng lớp khi mỗi ảnh có trọng số (số lần xuất hiện trong mẫu bootstrap)."""
    w = weight[p["img"]]
    g = weight[p["gtimg"]]
    out = {}
    for c, name in enumerate(CLASSES):
        m = (p["cls"] == c) & (w > 0)
        n = g[p["gtcls"] == c].sum()
        out[name] = ap_from_tp(p["tp"][m], p["conf"][m], n, w[m])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["clean_val"]
    run_dir = ROOT / "outputs" / "train" / args.run
    if not (run_dir / "weights" / "best.pt").exists():
        sys.exit(f"Chưa có {run_dir / 'weights' / 'best.pt'}")
    imgsz = yaml.safe_load((run_dir / "args.yaml").read_text(encoding="utf-8"))["imgsz"]
    files, scene, clean = val_images()
    print(f"val {len(files)} ảnh, sạch theo ngưỡng hiện tại {len(clean)} ảnh, imgsz {imgsz}")
    out = ROOT / "outputs" / "results" / "ppe4_val_clean" / args.run
    out.mkdir(parents=True, exist_ok=True)
    p = predict(args.run, files, imgsz, out)
    is_clean = np.array([f in clean for f in files], dtype=np.float64)
    ones = np.ones(len(files))
    full, sub = scores(p, ones), scores(p, is_clean)
    ref = json.loads((out / "ultralytics_map.json").read_text(encoding="utf-8"))
    gap = max(abs(full[c][0] - ref["per_class"][i]) for i, c in enumerate(CLASSES))
    print(f"Lệch lớn nhất so với model.val: {gap:.4f}")
    if gap > cfg["max_gap"]:
        sys.exit("AP tính lại không khớp model.val, không báo số.")
    groups = defaultdict(list)
    for i, f in enumerate(files):
        groups[scene[f]].append(i)
    keys = sorted(groups)
    rng = np.random.default_rng(cfg["seed"])
    boot = defaultdict(list)
    for _ in range(cfg["n_boot"]):
        w = np.zeros(len(files))
        for k in rng.integers(0, len(keys), len(keys)):
            w[groups[keys[k]]] += 1
        a, b = scores(p, w), scores(p, w * is_clean)
        for c in CLASSES:
            boot[c + "_full"].append(a[c][0])
            boot[c + "_clean"].append(b[c][0])
            boot[c + "_diff"].append(b[c][0] - a[c][0])
        boot["mean_full"].append(np.mean([a[c][0] for c in CLASSES]))
        boot["mean_clean"].append(np.mean([b[c][0] for c in CLASSES]))
        boot["mean_diff"].append(boot["mean_clean"][-1] - boot["mean_full"][-1])
    ci = lambda k: [round(float(x), 4) for x in np.percentile(boot[k], [2.5, 97.5])]  # noqa: E731
    res = dict(run=args.run, imgsz=imgsz, images=len(files), clean_images=len(clean), scenes=len(keys), n_boot=cfg["n_boot"],
               note="sạch theo ngưỡng hiện tại; số rò rỉ đo được là mức thấp", classes={})
    for i, c in enumerate(CLASSES):
        res["classes"][c] = dict(gt_full=int((p["gtcls"] == i).sum()), gt_clean=int(((p["gtcls"] == i) & (is_clean[p["gtimg"]] > 0)).sum()),
                                 map50_full=round(full[c][0], 4), map50_clean=round(sub[c][0], 4), map5095_full=round(full[c][1], 4), map5095_clean=round(sub[c][1], 4),
                                 diff=round(sub[c][0] - full[c][0], 4), ci_full=ci(c + "_full"), ci_clean=ci(c + "_clean"), ci_diff=ci(c + "_diff"))
    res["ultralytics"] = json.loads((out / "ultralytics_map.json").read_text(encoding="utf-8"))
    res["mean"] = dict(map50_full=round(float(np.mean([full[c][0] for c in CLASSES])), 4), map50_clean=round(float(np.mean([sub[c][0] for c in CLASSES])), 4),
                       map5095_full=round(float(np.mean([full[c][1] for c in CLASSES])), 4), map5095_clean=round(float(np.mean([sub[c][1] for c in CLASSES])), 4),
                       ci_full=ci("mean_full"), ci_clean=ci("mean_clean"), ci_diff=ci("mean_diff"))
    (out / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
