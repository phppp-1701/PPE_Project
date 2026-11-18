"""Camera trực tiếp (backend/live.py) và đổi PPE bắt buộc khi đang chạy (Pipeline.set_required, FR-10).

Dùng camera giả, pipeline giả, database SQLite tạm: không cần webcam, GPU hay mô hình. Kiểm logic điều khiển
(bắt đầu, dừng, áp dụng chính sách, ghi sự kiện và phiên), không kiểm chất lượng nhận diện.
"""

import sys
import threading
import time
import uuid
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ppe import HAVE, MISSING  # noqa: E402
from ppe.events import EventManager  # noqa: E402
from ppe.pipeline import Pipeline  # noqa: E402
from ppe.temporal import TemporalConfirmer  # noqa: E402

from backend.live import IDLE, RUNNING, LiveCamera, load_live_config  # noqa: E402


def wait_for(cond, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


# ---------- Pipeline.set_required (EventManager, TemporalConfirmer thật) ----------

def bare_pipeline(cfg, temporal_params):
    """Pipeline không nạp mô hình: chỉ phần thời gian và sự kiện (stage full)."""
    p = Pipeline.__new__(Pipeline)
    p.cfg, p.stage, p.required = cfg, 4, list(cfg["required_ppe"])
    p.temporal = TemporalConfirmer(params=temporal_params)
    p.log = []
    p.events = EventManager("cam0", "s1", p.required, on_change=lambda kind, ev: p.log.append((kind, ev)))
    return p


def feed(p, states, t0=0.0, dt=0.1):
    t = t0
    for st in states:
        checks = {k: p.temporal.update(t, 1, k, st[k]) for k in p.required}
        p.events.update(t, 1, checks)
        t += dt
    return t


def test_set_required_closes_open_event_and_restarts(test_cfg, temporal_params):
    p = bare_pipeline(test_cfg, temporal_params)
    t = feed(p, [{"helmet": MISSING, "vest": HAVE, "gloves": HAVE}] * 30)
    assert len(p.events.open) == 1
    p.set_required(["vest", "helmet"], 2, t)
    closed = [ev for kind, ev in p.log if kind == "closed"]
    assert len(closed) == 1 and closed[0]["close_reason"] == "policy_changed"
    assert p.events.open == {}
    assert p.required == ["helmet", "vest"]                 # thứ tự cố định theo cấu hình
    assert p.events.required == ["helmet", "vest"] and p.events.policy_version == 2
    assert len(p.temporal.history) == 0                     # đếm lại từ đầu
    # sự kiện mới mang phiên bản chính sách mới; găng không còn bắt buộc
    feed(p, [{"helmet": HAVE, "vest": MISSING, "gloves": MISSING}] * 30, t0=t)
    created = [ev for kind, ev in p.log if kind == "created"]
    assert created[-1]["policy_version"] == 2 and created[-1]["missing_items"] == ["vest"]


def test_set_required_empty_list_no_events(test_cfg, temporal_params):
    p = bare_pipeline(test_cfg, temporal_params)
    p.set_required([], 2, 0.0)
    p.log.clear()
    checks = {}
    for i in range(30):
        p.events.update(i * 0.1, 1, checks)
    assert p.log == [] and p.events.open == {}


def test_compliance_empty_list_checks_nothing(test_cfg):
    """Tắt hết PPE: không món nào được xét (trước đây danh sách rỗng bị hiểu thành 'mọi PPE')."""
    from conftest import person
    from ppe.association import Associator
    from ppe.compliance import Compliance
    p = person(1, 100, 100, 300, 600)
    a = Associator(test_cfg)([p], [])
    comp = Compliance(test_cfg)
    assert comp([p], a, (720, 1280, 3), [])[1] == {}
    assert set(comp([p], a, (720, 1280, 3), ["vest"])[1]) == {"vest"}
    assert set(comp([p], a, (720, 1280, 3))[1]) == set(test_cfg["ppe"])        # không truyền: như cũ, mọi PPE


def test_set_required_rejects_unknown(test_cfg, temporal_params):
    p = bare_pipeline(test_cfg, temporal_params)
    with pytest.raises(ValueError):
        p.set_required(["helmet", "mask"], 2, 0.0)


# ---------- LiveCamera với camera và pipeline giả ----------

class FakeCap:
    def __init__(self, fail_after=None):
        self.n, self.fail_after, self.released = 0, fail_after, False

    def read(self):
        time.sleep(0.005)
        self.n += 1
        if self.fail_after is not None and self.n > self.fail_after:
            return False, None
        return True, np.full((72, 128, 3), self.n % 255, np.uint8)

    def release(self):
        self.released = True


class FakePipe:
    """Giống giao diện Pipeline: tạo một sự kiện ở khung thứ 3 (1 ảnh minh chứng), khung thứ 6 thêm 1 ảnh;
    set_required đóng sự kiện đang mở với lý do policy_changed như Pipeline thật."""

    def __init__(self, source_id, session_id, on_event):
        self.source_id, self.session_id, self.on_event = source_id, session_id, on_event
        self.cfg = {"ppe": {k: {} for k in ("helmet", "vest", "gloves", "goggles", "boots")}}
        self.required, self.version, self.calls, self.n, self.ev, self.closed_at = [], None, [], 0, None, None

    def set_required(self, req, version, t):
        self.calls.append((list(req), version, t))
        if self.ev is not None:
            self._close(t, "policy_changed")
        self.required, self.version = [p for p in self.cfg["ppe"] if p in req], version

    def _close(self, t, reason):
        self.ev.update(event_state="closed", end_time=t, close_reason=reason, last_change_time=t)
        self.on_event("closed", dict(self.ev))
        self.ev = None

    def process(self, frame, t):
        self.n += 1
        if self.n == 3 and self.required:
            self.ev = dict(event_id=str(uuid.uuid4()), source_id=self.source_id, session_id=self.session_id,
                           track_id=1, start_time=t, confirmed_at=t, last_seen_time=t,
                           missing_items=[self.required[0]], event_state="active", end_time=None, close_reason=None,
                           evidence_refs=[{"t": t, "path": "a_0.jpg"}], policy_version=self.version, history=[],
                           last_change_time=t)
            self.on_event("created", dict(self.ev, evidence_refs=list(self.ev["evidence_refs"])))
        if self.n == 6 and self.ev is not None:
            self.ev["evidence_refs"].append({"t": t, "path": "a_1.jpg"})
            self.ev["last_change_time"] = t
            self.on_event("missing_items", dict(self.ev, evidence_refs=list(self.ev["evidence_refs"])))
        return {"tracks": [object()] * 2, "ppe": [], "timing": {}}

    def close(self, t):
        self.closed_at = t
        if self.ev is not None:
            self._close(t, "session_ended_unverified")


def make_live(on_event=None, on_session=None, cap=None):
    holder = {}

    def pipe_factory(source_id, session_id, emit):
        holder["pipe"] = FakePipe(source_id, session_id, emit)
        return holder["pipe"]

    cam = LiveCamera(load_live_config(), on_event=on_event, on_session=on_session,
                     capture_factory=lambda: cap or FakeCap(), pipeline_factory=pipe_factory,
                     draw_factory=lambda: (lambda frame, out, cfg: frame))
    return cam, holder


def test_live_start_policy_stop():
    events, sessions = [], []
    cam, holder = make_live(lambda k, ev: events.append((k, ev)), lambda k, info: sessions.append((k, info)))
    cam.start(["vest", "helmet"], 3)
    assert wait_for(lambda: cam.state == RUNNING and cam.latest_jpeg() is not None and cam.frames >= 6)
    pipe = holder["pipe"]
    assert pipe.calls[0] == (["vest", "helmet"], 3, 0.0)    # danh sách theo nguồn áp ngay khi mở
    assert cam.status()["persons"] == 2 and cam.status()["required_ppe"] == ["helmet", "vest"]
    assert [k for k, _ in events][:2] == ["created", "missing_items"]
    assert events[0][1]["source_id"] == cam.source_id and "system_time" in events[0][1]

    assert cam.set_policy(["gloves"], 4)
    assert wait_for(lambda: cam.policy_version == 4)
    assert pipe.calls[-1][:2] == (["gloves"], 4) and pipe.calls[-1][2] > 0
    assert events[-1][0] == "closed" and events[-1][1]["close_reason"] == "policy_changed"
    assert cam.status()["required_ppe"] == ["gloves"]

    with pytest.raises(RuntimeError):
        cam.start(["helmet"], 5)                             # đang chạy thì không mở phiên thứ hai
    cam.stop()
    assert cam.state == IDLE and pipe.closed_at is not None
    assert [k for k, _ in sessions] == ["start", "end"] and sessions[1][1]["error"] is None
    assert cam.set_policy(["helmet"], 6) is False            # đã dừng: không áp dụng


def test_live_mjpeg_yields_parts_and_ends_on_stop():
    cam, _ = make_live()
    cam.start(["helmet"], 1)
    assert wait_for(lambda: cam.latest_jpeg() is not None)
    gen = cam.mjpeg()
    part = next(gen)
    assert part.startswith(b"--frame\r\nContent-Type: image/jpeg") and b"\xff\xd8" in part
    threading.Timer(0.1, cam.stop).start()
    list(gen)                                                # kết thúc khi phiên bắt đầu dừng, không treo
    assert wait_for(lambda: cam.state == IDLE)


def test_live_draws_only_required_ppe_boxes():
    """Món đã tắt: hộp detector của món đó không được đưa vào hình vẽ (kết quả nhận diện không đổi)."""
    from ppe import Det
    seen = []

    class Pipe(FakePipe):
        def __init__(self, *a):
            super().__init__(*a)
            self.cfg = {"ppe": {"helmet": {"cls": 1}, "vest": {"cls": 2}, "goggles": {"cls": 4}}}

        def process(self, frame, t):
            box = np.array([0, 0, 10, 10], float)
            self.last = {"tracks": [], "ppe": [Det(1, box, 0.9), Det(4, box, 0.9)], "timing": {}}
            return self.last

    holder = {}
    cam = LiveCamera(load_live_config(), capture_factory=FakeCap,
                     pipeline_factory=lambda *a: holder.setdefault("p", Pipe(*a)),
                     draw_factory=lambda: (lambda frame, out, cfg: (seen.append(out), frame)[1]))
    cam.start(["helmet"], 1)
    assert wait_for(lambda: len(seen) >= 3)
    cam.stop()
    assert {d.cls for d in seen[-1]["ppe"]} == {1}                     # kính (4) đã tắt: không vẽ
    assert {d.cls for d in holder["p"].last["ppe"]} == {1, 4}          # kết quả gốc giữ nguyên


def test_hide_rejected_drops_only_vetoed_boxes():
    """Hộp bị bộ phân loại bác bỏ (kính thường...) không vẽ; hộp Có và hộp xám vì lý do khác vẫn vẽ."""
    from backend.live import hide_rejected
    a, b, c = object(), object(), object()
    kinds = {id(a): ("co", 1, "Mu>1"), id(b): ("bac_bo", 1, "Kinh thuong"), id(c): ("tranh_chap", None, "Gang (tranh chap)")}
    out = {"assoc": object(), "ppe": [a, b, c]}
    got = hide_rejected(out, {}, lambda o, cfg: kinds)
    assert got["ppe"] == [a, c] and out["ppe"] == [a, b, c]       # bản gốc không đổi
    assert hide_rejected({"ppe": [a]}, {}, None) == {"ppe": [a]}   # chưa có bước gán: giữ nguyên


def test_live_camera_failure_sets_error():
    sessions = []
    cap = FakeCap(fail_after=5)
    cam, _ = make_live(on_session=lambda k, info: sessions.append((k, info)), cap=cap)
    cam.start(["helmet"], 1)
    assert wait_for(lambda: cam.state == "error", timeout=10)
    assert "Webcam" in cam.status()["error"] and cap.released
    assert sessions[-1][0] == "end" and sessions[-1][1]["error"]
    cam.start(["helmet"], 1)                                 # mở lại được sau lỗi
    cam.stop()


def test_live_pipeline_load_error():
    def bad_factory(*a):
        raise RuntimeError("không có trọng số")
    cam = LiveCamera(load_live_config(), capture_factory=FakeCap, pipeline_factory=bad_factory,
                     draw_factory=lambda: (lambda f, o, c: f))
    cam.start(["helmet"], 1)
    assert wait_for(lambda: cam.state == "error")
    assert "không có trọng số" in cam.status()["error"]


# ---------- API backend với database tạm ----------

@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import backend.app as app_mod
    import backend.db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "ppe.db")
    cam, holder = make_live(app_mod._live_event, app_mod._live_session)
    monkeypatch.setattr(app_mod, "LIVE", cam)
    with TestClient(app_mod.app) as c:
        yield c, cam, holder, db_mod
    cam.stop()


