"""Kiểm tra đầu ra một lần train: best.pt có lưu, tải được, đúng 6 lớp, kích thước hợp lý. Không đánh giá điểm.

Cách chạy:
    python scripts/04f_check_run.py --run /kaggle/working/runs/yolo11s_ppe6_c2_smoke          # trên Kaggle, ghi smoke_check.json cạnh run
    python scripts/04f_check_run.py --run <thư mục đã tải về> --save                         # trên máy, ghi data/ppe6/variants/kaggle_smoke.json

Mốc kích thước ở configs/ppe6.yaml mục `kaggle`. --save dùng cho file tải từ Kaggle về, để checklist của 03n ghi nhận.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import check_weights  # noqa: E402


def folder_mb(path):
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file()) / 1e6


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["kaggle"]
    run = Path(args.run)
    found = list(run.rglob("best.pt"))
    if len(found) != 1:
        sys.exit(f"Tìm thấy {len(found)} best.pt trong {run}.")
    best = found[0]
    mb = best.stat().st_size / 1e6
    from ultralytics import YOLO

    names = YOLO(str(best)).names
    errors = check_weights(mb, names, cfg["min_best_mb"], cfg["max_best_mb"], cfg["class_names"])
    res = dict(best=str(best), best_mb=round(mb, 2), sha256=hashlib.sha256(best.read_bytes()).hexdigest(), names=[names[i] for i in sorted(names)], folder_mb=round(folder_mb(run), 1), errors=errors)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if errors:
        sys.exit("Đầu ra không đạt.")
    out = ROOT / "data" / "ppe6" / "variants" / "kaggle_smoke.json" if args.save else run / "smoke_check.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Đạt, đã ghi", out)


if __name__ == "__main__":
    main()
