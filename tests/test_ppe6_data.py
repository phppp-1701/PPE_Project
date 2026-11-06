"""Kiểm tra logic dữ liệu 6 lớp: quyết định người thắng agent, rò rỉ, nhãn, nhập CVAT."""

import numpy as np
import pytest

from ppe.ppe6_data import (ap_from_tp, blocks_train, box_iou_xyxy, cover_fraction, ignore_filter, mask_decision, merge_glass_status, check_label_rows, check_leaks, disagreement, diverse_pick, effective, eval_status, merge_review, parse_cvat,
                           scope_threshold)

AGENT = dict(label="safety", note="", decided_by="agent")
XML = """<annotations><image id="0" name="a.jpg" width="100" height="100">
<tag label="image_checked" source="manual"/>
<box label="boots_review" xtl="10" ytl="10" xbr="20" ybr="20"><attribute name="box_id">b1</attribute><attribute name="decision">ordinary</attribute><attribute name="person_ok">du_lon</attribute></box>
<box label="boots_review" xtl="30" ytl="30" xbr="40" ybr="40"><attribute name="box_id">b2</attribute><attribute name="decision">chua_duyet</attribute></box>
<box label="boots_new" xtl="50" ytl="50" xbr="60" ybr="70"></box>
</image></annotations>"""
INDEX = {"b1": dict(file="a.jpeg", image_name="a.jpg", target="boots", source="sh17", agent_label="safety", cx="0.15", cy="0.15", w="0.1", h="0.1"),
         "b2": dict(file="a.jpeg", image_name="a.jpg", target="boots", source="sh17", agent_label="safety", cx="0.35", cy="0.35", w="0.1", h="0.1")}


def test_human_beats_agent():
    assert effective(AGENT, None) == ("safety", "", "agent")
    assert effective(AGENT, dict(after="ordinary")) == ("ordinary", "", "human")


def test_unclear_goggles_block_train_but_default_shoes_do_not():
    assert blocks_train("unclear", "dark_lens", "goggles")
    assert blocks_train("unclear", "", "boots")
    assert not blocks_train("unclear", "not_safety", "boots")
    assert not blocks_train("unclear", "too_small", "boots")
    assert not blocks_train("safety", "", "goggles")


def test_eval_image_needs_human_for_every_box():
    assert eval_status([("safety", "agent")]) == "pending"
    assert eval_status([("safety", "human"), ("safety", "agent")]) == "pending"
    assert eval_status([("safety", "human"), ("ordinary", "human")]) == "ready"
    assert eval_status([("unclear", "human")]) == "rejected"
    assert eval_status([]) == "ready"


def test_leak_checks_find_image_scene_and_ppe4_val():
    scene = dict(a="s1", b="s1", c="s2", d="s3")
    split = dict(a="train", b="val", c="train", d="val")
    assert check_leaks({"train": {"a", "c"}, "val_new": {"d"}}, scene, split) == []
    assert any("cảnh trùng" in x for x in check_leaks({"train": {"a"}, "val_new": {"b"}}, scene, split))
    assert any("ảnh trùng" in x for x in check_leaks({"train": {"a"}, "val_new": {"a"}}, scene, split))
    assert any("val/test" in x for x in check_leaks({"train": {"d"}}, scene, split))


def test_label_checks():
    assert check_label_rows(["5 0.5 0.5 0.2 0.2"]) == []
    assert check_label_rows(["6 0.5 0.5 0.2 0.2"])
    assert check_label_rows(["1 0.5 0.5 0 0.2"])
    assert check_label_rows(["1 0.95 0.5 0.2 0.2"])
    assert check_label_rows(["1 0.5 0.5"])


def test_diverse_pick_is_repeatable_and_keeps_order_free():
    rng = np.random.default_rng(0)
    e = rng.normal(size=(20, 8))
    e /= np.linalg.norm(e, axis=1, keepdims=True)
    keys = [f"f{i:02d}" for i in range(20)]
    a = diverse_pick(e, keys, 5, 0)
    assert a == diverse_pick(e, keys, 5, 0) and len(set(a)) == 5
    assert diverse_pick(e[:3], keys[:3], 5, 0) == keys[:3]


def test_ap_perfect_and_empty():
    tp = np.ones((3, 2), dtype=bool)
    assert ap_from_tp(tp, np.array([0.9, 0.8, 0.7]), 3)[0] == pytest.approx(1.0, abs=0.01)
    assert ap_from_tp(tp, np.array([0.9, 0.8, 0.7]), 0) == (0.0, 0.0)
    half = ap_from_tp(np.array([[True], [False]]), np.array([0.9, 0.8]), 2)[0]
    assert half == pytest.approx(0.5, abs=0.02)   # precision về 0 ngay tại recall lớn nhất, như compute_ap của Ultralytics


