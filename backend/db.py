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

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "ppe.db"


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
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


if __name__ == "__main__":
    init_db()
    ensure_default_sources()
    print("Khởi tạo cơ sở dữ liệu SQLite thành công tại:", DB_PATH)

