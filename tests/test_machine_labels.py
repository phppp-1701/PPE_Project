"""Quy trình máy gán, người kiểm định: nhãn máy không lẫn với nhãn người."""

import pytest

from ppe.machine_labels import (HUMAN_AUDITED, HUMAN_REVIEWED, MACHINE_CONSENSUS, MACHINE_LABELED, audit_tiers, check_labeler, check_pass_row, eval_usable, is_machine_name, label_status, merge_passes, stratified_sample)
from ppe.ppe6_data import merge_blind, merge_review, parse_cvat


def row(decision="safety", person="du_lon", kind="box", image=""):
    return dict(labeler="machine_pass_a", kind=kind, decision=decision, person_ok=person, image_result=image)


def test_merge_requires_every_field_and_both_passes():
    k1, k2, k3, k4 = ("task_a", "box", "r1"), ("task_a", "box", "r2"), ("task_a", "box", "r3"), ("task_b", "image", "i1")
    a = {k1: row(), k2: row(), k3: row(), k4: row("", "", "image", "no_missing")}
    b = {k1: row(), k2: row(person="qua_nho"), k4: row("", "", "image", "missing_box")}
    m = {r["id"]: r for r in merge_passes(a, b)}
    assert m["r1"]["status"] == MACHINE_CONSENSUS
    assert m["r2"]["status"] == MACHINE_LABELED and m["r2"]["differ"] == "person_ok"
    assert m["r3"]["status"] == MACHINE_LABELED and m["r3"]["differ"] == "thieu_luot"
    assert m["i1"]["status"] == MACHINE_LABELED and m["i1"]["differ"] == "image_result"


def test_disagreement_queue_never_reaches_eval():
    assert eval_usable(MACHINE_LABELED, True) is False
    assert eval_usable(MACHINE_CONSENSUS, False) is False
    assert eval_usable(MACHINE_CONSENSUS, True) is True
    assert eval_usable(HUMAN_AUDITED, False) is True


def test_status_is_not_mixed():
    assert label_status(MACHINE_CONSENSUS) == MACHINE_CONSENSUS
    assert label_status(MACHINE_CONSENSUS, audited=True) == HUMAN_AUDITED
    assert label_status(MACHINE_LABELED, audited=True, reviewed=True) == HUMAN_REVIEWED
    assert label_status() == MACHINE_LABELED


@pytest.mark.parametrize("name", ["Phuong", "Huy", "AGENT_TEST", "machine"])
def test_machine_rows_cannot_carry_a_person_name(name):
    with pytest.raises(ValueError):
        check_labeler(name)
    assert check_pass_row(dict(row(), labeler=name))


def test_valid_rows_and_bad_values():
    assert check_pass_row(row()) == [] and check_pass_row(row("", "", "image", "reject")) == []
    assert check_pass_row(row("maybe")) and check_pass_row(row("", "", "image", "ok"))


@pytest.mark.parametrize("name", ["machine", "machine_pass_a", "machine_pass_b"])
def test_machine_name_refused_by_human_import(name):
    with pytest.raises(ValueError):
        merge_blind([], [], {}, {}, name, "task_a", "t", True, partial=True)
    with pytest.raises(ValueError):
        merge_review([], [], {}, name, "P0a", "t")
    assert is_machine_name(name)


def test_audit_tier_rate_and_systematic_error():
    ok = [dict(tier="x", machine="safety", human="safety")] * 29 + [dict(tier="x", machine="safety", human="unclear")]
    high = [dict(tier="y", machine="safety", human="safety")] * 8 + [dict(tier="y", machine="safety", human="ordinary"), dict(tier="y", machine="unclear", human="safety")]
    system = [dict(tier="z", machine="safety", human="safety")] * 40 + [dict(tier="z", machine="safety", human="ordinary")] * 3
    t = audit_tiers(ok + high + system, 0.10)
    assert t["x"]["passed"] and not t["y"]["passed"]
    assert not t["z"]["passed"] and t["z"]["rate"] < 0.10 and "ordinary" in t["z"]["pattern"]


