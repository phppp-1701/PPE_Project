"""Bước B2: vùng thân theo khung xương bản chặt cho áo (association.torso_strict, kế hoạch ppe6 mục B2).

Tham số TS dưới đây là GIÁ TRỊ THỬ để kiểm logic (như test_cfg), KHÔNG phải tham số hệ thống: tham số thật chọn trên
val bằng 05a --torso-strict, chưa chạy. Vùng cũ (torso x 0,2-0,8, y 0,25-0,7), max_distance là giá trị thử của test_cfg.
"""

import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from conftest import det, person

from ppe import load_config
from ppe.association import Associator, region_box, shoulder_geometry, torso_strict_box

VEST, HELMET, GLOVES = 2, 1, 3
TS = dict(kp_conf=0.5, kx=1.0, ky0=-0.2, kh=0.15, slope_max_deg=30.0, s_min=0.8, edge_px=4)
FRAME = (1000, 1600, 3)          # H = 1000: người có y2 = 1000 chạm mép dưới


def _cfg(test_cfg, strict=True, **over):
    cfg = copy.deepcopy(test_cfg)
    cfg["pose"].update(enabled=True, wrist_conf=0.5, rho_x=0.2, rho_y=0.1)
    cfg["association"].pop("torso_pose", None)
    if strict:
        cfg["association"]["torso_strict"] = {**TS, **over}
    return cfg


def _kps(shoulders, hips=None, sh_conf=0.9, hip_conf=0.9):
    k = [(0.0, 0.0, 0.0)] * 17
    k[5], k[6] = (*shoulders[0], sh_conf), (*shoulders[1], sh_conf)
    if hips:
        k[11], k[12] = (*hips[0], hip_conf), (*hips[1], hip_conf)
    return k


def _close_up(shoulders=((300.0, 450.0), (700.0, 450.0)), **kw):
    """Người sát camera bị cắt ở ngực: hộp (100, 0, 900, 1000) tới mép dưới khung, sw = 400."""
    p = person(1, 100, 0, 900, 1000)
    p.extra["kps"] = _kps(shoulders, **kw)
    return p


def _vest_low():
    return det(VEST, 250, 550, 750, 1000)        # tâm (500, 775): dưới vùng cũ (y1 = 700), rộng 500 >= 0,8 * 400


def _vest_of(res, tid):
    return res.owned.get(tid, {}).get(("vest", None), [])


def _same(a, b):
    """Hai kết quả ghép giống nhau: cùng PPE của từng người, cùng tranh chấp, cùng lý do loại."""
    own = lambda r: {t: {k: [id(d) for d in v] for k, v in items.items() if v} for t, items in r.owned.items()}
    con = lambda r: {t: s for t, s in r.contested.items() if s}
    rej = lambda r: [(n, id(d), why) for n, d, why, _ in r.rejected]
    return own(a) == own(b) and con(a) == con(b) and rej(a) == rej(b)


# ------------------------------------------------------------ G4 và vùng R

def test_chest_cut_touching_bottom_vest_assigned(test_cfg):
    old = Associator(_cfg(test_cfg, strict=False))([_close_up()], [_vest_low()], FRAME)
    assert not _vest_of(old, 1) and old.rejected[0][2] == "outside"            # bản 4: loại "outside"
    new = Associator(_cfg(test_cfg))([_close_up()], [_vest_low()], FRAME)
    assert len(_vest_of(new, 1)) == 1


def test_not_touching_bottom_behaves_as_v4(test_cfg):
    """G4: đáy hộp người (1000) cách mép dưới khung (1200) quá edge_px -> không mở rộng."""
    res = Associator(_cfg(test_cfg))([_close_up()], [_vest_low()], (1200, 1600, 3))
    assert not _vest_of(res, 1) and res.rejected[0][2] == "outside"
    edge = Associator(_cfg(test_cfg))([_close_up()], [_vest_low()], (1000 + TS["edge_px"], 1600, 3))
    assert len(_vest_of(edge, 1)) == 1                                           # đúng biên edge_px vẫn tính chạm


