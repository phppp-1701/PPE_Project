"""Kiểm thử tự động cho vỏ ứng dụng desktop Windows (docs/desktop_app_plan.md, mốc M1).

Tất cả bài kiểm thử dùng thư mục tạm (`tmp_path`) và cơ sở dữ liệu SQLite tạm, không cần GPU, webcam hay tệp trọng số.
"""

from __future__ import annotations

import json
import socket
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from desktop.main import (  # noqa: E402
    BackendServer,
    SingleInstanceGuard,
    create_diagnostic_zip,
    focus_existing_instance,
    pick_free_port,
    setup_logging,
)
from desktop.paths import (  # noqa: E402
    bundle_root,
    ensure_user_dirs,
    get_data_dir,
    get_db_path,
    get_evidence_dir,
    get_logs_dir,
    get_user_settings_path,
    load_desktop_config,
    resolve_resource,
    save_user_settings,
)


def test_paths_default_web_mode_preserves_outputs(monkeypatch):
    """Chế độ web / pytest thông thường phải giữ nguyên đường dẫn `outputs/ppe.db` và `outputs/evidence`."""
    monkeypatch.delenv("PPE_DESKTOP_MODE", raising=False)
    monkeypatch.delenv("PPE_DATA_DIR", raising=False)
    assert get_data_dir() == bundle_root() / "outputs"
    assert get_db_path() == bundle_root() / "outputs" / "ppe.db"
    assert get_evidence_dir() == bundle_root() / "outputs" / "evidence"


def test_paths_desktop_mode_uses_localappdata_and_never_overwrites_bundle_config(tmp_path, monkeypatch):
    """Chế độ desktop lưu dữ liệu vào `%LOCALAPPDATA%\\PPEMonitor` và ghi cài đặt riêng vào `settings.yaml`."""
    fake_local = tmp_path / "LocalAppData"
    monkeypatch.setenv("PPE_DESKTOP_MODE", "1")
    monkeypatch.delenv("PPE_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(fake_local))

    original_bundle_yaml = resolve_resource("configs/desktop.yaml").read_text(encoding="utf-8")

    data_dir = ensure_user_dirs()
    assert data_dir == fake_local / "PPEMonitor"
    assert get_db_path() == fake_local / "PPEMonitor" / "ppe.db"
    assert (data_dir / "evidence").is_dir()
    assert (data_dir / "logs").is_dir()
    assert (data_dir / "exports").is_dir()

    merged = save_user_settings({
        "camera": {"default_index": 2, "width": 1920, "height": 1080},
        "alerts": {"sound_enabled": True},
        "server": {"port": 9999},  # mục không nằm trong ALLOWED_USER_SECTIONS phải bị bỏ qua
    })
    assert merged["camera"]["default_index"] == 2
    assert merged["camera"]["width"] == 1920
    assert merged["alerts"]["sound_enabled"] is True
    assert merged["server"]["port"] == 0

    user_file = get_user_settings_path()
    assert user_file.exists()
    reloaded = load_desktop_config()
    assert reloaded["camera"]["default_index"] == 2
    # Cấu hình gốc trong bộ cài không bị thay đổi
    assert resolve_resource("configs/desktop.yaml").read_text(encoding="utf-8") == original_bundle_yaml


def test_paths_pyinstaller_frozen_resolution(tmp_path, monkeypatch):
    """Giả lập môi trường đóng gói PyInstaller (`sys.frozen` + `sys._MEIPASS`) để kiểm quy đổi tài nguyên."""
    fake_dist = tmp_path / "dist" / "PPEMonitor"
    fake_internal = fake_dist / "_internal"
    (fake_internal / "configs").mkdir(parents=True)
    sample_cfg = fake_internal / "configs" / "desktop.yaml"
    sample_cfg.write_text("app:\n  name: PPE Monitor\n  slug: PPEMonitor\n", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(fake_internal), raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_dist / "PPEMonitor.exe"))

    assert bundle_root() == fake_internal.resolve()
    assert resolve_resource("configs/desktop.yaml") == sample_cfg.resolve()

    # Tệp đặt trực tiếp cạnh `.exe` (vd. cập nhật trọng số ngoài) được ưu tiên hơn `_internal`
    external_override = fake_dist / "configs" / "desktop.yaml"
    external_override.parent.mkdir(parents=True, exist_ok=True)
    external_override.write_text("app:\n  name: Override\n", encoding="utf-8")
    assert resolve_resource("configs/desktop.yaml") == external_override.resolve()


