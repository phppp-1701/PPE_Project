"""FastAPI Backend cho Hệ thống giám sát vi phạm PPE 6 lớp (docs/spec.md mục 6, Bảng 3.8, docs/desktop_app_plan.md mục 4)."""

import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import threading
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import (
    ROOT,
    ensure_default_sources,
    ensure_source,
    get_db,
    init_db,
    recover_crashed_sessions,
    rename_source,
)
from .discovery import get_discovered, start_discovery
from .live import LiveCamera, load_camera_catalog, load_live_config, probe_cameras
from .video_file import sanitize_video_source_id
from desktop import APP_NAME, APP_VERSION
from desktop.paths import (
    get_data_dir,
    get_db_path,
    get_evidence_dir,
    get_logs_dir,
    is_desktop_mode,
    load_desktop_config,
    resolve_resource,
    save_user_settings,
)

import yaml

# PPE hệ thống biết (thứ tự cố định theo configs/pipeline.yaml); chính sách chỉ nhận các tên này.
KNOWN_PPE = list(yaml.safe_load(resolve_resource("configs/pipeline.yaml").read_text(encoding="utf-8"))["ppe"])
_FOCUS_CALLBACK = None
_WEIGHT_HASH_CACHE: dict[str, str] = {}


def register_focus_handler(callback):
    """Đăng ký hàm đưa cửa sổ ứng dụng desktop lên trước khi người dùng mở lần hai."""
    global _FOCUS_CALLBACK
    _FOCUS_CALLBACK = callback


app = FastAPI(
    title="Hệ thống Giám sát Trang bị Bảo hộ Lao động (PPE-6)",
    description="API quản lý sự kiện vi phạm, ảnh minh chứng và chính sách 6 lớp PPE theo thời gian thực",
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    recover_crashed_sessions()
    ensure_default_sources()
    # đăng ký mọi camera trong danh mục (camera IP + webcam) để chọn theo dõi từ dashboard
    for cam in load_camera_catalog():
        ensure_source(cam["source_id"], cam["name"], "camera", KNOWN_PPE)
    # nghe UDP quảng cáo của các laptop_cam_server trong mạng LAN ("Quét camera trong mạng")
    start_discovery(DISCOVERY_PORT)
    # nền: tự thêm camera LAN mới phát hiện vào danh mục (auto_add_discovered)
    threading.Thread(target=_auto_add_discovered_worker, daemon=True, name="ppe-auto-add").start()


@app.on_event("shutdown")
def shutdown():
    stop_all_lives()   # đóng sự kiện đang mở, tắt mọi camera


# === SCHEMAS ===
class EventCreateSchema(BaseModel):
    event_id: str
    source_id: str = "video"
    session_id: str = "default"
    track_id: int
    start_time: float
    confirmed_at: float
    last_seen_time: float
    missing_items: List[str]
    event_state: str = "active"
    policy_version: int = 1
    system_time: Optional[str] = None
    evidence_refs: Optional[List[dict]] = []
    history: Optional[List[dict]] = []


class EventPatchSchema(BaseModel):
    last_seen_time: Optional[float] = None
    missing_items: Optional[List[str]] = None
    event_state: Optional[str] = None
    end_time: Optional[float] = None
    close_reason: Optional[str] = None
    last_change_time: Optional[float] = None
    evidence_refs: Optional[List[dict]] = None
    change_type: Optional[str] = None


class PolicyUpdateSchema(BaseModel):
    required_ppe: List[str]


class FeedbackSchema(BaseModel):
    feedback_type: str = "correct"  # 'correct', 'false_alarm', 'missed', 'custom'
    false_alarm_items: Optional[List[str]] = []
    notes: Optional[str] = ""


class LiveStartSchema(BaseModel):
    source: str = "camera"          # "camera" | "file"
    camera_index: Optional[Any] = None   # int = webcam; str http/rtsp = camera IP (bridge Fofu)
    path: Optional[str] = None
    mode: str = "realtime"          # "realtime" | "fast"
    source_id: Optional[str] = None # nguồn muốn theo dõi (cam0 / webcam{n}); bỏ trống = mặc định


class CleanupRequestSchema(BaseModel):
    keep_days: Optional[int] = None


# === HELPERS ===

def _build_events_query(
    source_id: Optional[str] = None,
    session_id: Optional[str] = None,
    state: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
):
    conditions = []
    params: list[Any] = []
    if source_id:
        conditions.append("source_id = ?")
        params.append(source_id)
    if state:
        conditions.append("event_state = ?")
        params.append(state)
    if session_id:
        conditions.append("session_id = ?")
        params.append(session_id)
    if date_from:
        conditions.append("system_time >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("system_time <= ?")
        params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)
    if q and q.strip():
        q_clean = q.strip()
        if q_clean.isdigit():
            conditions.append("(event_id LIKE ? OR track_id = ? OR session_id LIKE ?)")
            params.extend([f"%{q_clean}%", int(q_clean), f"%{q_clean}%"])
        else:
            conditions.append("(event_id LIKE ? OR session_id LIKE ? OR source_id LIKE ?)")
            params.extend([f"%{q_clean}%", f"%{q_clean}%", f"%{q_clean}%"])
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_clause, params


def _short_sha256(file_path: Path) -> Optional[str]:
    key = str(file_path)
    if key in _WEIGHT_HASH_CACHE:
        return _WEIGHT_HASH_CACHE[key]
    if not file_path.exists() or not file_path.is_file():
        return None
    try:
        h = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        short = h.hexdigest()[:12]
        _WEIGHT_HASH_CACHE[key] = short
        return short
    except Exception:
        return None


def _get_git_commit() -> str:
    try:
        # CREATE_NO_WINDOW: không bật cửa sổ terminal lên mỗi lần dashboard hỏi thông tin hệ thống
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=1.5,
            creationflags=flags,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "release"


# === API ENDPOINTS ===

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard/index.html")


@app.post("/api/events")
def create_event(ev: EventCreateSchema):
    """POST /events: Tạo sự kiện mới từ chuỗi xử lý (Bảng 3.8). Gửi lại cùng event_id không tạo trùng."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT event_id FROM violation_events WHERE event_id = ?", (ev.event_id,))
    if cur.fetchone():
        conn.close()
        return {"status": "ok", "message": "Event already exists", "event_id": ev.event_id}

    now = ev.system_time or datetime.now().isoformat()

    cur.execute("INSERT OR IGNORE INTO sources (source_id, name, created_at) VALUES (?, ?, ?)",
                (ev.source_id, f"Nguồn {ev.source_id}", now))
    cur.execute("INSERT OR IGNORE INTO monitoring_sessions (session_id, source_id, policy_version, start_time, status) VALUES (?, ?, ?, ?, 'active')",
                (ev.session_id, ev.source_id, ev.policy_version, now))

    cur.execute("""
    INSERT INTO violation_events (
        event_id, source_id, session_id, track_id, start_time, confirmed_at,
        last_seen_time, missing_items, event_state, policy_version, last_change_time, system_time
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ev.event_id, ev.source_id, ev.session_id, ev.track_id, ev.start_time,
        ev.confirmed_at, ev.last_seen_time, json.dumps(sorted(ev.missing_items)),
        ev.event_state, ev.policy_version, ev.confirmed_at, now
    ))

    cur.execute("""
    INSERT INTO event_history (event_id, t, change_type, missing_items, system_time)
    VALUES (?, ?, 'created', ?, ?)
    """, (ev.event_id, ev.confirmed_at, json.dumps(sorted(ev.missing_items)), now))

    if ev.evidence_refs:
        for ref in ev.evidence_refs:
            cur.execute("""
            INSERT INTO event_evidence (event_id, t, file_path, system_time)
            VALUES (?, ?, ?, ?)
            """, (ev.event_id, ref.get("t", ev.confirmed_at), ref.get("path", ""), now))

    conn.commit()
    conn.close()
    return {"status": "created", "event_id": ev.event_id}