def test_region_never_wider_than_old_region(test_cfg):
    cfg = _cfg(test_cfg)
    p = _close_up()
    old = region_box(p.xyxy, cfg["association"]["regions"]["torso"])
    r, sw = torso_strict_box(p, cfg["association"]["torso_strict"], old, FRAME)
    assert r[0] >= old[0] and r[2] <= old[2] and sw == pytest.approx(400)
    assert r[1] == pytest.approx(450 - TS["ky0"] * 400) and r[3] == pytest.approx(1000)   # tới đáy hộp người


def test_vest_outside_old_columns_not_assigned_but_b1_would(test_cfg):
    """Tâm áo x = 800 ngoài vùng cũ (x2 = 740) nhưng trong dải kx của B1: B2 không ghép, B1 có."""
    side_vest = det(VEST, 700, 550, 900, 1000)
    b2 = Associator(_cfg(test_cfg))([_close_up()], [side_vest], FRAME)
    assert not _vest_of(b2, 1) and b2.rejected[0][2] == "outside"
    cfg_b1 = _cfg(test_cfg, strict=False)
    cfg_b1["association"]["torso_pose"] = dict(load_config()["association"]["torso_pose_b1"])
    b1 = Associator(cfg_b1)([_close_up()], [side_vest])
    assert len(_vest_of(b1, 1)) == 1


def test_hips_visible_bound_bottom(test_cfg):
    cfg = _cfg(test_cfg)
    p = _close_up(hips=((350.0, 800.0), (650.0, 800.0)))
    old = region_box(p.xyxy, cfg["association"]["regions"]["torso"])
    r, _ = torso_strict_box(p, cfg["association"]["torso_strict"], old, FRAME)
    assert r[3] == pytest.approx(800 + TS["kh"] * 400)
    low = det(VEST, 300, 820, 700, 1000)                                         # tâm y 910 > 860: ngoài R
    assert not _vest_of(Associator(cfg)([p], [low], FRAME), 1)


# ------------------------------------------------------------ G5 cỡ áo

def test_g5_narrow_vest_below_old_region_rejected(test_cfg):
    narrow = det(VEST, 450, 600, 550, 950)                                       # rộng 100 < 0,8 * 400
    assert not _vest_of(Associator(_cfg(test_cfg))([_close_up()], [narrow], FRAME), 1)
    no_g5 = Associator(_cfg(test_cfg, s_min=0.0))([_close_up()], [narrow], FRAME)
    assert len(_vest_of(no_g5, 1)) == 1                                          # chỉ G5 chặn


def test_g5_not_applied_inside_old_region(test_cfg):
    """Áo hẹp nhưng tâm trong vùng cũ: ghép như bản 4, G5 không xét."""
    narrow_in_old = det(VEST, 450, 300, 550, 650)
    old = Associator(_cfg(test_cfg, strict=False))([_close_up()], [narrow_in_old], FRAME)
    new = Associator(_cfg(test_cfg))([_close_up()], [narrow_in_old], FRAME)
    assert len(_vest_of(old, 1)) == 1 and len(_vest_of(new, 1)) == 1


# ------------------------------------------------------------ G2, G3: pose bất thường -> như bản 4

