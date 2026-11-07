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
    (m.AUDIT / "_private" / "audit_img2_images.csv").write_text("audit_image,image,task,origin\nimg_2.jpg,src_1.jpg,task_d,sample\n", encoding="utf-8")
    (rev / "fast_audit_img2_state.json").write_text(json.dumps(dict(reviewer=reviewer, images={"img_2.jpg": "image_checked"}, flags={})), encoding="utf-8")
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



def test_audit_img2_shows_existing_boxes_and_question_without_new_steps(tmp_path):
    from ppe.fast_review import Session, load_pack
    from ppe.ppe6_data import leak_tokens
    m = load_03t()
    fake_blind(m, tmp_path)
    shown = {"img_000001.jpg": [dict(item_id="r9", target="goggles", xtl=1.0, ytl=2.0, xbr=9.0, ybr=9.0)]}
    _, imgs = m.build_pack("audit_img2", [], {"img_000001.jpg": ("task_a", 100, 80)}, False, 5, shown, {"img_000001.jpg": "goggles"})
    xml = (m.AUDIT / "audit_img2" / "annotations.xml").read_text(encoding="utf-8")
    assert leak_tokens(xml) == [] and "r9" not in xml and "img_000001" not in xml
    pack = load_pack(m.AUDIT / "audit_img2")
    im = pack["images"][0]
    assert im["boxes"] == [] and len(im["shown"]) == 1 and im["ask"] == "goggles"
    s = Session(pack, "audit_img2", "Nguoi That", tmp_path)
    v = s.view("", 0, 0)
    assert [x["type"] for x in v["steps"]] == ["image"] and v["shown"][im["name"]] and v["ask"][im["name"]] == "goggles"


def test_audit_import_uses_img2_not_first_image_pack(tmp_path):
    import csv
    import json
    m = load_03t()
    rev = write_audit_state(m, tmp_path, "Nguoi That")
    (m.AUDIT / "_private" / "audit_img_images.csv").write_text("audit_image,image,task,origin\nimg_1.jpg,src_1.jpg,task_d,sample\n", encoding="utf-8")
    (rev / "fast_audit_img_state.json").write_text(json.dumps(dict(reviewer="Nguoi That", images={"img_1.jpg": "image_checked"}, flags={"image:img_1.jpg": True})), encoding="utf-8")
    m.cmd_audit_import("Nguoi That")
    rows = list(csv.DictReader((rev / "audit_review.csv").open(encoding="utf-8")))
    assert [r["after"] for r in rows if r["kind"] == "image"] == ["no_missing"]
    assert (rev / "fast_audit_img_state.json").exists()