@app.patch("/api/events/{event_id}")
def update_event(event_id: str, patch: EventPatchSchema):
    """PATCH /events/{event_id}: Cập nhật missing_items, trạng thái, last_seen_time, hoặc đóng sự kiện."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM violation_events WHERE event_id = ?", (event_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")

    updates = []
    params = []
    now = datetime.now().isoformat()

    if patch.last_seen_time is not None:
        updates.append("last_seen_time = ?")
        params.append(patch.last_seen_time)
    if patch.event_state is not None:
        updates.append("event_state = ?")
        params.append(patch.event_state)
    if patch.missing_items is not None:
        updates.append("missing_items = ?")
        params.append(json.dumps(sorted(patch.missing_items)))
    if patch.end_time is not None:
        updates.append("end_time = ?")
        params.append(patch.end_time)
    if patch.close_reason is not None:
        updates.append("close_reason = ?")
        params.append(patch.close_reason)
    if patch.last_change_time is not None:
        updates.append("last_change_time = ?")
        params.append(patch.last_change_time)

    if updates:
        sql = f"UPDATE violation_events SET {', '.join(updates)} WHERE event_id = ?"
        params.append(event_id)
        cur.execute(sql, params)

    t = patch.last_change_time or patch.last_seen_time or row["last_seen_time"]
    change_type = patch.change_type or patch.event_state or "updated"
    cur_items = json.dumps(sorted(patch.missing_items)) if patch.missing_items is not None else row["missing_items"]
    cur.execute("""
    INSERT INTO event_history (event_id, t, change_type, missing_items, system_time)
    VALUES (?, ?, ?, ?, ?)
    """, (event_id, t, change_type, cur_items, now))

    if patch.evidence_refs:
        for ref in patch.evidence_refs:
            cur.execute("""
            INSERT INTO event_evidence (event_id, t, file_path, system_time)
            VALUES (?, ?, ?, ?)
            """, (event_id, ref.get("t", t), ref.get("path", ""), now))

    conn.commit()
    conn.close()
    return {"status": "updated", "event_id": event_id}


@app.get("/api/events")
def list_events(
    source_id: Optional[str] = None,
    session_id: Optional[str] = None,
    state: Optional[str] = None,
    ppe: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """GET /events: Lọc theo nguồn, phiên, trạng thái, loại PPE thiếu, khoảng thời gian và từ khóa."""
    conn = get_db()
    cur = conn.cursor()

    where_clause, params = _build_events_query(source_id, session_id, state, date_from, date_to, q)
    cur.execute(f"SELECT * FROM violation_events {where_clause} ORDER BY system_time DESC, confirmed_at DESC", params)
    rows = cur.fetchall()

    matched_rows = []
    for r in rows:
        items = json.loads(r["missing_items"])
        if ppe and ppe not in items:
            continue
        matched_rows.append((r, items))

    total_matched = len(matched_rows)
    sliced = matched_rows[offset: offset + limit] if limit > 0 else matched_rows

    events = []
    for r, items in sliced:
        cur.execute("SELECT file_path FROM event_evidence WHERE event_id = ? LIMIT 1", (r["event_id"],))
        ev_row = cur.fetchone()
        thumb_url = None
        if ev_row and ev_row["file_path"]:
            thumb_name = Path(ev_row["file_path"]).name
            thumb_url = f"/api/evidence/{r['session_id']}/{thumb_name}"

        cur.execute("SELECT COUNT(*) FROM event_evidence WHERE event_id = ?", (r["event_id"],))
        ev_count = cur.fetchone()[0]

        cur.execute("SELECT feedback_type FROM event_feedback WHERE event_id = ? ORDER BY id DESC LIMIT 1", (r["event_id"],))
        fb_row = cur.fetchone()
        latest_feedback = fb_row["feedback_type"] if fb_row else None

        events.append({
            "event_id": r["event_id"],
            "source_id": r["source_id"],
            "session_id": r["session_id"],
            "track_id": r["track_id"],
            "start_time": r["start_time"],
            "confirmed_at": r["confirmed_at"],
            "last_seen_time": r["last_seen_time"],
            "missing_items": items,
            "event_state": r["event_state"],
            "end_time": r["end_time"],
            "close_reason": r["close_reason"],
            "policy_version": r["policy_version"],
            "last_change_time": r["last_change_time"],
            "system_time": r["system_time"],
            "thumbnail_url": thumb_url,
            "evidence_count": ev_count,
            "feedback": latest_feedback,
        })

    conn.close()
    return {"count": len(events), "total": total_matched, "events": events}


def extract_event_frames(row, cur):
    """Trích xuất và trả về danh sách ảnh theo từng mốc thời gian vi phạm của sự kiện."""
    event_id = row["event_id"]
    session_id = row["session_id"]
    track_id = row["track_id"]
    out_dir = get_evidence_dir() / session_id
    out_dir.mkdir(parents=True, exist_ok=True)

    cur.execute("SELECT * FROM event_evidence WHERE event_id = ? ORDER BY t ASC", (event_id,))
    ev_records = cur.fetchall()

    cur.execute("SELECT * FROM event_history WHERE event_id = ? ORDER BY t ASC", (event_id,))
    hist_records = cur.fetchall()

    milestones = []
    seen_items = None
    for h in hist_records:
        items = json.loads(h["missing_items"])
        if items != seen_items or not milestones:
            milestones.append((float(h["t"]), h["change_type"], items))
            seen_items = items
    if hist_records and float(hist_records[-1]["t"]) not in [m[0] for m in milestones]:
        milestones.append((float(hist_records[-1]["t"]), hist_records[-1]["change_type"], json.loads(hist_records[-1]["missing_items"])))

    if not milestones:
        milestones.append((float(row["confirmed_at"]), "confirmed", json.loads(row["missing_items"])))

    video_prefix = session_id.split("_")[0]
    video_file = ROOT / "data" / "videos" / f"{video_prefix}.mp4"
    cap = None
    if video_file.exists():
        import cv2
        cap = cv2.VideoCapture(str(video_file))

    frames = []
    for idx, (t_sec, ctype, items) in enumerate(milestones):
        matched_file = None
        for er in ev_records:
            if abs(float(er["t"]) - t_sec) < 0.05:
                matched_file = Path(er["file_path"]).name
                break

        if not matched_file:
            fname = f"{event_id}_t{int(t_sec*1000)}ms.jpg"
            target = out_dir / fname
            if not target.exists() and cap is not None:
                cap.set(cv2.CAP_PROP_POS_MSEC, int(t_sec * 1000))
                ret, frame = cap.read()
                if not ret:
                    total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    if total_f > 0:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total_f - 1))
                        ret, frame = cap.read()
                if ret:
                    w = frame.shape[1]
                    cv2.rectangle(frame, (0, 0), (w, 42), (15, 23, 42), -1)
                    items_str = ", ".join(items) if items else "Không thiếu trang bị"
                    banner = f"Moc t={t_sec:.2f}s | Nguoi ID {track_id} | {ctype} | Thieu: {items_str}"
                    cv2.putText(frame, banner, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.imwrite(str(target), frame)
            if target.exists():
                matched_file = fname

        rel_url = f"/api/evidence/{session_id}/{matched_file}" if matched_file else None

        label_map = {
            "created": "Bắt đầu & xác nhận vi phạm",
            "confirmed": "Xác nhận vi phạm",
            "missing_items": "Thay đổi danh sách vi phạm",
            "pending_observation": "Tạm che khuất (chờ quan sát)",
            "active": "Tái quan sát (đang vi phạm)",
            "closed": "Kết thúc vi phạm",
        }
        friendly_label = label_map.get(ctype, ctype)

        frames.append({
            "index": idx,
            "t": round(t_sec, 2),
            "label": f"Mốc {t_sec:.2f}s: {friendly_label}",
            "change_type": ctype,
            "missing_items": items,
            "url": rel_url
        })

    if cap is not None:
        cap.release()

    return frames


@app.get("/api/events/{event_id}")
def get_event_detail(event_id: str):
    """GET /events/{event_id}: Chi tiết sự kiện, danh sách minh chứng và toàn bộ lịch sử thay đổi."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM violation_events WHERE event_id = ?", (event_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")

    cur.execute("SELECT * FROM event_history WHERE event_id = ? ORDER BY t ASC", (event_id,))
    history = [
        {"t": h["t"], "change_type": h["change_type"], "missing_items": json.loads(h["missing_items"]), "system_time": h["system_time"]}
        for h in cur.fetchall()
    ]

    cur.execute("SELECT * FROM event_evidence WHERE event_id = ? ORDER BY t ASC", (event_id,))
    evidence = []
    for e in cur.fetchall():
        path = Path(e["file_path"])
        rel_url = f"/api/evidence/{row['session_id']}/{path.name}"
        evidence.append({"t": e["t"], "path": str(path), "url": rel_url, "system_time": e["system_time"]})

    frames = extract_event_frames(row, cur)

    cur.execute("SELECT * FROM event_feedback WHERE event_id = ? ORDER BY id DESC", (event_id,))
    feedbacks = [
        {
            "id": f["id"],
            "feedback_type": f["feedback_type"],
            "false_alarm_items": json.loads(f["false_alarm_items"]) if f["false_alarm_items"] else [],
            "notes": f["notes"],
            "system_time": f["system_time"]
        }
        for f in cur.fetchall()
    ]

    conn.close()
    return {
        "event_id": row["event_id"],
        "source_id": row["source_id"],
        "session_id": row["session_id"],
        "track_id": row["track_id"],
        "start_time": row["start_time"],
        "confirmed_at": row["confirmed_at"],
        "last_seen_time": row["last_seen_time"],
        "missing_items": json.loads(row["missing_items"]),
        "event_state": row["event_state"],
        "end_time": row["end_time"],
        "close_reason": row["close_reason"],
        "policy_version": row["policy_version"],
        "last_change_time": row["last_change_time"],
        "system_time": row["system_time"],
        "history": history,
        "evidence": evidence,
        "frames": frames,
        "feedbacks": feedbacks,
    }


@app.post("/api/events/{event_id}/feedback")
def submit_feedback(event_id: str, fb: FeedbackSchema):
    """POST /events/{event_id}/feedback: Tiếp nhận góp ý / đánh giá chỉnh sửa từ giám sát viên."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT event_id FROM violation_events WHERE event_id = ?", (event_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")
    now = datetime.now().isoformat()
    cur.execute("""
    INSERT INTO event_feedback (event_id, feedback_type, false_alarm_items, notes, system_time)
    VALUES (?, ?, ?, ?, ?)
    """, (event_id, fb.feedback_type, json.dumps(fb.false_alarm_items or []), fb.notes or "", now))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Đã lưu góp ý thành công", "system_time": now}


@app.get("/api/evidence/{session_id}/{filename}")
def serve_evidence(session_id: str, filename: str):
    """GET /events/{event_id}/evidence: Trả về tệp ảnh minh chứng cắt từ video."""
    ev_root = get_evidence_dir()
    target = ev_root / session_id / filename
    if not target.exists():
        matches = list(ev_root.glob(f"**/{filename}")) if ev_root.exists() else []
        if matches:
            target = matches[0]
        else:
            raise HTTPException(status_code=404, detail="Evidence image file not found")
    return FileResponse(str(target), media_type="image/jpeg")


@app.get("/api/stats")
def get_stats(source_id: Optional[str] = None, session_id: Optional[str] = None):
    """GET /api/stats: Thống kê sự kiện, trạng thái, phân bố 5 lớp PPE, phản hồi giám sát và phân bố theo nguồn/giờ."""
    conn = get_db()
    cur = conn.cursor()

    where_clause, params = _build_events_query(source_id=source_id, session_id=session_id)

    cur.execute(f"SELECT COUNT(*) FROM violation_events {where_clause}", params)
    total_events = cur.fetchone()[0]

    cur.execute(f"SELECT event_state, COUNT(*) FROM violation_events {where_clause} GROUP BY event_state", params)
    by_state = {r[0]: r[1] for r in cur.fetchall()}

    cur.execute(f"SELECT missing_items, system_time, source_id FROM violation_events {where_clause}", params)
    ppe_counts = {"helmet": 0, "vest": 0, "gloves": 0, "goggles": 0, "boots": 0}
    hourly_counts = {f"{h:02d}": 0 for h in range(24)}
    by_source: dict[str, int] = {}

    for r in cur.fetchall():
        items = json.loads(r["missing_items"])
        for it in items:
            if it in ppe_counts:
                ppe_counts[it] += 1
        src = r["source_id"]
        by_source[src] = by_source.get(src, 0) + 1
        st = r["system_time"] or ""
        if "T" in st and len(st.split("T")[1]) >= 2:
            hr = st.split("T")[1][:2]
            if hr in hourly_counts:
                hourly_counts[hr] += 1

    # Thống kê phản hồi giám sát viên (lấy phản hồi mới nhất của mỗi sự kiện)
    cur.execute("""
        SELECT f.feedback_type, COUNT(*)
        FROM event_feedback f
        INNER JOIN (
            SELECT event_id, MAX(id) AS max_id FROM event_feedback GROUP BY event_id
        ) latest ON f.id = latest.max_id
        GROUP BY f.feedback_type
    """)
    fb_map = {r[0]: r[1] for r in cur.fetchall()}
    reviewed_total = sum(fb_map.values())
    false_alarm_count = fb_map.get("false_alarm", 0)

    conn.close()
    return {
        "total_events": total_events,
        "active_events": by_state.get("active", 0),
        "pending_events": by_state.get("pending_observation", 0),
        "closed_events": by_state.get("closed", 0),
        "ppe_violations": ppe_counts,
        "by_source": by_source,
        "hourly_violations": hourly_counts,
        "feedback_summary": {
            "reviewed_events": reviewed_total,
            "correct_count": fb_map.get("correct", 0),
            "false_alarm_count": false_alarm_count,
            "false_alarm_rate": round(false_alarm_count / reviewed_total, 4) if reviewed_total > 0 else 0.0,
        },
    }


@app.get("/api/sources")
def list_sources():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sources ORDER BY source_id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/sessions")
def list_sessions(limit: int = 50):
    """Danh sách các phiên giám sát gần nhất kèm số lượng sự kiện của từng phiên."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*, COUNT(e.event_id) AS event_count
        FROM monitoring_sessions s
        LEFT JOIN violation_events e ON s.session_id = e.session_id
        GROUP BY s.session_id
        ORDER BY s.start_time DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/sources/{source_id}/policy")
def get_policy(source_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ppe_policies WHERE source_id = ? ORDER BY version DESC LIMIT 1", (source_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"source_id": source_id, "version": 1, "required_ppe": ["helmet", "vest", "gloves", "goggles", "boots"]}
    return {"source_id": source_id, "version": row["version"], "required_ppe": json.loads(row["required_ppe"]), "created_at": row["created_at"]}


@app.put("/api/sources/{source_id}/policy")
def update_policy(source_id: str, payload: PolicyUpdateSchema):
    """Lưu phiên bản chính sách mới. Nguồn đang chạy camera/video trực tiếp thì áp dụng ngay (đóng sự kiện đang mở với lý do
    policy_changed, đếm lại theo danh sách mới)."""
    bad = [p for p in payload.required_ppe if p not in KNOWN_PPE]
    if bad:
        raise HTTPException(status_code=400, detail=f"PPE không hợp lệ: {bad}; chỉ nhận {KNOWN_PPE}")
    payload.required_ppe = [p for p in KNOWN_PPE if p in set(payload.required_ppe)]
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("INSERT OR IGNORE INTO sources (source_id, name, source_type, created_at) VALUES (?, ?, 'camera', ?)",
                (source_id, f"Nguồn {source_id}", now))
    cur.execute("SELECT version FROM ppe_policies WHERE source_id = ? ORDER BY version DESC LIMIT 1", (source_id,))
    row = cur.fetchone()
    next_ver = (row["version"] + 1) if row else 1

    cur.execute("""
    INSERT INTO ppe_policies (source_id, version, required_ppe, created_at)
    VALUES (?, ?, ?, ?)
    """, (source_id, next_ver, json.dumps(payload.required_ppe), now))

    conn.commit()
    conn.close()
    # hot-apply cho mọi camera đang chạy cùng nguồn này (nhiều camera cùng lúc)
    applied = False
    for lv in _LIVES.values():
        if lv.source_id == source_id and lv.is_active():
            applied = lv.set_policy(payload.required_ppe, next_ver) or applied
    return {"source_id": source_id, "version": next_ver, "required_ppe": payload.required_ppe, "applied_live": applied}


# === CAMERA TRỰC TIẾP & TỆP VIDEO (backend/live.py, backend/video_file.py) ===
_sent_refs = {}   # event_id -> số ảnh minh chứng đã ghi vào database (PATCH chỉ gửi ảnh mới)


def _live_event(kind, ev):
    """Sự kiện từ chuỗi xử lý của camera/video: ghi thẳng vào SQLite bằng cùng hàm của POST/PATCH /api/events."""
    eid = ev["event_id"]
    refs = ev.get("evidence_refs") or []
    if kind == "created":
        create_event(EventCreateSchema(**ev))
    else:
        update_event(eid, EventPatchSchema(
            last_seen_time=ev.get("last_seen_time"), missing_items=ev.get("missing_items"),
            event_state=ev.get("event_state"), end_time=ev.get("end_time"), close_reason=ev.get("close_reason"),
            last_change_time=ev.get("last_change_time"), evidence_refs=refs[_sent_refs.get(eid, 0):] or None,
            change_type=kind))
    _sent_refs[eid] = len(refs)
    if kind == "closed":
        _sent_refs.pop(eid, None)


def _live_session(kind, info):
    conn = get_db()
    now = datetime.now().isoformat()
    if kind == "start":
        stype = info.get("source_type") or "camera"
        conn.execute("INSERT OR IGNORE INTO sources (source_id, name, source_type, created_at) "
                     "VALUES (?, ?, ?, ?)", (info["source_id"], f"Nguồn {info['source_id']}", stype, now))
        conn.execute("INSERT OR IGNORE INTO monitoring_sessions (session_id, source_id, policy_version, start_time, status) "
                     "VALUES (?, ?, ?, ?, 'active')", (info["session_id"], info["source_id"], info["policy_version"] or 1, now))
    else:
        conn.execute("UPDATE monitoring_sessions SET end_time = ?, status = ? WHERE session_id = ?",
                     (now, "error" if info.get("error") else "ended", info["session_id"]))
    conn.commit()
    conn.close()


LIVE_DEFAULT_SOURCE_ID = str(load_live_config().get("source_id", "cam0"))
MAX_PARALLEL = int(load_live_config().get("max_parallel", 4))
DISCOVERY_PORT = int(load_live_config().get("discovery_port", 50010))
_LIVES: dict[str, LiveCamera] = {}   # source_id -> LiveCamera: nhiều camera chạy đồng thời


def _full_camera_catalog() -> list[dict]:
    """Danh mục camera đầy đủ: catalog tĩnh (Fofu + webcam) + các nguồn URL người dùng
    đã thêm (lưu trong bảng sources cột rtsp_url — sống qua lần khởi động lại).
    Tên nguồn lấy theo database (người dùng có thể đổi thành tên khu vực trong xưởng)."""
    items = load_camera_catalog()
    have = {i["source_id"] for i in items}
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT source_id, name, rtsp_url FROM sources "
            "WHERE source_type = 'camera' AND rtsp_url IS NOT NULL AND rtsp_url != ''"
        ).fetchall()
        names = {r["source_id"]: r["name"] for r in
                 conn.execute("SELECT source_id, name FROM sources").fetchall()}
    finally:
        conn.close()
    for r in rows:
        if r["source_id"] in have:
            continue
        items.append({
            "source_id": r["source_id"],
            "name": r["name"],
            "camera_index": r["rtsp_url"],
            "source_type": "camera",
            "in_use": False,
        })
    # tên đã đặt lại trong database (tên khu vực) ưu tiên hơn tên mặc định
    for item in items:
        db_name = names.get(item["source_id"])
        if db_name:
            item["name"] = db_name
    return items


def get_live(source_id: str) -> LiveCamera:
    """Lấy (hoặc tạo) LiveCamera cho một nguồn camera; mỗi nguồn một phiên độc lập."""
    live = _LIVES.get(source_id)
    if live is None:
        live = LiveCamera(on_event=_live_event, on_session=_live_session)
        _LIVES[source_id] = live
    return live


def active_lives() -> list[LiveCamera]:
    """Các LiveCamera đang chạy phiên (mọi nguồn)."""
    return [lv for lv in _LIVES.values() if lv.is_active()]


def stop_all_lives():
    for lv in list(_LIVES.values()):
        try:
            lv.stop()
        except Exception:
            pass


def any_live_running() -> bool:
    return any(lv.is_active() for lv in _LIVES.values())


@app.post("/api/live/start")
def live_start(payload: Optional[LiveStartSchema] = Body(default=None)):
    """Mở webcam hoặc tệp video và chạy chuỗi xử lý với chính sách mới nhất của nguồn tương ứng."""
    req = payload or LiveStartSchema()
    source_type = "file" if str(req.source).lower() == "file" else "camera"

    if source_type == "file":
        if not req.path or not str(req.path).strip():
            raise HTTPException(status_code=400, detail="Chưa chọn đường dẫn tệp video")
        p = Path(str(req.path)).expanduser()
        src_id = sanitize_video_source_id(p)
        ensure_source(src_id, f"Video: {p.name}", "video", KNOWN_PPE)
        pol = get_policy(src_id)
        try:
            return get_live(src_id).start(
                pol["required_ppe"],
                pol["version"],
                source_type="file",
                file_path=str(p),
                playback_mode=req.mode,
                source_id=src_id,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))
    else:
        # chọn nguồn từ danh mục camera đầy đủ (cam0 + webcam + urlcam người dùng thêm)
        catalog = {c["source_id"]: c for c in _full_camera_catalog()}
        src_id = req.source_id or LIVE_DEFAULT_SOURCE_ID
        cam_entry = catalog.get(src_id)
        if cam_entry is None and isinstance(req.camera_index, int):
            src_id = f"webcam{req.camera_index}"
            cam_entry = catalog.get(src_id)
        if cam_entry is None:
            raise HTTPException(status_code=400,
                                detail=f"Không tìm thấy camera {src_id!r} trong danh mục. Hãy chọn lại trong dashboard.")
        # giới hạn số camera chạy pipeline đồng thời (configs/live.yaml: max_parallel)
        running = sum(1 for lv in _LIVES.values() if lv.is_active())
        already = src_id in _LIVES and _LIVES[src_id].is_active()
        if not already and running >= MAX_PARALLEL:
            raise HTTPException(status_code=409,
                                detail=f"Đã đạt tối đa {MAX_PARALLEL} camera chạy đồng thời "
                                       f"(configs/live.yaml: max_parallel). Hãy dừng bớt camera trước khi thêm.")
        ensure_source(src_id, cam_entry["name"], "camera", KNOWN_PPE)
        pol = get_policy(src_id)
        cam_idx = req.camera_index if req.camera_index is not None else cam_entry["camera_index"]
        try:
            return get_live(src_id).start(
                pol["required_ppe"],
                pol["version"],
                source_type="camera",
                camera_index=cam_idx,
                source_id=src_id,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))


