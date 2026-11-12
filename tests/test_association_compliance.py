"""Gán PPE theo vùng cơ thể và ba trạng thái (spec 5.2, 5.3)."""

from conftest import det, person

from ppe import HAVE, MISSING, UNKNOWN
from ppe.association import Associator
from ppe.compliance import Compliance

FRAME = (1000, 1000, 3)


def run(cfg, tracks, dets):
    a = Associator(cfg)(tracks, dets)
    return a, Compliance(cfg)(tracks, a, FRAME)


def test_one_person_full_ppe(test_cfg):
    p = person(1, 100, 100, 300, 700)          # rộng 200, cao 600
    dets = [det(1, 170, 100, 230, 160),        # mũ ở đầu
            det(2, 150, 300, 250, 450),        # áo ở thân
            det(3, 90, 450, 130, 500),         # găng trái
            det(3, 270, 450, 310, 500)]        # găng phải
    a, s = run(test_cfg, [p], dets)
    assert {k: v["state"] for k, v in s[1].items()} == {"helmet": HAVE, "vest": HAVE, "gloves": HAVE}


def test_missing_helmet_when_head_visible(test_cfg):
    p = person(1, 100, 100, 300, 700)
    _, s = run(test_cfg, [p], [det(2, 150, 300, 250, 450)])
    assert s[1]["helmet"]["state"] == MISSING
    assert s[1]["gloves"]["state"] == MISSING        # tay nhìn rõ, không có găng


def test_one_glove_is_not_both_hands(test_cfg):
    p = person(1, 100, 100, 300, 700)
    _, s = run(test_cfg, [p], [det(3, 90, 450, 130, 500), det(3, 100, 520, 140, 560)])   # hai găng cùng tay trái
    assert s[1]["gloves"]["sides"]["left"][0] == HAVE
    assert s[1]["gloves"]["sides"]["right"][0] == MISSING
    assert s[1]["gloves"]["state"] == MISSING


def test_head_outside_frame_is_unknown(test_cfg):
    p = person(1, 100, -200, 300, 400)          # đầu nằm ngoài ảnh
    _, s = run(test_cfg, [p], [])
    assert s[1]["helmet"]["state"] == UNKNOWN


def test_low_confidence_person_is_unknown(test_cfg):
    p = person(1, 100, 100, 300, 700, confident=False)
    _, s = run(test_cfg, [p], [])
    assert all(v["state"] == UNKNOWN for v in s[1].values())


def test_contested_helmet_not_assigned(test_cfg):
    a = person(1, 100, 100, 300, 700)
    b = person(2, 200, 100, 400, 700)           # hai người đứng sát, vùng đầu chồng nhau
    assoc, s = run(test_cfg, [a, b], [det(1, 230, 110, 270, 150)])
    assert not assoc.owned
    assert assoc.rejected[0][2] == "contested"
    # Bị tranh chấp -> không được kết luận Thiếu cho ai.
    assert s[1]["helmet"]["state"] != MISSING and s[2]["helmet"]["state"] != MISSING


def test_far_ppe_rejected(test_cfg):
    test_cfg["association"]["max_distance"]["helmet"] = 0.01
    a, _ = run(test_cfg, [person(1, 100, 100, 300, 700)], [det(1, 100, 100, 140, 140)])
    assert a.rejected[0][2] == "far"


def pose_cfg(cfg):
    cfg["pose"].update(enabled=True, wrist_conf=0.5, rho_x=0.2, rho_y=0.1)
    return cfg


def with_wrists(left, right):
    p = person(1, 100, 100, 300, 700)          # rộng 200, cao 600: bán trục elip 40 và 60 px
    p.extra["wrists"] = {"left": left, "right": right}
    return p


def test_pose_low_wrist_conf_is_unknown_not_missing(test_cfg):
    """Không thấy cổ tay đạt ngưỡng thì không được suy ra Thiếu găng."""
    _, s = run(pose_cfg(test_cfg), [with_wrists((120, 500, 0.2), (280, 500, 0.2))], [])
    assert s[1]["gloves"]["state"] == UNKNOWN


def test_pose_no_wrists_is_unknown(test_cfg):
    _, s = run(pose_cfg(test_cfg), [person(1, 100, 100, 300, 700)], [])
    assert s[1]["gloves"]["state"] == UNKNOWN


def test_pose_visible_hand_without_glove_is_missing(test_cfg):
    _, s = run(pose_cfg(test_cfg), [with_wrists((120, 500, 0.9), (280, 500, 0.2))], [])
    assert s[1]["gloves"]["state"] == MISSING


def test_pose_both_gloves_inside_ellipse(test_cfg):
    dets = [det(3, 110, 490, 130, 510), det(3, 270, 490, 290, 510)]
    _, s = run(pose_cfg(test_cfg), [with_wrists((120, 500, 0.9), (280, 500, 0.9))], dets)
    assert s[1]["gloves"]["state"] == HAVE


