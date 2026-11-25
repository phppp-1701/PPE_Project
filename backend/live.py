"""Camera trực tiếp và phát tệp video trong backend (FR-01, FR-10, docs/desktop_app_plan.md mục 4.1).

Hai chế độ nguồn:
1. Chế độ `camera` (webcam trực tiếp - hai luồng):
    - luồng đọc: đọc webcam liên tục, chỉ giữ khung MỚI NHẤT (xử lý chậm hơn camera thì bỏ khung cũ, hình không trễ dần);
    - luồng xử lý: lấy khung mới nhất -> Pipeline (nhận diện như configs/pipeline.yaml) -> vẽ (hàm draw của
      scripts/05_run_video.py) -> JPEG cho /api/live/stream. Sự kiện vi phạm đi qua `on_event` (backend ghi SQLite).
   Thời gian t của chuỗi xử lý = giây thật kể từ lúc mở phiên.
2. Chế độ `file` (tệp video - đọc tuần tự):
    - đọc lần lượt từng khung hình (không bỏ khung), thời gian `t = chỉ_số_khung / fps_video` khớp với `05_run_video.py`.
    - hỗ trợ phát `realtime` (đợi theo tốc độ gốc của video) hoặc `fast` (xử lý nhanh nhất có thể), tạm dừng / tiếp tục.
Đổi PPE bắt buộc khi đang chạy: `set_policy` ghi yêu cầu, luồng xử lý áp dụng trước khung kế tiếp
(Pipeline.set_required: đóng sự kiện đang mở với lý do policy_changed, đếm lại từ đầu).
"""

import copy
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")   # không để Ultralytics tự cài gói

import cv2
import yaml

from desktop.paths import (
    bundle_root,
    get_evidence_dir,
    is_desktop_mode,
    load_desktop_config,
    resolve_resource,
)
from .video_file import open_video_file

ROOT = bundle_root()
LIVE_CONFIG = resolve_resource("configs/live.yaml")
if str(ROOT / "src") not in sys.path and (ROOT / "src").exists():
    sys.path.insert(0, str(ROOT / "src"))

IDLE, STARTING, RUNNING, STOPPING, ERROR = "idle", "starting", "running", "stopping", "error"
ALL_PPE_ORDER = ("helmet", "vest", "gloves", "goggles", "boots")


def load_live_config(path=None):
    target = Path(path) if path is not None else resolve_resource("configs/live.yaml")
    return yaml.safe_load(target.read_text(encoding="utf-8"))


def _resolve_runtime_device(default_device):
    """Chọn thiết bị suy luận theo cài đặt người dùng và tự rơi về CPU nếu máy không có CUDA."""
    pref = "auto"
    if is_desktop_mode():
        pref = str((load_desktop_config().get("processing") or {}).get("device") or "auto").lower()
    if pref == "cpu":
        return "cpu"
    try:
        import torch

        if not torch.cuda.is_available():
            return "cpu"
    except Exception:
        return "cpu"
    return 0 if pref == "cuda" else default_device


def build_runtime_pipeline_config():
    """Tạo bản sao cấu hình pipeline trong bộ nhớ (không sửa file configs/pipeline.yaml hay src/ppe/):
    quy đổi đường dẫn trọng số, thư mục minh chứng và thiết bị suy luận theo môi trường chạy."""
    from ppe import load_config

    cfg = copy.deepcopy(load_config(resolve_resource("configs/pipeline.yaml")))
    cfg["detector"]["weights"] = str(resolve_resource(cfg["detector"]["weights"]))
    cfg["detector"]["device"] = _resolve_runtime_device(cfg["detector"].get("device", 0))
    if (cfg.get("pose") or {}).get("weights"):
        cfg["pose"]["weights"] = str(resolve_resource(cfg["pose"]["weights"]))
    if cfg.get("part_cls"):
        if cfg["part_cls"].get("weights"):
            cfg["part_cls"]["weights"] = str(resolve_resource(cfg["part_cls"]["weights"]))
        by_ppe = cfg["part_cls"].get("weights_by_ppe") or {}
        cfg["part_cls"]["weights_by_ppe"] = {k: str(resolve_resource(v)) for k, v in by_ppe.items()}
    cfg["events"]["evidence_dir"] = str(get_evidence_dir())
    return cfg


