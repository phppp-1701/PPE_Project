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