@pytest.mark.parametrize("make", [
    lambda: person(1, 100, 0, 900, 1000),                                        # không có kps
    lambda: _close_up(sh_conf=0.3),                                              # G2 vai dưới ngưỡng
    lambda: _close_up(shoulders=((300.0, 450.0), (950.0, 450.0))),               # G3a vai ngoài hộp người
    lambda: _close_up(shoulders=((300.0, 450.0), (700.0, 750.0))),               # G3b vai nghiêng 36,9° > 30°
    lambda: _close_up(hips=((350.0, 400.0), (650.0, 400.0))),                    # G3c hông cao hơn vai
    lambda: _close_up(shoulders=((500.0, 450.0), (500.4, 450.0))),               # G3d sw < 1 px
])
def test_abnormal_pose_falls_back_to_v4(test_cfg, make):
    p = make()
    cfg = _cfg(test_cfg)
    old = region_box(p.xyxy, cfg["association"]["regions"]["torso"])
    assert torso_strict_box(p, cfg["association"]["torso_strict"], old, FRAME) is None
    v = _vest_low()
    a = Associator(_cfg(test_cfg, strict=False))([p], [v], FRAME)
    b = Associator(cfg)([p], [v], FRAME)
    assert _same(a, b) and b.rejected[0][2] == "outside"


def test_one_shoulder_low_conf():
    p = _close_up()
    p.extra["kps"][6] = (700.0, 450.0, 0.2)
    assert shoulder_geometry(p, 0.5) is None


# ------------------------------------------------------------ hai người

def test_two_truncated_people_side_by_side(test_cfg):
    cfg = _cfg(test_cfg)
    a, b = person(1, 0, 0, 500, 1000), person(2, 500, 0, 1000, 1000)
    a.extra["kps"] = _kps(((150.0, 450.0), (350.0, 450.0)))
    b.extra["kps"] = _kps(((650.0, 450.0), (850.0, 450.0)))
    res = Associator(cfg)([a, b], [det(VEST, 600, 550, 900, 1000)], FRAME)     # áo người 2, tâm (750, 775)
    assert _vest_of(res, 2) and not _vest_of(res, 1)
    mid = Associator(cfg)([a, b], [det(VEST, 400, 550, 600, 1000)], FRAME)     # áo giữa: ngoài R của cả hai
    assert not _vest_of(mid, 1) and not _vest_of(mid, 2)


def test_two_overlapping_people_middle_vest_contested(test_cfg):
    cfg = _cfg(test_cfg)
    a, b = person(1, 0, 0, 600, 1000), person(2, 300, 0, 900, 1000)
    a.extra["kps"] = _kps(((200.0, 450.0), (400.0, 450.0)))
    b.extra["kps"] = _kps(((500.0, 450.0), (700.0, 450.0)))
    res = Associator(cfg)([a, b], [det(VEST, 360, 550, 540, 1000)], FRAME)     # tâm x 450 trong R của cả hai
    assert not _vest_of(res, 1) and not _vest_of(res, 2) and res.rejected[0][2] == "contested"


# ------------------------------------------------------------ G1, điều kiện kỹ thuật

def test_only_vest_uses_strict_region(test_cfg):
    """Mũ, găng ở cùng vị trí: kết quả như khi không có torso_strict."""
    for d in (det(HELMET, 250, 550, 750, 1000), det(GLOVES, 250, 550, 750, 1000)):
        a = Associator(_cfg(test_cfg, strict=False))([_close_up()], [d], FRAME)
        b = Associator(_cfg(test_cfg))([_close_up()], [d], FRAME)
        assert _same(a, b)


def test_no_frame_shape_behaves_as_v4(test_cfg):
    res = Associator(_cfg(test_cfg))([_close_up()], [_vest_low()])
    assert not _vest_of(res, 1) and res.rejected[0][2] == "outside"


def test_pose_disabled_turns_b2_off(test_cfg):
    cfg = _cfg(test_cfg)
    cfg["pose"]["enabled"] = False
    assert Associator(cfg).torso_strict is None


def test_without_torso_strict_section_is_none(test_cfg):
    assert Associator(_cfg(test_cfg, strict=False)).torso_strict is None


def test_current_config_b1_b2_off():
    """Cấu hình đang dùng: không có torso_pose, torso_strict; torso_pose_b1 không bật B1."""
    cfg = load_config()
    cfg["pose"]["enabled"] = True
    a = Associator(cfg)
    assert a.torso_pose is None and a.torso_strict is None


