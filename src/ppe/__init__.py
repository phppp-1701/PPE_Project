"""Chuỗi xử lý giám sát PPE (docs/spec.md mục 5). Kiểu dữ liệu và hàm dùng chung cho các module."""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
PIPELINE_CONFIG = ROOT / "configs" / "pipeline.yaml"

# Trạng thái PPE của một người trong một khung hình (Bảng 3.5).
HAVE, MISSING, UNKNOWN = "co", "thieu", "chua_xac_dinh"


class MissingParameter(ValueError):
    """Tham số trong configs/pipeline.yaml còn null (chưa chọn trên val / video chỉnh tham số)."""


def load_config(path=PIPELINE_CONFIG):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def require(cfg, *keys):
    """Lấy cfg[k1][k2]...; báo MissingParameter nếu giá trị (hoặc giá trị con) còn null."""
    value = cfg
    for k in keys:
        value = value[k]
    nulls = [k for k, v in value.items() if v is None] if isinstance(value, dict) else ([] if value is not None else [""])
    if nulls:
        name = ".".join(keys)
        raise MissingParameter(f"configs/pipeline.yaml: {name}{' -> ' + ', '.join(nulls) if nulls != [''] else ''} "
                               "còn null (chưa chọn)")
    return value


@dataclass
class Det:
    """Một hộp phát hiện, tọa độ pixel ảnh gốc."""
    cls: int
    xyxy: np.ndarray
    conf: float

    @property
    def center(self):
        return (self.xyxy[0] + self.xyxy[2]) / 2, (self.xyxy[1] + self.xyxy[3]) / 2


@dataclass
class Track:
    """Một người đang được theo dõi ở khung hiện tại."""
    track_id: int
    xyxy: np.ndarray
    det_conf: float
    confident: bool          # hộp người khung này đạt ngưỡng conf person -> được dùng để xác định trạng thái
    extra: dict = field(default_factory=dict)


def box_area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def intersect(a, b):
    return np.array([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])], dtype=float)
