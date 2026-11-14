"""Xác nhận theo thời gian và vòng đời sự kiện (spec 5.4, 5.5)."""

from ppe import HAVE, MISSING, UNKNOWN
from ppe.events import CLOSED, PENDING, EventManager
from ppe.temporal import TemporalConfirmer

REQ = ["helmet", "vest"]
FPS = 10


def feed(tc, em, seq, tid=1, t0=0.0):
    """seq: danh sách {ppe: state} theo từng khung 0,1 giây. None = người không có mặt ở khung."""
    t = t0
    for states in seq:
        if states is None:
            em.absent(t, set())
        else:
            checks = {p: tc.update(t, tid, p, states[p]) for p in REQ}
            em.update(t, tid, checks)
        t += 1 / FPS
    return t


def setup(params):
    log = []
    return TemporalConfirmer(params=params), EventManager("cam", "s1", REQ, on_change=lambda k, e: log.append(k)), log


def test_continuous_missing_helmet_gives_one_event(temporal_params):
    tc, em, log = setup(temporal_params)
    feed(tc, em, [{"helmet": MISSING, "vest": HAVE}] * 100)          # 10 giây thiếu mũ liên tục
    assert log.count("created") == 1
    assert len(em.open) == 1 and list(em.open.values())[0]["missing_items"] == ["helmet"]


def test_single_missing_frame_does_not_alert(temporal_params):
    tc, em, log = setup(temporal_params)
    seq = [{"helmet": HAVE, "vest": HAVE}] * 20 + [{"helmet": MISSING, "vest": HAVE}] + [{"helmet": HAVE, "vest": HAVE}] * 20
    feed(tc, em, seq)
    assert "created" not in log


def test_unknown_is_not_recovery(temporal_params):
    tc, em, log = setup(temporal_params)
    t = feed(tc, em, [{"helmet": MISSING, "vest": HAVE}] * 30)
    feed(tc, em, [{"helmet": UNKNOWN, "vest": UNKNOWN}] * 50, t0=t)
    ev = list(em.open.values())[0]
    assert ev["event_state"] == PENDING and ev["missing_items"] == ["helmet"]


def test_recovered_closes_event(temporal_params):
    tc, em, log = setup(temporal_params)
    t = feed(tc, em, [{"helmet": MISSING, "vest": HAVE}] * 30)
    feed(tc, em, [{"helmet": HAVE, "vest": HAVE}] * 30, t0=t)
    assert not em.open and em.closed[0]["close_reason"] == "recovered"


def test_second_missing_ppe_updates_same_event(temporal_params):
    tc, em, log = setup(temporal_params)
    t = feed(tc, em, [{"helmet": MISSING, "vest": HAVE}] * 30)
    feed(tc, em, [{"helmet": MISSING, "vest": MISSING}] * 30, t0=t)
    assert log.count("created") == 1
    assert list(em.open.values())[0]["missing_items"] == ["helmet", "vest"]


def test_absent_person_pending_then_session_end(temporal_params):
    tc, em, log = setup(temporal_params)
    t = feed(tc, em, [{"helmet": MISSING, "vest": HAVE}] * 30)
    t = feed(tc, em, [None] * 10, t0=t)
    assert list(em.open.values())[0]["event_state"] == PENDING
    em.end_session(t)
    assert em.closed[0]["event_state"] == CLOSED and em.closed[0]["close_reason"] == "session_ended_unverified"


def test_min_valid_frac_blocks_sparse_missing():
    """Vài khung Thiếu lẻ giữa nhiều khung Chưa xác định: không xác nhận khi bật min_valid_frac_on."""
    from ppe import MISSING, UNKNOWN
    from ppe.temporal import TemporalConfirmer
    base = dict(T_on=5.0, T_off=2.0, n_on=15, n_off=15, theta_on=0.7, theta_off=0.7)
    seq = [(i * 0.04, MISSING if i % 6 == 0 else UNKNOWN) for i in range(120)]   # 20 Thiếu / 120 khung
    for frac, expect in ((None, True), (0.3, False)):
        tc = TemporalConfirmer(params=dict(base, min_valid_frac_on=frac))
        got = any(tc.update(t, 1, "goggles", s).missing_confirmed for t, s in seq)
        assert got == expect
