"""Round5 U1: vùng chân (Detector.feet_box) — keypoint gối, dự phòng theo tỉ lệ, nới pad, cắt mép ảnh."""

from types import SimpleNamespace

import numpy as np

from ppe.detector import Detector

F = dict(enabled=True, imgsz=320, pad=0.1, feet_top=0.6, kp_conf=0.5, min_px=160, cls=5, conf_scale=0.8)


def _det():
    d = Detector.__new__(Detector)      # không nạp mô hình; chỉ kiểm hình học
    d.feet = F
    return d


def _t(xyxy, kps=None):
    return SimpleNamespace(xyxy=np.array(xyxy, dtype=float), extra={"kps": kps} if kps else {})


def test_fallback_without_keypoints():
    b = _det().feet_box(_t([100, 0, 300, 1000]), 1920, 1080)
    assert b == (80, 560, 320, 1040)                 # đỉnh 600 - 0,1 x 400; đáy 1000 + 0,1 x 400 (trong khung)


def test_knee_keypoints_used():
    k = [(0.0, 0.0, 0.0)] * 17
    k[13], k[14] = (150.0, 700.0, 0.9), (250.0, 720.0, 0.9)
    b = _det().feet_box(_t([100, 0, 300, 1000], k), 1920, 1080)
    assert b[1] == int(700 - 0.1 * 300)


def test_clipped_at_frame_edge_and_small_skipped():
    b = _det().feet_box(_t([0, 600, 200, 1080]), 1920, 1080)
    assert b[0] == 0 and b[3] == 1080
    assert _det().feet_box(_t([0, 0, 40, 100]), 1920, 1080) is None
