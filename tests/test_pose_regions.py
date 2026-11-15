"""Bước F (kế hoạch ppe6 mục F, 16/11/2026): vùng theo khung xương. F1 kính theo mắt, F2 áo theo vai với edge_frac,
F3 găng dự phòng theo vùng tay. Tham số ở đây là GIÁ TRỊ THỬ (chưa chọn trên val); vùng cũ, max_distance của test_cfg."""

import copy

from conftest import det, person

from ppe import HAVE, MISSING, UNKNOWN
from ppe.association import Associator, eye_anchor_distance
from ppe.compliance import Compliance

GOG, GLV, VEST = 4, 3, 2
FRAME = (1000, 1600, 3)


def _cfg(test_cfg, f1=False, f2=None, f3=False):
    cfg = copy.deepcopy(test_cfg)
    cfg["pose"].update(enabled=True, wrist_conf=0.8, rho_x=0.2, rho_y=0.1)
    from ppe import load_config
    full = load_config()
    cfg["ppe"] = full["ppe"]
    cfg["association"]["regions"]["head"] = {"x0": 0.0, "x1": 1.0, "y0": 0.0, "y1": 0.3}
    for k in ("eye_anchor", "gloves_region_fallback", "torso_strict", "torso_pose"):
        cfg["association"].pop(k, None)
    if f1:
        cfg["association"]["eye_anchor"] = {"kp_conf": 0.5, "k_eye": 0.5}
    if f2 is not None:
        cfg["association"]["torso_strict"] = dict(kp_conf=0.5, kx=1.0, ky0=-0.2, kh=0.15, slope_max_deg=30.0, s_min=0.8,
                                                  edge_frac=f2)
    if f3:
        cfg["association"]["gloves_region_fallback"] = True
    return cfg


def _kps(eyes=((450.0, 500.0), (550.0, 500.0)), eye_conf=0.9, wrists_conf=0.3, shoulders=((300.0, 650.0), (700.0, 650.0))):
    k = [(0.0, 0.0, 0.0)] * 17
    k[1], k[2] = (*eyes[0], eye_conf), (*eyes[1], eye_conf)
    k[5], k[6] = (*shoulders[0], 0.9), (*shoulders[1], 0.9)
    k[9], k[10] = (150.0, 900.0, wrists_conf), (850.0, 900.0, wrists_conf)
    return k


def _close_up(**kw):
    """Người sát camera bị cắt: hộp (100, 0, 900, 1000); mắt ở y 500 (tỉ lệ 0,5, dưới vùng đầu cũ y1 0,3)."""
    p = person(1, 100, 0, 900, 1000)
    p.extra["kps"] = _kps(**kw)
    k = p.extra["kps"]
    p.extra["wrists"] = {"left": k[9], "right": k[10]}
    return p


def _owner(res, name, tid=1):
    return [s for (n, s), ds in res.owned.get(tid, {}).items() if n == name and ds]


# ------------------------------------------------------------ F1 kính theo mắt

def test_f1_goggles_on_eyes_assigned_only_with_eye_anchor(test_cfg):
    g = det(GOG, 440, 470, 560, 530)                                             # tâm (500, 500) = trung điểm mắt
    old = Associator(_cfg(test_cfg))([_close_up()], [g], FRAME)
    assert not _owner(old, "goggles") and old.rejected[0][2] == "outside"
    new = Associator(_cfg(test_cfg, f1=True))([_close_up()], [g], FRAME)
    assert _owner(new, "goggles") == [None]


def test_f1_far_from_eyes_or_eyes_weak_not_assigned(test_cfg):
    far = det(GOG, 440, 540, 560, 600)                                           # tâm cách mắt 70 px > 0,5 x 100
    assert not _owner(Associator(_cfg(test_cfg, f1=True))([_close_up()], [far], FRAME), "goggles")
    g = det(GOG, 440, 470, 560, 530)
    weak = Associator(_cfg(test_cfg, f1=True))([_close_up(eye_conf=0.3)], [g], FRAME)
    assert not _owner(weak, "goggles")
    p = _close_up()
    assert eye_anchor_distance(p, (500, 500), {"kp_conf": 0.5, "k_eye": 0.5}) == 0.0
    assert eye_anchor_distance(p, (500, 560), {"kp_conf": 0.5, "k_eye": 0.5}) is None


def test_f1_only_goggles_changes(test_cfg):
    h = det(1, 440, 470, 560, 530)                                               # mũ ở cùng chỗ: không dùng mắt
    a = Associator(_cfg(test_cfg))([_close_up()], [h], FRAME)
    b = Associator(_cfg(test_cfg, f1=True))([_close_up()], [h], FRAME)
    assert _owner(a, "helmet") == _owner(b, "helmet")


# ------------------------------------------------------------ F3 găng dự phòng

def test_f3_wrist_invalid_glove_in_hand_region_assigned_and_have(test_cfg):
    g = det(GLV, 120, 860, 200, 940)                                             # tay trái, cổ tay 0,3 < 0,8
    base, f3 = _cfg(test_cfg), _cfg(test_cfg, f3=True)
    a0 = Associator(base)([_close_up()], [g], FRAME)
    assert not _owner(a0, "gloves")
    s0 = Compliance(base)([_close_up()], a0, FRAME)
    assert s0[1]["gloves"]["sides"]["left"][0] == UNKNOWN
    p = _close_up()
    a1 = Associator(f3)([p], [g], FRAME)
    assert _owner(a1, "gloves") == ["left"]
    s1 = Compliance(f3)([p], a1, FRAME)
    assert s1[1]["gloves"]["sides"]["left"][0] == HAVE


def test_f3_no_box_never_missing(test_cfg):
    f3 = _cfg(test_cfg, f3=True)
    p = _close_up()
    s = Compliance(f3)([p], Associator(f3)([p], [], FRAME), FRAME)
    assert {st for st, _ in s[1]["gloves"]["sides"].values()} == {UNKNOWN}
    assert s[1]["gloves"]["state"] != MISSING


def test_f3_valid_wrist_uses_ellipse_as_before(test_cfg):
    g = det(GLV, 120, 860, 200, 940)
    a = Associator(_cfg(test_cfg))([_close_up(wrists_conf=0.9)], [g], FRAME)
    b = Associator(_cfg(test_cfg, f3=True))([_close_up(wrists_conf=0.9)], [g], FRAME)
    assert _owner(a, "gloves") == _owner(b, "gloves")


# ------------------------------------------------------------ F2 edge_frac

def test_f2_edge_frac_scales_with_frame(test_cfg):
    p = person(1, 100, 0, 900, 950)                                              # đáy cách mép dưới 50 px = 5% khung
    p.extra["kps"] = _kps(shoulders=((300.0, 450.0), (700.0, 450.0)))
    v = det(VEST, 250, 550, 750, 950)                                            # tâm y 750: dưới vùng thân cũ (0,7 x 950)
    assert _owner(Associator(_cfg(test_cfg, f2=0.10))([p], [v], FRAME), "vest") == [None]
    assert not _owner(Associator(_cfg(test_cfg, f2=0.01))([p], [v], FRAME), "vest")
