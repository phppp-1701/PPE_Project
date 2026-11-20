"""Kiểm tra scripts/04m_crop_pass.py: cách tính tp trùng Ultralytics, NMS, gộp hộp crop chỉ cho lớp trong `classes`."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CFG = dict(classes=[3, 4, 5], nms_iou=0.5, max_det=300, pad=0.15, min_side_ratio=0.6, imgsz=640)


def _mod():
    spec = importlib.util.spec_from_file_location("crop04m", ROOT / "scripts" / "04m_crop_pass.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _boxes(rng, n):
    xy = rng.uniform(0, 400, (n, 2))
    wh = rng.uniform(10, 120, (n, 2))
    return np.hstack([xy, xy + wh])


def test_match_tp_same_as_ultralytics():
    torch = pytest.importorskip("torch")
    from ultralytics.models.yolo.detect.val import DetectionValidator
    from ultralytics.utils.metrics import box_iou

    m = _mod()
    v = DetectionValidator.__new__(DetectionValidator)
    v.iouv = torch.linspace(0.5, 0.95, 10)
    rng = np.random.default_rng(0)
    for _ in range(30):
        g = _boxes(rng, rng.integers(0, 8))
        gc = rng.integers(0, 3, len(g))
        p = np.vstack([g + rng.normal(0, 8, g.shape), _boxes(rng, rng.integers(0, 6))]) if len(g) else _boxes(rng, 4)
        pc = np.concatenate([gc, rng.integers(0, 3, len(p) - len(gc))]) if len(g) else rng.integers(0, 3, len(p))
        mine = m.match_tp(p, pc, g, gc)
        if not len(g):
            assert not mine.any()
            continue
        ref = v.match_predictions(torch.tensor(pc), torch.tensor(gc), box_iou(torch.tensor(g, dtype=torch.float32), torch.tensor(p, dtype=torch.float32))).numpy()
        assert (mine == ref).all()


def test_nms_keeps_best_and_drops_overlap():
    m = _mod()
    b = np.array([[0, 0, 100, 100], [5, 5, 100, 100], [200, 200, 260, 260]], dtype=float)
    k = m.nms(b, np.array([0.5, 0.9, 0.3]), 0.5)
    assert k.tolist() == [1, 2]


def test_merge_only_touches_listed_classes():
    m = _mod()
    pbox = np.array([[0, 0, 50, 50], [100, 100, 140, 140], [300, 300, 340, 340]], dtype=float)
    pconf = np.array([0.9, 0.4, 0.7])
    pcls = np.array([0, 3, 2])
    extra = np.array([[102, 102, 140, 140, 0.6, 3],    # trùng găng gốc -> NMS giữ hộp conf cao hơn
                      [400, 400, 430, 430, 0.5, 3],    # găng mới
                      [302, 302, 340, 340, 0.8, 2]])   # áo không thuộc classes -> bỏ
    b, s, c = m.merge_image(pbox, pconf, pcls, extra, CFG)
    assert sorted(zip(c.tolist(), np.round(s, 2).tolist())) == [(0, 0.9), (2, 0.7), (3, 0.5), (3, 0.6)]
    assert (np.diff(s) <= 0).all()


def test_person_crops_skip_small_and_map_offsets():
    m = _mod()
    im = np.zeros((2000, 3000, 3), dtype=np.uint8)
    rp = (0.5, 0.0, 10.0)   # gain, pad x, pad y: canvas = gốc * 0,5 + pad
    big = np.array([500, 210, 700, 710], dtype=float)    # gốc: 1000-1400 x 400-1400
    small = np.array([10, 20, 60, 120], dtype=float)     # gốc dài 200 px < 0,6 * 640
    crops, offs = m.person_crops(im, np.vstack([big, small]), rp, CFG)
    assert len(crops) == 1
    assert offs[0] == (940, 250)
    assert crops[0].shape[:2] == (1300, 520)