def test_pose_glove_outside_ellipse_not_assigned(test_cfg):
    a, s = run(pose_cfg(test_cfg), [with_wrists((120, 300, 0.9), (280, 300, 0.9))], [det(3, 110, 490, 130, 510)])
    assert a.rejected[0][2] == "outside" and s[1]["gloves"]["state"] == MISSING


def test_pose_clasped_hands_single_glove_box_marks_other_wrist_contested(test_cfg):
    """Khi hai cổ tay sát nhau (chắp tay), 1 khung găng tay nhỏ nằm trong cả 2 elip:
    tay gần hơn nhận găng, tay còn lại được đánh dấu contested -> UNKNOWN thay vì báo sai MISSING."""
    p = with_wrists((195, 500, 0.9), (215, 500, 0.9))
    _, s = run(pose_cfg(test_cfg), [p], [det(3, 190, 490, 210, 510)])
    assert s[1]["gloves"]["sides"]["left"][0] == HAVE
    assert s[1]["gloves"]["sides"]["right"][0] == UNKNOWN
    assert s[1]["gloves"]["state"] == UNKNOWN


def test_pose_clasped_hands_wide_glove_box_covers_both_wrists(test_cfg):
    """Khi hai cổ tay chắp sát nhau và YOLO gom thành 1 khung găng tay rộng trùm qua cả 2 cổ tay:
    cả 2 tay đều được tính là HAVE."""
    p = with_wrists((195, 500, 0.9), (215, 500, 0.9))
    _, s = run(pose_cfg(test_cfg), [p], [det(3, 180, 485, 230, 515)])
    assert s[1]["gloves"]["sides"]["left"][0] == HAVE
    assert s[1]["gloves"]["sides"]["right"][0] == HAVE
    assert s[1]["gloves"]["state"] == HAVE


def test_six_class_goggles_and_boots_truncated_feet(test_cfg):
    from ppe import load_config
    full = load_config()
    test_cfg["ppe"] = full["ppe"]
    test_cfg["required_ppe"] = full["required_ppe"]
    # Người 1 đứng trọn trong khung hình (y2=700 < 1000), đeo kính (cls 4) và đi ủng (cls 5)
    p1 = person(1, 100, 100, 300, 700)
    dets = [
        det(4, 170, 140, 230, 180),  # kính ở vùng đầu
        det(5, 120, 620, 180, 695),  # ủng trái
        det(5, 220, 620, 280, 695),  # ủng phải
    ]
    _, s1 = run(test_cfg, [p1], dets)
    assert s1[1]["goggles"]["state"] == HAVE
    assert s1[1]["boots"]["state"] == HAVE

    # Người 2 bị cắt ngang chân ở đáy khung hình (y2=1000), vùng feet (y1=1.02) tràn ra ngoài -> UNKNOWN
    p2 = person(2, 400, 400, 600, 1000)
    _, s2 = run(test_cfg, [p2], [])
    assert s2[2]["boots"]["state"] == UNKNOWN


def test_bending_person_adaptive_distance_accepts_displaced_ppe(test_cfg):
    # Người cúi gập người (rộng 200, cao 400 -> tỉ lệ aspect = 2.0 < 2.8)
    p = person(1, 100, 100, 300, 500)
    # Đặt max_distance chuẩn = 0.10
    test_cfg["association"]["max_distance"]["vest"] = 0.10
    # Tâm áo ở y = 340 -> khoảng cách chuẩn hóa tới tâm torso (290) là 0.125 > 0.10
    # Nếu không có hệ số nới rộng, áo sẽ bị từ chối do "far"
    # Nhờ nới rộng theo tư thế cúi (0.10 * (1 + 0.5*(2.8-2.0)) = 0.14 > 0.125), áo được gán cho người
    vest_det = det(2, 160, 310, 240, 370)
    a, s = run(test_cfg, [p], [vest_det])
    assert a.owned[1][("vest", None)]
    assert s[1]["vest"]["state"] == HAVE


def test_trench_buried_feet_marked_unknown_via_ankles(test_cfg):
    from ppe import load_config
    full = load_config()
    test_cfg["ppe"] = full["ppe"]
    test_cfg["required_ppe"] = full["required_ppe"]
    # Người đứng trong rãnh / hố (y2=700 < 1000, không chạm đáy khung hình)
    p = person(1, 100, 100, 300, 700)
    # Cổ chân ở rất gần đáy bounding box (cách đáy 15px < 0.065 * 600 = 39px)
    p.extra["ankles"] = {"max_y": 688.0, "conf": 0.85}
    _, s = run(test_cfg, [p], [])
    # Dù không chạm đáy ảnh nhưng cổ chân sát đáy hộp người -> chân bị vùi/khuất rãnh -> UNKNOWN
    assert s[1]["boots"]["state"] == UNKNOWN

