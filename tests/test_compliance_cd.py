"""Bước C (phủ quyết mũ khi nhìn thẳng) và D (nhận quay lưng), kế hoạch ppe6 mục C, D (16/11/2026).

Ngưỡng bộ phân loại (part_cls) lấy từ configs/pipeline.yaml như khi chạy (qua _helmet_v4). face_conf của C ở đây là giá
trị thử (chưa chọn trên val); số của D là quy ước người dùng đã duyệt (0,3 / 5% / 0,9 / 1,0 s).
"""

import copy

from conftest import det, person
from test_association_compliance import _helmet_v4, _kps, run

from ppe import HAVE, MISSING, UNKNOWN, load_config
from ppe.association import Associator
from ppe.compliance import Compliance, back_view_now, frontal_strict

FRAME = (1000, 1000, 3)
BV = dict(kp_conf=0.3, min_sep=0.05, face_strong=0.9, hold_s=1.0)
HELMET_BOX = (1, 170, 100, 230, 160)


def _cfg(test_cfg, c=False, d=False, face_conf=0.8, t_veto=None):
    cfg = _helmet_v4(test_cfg)
    cfg["part_cls"].pop("veto_frontal", None)
    cfg["compliance"].pop("back_view", None)
    if c:
        cfg["part_cls"]["veto_frontal"] = {"helmet": {"face_conf": face_conf}}
        if t_veto is not None:
            cfg["part_cls"]["veto_frontal"]["helmet"]["t_veto"] = t_veto
    if d:
        cfg["compliance"]["back_view"] = dict(BV)
    return cfg


def _p(view="front", sh=0.9, face=0.95, eyes=None, p_helmet=0.02, p_goggles=None, sep=100.0, ears=None):
    """Người (100, 100, 300, 700), rộng 200. view: front (x5 > x6), back (x5 < x6), side (vai trùng x)."""
    p = _kps(person(1, 100, 100, 300, 700), eyes=face if eyes is None else eyes, head=face)
    k = list(p.extra["kps"])
    if ears is not None:                                                         # tai (3, 4)
        k[3], k[4] = (k[3][0], k[3][1], ears), (k[4][0], k[4][1], ears)
    if view == "front":
        k[5], k[6] = (200.0 + sep / 2, 250.0, sh), (200.0 - sep / 2, 250.0, sh)
    elif view == "back":
        k[5], k[6] = (200.0 - sep / 2, 250.0, sh), (200.0 + sep / 2, 250.0, sh)
    else:
        k[5], k[6] = (200.0, 250.0, sh), (200.0, 250.0, sh)
    p.extra["kps"] = k
    p.extra["parts"] = {("helmet", None): p_helmet}
    if p_goggles is not None:
        p.extra["parts"][("goggles", None)] = p_goggles
    return p


def _state(cfg, p, name, dets=(), t=None, comp=None):
    a = Associator(cfg)([p], [det(*x) for x in dets])
    return (comp or Compliance(cfg))([p], a, FRAME, t=t)[1][name]["state"]


# ------------------------------------------------------------ C

def test_c_frontal_bald_head_helmet_box_vetoed(test_cfg):
    """Ca video13: nhìn thẳng, bộ phân loại chắc không mũ, detector có hộp mũ -> C: Thiếu; bản 4: Có."""
    assert _state(_cfg(test_cfg), _p(), "helmet", [HELMET_BOX]) == HAVE
    assert _state(_cfg(test_cfg, c=True), _p(), "helmet", [HELMET_BOX]) == MISSING


def test_c_needs_high_face_conf(test_cfg):
    p = _p(face=0.75)                                                            # < face_conf 0,8
    assert _state(_cfg(test_cfg, c=True), p, "helmet", [HELMET_BOX]) == HAVE
    assert frontal_strict(_p(face=0.85).extra["kps"], 0.8, 0.5) and not frontal_strict(p.extra["kps"], 0.8, 0.5)


def test_c_not_applied_back_side_or_weak_shoulders(test_cfg):
    cfg = _cfg(test_cfg, c=True)
    for p in (_p(view="back"), _p(view="side"), _p(sh=0.4)):
        assert _state(cfg, p, "helmet", [HELMET_BOX]) == HAVE                    # như bản 4


