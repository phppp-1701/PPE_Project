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
    assert crops[0].shape == (640, 640, 3)        # vùng cắt 1300 x 520 -> vuông 640 (cùng cỡ cho mọi người)
    r, dx, dy, ox, oy = offs[0]
    assert (ox, oy) == (940, 250) and abs(r - 640 / 1300) < 1e-12 and (dx, dy) == (192, 0)
    back = m.unletterbox([dx, dy, dx + 256, dy + 640], r, dx, dy, ox, oy)
    assert np.allclose(back, [940, 250, 940 + 520, 250 + 1300], atol=1.5)


def test_detector_zoom_merge_with_fake_model():
    """src/ppe/detector.py: hộp từ ảnh cắt đổi về toạ độ khung, nhân conf_scale, lọc conf, NMS với PPE cả khung."""
    pytest.importorskip("torchvision")
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from ppe import Det
    from ppe.detector import Detector

    class Boxes:
        def __init__(self, rows):
            a = np.array(rows, dtype=float).reshape(-1, 6)
            self.xyxy, self.conf, self.cls = a[:, :4], a[:, 4], a[:, 5]

        def cpu(self):
            return self

        def numpy(self):
            return self

    class R:
        def __init__(self, rows):
            self.boxes = Boxes(rows)

    class FakeModel:
        def __init__(self):
            self.calls = []

        def predict(self, crop, **kw):
            self.calls.append(([crop.shape], kw))
            # toạ độ trong ảnh cắt 500 x 400: găng trùng găng cả khung (conf cao hơn), găng mới, áo (không thuộc
            # zoom.classes), găng conf thấp; mô hình thấy ảnh vuông 640: x * 1,28 + 64, y * 1,28
            rows = [[60, 60, 100, 100, 0.9, 3], [300, 300, 340, 340, 0.5, 3], [10, 10, 200, 200, 0.95, 2],
                    [380, 400, 400, 420, 0.3, 3]]
            return [R([[x1 * 1.28 + 64, y1 * 1.28, x2 * 1.28 + 64, y2 * 1.28, s, c] for x1, y1, x2, y2, s, c in rows])]

    d = Detector.__new__(Detector)
    d.zoom_model, d.device, d.nms_iou = FakeModel(), 0, 0.5
    d.conf = {"person": 0.4, "helmet": 0.3, "vest": 0.3, "gloves": 0.3, "goggles": 0.15, "boots": 0.15}
    d.zoom = dict(every_n_frames=1, pad=0.0, imgsz=640, min_side_ratio=0.6, classes=[3, 4, 5], conf_scale=0.8, nms_iou=0.5, half=False)
    d.zoom_names = {3: "gloves", 4: "goggles", 5: "boots"}
    frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
    big = Det(0, np.array([100.0, 100.0, 500.0, 600.0]), 0.9)      # cạnh dài 500 >= 384 -> cắt
    small = Det(0, np.array([700.0, 700.0, 750.0, 800.0]), 0.9)    # cạnh dài 100 -> bỏ
    ppe = [Det(3, np.array([161.0, 161.0, 200.0, 200.0]), 0.4), Det(1, np.array([150.0, 100.0, 250.0, 150.0]), 0.8)]
    out = d._zoom_ppe(frame, [big, small], ppe)
    assert d.zoom_model.calls[0][0] == [(640, 640, 3)]
    assert abs(d.zoom_model.calls[0][1]["conf"] - 0.15 / 0.8) < 1e-9
    got = sorted((x.cls, round(x.conf, 3), tuple(np.round(x.xyxy).astype(int))) for x in out)
    assert got == [(1, 0.8, (150, 100, 250, 150)), (3, 0.4, (400, 400, 440, 440)), (3, 0.72, (160, 160, 200, 200))]
