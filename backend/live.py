"""Camera trực tiếp trong backend (FR-01, FR-10): đọc webcam, chạy chuỗi xử lý, phát khung đã vẽ cho dashboard.

Hai luồng:
    - luồng đọc: đọc webcam liên tục, chỉ giữ khung MỚI NHẤT (xử lý chậm hơn camera thì bỏ khung cũ, hình không trễ dần);
    - luồng xử lý: lấy khung mới nhất -> Pipeline (nhận diện như configs/pipeline.yaml) -> vẽ (hàm draw của
      scripts/05_run_video.py) -> JPEG cho /api/live/stream. Sự kiện vi phạm đi qua `on_event` (backend ghi SQLite).
Thời gian t của chuỗi xử lý = giây thật kể từ lúc mở phiên (cửa sổ xác nhận vi phạm tính theo giây).
Đổi PPE bắt buộc khi đang chạy: `set_policy` ghi yêu cầu, luồng xử lý áp dụng trước khung kế tiếp
(Pipeline.set_required: đóng sự kiện đang mở với lý do policy_changed, đếm lại từ đầu).
Video webcam không được lưu; chỉ ảnh minh chứng của sự kiện được lưu như khi chạy video.
"""

import copy
import importlib.util
import os
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

ROOT = bundle_root()
LIVE_CONFIG = resolve_resource("configs/live.yaml")
if str(ROOT / "src") not in sys.path and (ROOT / "src").exists():
    sys.path.insert(0, str(ROOT / "src"))

IDLE, STARTING, RUNNING, STOPPING, ERROR = "idle", "starting", "running", "stopping", "error"


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


def open_camera(cfg):
    """Mở webcam theo configs/live.yaml. Trả về cv2.VideoCapture đã mở, lỗi thì RuntimeError."""
    api = cv2.CAP_DSHOW if cfg.get("backend") == "dshow" and os.name == "nt" else cv2.CAP_ANY
    cap = cv2.VideoCapture(int(cfg["camera_index"]), api)
    if not cap.isOpened():
        raise RuntimeError(
            f"Không mở được webcam số {cfg['camera_index']} "
            "(đang bị ứng dụng khác dùng hoặc bị chặn ở Cài đặt Windows > Quyền riêng tư > Camera?)"
        )
    if cfg.get("fourcc"):
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*cfg["fourcc"]))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(cfg["width"]))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(cfg["height"]))
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


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


