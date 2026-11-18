"""Bước A (kế hoạch 2026-11-16_c5_detector_plan.md): đo tốc độ detector trên laptop cho các cỡ mô hình × imgsz,
trước khi quyết định train ở 1280 hay dùng YOLO11m. Chỉ đo tốc độ (không đo độ chính xác): trọng số COCO của
Ultralytics có cùng kiến trúc thân với bản 6 lớp, chỉ khác đầu phân lớp, nên thời gian gần như như nhau.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04i_detector_speed.py

Tham số ở configs/ppe6.yaml mục `speed_check`. Ghi outputs/results/error_analysis/detector_speed.json:
mỗi cấu hình: ms/khung (trung bình, p50, p95) của model.predict batch 1 trên khung video thật, như Detector của pipeline.
"""

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["speed_check"]
    from ultralytics import YOLO
    import torch

    cap = cv2.VideoCapture(str(ROOT / cfg["video"]))
    frames = []
    while len(frames) < cfg["frames"]:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    res = dict(video=cfg["video"], frames=len(frames), gpu=torch.cuda.get_device_name(0), runs=[])
    for w in cfg["weights"]:
        model = YOLO(w)
        for imgsz, half in [(z, h) for z in cfg["imgsz"] for h in cfg.get("half", [False])]:
            for f in frames[:cfg["warmup"]]:
                model.predict(f, imgsz=imgsz, conf=0.1, device=0, verbose=False, half=half)
            ts = []
            for f in frames[cfg["warmup"]:]:
                torch.cuda.synchronize()
                s = time.perf_counter()
                model.predict(f, imgsz=imgsz, conf=0.1, device=0, verbose=False, half=half)
                torch.cuda.synchronize()
                ts.append((time.perf_counter() - s) * 1000)
            ts = np.array(ts)
            r = dict(weights=w, imgsz=imgsz, half=half, n=len(ts), mean_ms=round(float(ts.mean()), 2),
                     p50_ms=round(float(np.percentile(ts, 50)), 2), p95_ms=round(float(np.percentile(ts, 95)), 2))
            res["runs"].append(r)
            print(r)
    out = ROOT / "outputs" / "results" / "error_analysis" / cfg.get("out", "detector_speed.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
