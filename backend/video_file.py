"""Nguồn phát từ tệp video cho LiveCamera (docs/desktop_app_plan.md mục 4.1).

Nguyên tắc:
- Đọc tuần tự từng khung hình (không bỏ khung) để mốc thời gian `t = frame_index / fps` khớp tuyệt đối với
  `scripts/05_run_video.py`.
- Hỗ trợ 2 chế độ phát:
    + `realtime`: giữ nhịp theo tốc độ gốc của video để người giám sát quan sát trực tiếp.
    + `fast`: xử lý nhanh nhất có thể để duyệt nhanh toàn bộ tệp video.
- Hỗ trợ tạm dừng (`pause`) và tiếp tục (`resume`) mà không làm lệch mốc thời gian `t` của sự kiện.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import cv2

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


def sanitize_video_source_id(file_path: str | Path) -> str:
    """Tạo `source_id` chuẩn từ tên tệp video (vd. `video4.mp4` -> `video_video4`)."""
    stem = Path(file_path).stem.strip()
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", stem).strip("_").lower() or "file"
    if clean.startswith("video"):
        return clean
    return f"video_{clean}"


def open_video_file(file_path: str | Path) -> tuple[cv2.VideoCapture, dict[str, Any]]:
    """Kiểm tra và mở tệp video bằng OpenCV; trả về `(cap, meta)` hoặc ném `RuntimeError` dễ hiểu."""
    if not file_path or not str(file_path).strip():
        raise RuntimeError("Chưa chọn tệp video. Vui lòng chọn tệp .mp4, .avi hoặc .mov.")
    p = Path(str(file_path)).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise RuntimeError(f"Không tìm thấy tệp video: {p}")
    if p.suffix.lower() not in ALLOWED_VIDEO_EXTENSIONS:
        raise RuntimeError(
            f"Định dạng tệp '{p.suffix}' không được hỗ trợ. Vui lòng chọn tệp {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}."
        )

    cap = cv2.VideoCapture(str(p))
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được tệp video '{p.name}'. Tệp có thể bị hỏng hoặc thiếu codec.")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0.1 or fps > 240.0:
        fps = 25.0
    total_frames = max(0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration_s = round(total_frames / fps, 2) if total_frames > 0 else 0.0

    meta = {
        "path": str(p),
        "file_name": p.name,
        "source_id": sanitize_video_source_id(p),
        "source_name": f"Video: {p.name}",
        "fps": round(fps, 3),
        "total_frames": total_frames,
        "duration_s": duration_s,
        "resolution": [width, height] if width and height else None,
    }
    return cap, meta
