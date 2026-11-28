"""Bước S: khung bỏ qua bộ phân loại dùng lại phiếu đã gộp, không thêm phiếu (docs/experiments/2026-11-27_unknown_fix_plan.md)."""

import copy

from conftest import person

from ppe.compliance import Compliance


def test_skip_frame_reuses_window_mean(test_cfg):
    c = Compliance(copy.deepcopy(test_cfg))
    c.part = {"vote_window_s": 1.0}
    t = person(1, 0, 0, 100, 300)
    c.now = 0.0
    t.extra["parts"] = {("helmet", None): 0.9}
    assert c.part_ps("helmet", t, None) == [0.9]
    c.now = 0.1
    t.extra["parts"] = {("helmet", None): 0.5}
    assert abs(c.part_ps("helmet", t, None)[0] - 0.7) < 1e-9
    c.now = 0.2                                   # khung bỏ qua: không thêm phiếu, dùng trung bình đã có
    t.extra.pop("parts")
    t.extra["parts_skip"] = True
    assert abs(c.part_ps("helmet", t, None)[0] - 0.7) < 1e-9
    assert len(c.p_hist[(1, "helmet", None)]) == 2
    c.now = 1.5                                   # hết cửa sổ: không còn phiếu
    assert c.part_ps("helmet", t, None) == []


def test_skip_frame_uses_only_last_run_sides(test_cfg):
    """P2: chân chỉ có trong lịch sử cũ (không có ở lần chạy gần nhất) không được dùng ở khung bỏ qua."""
    c = Compliance(copy.deepcopy(test_cfg))
    c.part = {"vote_window_s": 1.0}
    t = person(1, 0, 0, 100, 300)
    c.now = 0.0
    t.extra["parts"] = {("boots", "15"): 0.9, ("boots", "16"): 0.1}
    assert sorted(c.part_ps("boots", t, None)) == [0.1, 0.9]
    c.now = 0.1
    t.extra["parts"] = {("boots", "16"): 0.1}               # lần chạy này chỉ thấy một chân
    assert c.part_ps("boots", t, None) == [0.1]
    c.now = 0.2
    t.extra.pop("parts")
    t.extra["parts_skip"] = True
    assert c.part_ps("boots", t, None) == [0.1]             # không lấy lại chân "15"
