"""Fofu FF-8120WP/B bridge v2 — native CACS login + RTMP pull -> MJPEG.

Khác bridge v1 (hack snapshot ~10fps): dùng đúng protocol CACS của camera
(DH key exchange + DES theo shared secret, login bằng md5(password) đã lưu
trong localStorage web UI) để lấy URL RTMP H.264 thật (~13-15fps) rồi phát
MJPEG cho app PPE:

    cv2.VideoCapture("http://127.0.0.1:8077/stream.mjpg")

Chạy:  python scripts/fofu_bridge.py [--token p0|p1] [--port 8077]
"""
import argparse
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Low-latency FFmpeg options cho RTMP (rtmp_buffer mặc định 3000ms!)
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "fflags;nobuffer|flags;low_delay|probesize;500000|analyzeduration;0|rtmp_buffer;100")

import cv2

from mipc_camera_client import MipcCameraClient
from mipc_camera_client.crypto_helpers import des_encrypt_password_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("fofu-bridge")

HOST = "192.168.1.202"
SN = "1jfiegbqnuu6a"
STORED_MD5 = "994b89017e4c7143ef7ff13a5901dbf7"  # md5(password) từ localStorage

STATE = {"jpeg": b"", "lock": threading.Lock(), "fps": 0.0, "err": "starting", "url": ""}


def native_login() -> MipcCameraClient:
    c = MipcCameraClient(HOST)
    c._r.headers["Referer"] = f"http://{HOST}/"
    c.run_dh()
    resp = c.run_rpc("cacs_login_req", {
        "dlid": c.lid,
        "dnid": c._create_nid_ex(2),
        "duser": SN,
        "dpass": des_encrypt_password_hash(STORED_MD5, str(c.shared_secret)),
        "dsession_req": 1,
        "dparam__x_countz_": 1, "dparam": 1,
        "dparam_name": "spv", "dparam_value": "v1",
    })
    result = resp.get("data", {}).get("result", "(missing)")
    if result != "":
        raise RuntimeError(f"login failed: {result}")
    c._handle_login_response(resp)
    return c


def puller(token: str):
    """Vòng lặp chính: login -> RTMP -> pull -> relogin khi chết."""
    backoff = 3
    while True:
        try:
            LOG.info("login CACS ...")
            c = native_login()
            url = c.get_rtmp_stream(token)
            STATE["url"] = url
            LOG.info("RTMP[%s]: %s", token, url)
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not cap.isOpened():
                raise RuntimeError("không mở được RTMP")
            STATE["err"] = ""
            backoff = 3
            frames = 0
            last = time.time()
            dead = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    dead += 1
                    if dead > 30:  # ~3s không có frame -> coi như chết
                        raise RuntimeError("stream dead (no frames)")
                    time.sleep(0.1)
                    continue
                dead = 0
                okj, jpeg = cv2.imencode(".jpg", frame,
                                         [cv2.IMWRITE_JPEG_QUALITY, 80])
                if okj:
                    with STATE["lock"]:
                        STATE["jpeg"] = jpeg.tobytes()
                frames += 1
                now = time.time()
                if now - last >= 2.0:
                    STATE["fps"] = frames / (now - last)
                    frames = 0
                    last = now
        except Exception as e:
            STATE["err"] = f"{type(e).__name__}: {e}"
            LOG.warning("stream lỗi: %s — retry sau %ss", e, backoff)
            try:
                cap.release()
            except Exception:
                pass
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/stream.mjpg"):
            # Raw MJPEG (các JPEG nối liền, KHÔNG multipart header) — FFmpeg
            # demuxer đọc chuẩn, không bị kệch buffer như multipart.
            self.send_response(200)
            self.send_header("Content-Type", "video/x-mjpeg")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                while True:
                    with STATE["lock"]:
                        jpeg = STATE["jpeg"]
                    if jpeg:
                        self.wfile.write(jpeg)
                    time.sleep(0.03)  # ~30fps emit cap, theo nhịp puller
            except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
                pass
        elif self.path.startswith("/status"):
            body = (f'{{"fps": {STATE["fps"]:.1f}, "err": "{STATE["err"]}", '
                    f'"url": "{STATE["url"]}"}}').encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/snapshot.jpg"):
            with STATE["lock"]:
                jpeg = STATE["jpeg"]
            self.send_response(200 if jpeg else 503)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpeg)))
            self.end_headers()
            if jpeg:
                self.wfile.write(jpeg)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


class QuietServer(ThreadingHTTPServer):
    """Không in traceback cho các lỗi ngắt kết nối bình thường của viewer."""
    def handle_error(self, request, client_address):
        import sys
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError,
                            BrokenPipeError, TimeoutError)):
            return
        super().handle_error(request, client_address)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8077)
    ap.add_argument("--token", default="p0", choices=["p0", "p1"],
                    help="p0 = 1280x720 (main), p1 = 640x360 (sub)")
    args = ap.parse_args()

    threading.Thread(target=puller, args=(args.token,), daemon=True).start()
    LOG.info("MJPEG: http://127.0.0.1:%d/stream.mjpg | status: /status", args.port)
    QuietServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
