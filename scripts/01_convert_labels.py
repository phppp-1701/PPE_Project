"""Bước 1: đổi nhãn từng bộ dữ liệu gốc về 4 lớp chung (0 person, 1 helmet, 2 vest, 3 gloves).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/01_convert_labels.py                        # tất cả các bộ trong configs/label_map.yaml
    python scripts/01_convert_labels.py --sources sh17 chv     # chỉ một số bộ
    python scripts/01_convert_labels.py --overwrite            # ghi đè kết quả cũ trong data/ppe4/converted/

Chỉ ĐỌC data/raw/. Với mỗi bộ, ghi vào data/ppe4/converted/<bộ>/:
    labels/<tên ảnh>.txt   nhãn YOLO 4 lớp (file rỗng = ảnh không còn hộp nào sau khi lọc)
    index.csv              mỗi ảnh một dòng: đường dẫn ảnh gốc, file nhãn mới, tập gốc, số hộp từng lớp
Ảnh KHÔNG được chép ở bước này; bước 03 (chia tập) mới chép ảnh vào data/ppe4/images/.
Thống kê in ra màn hình và lưu vào data/ppe4/converted/summary.json.
"""

import argparse
import collections
import csv
import json
import shutil
import sys
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "label_map.yaml"
OUT_ROOT = ROOT / "data" / "ppe4" / "converted"
RAW_ROOT = ROOT / "data" / "raw"
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def read_split_list(path):
    """File danh sách ảnh của một tập -> tập tên ảnh (bỏ thư mục, giữ đuôi)."""
    return {Path(l.strip()).name for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}


def list_images(folder):
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG_EXT)


def parse_yolo(label_path, stats):
    """Đọc nhãn YOLO -> danh sách (lớp gốc, cx, cy, w, h); dòng lỗi được đếm và bỏ."""
    boxes = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        f = line.split()
        if not f:
            continue
        try:
            c = int(f[0])
            x, y, w, h = map(float, f[1:5])
            ok = len(f) == 5 and 0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1
        except (ValueError, IndexError):
            ok = False
        if not ok:
            stats["invalid_lines"] += 1
            continue
        boxes.append((c, x, y, w, h))
    return boxes


def pixel_to_yolo(x1, y1, x2, y2, img_w, img_h, stats):
    """Hộp pixel (góc trên trái, góc dưới phải) -> YOLO chuẩn hóa; cắt về trong ảnh."""
    cx1, cy1 = max(0, min(x1, img_w)), max(0, min(y1, img_h))
    cx2, cy2 = max(0, min(x2, img_w)), max(0, min(y2, img_h))
    if (cx1, cy1, cx2, cy2) != (x1, y1, x2, y2):
        stats["clipped_boxes"] += 1
    if cx2 <= cx1 or cy2 <= cy1:
        stats["invalid_lines"] += 1
        return None
    return ((cx1 + cx2) / 2 / img_w, (cy1 + cy2) / 2 / img_h, (cx2 - cx1) / img_w, (cy2 - cy1) / img_h)


def collect_yolo(cfg, root, stats):
    """Bộ có nhãn YOLO: trả về danh sách (ảnh, tập gốc, các hộp gốc)."""
    items = []
    if "splits" in cfg:  # thư mục riêng cho từng tập (Construction-PPE)
        groups = [(s, root / cfg["images"].format(split=s), root / cfg["labels"].format(split=s)) for s in cfg["splits"]]
    else:  # một thư mục ảnh chung + file danh sách từng tập (SH17, CHV)
        groups = [(None, root / cfg["images"], root / cfg["labels"])]
        split_of = {}
        for s, f in cfg["split_lists"].items():
            for name in read_split_list(root / f):
                split_of[name] = s

    for split, img_dir, lab_dir in groups:
        images = list_images(img_dir)
        image_stems = {p.stem for p in images}
        stats["label_files_without_image"] += sum(1 for p in lab_dir.glob("*.txt") if p.stem not in image_stems)
        for img in images:
            lab = lab_dir / (img.stem + ".txt")
            if not lab.exists():
                stats["images_without_label"] += 1
                continue
            s = split if split else split_of.get(img.name, "")
            if not s:
                stats["images_not_in_split_list"] += 1
            items.append((img, s, parse_yolo(lab, stats)))
    return items


def collect_pictor(cfg, root, stats):
    """Pictor-PPE: dòng `ảnh<TAB>x1,y1,x2,y2,lớp...` (pixel) -> hộp YOLO chuẩn hóa."""
    img_dir = root / cfg["images"]
    items, labelled = [], set()
    for split, f in cfg["label_files"].items():
        for line in (root / f).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            name, *raw = line.split("\t")
            img = img_dir / name
            if not img.exists():
                stats["labels_without_image"] += 1
                continue
            labelled.add(name)
            with Image.open(img) as im:
                img_w, img_h = im.size
                if im.getexif().get(0x0112, 1) != 1:
                    stats["exif_rotated_images"] += 1
            boxes = []
            for b in raw:
                try:
                    x1, y1, x2, y2, c = (int(v) for v in b.split(","))
                except ValueError:
                    stats["invalid_lines"] += 1
                    continue
                yb = pixel_to_yolo(x1, y1, x2, y2, img_w, img_h, stats)
                if yb:
                    boxes.append((c, *yb))
            items.append((img, split, boxes))
    stats["images_without_label"] += sum(1 for p in list_images(img_dir) if p.name not in labelled)
    return items


