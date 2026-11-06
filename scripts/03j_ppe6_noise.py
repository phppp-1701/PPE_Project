"""Thử nghiệm 6 lớp: đo nhiễu của giày SH17 chưa phân loại. Chỉ đọc, ghi vào outputs/results/ppe6_noise/ và data/ppe6/review/.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv, sau 03i):
    python scripts/03j_ppe6_noise.py

Đo: phân bố cạnh dài hộp giày quanh ngưỡng `review.min_side_px`, tác động nếu đổi ngưỡng; số ảnh train và hộp không nhãn sẽ bị học
như nền; so sánh che vùng và loại ảnh. Chọn mẫu phân tầng theo cỡ hộp và độ tối để người duyệt (P2).
Ghi noise.json, shoe_size_hist.png, data/ppe6/review/p2_shoe_sample.csv. Không tự chọn che vùng hay loại ảnh.
"""

import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "ppe6"
OUT = ROOT / "outputs" / "results" / "ppe6_noise"
OLD = ("person", "helmet", "vest", "gloves")


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8")))


def long_side(b, size, imgsz):
    w, h = size
    return max(float(b["w"]) * w, float(b["h"]) * h) * imgsz / max(w, h)


def image_size(path):
    with Image.open(path) as im:
        w, h = im.size
        if im.getexif().get(274, 1) in (5, 6, 7, 8):
            w, h = h, w
    return w, h


def chart(sides, thr, path):
    """Một chuỗi, một màu; đường ngưỡng ghi nhãn trực tiếp. Trục dưới cắt ở 96 px vì vùng cần xem là quanh ngưỡng."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    ax.hist(np.clip(sides, 0, 96), bins=np.arange(0, 100, 4), color="#3b6fb6", edgecolor="white", linewidth=1.5)
    ax.axvline(thr, color="#333333", linewidth=1.5, linestyle="--")
    ax.text(thr + 1.5, ax.get_ylim()[1] * 0.92, f"ngưỡng {thr} px", color="#333333", fontsize=9)
    ax.set_xlabel("Cạnh dài hộp giày ở đầu vào 960 (px); cột cuối gồm mọi hộp từ 96 px")
    ax.set_ylabel("Số hộp")
    ax.set_title(f"Cỡ hộp giày SH17 ({len(sides)} hộp)", loc="left", fontsize=11)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    rv = cfg["review"]
    OUT.mkdir(parents=True, exist_ok=True)
    stats = {r["image"]: r for r in rd(ROOT / "data" / "ppe4" / "stats.csv")}
    dec = {r["box_id"]: r for r in rd(BASE / "review" / "decisions_v2.csv")}
    train = {p.name for p in (BASE / "dataset" / "images" / "train").iterdir()}
    status = {r["file"]: r for r in rd(BASE / "dataset" / "eval_status.csv")}
    boxes = [b for b in rd(BASE / "review" / "boxes.csv") if b["source"] == "sh17" and b["target"] == "boots"]
    sizes = {}
    for b in boxes:
        if b["image"] not in sizes:
            sizes[b["image"]] = image_size(ROOT / b["image"])
    sides = np.array([long_side(b, sizes[b["image"]], rv["imgsz"]) for b in boxes])
    thr = rv["min_side_px"]
    chart(sides, thr, OUT / "shoe_size_hist.png")
    unset = np.array([dec[b["box_id"]]["note"] in ("not_safety", "too_small") for b in boxes])
    in_eval = np.array([stats[b["image"]]["file"] in status for b in boxes])
    impact = {}
    for t in rv["min_side_grid"]:
        impact[str(t)] = dict(boxes_below=int((sides < t).sum()), default_boxes_below=int(((sides < t) & unset).sum()),
                              safety_boxes_below=int(((sides < t) & ~unset).sum()), eval_boxes_below=int(((sides < t) & in_eval).sum()),
                              change_vs_current=int((sides < t).sum()) - int((sides < thr).sum()))

    # Hộp không nhãn sẽ thành nền ở train
    left = [b for b in boxes if stats[b["image"]]["file"] in train and dec[b["box_id"]]["note"] in ("not_safety", "too_small")]
    imgs = sorted({b["image"] for b in left})
    area = []
    for b in left:
        area.append(float(b["w"]) * float(b["h"]))
    lost = {c: sum(int(stats[i]["n_" + c]) for i in imgs) for c in OLD}
    total = {c: 0 for c in OLD}
    n_train = 0
    for r in stats.values():
        if r["file"] in train:
            n_train += 1
            for c in OLD:
                total[c] += int(r["n_" + c])
    goggles_lost = sum(1 for b in rd(BASE / "review" / "boxes.csv") if b["target"] == "goggles" and b["image"] in set(imgs) and dec[b["box_id"]]["label"] == "safety")
    boots_lost = sum(1 for b in boxes if b["image"] in set(imgs) and dec[b["box_id"]]["label"] == "safety")

    # Mẫu phân tầng: cỡ hộp x độ tối
    rng = random.Random(cfg["eval"]["seed"])
    by_img = defaultdict(list)
    for b in left:
        by_img[b["image"]].append(b)
    strata = defaultdict(list)
    for i, (image, group) in enumerate(sorted(by_img.items()), 1):
        with Image.open(ROOT / image) as raw:
            im = ImageOps.exif_transpose(raw).convert("L")
        w, h = im.size
        for b in group:
            cx, cy, bw, bh = (float(b[k]) for k in ("cx", "cy", "w", "h"))
            crop = np.asarray(im.crop((int((cx - bw / 2) * w), int((cy - bh / 2) * h), int((cx + bw / 2) * w) + 1, int((cy + bh / 2) * h) + 1)))
            side = long_side(b, (w, h), rv["imgsz"])
            size_bin = "nho" if side < 48 else "vua" if side < 96 else "lon"
            dark = "toi" if crop.size and float(np.median(crop)) < rv["dark_luma"] else "sang"
            strata[(size_bin, dark)].append(dict(box_id=b["box_id"], stratum=f"{size_bin}_{dark}", side_px=round(side, 1), image=b["image"]))
        if i % 200 == 0:
            print(f"  {i}/{len(by_img)} ảnh", flush=True)
    per = rv["p2_shoes"] // len(strata)
    sample = []
    for k in sorted(strata):
        v = sorted(strata[k], key=lambda x: x["box_id"])
        sample += rng.sample(v, min(per, len(v)))
    with (BASE / "review" / "p2_shoe_sample.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["box_id", "stratum", "side_px", "image"], lineterminator="\n")
        w.writeheader()
        w.writerows(sample)
    res = dict(n_boxes=len(boxes), threshold=thr, side_percentiles={p: round(float(np.percentile(sides, p)), 1) for p in (10, 25, 50, 75, 90)}, impact=impact,
               train_images=n_train, train_old_boxes=total, unlabeled_in_train=dict(images=len(imgs), boxes=len(left), by_note=dict(Counter(dec[b["box_id"]]["note"] for b in left)),
                                                                                  median_box_area_share=round(float(np.median(area)), 5)),
               if_drop_images=dict(images=len(imgs), old_boxes=lost, goggles_safety=goggles_lost, boots_safety=boots_lost),
               strata={f"{a}_{b}": len(v) for (a, b), v in sorted(strata.items())}, p2_sample=len(sample))
    (OUT / "noise.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
