"""Điểm vào của ứng dụng desktop Windows PPE Monitor (docs/desktop_app_plan.md mục 3, 6, 7, M1).

Luồng khởi động:
1. Đặt `YOLO_AUTOINSTALL=False` và `PPE_DESKTOP_MODE=1`.
2. Kiểm tra khóa một phiên bản chạy (`app.lock`); nếu đã có cửa sổ mở thì đưa cửa sổ đó lên trước và thoát mã 0.
3. Khởi tạo thư mục dữ liệu `%LOCALAPPDATA%\\PPEMonitor\\` và ghi log xoay vòng (giữ tối đa 7 file).
4. Mở ngay cửa sổ `pywebview` với màn hình chờ (`desktop/assets/splash.html`).
5. Ở luồng nền: kiểm tra phần cứng/trọng số, chọn cổng trống trên `127.0.0.1`, chạy `uvicorn` phục vụ `backend.app`,
   đợi `/api/health` sẵn sàng rồi điều hướng cửa sổ vào giao diện chính.
6. Khi đóng cửa sổ: hỏi xác nhận nếu đang chạy nguồn giám sát, dừng `LiveCamera` (`session_ended_unverified`),
   tắt `uvicorn`, nhả khóa phiên bản chạy.
"""

from __future__ import annotations

import argparse
import ctypes
import io
import json
import logging
import os
import platform
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# Chặn tuyệt đối việc Ultralytics tự cài gói trên máy người dùng cuối (mục 6, dòng 276)
os.environ["YOLO_AUTOINSTALL"] = "False"
os.environ.setdefault("PPE_DESKTOP_MODE", "1")

# Khi đóng gói PyInstaller chế độ không cửa sổ console (`console=False`), stdout/stderr là None -> bọc bộ đệm rỗng
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

# Đảm bảo import được `desktop`, `backend` và `src/ppe` khi chạy trực tiếp `python desktop/main.py`
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if (_REPO_ROOT / "src").exists() and str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from filelock import FileLock, Timeout  # noqa: E402
import yaml  # noqa: E402

from desktop import APP_NAME, APP_VERSION  # noqa: E402
from desktop.paths import (  # noqa: E402
    ensure_user_dirs,
    get_data_dir,
    get_db_path,
    get_exports_dir,
    get_instance_info_path,
    get_lock_path,
    get_logs_dir,
    load_desktop_config,
    resolve_resource,
)

LOGGER = logging.getLogger("ppe_desktop")

# Hằng số hộp thoại và cửa sổ Win32
MB_OK = 0x00000000
MB_YESNO = 0x00000004
MB_ICONERROR = 0x00000010
MB_ICONQUESTION = 0x00000020
MB_ICONWARNING = 0x00000030
MB_TOPMOST = 0x00040000
IDYES = 6
SW_RESTORE = 9


def show_windows_message(title: str, message: str, flags: int = MB_OK | MB_ICONWARNING) -> int:
    """Hiện hộp thoại gốc của Windows (hoạt động cả trước khi pywebview khởi tạo)."""
    if os.name == "nt":
        try:
            return int(ctypes.windll.user32.MessageBoxW(0, str(message), str(title), flags | MB_TOPMOST))
        except Exception:
            pass
    return IDYES


def is_webview2_installed() -> bool:
    """Kiểm tra Microsoft Edge WebView2 Runtime trên Windows 10/11."""
    if os.name != "nt":
        return True
    try:
        import winreg

        webview2_guid = r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
        webview2_guid_32 = r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for subkey in (webview2_guid, webview2_guid_32):
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        pv, _ = winreg.QueryValueEx(key, "pv")
                        if pv and str(pv) != "0.0.0.0":
                            return True
                except OSError:
                    continue
    except Exception:
        pass
    # Kiểm tra đường dẫn Edge WebView2 tích hợp sẵn của Windows 11
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    return (Path(pf86) / "Microsoft" / "EdgeWebView" / "Application").exists()