def _find_file_live() -> Optional[LiveCamera]:
    for lv in _LIVES.values():
        if lv.is_active() and lv.source_type == "file":
            return lv
    return None


@app.post("/api/live/pause")
def live_pause(source_id: Optional[str] = Query(default=None)):
    live = _LIVES.get(source_id) if source_id else _find_file_live()
    if live is None:
        raise HTTPException(status_code=409, detail="Không có phiên tệp video nào đang phát")
    try:
        return live.pause()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/live/resume")
def live_resume(source_id: Optional[str] = Query(default=None)):
    live = _LIVES.get(source_id) if source_id else _find_file_live()
    if live is None:
        raise HTTPException(status_code=409, detail="Không có phiên tệp video nào đang tạm dừng")
    try:
        return live.resume()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/live/stop")
def live_stop(source_id: Optional[str] = Query(default=None)):
    """Dừng một nguồn (source_id) hoặc toàn bộ camera đang chạy."""
    if source_id:
        live = _LIVES.get(source_id)
        if live is None:
            raise HTTPException(status_code=404, detail=f"Không có phiên nào cho nguồn {source_id}")
        return live.stop()
    stop_all_lives()
    return {"stopped": "all"}


@app.get("/api/live/status")
def live_status(source_id: Optional[str] = Query(default=None)):
    """Trạng thái một nguồn, hoặc nguồn mặc định/đang chạy nếu không truyền (tương thích ngược)."""
    if source_id:
        live = _LIVES.get(source_id)
        if live is None:
            raise HTTPException(status_code=404, detail=f"Không có phiên nào cho nguồn {source_id}")
        return live.status()
    lives = active_lives()
    if lives:
        return lives[0].status()
    return get_live(LIVE_DEFAULT_SOURCE_ID).status()


