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

