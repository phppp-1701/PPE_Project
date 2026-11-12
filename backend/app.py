"""FastAPI Backend cho Hệ thống giám sát vi phạm PPE 6 lớp (docs/spec.md mục 6, Bảng 3.8)."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import ROOT, ensure_default_sources, get_db, init_db

app = FastAPI(
    title="Hệ thống Giám sát Trang bị Bảo hộ Lao động (PPE-6)",
    description="API quản lý sự kiện vi phạm, ảnh minh chứng và chính sách 6 lớp PPE theo thời gian thực",
    version="1.0.0",
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
    ensure_default_sources()


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



# === API ENDPOINTS ===

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard/index.html")


@app.post("/api/events")
def create_event(ev: EventCreateSchema):
    """POST /events: Tạo sự kiện mới từ chuỗi xử lý (Bảng 3.8). Gửi lại cùng event_id không tạo trùng."""
    conn = get_db()
    cur = conn.cursor()

    # Kiểm tra sự kiện đã tồn tại chưa
    cur.execute("SELECT event_id FROM violation_events WHERE event_id = ?", (ev.event_id,))
    if cur.fetchone():
        conn.close()
        return {"status": "ok", "message": "Event already exists", "event_id": ev.event_id}

    now = ev.system_time or datetime.now().isoformat()

    # Đảm bảo source & session tồn tại
    cur.execute("INSERT OR IGNORE INTO sources (source_id, name, created_at) VALUES (?, ?, ?)",
                (ev.source_id, f"Nguồn {ev.source_id}", now))
    cur.execute("INSERT OR IGNORE INTO monitoring_sessions (session_id, source_id, policy_version, start_time, status) VALUES (?, ?, ?, ?, 'active')",
                (ev.session_id, ev.source_id, ev.policy_version, now))

    # Thêm sự kiện
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

    # Ghi nhật ký khởi tạo
    cur.execute("""
    INSERT INTO event_history (event_id, t, change_type, missing_items, system_time)
    VALUES (?, ?, 'created', ?, ?)
    """, (ev.event_id, ev.confirmed_at, json.dumps(sorted(ev.missing_items)), now))

    # Ghi minh chứng (nếu có)
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

    # Thêm bản ghi lịch sử nếu có thay đổi
    t = patch.last_change_time or patch.last_seen_time or row["last_seen_time"]
    change_type = patch.change_type or patch.event_state or "updated"
    cur_items = json.dumps(sorted(patch.missing_items)) if patch.missing_items is not None else row["missing_items"]
    cur.execute("""
    INSERT INTO event_history (event_id, t, change_type, missing_items, system_time)
    VALUES (?, ?, ?, ?, ?)
    """, (event_id, t, change_type, cur_items, now))

    # Thêm minh chứng mới nếu có
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
    state: Optional[str] = None,
    ppe: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """GET /events: Lọc theo nguồn, trạng thái (active, pending_observation, closed), loại PPE thiếu."""
    conn = get_db()
    cur = conn.cursor()

    conditions = []
    params = []

    if source_id:
        conditions.append("source_id = ?")
        params.append(source_id)
    if state:
        conditions.append("event_state = ?")
        params.append(state)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    cur.execute(f"SELECT * FROM violation_events {where_clause} ORDER BY confirmed_at DESC LIMIT ? OFFSET ?", (*params, limit, offset))
    rows = cur.fetchall()

    events = []
    for r in rows:
        items = json.loads(r["missing_items"])
        if ppe and ppe not in items:
            continue

        # Lấy ảnh minh chứng đầu tiên làm thumbnail
        cur.execute("SELECT file_path FROM event_evidence WHERE event_id = ? LIMIT 1", (r["event_id"],))
        ev_row = cur.fetchone()
        thumb_url = None
        if ev_row and ev_row["file_path"]:
            thumb_name = Path(ev_row["file_path"]).name
            thumb_url = f"/api/evidence/{r['session_id']}/{thumb_name}"

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
            "last_change_time": r["last_change_time"],
            "system_time": r["system_time"],
            "thumbnail_url": thumb_url,
        })

    conn.close()
    return {"count": len(events), "events": events}


def extract_event_frames(row, cur):
    """Trích xuất và trả về danh sách ảnh theo từng mốc thời gian vi phạm của sự kiện."""
    event_id = row["event_id"]
    session_id = row["session_id"]
    track_id = row["track_id"]
    out_dir = ROOT / "outputs" / "evidence" / session_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Minh chứng đã ghi nhận trong bảng event_evidence
    cur.execute("SELECT * FROM event_evidence WHERE event_id = ? ORDER BY t ASC", (event_id,))
    ev_records = cur.fetchall()

    # 2. Toàn bộ lịch sử các mốc thay đổi trạng thái
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

    # Mở video nếu có tệp video gốc
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

    # Lấy các khung hình theo từng mốc thời gian
    frames = extract_event_frames(row, cur)

    # Lấy phản hồi / góp ý của giám sát viên
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
    target = ROOT / "outputs" / "evidence" / session_id / filename
    if not target.exists():
        # Kiểm tra tìm kiếm trong toàn bộ outputs/evidence
        matches = list((ROOT / "outputs" / "evidence").glob(f"**/{filename}"))
        if matches:
            target = matches[0]
        else:
            raise HTTPException(status_code=404, detail="Evidence image file not found")
    return FileResponse(str(target), media_type="image/jpeg")


@app.get("/api/stats")
def get_stats():
    """GET /events/stats: Thống kê số lượng sự kiện, trạng thái và số lượt vi phạm theo 6 lớp PPE."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM violation_events")
    total_events = cur.fetchone()[0]

    cur.execute("SELECT event_state, COUNT(*) FROM violation_events GROUP BY event_state")
    by_state = {r[0]: r[1] for r in cur.fetchall()}

    cur.execute("SELECT missing_items FROM violation_events")
    ppe_counts = {"helmet": 0, "vest": 0, "gloves": 0, "goggles": 0, "boots": 0}
    for r in cur.fetchall():
        items = json.loads(r[0])
        for it in items:
            if it in ppe_counts:
                ppe_counts[it] += 1

    conn.close()
    return {
        "total_events": total_events,
        "active_events": by_state.get("active", 0),
        "pending_events": by_state.get("pending_observation", 0),
        "closed_events": by_state.get("closed", 0),
        "ppe_violations": ppe_counts,
    }


@app.get("/api/sources")
def list_sources():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sources ORDER BY source_id")
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
    return {"source_id": source_id, "version": row["version"], "required_ppe": json.loads(row["required_ppe"])}


@app.put("/api/sources/{source_id}/policy")
def update_policy(source_id: str, payload: PolicyUpdateSchema):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT version FROM ppe_policies WHERE source_id = ? ORDER BY version DESC LIMIT 1", (source_id,))
    row = cur.fetchone()
    next_ver = (row["version"] + 1) if row else 1
    now = datetime.now().isoformat()

    cur.execute("""
    INSERT INTO ppe_policies (source_id, version, required_ppe, created_at)
    VALUES (?, ?, ?, ?)
    """, (source_id, next_ver, json.dumps(payload.required_ppe), now))

    conn.commit()
    conn.close()
    return {"source_id": source_id, "version": next_ver, "required_ppe": payload.required_ppe}


# Mount Static Files Dashboard
DASHBOARD_DIR = ROOT / "dashboard"
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/dashboard", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")