@app.get("/api/live/statuses")
def live_statuses():
    """Trạng thái của tất cả nguồn camera đang được theo dõi (một request cho cả dashboard).
    Bỏ qua các nguồn idle chưa từng chạy để dashboard hiện empty-state thay vì tile đen."""
    def _interesting(lv: LiveCamera) -> bool:
        return lv.is_active() or lv.frames > 0 or lv.state in ("starting", "stopping", "error")
    return {"cameras": [lv.status() for lv in _LIVES.values() if _interesting(lv)], "max_parallel": MAX_PARALLEL}


@app.get("/api/live/stream")
def live_stream(source_id: Optional[str] = Query(default=None)):
    """Khung đã vẽ dạng MJPEG (dùng trực tiếp trong <img src>). Kết thúc khi camera dừng."""
    live = _LIVES.get(source_id) if source_id else (active_lives() or [None])[0]
    if live is None or not live.is_active():
        raise HTTPException(status_code=409, detail="Camera chưa chạy")
    return StreamingResponse(live.mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-store"})


@app.get("/api/live/snapshot")
def live_snapshot(source_id: Optional[str] = Query(default=None)):
    """Một ảnh JPEG mới nhất (để kiểm tra nhanh, không cần trình duyệt)."""
    live = _LIVES.get(source_id) if source_id else (active_lives() or [None])[0]
    if live is None:
        raise HTTPException(status_code=409, detail="Camera chưa chạy")
    jpg = live.latest_jpeg()
    if jpg is None:
        raise HTTPException(status_code=404, detail="Chưa có khung hình")
    return Response(content=jpg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


# === CÁC API QUẢN TRỊ ỨNG DỤNG DESKTOP (docs/desktop_app_plan.md mục 4.2) ===

@app.get("/api/cameras")
def list_cameras():
    """Danh mục camera người dùng có thể chọn theo dõi: webcam quét được + camera IP (Fofu)
    + các nguồn URL đã thêm + các camera tự quét được trong mạng LAN (UDP discovery)."""
    cfg = load_desktop_config()
    cam_cfg = cfg.get("camera") or {}
    max_idx = int(cam_cfg.get("max_probe_index", 3))
    active_int_indices = [lv.camera_index for lv in active_lives()
                          if lv.source_type == "camera" and isinstance(lv.camera_index, int)]
    webcams = probe_cameras(max_index=max_idx, active_indices=active_int_indices,
                            active_resolution=active_lives()[0].resolution if active_lives() else None)
    if not webcams:
        default_idx = int(cam_cfg.get("default_index", 0))
        webcams = [{
            "index": default_idx,
            "name": f"Webcam {default_idx} (Mặc định)",
            "width": int(cam_cfg.get("width", 1280)),
            "height": int(cam_cfg.get("height", 720)),
            "active": False,
        }]
    catalog = _full_camera_catalog()
    running = {lv.source_id for lv in active_lives()}
    for item in catalog:
        item["in_use"] = item["source_id"] in running
        if item["source_id"].startswith("webcam"):
            idx = int(item["source_id"].replace("webcam", ""))
            probe = next((w for w in webcams if w["index"] == idx), None)
            if probe:
                item["width"], item["height"] = probe["width"], probe["height"]
    return {
        "cameras": webcams,                       # giữ shape cũ cho nơi đang dùng
        "default_index": int(cam_cfg.get("default_index", 0)),
        "catalog": catalog,                        # danh sách chọn theo dõi (source_id + in_use)
        "discovered": get_discovered(),            # camera tự quét được trong mạng LAN
        "max_parallel": MAX_PARALLEL,
        "running": sorted(running),
    }


class CameraUrlSchema(BaseModel):
    name: str
    url: str


class SourceNameSchema(BaseModel):
    name: str


def _next_urlcam_id() -> str:
    conn = get_db()
    try:
        rows = conn.execute("SELECT source_id FROM sources WHERE source_id LIKE 'urlcam%'").fetchall()
    finally:
        conn.close()
    nums = [int(r["source_id"].replace("urlcam", "")) for r in rows
            if r["source_id"].replace("urlcam", "").isdigit()]
    return f"urlcam{max(nums, default=0) + 1}"


def _auto_add_discovered_worker():
    """Nền: mỗi 5 giây kiểm tra camera vừa được phát hiện trong LAN (UDP) và
    tự thêm vào danh mục (bảng sources, rtsp_url) nếu chưa có — người dùng chỉ
    cần chạy laptop_cam_server trên laptop khác, app tự thấy, tick chọn là chạy.
    Tắt bằng auto_add_discovered: false trong configs/live.yaml."""
    while True:
        time.sleep(5.0)
        try:
            if not bool(load_live_config().get("auto_add_discovered", True)):
                continue
            for cam in get_discovered():
                conn = get_db()
                try:
                    row = conn.execute("SELECT source_id, name FROM sources WHERE rtsp_url = ? LIMIT 1",
                                       (cam["url"],)).fetchone()
                finally:
                    conn.close()
                if row:
                    continue
                src_id = _next_urlcam_id()
                ensure_source(src_id, f"{cam['name']} (LAN)", "camera", KNOWN_PPE, rtsp_url=cam["url"])
                print(f"[discovery] tự thêm camera LAN: {src_id} = '{cam['name']}' -> {cam['url']}", flush=True)
        except Exception as e:
            print(f"[discovery] auto-add lỗi: {e!r}", flush=True)


@app.post("/api/cameras/url")
def add_camera_url(payload: CameraUrlSchema):
    """Thêm camera ngoài bằng URL stream (MJPEG/RTSP) — ví dụ iPhone app, laptop_cam_server."""
    url = str(payload.url).strip()
    name = str(payload.name).strip() or "Camera ngoài"
    if not url.lower().startswith(("http://", "https://", "rtsp://", "rtmp://")):
        raise HTTPException(status_code=400, detail="URL phải bắt đầu bằng http://, rtsp:// hoặc rtmp://")
    # trùng URL đã có thì trả lại nguồn cũ thay vì tạo trùng
    conn = get_db()
    try:
        row = conn.execute("SELECT source_id, name FROM sources WHERE rtsp_url = ? LIMIT 1", (url,)).fetchone()
    finally:
        conn.close()
    if row:
        return {"source_id": row["source_id"], "name": row["name"], "url": url, "existed": True}
    src_id = _next_urlcam_id()
    ensure_source(src_id, name, "camera", KNOWN_PPE, rtsp_url=url)
    return {"source_id": src_id, "name": name, "url": url, "existed": False}


@app.get("/api/cameras/discovered")
def list_discovered():
    """Camera trong mạng LAN tự quảng cáo qua UDP (laptop_cam_server) — còn 'thở' trong 12s gần nhất."""
    return {"discovered": get_discovered(), "discovery_port": DISCOVERY_PORT}


@app.put("/api/sources/{source_id}/name")
def rename_source_route(source_id: str, payload: SourceNameSchema):
    """Đặt tên khu vực cho camera (hiện trong tile, feed sự kiện và bảng thống kê theo nguồn)."""
    name = str(payload.name).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên nguồn không được để trống")
    conn = get_db()
    try:
        row = conn.execute("SELECT source_id FROM sources WHERE source_id = ?", (source_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Không có nguồn {source_id}")
    finally:
        conn.close()
    rename_source(source_id, name)
    return {"source_id": source_id, "name": name}


@app.get("/api/evidence/path")
def evidence_path():
    """Đường dẫn thư mục gốc chứa ảnh minh chứng (để nút 'Mở thư mục minh chứng' dùng)."""
    return {"path": str(get_evidence_dir())}


@app.get("/api/settings")
def get_settings():
    """Đọc cấu hình hiệu lực của ứng dụng desktop (kèm danh sách mẫu quy định PPE `presets`)."""
    cfg = load_desktop_config()
    return {
        "camera": cfg.get("camera") or {},
        "processing": cfg.get("processing") or {},
        "paths": {"data_dir": str(get_data_dir(cfg)), "configured_data_dir": (cfg.get("paths") or {}).get("data_dir", "")},
        "retention": cfg.get("retention") or {},
        "alerts": cfg.get("alerts") or {},
        "presets": cfg.get("presets") or [],
    }


@app.put("/api/settings")
def update_settings(patch: dict[str, Any] = Body(...)):
    """Lưu cài đặt người dùng vào `%LOCALAPPDATA%\\PPEMonitor\\settings.yaml` (không sửa file gốc trong bộ cài)."""
    merged = save_user_settings(patch)
    return {
        "status": "ok",
        "message": "Đã lưu cài đặt hệ thống",
        "settings": {
            "camera": merged.get("camera") or {},
            "processing": merged.get("processing") or {},
            "paths": {"data_dir": str(get_data_dir(merged)), "configured_data_dir": (merged.get("paths") or {}).get("data_dir", "")},
            "retention": merged.get("retention") or {},
            "alerts": merged.get("alerts") or {},
            "presets": merged.get("presets") or [],
        },
    }


@app.post("/api/settings/cleanup")
def cleanup_old_data(req: Optional[CleanupRequestSchema] = Body(default=None)):
    """Xóa các sự kiện và ảnh minh chứng cũ hơn N ngày theo xác nhận của người quản trị."""
    cfg = load_desktop_config()
    days = int((req.keep_days if req and req.keep_days is not None else (cfg.get("retention") or {}).get("keep_days", 30)))
    if days < 1:
        raise HTTPException(status_code=400, detail="Số ngày giữ dữ liệu phải >= 1")
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT event_id, session_id FROM violation_events WHERE system_time < ? AND event_state = 'closed'",
        (cutoff,),
    )
    old_events = cur.fetchall()
    removed_files = 0
    ev_root = get_evidence_dir(cfg)

    for ev in old_events:
        cur.execute("SELECT file_path FROM event_evidence WHERE event_id = ?", (ev["event_id"],))
        for er in cur.fetchall():
            fname = Path(er["file_path"]).name
            candidate = ev_root / ev["session_id"] / fname
            if candidate.exists():
                try:
                    candidate.unlink()
                    removed_files += 1
                except Exception:
                    pass
        cur.execute("DELETE FROM violation_events WHERE event_id = ?", (ev["event_id"],))

    conn.commit()
    conn.close()
    return {
        "status": "ok",
        "deleted_events": len(old_events),
        "deleted_files": removed_files,
        "keep_days": days,
    }


@app.get("/api/system")
def get_system_info():
    """Thông tin hệ thống, phần cứng GPU/CPU, dung lượng đĩa, đường dẫn dữ liệu và thông số mô hình (chỉ đọc)."""
    cfg = load_desktop_config()
    pipe_path = resolve_resource("configs/pipeline.yaml")
    pipe_cfg = yaml.safe_load(pipe_path.read_text(encoding="utf-8")) if pipe_path.exists() else {}

    det_cfg = pipe_cfg.get("detector") or {}
    det_rel = str(det_cfg.get("weights") or "")
    det_file = resolve_resource(det_rel) if det_rel else Path()
    det_exists = det_file.exists() and det_file.is_file()

    pose_cfg = pipe_cfg.get("pose") or {}
    part_cfg = pipe_cfg.get("part_cls") or {}

    gpu_available = False
    gpu_name = None
    torch_version = None
    try:
        import torch

        torch_version = torch.__version__
        gpu_available = bool(torch.cuda.is_available())
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    pref_dev = str((cfg.get("processing") or {}).get("device") or "auto").lower()
    active_device = "CPU"
    if pref_dev != "cpu" and gpu_available:
        active_device = f"CUDA ({gpu_name})"

    data_dir = get_data_dir(cfg)
    disk_free_gb = None
    disk_total_gb = None
    try:
        target_check = data_dir if data_dir.exists() else data_dir.parent
        usage = shutil.disk_usage(str(target_check))
        disk_free_gb = round(usage.free / (1024 ** 3), 2)
        disk_total_gb = round(usage.total / (1024 ** 3), 2)
    except Exception:
        pass

    low_disk_warn_gb = float((cfg.get("retention") or {}).get("low_disk_warn_gb", 2.0))

    return {
        "app_name": APP_NAME,
        "app_version": str((cfg.get("app") or {}).get("version") or APP_VERSION),
        "git_commit": _get_git_commit(),
        "desktop_mode": is_desktop_mode(),
        "compute": {
            "configured": pref_dev,
            "active_device": active_device,
            "gpu_available": gpu_available,
            "gpu_name": gpu_name,
            "torch_version": torch_version,
        },
        "storage": {
            "data_dir": str(data_dir),
            "db_path": str(get_db_path(cfg)),
            "evidence_dir": str(get_evidence_dir(cfg)),
            "logs_dir": str(get_logs_dir(cfg)),
            "disk_free_gb": disk_free_gb,
            "disk_total_gb": disk_total_gb,
            "low_disk_warning": bool(disk_free_gb is not None and disk_free_gb < low_disk_warn_gb),
        },
        "model": {
            "detector_weights": det_rel,
            "detector_model_name": det_file.parent.parent.name if len(det_file.parents) >= 2 else det_file.name,
            "detector_exists": det_exists,
            "detector_sha256": _short_sha256(det_file) if det_exists else None,
            "imgsz": det_cfg.get("imgsz"),
            "conf_person": det_cfg.get("conf_person"),
            "conf_ppe": det_cfg.get("conf_ppe"),
            "pose_enabled": bool(pose_cfg.get("enabled")),
            "pose_weights": pose_cfg.get("weights"),
            "part_cls_enabled": bool(part_cfg.get("enabled")),
            "temporal": pipe_cfg.get("temporal") or {},
            "compliance": {
                "tau_in": (pipe_cfg.get("compliance") or {}).get("tau_in"),
                "tau_occ": (pipe_cfg.get("compliance") or {}).get("tau_occ"),
                "area_min_px": (pipe_cfg.get("compliance") or {}).get("area_min_px"),
            },
        },
    }


def _collect_export_rows(
    source_id: Optional[str] = None,
    session_id: Optional[str] = None,
    state: Optional[str] = None,
    ppe: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
):
    conn = get_db()
    cur = conn.cursor()
    where_clause, params = _build_events_query(source_id, session_id, state, date_from, date_to, q)
    cur.execute(f"SELECT * FROM violation_events {where_clause} ORDER BY system_time DESC, confirmed_at DESC", params)
    rows = cur.fetchall()

    exported = []
    evidence_files: list[tuple[Path, str]] = []
    ev_root = get_evidence_dir()

    for r in rows:
        items = json.loads(r["missing_items"])
        if ppe and ppe not in items:
            continue

        cur.execute("SELECT file_path FROM event_evidence WHERE event_id = ? ORDER BY t ASC", (r["event_id"],))
        ev_rows = cur.fetchall()

        cur.execute(
            "SELECT feedback_type, false_alarm_items, notes FROM event_feedback WHERE event_id = ? ORDER BY id DESC LIMIT 1",
            (r["event_id"],),
        )
        fb = cur.fetchone()
        fb_str = ""
        if fb:
            fa_items = json.loads(fb["false_alarm_items"]) if fb["false_alarm_items"] else []
            fb_str = fb["feedback_type"]
            if fa_items:
                fb_str += f" ({','.join(fa_items)})"
            if fb["notes"]:
                fb_str += f": {fb['notes']}"

        for er in ev_rows:
            fname = Path(er["file_path"]).name
            candidate = ev_root / r["session_id"] / fname
            if not candidate.exists() and ev_root.exists():
                matches = list(ev_root.glob(f"**/{fname}"))
                if matches:
                    candidate = matches[0]
            if candidate.exists() and candidate.is_file():
                evidence_files.append((candidate, f"evidence/{r['session_id']}/{fname}"))

        exported.append({
            "event_id": r["event_id"],
            "source_id": r["source_id"],
            "session_id": r["session_id"],
            "track_id": r["track_id"],
            "status": r["event_state"],
            "missing_items": ", ".join(items),
            "started_at": r["system_time"],
            "confirmed_at": round(float(r["confirmed_at"] or 0.0), 2),
            "closed_at": round(float(r["end_time"]), 2) if r["end_time"] is not None else "",
            "close_reason": r["close_reason"] or "",
            "policy_version": r["policy_version"],
            "evidence_count": len(ev_rows),
            "feedback": fb_str,
        })

    conn.close()
    return exported, evidence_files


def _build_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    """Tạo nội dung CSV mã hóa UTF-8 có BOM (\ufeff) để Microsoft Excel mở hiển thị đúng tiếng Việt."""
    fieldnames = [
        "event_id",
        "source_id",
        "session_id",
        "track_id",
        "status",
        "missing_items",
        "started_at",
        "confirmed_at",
        "closed_at",
        "close_reason",
        "policy_version",
        "evidence_count",
        "feedback",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return "\ufeff".encode("utf-8") + buf.getvalue().encode("utf-8")


@app.get("/api/export/events.csv")
def export_events_csv(
    source_id: Optional[str] = None,
    session_id: Optional[str] = None,
    state: Optional[str] = None,
    ppe: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
):
    """Xuất danh sách sự kiện theo bộ lọc ra tệp CSV (UTF-8 có BOM cho Excel)."""
    rows, _ = _collect_export_rows(source_id, session_id, state, ppe, date_from, date_to, q)
    csv_bytes = _build_csv_bytes(rows)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    headers = {"Content-Disposition": f'attachment; filename="ppe_events_{stamp}.csv"'}
    return Response(content=csv_bytes, media_type="text/csv; charset=utf-8", headers=headers)


@app.get("/api/export/events.zip")
def export_events_zip(
    source_id: Optional[str] = None,
    session_id: Optional[str] = None,
    state: Optional[str] = None,
    ppe: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
):
    """Xuất gói ZIP gồm bảng `events.csv` và toàn bộ tệp ảnh minh chứng của các sự kiện theo bộ lọc."""
    rows, ev_files = _collect_export_rows(source_id, session_id, state, ppe, date_from, date_to, q)
    csv_bytes = _build_csv_bytes(rows)
    zip_buf = io.BytesIO()
    added_arcs = set()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("events.csv", csv_bytes)
        for src_path, arcname in ev_files:
            if arcname not in added_arcs:
                zf.write(src_path, arcname=arcname)
                added_arcs.add(arcname)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    headers = {"Content-Disposition": f'attachment; filename="ppe_events_evidence_{stamp}.zip"'}
    return Response(content=zip_buf.getvalue(), media_type="application/zip", headers=headers)


@app.get("/api/health")
def health_check():
    """Kiểm tra trạng thái sẵn sàng của máy chủ nội bộ (dùng bởi cửa sổ desktop lúc khởi động)."""
    running = [lv.source_id for lv in active_lives()]
    return {
        "status": "ok",
        "desktop": is_desktop_mode(),
        "live_state": "running" if running else (get_live(LIVE_DEFAULT_SOURCE_ID).state or "idle"),
        "running_cameras": running,
    }


@app.post("/api/desktop/focus")
def desktop_focus():
    """Đưa cửa sổ đang mở lên trước khi người dùng bấm mở ứng dụng lần thứ hai."""
    if callable(_FOCUS_CALLBACK):
        try:
            _FOCUS_CALLBACK()
        except Exception:
            pass
    return {"status": "ok"}


# Mount Static Files Dashboard
DASHBOARD_DIR = resolve_resource("dashboard")
if not DASHBOARD_DIR.exists():
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/dashboard", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")