class LiveCamera:
    def __init__(self, cfg=None, on_event=None, on_session=None,
                 capture_factory=None, pipeline_factory=None, draw_factory=None):
        """on_event(kind, ev): mỗi thay đổi sự kiện (như events.jsonl). on_session("start"|"end", info): ghi phiên.
        Ba factory dùng cho kiểm thử (camera, pipeline, hàm vẽ giả); mặc định là webcam, Pipeline, draw thật."""
        self.cfg = cfg or load_live_config()
        self.source_id = self.cfg["source_id"]
        self.on_event = on_event
        self.on_session = on_session
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
        self._threads = []
        self._cap = self._pipe = None
        self._frame, self._frame_seq = None, 0
        self._jpeg, self._jpeg_seq = None, 0
        self._done = deque()       # thời điểm xử lý xong từng khung (FPS xử lý)
        self._reads = deque()      # thời điểm webcam trả từng khung (FPS camera: xử lý không thể nhanh hơn số này)
        self.frames, self.persons, self.resolution, self.event_errors = 0, 0, None, 0
        self._t0 = None

    # ---------- điều khiển ----------
    def start(self, required_ppe, policy_version):
        """Mở phiên mới (trả về ngay; nạp mô hình và mở camera ở luồng nền). Đang chạy thì báo lỗi."""
        with self._lock:
            if self.state in (STARTING, RUNNING, STOPPING):
                raise RuntimeError(f"Camera đang ở trạng thái {self.state}")
            self._reset()
            self.state = STARTING
            self.session_id = f"{self.source_id}_{datetime.now():%Y%m%d_%H%M%S}"
            self.required, self.policy_version = list(required_ppe), policy_version
        th = threading.Thread(target=self._run, name="live-worker", daemon=True)
        self._threads.append(th)
        th.start()
        return self.status()

    def stop(self, timeout=10.0):
        """Dừng phiên: đóng sự kiện đang mở (session_ended_unverified), tắt webcam."""
        with self._lock:
            active = self.state in (STARTING, RUNNING)
            if active:
                self.state = STOPPING
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
            return dict(state=self.state, error=self.error, source_id=self.source_id, session_id=self.session_id,
                        required_ppe=list(self.required), policy_version=self.policy_version,
                        fps=round(len(done) / win, 1), camera_fps=round(len(reads) / win, 1),
                        frames=self.frames, persons=self.persons,
                        resolution=self.resolution, event_errors=self.event_errors,
                        uptime_s=round(now - self._t0, 1) if self._t0 else 0.0)

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
        return time.monotonic() - self._t0

    def _reader(self):
        fails = 0
        while not self._stop.is_set():
            ok, frame = self._cap.read()
            if not ok or frame is None:
                fails += 1
                if fails >= 50:
                    self._fail("Webcam không trả khung hình (bị ngắt hoặc ứng dụng khác chiếm)")
                    return
                time.sleep(0.02)
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
            self._new_frame.notify_all()
            self._new_jpeg.notify_all()

    def _run(self):
        try:
            draw = self.draw_factory()
            self._pipe = self.pipeline_factory(self.source_id, self.session_id, self._emit)
            self._pipe.set_required(self.required, self.policy_version, 0.0)   # danh sách theo nguồn (có thể rỗng)
            self.required = list(self._pipe.required)                          # thứ tự cố định theo cấu hình
            self._cap = self.capture_factory()
        except Exception as e:
            with self._lock:
                self.error = f"Không khởi động được: {e}"
                self.state = ERROR
            self._release()
            return
        self._t0 = time.monotonic()
        if self.on_session:
            self.on_session("start", dict(session_id=self.session_id, source_id=self.source_id,
                                          policy_version=self.policy_version))
        with self._lock:
            if self.state == STARTING:
                self.state = RUNNING
        reader = threading.Thread(target=self._reader, name="live-reader", daemon=True)
        self._threads.append(reader)
        reader.start()
        try:
            self._loop(draw)
        except Exception as e:
            self._fail(f"Lỗi khi xử lý khung: {e!r}")
        finally:
            self._stop.set()
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
                    self.state = ERROR if self.error else IDLE
                    self._new_jpeg.notify_all()

    def _loop(self, draw):
        st = self.cfg["stream"]
        max_w, quality = int(st["max_width"]), int(st["jpeg_quality"])
        seen = 0
        while not self._stop.is_set():
            with self._lock:
                while self._frame_seq == seen and not self._stop.is_set():
                    self._new_frame.wait(1.0)
                if self._stop.is_set():
                    return
                frame, seen = self._frame, self._frame_seq
                pending, self._pending_policy = self._pending_policy, None
            t = self._now()
            if pending is not None:
                self._pipe.set_required(pending[0], pending[1], t)
                with self._lock:
                    self.required, self.policy_version = self._pipe.required, pending[1]
            out = self._pipe.process(frame, t)
            img = draw(frame, self._only_required(out), self._pipe.cfg)
            self._overlay(img, out)
            h, w = img.shape[:2]
            if w > max_w:
                img = cv2.resize(img, (max_w, round(h * max_w / w)), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
            now = time.monotonic()
            with self._lock:
                self.frames += 1
                self.persons = len(out.get("tracks", out.get("persons", [])))
                self.resolution = [w, h]
                self._done.append(now)
                while self._done and self._done[0] <= now - float(st["fps_window_s"]):
                    self._done.popleft()
                if ok:
                    self._jpeg, self._jpeg_seq = buf.tobytes(), self._jpeg_seq + 1
                    self._new_jpeg.notify_all()

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
