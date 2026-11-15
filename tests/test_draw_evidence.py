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


def _out_helmet_box(c2, state=None):
    """Người có hộp mũ detector gán cho mình; compliance ghi c2 (bước C2) = None / "veto" / "conflict"."""
    from ppe import Det, MISSING
    state = state or (HAVE if c2 is None else MISSING)
    tr = SimpleNamespace(track_id=1, xyxy=np.array([100.0, 100.0, 300.0, 700.0]), confident=True, extra={"kps": _kps()})
    box = Det(1, np.array([150.0, 100.0, 250.0, 180.0]), 0.6)
    assoc = SimpleNamespace(owned={1: {("helmet", None): [box]}}, rejected=[])
    det = {"v": 1.0, "o": 0.0, "area": 1, "observable": True, "has": c2 is None, "contested": False, "vote": "neg", "c2": c2}
    return {"tracks": [tr], "lost": [], "ppe": [box], "assoc": assoc,
            "states": {1: {"helmet": {"state": state, "sides": {None: (state, det)}}}}}


def test_draw_c2_vetoed_helmet_box_gray():
    """Bước C2 bác bỏ hộp mũ (vd đầu trọc video13): hộp detector vẽ xám (như kính thường), không vẽ màu mũ."""
    rv, cfg = _rv(), _cfg()
    plain = _draw(rv, cfg, _out_helmet_box(None))
    for c2 in ("veto", "conflict"):
        img = _draw(rv, cfg, _out_helmet_box(c2))
        assert tuple(int(v) for v in img[140, 150]) == rv.LOST_COLOR        # cạnh trái hộp mũ
    assert tuple(int(v) for v in plain[140, 150]) == rv.PPE_COLOR["helmet"]
    out = _out_helmet_box("veto")
    before = copy.deepcopy(out["states"])
    _draw(rv, cfg, out)
    assert out["states"] == before


def test_box_colored_only_when_state_have():
    """Quy tắc nhất quán (16/11/2026): hộp màu PPE chỉ khi gán cho người và món đó là Có; còn lại xám kèm lý do."""
    from ppe import MISSING, UNKNOWN
    rv, cfg = _rv(), _cfg()
    for state, kind in ((HAVE, "co"), (MISSING, "chua_ket_luan"), (UNKNOWN, "chua_ket_luan")):
        out = _out_helmet_box(None, state)
        assert rv.box_status(out, cfg)[id(out["ppe"][0])][0] == kind
        img = _draw(rv, cfg, out)
        want = rv.PPE_COLOR["helmet"] if state == HAVE else rv.LOST_COLOR
        assert tuple(int(v) for v in img[140, 150]) == want
        assert rv.display_check(out, cfg, img.shape) == []


def test_unassigned_box_gray_with_reason():
    from ppe import Det, MISSING
    rv, cfg = _rv(), _cfg()
    out = _out_helmet_box(None, MISSING)
    stray = Det(1, np.array([600.0, 100.0, 700.0, 180.0]), 0.8)
    out["ppe"].append(stray)
    out["assoc"].rejected = [("helmet", stray, "contested", [])]
    st = rv.box_status(out, cfg)
    assert st[id(stray)][0] == "tranh_chap" and st[id(stray)][2].endswith("(tranh chap)")
    img = _draw(rv, cfg, out)
    assert tuple(int(v) for v in img[140, 600]) == rv.LOST_COLOR


def test_display_check_finds_have_without_evidence():
    """Phép kiểm bắt được món Có mà không có hộp màu, không có vùng (PL) (vd không có keypoint để vẽ vùng)."""
    rv, cfg = _rv(), _cfg()
    out = _out("pos", False)
    out["ppe"], out["assoc"] = [], SimpleNamespace(owned={}, rejected=[])
    assert rv.display_check(out, cfg, (1000, 1000, 3)) == []                 # có keypoint: vùng (PL)
    out["tracks"][0].extra = {}
    assert rv.display_check(out, cfg, (1000, 1000, 3)) == [("co_khong_bang_chung", 1, "goggles", None)]


def test_one_glove_box_for_both_hands():
    """Một hộp găng phủ hai tay, gán cho cả tay trái và tay phải (cả hai Có): hộp màu, không báo thiếu bằng chứng."""
    from ppe import Det
    rv, cfg = _rv(), _cfg()
    tr = SimpleNamespace(track_id=1, xyxy=np.array([100.0, 100.0, 300.0, 700.0]), confident=True, extra={"kps": _kps()})
    box = Det(3, np.array([150.0, 400.0, 250.0, 480.0]), 0.8)
    det = {"v": 1.0, "o": 0.0, "area": 1, "observable": True, "has": True, "contested": False, "vote": None, "c2": None}
    out = {"tracks": [tr], "lost": [], "ppe": [box],
           "assoc": SimpleNamespace(owned={1: {("gloves", "left"): [box], ("gloves", "right"): [box]}}, rejected=[]),
           "states": {1: {"gloves": {"state": HAVE, "sides": {"left": (HAVE, det), "right": (HAVE, det)}}}}}
    assert rv.box_status(out, cfg)[id(box)][0] == "co"
    assert rv.display_check(out, cfg, (1000, 1000, 3)) == []
