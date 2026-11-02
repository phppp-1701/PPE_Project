"""Bước 2: huấn luyện YOLO11s trên bộ 4 lớp (docs/spec.md mục 3). Chạy trên Kaggle.

Cách chạy (trong notebook Kaggle, sau khi git clone repo và cài ultralytics==8.4.189):
    python scripts/04_train.py                          # tự tìm data.yaml trong /kaggle/input
    python scripts/04_train.py --data /đường/dẫn/data.yaml
    python scripts/04_train.py --resume /kaggle/input/<output lần trước>/.../weights/last.pt

Tham số trong configs/train.yaml. Ghi vào --out (mặc định /kaggle/working/runs/<run_name>):
    weights/best.pt, last.pt   trọng số (best chọn theo mAP@0.5:0.95 trên val)
    args.yaml, results.csv     tham số thật đã dùng, kết quả từng epoch (Ultralytics tự ghi)
    run_info.json              GPU, phiên bản, thời gian, P/R/mAP từng lớp của best.pt trên val
"""

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "train.yaml"


def find_data_yaml(base):
    """data.yaml của bộ 4 lớp đã chia (có images/train) trong thư mục dữ liệu Kaggle."""
    found = [p for p in Path(base).rglob("data.yaml") if (p.parent / "images" / "train").is_dir()]
    if len(found) != 1:
        sys.exit(f"Tìm thấy {len(found)} data.yaml có images/train trong {base}: {found}. Dùng --data.")
    return found[0]


def per_class(metrics, names):
    """P, R, mAP@0.5, mAP@0.5:0.95 từng lớp và trung bình, từ kết quả model.val()."""
    box = metrics.box
    rows = {"all": dict(P=box.mp, R=box.mr, mAP50=box.map50, mAP50_95=box.map)}
    for i, c in enumerate(box.ap_class_index):
        p, r, ap50, ap = box.class_result(i)
        rows[names[int(c)]] = dict(P=p, R=r, mAP50=ap50, mAP50_95=ap)
    return {k: {m: round(float(v), 4) for m, v in d.items()} for k, d in rows.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", help="đường dẫn data.yaml (mặc định: tự tìm trong /kaggle/input)")
    ap.add_argument("--out", default="/kaggle/working/runs", help="thư mục ghi kết quả")
    ap.add_argument("--resume", help="last.pt của lần chạy bị ngắt, để chạy tiếp")
    args = ap.parse_args()

    import torch
    import ultralytics
    from ultralytics import YOLO

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "không có GPU"
    print(f"ultralytics {ultralytics.__version__}, torch {torch.__version__}, GPU: {gpu}")

    start = time.time()
    if args.resume:
        model = YOLO(args.resume)
        model.train(resume=True)
        data = model.trainer.args.data
    else:
        data = str(Path(args.data) if args.data else find_data_yaml("/kaggle/input"))
        print(f"data: {data}")
        model = YOLO(cfg["model"])
        model.train(data=data, project=args.out, name=cfg["run_name"], exist_ok=False, **cfg["train"])
    hours = (time.time() - start) / 3600
    save_dir = Path(model.trainer.save_dir)

    # Đánh giá lại best.pt trên val để có số từng lớp (chỉ val; test để dành đến cuối).
    best = YOLO(save_dir / "weights" / "best.pt")
    metrics = best.val(data=data, split="val", imgsz=cfg["train"]["imgsz"], batch=16,
                       device=cfg["train"]["device"], project=str(save_dir), name="val_best")
    info = dict(
        run_name=cfg["run_name"], gpu=gpu, ultralytics=ultralytics.__version__, torch=torch.__version__,
        data=data, model=cfg["model"], config=cfg, resumed_from=args.resume, train_hours=round(hours, 2),
        weights=str(save_dir / "weights" / "best.pt"), val=per_class(metrics, best.names))
    (save_dir / "run_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(info["val"], indent=2))
    print(f"Xong: {save_dir}")


if __name__ == "__main__":
    main()
