"""Bước 1 (phụ): đóng gói nhãn 4 lớp của một bộ thành các phần nhỏ định dạng CVAT "YOLO 1.1".

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/01a_cvat_export.py --source chv                  # mỗi phần 100 ảnh
    python scripts/01a_cvat_export.py --source chv --part-size 50 --overwrite

Đọc data/ppe4/converted/<bộ>/index.csv và labels/ (kết quả của 01_convert_labels.py), ảnh gốc trong data/raw/.
Ghi vào data/ppe4/converted/<bộ>/cvat/:
    <bộ>_partXX_images.zip     ảnh của phần đó -> dùng khi tạo task trong CVAT
    <bộ>_partXX_yolo1.1.zip    obj.names, obj.data, train.txt, obj_train_data/*.txt -> Upload annotations, chọn "YOLO 1.1"
    parts.csv                  ảnh nào thuộc phần nào
Thứ tự lớp trong obj.names lấy từ configs/label_map.yaml (0 person, 1 helmet, 2 vest, 3 gloves).
"""

import argparse
import csv
import shutil
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "label_map.yaml"
CONVERTED = ROOT / "data" / "ppe4" / "converted"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, help="tên bộ trong data/ppe4/converted/")
    p.add_argument("--part-size", type=int, default=100, help="số ảnh mỗi phần (mỗi task CVAT)")
    p.add_argument("--overwrite", action="store_true", help="xóa thư mục cvat/ cũ của bộ đó rồi tạo lại")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    classes = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["classes"]
    names = [classes[k] for k in sorted(classes)]
    src_dir = CONVERTED / args.source
    out_dir = src_dir / "cvat"
    if out_dir.exists() and any(out_dir.iterdir()):
        if not args.overwrite:
            sys.exit(f"{out_dir} đã có dữ liệu; chạy lại với --overwrite để tạo lại.")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    with open(src_dir / "index.csv", encoding="utf-8") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: Path(r["image"]).name)

    obj_names = "\n".join(names) + "\n"
    obj_data = f"classes = {len(names)}\ntrain = data/train.txt\nnames = data/obj.names\nbackup = backup/\n"
    parts = []
    for i in range(0, len(rows), args.part_size):
        chunk = rows[i:i + args.part_size]
        part = f"{args.source}_part{i // args.part_size + 1:02d}"
        with zipfile.ZipFile(out_dir / f"{part}_images.zip", "w", zipfile.ZIP_STORED) as zi:
            for r in chunk:
                zi.write(ROOT / r["image"], Path(r["image"]).name)
        with zipfile.ZipFile(out_dir / f"{part}_yolo1.1.zip", "w", zipfile.ZIP_DEFLATED) as zl:
            zl.writestr("obj.names", obj_names)
            zl.writestr("obj.data", obj_data)
            zl.writestr("train.txt", "".join(f"data/obj_train_data/{Path(r['image']).name}\n" for r in chunk))
            for r in chunk:
                zl.write(ROOT / r["label"], f"obj_train_data/{Path(r['image']).stem}.txt")
        parts += [{"part": part, "image": Path(r["image"]).name, "orig_split": r["orig_split"]} for r in chunk]
        print(f"{part}: {len(chunk)} ảnh ({Path(chunk[0]['image']).name} .. {Path(chunk[-1]['image']).name})")

    with open(out_dir / "parts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["part", "image", "orig_split"])
        w.writeheader()
        w.writerows(parts)
    print(f"Đã ghi {len(rows)} ảnh thành {-(-len(rows) // args.part_size)} phần vào {out_dir.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
