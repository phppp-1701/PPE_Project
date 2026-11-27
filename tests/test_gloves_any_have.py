"""G1: gộp hai tay của găng (compliance.gloves_any_have; docs/experiments/2026-11-27_unknown_fix_plan.md)."""

import copy

from conftest import person

from ppe import HAVE, MISSING, UNKNOWN
from ppe.association import Association
from ppe.compliance import Compliance


def _state(test_cfg, left, right, any_have):
    cfg = copy.deepcopy(test_cfg)
    cfg.setdefault("compliance", {})["gloves_any_have"] = any_have
    c = Compliance(cfg)
    c.side_state = lambda name, t, side, *a, **k: ({"left": left, "right": right}[side], {})
    return c([person(1, 0, 0, 100, 300)], Association(), (500, 500, 3), ["gloves"])[1]["gloves"]["state"]


def test_one_have_other_unknown(test_cfg):
    assert _state(test_cfg, HAVE, UNKNOWN, False) == UNKNOWN
    assert _state(test_cfg, HAVE, UNKNOWN, True) == HAVE


def test_missing_still_wins(test_cfg):
    assert _state(test_cfg, HAVE, MISSING, True) == MISSING


def test_both_unknown_stays_unknown(test_cfg):
    assert _state(test_cfg, UNKNOWN, UNKNOWN, True) == UNKNOWN


def test_g1b_needs_confident_glove(test_cfg):
    cfg = copy.deepcopy(test_cfg)
    cfg.setdefault("compliance", {})["gloves_any_have"] = {"min_conf": 0.9}
    c = Compliance(cfg)
    for conf, want in ((0.95, HAVE), (0.5, UNKNOWN)):
        c.side_state = lambda name, t, side, *a, conf=conf, **k: (
            (HAVE, {"conf": conf}) if side == "left" else (UNKNOWN, {"conf": 0.0}))
        assert c([person(1, 0, 0, 100, 300)], Association(), (500, 500, 3), ["gloves"])[1]["gloves"]["state"] == want