def test_pick_free_port_avoids_busy_port():
    """Chọn cổng tự động trả cổng hợp lệ và tự né khi cổng ưu tiên đang bận."""
    p1 = pick_free_port("127.0.0.1", 0)
    assert 1024 <= p1 <= 65535

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        busy_port = occupied.getsockname()[1]
        fallback_port = pick_free_port("127.0.0.1", busy_port)
        assert fallback_port != busy_port and fallback_port > 0


def test_single_instance_lock_blocks_second_process(tmp_path):
    """Chỉ một tiến trình giữ được `app.lock`; tiến trình thứ hai bị chặn cho tới khi nhả khóa."""
    lock_file = tmp_path / "app.lock"
    info_file = tmp_path / "instance.json"

    g1 = SingleInstanceGuard(lock_file, info_file)
    g2 = SingleInstanceGuard(lock_file, info_file)
    assert g1.acquire() is True
    g1.write_info(port=51234, title="PPE Monitor Test")
    assert info_file.exists()

    assert g2.acquire() is False
    g1.release()
    assert not info_file.exists()

    assert g2.acquire() is True
    g2.release()


def test_backend_server_lifecycle_crash_recovery_and_focus(tmp_path, monkeypatch):
    """Máy chủ nền khởi động ở cổng tự chọn, phục hồi sự kiện treo (`app_crash_recovered`), nhận tín hiệu focus và dừng sạch."""
    import urllib.request
    import backend.db as db_mod

    monkeypatch.setenv("PPE_DESKTOP_MODE", "1")
    monkeypatch.setenv("PPE_DATA_DIR", str(tmp_path / "userdata"))
    ensure_user_dirs()
    db_mod.configure_db_path(get_db_path())
    db_mod.init_db()

    # Giả lập sự kiện & phiên đang mở bị kẹt do lần trước tắt bằng Task Manager
    conn = db_mod.get_db()
    now = "2026-11-18T10:00:00"
    conn.execute("INSERT INTO sources (source_id, name, source_type, created_at) VALUES ('cam0', 'Webcam', 'camera', ?)", (now,))
    conn.execute(
        "INSERT INTO monitoring_sessions (session_id, source_id, policy_version, start_time, status) "
        "VALUES ('crashed_s1', 'cam0', 1, ?, 'active')",
        (now,),
    )
    conn.execute(
        "INSERT INTO violation_events ("
        "event_id, source_id, session_id, track_id, start_time, confirmed_at, last_seen_time, "
        "missing_items, event_state, policy_version, last_change_time, system_time"
        ") VALUES ('ev_crashed', 'cam0', 'crashed_s1', 4, 1.0, 2.5, 6.0, '[\"helmet\"]', 'active', 1, 2.5, ?)",
        (now,),
    )
    conn.commit()
    conn.close()

    focused_calls = []
    srv = BackendServer(host="127.0.0.1", port=0)
    info_path = tmp_path / "instance.json"
    info_path.write_text(json.dumps({"pid": 999999, "port": srv.port, "title": "NonExistentWindow"}), encoding="utf-8")

    try:
        srv.start(focus_callback=lambda: focused_calls.append(True))
        assert srv.wait_ready(timeout_s=10.0) is True

        # Kiểm tra /api/health
        with urllib.request.urlopen(f"{srv.base_url}/api/health", timeout=2.0) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        assert health["status"] == "ok" and health["desktop"] is True

        # Kiểm tra phục hồi sự kiện treo sau sự cố tắt đột ngột
        with urllib.request.urlopen(f"{srv.base_url}/api/events/ev_crashed", timeout=2.0) as resp:
            ev_detail = json.loads(resp.read().decode("utf-8"))
        assert ev_detail["event_state"] == "closed"
        assert ev_detail["close_reason"] == "app_crash_recovered"

        conn = db_mod.get_db()
        sess_status = conn.execute(
            "SELECT status FROM monitoring_sessions WHERE session_id = 'crashed_s1'"
        ).fetchone()["status"]
        conn.close()
        assert sess_status == "recovered"

        # Kiểm tra mở app lần hai gọi cửa sổ thứ nhất lên trước qua HTTP nội bộ
        assert focus_existing_instance(info_path) is True
        assert focused_calls == [True]
    finally:
        srv.stop(timeout_s=5.0)

    assert srv._thread is None or not srv._thread.is_alive()


