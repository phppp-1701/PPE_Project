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