def convert_source(name, cfg, classes, overwrite):
    root = ROOT / cfg["root"]
    out_dir = OUT_ROOT / name
    assert RAW_ROOT not in out_dir.parents, "không bao giờ ghi vào data/raw"
    if out_dir.exists() and any(out_dir.iterdir()):
        if not overwrite:
            sys.exit(f"{out_dir} đã có dữ liệu; chạy lại với --overwrite để ghi đè.")
        shutil.rmtree(out_dir)
    (out_dir / "labels").mkdir(parents=True)

    stats = collections.Counter()
    collect = collect_pictor if cfg["format"] == "pictor" else collect_yolo
    items = collect(cfg, root, stats)
    mapping = {int(k): int(v) for k, v in cfg["map"].items()}

    boxes_per_class = collections.Counter()
    images_per_class = collections.Counter()
    dropped_per_orig = collections.Counter()
    per_split = collections.Counter()
    seen_stems = set()
    rows = []
    for img, split, boxes in items:
        if img.stem in seen_stems:  # hai ảnh khác đuôi cùng tên -> nhãn sẽ ghi đè nhau
            sys.exit(f"Trùng tên ảnh trong {name}: {img.stem}")
        seen_stems.add(img.stem)
        lines, counts = [], collections.Counter()
        for c, x, y, w, h in boxes:
            if c not in mapping:
                dropped_per_orig[c] += 1
                continue
            new_c = mapping[c]
            counts[new_c] += 1
            lines.append(f"{new_c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
        label_out = out_dir / "labels" / (img.stem + ".txt")
        label_out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        boxes_per_class.update(counts)
        images_per_class.update(counts.keys())
        per_split[split] += 1
        if not lines:
            stats["images_with_no_kept_box"] += 1
        rows.append({
            "source": name,
            "image": img.relative_to(ROOT).as_posix(),
            "label": label_out.relative_to(ROOT).as_posix(),
            "orig_split": split,
            **{f"n_{classes[k]}": counts[k] for k in sorted(classes)},
            "gloves_labeled": int(cfg["gloves_labeled"]),
        })

    with open(out_dir / "index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    return {
        "images": len(rows),
        "orig_split": dict(sorted(per_split.items())),
        "boxes": {classes[k]: boxes_per_class[k] for k in sorted(classes)},
        "images_with_class": {classes[k]: images_per_class[k] for k in sorted(classes)},
        "gloves_labeled": cfg["gloves_labeled"],
        "dropped_boxes_by_orig_class": dict(sorted(dropped_per_orig.items())),
        "checks": dict(sorted(stats.items())),
    }


def print_table(summary, classes):
    names = [classes[k] for k in sorted(classes)]
    head = f"{'Bộ':18s}{'Ảnh':>8s}" + "".join(f"{n + ' (hộp/ảnh)':>22s}" for n in names)
    print("\n" + head)
    print("-" * len(head))
    total_img, total = 0, collections.Counter()
    for src, s in summary.items():
        cells = []
        for n in names:
            if n == "gloves" and not s["gloves_labeled"]:
                cells.append(f"{'chưa gán':>22s}")
            else:
                cells.append(f"{s['boxes'][n]:>12,d} / {s['images_with_class'][n]:<7,d}")
            total[n] += s["boxes"][n]
            total["img_" + n] += s["images_with_class"][n]
        total_img += s["images"]
        print(f"{src:18s}{s['images']:>8,d}" + "".join(cells))
    print("-" * len(head))
    print(f"{'Tổng':18s}{total_img:>8,d}" + "".join(f"{total[n]:>12,d} / {total['img_' + n]:<7,d}" for n in names))
    for src, s in summary.items():
        print(f"\n[{src}] tập gốc: {s['orig_split']}; hộp bị bỏ theo lớp gốc: {s['dropped_boxes_by_orig_class']}; kiểm tra: {s['checks']}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sources", nargs="*", help="tên bộ trong configs/label_map.yaml (mặc định: tất cả)")
    p.add_argument("--overwrite", action="store_true", help="xóa kết quả cũ của bộ đó trong data/ppe4/converted/ rồi ghi lại")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows mặc định cp1252, không in được tiếng Việt

    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    classes = {int(k): v for k, v in config["classes"].items()}
    sources = args.sources or list(config["sources"])

    summary = {}
    for name in sources:
        print(f"[convert] {name} ...", flush=True)
        summary[name] = convert_source(name, config["sources"][name], classes, args.overwrite)

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    out = OUT_ROOT / "summary.json"
    old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    old.update(summary)
    out.write_text(json.dumps(old, indent=2, ensure_ascii=False), encoding="utf-8")
    print_table(summary, classes)
    print(f"\nĐã lưu {out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
