"""Thống kê dữ liệu C5 so với C4 (trước khi train C5), để hiểu dữ liệu và ghi báo cáo. Chỉ đọc, không sửa dữ liệu.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04k_c5_data_stats.py

Ghi outputs/results/c5_eval/data_stats.json và in bảng:
- train C4 (dataset_c2 + c4_extra) và C5 (c5/dataset_c5 + c5/c5_extra): số ảnh, số hộp từng lớp theo nguồn, số ảnh có lớp,
  số ảnh có vùng che, bản lặp (oversample);
- cỡ hộp (cạnh ngắn, px) sau khi đưa ảnh về imgsz 960 và 1280 (letterbox theo cạnh dài): tỉ lệ < 16, 16-32, 32-64, >= 64;
- val, test đã sửa (c5/eval): số hộp, số vùng ignore từng lớp theo tập con (ppe4, lớp mới, CHVG).
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
P6 = ROOT / "data" / "ppe6"
NAMES = ["person", "helmet", "vest", "gloves", "goggles", "boots"]
BINS = [16, 32, 64]


def src_of(name):
    s = name.split("__")[0]
    return {"cppe2": "cppe_moi", "construction_ppe": "cppe_cu", "crop": "cat_nguoi", "shrink": "thu_nho"}.get(s, s)


def rows(path):
    out = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            t = line.split()
            if t:
                out.append((int(t[0]), *map(float, t[1:5])))
    return out


def size_bin(px):
    for i, b in enumerate(BINS):
        if px < b:
            return i
    return len(BINS)


def train_stats(main, extra):
    """main, extra: thư mục có images/train, labels/train; extra có oversample.txt."""
    boxes, imgs_with, size = Counter(), Counter(), {960: defaultdict(Counter), 1280: defaultdict(Counter)}
    n_img = Counter()
    for base in (main, extra):
        for lab in sorted((base / "labels" / "train").glob("*.txt")):
            img = next((base / "images" / "train").glob(lab.stem + ".*"), None)
            if img is None:
                continue
            s = src_of(lab.stem)
            n_img[s] += 1
            with Image.open(img) as im:
                w, h = im.size
            seen = set()
            for c, cx, cy, bw, bh in rows(lab):
                boxes[(NAMES[c], s)] += 1
                seen.add(c)
                short = min(bw * w, bh * h)
                for z in (960, 1280):
                    size[z][NAMES[c]][size_bin(short * z / max(w, h))] += 1
            for c in seen:
                imgs_with[NAMES[c]] += 1
    rep = (extra / "oversample.txt").read_text(encoding="utf-8").split()
    return dict(images=dict(n_img), images_total=sum(n_img.values()), oversample=len(rep),
                boxes={f"{k[0]}|{k[1]}": v for k, v in sorted(boxes.items())},
                boxes_total={n: sum(v for k, v in boxes.items() if k[0] == n) for n in NAMES},
                images_with=dict(imgs_with),
                size_share={str(z): {n: [round(size[z][n][i] / max(sum(size[z][n].values()), 1), 3) for i in range(len(BINS) + 1)]
                                     for n in NAMES} for z in size})


def eval_stats():
    ev = P6 / "c5" / "eval"
    files = json.loads((ev / "files.json").read_text(encoding="utf-8"))
    ppe4 = {s: {p.name for p in (ROOT / "data" / "ppe4" / "dataset" / "images" / s).iterdir()} for s in ("val", "test")}
    ign = defaultdict(Counter)
    for r in csv.DictReader(open(ev / "ignore.csv", encoding="utf-8")):
        ign[(r["split"], r["file"])][int(r["cls"])] += 1
    out = {}
    for sp in ("val", "test"):
        subs = {"ppe4": (set(files[sp]["all"]) & ppe4[sp], [0, 1, 2, 3]), "lop_moi": (set(files[sp]["new_class_files"]), [4, 5]),
                "chvg": (set(files[sp].get("chvg_files", [])), [4])}
        for name, (fs, cls) in subs.items():
            gt, ig = Counter(), Counter()
            for f in fs:
                for c, *_ in rows(ev / sp / "labels" / (Path(f).stem + ".txt")):
                    gt[c] += 1
                ig.update(ign.get((sp, f), Counter()))
            out[f"{sp}|{name}"] = dict(images=len(fs), **{NAMES[c]: dict(gt=gt[c], ignore=ig[c]) for c in cls})
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    res = dict(c4=train_stats(P6 / "dataset_c2", P6 / "c4_extra"), c5=train_stats(P6 / "c5" / "dataset_c5", P6 / "c5" / "c5_extra"),
               eval=eval_stats(), size_bins_px=BINS, note="nhãn C5: nhãn máy có kiểm định mẫu của người (kế hoạch 2026-11-16_c5_detector_plan)")
    out = ROOT / "outputs" / "results" / "c5_eval" / "data_stats.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for v in ("c4", "c5"):
        t = res[v]
        print(f"[{v}] ảnh {t['images_total']} {t['images']} lặp {t['oversample']}")
        print("  hộp", t["boxes_total"])
        print("  ảnh có lớp", t["images_with"])
    for z in ("960", "1280"):
        print(f"[C5 cỡ hộp @ {z}] <16 / 16-32 / 32-64 / >=64:", {n: res["c5"]["size_share"][z][n] for n in NAMES})
    for k, v in res["eval"].items():
        print(k, v)


if __name__ == "__main__":
    main()
