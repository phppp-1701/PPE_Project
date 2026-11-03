"""Bước 2: phân tích lỗi của một lần huấn luyện trên val (docs/spec.md mục 3: xem lỗi bỏ sót, nhầm, hộp lệch).

Cách chạy (trên laptop, từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04b_analyze_val.py                                  # mặc định r1
    python scripts/04b_analyze_val.py --run outputs/train/yolo11s_ppe4_r2

Đọc <run>/weights/best.pt, <run>/args.yaml (imgsz), data/ppe4/dataset (tập val); tham số trong
configs/train.yaml mục `analyze`. Chỉ dùng val, không đụng test. Ghi vào outputs/results/<tên run>_val/:
    metrics.json       mAP/P/R từng lớp do Ultralytics tính lại trên laptop (so với run_info.json của Kaggle)
    gt_boxes.csv       mỗi hộp nhãn: ảnh, bộ, lớp, cạnh ngắn (px ở imgsz), tìm được không, conf, IoU
    false_pos.csv      mỗi dự đoán thừa: ảnh, bộ, lớp, conf, cạnh ngắn, IoU lớn nhất với hộp nhãn cùng lớp / khác lớp
    recall_by_size.csv tỉ lệ tìm được theo lớp × bộ × cỡ hộp
    missed_<lớp>.jpg, false_pos_<lớp>.jpg  ô cắt quanh mẫu bỏ sót / dự đoán thừa để xem bằng mắt
"""

import argparse
import collections
import csv
import json
import random
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "train.yaml"
DATASET = ROOT / "data" / "ppe4" / "dataset"
CLASSES = yaml.safe_load((ROOT / "configs" / "label_map.yaml").read_text(encoding="utf-8"))["classes"]
TILE = 220


def read_gt(label_path, w, h):
    """Hộp nhãn dạng (lớp, x1, y1, x2, y2) theo pixel ảnh gốc."""
    boxes = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c, cx, cy, bw, bh = line.split()
            cx, cy, bw, bh = float(cx) * w, float(cy) * h, float(bw) * w, float(bh) * h
            boxes.append((int(c), cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2))
    return boxes


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def size_bin(side, bins):
    return next((f"<{t}" for t in bins if side < t), f">={bins[-1]}")


def match(gt, pred, thr):
    """Ghép tham lam theo conf giảm dần, chỉ trong cùng lớp. Trả về (gt -> (pred, iou), danh sách pred thừa)."""
    gt_hit, fp = {}, []
    for pi in sorted(range(len(pred)), key=lambda i: -pred[i][5]):
        best, best_iou = None, thr
        for gi, g in enumerate(gt):
            if g[0] == pred[pi][0] and gi not in gt_hit:
                v = iou(g[1:], pred[pi][1:5])
                if v >= best_iou:
                    best, best_iou = gi, v
        if best is None:
            fp.append(pi)
        else:
            gt_hit[best] = (pi, best_iou)
    return gt_hit, fp


def tile(img_path, box, color, text, others):
    """Ô cắt quanh một hộp (rộng gấp 3 hộp, tối thiểu 96 px), vẽ hộp chính và các hộp nhãn khác cùng lớp."""
    with Image.open(img_path) as im:
        im = im.convert("RGB")
        x1, y1, x2, y2 = box
        side = max(x2 - x1, y2 - y1, 32) * 3
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        crop = (int(max(0, cx - side / 2)), int(max(0, cy - side / 2)),
                int(min(im.width, cx + side / 2)), int(min(im.height, cy + side / 2)))
        t = im.crop(crop)
    s = TILE / max(t.width, t.height)
    t = t.resize((max(1, int(t.width * s)), max(1, int(t.height * s))))
    d = ImageDraw.Draw(t)
    sh = lambda b: [(b[0] - crop[0]) * s, (b[1] - crop[1]) * s, (b[2] - crop[0]) * s, (b[3] - crop[1]) * s]
    for b in others:
        d.rectangle(sh(b), outline=(0, 200, 0), width=1)
    d.rectangle(sh(box), outline=color, width=2)
    out = Image.new("RGB", (TILE, TILE + 28), (30, 30, 30))
    out.paste(t, (0, 0))
    ImageDraw.Draw(out).text((3, TILE + 2), text, fill=(255, 255, 255))
    return out


