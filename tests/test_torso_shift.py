"""Bước V2: vùng thân đặt theo hai vai (association.torso_shift; docs/experiments/2026-11-27_unknown_fix_plan.md).

Người dang tay: hộp người rộng, thân lệch sang trái hộp; áo nằm ngoài vùng thân theo tỉ lệ nhưng trong vùng theo vai.
Giá trị TS là giá trị thử để kiểm logic; tham số hệ thống ở configs/pipeline.yaml.
"""

import copy

from conftest import det, person

from ppe.association import Associator

VEST = 2
TS = dict(kp_conf=0.5, kx=1.259)


def _cfg(test_cfg, shift=True):
    cfg = copy.deepcopy(test_cfg)
    cfg["pose"].update(enabled=True, wrist_conf=0.5, rho_x=0.2, rho_y=0.1)
    for k in ("torso_pose", "torso_strict", "torso_shift"):
        cfg["association"].pop(k, None)
    if shift:
        cfg["association"]["torso_shift"] = dict(TS)
    return cfg


def _wide_person(sh_conf=0.9):
    """Hộp (0, 0, 1000, 2000), thân ở x 40-160 (vai 60 và 140), tay dang sang phải tới x 1000."""
    p = person(1, 0, 0, 1000, 2000)
    k = [(0.0, 0.0, 0.0)] * 17
    k[5], k[6] = (140.0, 600.0, sh_conf), (60.0, 600.0, sh_conf)
    k[11], k[12] = (130.0, 1100.0, 0.9), (70.0, 1100.0, 0.9)
    p.extra["kps"] = k
    return p


def test_shift_assigns_vest_on_offcenter_torso(test_cfg):
    vest = det(VEST, 60, 600, 140, 1100)             # tâm (100, 850): ngoài vùng thân theo tỉ lệ (lệch ngang)
    old = Associator(_cfg(test_cfg, shift=False))([_wide_person()], [vest], (2000, 1000, 3))
    new = Associator(_cfg(test_cfg))([_wide_person()], [vest], (2000, 1000, 3))
    assert not old.owned.get(1, {}).get(("vest", None))
    assert new.owned[1][("vest", None)] == [vest]


def test_shift_needs_shoulders(test_cfg):
    vest = det(VEST, 60, 600, 140, 1100)
    res = Associator(_cfg(test_cfg))([_wide_person(sh_conf=0.2)], [vest], (2000, 1000, 3))
    assert not res.owned.get(1, {}).get(("vest", None))


def test_shift_keeps_old_region(test_cfg):
    vest = det(VEST, 400, 700, 600, 1000)            # tâm (500, 850): trong vùng cũ, ngoài vùng theo vai
    res = Associator(_cfg(test_cfg))([_wide_person()], [vest], (2000, 1000, 3))
    old = Associator(_cfg(test_cfg, shift=False))([_wide_person()], [vest], (2000, 1000, 3))
    assert bool(res.owned.get(1, {}).get(("vest", None))) == bool(old.owned.get(1, {}).get(("vest", None)))