def test_c_vote_not_neg_keeps_box(test_cfg):
    cfg = _cfg(test_cfg, c=True)
    thr = cfg["part_cls"]["thresholds"]["helmet"]
    unsure = (1 - thr["t_neg"] + thr["t_pos"]) / 2
    for ph in (unsure, 0.99):
        assert _state(cfg, _p(p_helmet=ph), "helmet", [HELMET_BOX]) == HAVE


def test_c_only_helmet_changes(test_cfg):
    p = _p(p_goggles=0.02)
    a, b = _cfg(test_cfg), _cfg(test_cfg, c=True)
    for name in ("vest", "gloves", "goggles", "boots"):
        assert _state(a, p, name, [HELMET_BOX]) == _state(b, p, name, [HELMET_BOX])


# ------------------------------------------------------------ C2 (hai mức, t_veto thử 0,8)

def test_c2_two_levels_with_detector_box(test_cfg):
    """Nhìn thẳng + hộp detector: rất chắc không mũ -> Thiếu; phân vân -> Chưa xác định; không neg -> Có."""
    cfg = _cfg(test_cfg, c=True, t_veto=0.8)
    assert cfg["part_cls"]["thresholds"]["helmet"]["t_neg"] == 0.5
    assert _state(cfg, _p(p_helmet=0.10), "helmet", [HELMET_BOX]) == MISSING     # 1 - p = 0,90 >= 0,8 (đầu trọc)
    assert _state(cfg, _p(p_helmet=0.19), "helmet", [HELMET_BOX]) == MISSING     # 0,81
    assert _state(cfg, _p(p_helmet=0.45), "helmet", [HELMET_BOX]) == UNKNOWN     # 0,55: phân vân (mũ thật ảnh xấu)
    assert _state(cfg, _p(p_helmet=0.60), "helmet", [HELMET_BOX]) == HAVE        # 0,40 < t_neg: không neg
    assert _state(_cfg(test_cfg), _p(p_helmet=0.45), "helmet", [HELMET_BOX]) == HAVE   # bản 4: Có


def test_c2_no_box_unchanged(test_cfg):
    """Không có hộp detector: như hiện tại (phiếu neg + nhìn rõ -> Thiếu)."""
    for ph in (0.10, 0.45):
        assert _state(_cfg(test_cfg, c=True, t_veto=0.8), _p(p_helmet=ph), "helmet") ==             _state(_cfg(test_cfg), _p(p_helmet=ph), "helmet")


def test_c2_not_frontal_or_back_unchanged(test_cfg):
    cfg = _cfg(test_cfg, c=True, d=True, t_veto=0.8)
    for p in (_p(p_helmet=0.45, face=0.75), _p(view="back", sh=0.9, face=0.3, p_helmet=0.45),
              _p(view="side", p_helmet=0.10)):
        assert _state(cfg, p, "helmet", [HELMET_BOX]) == HAVE


def test_c2_only_helmet_changes(test_cfg):
    p = _p(p_helmet=0.45, p_goggles=0.02)
    a, b = _cfg(test_cfg), _cfg(test_cfg, c=True, t_veto=0.8)
    for name in ("vest", "gloves", "goggles", "boots"):
        assert _state(a, p, name, [HELMET_BOX]) == _state(b, p, name, [HELMET_BOX])


# ------------------------------------------------------------ D

def test_d_back_low_conf_shoulders_goggles_unknown(test_cfg):
    """Ca video16: vai ngược nhưng 0,45 (< 0,5 của cổng cũ), pose đoán mặt (mắt 0,58) -> D: kính Chưa xác định."""
    p = _p(view="back", sh=0.45, face=0.89, eyes=0.58, p_goggles=0.04)
    assert _state(_cfg(test_cfg), p, "goggles") == MISSING                       # bản 4: Thiếu sai
    assert _state(_cfg(test_cfg, d=True), p, "goggles") == UNKNOWN