def test_api_live_flow(client):
    c, cam, holder, db_mod = client
    src = cam.source_id
    assert c.get(f"/api/sources/{src}/policy").json()["version"] == 1          # nguồn webcam được tạo sẵn
    assert any(s["source_id"] == src and s["source_type"] == "camera" for s in c.get("/api/sources").json())
    assert c.put(f"/api/sources/{src}/policy", json={"required_ppe": ["helmet", "mask"]}).status_code == 400
    r = c.put(f"/api/sources/{src}/policy", json={"required_ppe": ["vest", "helmet"]}).json()
    assert r["required_ppe"] == ["helmet", "vest"] and r["version"] == 2 and r["applied_live"] is False

    assert c.get("/api/live/stream").status_code == 409                          # chưa chạy
    st = c.post("/api/live/start").json()
    assert st["state"] in ("starting", "running") and st["policy_version"] == 2
    assert c.post("/api/live/start").status_code == 409
    assert wait_for(lambda: cam.frames >= 8)
    assert c.get("/api/live/status").json()["state"] == "running"
    snap = c.get("/api/live/snapshot")
    assert snap.status_code == 200 and snap.content[:2] == b"\xff\xd8"

    evs = c.get(f"/api/events?source_id={src}").json()["events"]
    assert len(evs) == 1 and evs[0]["missing_items"] == ["helmet"] and evs[0]["event_state"] == "active"
    assert c.get(f"/api/events?session_id={st['session_id']}").json()["count"] == 1
    assert c.get("/api/events?session_id=khong_co").json()["count"] == 0

    r = c.put(f"/api/sources/{src}/policy", json={"required_ppe": ["gloves"]}).json()
    assert r["applied_live"] is True and r["version"] == 3
    assert wait_for(lambda: cam.policy_version == 3)
    ev = c.get(f"/api/events/{evs[0]['event_id']}").json()
    assert ev["event_state"] == "closed" and ev["close_reason"] == "policy_changed"

    c.post("/api/live/stop")
    conn = db_mod.get_db()
    n_ref = conn.execute("SELECT COUNT(*) FROM event_evidence WHERE event_id = ?", (evs[0]["event_id"],)).fetchone()[0]
    sess = conn.execute("SELECT * FROM monitoring_sessions WHERE source_id = ?", (src,)).fetchall()
    conn.close()
    assert n_ref == 2                                                              # ảnh minh chứng không bị ghi trùng
    assert len(sess) == 1 and sess[0]["status"] == "ended" and sess[0]["end_time"] and sess[0]["policy_version"] == 2
    assert c.get("/api/live/status").json()["state"] == "idle"


def test_api_events_sorted_by_system_time(client):
    """Danh sách sự kiện xếp theo giờ thật, không theo giây trong video / phiên (confirmed_at không so được giữa phiên)."""
    c = client[0]
    base = dict(track_id=1, start_time=0.0, last_seen_time=0.0, missing_items=["helmet"])
    c.post("/api/events", json=dict(base, event_id="cu", source_id="video", session_id="v1", confirmed_at=90.0,
                                    system_time="2026-11-11T10:00:00"))
    c.post("/api/events", json=dict(base, event_id="moi", source_id="cam0", session_id="c1", confirmed_at=3.0,
                                    system_time="2026-11-16T20:00:00"))
    assert [e["event_id"] for e in c.get("/api/events").json()["events"]] == ["moi", "cu"]