def open_camera(cfg, camera_index_override=None):
    """Mở webcam theo configs/live.yaml (hoặc chỉ số override). Trả về cv2.VideoCapture đã mở, lỗi thì RuntimeError."""
    cam_cfg = dict(cfg)
    if is_desktop_mode():
        desk_cam = (load_desktop_config().get("camera") or {})
        if camera_index_override is None and "default_index" in desk_cam:
            cam_cfg["camera_index"] = int(desk_cam["default_index"])
        if "width" in desk_cam:
            cam_cfg["width"] = int(desk_cam["width"])
        if "height" in desk_cam:
            cam_cfg["height"] = int(desk_cam["height"])
        if "backend" in desk_cam:
            cam_cfg["backend"] = desk_cam["backend"]

    src = camera_index_override if camera_index_override is not None else cam_cfg["camera_index"]

    # Nguồn URL (MJPEG/RTSP — ví dụ bridge camera Fofu: http://127.0.0.1:8077/stream.mjpg):
    # OpenCV đọc trực tiếp, không set FOURCC/độ phân giải vì stream đã cố định.
    if isinstance(src, str) and src.lower().startswith(("http://", "https://", "rtsp://")):
        # giảm buffer + đặt timeout FFmpeg (µs) phía consumer: stream chết thì read
        # trả lỗi trong ~5s thay vì treo vô hạn, để vòng đọc kịp mở lại kết nối
        os.environ.setdefault(
            "OPENCV_FFMPEG_CAPTURE_OPTIONS",
            "fflags;nobuffer|flags;low_delay|probesize;500000|analyzeduration;0|timeout;5000000")
        cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            raise RuntimeError(
                f"Không mở được stream URL {src} "
                "(kiểm tra bridge camera Fofu đã chạy chưa: python scripts/fofu_bridge.py)"
            )
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    idx = int(src)
    api = cv2.CAP_DSHOW if cam_cfg.get("backend") == "dshow" and os.name == "nt" else cv2.CAP_ANY
    cap = cv2.VideoCapture(idx, api)
    if not cap.isOpened():
        raise RuntimeError(
            f"Không mở được webcam số {idx} "
            "(đang bị ứng dụng khác dùng hoặc bị chặn ở Cài đặt Windows > Quyền riêng tư > Camera?)"
        )
    if cam_cfg.get("fourcc"):
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*cam_cfg["fourcc"]))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(cam_cfg["width"]))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(cam_cfg["height"]))
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def probe_cameras(max_index: int = 3, active_indices=None, active_resolution=None) -> list[dict]:
    """Dò danh sách webcam từ 0..max_index. Webcam đang chạy trong LiveCamera thì không mở đè.

    Dò chạy trong TIỂU TRÌNH RIÊNG (backend/camera_probe_worker.py): DirectShow trên Windows
    thỉnh thoảng segfault khi mở/thả webcam trong cùng tiến trình với luồng đang ghi —
    crash đó từng làm sập cả app khi bấm Dừng. Crash giờ chỉ chết worker."""
    desk_cam = (load_desktop_config().get("camera") or {})
    active_set = {int(i) for i in (active_indices or [])}
    found = []

    # 1) thử dò bằng worker tiểu trình riêng (an toàn với crash native)
    import subprocess
    try:
        worker = Path(__file__).parent / "camera_probe_worker.py"
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        res = subprocess.run(
            [sys.executable, str(worker), str(max_index), json.dumps(sorted(active_set))],
            capture_output=True, text=True, timeout=25, creationflags=flags,
        )
        probed = json.loads(res.stdout.strip().splitlines()[-1])
        for p in probed:
            idx = int(p["index"])
            active = idx in active_set
            if active:
                w, h = (active_resolution or [1280, 720])
                found.append({"index": idx, "name": f"Webcam {idx} (Đang sử dụng)",
                              "width": int(w), "height": int(h), "active": True})
            else:
                found.append({"index": idx, "name": f"Webcam {idx} ({p['width']}x{p['height']})",
                              "width": p["width"], "height": p["height"], "active": False})
        return found
    except Exception:
        pass   # worker lỗi (mất json / timeout) — rơi về dò trong tiến trình bên dưới

    # 2) fallback: dò trong tiến trình (như bản cũ)
    api = cv2.CAP_DSHOW if desk_cam.get("backend", "dshow") == "dshow" and os.name == "nt" else cv2.CAP_ANY
    for idx in range(max(1, int(max_index) + 1)):
        if idx in active_set:
            w, h = (active_resolution or [int(desk_cam.get("width", 1280)), int(desk_cam.get("height", 720))])
            found.append({
                "index": idx,
                "name": f"Webcam {idx} (Đang sử dụng)",
                "width": w,
                "height": h,
                "active": True,
            })
            continue
        cap = None
        try:
            cap = cv2.VideoCapture(idx, api)
            if cap is not None and cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
                found.append({
                    "index": idx,
                    "name": f"Webcam {idx} ({w}x{h})",
                    "width": w,
                    "height": h,
                    "active": False,
                })
        except Exception:
            pass
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
    return found


