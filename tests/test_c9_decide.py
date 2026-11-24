"""Kiểm tra scripts/04n_c9_decide.py: áp đúng ba điều kiện của c9_decision, đúng tập con cho từng lớp."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = dict(baseline="c6_ft", min_gloves_gain=0.03, max_drop=0.02)


def _mod():
    spec = importlib.util.spec_from_file_location("decide04n", ROOT / "scripts" / "04n_c9_decide.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _res(diffs):
    """diffs: {(tập con, lớp): hiệu} -> dạng JSON của 04j."""
    subs = {}
    for (s, c), d in diffs.items():
        subs.setdefault(s, {"classes": {}})["classes"][c] = {"diff50": {"point": d, "ci": [d - 0.01, d + 0.01]}}
    return {"split": "val", "subsets": subs}


def _full(over=None):
    d = {("ppe4", c): 0.0 for c in ("person", "helmet", "vest", "gloves")}
    d.update({("goggles_all", "goggles"): 0.0, ("new", "boots"): 0.0})
    d.update(over or {})
    return _res(d)


def _zoom(gloves=0.05, goggles=0.0, boots=0.0, boots_ppe4=-0.5):
    # ủng tập ppe4 không có trong tiêu chí: giá trị xấu ở đó không được ảnh hưởng kết luận
    return _res({("ppe4", "gloves"): gloves, ("goggles_all", "goggles"): goggles, ("new", "boots"): boots, ("ppe4", "boots"): boots_ppe4})


def test_pass_when_all_conditions_hold():
    checks, ok = _mod().decide(_full(), _zoom(), CFG)
    assert ok and len(checks) == 9


def test_gloves_gain_below_threshold_fails():
    checks, ok = _mod().decide(_full(), _zoom(gloves=0.029), CFG)
    assert not ok and [x["cls"] for x in checks if not x["ok"]] == ["gloves"]


def test_drop_at_limit_passes_beyond_fails():
    m = _mod()
    assert m.decide(_full({("new", "boots"): -0.02}), _zoom(), CFG)[1]
    _, ok = m.decide(_full({("goggles_all", "goggles"): -0.021}), _zoom(), CFG)
    assert not ok
    checks, ok = m.decide(_full(), _zoom(boots=-0.03), CFG)
    assert not ok and [(x["check"], x["cls"]) for x in checks if not x["ok"]] == [("có zoom: không tụt", "boots")]
