"""Nạp các sự kiện vi phạm từ outputs/results/video/*/events.jsonl vào database SQLite."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.db import get_db, init_db, ensure_default_sources


def import_jsonl(clear_existing=False):
    init_db()
    ensure_default_sources()
    conn = get_db()
    cur = conn.cursor()

    if clear_existing:
        cur.execute("DELETE FROM event_evidence")
        cur.execute("DELETE FROM event_history")
        cur.execute("DELETE FROM violation_events")
        conn.commit()

    # Chỉ nạp các video thử nghiệm chính thức đã hiệu chuẩn (video4, video5, video6, video7)
    # Loại trừ video cũ uncalibrated từ giai đoạn thử nghiệm ban đầu (video1, video2)
    valid_videos = {"video4", "video5", "video6", "video7"}
    all_jsonl = list((ROOT / "outputs" / "results" / "video").glob("*/events.jsonl"))
    jsonl_files = [jf for jf in all_jsonl if jf.parent.name in valid_videos]
    print(f"Tìm thấy {len(jsonl_files)} tệp events.jsonl hợp lệ: {[jf.parent.name for jf in jsonl_files]}")

    total_events = 0
    for jf in jsonl_files:
        video_name = jf.parent.name
        for line in jf.read_text(encoding="utf-8").strip().splitlines():
            if not line:
                continue
            rec = json.loads(line)
            ev_id = rec["event_id"]
            change = rec.get("change", "created")

            cur.execute("SELECT event_id FROM violation_events WHERE event_id = ?", (ev_id,))
            exists = cur.fetchone()

            if change == "created" or not exists:
                cur.execute("INSERT OR IGNORE INTO sources (source_id, name, created_at) VALUES (?, ?, ?)",
                            (rec["source_id"], f"Video {rec['source_id']}", rec.get("system_time", "")))
                cur.execute("INSERT OR IGNORE INTO monitoring_sessions (session_id, source_id, policy_version, start_time, status) VALUES (?, ?, ?, ?, 'active')",
                            (rec["session_id"], rec["source_id"], rec.get("policy_version", 1), rec.get("system_time", "")))

                cur.execute("""
                INSERT OR REPLACE INTO violation_events (
                    event_id, source_id, session_id, track_id, start_time, confirmed_at,
                    last_seen_time, missing_items, event_state, end_time, close_reason,
                    policy_version, last_change_time, system_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ev_id, rec["source_id"], rec["session_id"], rec["track_id"], rec["start_time"],
                    rec["confirmed_at"], rec["last_seen_time"], json.dumps(sorted(rec["missing_items"])),
                    rec["event_state"], rec.get("end_time"), rec.get("close_reason"),
                    rec.get("policy_version", 1), rec.get("last_change_time", rec["confirmed_at"]),
                    rec.get("system_time", "")
                ))
                total_events += 1

                for ref in rec.get("evidence_refs", []):
                    cur.execute("""
                    INSERT INTO event_evidence (event_id, t, file_path, system_time)
                    VALUES (?, ?, ?, ?)
                    """, (ev_id, ref["t"], ref["path"], rec.get("system_time", "")))

            else:
                cur.execute("""
                UPDATE violation_events SET
                    last_seen_time = ?, missing_items = ?, event_state = ?,
                    end_time = ?, close_reason = ?, last_change_time = ?
                WHERE event_id = ?
                """, (
                    rec["last_seen_time"], json.dumps(sorted(rec["missing_items"])), rec["event_state"],
                    rec.get("end_time"), rec.get("close_reason"), rec.get("last_change_time", rec["last_seen_time"]),
                    ev_id
                ))

            # Luôn ghi history
            cur.execute("""
            INSERT INTO event_history (event_id, t, change_type, missing_items, system_time)
            VALUES (?, ?, ?, ?, ?)
            """, (ev_id, rec.get("last_change_time", rec.get("confirmed_at", 0)), change, json.dumps(sorted(rec["missing_items"])), rec.get("system_time", "")))

    conn.commit()
    conn.close()
    print(f"Đã nạp thành công các sự kiện vào SQLite outputs/ppe.db!")


if __name__ == "__main__":
    clear = "--clear" in sys.argv
    import_jsonl(clear_existing=clear)