def test_d_back_helmet_no_box_unknown_with_box_have(test_cfg):
    """Ca video17: quay lưng, detector không thấy mũ, bộ phân loại chắc không mũ -> D: Chưa xác định; có hộp: Có."""
    p = _p(view="back", sh=0.99, face=0.04, ears=0.85)                           # mặt 0,01-0,04, tai 0,84-0,87
    assert _state(_cfg(test_cfg), p, "helmet") == MISSING
    assert _state(_cfg(test_cfg, d=True), p, "helmet") == UNKNOWN
    assert _state(_cfg(test_cfg, d=True), p, "helmet", [HELMET_BOX]) == HAVE


def test_d_strong_face_is_not_back(test_cfg):
    p = _p(view="back", sh=0.9, face=0.95, p_goggles=0.04)                       # mũi, hai mắt >= 0,9
    assert not back_view_now(p.extra["kps"], p.xyxy, BV)
    assert _state(_cfg(test_cfg, d=True), p, "goggles") == _state(_cfg(test_cfg), p, "goggles")


def test_d_min_sep_and_low_conf_not_back(test_cfg):
    close = _p(view="back", sh=0.9, face=0.3, sep=5.0)                           # 5 px < 5% x 200
    weak = _p(view="back", sh=0.2, face=0.3)                                     # vai < 0,3
    assert not back_view_now(close.extra["kps"], close.xyxy, BV)
    assert not back_view_now(weak.extra["kps"], weak.xyxy, BV)
    assert back_view_now(_p(view="back", sh=0.3, face=0.3).extra["kps"], close.xyxy, BV)   # đúng biên 0,3


def test_d_hold_over_time(test_cfg):
    """Quay lưng ở t = 0; t = 0,5 s không còn dấu hiệu nhưng vẫn trong hold_s -> vẫn coi là quay lưng; t = 1,6 s hết."""
    cfg = _cfg(test_cfg, d=True)
    comp = Compliance(cfg)
    back = _p(view="back", sh=0.9, face=0.3, p_goggles=0.04)
    front = _p(view="front", sh=0.9, face=0.95, p_goggles=0.04)
    assert _state(cfg, back, "goggles", t=0.0, comp=comp) == UNKNOWN
    assert _state(cfg, front, "goggles", t=0.5, comp=comp) == UNKNOWN
    assert _state(cfg, front, "goggles", t=1.6, comp=comp) == MISSING
    assert _state(cfg, front, "goggles", t=None, comp=Compliance(cfg)) == MISSING   # không có thời gian: không giữ


def test_d_other_ppe_unchanged(test_cfg):
    p = _p(view="back", sh=0.45, face=0.3)
    a, b = _cfg(test_cfg), _cfg(test_cfg, d=True)
    for name in ("vest", "gloves", "boots"):
        assert _state(a, p, name) == _state(b, p, name)


def test_d_blocks_c_when_back(test_cfg):
    """Quay lưng (theo D, kể cả giữ thời gian) thì C không phủ quyết."""
    cfg = _cfg(test_cfg, c=True, d=True)
    comp = Compliance(cfg)
    assert _state(cfg, _p(view="back", sh=0.9, face=0.3), "helmet", [HELMET_BOX], t=0.0, comp=comp) == HAVE
    assert _state(cfg, _p(), "helmet", [HELMET_BOX], t=0.5, comp=comp) == HAVE   # còn trong hold_s
    assert _state(cfg, _p(), "helmet", [HELMET_BOX], t=1.6, comp=comp) == MISSING


# ------------------------------------------------------------ cấu hình

def test_no_keys_same_as_v4(test_cfg):
    cfg = _cfg(test_cfg)
    comp = Compliance(cfg)
    assert comp.veto_frontal == {} and comp.back_cfg is None


def test_current_config_d_and_c2_on():
    """Cấu hình đang dùng (16/11/2026, người dùng duyệt): D bật đúng quy ước; C2 bật với tham số chọn trên val."""
    cfg = load_config()
    assert cfg["part_cls"]["veto_frontal"] == {"helmet": {"face_conf": 0.7, "t_veto": 0.7}}
    assert cfg["compliance"]["back_view"] == BV


def test_pose_disabled_turns_d_off(test_cfg):
    cfg = copy.deepcopy(_cfg(test_cfg, d=True))
    cfg["pose"]["enabled"] = False
    assert Compliance(cfg).back_cfg is None
