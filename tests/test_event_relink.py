"""R1: nối sự kiện khi đổi mã theo dõi (events.relink; docs/experiments/2026-11-27_unknown_fix_plan.md)."""

from types import SimpleNamespace

from ppe.events import EventManager

REQ = ["helmet"]
MISS = {"helmet": SimpleNamespace(missing_confirmed=True, since=0.0, valid_now=True, recovered=False)}


def _em(relink):
    out = []
    em = EventManager("s", "x", REQ, on_change=lambda k, ev: out.append((k, ev)), relink=relink)
    return em, out


def test_new_track_at_same_place_continues_event():
    em, out = _em({"iou": 0.5, "max_gap_s": 2.0})
    em.update(0.0, 1, MISS, box=[0, 0, 100, 200])
    em.absent(0.5, set())                               # người 1 mất dấu
    em.update(1.0, 2, MISS, box=[5, 0, 105, 200])        # người 2 xuất hiện đúng chỗ
    created = [ev for k, ev in out if k == "created"]
    assert len(created) == 1 and list(em.open) == [2]
    assert em.open[2]["relinked_from"] == [1]


def test_far_or_late_track_makes_new_event():
    em, out = _em({"iou": 0.5, "max_gap_s": 2.0})
    em.update(0.0, 1, MISS, box=[0, 0, 100, 200])
    em.absent(0.5, set())
    em.update(1.0, 2, MISS, box=[500, 0, 600, 200])      # chỗ khác
    em.update(3.0, 3, MISS, box=[0, 0, 100, 200])        # quá 2 s
    assert sum(k == "created" for k, _ in out) == 3


def test_present_person_is_not_taken():
    em, out = _em({"iou": 0.5, "max_gap_s": 2.0})
    em.update(0.0, 1, MISS, box=[0, 0, 100, 200])
    em.update(0.1, 2, MISS, box=[5, 0, 105, 200])        # người 1 chưa vắng mặt
    assert sum(k == "created" for k, _ in out) == 2


def test_without_relink_as_before():
    em, out = _em(None)
    em.update(0.0, 1, MISS, box=[0, 0, 100, 200])
    em.absent(0.5, set())
    em.update(1.0, 2, MISS, box=[5, 0, 105, 200])
    assert sum(k == "created" for k, _ in out) == 2
