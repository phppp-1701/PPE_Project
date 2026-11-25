"""A2 (docs/experiments/2026-11-25_close_range_fixes.md): lớp hiển thị chỉ đổi trạng thái vẽ, không đổi kết quả."""

from ppe import HAVE, MISSING, UNKNOWN
from ppe.display import DisplaySmoother


def _s(state):
    return {1: {"gloves": {"state": state}}}


def test_unknown_shows_last_definite_within_hold():
    d = DisplaySmoother(1.0)
    assert d(0.0, _s(MISSING))[1]["gloves"] == MISSING
    assert d(0.5, _s(UNKNOWN))[1]["gloves"] == MISSING      # trong 1 s: vẫn hiện Thiếu
    assert d(1.0, _s(UNKNOWN))[1]["gloves"] == MISSING
    assert d(1.2, _s(UNKNOWN))[1]["gloves"] == UNKNOWN      # quá 1 s: Chưa xác định


def test_definite_states_switch_immediately():
    d = DisplaySmoother(2.0)
    d(0.0, _s(MISSING))
    assert d(0.1, _s(HAVE))[1]["gloves"] == HAVE            # Thiếu -> Có hiện ngay
    assert d(0.2, _s(MISSING))[1]["gloves"] == MISSING      # Có -> Thiếu hiện ngay


def test_input_states_not_modified():
    d = DisplaySmoother(1.0)
    d(0.0, _s(HAVE))
    st = _s(UNKNOWN)
    d(0.5, st)
    assert st[1]["gloves"]["state"] == UNKNOWN               # kết quả nhận diện giữ nguyên


def test_per_track():
    d = DisplaySmoother(1.0)
    d(0.0, _s(HAVE))
    assert d(0.5, {2: {"gloves": {"state": UNKNOWN}}})[2]["gloves"] == UNKNOWN