def pick_free_port(host: str = "127.0.0.1", preferred_port: int = 0) -> int:
    """Chọn cổng trống trên 127.0.0.1 (nếu `preferred_port` bằng 0 hoặc đang bận thì xin hệ điều hành cấp cổng mới)."""
    if preferred_port and int(preferred_port) > 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, int(preferred_port)))
                return int(preferred_port)
            except OSError:
                pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


def setup_logging(cfg: dict[str, Any]) -> Path:
    """Cấu hình log xoay vòng tại `%LOCALAPPDATA%\\PPEMonitor\\logs\\` (mặc định giữ 7 file, mức INFO)."""
    log_cfg = cfg.get("logging") or {}
    logs_dir = get_logs_dir(cfg)
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "ppe_monitor.log"

    max_files = max(2, int(log_cfg.get("max_files", 7)))
    max_bytes = max(262_144, int(log_cfg.get("max_bytes", 5_242_880)))
    level_name = str(log_cfg.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    LOGGER.setLevel(level)
    for h in list(LOGGER.handlers):
        LOGGER.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass

    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=max_files - 1,  # 1 file chính + 6 bản xoay vòng = đúng 7 file
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    LOGGER.addHandler(handler)
    LOGGER.propagate = False
    return log_file


def _bring_pid_window_to_front(pid: int | None, title: str | None) -> bool:
    """Dùng Win32 API tìm cửa sổ của tiến trình đang chạy và đưa lên trước màn hình."""
    if os.name != "nt":
        return False
    try:
        user32 = ctypes.windll.user32
        found_hwnds: list[int] = []

        if pid:
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

            def _enum_cb(hwnd, _lparam):
                if user32.IsWindowVisible(hwnd):
                    win_pid = ctypes.c_ulong(0)
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))
                    if int(win_pid.value) == int(pid):
                        found_hwnds.append(hwnd)
                return True

            user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)

        if not found_hwnds and title:
            hwnd = user32.FindWindowW(None, str(title))
            if hwnd:
                found_hwnds.append(hwnd)

        for hwnd in found_hwnds:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


def focus_existing_instance(info_path: Path | None = None) -> bool:
    """Đọc `instance.json` của phiên bản đang chạy và gọi cửa sổ đó hiện lên trước."""
    target = info_path or get_instance_info_path()
    if not target.exists():
        return False
    try:
        info = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return False

    port = info.get("port")
    notified = False
    if port:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{int(port)}/api/desktop/focus", data=b"{}", method="POST")
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                notified = resp.status == 200
        except Exception:
            pass

    win_focused = _bring_pid_window_to_front(info.get("pid"), info.get("title"))
    return bool(notified or win_focused)