def sheet(tiles, path, cols=6):
    if not tiles:
        return
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGB", (cols * TILE, rows * (TILE + 28)), (0, 0, 0))
    for i, t in enumerate(tiles):
        out.paste(t, ((i % cols) * TILE, (i // cols) * (TILE + 28)))
    out.save(path, quality=90)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="outputs/train/yolo11s_ppe4_r1", help="thư mục kết quả huấn luyện")
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    from ultralytics import YOLO

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["analyze"]
    run = ROOT / args.run
    imgsz = yaml.safe_load((run / "args.yaml").read_text(encoding="utf-8"))["imgsz"]
    out = ROOT / "outputs" / "results" / f"{run.name}_val"
    out.mkdir(parents=True, exist_ok=True)
    model = YOLO(run / "weights" / "best.pt")
    names = {int(k): v for k, v in model.names.items()}
    assert names == CLASSES, f"lớp của mô hình {names} khác label_map {CLASSES}"

    print(f"1/2 model.val trên val (imgsz {imgsz})", flush=True)
    m = model.val(data=str(DATASET / "data.yaml"), split="val", imgsz=imgsz, batch=args.batch,
                  project=str(out), name="ultralytics_val", exist_ok=True, plots=True)
    box = m.box
    metrics = {"all": dict(P=box.mp, R=box.mr, mAP50=box.map50, mAP50_95=box.map)}
    for i, c in enumerate(box.ap_class_index):
        p, r, ap50, ap_ = box.class_result(i)
        metrics[names[int(c)]] = dict(P=p, R=r, mAP50=ap50, mAP50_95=ap_)
    metrics = {k: {a: round(float(b), 4) for a, b in v.items()} for k, v in metrics.items()}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"2/2 dự đoán từng ảnh (conf {cfg['conf']}) và ghép với nhãn", flush=True)
    # Truyền thư mục (đọc lần lượt từng ảnh); truyền danh sách thì Ultralytics mở hết ảnh vào RAM.
    n_images = sum(1 for _ in (DATASET / "images" / "val").iterdir())
    gt_rows, fp_rows = [], []
    for i, res in enumerate(model.predict(str(DATASET / "images" / "val"), imgsz=imgsz, conf=cfg["conf"],
                                         batch=args.batch, stream=True, verbose=False), 1):
        img = Path(res.path)
        h, w = res.orig_shape
        scale = imgsz / max(w, h)
        source = img.name.split("__")[0]
        gt = read_gt(DATASET / "labels" / "val" / (img.stem + ".txt"), w, h)
        pred = [(int(c), *xyxy, float(s)) for c, xyxy, s in
                zip(res.boxes.cls.tolist(), res.boxes.xyxy.tolist(), res.boxes.conf.tolist())]
        hit, fp = match(gt, pred, cfg["match_iou"])
        for gi, g in enumerate(gt):
            side = min(g[3] - g[1], g[4] - g[2]) * scale
            pi, v = hit.get(gi, (None, 0.0))
            gt_rows.append(dict(file=img.name, source=source, cls=names[g[0]], x1=g[1], y1=g[2], x2=g[3], y2=g[4],
                                side_px=round(side, 1), found=int(pi is not None),
                                conf=round(pred[pi][5], 3) if pi is not None else "", iou=round(v, 3)))
        for pi in fp:
            p = pred[pi]
            same = max([iou(g[1:], p[1:5]) for g in gt if g[0] == p[0]], default=0.0)
            other = max([(iou(g[1:], p[1:5]), names[g[0]]) for g in gt if g[0] != p[0]], default=(0.0, ""))
            fp_rows.append(dict(file=img.name, source=source, cls=names[p[0]], x1=p[1], y1=p[2], x2=p[3], y2=p[4],
                                conf=round(p[5], 3), side_px=round(min(p[3] - p[1], p[4] - p[2]) * scale, 1),
                                iou_same_cls=round(same, 3), iou_other_cls=round(other[0], 3), other_cls=other[1]))
        if i % 200 == 0 or i == n_images:
            print(f"  {i}/{n_images}", flush=True)

    for name, rows in (("gt_boxes.csv", gt_rows), ("false_pos.csv", fp_rows)):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)

    # Tỉ lệ tìm được theo lớp × bộ × cỡ hộp.
    bins = cfg["size_bins_px"]
    order = [f"<{t}" for t in bins] + [f">={bins[-1]}"]
    stat = collections.defaultdict(lambda: [0, 0])
    for r in gt_rows:
        for src in (r["source"], "ALL"):
            for b in (size_bin(r["side_px"], bins), "all"):
                stat[(r["cls"], src, b)][0] += r["found"]
                stat[(r["cls"], src, b)][1] += 1
    with open(out / "recall_by_size.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["cls", "source", "size_bin", "found", "total", "recall"])
        for (c, src, b), (k, n) in sorted(stat.items()):
            wr.writerow([c, src, b, k, n, round(k / n, 3)])
    fp_count = collections.Counter((r["cls"], r["source"]) for r in fp_rows)

    print(f"\nmAP trên laptop: {json.dumps(metrics['all'])}")
    print(f"\nTỉ lệ tìm được ở conf {cfg['conf']}, IoU >= {cfg['match_iou']} (số tìm được/tổng):")
    sources = sorted({r["source"] for r in gt_rows}) + ["ALL"]
    for c in CLASSES.values():
        print(f"\n  {c}" + "".join(f"{b:>16}" for b in order + ["all"]) + f"{'dự đoán thừa':>16}")
        for src in sources:
            cells = ""
            for b in order + ["all"]:
                k, n = stat.get((c, src, b), (0, 0))
                cells += f"{(f'{k}/{n} ({k / n:.0%})' if n else '-'):>16}"
            fpn = sum(v for (fc, fs), v in fp_count.items() if fc == c and src in ("ALL", fs))
            print(f"  {src:<17}"[:19] + cells + f"{fpn:>16}")

    # Ô cắt để xem bằng mắt: đỏ = hộp nhãn bị bỏ sót, vàng = dự đoán thừa, xanh = các hộp nhãn cùng lớp khác.
    rng = random.Random(cfg["seed"])
    gt_by_file = collections.defaultdict(list)
    for r in gt_rows:
        gt_by_file[(r["file"], r["cls"])].append((r["x1"], r["y1"], r["x2"], r["y2"]))
    for c in cfg["sample_classes"]:
        for kind, rows, color in (("missed", [r for r in gt_rows if r["cls"] == c and not r["found"]], (255, 0, 0)),
                                  ("false_pos", [r for r in fp_rows if r["cls"] == c], (255, 220, 0))):
            pick = rng.sample(rows, min(cfg["n_samples"], len(rows)))
            tiles = []
            for r in pick:
                b = (r["x1"], r["y1"], r["x2"], r["y2"])
                text = f"{r['file'][:24]} {r['side_px']}px" + (f" c{r['conf']}" if kind == "false_pos" else "")
                others = [o for o in gt_by_file[(r["file"], c)] if o != b]
                tiles.append(tile(DATASET / "images" / "val" / r["file"], b, color, text, others))
            sheet(tiles, out / f"{kind}_{c}.jpg")
    print(f"\nĐã ghi {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