def load_camera_catalog() -> list[dict]:
    """Danh mục camera người dùng có thể chọn theo dõi:
    - cam0: camera IP từ configs/live.yaml (Fofu qua bridge MJPEG) — source_id giữ nguyên
      cho khớp dữ liệu sự kiện/policy cũ;
    - webcam{index}: các webcam quét được trên máy.
    """
    cfg = load_live_config()
    items = [{
        "source_id": str(cfg.get("source_id", "cam0")),
        "name": str(cfg.get("source_name", "Camera IP")),
        "camera_index": cfg.get("camera_index", 0),
        "source_type": "camera",
        "in_use": False,   # app.py gán lại theo trạng thái phiên
    }]
    try:
        for cam in probe_cameras(max_index=3, active_indices=[]):
            items.append({
                "source_id": f"webcam{cam['index']}",
                "name": cam["name"],
                "camera_index": int(cam["index"]),
                "source_type": "camera",
                "in_use": False,
            })
    except Exception:
        pass
    return items


def default_pipeline(source_id, session_id, on_event):
    """Pipeline đầy đủ với configs/pipeline.yaml (nạp mô hình mất vài giây)."""
    from ppe.pipeline import Pipeline
    return Pipeline(source_id, session_id, stage="full", cfg=build_runtime_pipeline_config(), on_event=on_event)


def default_draw():
    """Hàm draw của scripts/05_run_video.py (cùng quy tắc hiển thị với video đã vẽ). Nạp bằng importlib như 06c,
    không sửa 05_run_video.py (file nằm trong manifest đóng băng)."""
    spec = importlib.util.spec_from_file_location("run_video", resolve_resource("scripts/05_run_video.py"))
    rv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rv)
    return lambda frame, out, cfg: rv.draw(frame, hide_rejected(out, cfg, rv.box_status), cfg, False)


def hide_rejected(out, cfg, box_status):
    """Chỉ để vẽ trên camera trực tiếp (người dùng yêu cầu 16/11/2026): bỏ hộp detector mà bộ phân loại đã bác bỏ
    (loại "bac_bo": kính thường, mũ bác bỏ bước C2, ủng bác bỏ bước M1). Hệ thống đã kết luận đó không phải PPE nên không
    vẽ hộp xám. Hộp xám vì lý do khác (tranh chấp, ngoài vùng, chưa kết luận) vẫn vẽ. Video đã vẽ (05_run_video) không đổi."""
    if "assoc" not in out or not out.get("ppe"):
        return out
    st = box_status(out, cfg)
    return dict(out, ppe=[d for d in out["ppe"] if st[id(d)][0] != "bac_bo"])