def test_b1_and_b2_together_rejected(test_cfg):
    cfg = _cfg(test_cfg)
    cfg["association"]["torso_pose"] = dict(load_config()["association"]["torso_pose_b1"])
    with pytest.raises(ValueError):
        Associator(cfg)


def test_random_scenes_not_touching_bottom_identical_to_v4(test_cfg):
    """Người không chạm mép dưới (G4 không qua): B2 cho kết quả ghép giống hệt bản 4 trên cảnh ngẫu nhiên."""
    rng = np.random.default_rng(0)
    v4, b2 = Associator(_cfg(test_cfg, strict=False)), Associator(_cfg(test_cfg))
    for _ in range(200):
        tracks = []
        for tid in range(int(rng.integers(1, 4))):
            x1, y1 = rng.uniform(0, 1000), rng.uniform(0, 300)
            w, h = rng.uniform(100, 500), rng.uniform(200, 600)
            p = person(tid + 1, x1, y1, x1 + w, y1 + h)
            mx, my = x1 + w / 2, y1 + 0.25 * h
            p.extra["kps"] = _kps(((mx - 0.2 * w, my), (mx + 0.2 * w, my)))
            tracks.append(p)
        dets = []
        for _ in range(int(rng.integers(1, 5))):
            cls = int(rng.choice([HELMET, VEST, GLOVES]))
            x, y = rng.uniform(0, 1400), rng.uniform(0, 900)
            dets.append(det(cls, x, y, x + rng.uniform(20, 300), y + rng.uniform(20, 300)))
        frame = (2000, 1600, 3)                                                  # mọi y2 <= 900 < 2000 - edge_px
        assert _same(v4(tracks, dets, frame), b2(tracks, dets, frame))


# ------------------------------------------------------------ V4: chia val theo nhóm (05a)

def _load_05a():
    path = Path(__file__).resolve().parents[1] / "scripts" / "05a_calibrate_val.py"
    spec = importlib.util.spec_from_file_location("calib05a", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _row(file, image, group, source, n_vest=1):
    return dict(file=file, image=image, group_id=group, source=source, n_vest=str(n_vest))


def test_unit_folds_keep_groups_and_number_blocks_together():
    m = _load_05a()
    rows = [
        _row("a1", "raw/x/image1005.jpg", "g1", "cons"), _row("a2", "raw/x/image1006.jpg", "g2", "cons"),
        _row("a3", "raw/x/image1049.jpg", "g3", "cons"),                         # cùng khối 1000-1049
        _row("b1", "raw/x/image1050.jpg", "g4", "cons"),                         # khối khác
        _row("c1", "raw/y/ppe_0020.jpg", "g5", "chv"), _row("c2", "raw/z/pexels-photo-77.jpeg", "g5", "sh17"),
        _row("d1", "raw/z/pexels-photo.jpg", "g6", "sh17"), _row("d2", "raw/z/other.jpg", "g6", "sh17"),
        _row("e1", "raw/z/pexels-photo-9000.jpeg", "g7", "sh17", 3),
    ]
    fold, units = m.unit_folds(rows, 50)
    assert set(fold.values()) <= {1, 2} and set(fold) == {r["file"] for r in rows}
    assert fold["a1"] == fold["a2"] == fold["a3"]                                # khối số
    assert fold["c1"] == fold["c2"]                                              # cùng group_id, khác nguồn
    assert fold["d1"] == fold["d2"]                                              # không có số: theo group_id
    by_group = {}
    for r in rows:
        by_group.setdefault(r["group_id"], set()).add(fold[r["file"]])
    assert all(len(v) == 1 for v in by_group.values())                           # không nhóm nào ở cả hai phần
    assert m.unit_folds(list(reversed(rows)), 50)[0] == fold                     # tất định, không phụ thuộc thứ tự
    assert sum(len(u["files"]) for u in units) == len(rows)
