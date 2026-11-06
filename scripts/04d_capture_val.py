"""Chạy model.val và lưu nguyên dự đoán, nhãn, tp của Ultralytics cho từng ảnh. Chỉ dùng val, không chạy test.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04d_capture_val.py --weights outputs/train/yolo11s_ppe4_r2/weights/best.pt --data data/ppe4/dataset/data.yaml --out outputs/results/ppe6_eval/r2_ppe4val

Ghi <out>/capture.npz: mỗi dự đoán (ảnh, hộp ở không gian ảnh đã letterbox, conf, lớp, tp 10 mức IoU) và mỗi nhãn (ảnh, hộp, lớp),
`files`, `canvas` (cỡ letterbox), `ratio_pad`, `ori_shape`. Bộ đánh giá 04e đọc file này, nên baseline và ứng viên cùng một đường tính.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--batch", type=int, default=4)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    from ultralytics import YOLO
    from ultralytics.models.yolo.detect.val import DetectionValidator

    rows = []
    original = DetectionValidator._process_batch

    def hooked(self, preds, batch):
        out = original(self, preds, batch)
        rows.append(dict(file=Path(batch["im_file"]).name, pb=preds["bboxes"].float().cpu().numpy(), conf=preds["conf"].float().cpu().numpy(), cls=preds["cls"].cpu().numpy(),
                         tp=out["tp"], gb=batch["bboxes"].float().cpu().numpy().reshape(-1, 4), gc=batch["cls"].cpu().numpy().reshape(-1),
                         canvas=list(batch["imgsz"]), ori=list(batch["ori_shape"]), rp=[float(batch["ratio_pad"][0][0]), *[float(x) for x in batch["ratio_pad"][1]]]))
        return out

    DetectionValidator._process_batch = hooked
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    m = YOLO(args.weights).val(data=args.data, split="val", imgsz=args.imgsz, batch=args.batch, plots=False, project=str(out), name="val", exist_ok=True, device=0, verbose=False)
    DetectionValidator._process_batch = original
    idx = np.concatenate([[i] * len(r["conf"]) for i, r in enumerate(rows)] or [[]]).astype(int)
    gidx = np.concatenate([[i] * len(r["gc"]) for i, r in enumerate(rows)] or [[]]).astype(int)
    np.savez_compressed(out / "capture.npz", files=np.array([r["file"] for r in rows]), img=idx, box=np.concatenate([r["pb"] for r in rows]), conf=np.concatenate([r["conf"] for r in rows]),
                        cls=np.concatenate([r["cls"] for r in rows]).astype(int), tp=np.concatenate([r["tp"] for r in rows]), gimg=gidx, gbox=np.concatenate([r["gb"] for r in rows]),
                        gcls=np.concatenate([r["gc"] for r in rows]).astype(int), canvas=np.array([r["canvas"] for r in rows]), ori=np.array([r["ori"] for r in rows]), ratio_pad=np.array([r["rp"] for r in rows]))
    (out / "ultralytics.json").write_text(json.dumps(dict(map50=float(m.box.map50), map5095=float(m.box.map), ap50={int(c): float(a) for c, a in zip(m.box.ap_class_index, m.box.ap50)})), encoding="utf-8")
    print("Đã ghi", out, len(rows), "ảnh", float(m.box.map50))


if __name__ == "__main__":
    main()