def summarize_persons_in_frame(out, required_ppe, open_events_by_track=None) -> list[dict]:
    """Tổng hợp trạng thái từng người đang hiện diện trong khung hình để hiển thị trực quan cho Admin."""
    req_set = set(required_ppe or [])
    states_map = out.get("states") or {}
    checks_map = out.get("checks") or {}
    open_map = open_events_by_track or {}
    result = []

    for tr in out.get("tracks") or []:
        tid = getattr(tr, "track_id", None)
        if tid is None:
            continue
        confident = bool(getattr(tr, "confident", True))
        per_st = states_map.get(tid) or {}
        per_chk = checks_map.get(tid) or {}
        open_ev = open_map.get(tid)

        items = {}
        missing_now = []
        confirmed_missing = []
        if open_ev and open_ev.get("missing_items"):
            confirmed_missing = list(open_ev["missing_items"])

        for ppe in ALL_PPE_ORDER:
            if ppe not in req_set:
                items[ppe] = "unchecked"
                continue
            raw_state = (per_st.get(ppe) or {}).get("state") or "unknown"
            items[ppe] = raw_state
            if raw_state == "missing":
                missing_now.append(ppe)
            chk = per_chk.get(ppe)
            if chk is not None and getattr(chk, "missing_confirmed", False) and ppe not in confirmed_missing:
                confirmed_missing.append(ppe)

        if confirmed_missing or (open_ev and open_ev.get("event_state") == "active"):
            overall = "violation"
        elif missing_now:
            overall = "observing_missing"
        elif req_set and all(items.get(p) == "have" for p in req_set):
            overall = "compliant"
        else:
            overall = "observing"

        result.append({
            "track_id": int(tid),
            "confident": confident,
            "status": overall,
            "items": items,
            "missing_now": missing_now,
            "confirmed_missing": confirmed_missing,
            "event_id": open_ev.get("event_id") if open_ev else None,
        })

    for lost_item in out.get("lost") or []:
        try:
            ltid = int(lost_item[0])
        except Exception:
            continue
        open_ev = open_map.get(ltid)
        result.append({
            "track_id": ltid,
            "confident": False,
            "status": "lost",
            "items": {p: ("unchecked" if p not in req_set else "unknown") for p in ALL_PPE_ORDER},
            "missing_now": [],
            "confirmed_missing": list(open_ev.get("missing_items") or []) if open_ev else [],
            "event_id": open_ev.get("event_id") if open_ev else None,
        })

    result.sort(key=lambda x: (0 if x["status"] == "violation" else (1 if x["status"] == "observing_missing" else 2), x["track_id"]))
    return result


