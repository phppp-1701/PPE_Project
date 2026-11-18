"""Quản lý đường dẫn và cấu hình khi chạy từ mã nguồn hoặc từ bộ cài PyInstaller (docs/desktop_app_plan.md mục 3).

Nguyên tắc:
- Khi chạy bản web / pytest thông thường (không bật PPE_DESKTOP_MODE và không đóng gói): giữ nguyên `outputs/ppe.db`
  và `outputs/evidence/` để toàn bộ bài kiểm thử và luồng web hiện tại không đổi.
- Khi chạy ứng dụng desktop (`PPE_DESKTOP_MODE=1` hoặc tiến trình đóng gói `sys.frozen`): tài nguyên chỉ đọc lấy từ
  thư mục cài đặt (`sys._MEIPASS` / cạnh file `.exe`), còn dữ liệu người dùng (SQLite, minh chứng, cài đặt, CSV, log,
  file lock) nằm trong `%LOCALAPPDATA%\\PPEMonitor\\` (hoặc `PPE_DATA_DIR` nếu được chỉ định).
"""

from __future__ import annotations

import copy
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from . import APP_SLUG

ALLOWED_USER_SECTIONS = {"camera", "processing", "paths", "retention", "alerts", "presets"}


def is_frozen() -> bool:
    """Trả về True khi chạy từ bộ đóng gói PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def is_desktop_mode() -> bool:
    """Trả về True khi đang chạy ở chế độ ứng dụng desktop (đóng gói hoặc đặt PPE_DESKTOP_MODE=1)."""
    flag = os.environ.get("PPE_DESKTOP_MODE", "").strip().lower()
    return is_frozen() or flag in ("1", "true", "yes")


def exe_dir() -> Path:
    """Thư mục chứa file thực thi khi đóng gói, hoặc thư mục gốc repo khi chạy từ mã nguồn."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def bundle_root() -> Path:
    """Thư mục gốc chứa tài nguyên đóng gói (`configs/`, `dashboard/`, `scripts/`)."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            mp = Path(meipass).resolve()
            if (mp / "configs").exists():
                return mp
        return exe_dir()
    return Path(__file__).resolve().parents[1]


def resolve_resource(rel_path: str | Path) -> Path:
    """Tìm đường dẫn thực tế của tài nguyên chỉ đọc (cấu hình, dashboard, trọng số).

    Khi đóng gói chế độ thư mục (onedir), ưu tiên file đặt cạnh `.exe` trước (tiện cập nhật trọng số ngoài nếu cần),
    sau đó tới `_internal` (`sys._MEIPASS`).
    """
    p = Path(rel_path)
    if p.is_absolute():
        return p
    if is_frozen():
        beside_exe = exe_dir() / p
        if beside_exe.exists():
            return beside_exe
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            in_bundle = Path(meipass).resolve() / p
            if in_bundle.exists():
                return in_bundle
    return bundle_root() / p


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Gộp đệ quy hai dict mà không làm thay đổi dict gốc."""
    merged = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = copy.deepcopy(v)
    return merged


