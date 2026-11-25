"""F2 (docs/experiments/2026-11-25_close_range_fixes.md): nhớ PPE theo (người, PPE, bên).

hold_conf, hold_iou ở đây là giá trị thử để kiểm logic; have_hold_s lấy từ cấu hình thử (test_cfg).
"""

import copy

from conftest import det, person

from ppe import HAVE, MISSING
from ppe.association import Associator
from ppe.compliance import Compliance

FRAME = (1000, 1000, 3)
VEST = (2, 150, 300, 250, 450)


def _cfg(test_cfg, mem=True):
    cfg = copy.deepcopy(test_cfg)
    cfg["required_ppe"] = ["vest"]
    cfg["compliance"]["have_hold_s"] = {"helmet": 1.0, "vest": 1.0, "gloves": 1.5}
    cfg["compliance"].pop("ppe_memory", None)           # cấu hình thật đã bật F2 cho găng, kính, ủng
    if mem:
        cfg["compliance"]["ppe_memory"] = {"hold_conf": 0.10, "hold_iou": 0.5}
    return cfg


def _step(cfg, comp, t, dets=(), weak=()):
    p = person(1, 100, 100, 300, 700)
    a = Associator(cfg)([p], [det(*x) for x in dets])
    comp.weak = [det(*x[:5], conf=x[5]) for x in weak]
    return comp([p], a, FRAME, t=t)[1]["vest"]


def test_without_memory_box_loss_is_missing_after_hold(test_cfg):
    cfg = _cfg(test_cfg, mem=False)
    comp = Compliance(cfg)
    assert _step(cfg, comp, 0.0, [VEST])["state"] == HAVE
    assert _step(cfg, comp, 0.5)["state"] != HAVE                 # như cũ: mất hộp -> không còn Có
    assert _step(cfg, comp, 1.6)["state"] == MISSING


def test_time_hold_keeps_have_then_expires(test_cfg):
    cfg = _cfg(test_cfg)
    comp = Compliance(cfg)
    assert _step(cfg, comp, 0.0, [VEST])["state"] == HAVE
    r = _step(cfg, comp, 0.5)
    assert r["state"] == HAVE and r["sides"][None][1]["held"] == "time"
    assert _step(cfg, comp, 1.0)["state"] == HAVE                 # đúng have_hold_s (1,0 s): còn giữ
    assert _step(cfg, comp, 1.1)["state"] == MISSING              # quá have_hold_s: bỏ giữ, báo chậm tối đa 1,0 s


def test_weak_box_at_same_place_renews_memory(test_cfg):
    cfg = _cfg(test_cfg)
    comp = Compliance(cfg)
    _step(cfg, comp, 0.0, [VEST])
    weak = [(2, 152, 302, 252, 452, 0.15)]                        # điểm dưới ngưỡng, trùng vị trí nhớ
    for t in (0.8, 1.6, 2.4, 3.2):
        r = _step(cfg, comp, t, weak=weak)
        assert r["state"] == HAVE and r["sides"][None][1]["held"] == "weak"


def test_weak_box_elsewhere_does_not_renew(test_cfg):
    cfg = _cfg(test_cfg)
    comp = Compliance(cfg)
    _step(cfg, comp, 0.0, [VEST])
    far = [(2, 150, 500, 250, 650, 0.15)]                         # IoU với hộp nhớ = 0
    assert _step(cfg, comp, 0.8, weak=far)["sides"][None][1]["held"] == "time"
    assert _step(cfg, comp, 1.2, weak=far)["state"] == MISSING


def test_memory_is_per_track(test_cfg):
    cfg = _cfg(test_cfg)
    comp = Compliance(cfg)
    _step(cfg, comp, 0.0, [VEST])
    p2 = person(2, 100, 100, 300, 700)
    a = Associator(cfg)([p2], [])
    comp.weak = []
    assert comp([p2], a, FRAME, t=0.5)[2]["vest"]["state"] == MISSING   # người khác không thừa hưởng bộ nhớ


def test_memory_only_for_listed_ppe(test_cfg):
    """ppe_memory.ppe: chỉ các món trong danh sách được giữ (người dùng chọn găng, kính, ủng ngày 25/11/2026)."""
    cfg = _cfg(test_cfg)
    cfg["compliance"]["ppe_memory"]["ppe"] = ["gloves"]
    comp = Compliance(cfg)
    assert _step(cfg, comp, 0.0, [VEST])["state"] == HAVE
    r = _step(cfg, comp, 0.5)
    assert r["state"] != HAVE and not r["sides"][None][1].get("held")   # áo không trong danh sách: như cũ