def test_rotating_logs_and_diagnostic_zip_exclude_media(tmp_path, monkeypatch):
    """Log xoay vòng giữ tối đa 7 file; gói chẩn đoán ZIP chỉ chứa thông tin kỹ thuật, không chứa ảnh/video."""
    monkeypatch.setenv("PPE_DESKTOP_MODE", "1")
    monkeypatch.setenv("PPE_DATA_DIR", str(tmp_path / "diag_data"))
    cfg = load_desktop_config()
    cfg["logging"] = {"level": "INFO", "max_files": 7, "max_bytes": 262_144}

    ensure_user_dirs(cfg)
    # Tạo một ảnh minh chứng giả trong evidence/ để chắc chắn gói chẩn đoán KHÔNG gom ảnh
    fake_img = get_evidence_dir(cfg) / "s1" / "secret_worker.jpg"
    fake_img.parent.mkdir(parents=True, exist_ok=True)
    fake_img.write_bytes(b"\xff\xd8\xff\xd9")

    log_file = setup_logging(cfg)
    import logging

    lg = logging.getLogger("ppe_desktop")
    lg.info("Dòng log kiểm thử M1")
    for h in lg.handlers:
        h.flush()

    assert log_file.exists()
    assert get_logs_dir(cfg) == log_file.parent

    zip_out = tmp_path / "diagnostic.zip"
    create_diagnostic_zip(zip_out, cfg)
    assert zip_out.exists()

    with zipfile.ZipFile(zip_out, "r") as zf:
        names = set(zf.namelist())
        assert "diagnostic_info.json" in names
        assert "desktop_effective.yaml" in names
        assert "configs/pipeline.yaml" in names
        assert "logs/ppe_monitor.log" in names
        assert not any(n.endswith((".jpg", ".png", ".mp4", ".avi")) for n in names)
        loaded_eff = yaml.safe_load(zf.read("desktop_effective.yaml").decode("utf-8"))
        assert loaded_eff["app"]["name"] == "PPE Monitor"


def test_summarize_persons_in_frame_inspector():
    """Bảng Đối tượng trong khung hình (Admin Inspector) phân loại đúng trạng thái từng người và từng PPE."""
    from types import SimpleNamespace
    from backend.live import summarize_persons_in_frame

    tr1 = SimpleNamespace(track_id=4, confident=True)
    tr2 = SimpleNamespace(track_id=7, confident=True)
    out = {
        "tracks": [tr1, tr2],
        "lost": [(9, [0, 0, 10, 10])],
        "states": {
            4: {
                "helmet": {"state": "have"},
                "vest": {"state": "have"},
                "gloves": {"state": "missing"},
                "boots": {"state": "have"},
            },
            7: {
                "helmet": {"state": "have"},
                "vest": {"state": "have"},
                "gloves": {"state": "have"},
                "boots": {"state": "have"},
            },
        },
        "checks": {
            4: {"gloves": SimpleNamespace(missing_confirmed=True)},
            7: {},
        },
    }
    open_ev = {4: {"event_id": "ev_04", "event_state": "active", "missing_items": ["gloves"]}}
    summary = summarize_persons_in_frame(out, ["helmet", "vest", "gloves", "boots"], open_ev)

    assert len(summary) == 3
    # Người đang vi phạm được ưu tiên xếp đầu danh sách
    assert summary[0]["track_id"] == 4
    assert summary[0]["status"] == "violation"
    assert summary[0]["items"]["gloves"] == "missing"
    assert summary[0]["items"]["goggles"] == "unchecked"
    assert summary[0]["confirmed_missing"] == ["gloves"]
    assert summary[0]["event_id"] == "ev_04"

    p7 = next(x for x in summary if x["track_id"] == 7)
    assert p7["status"] == "compliant"
    assert p7["items"]["helmet"] == "have"

    p9 = next(x for x in summary if x["track_id"] == 9)
    assert p9["status"] == "lost"