def test_import_skips_unreviewed_and_keeps_before_after():
    boxes, tags = parse_cvat(XML)
    rows, added, skipped = merge_review(boxes, tags, INDEX, "Phuong", "P0a", "2026-11-06T10:00:00")
    assert skipped == 1
    assert [r["box_id"] for r in rows] == ["b1", "image:a.jpeg"]
    assert rows[0]["before"] == "safety" and rows[0]["after"] == "ordinary" and rows[0]["reviewer"] == "Phuong"
    assert rows[0]["new_cx"] == ""
    assert added[0]["target"] == "boots" and added[0]["file"] == "a.jpeg"


@pytest.mark.parametrize("name", ["", "Claude", "agent", " auto "])
def test_import_refuses_non_human_reviewer(name):
    boxes, tags = parse_cvat(XML)
    with pytest.raises(ValueError):
        merge_review(boxes, tags, INDEX, name, "P0a", "t")


def test_disagreement_and_scope():
    rows = [dict(box_id="b1", target="boots", source="sh17", before="safety", after="ordinary"), dict(box_id="b2", target="boots", source="sh17", before="safety", after="safety"),
            dict(box_id="image:x", target="image", source="", before="", after="checked")]
    assert disagreement(rows) == {("boots", "sh17"): (1, 2)}
    assert scope_threshold([(50, False), (100, False), (150, True), (200, True)], 0.9) == 150
    assert scope_threshold([], 0.9) is None


MERGE = dict(min_corr=0.98, max_hamming=8, min_helmet_iou=0.5)


def test_merge_requires_same_image_and_boxes():
    assert merge_glass_status(1.0, 0, 0.8, MERGE) == "ok"
    assert merge_glass_status(0.5, 0, 0.8, MERGE) == "image_mismatch"
    assert merge_glass_status(1.0, 20, 0.8, MERGE) == "image_mismatch"
    assert merge_glass_status(1.0, 0, 0.2, MERGE) == "box_mismatch"
    assert merge_glass_status(1.0, 0, None, MERGE) == "no_helmet_check"
    assert box_iou_xyxy((0, 0, 1, 1), (0, 0, 1, 1)) == pytest.approx(1.0)


def test_mask_stops_when_label_mostly_covered():
    region = [(0.0, 0.0, 0.5, 1.0)]
    assert cover_fraction((0.0, 0.0, 1.0, 1.0), region) == pytest.approx(0.5, abs=0.04)
    assert mask_decision(region, [(1, 0.1, 0.1, 0.4, 0.4)], 0.5)[0] is False
    ok, worst = mask_decision(region, [(1, 0.6, 0.1, 0.9, 0.4)], 0.5)
    assert ok and worst == 0
    two = [(0.0, 0.0, 0.5, 1.0), (0.0, 0.0, 0.5, 1.0)]
    assert cover_fraction((0.0, 0.0, 1.0, 1.0), two) == pytest.approx(0.5, abs=0.04)


def test_ignore_removes_false_positive_only():
    boxes = np.array([[0, 0, 10, 10], [0, 0, 10, 10], [50, 50, 60, 60], [0, 0, 10, 10.0]])
    tp = np.array([[False], [True], [False], [False]])
    classes = np.array([5, 5, 5, 4])
    keep = ignore_filter(tp, boxes, classes, [(5, 0, 0, 10, 10)])
    assert keep.tolist() == [False, True, True, True]


def test_scene_leak_blocks_masked_copy_of_eval_scene():
    scene = dict(a="s1", b="s1")
    assert check_leaks({"train": {"a"}, "test_new": {"b"}}, scene, dict(a="train", b="test"))



def test_apply_ignore_uses_letterbox_coordinates():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("e", Path(__file__).resolve().parents[1] / "scripts" / "04e_ppe6_eval.py")
    e = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(e)
    # Ảnh 100x100, thu 0.5, đệm x 10: hộp chuẩn hóa tâm (0.5, 0.5) rộng 0.2 nằm ở 30-40 x, 20-30 y.
    z = dict(files=np.array(["a.jpg"]), img=np.array([0, 0]), box=np.array([[30, 20, 40, 30.0], [0, 0, 5, 5.0]]), conf=np.array([0.9, 0.8]), cls=np.array([5, 5]),
             tp=np.zeros((2, 1), dtype=bool), ori=np.array([[100, 100]]), ratio_pad=np.array([[0.5, 10, 0]]))
    out, dropped = e.apply_ignore(z, {"a.jpg": [(5, 0.5, 0.5, 0.2, 0.2)]})
    assert dropped == 1 and len(out["conf"]) == 1
