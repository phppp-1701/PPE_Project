"""Bước B: vùng thân theo khung xương cho áo (association.torso_pose). B lần 1 đã TẮT trong cấu hình (15/11/2026);
test bật lại bằng tham số B lần 1 lưu ở association.torso_pose_b1 của configs/pipeline.yaml (đã chọn trên val) để
giữ kiểm tra cho code; vùng cũ, max_distance là giá trị thử của test_cfg."""

import copy

from conftest import det, person

from ppe.association import Associator, torso_pose_box

VEST, HELMET = 2, 1


def _cfg(test_cfg, torso=True):
    cfg = copy.deepcopy(test_cfg)
    cfg["pose"].update(enabled=True, wrist_conf=0.5, rho_x=0.2, rho_y=0.1)
    assert cfg["association"].get("torso_pose_b1"), "configs/pipeline.yaml phải lưu association.torso_pose_b1"
    cfg["association"].pop("torso_pose", None)
    if torso:
        cfg["association"]["torso_pose"] = dict(cfg["association"]["torso_pose_b1"])
    return cfg


def _kps(shoulders, hips=None, sh_conf=0.9, hip_conf=0.9):
    k = [(0.0, 0.0, 0.0)] * 17
    k[5], k[6] = (*shoulders[0], sh_conf), (*shoulders[1], sh_conf)
    if hips:
        k[11], k[12] = (*hips[0], hip_conf), (*hips[1], hip_conf)
    return k


def _close_up(sh_conf=0.9, kps=True):
    """Người sát camera bị cắt ở ngực: hộp người từ đầu tới mép dưới khung (y = 1000), không thấy hông."""
    p = person(1, 100, 0, 900, 1000)
    if kps:
        p.extra["kps"] = _kps(((300.0, 450.0), (700.0, 450.0)), sh_conf=sh_conf)     # sw = 400
    return p


def _vest_low():
    return det(VEST, 250, 550, 750, 1000)        # tâm (500, 775): y tương đối 0,775, ngoài vùng torso cũ (y1 0,7)


def test_chest_cut_vest_assigned_only_with_torso_pose(test_cfg):
    old = Associator(_cfg(test_cfg, torso=False))([_close_up()], [_vest_low()])
    assert not old.owned and old.rejected[0][2] == "outside"
    new = Associator(_cfg(test_cfg))([_close_up()], [_vest_low()])
    assert len(new.owned[1][("vest", None)]) == 1


def test_region_clipped_to_person_box(test_cfg):
    tp = _cfg(test_cfg)["association"]["torso_pose"]
    r = torso_pose_box(_close_up(), tp)
    assert r[0] >= 100 and r[2] <= 900 and r[3] <= 1000         # phần thật sự thấy trong khung (hộp người)
    assert abs(r[1] - (450 - tp["ky0"] * 400)) < 1e-6


def test_missing_or_low_conf_shoulders_fall_back_to_old_region(test_cfg):
    cfg = _cfg(test_cfg)
    for p in (_close_up(sh_conf=0.3), _close_up(kps=False)):
        res = Associator(cfg)([p], [_vest_low()])
        assert not res.owned and res.rejected[0][2] == "outside"   # như bản 4
    p = _close_up()
    p.extra["kps"][6] = (700.0, 450.0, 0.2)                        # một vai dưới ngưỡng
    assert torso_pose_box(p, cfg["association"]["torso_pose"]) is None


def test_hips_visible_bound_bottom(test_cfg):
    """Thấy hông: đáy vùng = hông + kh * sw; áo nằm thấp hơn nhiều thì không thành ứng viên qua vùng khung xương."""
    cfg = _cfg(test_cfg)
    tp = cfg["association"]["torso_pose"]
    p = person(1, 100, 0, 900, 2000)
    p.extra["kps"] = _kps(((300.0, 450.0), (700.0, 450.0)), hips=((350.0, 1000.0), (650.0, 1000.0)))
    r = torso_pose_box(p, tp)
    assert abs(r[3] - (1000 + tp["kh"] * 400)) < 1e-6
    far = det(VEST, 300, 1700, 700, 1900)                          # tâm y 1800: dưới đáy vùng, ngoài vùng cũ
    res = Associator(cfg)([p], [far])
    assert not res.owned


def test_two_people_side_by_side_no_cross_assignment(test_cfg):
    cfg = _cfg(test_cfg)
    a, b = person(1, 0, 0, 500, 1000), person(2, 500, 0, 1000, 1000)
    a.extra["kps"] = _kps(((150.0, 450.0), (350.0, 450.0)))
    b.extra["kps"] = _kps(((650.0, 450.0), (850.0, 450.0)))
    res = Associator(cfg)([a, b], [det(VEST, 600, 550, 900, 1000)])   # áo của người 2, tâm (750, 775)
    assert res.owned[2][("vest", None)] and not res.owned.get(1, {}).get(("vest", None))
    mid = Associator(cfg)([a, b], [det(VEST, 400, 550, 600, 1000)])   # áo ở giữa hai người: tranh chấp, không gán
    assert not any(mid.owned[t].get(("vest", None)) for t in (1, 2))
    assert mid.rejected[0][2] == "contested"


def test_only_vest_uses_torso_pose(test_cfg):
    """Mũ, găng không dùng vùng thân: cùng vị trí, kết quả như khi không có torso_pose."""
    helmet = det(HELMET, 250, 550, 750, 1000)
    old = Associator(_cfg(test_cfg, torso=False))([_close_up()], [helmet])
    new = Associator(_cfg(test_cfg))([_close_up()], [helmet])
    assert dict(old.owned) == dict(new.owned) and [r[2] for r in old.rejected] == [r[2] for r in new.rejected]


def test_without_torso_pose_section_behaves_as_before(test_cfg):
    cfg = _cfg(test_cfg, torso=False)
    assert Associator(cfg).torso_pose is None


def test_current_config_has_torso_pose_off():
    """Cấu hình đang dùng: B lần 1 tắt (không có khóa torso_pose) => Associator ghép áo như bản 4."""
    from ppe import load_config
    cfg = load_config()
    assert "torso_pose" not in cfg["association"]
    cfg["pose"]["enabled"] = True
    assert Associator(cfg).torso_pose is None
