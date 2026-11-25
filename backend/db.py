"""Cơ sở dữ liệu SQLite cho hệ thống giám sát vi phạm PPE 6 lớp (docs/spec.md mục 6).

Bao gồm 6 bảng:
    - sources: Nguồn camera hoặc tệp video
    - ppe_policies: Cấu hình PPE bắt buộc (phiên bản hóa)
    - monitoring_sessions: Phiên giám sát
    - violation_events: Sự kiện vi phạm (mỗi đợt vi phạm liên tục)
    - event_history: Nhật ký thay đổi trạng thái và trang bị thiếu
    - event_evidence: Đường dẫn các ảnh minh chứng
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from desktop.paths import bundle_root, get_db_path

ROOT = bundle_root()
DB_PATH = get_db_path()


def configure_db_path(path: Path | None = None) -> Path:
    """Cập nhật lại đường dẫn SQLite theo cấu hình hiện hành (dùng khi khởi động app desktop)."""
    global DB_PATH
    DB_PATH = Path(path) if path is not None else get_db_path()
    init_db()
    return DB_PATH


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # nhiều camera ghi sự kiện đồng thời: WAL + busy_timeout để không văng "database is locked"
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # 1. Bảng Nguồn (Sources)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        source_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        source_type TEXT NOT NULL DEFAULT 'video',
        rtsp_url TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    # 2. Bảng Chính sách PPE (PPE Policies)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ppe_policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        required_ppe TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(source_id) REFERENCES sources(source_id) ON DELETE CASCADE,
        UNIQUE(source_id, version)
    )
    """)

    # 3. Bảng Phiên giám sát (Monitoring Sessions)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS monitoring_sessions (
        session_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        policy_version INTEGER NOT NULL DEFAULT 1,
        start_time TEXT NOT NULL,
        end_time TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        FOREIGN KEY(source_id) REFERENCES sources(source_id)
    )
    """)

    # 4. Bảng Sự kiện vi phạm (Violation Events)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS violation_events (
        event_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        track_id INTEGER NOT NULL,
        start_time REAL NOT NULL,
        confirmed_at REAL NOT NULL,
        last_seen_time REAL NOT NULL,
        missing_items TEXT NOT NULL,
        event_state TEXT NOT NULL DEFAULT 'active',
        end_time REAL,
        close_reason TEXT,
        policy_version INTEGER NOT NULL DEFAULT 1,
        last_change_time REAL NOT NULL,
        system_time TEXT NOT NULL,
        FOREIGN KEY(source_id) REFERENCES sources(source_id),
        FOREIGN KEY(session_id) REFERENCES monitoring_sessions(session_id)
    )
    """)

    # 5. Bảng Nhật ký thay đổi PPE (Event PPE History)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS event_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL,
        t REAL NOT NULL,
        change_type TEXT NOT NULL,
        missing_items TEXT NOT NULL,
        system_time TEXT NOT NULL,
        FOREIGN KEY(event_id) REFERENCES violation_events(event_id) ON DELETE CASCADE
    )
    """)

    # 6. Bảng Minh chứng vi phạm (Event Evidence)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS event_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL,
        t REAL NOT NULL,
        file_path TEXT NOT NULL,
        system_time TEXT NOT NULL,
        FOREIGN KEY(event_id) REFERENCES violation_events(event_id) ON DELETE CASCADE
    )
    """)

    # 7. Bảng Phản hồi / Góp ý của Giám sát viên (Event Feedback & Corrections)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS event_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL,
        feedback_type TEXT NOT NULL,
        false_alarm_items TEXT,
        notes TEXT,
        system_time TEXT NOT NULL,
        FOREIGN KEY(event_id) REFERENCES violation_events(event_id) ON DELETE CASCADE
    )
    """)

    # Chỉ mục tối ưu truy vấn
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON violation_events(source_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_state ON violation_events(event_state)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON violation_events(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_event ON event_feedback(event_id)")

    conn.commit()
    conn.close()


def ensure_source(source_id, name, source_type, required_ppe, rtsp_url=None):
    """Tạo nguồn (vd. webcam của chế độ trực tiếp) kèm chính sách phiên bản 1 nếu chưa có; có rồi thì giữ nguyên.
    `rtsp_url`: URL stream cho camera IP thêm từ dashboard (khác NULL thì lưu vào bảng sources)."""
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute("INSERT OR IGNORE INTO sources (source_id, name, source_type, rtsp_url, is_active, created_at) "
                 "VALUES (?, ?, ?, ?, 1, ?)", (source_id, name, source_type, rtsp_url, now))
    conn.execute("INSERT OR IGNORE INTO ppe_policies (source_id, version, required_ppe, created_at) VALUES (?, 1, ?, ?)",
                 (source_id, json.dumps(list(required_ppe)), now))
    conn.commit()
    conn.close()


def rename_source(source_id, name):
    """Đặt lại tên nguồn = tên khu vực trong xưởng (hiện trong tile, feed sự kiện, thống kê)."""
    conn = get_db()
    conn.execute("UPDATE sources SET name = ? WHERE source_id = ?", (name, source_id))
    conn.commit()
    conn.close()


def ensure_default_sources():
    """Tạo sẵn các nguồn video mặc định kèm chính sách 6 lớp."""
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    default_ppe = json.dumps(["helmet", "vest", "gloves", "goggles", "boots"])

    sources = [
        ("video", "Luồng Video Trực tiếp / Mặc định", "video", None),
        ("video4", "Video 4 (Công trường 3 công nhân)", "video", None),
        ("video5", "Video 5 (Công trường bắt tay)", "video", None),
        ("video6", "Video 6 (Công trường cắt biên chân)", "video", None),
    ]

    for sid, name, stype, url in sources:
        cur.execute("INSERT OR IGNORE INTO sources (source_id, name, source_type, rtsp_url, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)", (sid, name, stype, url, now))
        cur.execute("INSERT OR IGNORE INTO ppe_policies (source_id, version, required_ppe, created_at) VALUES (?, 1, ?, ?)", (sid, default_ppe, now))

    conn.commit()
    conn.close()


def recover_crashed_sessions(close_reason: str = "app_crash_recovered") -> dict:
    """Đóng các sự kiện và phiên giám sát còn treo từ lần tắt đột ngột trước (docs/desktop_app_plan.md mục 7)."""
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()

    cur.execute(
        "SELECT event_id, last_seen_time, missing_items FROM violation_events "
        "WHERE event_state IN ('active', 'pending_observation')"
    )
    open_events = cur.fetchall()
    for ev in open_events:
        t = float(ev["last_seen_time"] or 0.0)
        cur.execute(
            "UPDATE violation_events SET event_state = 'closed', end_time = ?, close_reason = ?, last_change_time = ? "
            "WHERE event_id = ?",
            (t, close_reason, t, ev["event_id"]),
        )
        cur.execute(
            "INSERT INTO event_history (event_id, t, change_type, missing_items, system_time) VALUES (?, ?, 'closed', ?, ?)",
            (ev["event_id"], t, ev["missing_items"], now),
        )

    cur.execute("SELECT COUNT(*) FROM monitoring_sessions WHERE status = 'active'")
    open_sessions = cur.fetchone()[0]
    if open_sessions:
        cur.execute(
            "UPDATE monitoring_sessions SET end_time = ?, status = 'recovered' WHERE status = 'active'",
            (now,),
        )

    conn.commit()
    conn.close()
    return {"recovered_events": len(open_events), "recovered_sessions": open_sessions}


if __name__ == "__main__":
    init_db()
    ensure_default_sources()
    print("Khởi tạo cơ sở dữ liệu SQLite thành công tại:", DB_PATH)

