"""Tự phát hiện camera trong mạng LAN (không cần cài package thêm).

`scripts/laptop_cam_server.py` chạy trên laptop/điện thoại-khác phát UDP broadcast
mỗi 2 giây kèm URL stream. Module này nghe, gom lại; dashboard bấm "Quét camera
trong mạng" sẽ thấy các camera còn "thở" trong 12 giây gần nhất.
Chỉ dùng thư viện chuẩn Python — không thêm phụ thuộc.
"""

import json
import socket
import threading
import time

_STATE = {"cams": {}, "lock": threading.Lock()}
_STARTED = False
_MAX_AGE_S = 12.0


def _listen(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("", port))
    except OSError:
        return   # port bị chiếm (máy khác đã nghe) — bỏ qua, không làm sập app
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            msg = json.loads(data.decode("utf-8", errors="replace"))
            if msg.get("app") != "ppe-cam":
                continue
            url = msg.get("stream") or f"http://{addr[0]}:{msg.get('port', 8078)}/stream.mjpg"
            with _STATE["lock"]:
                _STATE["cams"][url] = {
                    "name": msg.get("name") or f"Cam {addr[0]}",
                    "url": url,
                    "host": addr[0],
                    "last_seen": time.time(),
                }
            # dọn các cam đã im lặng lâu (tránh phình to)
            with _STATE["lock"]:
                for k in [k for k, v in _STATE["cams"].items() if time.time() - v["last_seen"] > 300]:
                    _STATE["cams"].pop(k, None)
        except Exception:
            continue


def start_discovery(port: int):
    """Bật luồng nghe UDP (idempotent — gọi nhiều lần cũng chỉ chạy một listener)."""
    global _STARTED
    if _STARTED:
        return
    threading.Thread(target=_listen, args=(int(port),), daemon=True, name="ppe-cam-discovery").start()
    _STARTED = True


def get_discovered() -> list:
    """Các camera còn phát quảng cáo trong 12 giây gần nhất, sắp theo tên."""
    now = time.time()
    with _STATE["lock"]:
        fresh = [dict(v) for v in _STATE["cams"].values() if now - v["last_seen"] <= _MAX_AGE_S]
    return sorted(fresh, key=lambda c: c["name"])
