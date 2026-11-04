"""Cấu hình chung cho pytest: thêm src/ vào đường dẫn và tạo cấu hình thử.

Giá trị trong `test_cfg` chỉ để kiểm tra logic của code, KHÔNG phải tham số của hệ thống
(tham số thật chọn trên val / video chỉnh tham số và ghi ở configs/pipeline.yaml).
"""

import copy
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ppe import Det, Track, load_config  # noqa: E402


@pytest.fixture
def test_cfg():
    cfg = copy.deepcopy(load_config())
    cfg["association"]["regions"] = {
        "head": {"x0": 0.0, "x1": 1.0, "y0": 0.0, "y1": 0.3},
        "torso": {"x0": 0.2, "x1": 0.8, "y0": 0.25, "y1": 0.7},
        "hands": {"x0": -0.1, "x1": 1.1, "y0": 0.3, "y1": 0.9},
    }
    cfg["association"]["max_distance"] = {"helmet": 0.5, "vest": 0.5, "gloves": 0.6}
    cfg["association"]["ambiguity_margin"] = None
    cfg["compliance"]["tau_in"] = {"helmet": 0.9, "vest": 0.9, "gloves": 0.9}
    cfg["compliance"]["tau_occ"] = {"helmet": 0.3, "vest": 0.3, "gloves": 0.3}
    cfg["compliance"]["area_min_px"] = {"helmet": 10, "vest": 10, "gloves": 10}
    return cfg


@pytest.fixture
def temporal_params():
    return dict(T_on=2.0, T_off=2.0, n_on=3, n_off=3, theta_on=0.6, theta_off=0.6)


def person(tid, x1, y1, x2, y2, confident=True):
    return Track(tid, np.array([x1, y1, x2, y2], dtype=float), 0.9, confident)


def det(cls, x1, y1, x2, y2, conf=0.9):
    return Det(cls, np.array([x1, y1, x2, y2], dtype=float), conf)