def default_desktop_data_dir(slug: str = APP_SLUG) -> Path:
    """Thư mục dữ liệu người dùng mặc định trên Windows: `%LOCALAPPDATA%\\PPEMonitor`."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / slug
    return Path.home() / "AppData" / "Local" / slug


def load_base_desktop_config() -> dict[str, Any]:
    """Đọc cấu hình mặc định `configs/desktop.yaml` trong thư mục mã nguồn / bộ cài."""
    cfg_path = resolve_resource("configs/desktop.yaml")
    if not cfg_path.exists():
        return {
            "app": {"name": "PPE Monitor", "slug": APP_SLUG, "title": "PPE Monitor", "version": "1.0.0",
                    "min_width": 1280, "min_height": 720, "maximized": True},
            "server": {"host": "127.0.0.1", "port": 0, "startup_timeout_s": 30.0, "shutdown_timeout_s": 5.0},
            "paths": {"data_dir": ""},
            "camera": {"default_index": 0, "max_probe_index": 4, "backend": "dshow", "width": 1280, "height": 720},
            "processing": {"device": "auto"},
            "retention": {"keep_days": 30, "auto_cleanup": False, "low_disk_warn_gb": 2.0},
            "alerts": {"sound_enabled": False, "toast_duration_ms": 5000},
            "logging": {"level": "INFO", "max_files": 7, "max_bytes": 5242880},
            "presets": [],
        }
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


def _expand_path(raw: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def get_base_state_dir(base_cfg: dict[str, Any] | None = None) -> Path:
    """Thư mục gốc cố định để lưu khóa phiên bản chạy và `settings.yaml` gốc của người dùng."""
    env_dir = os.environ.get("PPE_DATA_DIR", "").strip()
    if env_dir:
        return _expand_path(env_dir)
    cfg = base_cfg if base_cfg is not None else load_base_desktop_config()
    slug = (cfg.get("app") or {}).get("slug") or APP_SLUG
    return default_desktop_data_dir(slug)


def get_user_settings_path(base_cfg: dict[str, Any] | None = None) -> Path:
    """Đường dẫn file lưu cài đặt riêng của người dùng (không ghi đè `configs/desktop.yaml` của bộ cài)."""
    return get_base_state_dir(base_cfg) / "settings.yaml"


def load_desktop_config() -> dict[str, Any]:
    """Đọc `configs/desktop.yaml` kết hợp với bản ghi đè `settings.yaml` của người dùng (nếu có)."""
    base = load_base_desktop_config()
    user_file = get_user_settings_path(base)
    if user_file.exists():
        try:
            user_cfg = yaml.safe_load(user_file.read_text(encoding="utf-8")) or {}
            if isinstance(user_cfg, dict):
                filtered = {k: v for k, v in user_cfg.items() if k in ALLOWED_USER_SECTIONS}
                return deep_merge(base, filtered)
        except Exception:
            pass
    return base


def save_user_settings(patch: dict[str, Any]) -> dict[str, Any]:
    """Lưu phần cấu hình được phép chỉnh của người dùng vào `settings.yaml` và trả về cấu hình sau khi gộp."""
    clean_patch = {k: v for k, v in (patch or {}).items() if k in ALLOWED_USER_SECTIONS}
    base = load_base_desktop_config()
    user_file = get_user_settings_path(base)
    existing: dict[str, Any] = {}
    if user_file.exists():
        try:
            loaded = yaml.safe_load(user_file.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                existing = {k: v for k, v in loaded.items() if k in ALLOWED_USER_SECTIONS}
        except Exception:
            existing = {}
    updated_user = deep_merge(existing, clean_patch)
    user_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = user_file.with_suffix(".yaml.tmp")
    tmp_file.write_text(yaml.safe_dump(updated_user, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp_file.replace(user_file)
    return deep_merge(base, updated_user)


def get_data_dir(cfg: dict[str, Any] | None = None) -> Path:
    """Thư mục dữ liệu hiện hành.

    - Nếu đặt `PPE_DATA_DIR`: luôn ưu tiên biến môi trường này.
    - Nếu ở chế độ desktop (`PPE_DESKTOP_MODE=1` hoặc đã đóng gói `.exe`): dùng `paths.data_dir` trong cấu hình
      nếu có, mặc định `%LOCALAPPDATA%\\PPEMonitor`.
    - Ngược lại (bản web / `pytest`): giữ nguyên `<repo>/outputs` như trước.
    """
    env_dir = os.environ.get("PPE_DATA_DIR", "").strip()
    if env_dir:
        return _expand_path(env_dir)
    if is_desktop_mode():
        resolved_cfg = cfg if cfg is not None else load_desktop_config()
        custom = ((resolved_cfg.get("paths") or {}).get("data_dir") or "").strip()
        if custom:
            return _expand_path(custom)
        slug = (resolved_cfg.get("app") or {}).get("slug") or APP_SLUG
        return default_desktop_data_dir(slug)
    return bundle_root() / "outputs"


def get_db_path(cfg: dict[str, Any] | None = None) -> Path:
    """Đường dẫn cơ sở dữ liệu SQLite (`ppe.db`)."""
    return get_data_dir(cfg) / "ppe.db"


def get_evidence_dir(cfg: dict[str, Any] | None = None) -> Path:
    """Thư mục lưu ảnh minh chứng của các sự kiện vi phạm."""
    return get_data_dir(cfg) / "evidence"


def get_logs_dir(cfg: dict[str, Any] | None = None) -> Path:
    """Thư mục ghi log xoay vòng của ứng dụng desktop."""
    return get_data_dir(cfg) / "logs"


def get_exports_dir(cfg: dict[str, Any] | None = None) -> Path:
    """Thư mục mặc định gợi ý khi xuất CSV / ZIP."""
    return get_data_dir(cfg) / "exports"


def get_lock_path(base_cfg: dict[str, Any] | None = None) -> Path:
    """Đường dẫn file khóa đảm bảo chỉ một phiên bản ứng dụng chạy tại một thời điểm."""
    return get_base_state_dir(base_cfg) / "app.lock"


def get_instance_info_path(base_cfg: dict[str, Any] | None = None) -> Path:
    """Đường dẫn file lưu thông tin tiến trình đang mở (PID, cổng, tiêu đề cửa sổ) để gọi cửa sổ lên trước."""
    return get_base_state_dir(base_cfg) / "instance.json"


def ensure_user_dirs(cfg: dict[str, Any] | None = None) -> Path:
    """Tạo sẵn các thư mục dữ liệu người dùng và kiểm tra quyền ghi; trả về `data_dir`."""
    data_dir = get_data_dir(cfg)
    for sub in (data_dir, get_evidence_dir(cfg), get_logs_dir(cfg), get_exports_dir(cfg), get_base_state_dir()):
        sub.mkdir(parents=True, exist_ok=True)
    probe = data_dir / ".write_test"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink(missing_ok=True)
    return data_dir