class LiveCamera:
    def __init__(self, cfg=None, on_event=None, on_session=None,
                 capture_factory=None, pipeline_factory=None, draw_factory=None):
        """on_event(kind, ev): mỗi thay đổi sự kiện (như events.jsonl). on_session("start"|"end", info): ghi phiên.
        Ba factory dùng cho kiểm thử (camera, pipeline, hàm vẽ giả); mặc định là webcam, Pipeline, draw thật."""
        self.cfg = cfg or load_live_config()
        self.default_source_id = self.cfg["source_id"]
        self.source_id = self.default_source_id
        self.on_event = on_event
        self.on_session = on_session
        self._custom_capture_factory = capture_factory
        self.capture_factory = capture_factory or (lambda: open_camera(self.cfg))
        self.pipeline_factory = pipeline_factory or default_pipeline
        self.draw_factory = draw_factory or default_draw
        self._lock = threading.Lock()
        self._new_frame = threading.Condition(self._lock)    # luồng xử lý chờ khung mới từ luồng đọc
        self._new_jpeg = threading.Condition(self._lock)     # /api/live/stream chờ ảnh mới từ luồng xử lý
        self._reset()

    def _reset(self):
        self.state, self.error, self.session_id = IDLE, None, None
        self.required, self.policy_version = [], None
        self._pending_policy = None
        self._stop = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()   # mặc định không tạm dừng (set = được chạy)
        self.paused = False
        self._threads = []
        self._cap = self._pipe = None
        self._frame, self._frame_seq = None, 0
        self._jpeg, self._jpeg_seq = None, 0
        self._done = deque()       # thời điểm xử lý xong từng khung (FPS xử lý)
        self._reads = deque()      # thời điểm webcam trả từng khung (FPS camera: xử lý không thể nhanh hơn số này)
        self.frames, self.persons, self.resolution, self.event_errors = 0, 0, None, 0
        self.persons_detail = []
        self.source_type = "camera"
        _cam_src = self.cfg.get("camera_index", 0)
        # camera_index có thể là số (webcam) hoặc chuỗi URL (MJPEG/RTSP — camera IP)
        self.camera_index = _cam_src if isinstance(_cam_src, str) else int(_cam_src)
        self.file_path = None
        self.file_name = None
        self.playback_mode = "realtime"
        self.video_fps = 0.0
        self.total_frames = 0
        self.position_s = 0.0
        self.duration_s = 0.0
        self._t0 = None

    # ---------- điều khiển ----------
    def start(self, required_ppe, policy_version, *, source_type="camera", camera_index=None,
              file_path=None, playback_mode="realtime", source_id=None):
        """Mở phiên mới (trả về ngay; nạp mô hình và mở camera/video ở luồng nền). Đang chạy thì báo lỗi."""
        with self._lock:
            if self.state in (STARTING, RUNNING, STOPPING):
                raise RuntimeError(f"Camera đang ở trạng thái {self.state}")
            self._reset()
            self.state = STARTING
            self.source_type = "file" if str(source_type).lower() == "file" else "camera"
            self.playback_mode = "fast" if str(playback_mode).lower() == "fast" else "realtime"
            if self.source_type == "file":
                self.file_path = str(file_path or "")
                self.file_name = Path(self.file_path).name if self.file_path else None
                self.source_id = source_id or f"video_{Path(self.file_path).stem if self.file_path else 'file'}"
            else:
                _src = camera_index if camera_index is not None else self.cfg.get("camera_index", 0)
                self.camera_index = _src if isinstance(_src, str) else int(_src)
                self.source_id = source_id or self.default_source_id
            self.session_id = f"{self.source_id}_{datetime.now():%Y%m%d_%H%M%S}"
            self.required, self.policy_version = list(required_ppe), policy_version
        th = threading.Thread(target=self._run, name="live-worker", daemon=True)
        self._threads.append(th)
        th.start()
        return self.status()

    def pause(self):
        """Tạm dừng phát tệp video (không áp dụng cho webcam trực tiếp)."""
        with self._lock:
            if self.state != RUNNING or self.source_type != "file":
                raise RuntimeError("Chỉ có thể tạm dừng khi đang phát tệp video")
            self.paused = True
            self._pause_event.clear()
        return self.status()

    def resume(self):
        """Tiếp tục phát tệp video sau khi tạm dừng."""
        with self._lock:
            if self.state != RUNNING or self.source_type != "file":
                raise RuntimeError("Chỉ có thể tiếp tục khi đang phát tệp video")
            self.paused = False
            self._pause_event.set()
        return self.status()

    def stop(self, timeout=10.0):
        """Dừng phiên: đóng sự kiện đang mở (session_ended_unverified), tắt webcam / đóng tệp video."""
        with self._lock:
            active = self.state in (STARTING, RUNNING)
            if active:
                self.state = STOPPING
                self.paused = False
                self._pause_event.set()
                self._stop.set()
                self._new_frame.notify_all()
                self._new_jpeg.notify_all()
        if active:
            for th in list(self._threads):
                th.join(timeout)
        return self.status()   # gọi ngoài khóa: status() tự lấy khóa (Lock không lấy lại được)

    def set_policy(self, required_ppe, policy_version):
        """Đổi PPE bắt buộc khi đang chạy; luồng xử lý áp dụng trước khung kế tiếp."""
        with self._lock:
            if self.state in (STARTING, RUNNING):
                self._pending_policy = (list(required_ppe), policy_version)
                return True
        return False

    def is_active(self):
        return self.state in (STARTING, RUNNING)

    def status(self):
        win = float(self.cfg["stream"]["fps_window_s"])
        now = time.monotonic()
        with self._lock:
            done = [x for x in self._done if x > now - win]
            reads = [x for x in self._reads if x > now - win]
            return dict(
                state=self.state,
                error=self.error,
                source_id=self.source_id,
                source_type=self.source_type,
                camera_index=self.camera_index if self.source_type == "camera" else None,
                file_name=self.file_name,
                playback_mode=self.playback_mode,
                paused=self.paused,
                session_id=self.session_id,
                required_ppe=list(self.required),
                policy_version=self.policy_version,
                fps=round(len(done) / win, 1),
                camera_fps=round(self.video_fps, 1) if self.source_type == "file" else round(len(reads) / win, 1),
                frames=self.frames,
                frame=self.frames,
                total_frames=self.total_frames,
                position_s=round(self.position_s, 2),
                duration_s=round(self.duration_s, 2),
                persons=self.persons,
                persons_detail=list(self.persons_detail),
                resolution=self.resolution,
                event_errors=self.event_errors,
                uptime_s=round(now - self._t0, 1) if self._t0 else 0.0,
            )

    # ---------- phát ảnh ----------
    def mjpeg(self, boundary="frame", idle_timeout=2.0):
        """Luồng multipart MJPEG cho <img>. Kết thúc khi phiên dừng."""
        seq = 0
        while True:
            with self._lock:
                while self._jpeg_seq == seq and self.state in (STARTING, RUNNING):
                    self._new_jpeg.wait(idle_timeout)
                if self.state not in (STARTING, RUNNING) or self._jpeg is None:
                    return
                seq, jpg = self._jpeg_seq, self._jpeg
            yield (b"--" + boundary.encode() + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
                   + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")

    def latest_jpeg(self):
        with self._lock:
            return self._jpeg

    # ---------- luồng nền ----------
    def _emit(self, kind, ev):
        ev["system_time"] = datetime.now().isoformat(timespec="seconds")
        if self.on_event:
            try:
                self.on_event(kind, ev)
            except Exception as e:                  # lỗi ghi sự kiện không được làm dừng camera
                self.event_errors += 1
                print(f"[live] lỗi ghi sự kiện {ev.get('event_id')}: {e!r}", file=sys.stderr)

    def _now(self):
        if self.source_type == "file":
            return float(self.position_s)
        return time.monotonic() - self._t0

    def _reader(self):
        fails = 0
        url_src = isinstance(self.camera_index, str)
        # nguồn URL (camera IP): bridge có thể đang re-login hoặc người dùng
        # khởi động lại bat — kiên nhẫn ~60s trước khi kết thúc phiên
        max_fails = 120 if url_src else 50
        while not self._stop.is_set():
            ok, frame = self._cap.read()
            if not ok or frame is None:
                fails += 1
                if url_src and fails < max_fails and fails % 10 == 0:
                    try:
                        self._cap.release()
                    except Exception:
                        pass
                    try:
                        self._cap = open_camera(self.cfg, camera_index_override=self.camera_index)
                    except Exception:
                        pass
                if fails >= max_fails:
                    self._fail("Webcam không trả khung hình (bị ngắt hoặc ứng dụng khác chiếm)")
                    return
                time.sleep(0.5 if url_src else 0.02)
                continue
            fails = 0
            now = time.monotonic()
            with self._lock:
                self._reads.append(now)
                while self._reads and self._reads[0] <= now - float(self.cfg["stream"]["fps_window_s"]):
                    self._reads.popleft()
                self._frame, self._frame_seq = frame, self._frame_seq + 1
                self._new_frame.notify_all()

    def _fail(self, msg):
        with self._lock:
            if self.state != STOPPING:
                self.error = msg
            self._stop.set()
            self._pause_event.set()
            self._new_frame.notify_all()
            self._new_jpeg.notify_all()

    def _run(self):
        reader = None
        try:
            draw = self.draw_factory()
            self._pipe = self.pipeline_factory(self.source_id, self.session_id, self._emit)
            self._pipe.set_required(self.required, self.policy_version, 0.0)   # danh sách theo nguồn (có thể rỗng)
            self.required = list(self._pipe.required)                          # thứ tự cố định theo cấu hình
            if self.source_type == "file":
                if self._custom_capture_factory is not None and not self.file_path:
                    self._cap = self.capture_factory()
                    self.video_fps = 25.0
                else:
                    self._cap, meta = open_video_file(self.file_path)
                    self.file_name = meta["file_name"]
                    self.video_fps = float(meta["fps"])
                    self.total_frames = int(meta["total_frames"])
                    self.duration_s = float(meta["duration_s"])
                    self.resolution = meta["resolution"]
            else:
                if self._custom_capture_factory is not None:
                    self._cap = self.capture_factory()
                else:
                    self._cap = open_camera(self.cfg, camera_index_override=self.camera_index)
        except Exception as e:
            with self._lock:
                self.error = f"Không khởi động được: {e}"
                self.state = ERROR
            self._release()
            return
        self._t0 = time.monotonic()
        if self.on_session:
            self.on_session("start", dict(session_id=self.session_id, source_id=self.source_id,
                                          source_type=self.source_type, policy_version=self.policy_version))
        with self._lock:
            if self.state == STARTING:
                self.state = RUNNING

        if self.source_type == "camera":
            reader = threading.Thread(target=self._reader, name="live-reader", daemon=True)
            self._threads.append(reader)
            reader.start()

        try:
            if self.source_type == "file":
                self._loop_file(draw)
            else:
                self._loop(draw)
        except Exception as e:
            self._fail(f"Lỗi khi xử lý khung: {e!r}")
        finally:
            self._stop.set()
            self._pause_event.set()
            if reader is not None:
                reader.join(5.0)
            try:
                if self._pipe is not None and self._t0 is not None:
                    self._pipe.close(self._now())
            finally:
                self._release()
                if self.on_session:
                    self.on_session("end", dict(session_id=self.session_id, source_id=self.source_id,
                                                error=self.error))
                with self._lock:
                    self.paused = False
                    self.persons = 0
                    self.persons_detail = []
                    self.state = ERROR if self.error else IDLE
                    self._new_jpeg.notify_all()

    def _process_and_publish_frame(self, frame, t, draw, max_w, quality, win_s):
        with self._lock:
            pending, self._pending_policy = self._pending_policy, None
        if pending is not None:
            self._pipe.set_required(pending[0], pending[1], t)
            with self._lock:
                self.required, self.policy_version = self._pipe.required, pending[1]
        out = self._pipe.process(frame, t)
        open_ev_map = getattr(getattr(self._pipe, "events", None), "open", None) or {}
        persons_detail = summarize_persons_in_frame(out, self.required, open_ev_map)
        img = draw(frame, self._only_required(out), self._pipe.cfg)
        self._overlay(img, out)
        h, w = img.shape[:2]
        if w > max_w:
            img = cv2.resize(img, (max_w, round(h * max_w / w)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        now = time.monotonic()
        with self._lock:
            self.frames += 1
            self.position_s = float(t)
            self.persons = len(out.get("tracks", out.get("persons", [])))
            self.persons_detail = persons_detail
            self.resolution = [w, h]
            self._done.append(now)
            while self._done and self._done[0] <= now - win_s:
                self._done.popleft()
            if ok:
                self._jpeg, self._jpeg_seq = buf.tobytes(), self._jpeg_seq + 1
                self._new_jpeg.notify_all()

    def _loop(self, draw):
        st = self.cfg["stream"]
        max_w, quality, win_s = int(st["max_width"]), int(st["jpeg_quality"]), float(st["fps_window_s"])
        seen = 0
        while not self._stop.is_set():
            with self._lock:
                while self._frame_seq == seen and not self._stop.is_set():
                    self._new_frame.wait(1.0)
                if self._stop.is_set():
                    return
                frame, seen = self._frame, self._frame_seq
            t = time.monotonic() - self._t0
            self._process_and_publish_frame(frame, t, draw, max_w, quality, win_s)

    def _loop_file(self, draw):
        """Đọc tuần tự từng khung từ tệp video, thời gian t = frame_idx / fps_video (khớp 05_run_video.py)."""
        st = self.cfg["stream"]
        max_w, quality, win_s = int(st["max_width"]), int(st["jpeg_quality"]), float(st["fps_window_s"])
        fps = self.video_fps if self.video_fps > 0 else 25.0
        frame_interval = 1.0 / fps
        frame_idx = 0

        while not self._stop.is_set():
            while not self._pause_event.wait(0.1):
                if self._stop.is_set():
                    return
            if self._stop.is_set():
                return

            t_wall_start = time.monotonic()
            ok, frame = self._cap.read()
            if not ok or frame is None:
                # Đã đọc hết tệp video -> kết thúc phiên bình thường
                return

            now = time.monotonic()
            with self._lock:
                self._reads.append(now)
                while self._reads and self._reads[0] <= now - win_s:
                    self._reads.popleft()

            t_video = frame_idx / fps
            frame_idx += 1
            self._process_and_publish_frame(frame, t_video, draw, max_w, quality, win_s)

            if self.playback_mode == "realtime" and not self._stop.is_set():
                elapsed = time.monotonic() - t_wall_start
                remain = frame_interval - elapsed
                if remain > 0.002:
                    self._stop.wait(remain)

    def _only_required(self, out):
        """Bản sao kết quả chỉ để vẽ: bỏ hộp detector của PPE không bắt buộc (người dùng đã tắt món đó thì không vẽ hộp
        xám "(khong xet)", tránh hiểu là vẫn đang kiểm). Không đổi kết quả nhận diện, trạng thái hay sự kiện."""
        req = set(self._pipe.required)
        name_of = {p["cls"]: n for n, p in self._pipe.cfg["ppe"].items() if "cls" in p}
        if "ppe" not in out:
            return out
        return dict(out, ppe=[d for d in out["ppe"] if name_of.get(d.cls) in req])

    def _overlay(self, img, out):
        """Dòng chữ góc trên: nguồn, FPS, PPE đang kiểm (chữ không dấu vì OpenCV không vẽ được tiếng Việt)."""
        short = {"helmet": "Mu", "vest": "Ao", "gloves": "Gang", "goggles": "Kinh", "boots": "Ung"}
        text = (f"{self.source_id}  {self.status()['fps']:.1f} FPS  kiem: "
                + (" ".join(short.get(p, p) for p in self.required) or "(khong)"))
        s = max(0.5, img.shape[0] / 1080 * 0.8)
        (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, s, 1)
        cv2.rectangle(img, (0, 0), (tw + 12, th + base + 10), (0, 0, 0), -1)
        cv2.putText(img, text, (6, th + 5), cv2.FONT_HERSHEY_SIMPLEX, s, (255, 255, 255), 1, cv2.LINE_AA)

    def _release(self):
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