def test_audit_rebuild_refused_once_human_session_exists(tmp_path):
    m = load_03t()
    rev = write_audit_state(m, tmp_path, "Nguoi That")
    (rev / "machine_merged.csv").write_text("id,kind,status\nr1,box,machine_consensus\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        m.cmd_audit()
    assert (m.AUDIT / "_private" / "audit_items.csv").exists()


def test_rest_import_is_human_reviewed_and_never_touches_human_review(tmp_path):
    import csv
    import json
    m = load_03t()
    rev = write_audit_state(m, tmp_path, "Nguoi That")
    (m.AUDIT / "_private" / "rest_items.csv").write_text("audit_id,item_id,origin\na9,r1,rest\n", encoding="utf-8")
    (rev / "fast_rest_state.json").write_text(json.dumps(dict(reviewer="Nguoi That", boxes=dict(a9=dict(decision="ordinary", person_ok="qua_nho")))), encoding="utf-8")
    m.cmd_rest_import("Nguoi That")
    rows = list(csv.DictReader((rev / "rest_review.csv").open(encoding="utf-8")))
    assert [(r["origin"], r["after"]) for r in rows] == [("rest", "ordinary")] and not (rev / "human_review.csv").exists()
    with pytest.raises(SystemExit):
        m.cmd_rest_import("machine_pass_b")
    with pytest.raises(SystemExit):
        m.cmd_rest_import("Nguoi Khac")


def test_rest_pack_refuses_overwrite(tmp_path):
    m = load_03t()
    write_audit_state(m, tmp_path, "Nguoi That")
    (m.AUDIT / "rest").mkdir()
    with pytest.raises(SystemExit):
        m.cmd_rest()


def test_rest_import_takes_recheck_choice_over_first(tmp_path):
    import csv
    import json
    m = load_03t()
    rev = write_audit_state(m, tmp_path, "Nguoi That")
    (m.AUDIT / "_private" / "rest_items.csv").write_text("audit_id,item_id,origin\na9,r1,rest\n", encoding="utf-8")
    (m.AUDIT / "_private" / "recheck_items.csv").write_text("audit_id,item_id,origin\nb5,r1,recheck\n", encoding="utf-8")
    (rev / "fast_rest_state.json").write_text(json.dumps(dict(reviewer="Nguoi That", boxes=dict(a9=dict(decision="safety", person_ok="du_lon")))), encoding="utf-8")
    (rev / "fast_recheck_state.json").write_text(json.dumps(dict(reviewer="Nguoi That", boxes=dict(b5=dict(decision="ordinary", person_ok="du_lon")))), encoding="utf-8")
    m.cmd_rest_import("Nguoi That")
    rows = list(csv.DictReader((rev / "rest_review.csv").open(encoding="utf-8")))
    assert [(r["origin"], r["after"]) for r in rows] == [("rest_recheck", "ordinary")]
    assert json.loads((rev / "fast_rest_state.json").read_text(encoding="utf-8"))["boxes"]["a9"]["decision"] == "safety"


def test_boots_v3_import_writes_own_file_and_eval_count_uses_v3_for_boots(tmp_path, capsys):
    import csv
    import json
    m = load_03t()
    rev = write_audit_state(m, tmp_path, "Nguoi That")
    (m.AUDIT / "_private" / "boots_v3_items.csv").write_text("audit_id,item_id,origin\nc1,r1,boots_v3\n", encoding="utf-8")
    (rev / "fast_boots_v3_state.json").write_text(json.dumps(dict(reviewer="Nguoi That", boxes=dict(c1=dict(decision="ordinary", person_ok="du_lon")))), encoding="utf-8")
    with pytest.raises(SystemExit):
        m.cmd_boots_v3_import("machine_pass_a")
    m.cmd_boots_v3_import("Nguoi That")
    rows = list(csv.DictReader((rev / "boots_v3_review.csv").open(encoding="utf-8")))
    assert rows[0]["after"] == "ordinary" and rows[0]["guide_version"] == "3" and not (rev / "human_review.csv").exists()
    m.cmd_audit_import("Nguoi That")
    m.private_items = lambda: dict(r1=dict(box_id="b1", target="boots", source="sh17", set="val_new"))
    m.cmd_eval_count()
    out = capsys.readouterr().out
    assert "bản 3" in out and "'ordinary') 1" in out and "safety" not in out


def test_train_v3_import_counts_as_boots_v3_and_refuses_machine(tmp_path):
    import json
    from ppe.machine_labels import human_box_labels
    m = load_03t()
    rev = write_audit_state(m, tmp_path, "Nguoi That")
    (m.AUDIT / "_private" / "train_v3_items.csv").write_text("audit_id,box_id,target,source,origin,agent_label\nt1,b77,boots,sh17,p2,unclear\n", encoding="utf-8")
    (rev / "fast_train_v3_state.json").write_text(json.dumps(dict(reviewer="Nguoi That", boxes=dict(t1=dict(decision="safety", person_ok="du_lon")))), encoding="utf-8")
    with pytest.raises(SystemExit):
        m.cmd_train_v3_import("machine_pass_b")
    m.cmd_train_v3_import("Nguoi That")
    out = human_box_labels(rev)
    assert out["b77"]["after"] == "safety" and out["b77"]["file_from"] == "train_v3_review.csv" and not (rev / "human_review.csv").exists()


def test_chv_boots_import_writes_gate_files(tmp_path):
    import csv
    import json
    m = load_03t()
    rev = write_audit_state(m, tmp_path, "Nguoi That")
    (m.AUDIT / "_private" / "chv_boots_images.csv").write_text("audit_image,image,task,file\nx1.jpg,o1.jpg,task_d,chv__a.jpg\nx2.jpg,o2.jpg,task_d,chv__b.jpg\n", encoding="utf-8")
    (rev / "fast_chv_boots_state.json").write_text(json.dumps(dict(reviewer="Nguoi That", images={"x1.jpg": "image_checked", "x2.jpg": "image_checked"}, flags={"image:x2.jpg": True})), encoding="utf-8")
    m.cmd_chv_boots_import("Nguoi That")
    seen = list(csv.DictReader((rev / "chv_boots_seen.csv").open(encoding="utf-8")))
    added = list(csv.DictReader((rev / "chv_boots_added.csv").open(encoding="utf-8")))
    assert [r["after"] for r in seen] == ["checked", "checked"] and [r["file"] for r in added] == ["chv__b.jpg"]
