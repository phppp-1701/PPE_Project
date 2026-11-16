"""Bước M1 (kế hoạch 2026-11-16_post_holdout_fixes mục 2): bộ phân loại chân bác bỏ hộp ủng của detector.

Luật: khi có part_cls.veto_boots, nếu MỌI chân có ảnh cắt đều 1 - p >= t_veto thì bỏ hộp ủng (has = False); luật Thiếu
của ủng giữ nguyên (luật cũ). Vắng khóa: như bản cuối. t_veto ở đây là giá trị thử, không phải giá trị chọn trên val.
"""

from conftest import det, person
from test_association_compliance import _helmet_v4, _kps

from ppe import HAVE, MISSING
from ppe.association import Associator
from ppe.compliance import Compliance

FRAME = (1000, 1000, 3)
BOOT_BOX = (5, 160, 650, 240, 700)      # vùng chân của người (100, 100, 300, 700)


def _cfg(test_cfg, t_veto=None):
    cfg = _helmet_v4(test_cfg)
    cfg["part_cls"].pop("veto_boots", None)
    if t_veto is not None:
        cfg["part_cls"]["veto_boots"] = {"t_veto": t_veto}
    return cfg


def _p(feet=(0.05, 0.05)):
    """Người nhìn rõ, p có ủng của bộ phân loại cho từng chân (None = không có ảnh cắt chân đó)."""
    p = _kps(person(1, 100, 100, 300, 700))
    p.extra["parts"] = {("helmet", None): 0.99}
    for side, v in zip(("15", "16"), feet):
        if v is not None:
            p.extra["parts"][("boots", side)] = v
    return p


def _out(cfg, p, dets=(BOOT_BOX,)):
    a = Associator(cfg)([p], [det(*x) for x in dets])
    return Compliance(cfg)([p], a, FRAME)[1]


def test_without_key_box_is_have(test_cfg):
    assert _out(_cfg(test_cfg), _p())["boots"]["state"] == HAVE


def test_sandals_box_vetoed(test_cfg):
    """Ca h2: detector thấy ủng trên dép, bộ phân loại rất chắc không phải ủng ở cả hai chân -> bỏ hộp -> Thiếu."""
    s = _out(_cfg(test_cfg, 0.8), _p((0.05, 0.1)))["boots"]
    assert s["state"] == MISSING
    assert s["sides"][None][1]["c2"] == "veto" and not s["sides"][None][1]["has"]


def test_one_foot_unsure_keeps_box(test_cfg):
    assert _out(_cfg(test_cfg, 0.8), _p((0.05, 0.5)))["boots"]["state"] == HAVE
    assert _out(_cfg(test_cfg, 0.8), _p((0.05, 0.95)))["boots"]["state"] == HAVE


def test_threshold_boundary(test_cfg):
    assert _out(_cfg(test_cfg, 0.8), _p((0.2, 0.2)))["boots"]["state"] == MISSING      # 1 - p = 0,8 >= 0,8
    assert _out(_cfg(test_cfg, 0.8), _p((0.21, 0.21)))["boots"]["state"] == HAVE       # 0,79 < 0,8


def test_one_foot_crop_only(test_cfg):
    assert _out(_cfg(test_cfg, 0.8), _p((0.05, None)))["boots"]["state"] == MISSING
    assert _out(_cfg(test_cfg, 0.8), _p((None, None)))["boots"]["state"] == HAVE         # không có ảnh cắt: giữ hộp


def test_no_box_unchanged(test_cfg):
    a, b = _cfg(test_cfg), _cfg(test_cfg, 0.8)
    for feet in ((0.05, 0.05), (0.9, 0.9)):
        assert _out(a, _p(feet), dets=())["boots"]["state"] == _out(b, _p(feet), dets=())["boots"]["state"]


def test_other_ppe_unchanged(test_cfg):
    a, b = _cfg(test_cfg), _cfg(test_cfg, 0.8)
    dets = (BOOT_BOX, (1, 170, 100, 230, 160))
    sa, sb = _out(a, _p(), dets), _out(b, _p(), dets)
    for name in ("helmet", "vest", "gloves", "goggles"):
        assert sa[name]["state"] == sb[name]["state"]
