"""Kiểm API backend cho bảng FR (16/11/2026): chạy FastAPI bằng TestClient với SQLite TẠM (không đụng outputs/ppe.db).

Đẩy sự kiện thật của một lượt chạy video (events.jsonl của annotated_main/video3, bản cuối) qua POST/PATCH như
05_run_video, rồi đọc lại: danh sách, lọc, chi tiết, ảnh minh chứng, thống kê, nguồn, chính sách theo nguồn, phản hồi.
Ghi fr_api_check.json. Không đổi code backend.

Chạy (từ thư mục gốc, .venv): python outputs/results/close_eval/final/fr_api_check.py
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import backend.db as db  # noqa: E402

tmp = Path(tempfile.mkdtemp()) / "fr_check.db"
db.DB_PATH = tmp                      # SQLite tạm
from fastapi.testclient import TestClient  # noqa: E402

from backend.app import app  # noqa: E402

res = {"db_tam": str(tmp)}
ev_file = ROOT / "outputs" / "results" / "close_eval" / "annotated_main" / "video3" / "events.jsonl"
changes = [json.loads(line) for line in ev_file.read_text(encoding="utf-8").splitlines() if line.strip()]
with TestClient(app) as c:
    posted, patched, errs = 0, 0, []
    for ev in changes:
        if ev["change"] == "created":
            body = {k: ev[k] for k in ("event_id", "source_id", "session_id", "track_id", "start_time", "confirmed_at",
                                       "last_seen_time", "missing_items", "event_state", "policy_version",
                                       "evidence_refs", "history") if k in ev}
            r = c.post("/api/events", json=body)
            posted += r.status_code == 200
        else:
            body = {k: ev.get(k) for k in ("last_seen_time", "missing_items", "event_state", "end_time", "close_reason",
                                           "last_change_time", "evidence_refs")}
            body["change_type"] = ev["change"]
            r = c.patch(f"/api/events/{ev['event_id']}", json=body)
            patched += r.status_code == 200
        if r.status_code != 200:
            errs.append((ev["change"], r.status_code, r.text[:200]))
    n_events = len({e["event_id"] for e in changes})
    lst = c.get("/api/events", params={"limit": 200}).json()
    items = lst if isinstance(lst, list) else lst.get("events", lst.get("items", []))
    first = changes[0]["event_id"]
    det = c.get(f"/api/events/{first}")
    detail = det.json() if det.status_code == 200 else {}
    refs = detail.get("evidence_refs") or changes[0].get("evidence_refs") or []
    img = None
    if refs:
        p = Path(refs[0]["path"])
        img = c.get(f"/api/evidence/{p.parent.name}/{p.name}")
    stats = c.get("/api/stats").json()
    srcs = c.get("/api/sources").json()
    pol0 = c.get("/api/sources/video/policy").json()
    put = c.put("/api/sources/video/policy", json={"required_ppe": ["helmet", "vest"]}).json()
    pol1 = c.get("/api/sources/video/policy").json()
    fb = c.post(f"/api/events/{first}/feedback", json={"feedback_type": "correct", "notes": "kiểm FR"})
    filt = c.get("/api/events", params={"limit": 200, "source_id": "video"})
    home = c.get("/", follow_redirects=False)
    res.update(
        su_kien_trong_file=n_events, thay_doi=len(changes), post_ok=posted, patch_ok=patched, loi=errs,
        danh_sach_tra_ve=len(items), chi_tiet_status=det.status_code,
        chi_tiet_co_lich_su=bool(detail.get("history")), anh_minh_chung_status=img.status_code if img else None,
        anh_minh_chung_bytes=len(img.content) if img is not None else 0, anh_minh_chung_loai=img.headers.get("content-type") if img else None,
        thong_ke=stats, nguon=srcs, chinh_sach_truoc=pol0, chinh_sach_sau_put=put, chinh_sach_doc_lai=pol1,
        phan_hoi_status=fb.status_code, loc_theo_nguon_status=filt.status_code, trang_chu_status=home.status_code,
        trang_chu_location=home.headers.get("location"))
out = Path(__file__).with_name("fr_api_check.json")
out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k not in ("nguon",)}, ensure_ascii=False, indent=1))
print("Ghi", out.relative_to(ROOT))
