"""Bước F1 tầm gần (docs/experiments/2026-11-25_close_range_fixes.md): ủng theo mắt cá, găng theo cổ tay thang cẳng tay.

k_ankle, k_wrist ở đây là giá trị thử để kiểm logic, không phải tham số chọn trên val.
"""

import copy

from conftest import det, person
from test_association_compliance import _six

from ppe import HAVE, UNKNOWN
from ppe.association import Associator, limb_anchor_distance
from ppe.compliance import Compliance

FRAME = (1000, 1000, 3)


def _legs(ankle=0.9, knee=0.9):
    """Người chỉ thấy cẳng chân: hộp (100, 100, 300, 400); gối y 200, mắt cá y 330 (ống chân 130 px)."""
    p = person(1, 100, 100, 300, 400)
    k = [(200.0, 0.0, 0.0)] * 17
    k[13], k[14] = (170.0, 200.0, knee), (230.0, 200.0, knee)
    k[15], k[16] = (170.0, 330.0, ankle), (230.0, 330.0, ankle)
    p.extra["kps"] = k
    p.extra["wrists"] = {"left": (0.0, 0.0, 0.0), "right": (0.0, 0.0, 0.0)}
    return p


def _arm(wrist=0.6, elbow=0.9):
    """Người nửa thân (100, 100, 500, 500); cổ tay trái COCO 9 ở (150, 400), khuỷu 7 ở (150, 300): cẳng tay 100 px."""
    p = person(1, 100, 100, 500, 500)
    k = [(300.0, 150.0, 0.9)] * 17
    k[7], k[9] = (150.0, 300.0, elbow), (150.0, 400.0, wrist)
    k[8], k[10] = (450.0, 300.0, 0.1), (450.0, 400.0, 0.1)
    p.extra["kps"] = k
    p.extra["wrists"] = {"left": (150.0, 400.0, wrist), "right": (450.0, 400.0, 0.1)}
    return p


def _cfg(test_cfg, ankle=False, wrist=False):
    cfg = _six(copy.deepcopy(test_cfg))
    cfg["pose"]["wrist_conf"] = 0.8
    if ankle:
        cfg["association"]["ankle_anchor"] = {"kp_conf": 0.5, "k_ankle": 0.6}
    if wrist:
        cfg["association"]["wrist_anchor"] = {"kp_conf": 0.5, "k_wrist": 0.8}
    return cfg


BOOT = (5, 140, 260, 200, 390)      # tâm (170, 325): y chuẩn hóa 0,75 < feet.y0 0,8 của cấu hình thử -> vùng cũ loại


def _owned(cfg, p, dets, name, side=None):
    a = Associator(cfg)([p], [det(*x) for x in dets])
    return bool(a.owned.get(1, {}).get((name, side)))


def test_limb_anchor_distance_scale_and_gate():
    p = _legs()
    assert abs(limb_anchor_distance(p, (170.0, 330.0 + 39.0), 15, 13, 0.5, 0.6) - 0.5) < 1e-9   # 39 / (130 * 0,6)
    assert limb_anchor_distance(p, (170.0, 330.0 + 100.0), 15, 13, 0.5, 0.6) is None             # 100 > 78
    assert limb_anchor_distance(_legs(knee=0.3), (170.0, 335.0), 15, 13, 0.5, 0.6) is None       # gối dưới kp_conf


def test_boot_of_legs_only_person_assigned_by_ankle(test_cfg):
    assert not _owned(_cfg(test_cfg), _legs(), [BOOT], "boots")
    assert _owned(_cfg(test_cfg, ankle=True), _legs(), [BOOT], "boots")


def test_boot_anchor_edge_gate(test_cfg):
    """Lần 2: có edge_px thì chỉ neo khi mép trên hộp người chạm mép trên khung."""
    cfg = _cfg(test_cfg, ankle=True)
    cfg["association"]["ankle_anchor"]["edge_px"] = 4
    assert not _owned(cfg, _legs(), [BOOT], "boots")              # hộp người y1 = 100: không bị cắt -> như cũ
    p = _legs()
    p.xyxy[1] = 0.0                                               # người bị cắt ở mép trên: hộp (100, 0, 300, 400)
    boot = (5, 140, 240, 200, 360)                                # tâm y 300 = 0,75 chiều cao hộp < feet.y0 0,8
    assert not _owned(_cfg(test_cfg), p, [boot], "boots")         # vùng cũ loại
    assert _owned(cfg, p, [boot], "boots")                        # neo mắt cá nhận


def test_boot_far_from_ankle_not_assigned(test_cfg):
    far = (5, 230, 100, 290, 160)    # gần mép trên, xa mắt cá
    assert not _owned(_cfg(test_cfg, ankle=True), _legs(), [far], "boots")


def test_boot_anchor_needs_visible_ankle(test_cfg):
    assert not _owned(_cfg(test_cfg, ankle=True), _legs(ankle=0.2), [BOOT], "boots")


GLOVE = (3, 130, 400, 180, 470)      # tâm (155, 435): cách cổ tay 35 px, cổ tay conf 0,6 < pose.wrist_conf 0,8


def test_glove_low_wrist_conf_assigned_by_forearm_scale(test_cfg):
    assert not _owned(_cfg(test_cfg), _arm(), [GLOVE], "gloves", "left")
    cfg = _cfg(test_cfg, wrist=True)
    assert _owned(cfg, _arm(), [GLOVE], "gloves", "left")
    p = _arm()
    a = Associator(cfg)([p], [det(*GLOVE)])
    s = Compliance(cfg)([p], a, FRAME)[1]["gloves"]["sides"]
    assert s["left"][0] == HAVE                                   # tay có găng: Có
    assert s["right"][0] == UNKNOWN                               # tay kia không thấy: Chưa xác định


def test_wrist_anchor_never_infers_missing(test_cfg):
    cfg = _cfg(test_cfg, wrist=True)
    p = _arm()
    a = Associator(cfg)([p], [])
    s = Compliance(cfg)([p], a, FRAME)[1]["gloves"]["sides"]
    assert s["left"][0] == UNKNOWN                                # cổ tay < wrist_conf, không găng: không suy ra Thiếu


def test_glove_far_from_wrist_not_assigned(test_cfg):
    far = (3, 300, 120, 340, 160)
    assert not _owned(_cfg(test_cfg, wrist=True), _arm(), [far], "gloves", "left")
