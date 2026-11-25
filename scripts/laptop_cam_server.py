"""Server biến webcam của laptop bất kỳ thành camera trong mạng LAN cho app PPE.

Chạy file này trên laptop khác (cùng WiFi với máy chạy app PPE):
    pip install opencv-python
    python laptop_cam_server.py --name "Laptop phong ky thuat"

Nó làm 2 việc:
1. Phát webcam thành stream MJPEG:  http://<IP-laptop>:8078/stream.mjpg
2. Quảng cáo sự tồn tại bằng UDP broadcast mỗi 2 giây (port 50010) —
   app PPE bấm "Quét camera trong mạng" sẽ tự thấy laptop này, không cần gõ IP.

Yêu cầu máy chỉ cần Python 3 + opencv-python; không cần cài gì của project PPE.
"""

import argparse
import json
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

# console Windows thường là cp1252 — ép UTF-8 để in tiếng Việt không văng lỗi
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

STATE = {"jpeg": b"", "lock": threading.Lock(), "fps": 0.0}
ANNOUNCE_PORT = 50010


def local_ip():
    """IP LAN của máy này (không gửi gói nào ra ngoài, chỉ hỏi bảng định tuyến)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def puller(cam_index: int, width: int, height: int):
    api = cv2.CAP_DSHOW if cv2.os.name == "nt" else cv2.CAP_ANY
    frames = 0
    last = time.time()
    while True:
        cap = None
        try:
            cap = cv2.VideoCapture(cam_index, api)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            if not cap.isOpened():
                raise RuntimeError(f"Không mở được webcam {cam_index}")
            while True:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                okj, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if okj:
                    with STATE["lock"]:
                        STATE["jpeg"] = jpeg.tobytes()
                frames += 1
                now = time.time()
                if now - last >= 2.0:
                    STATE["fps"] = frames / (now - last)
                    frames, last = 0, now
        except Exception:
            time.sleep(2)   # webcam rớt: thử lại sau 2 giây
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass


def announcer(name: str, http_port: int, ip: str):
    """Quảng cáo mỗi 2 giây: 'tới là PPE-CAM, stream ở đây' — app PPE nghe được."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = json.dumps({
        "app": "ppe-cam",
        "name": name,
        "host": ip,
        "port": http_port,
        "stream": f"http://{ip}:{http_port}/stream.mjpg",
    }).encode("utf-8")
    while True:
        try:
            sock.sendto(msg, ("255.255.255.255", ANNOUNCE_PORT))
            sock.sendto(msg, (ip.rsplit(".", 1)[0] + ".255", ANNOUNCE_PORT))
        except Exception:
            pass
        time.sleep(2.0)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/stream.mjpg"):
            # Raw MJPEG (các JPEG nối liền) — OpenCV/FFmpeg của app PPE đọc chuẩn
            self.send_response(200)
            self.send_header("Content-Type", "video/x-mjpeg")
            self.end_headers()
            try:
                while True:
                    with STATE["lock"]:
                        jpeg = STATE["jpeg"]
                    if jpeg:
                        self.wfile.write(jpeg)
                    time.sleep(0.05)
            except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
                pass
        elif self.path.startswith("/snapshot.jpg"):
            with STATE["lock"]:
                jpeg = STATE["jpeg"]
            self.send_response(200 if jpeg else 503)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpeg)))
            self.end_headers()
            if jpeg:
                self.wfile.write(jpeg)
        elif self.path.startswith("/status"):
            body = json.dumps({"fps": round(STATE["fps"], 1)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass   # viewer ngắt kết nối là chuyện thường


def main():
    ap = argparse.ArgumentParser(description="Biến webcam laptop thành camera trong mạng LAN cho app PPE")
    ap.add_argument("--port", type=int, default=8078, help="cổng HTTP phát stream")
    ap.add_argument("--camera", type=int, default=0, help="chỉ số webcam (0 = mặc định)")
    ap.add_argument("--name", default=None, help="tên hiển thị trong app PPE (mặc định = tên máy)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    ip = local_ip()
    name = args.name or socket.gethostname()
    threading.Thread(target=puller, args=(args.camera, args.width, args.height), daemon=True).start()
    threading.Thread(target=announcer, args=(name, args.port, ip), daemon=True).start()

    print(f"[laptop-cam] Webcam {args.camera} của máy '{name}' ({ip}) đang phát trên mạng LAN:")
    print(f"[laptop-cam]   stream : http://{ip}:{args.port}/stream.mjpg")
    print(f"[laptop-cam]   trạng thái: http://{ip}:{args.port}/status")
    print(f"[laptop-cam]   quảng cáo UDP mỗi 2s tới port {ANNOUNCE_PORT} — app PPE bấm 'Quét camera trong mạng' sẽ thấy")
    print("[laptop-cam]   (giữ cửa sổ này mở; Ctrl+C để tắt)")
    QuietServer(("0.0.0.0", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
