"""Thử nghiệm 6 lớp: train bộ phân loại ảnh cắt bộ phận (YOLO11n-cls) trên Kaggle.

Cách chạy trên Kaggle (sau khi git clone nhánh exp/ppe6):
    python scripts/04g_train_parts_cls.py --data <thư mục parts có train/, val/> --out /kaggle/working/runs

Dữ liệu do 03y_ppe6_part_crops.py tạo. Tham số ở configs/ppe6.yaml mục `parts.train`.
Ghi <out>/<run_name>/weights/best.pt và run_info.json (độ chính xác top-1 trên val, từng lớp, ma trận nhầm lẫn).
"""

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="/kaggle/working/runs")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    from ultralytics import YOLO

    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["parts"]["train"]
    # Kaggle có thể đặt dataset ở đường dẫn khác tên đã đặt: tìm thư mục có train/glove và val/ dưới --data, rồi dưới /kaggle/input.
    found = []
    for base in (Path(args.data), Path("/kaggle/input")):
        if base.exists():
            found = sorted({q.parent.parent for q in base.rglob("glove") if q.is_dir() and q.parent.name == "train" and (q.parent.parent / "val").is_dir()})
        if found:
            break
    if len(found) != 1:
        for base in (Path(args.data), Path("/kaggle/input")):
            if base.exists():
                print("Nội dung", base, [str(x) for x in list(base.rglob("*"))[:20]])
        sys.exit(f"Tìm thấy {len(found)} thư mục có train/glove và val/: {found}")
    data = found[0]
    model = YOLO(cfg["model"])
    model.train(data=str(data), project=args.out, name=cfg["run_name"], exist_ok=False, **cfg["args"])
    save = Path(model.trainer.save_dir)
    best = YOLO(save / "weights" / "best.pt")
    m = best.val(data=str(data), split="val", imgsz=cfg["args"]["imgsz"], project=str(save), name="val_best")
    names = best.names
    cm = m.confusion_matrix.matrix.tolist()   # hàng: dự đoán, cột: thật
    per = {names[i]: round(cm[i][i] / max(sum(row[i] for row in cm), 1), 4) for i in names}
    info = dict(run_name=cfg["run_name"], data=str(data), top1=round(float(m.top1), 4), recall_per_class=per,
                confusion=dict(names=[names[i] for i in names], matrix=cm), args=cfg["args"])
    (save / "run_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: info[k] for k in ("top1", "recall_per_class")}, ensure_ascii=False, indent=2))
    print("Xong:", save)


if __name__ == "__main__":
    main()
