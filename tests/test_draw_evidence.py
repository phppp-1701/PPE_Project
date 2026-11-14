"""Bước A: vẽ bằng chứng của bộ phân loại trong 05_run_video.draw() chỉ là hiển thị, không đổi kết quả nhận diện."""

import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from ppe import HAVE, load_config

ROOT = Path(__file__).resolve().parents[1]


def _rv():
    spec = importlib.util.spec_from_file_location("run_video", ROOT / "scripts" / "05_run_video.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _kps():
    k = [(200.0, 150.0, 0.9), (190.0, 140.0, 0.9), (210.0, 140.0, 0.9), (180.0, 145.0, 0.9), (220.0, 145.0, 0.9)]
    k += [(200.0, 400.0, 0.9)] * 12
    return k


def _out(vote, has):
    tr = SimpleNamespace(track_id=1, xyxy=np.array([100.0, 100.0, 300.0, 700.0]), confident=True, extra={"kps": _kps()})
    det = {"v": 1.0, "o": 0.0, "area": 1, "observable": True, "has": has, "contested": False, "vote": vote}
    return {"tracks": [tr], "lost": [], "ppe": [],
            "states": {1: {"goggles": {"state": HAVE, "sides": {None: (HAVE, det)}}}}}


def _cfg():
    cfg = load_config()
    assert cfg["part_cls"]["enabled"] and "eye" in cfg["part_cls"]["geometry"]
    return cfg


def _draw(rv, cfg, out):
    img = np.zeros((1000, 1000, 3), np.uint8)
    return rv.draw(img, out, cfg, False)


def test_draw_does_not_change_results():
    rv, cfg = _rv(), _cfg()
    out = _out("pos", False)
    before = copy.deepcopy({"states": out["states"], "kps": out["tracks"][0].extra, "xyxy": out["tracks"][0].xyxy.tolist()})
    _draw(rv, cfg, out)
    after = {"states": out["states"], "kps": out["tracks"][0].extra, "xyxy": out["tracks"][0].xyxy.tolist()}
    assert before == after


def test_draw_classifier_region_only_when_pos_without_box():
    rv, cfg = _rv(), _cfg()
    base = _draw(rv, cfg, _out("unsure", False))
    pos = _draw(rv, cfg, _out("pos", False))
    with_box = _draw(rv, cfg, _out("pos", True))
    assert np.array_equal(base, with_box)                  # có hộp detector: không vẽ thêm
    diff = np.any(pos != base, axis=2)
    assert diff.any()                                     # phiếu pos, không hộp: có vẽ thêm
    # Vùng ảnh cắt mắt theo parts.eye_box: tâm (200, 140), cạnh s * 20 (s = geometry.eye.s)
    side = cfg["part_cls"]["geometry"]["eye"]["s"] * 20
    x1, y1, x2, y2 = 200 - side / 2, 140 - side / 2, 200 + side / 2, 140 + side / 2
    ys, xs = np.nonzero(diff)
    assert xs.min() >= x1 - 3 and ys.min() >= y1 - 3      # bắt đầu ở góc ảnh cắt (nhãn "(PL)" nằm dưới, bên phải)
    assert diff[int(y1), int(x1):int(x2)].any()           # có nét ở cạnh trên của vùng ảnh cắt
    assert not diff[int(y1) + 5:int(y2) - 5, int(x1) + 5:int(x2) - 5].all()   # nét đứt, không tô kín