def test_sample_is_fixed_and_covers_each_stratum():
    rows = [dict(id=f"r{i:03d}", s="a") for i in range(100)] + [dict(id=f"q{i}", s="b") for i in range(3)]
    x = stratified_sample(rows, 20, 5, 1, lambda r: r["s"])
    assert x == stratified_sample(rows, 20, 5, 1, lambda r: r["s"])
    assert sum(r["s"] == "b" for r in x) == 3 and 18 <= len(x) <= 22


def load_03t():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("m03t", Path(__file__).resolve().parents[1] / "scripts" / "03t_ppe6_machine_label.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fake_blind(m, tmp_path):
    import io
    import zipfile

    from PIL import Image
    d = tmp_path / "blind" / "task_a"
    d.mkdir(parents=True)
    with zipfile.ZipFile(d / "images.zip", "w") as z:
        b = io.BytesIO()
        Image.new("RGB", (100, 80)).save(b, "JPEG")
        z.writestr("img_000001.jpg", b.getvalue())
    for t in m.TASKS[1:]:
        e = tmp_path / "blind" / t
        e.mkdir()
        zipfile.ZipFile(e / "images.zip", "w").close()
    m.BLIND, m.AUDIT = tmp_path / "blind", tmp_path / "audit"
    m.AUDIT.mkdir()


def test_audit_pack_hides_machine_label_source_and_ids(tmp_path):
    from ppe.ppe6_data import leak_tokens
    m = load_03t()
    fake_blind(m, tmp_path)
    it = dict(item_id="r123456", target="boots", image="img_000001.jpg", xtl=1.0, ytl=2.0, xbr=30.0, ybr=40.0, decision_a="safety", source="sh17", agent_label="safety")
    mapped, imgs = m.build_pack("audit", [it], {"img_000001.jpg": ("task_a", 100, 80)}, True, 1)
    xml = (m.AUDIT / "audit" / "annotations.xml").read_text(encoding="utf-8")
    assert leak_tokens(xml) == [] and "r123456" not in xml and "img_000001" not in xml and "chua_chon" in xml
    assert mapped[0]["item_id"] == "r123456" and mapped[0]["audit_id"] in xml
    assert "safety" not in xml and "sh17" not in xml
    assert sorted(p.name for p in (m.AUDIT / "audit").iterdir()) == ["annotations.xml", "images.zip", "labels.json"]


def write_audit_state(m, tmp_path, reviewer, decision="safety"):
    import json
    rev = tmp_path / "rev"
    rev.mkdir(exist_ok=True)
    m.REVIEW = rev
    m.AUDIT = tmp_path / "audit2"
    (m.AUDIT / "_private").mkdir(parents=True, exist_ok=True)
    (m.AUDIT / "_private" / "audit_items.csv").write_text("audit_id,item_id,origin\na1,r1,sample\n", encoding="utf-8")
    m.private_items = lambda: dict(r1=dict(box_id="b1", target="boots", source="sh17"))
    (rev / "fast_audit_state.json").write_text(json.dumps(dict(reviewer=reviewer, boxes=dict(a1=dict(decision=decision, person_ok="du_lon" if decision != "chua_chon" else "chua_chon")))), encoding="utf-8")
    return rev


def test_audit_import_never_touches_human_review_and_refuses_machine_name(tmp_path):
    m = load_03t()
    rev = write_audit_state(m, tmp_path, "Nguoi That")
    m.cmd_audit_import("Nguoi That")
    assert (rev / "audit_review.csv").exists() and not (rev / "human_review.csv").exists()
    with pytest.raises(SystemExit):
        m.cmd_audit_import("machine_pass_a")
    with pytest.raises(SystemExit):
        m.cmd_audit_import("Nguoi Khac")


def test_audit_import_stops_on_unset_cell(tmp_path):
    m = load_03t()
    rev = write_audit_state(m, tmp_path, "Nguoi That", "chua_chon")
    with pytest.raises(SystemExit):
        m.cmd_audit_import("Nguoi That")
    assert not (rev / "audit_review.csv").exists()


def test_audit_session_works_without_cvat_link():
    from pathlib import Path

    from ppe.fast_review import IMAGE_STEP_TASKS
    assert "audit_img" in IMAGE_STEP_TASKS and Path(__file__).exists()