def test_video_file_sequential_playback_and_export_apis(tmp_path, monkeypatch):
    """Kiểm thử chạy nguồn tệp video tuần tự (pause/resume, thời gian theo khung) và các API xuất CSV/ZIP, cài đặt, hệ thống."""
    import cv2
    import numpy as np
    from fastapi.testclient import TestClient
    import backend.app as app_mod
    import backend.db as db_mod
    from backend.live import LiveCamera, load_live_config
    from tests.test_live import FakePipe, wait_for

    monkeypatch.setenv("PPE_DESKTOP_MODE", "1")
    monkeypatch.setenv("PPE_DATA_DIR", str(tmp_path / "app_data"))
    ensure_user_dirs()
    db_mod.configure_db_path(get_db_path())

    # Tạo một tệp video ngắn 12 khung bằng OpenCV trong thư mục tạm
    vid_path = tmp_path / "sample_worksite.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(vid_path), fourcc, 10.0, (160, 120))
    for i in range(12):
        writer.write(np.full((120, 160, 3), i * 15, dtype=np.uint8))
    writer.release()
    assert vid_path.exists()

    seen_timestamps = []

    class RecordingPipe(FakePipe):
        def process(self, frame, t):
            seen_timestamps.append(round(t, 3))
            return super().process(frame, t)

    cam = LiveCamera(
        load_live_config(),
        on_event=app_mod._live_event,
        on_session=app_mod._live_session,
        pipeline_factory=lambda s, sess, emit: RecordingPipe(s, sess, emit),
        draw_factory=lambda: (lambda f, o, c: f),
    )
    monkeypatch.setattr(app_mod, "LIVE", cam)

    with TestClient(app_mod.app) as c:
        # 1. Kiểm tra giao diện Dashboard & các module JS/CSS tĩnh
        for asset in (
            "/dashboard/index.html",
            "/dashboard/css/app.css",
            "/dashboard/js/api.js",
            "/dashboard/js/monitor.js",
            "/dashboard/js/events.js",
            "/dashboard/js/settings.js",
        ):
            r_asset = c.get(asset)
            assert r_asset.status_code == 200

        # 2. Kiểm tra API /api/system và /api/settings
        sys_res = c.get("/api/system").json()
        assert sys_res["app_name"] == "PPE Monitor"
        assert "model" in sys_res and "storage" in sys_res

        put_res = c.put("/api/settings", json={"alerts": {"sound_enabled": True}, "retention": {"keep_days": 14}}).json()
        assert put_res["settings"]["alerts"]["sound_enabled"] is True
        assert put_res["settings"]["retention"]["keep_days"] == 14

        # 3. Chạy tệp video ở chế độ nhanh (fast) và kiểm tra thời gian theo khung t = idx / fps
        st = c.post("/api/live/start", json={"source": "file", "path": str(vid_path), "mode": "fast"}).json()
        assert st["source_type"] == "file"
        assert wait_for(lambda: cam.state == "idle" and cam.frames == 12, timeout=5.0)

        # Không bỏ khung nào, thời gian khớp chính xác 0.0, 0.1, 0.2, ..., 1.1s
        assert len(seen_timestamps) == 12
        assert seen_timestamps[:4] == [0.0, 0.1, 0.2, 0.3]

        # Sự kiện tạo ra từ tệp video đã được lưu vào SQLite
        ev_list = c.get("/api/events").json()
        assert ev_list["total"] >= 1
        ev_id = ev_list["events"][0]["event_id"]

        # Gửi đánh giá giám sát viên có tiếng Việt
        fb_res = c.post(
            f"/api/events/{ev_id}/feedback",
            json={"feedback_type": "false_alarm", "false_alarm_items": ["helmet"], "notes": "Đội mũ khuất bóng râm"},
        )
        assert fb_res.status_code == 200

        # 4. Xuất CSV (UTF-8 có BOM) và ZIP
        csv_resp = c.get("/api/export/events.csv")
        assert csv_resp.status_code == 200
        raw_csv = csv_resp.content
        assert raw_csv.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM cho Excel
        csv_text = raw_csv.decode("utf-8-sig")
        assert ev_id in csv_text and "Đội mũ khuất bóng râm" in csv_text

        zip_resp = c.get("/api/export/events.zip")
        assert zip_resp.status_code == 200
        import io
        with zipfile.ZipFile(io.BytesIO(zip_resp.content), "r") as zf:
            assert "events.csv" in zf.namelist()