class SingleInstanceGuard:
    """Đảm bảo toàn hệ thống chỉ mở một cửa sổ ứng dụng duy nhất."""

    def __init__(self, lock_path: Path | None = None, info_path: Path | None = None):
        self.lock_path = lock_path or get_lock_path()
        self.info_path = info_path or get_instance_info_path()
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self.lock_path), timeout=0)
        self.acquired = False

    def acquire(self) -> bool:
        try:
            self._lock.acquire(timeout=0)
            self.acquired = True
            return True
        except Timeout:
            self.acquired = False
            return False

    def write_info(self, port: int | None, title: str) -> None:
        if not self.acquired:
            return
        payload = {
            "pid": os.getpid(),
            "port": port,
            "title": title,
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.info_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            self.info_path.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            self._lock.release()
        except Exception:
            pass
        self.acquired = False


def detect_compute_device(cfg: dict[str, Any]) -> dict[str, Any]:
    """Kiểm tra GPU NVIDIA CUDA hoặc rơi về CPU mà không làm sập ứng dụng."""
    pref = str((cfg.get("processing") or {}).get("device") or "auto").lower()
    if pref == "cpu":
        return {"mode": "cpu", "text": "CPU (theo cài đặt)", "level": "warn", "gpu_name": None}
    try:
        import torch

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            return {"mode": "cuda", "text": f"GPU: {gpu_name}", "level": "ok", "gpu_name": gpu_name}
        return {"mode": "cpu", "text": "CPU (không tìm thấy CUDA — chạy chậm hơn)", "level": "warn", "gpu_name": None}
    except Exception:
        return {"mode": "cpu", "text": "CPU (chế độ vỏ / chưa nạp PyTorch)", "level": "warn", "gpu_name": None}


def check_pipeline_weights() -> dict[str, Any]:
    """Kiểm tra các file trọng số khai báo trong `configs/pipeline.yaml` (chỉ đọc)."""
    pipe_path = resolve_resource("configs/pipeline.yaml")
    if not pipe_path.exists():
        return {"ok": False, "text": "Thiếu configs/pipeline.yaml", "level": "err", "missing": ["configs/pipeline.yaml"]}
    p_cfg = yaml.safe_load(pipe_path.read_text(encoding="utf-8")) or {}
    required_files: list[str] = []
    det_w = (p_cfg.get("detector") or {}).get("weights")
    if det_w:
        required_files.append(str(det_w))
    if (p_cfg.get("pose") or {}).get("enabled") and (p_cfg.get("pose") or {}).get("weights"):
        required_files.append(str(p_cfg["pose"]["weights"]))
    pc = p_cfg.get("part_cls") or {}
    if pc.get("enabled"):
        if pc.get("weights"):
            required_files.append(str(pc["weights"]))
        for w in (pc.get("weights_by_ppe") or {}).values():
            if w and str(w) not in required_files:
                required_files.append(str(w))

    missing = [rel for rel in required_files if not resolve_resource(rel).exists()]
    if not missing:
        det_name = Path(det_w).parent.parent.name if det_w else "sẵn sàng"
        return {"ok": True, "text": f"Sẵn sàng ({det_name})", "level": "ok", "missing": []}
    return {
        "ok": False,
        "text": f"Thiếu {len(missing)} tệp trọng số (chế độ hạn chế)",
        "level": "warn",
        "missing": missing,
    }


def create_diagnostic_zip(target_zip: Path, cfg: dict[str, Any] | None = None) -> Path:
    """Tạo gói chẩn đoán lỗi (ZIP: log, phiên bản, cấu hình, thông tin phần cứng; tuyệt đối không có ảnh/video)."""
    resolved_cfg = cfg or load_desktop_config()
    target_zip = Path(target_zip)
    target_zip.parent.mkdir(parents=True, exist_ok=True)

    sys_info = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "python": sys.version,
        "frozen": bool(getattr(sys, "frozen", False)),
        "compute": detect_compute_device(resolved_cfg),
        "weights": check_pipeline_weights(),
        "data_dir": str(get_data_dir(resolved_cfg)),
    }

    with zipfile.ZipFile(target_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("diagnostic_info.json", json.dumps(sys_info, ensure_ascii=False, indent=2))
        zf.writestr("desktop_effective.yaml", yaml.safe_dump(resolved_cfg, allow_unicode=True, sort_keys=False))
        pipe_file = resolve_resource("configs/pipeline.yaml")
        if pipe_file.exists():
            zf.write(pipe_file, arcname="configs/pipeline.yaml")
        logs_dir = get_logs_dir(resolved_cfg)
        if logs_dir.exists():
            for lf in sorted(logs_dir.glob("*.log*")):
                if lf.is_file():
                    zf.write(lf, arcname=f"logs/{lf.name}")
    return target_zip


class BackendServer:
    """Quản lý vòng đời `uvicorn.Server` chạy trên luồng nền `127.0.0.1:<port>`."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = pick_free_port(host, port)
        self._server = None
        self._thread: threading.Thread | None = None
        self.startup_error: str | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self, focus_callback=None) -> None:
        import uvicorn
        import backend.app as app_mod
        import backend.db as db_mod

        db_mod.configure_db_path(get_db_path())
        if focus_callback is not None:
            app_mod.register_focus_handler(focus_callback)

        config = uvicorn.Config(
            app_mod.app,
            host=self.host,
            port=self.port,
            log_config=None,
            access_log=False,
            timeout_graceful_shutdown=3,
        )
        server = uvicorn.Server(config)
        server.install_signal_handlers = lambda: None  # luồng phụ không được chiếm signal của tiến trình GUI
        self._server = server

        def _runner():
            try:
                server.run()
            except Exception as exc:
                self.startup_error = repr(exc)
                LOGGER.exception("Lỗi luồng máy chủ uvicorn: %s", exc)

        self._thread = threading.Thread(target=_runner, name="ppe-uvicorn", daemon=True)
        self._thread.start()

    def wait_ready(self, timeout_s: float = 30.0) -> bool:
        deadline = time.monotonic() + float(timeout_s)
        health_url = f"{self.base_url}/api/health"
        while time.monotonic() < deadline:
            if self.startup_error:
                return False
            try:
                with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                    if resp.status == 200:
                        return True
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(0.1)
        return False

    def is_live_running(self) -> bool:
        try:
            import backend.app as app_mod

            return bool(app_mod.LIVE.is_active())
        except Exception:
            return False

    def stop(self, timeout_s: float = 5.0) -> None:
        try:
            import backend.app as app_mod

            app_mod.LIVE.stop(timeout=min(5.0, float(timeout_s)))
        except Exception as exc:
            LOGGER.warning("Lỗi khi dừng LiveCamera lúc thoát: %s", exc)

        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=float(timeout_s))
            if self._thread.is_alive() and self._server is not None:
                self._server.force_exit = True
                self._thread.join(timeout=2.0)


class DesktopBridge:
    """API Python lộ ra cho JavaScript qua `window.pywebview.api`."""

    def __init__(self, startup_state: dict[str, Any], cfg: dict[str, Any]):
        self._state = startup_state
        self._cfg = cfg
        self._window = None

    def attach_window(self, window) -> None:
        self._window = window

    def get_startup_status(self) -> dict[str, Any]:
        return dict(self._state)

    def pick_video(self) -> str | None:
        """Mở hộp thoại chọn tệp video của Windows (`.mp4`, `.avi`, `.mov`)."""
        if self._window is None:
            return None
        import webview

        dialog_type = getattr(webview.FileDialog, "OPEN", webview.OPEN_DIALOG)
        result = self._window.create_file_dialog(
            dialog_type,
            allow_multiple=False,
            file_types=("Tệp video (*.mp4;*.avi;*.mov)", "Tất cả tệp (*.*)"),
        )
        if result and len(result) > 0:
            return str(result[0])
        return None

    def save_file(self, default_filename: str = "ppe_events.csv", kind: str = "csv") -> str | None:
        """Mở hộp thoại lưu tệp xuất CSV / ZIP của Windows."""
        if self._window is None:
            return None
        import webview

        dialog_type = getattr(webview.FileDialog, "SAVE", webview.SAVE_DIALOG)
        ftypes = (
            ("Bảng sự kiện CSV (*.csv)", "Tất cả tệp (*.*)")
            if kind == "csv"
            else ("Gói nén ZIP (*.zip)", "Tất cả tệp (*.*)")
        )
        exports_dir = str(get_exports_dir(self._cfg))
        result = self._window.create_file_dialog(
            dialog_type,
            directory=exports_dir,
            save_filename=default_filename,
            file_types=ftypes,
        )
        if isinstance(result, (list, tuple)):
            return str(result[0]) if result else None
        return str(result) if result else None

    def open_folder(self, target_path: str = "") -> bool:
        """Mở thư mục trong Windows Explorer (mặc định mở thư mục dữ liệu người dùng)."""
        p = Path(target_path).resolve() if target_path else get_data_dir(self._cfg)
        folder = p if p.is_dir() else p.parent
        if not folder.exists():
            return False
        if os.name == "nt":
            os.startfile(str(folder))  # type: ignore[attr-defined]
            return True
        return False

    def save_diagnostic_bundle(self) -> str | None:
        """Tạo gói ZIP chẩn đoán lỗi theo đường dẫn người dùng chọn."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chosen = self.save_file(f"ppe_diagnostic_{stamp}.zip", kind="zip")
        if not chosen:
            return None
        out = create_diagnostic_zip(Path(chosen), self._cfg)
        return str(out)


def _install_exception_hooks(cfg: dict[str, Any]) -> None:
    """Ghi log mọi lỗi chưa bắt và hiện hộp thoại kèm tùy chọn lưu gói chẩn đoán."""

    def _handle_uncaught(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        LOGGER.error("Lỗi không lường trước:\n%s", tb_text)
        ans = show_windows_message(
            f"{APP_NAME} — Đã xảy ra lỗi",
            f"Ứng dụng gặp sự cố ngoài dự kiến:\n{exc_value}\n\n"
            "Bạn có muốn lưu gói chẩn đoán (.zip, không chứa ảnh/video) vào thư mục dữ liệu để gửi nhóm phát triển không?",
            MB_YESNO | MB_ICONERROR,
        )
        if ans == IDYES:
            try:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                diag_path = get_exports_dir(cfg) / f"ppe_diagnostic_{stamp}.zip"
                create_diagnostic_zip(diag_path, cfg)
                show_windows_message(APP_NAME, f"Đã lưu gói chẩn đoán tại:\n{diag_path}", MB_OK | MB_ICONWARNING)
            except Exception:
                pass

    sys.excepthook = _handle_uncaught
    threading.excepthook = lambda args: LOGGER.error(
        "Lỗi luồng nền %s:\n%s",
        getattr(args.thread, "name", "?"),
        "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)),
    )


def run_desktop_app(auto_close_ms: int = 0, check_only: bool = False) -> int:
    """Chạy ứng dụng desktop PPE Monitor. Trả về mã thoát (0 = thành công)."""
    cfg = load_desktop_config()
    app_cfg = cfg.get("app") or {}
    srv_cfg = cfg.get("server") or {}
    version = str(app_cfg.get("version") or APP_VERSION)
    base_title = str(app_cfg.get("title") or f"{APP_NAME} — Giám sát Trang bị Bảo hộ Lao động")
    window_title = f"{base_title} v{version}"

    # 1. Đảm bảo chỉ mở một phiên bản chạy duy nhất
    guard = SingleInstanceGuard()
    if not guard.acquire():
        focus_existing_instance()
        return 0

    backend: BackendServer | None = None
    shutting_down = threading.Event()

    try:
        # 2. Kiểm tra thư mục dữ liệu người dùng & mở log xoay vòng
        try:
            data_dir = ensure_user_dirs(cfg)
            data_check = {"text": str(data_dir), "level": "ok"}
            data_warning = None
        except Exception as exc:
            data_dir = get_data_dir(cfg)
            data_check = {"text": f"Lỗi quyền ghi ({exc})", "level": "err"}
            data_warning = f"Không ghi được vào thư mục dữ liệu {data_dir}: {exc}"

        setup_logging(cfg)
        _install_exception_hooks(cfg)
        LOGGER.info("Khởi động %s v%s (PID=%s, data_dir=%s)", APP_NAME, version, os.getpid(), data_dir)

        # 3. Nếu chạy kiểm thử không giao diện (`--check-only`), khởi động backend rồi tắt sạch
        if check_only:
            backend = BackendServer(
                host=str(srv_cfg.get("host") or "127.0.0.1"),
                port=int(srv_cfg.get("port") or 0),
            )
            guard.write_info(backend.port, window_title)
            backend.start()
            ok = backend.wait_ready(float(srv_cfg.get("startup_timeout_s") or 30.0))
            LOGGER.info("Kiểm tra --check-only: server=%s, ready=%s", backend.base_url, ok)
            return 0 if ok else 1

        # 4. Kiểm tra WebView2 trên Windows trước khi mở cửa sổ
        if not is_webview2_installed():
            LOGGER.error("Máy chưa cài Microsoft Edge WebView2 Runtime.")
            show_windows_message(
                f"{APP_NAME} — Thiếu thành phần hiển thị",
                "Máy tính chưa có Microsoft Edge WebView2 Runtime.\n"
                "Vui lòng cài đặt WebView2 Runtime của Microsoft (miễn phí trên Windows 10/11) rồi mở lại ứng dụng.",
                MB_OK | MB_ICONERROR,
            )
            return 2

        import webview

        startup_state: dict[str, Any] = {
            "version": version,
            "progress": 18,
            "message": "Đang kiểm tra môi trường và phần cứng…",
            "ready": False,
            "fatal": False,
            "auto_proceed": True,
            "url": None,
            "warnings": [data_warning] if data_warning else [],
            "checks": {
                "data": data_check,
                "device": {"text": "Đang kiểm tra…", "level": ""},
                "weights": {"text": "Đang kiểm tra…", "level": ""},
                "server": {"text": "Đang chọn cổng trống…", "level": ""},
            },
        }

        bridge = DesktopBridge(startup_state, cfg)
        splash_path = resolve_resource("desktop/assets/splash.html")
        splash_url = splash_path.as_uri() if splash_path.exists() else None
        icon_path = resolve_resource("desktop/assets/icon.ico")

        window = webview.create_window(
            window_title,
            url=splash_url,
            html=None if splash_url else "<h1>Đang khởi động PPE Monitor...</h1>",
            js_api=bridge,
            width=max(1280, int(app_cfg.get("min_width") or 1280)),
            height=max(720, int(app_cfg.get("min_height") or 720)),
            min_size=(int(app_cfg.get("min_width") or 1280), int(app_cfg.get("min_height") or 720)),
            maximized=bool(app_cfg.get("maximized", True)) and auto_close_ms <= 0,
            background_color="#0b1120",
        )
        bridge.attach_window(window)

        backend = BackendServer(
            host=str(srv_cfg.get("host") or "127.0.0.1"),
            port=int(srv_cfg.get("port") or 0),
        )
        guard.write_info(backend.port, window_title)

        def _focus_window():
            try:
                window.restore()
            except Exception:
                pass
            _bring_pid_window_to_front(os.getpid(), window_title)

        def _shutdown_cleanly():
            if shutting_down.is_set():
                return
            shutting_down.set()
            LOGGER.info("Đang dừng backend và đóng ứng dụng sạch…")
            if backend is not None:
                backend.stop(timeout_s=float(srv_cfg.get("shutdown_timeout_s") or 5.0))
            guard.release()
            LOGGER.info("Đã thoát %s sạch.", APP_NAME)

        def _on_closing():
            if auto_close_ms <= 0 and backend is not None and backend.is_live_running():
                ans = show_windows_message(
                    APP_NAME,
                    "Đang giám sát. Dừng và thoát?",
                    MB_YESNO | MB_ICONQUESTION,
                )
                if ans != IDYES:
                    return False
            _shutdown_cleanly()
            return True

        window.events.closing += _on_closing

        def _bootstrap_worker():
            try:
                startup_state["progress"] = 40
                startup_state["message"] = "Đang kiểm tra GPU / CPU và trọng số nhận diện…"
                dev_info = detect_compute_device(cfg)
                startup_state["checks"]["device"] = {"text": dev_info["text"], "level": dev_info["level"]}

                w_info = check_pipeline_weights()
                startup_state["checks"]["weights"] = {"text": w_info["text"], "level": w_info["level"]}
                if not w_info["ok"]:
                    startup_state["warnings"].append(
                        "Chưa tìm thấy tệp trọng số mô hình (.pt). Ứng dụng vẫn mở ở chế độ xem sự kiện, thống kê, "
                        "cài đặt và trợ giúp; để bật nhận diện trực tiếp, hãy giải nén gói trọng số vào thư mục cài đặt."
                    )

                startup_state["progress"] = 68
                startup_state["message"] = f"Đang khởi động máy chủ nội bộ ({backend.base_url})…"
                startup_state["checks"]["server"] = {"text": f"127.0.0.1:{backend.port}", "level": ""}
                backend.start(focus_callback=_focus_window)

                ready = backend.wait_ready(timeout_s=float(srv_cfg.get("startup_timeout_s") or 30.0))
                if not ready:
                    err_detail = backend.startup_error or "Quá thời gian chờ /api/health"
                    LOGGER.error("Không khởi động được máy chủ nội bộ: %s", err_detail)
                    startup_state["fatal"] = True
                    startup_state["checks"]["server"] = {"text": "Lỗi khởi động", "level": "err"}
                    startup_state["warnings"].append(f"Không khởi động được máy chủ nội bộ: {err_detail}")
                    startup_state["message"] = "Không thể khởi động máy chủ nội bộ."
                    if auto_close_ms > 0:
                        time.sleep(0.3)
                        window.destroy()
                    return

                target_url = f"{backend.base_url}/dashboard/index.html"
                startup_state["checks"]["server"] = {"text": f"Sẵn sàng (127.0.0.1:{backend.port})", "level": "ok"}
                startup_state["progress"] = 100
                startup_state["message"] = "Đã sẵn sàng! Đang mở bảng điều khiển…"
                startup_state["url"] = target_url
                startup_state["ready"] = True
                LOGGER.info("Máy chủ nội bộ sẵn sàng tại %s", target_url)

                # Màn hình chờ splash.html tự chuyển trang sau khi nhận ready=True; chỉ gọi load_url dự phòng
                if not splash_url and not shutting_down.is_set():
                    window.load_url(target_url)
                else:
                    time.sleep(0.5 if auto_close_ms <= 0 else 0.35)
                    cur_url = ""
                    try:
                        cur_url = str(window.get_current_url() or "")
                    except Exception:
                        pass
                    if not shutting_down.is_set() and backend.base_url not in cur_url:
                        window.load_url(target_url)

                if auto_close_ms > 0:
                    time.sleep(max(0.2, auto_close_ms / 1000.0))
                    _shutdown_cleanly()
                    window.destroy()
            except Exception as exc:
                LOGGER.exception("Lỗi trong luồng khởi tạo ứng dụng: %s", exc)
                if auto_close_ms > 0:
                    _shutdown_cleanly()
                    window.destroy()

        start_kwargs: dict[str, Any] = {"gui": "edgechromium"} if os.name == "nt" else {}
        if icon_path.exists():
            start_kwargs["icon"] = str(icon_path)

        webview.start(_bootstrap_worker, **start_kwargs)
        _shutdown_cleanly()
        return 0 if not startup_state.get("fatal") else 1
    finally:
        if backend is not None and not shutting_down.is_set():
            backend.stop(timeout_s=float(srv_cfg.get("shutdown_timeout_s") or 5.0))
        guard.release()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ứng dụng desktop Windows PPE Monitor")
    parser.add_argument(
        "--auto-close-ms",
        type=int,
        default=0,
        help="Tự động đóng cửa sổ sau N mili-giây kể từ khi trang chính nạp xong (dùng cho kiểm thử tự động M1)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Chỉ kiểm tra khởi tạo đường dẫn, khóa phiên bản và máy chủ nền (không mở cửa sổ GUI)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_desktop_app(auto_close_ms=args.auto_close_ms, check_only=args.check_only)


if __name__ == "__main__":
    raise SystemExit(main())

