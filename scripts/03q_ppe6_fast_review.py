"""Thử nghiệm 6 lớp: giao diện duyệt nhanh cục bộ. Chỉ tự động hóa thao tác, mọi nhãn do người bấm từng hộp, từng ảnh.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03q_ppe6_fast_review.py --task task_a --reviewer "Tên bạn"
Rồi mở http://127.0.0.1:8765 bằng Chrome. Đóng và mở lại thì tiếp tục đúng chỗ.

Chỉ nghe trên 127.0.0.1, không cần token CVAT, không đọc thư mục ánh xạ riêng của gói mù.
Ghi data/ppe6/review/fast_<task>_state.json (lưu sau mỗi thao tác), fast_<task>_log.csv (nhật ký: người duyệt, thời gian, mã, giá trị trước, sau).
Cuối buổi chạy 03r_ppe6_fast_finish.py. Tham số ở configs/ppe6.yaml mục `fast_review`.
"""

import argparse
import json
import sys
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.fast_review import Session, load_pack  # noqa: E402

HOST = "127.0.0.1"
ACTIONS = {"box": {"kind", "item_id", "field", "value"}, "image": {"kind", "image", "value"}, "mark": {"kind", "table", "key", "on"}, "cursor": {"kind", "cursor"}}


def build_server(session, zip_path, cfg, port, task_id, job_id):
    lock = threading.Lock()
    page = (ROOT / "src" / "ppe" / "fast_review_ui.html").read_text(encoding="utf-8").replace("__CONTEXT__", str(cfg["zoom_context"])).encode("utf-8")
    pictures = zipfile.ZipFile(zip_path)
    names = set(session.names)
    allowed = {f"{HOST}:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, code, body, kind="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def state(self, code=200):
            self.reply(code, json.dumps(session.view(cfg["cvat_url"], task_id, job_id), ensure_ascii=False).encode("utf-8"))

        def fail(self, code, text):
            self.reply(code, json.dumps(dict(error=text), ensure_ascii=False).encode("utf-8"))

        def local(self):
            """Chặn trang web khác gọi vào công cụ qua trình duyệt."""
            origin = self.headers.get("Origin")
            return self.headers.get("Host") in allowed and (origin is None or origin.split("//")[-1] in allowed)

        def do_GET(self):
            if not self.local():
                return self.fail(403, "Chỉ dùng trên máy này.")
            if self.path == "/":
                return self.reply(200, page, "text/html; charset=utf-8")
            if self.path == "/api/state":
                with lock:
                    return self.state()
            if self.path.startswith("/image/") and unquote(self.path[7:]) in names:
                with lock:
                    data = pictures.read(unquote(self.path[7:]))
                return self.reply(200, data, "image/jpeg")
            return self.fail(404, "Không có.")

        def do_POST(self):
            if not self.local() or self.headers.get("Content-Type") != "application/json":
                return self.fail(403, "Chỉ dùng trên máy này.")
            size = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(size) or b"{}")
            except ValueError:
                return self.fail(400, "Dữ liệu sai.")
            if not isinstance(body, dict):
                return self.fail(400, "Mỗi lần chỉ một thao tác.")
            with lock:
                try:
                    if self.path == "/api/finish":
                        session.finish()
                    elif self.path == "/api/action":
                        self.apply(body)
                    else:
                        return self.fail(404, "Không có.")
                except ValueError as e:
                    return self.fail(400, str(e))
                return self.state()

        def apply(self, b):
            kind = b.get("kind")
            if kind not in ACTIONS or set(b) != ACTIONS[kind]:
                raise ValueError("Thao tác không hợp lệ.")
            if any(isinstance(v, (list, dict)) for v in b.values()):
                raise ValueError("Mỗi lần chỉ một hộp hoặc một ảnh.")
            if kind == "box":
                session.set_box(b["item_id"], b["field"], b["value"])
            elif kind == "image":
                session.set_image(b["image"], b["value"])
            elif kind == "mark":
                session.set_mark(b["table"], b["key"], b["on"])
            else:
                session.set_cursor(b["cursor"])

    return ThreadingHTTPServer((HOST, port), Handler)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", required=True, choices=["task_a", "task_b", "task_c", "task_d", "trial"])
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--port", type=int)
    ap.add_argument("--state-dir", help="thư mục lưu phiên, bắt buộc với task trial")
    ap.add_argument("--pack-dir", help="thư mục gói, chỉ để kiểm thử")
    ap.add_argument("--cvat-task-id", type=int, help="chỉ để kiểm thử")
    ap.add_argument("--image-step", action="store_true", help="chỉ để kiểm thử: thêm bước xem ảnh cho task trial")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["fast_review"]
    if args.task == "trial" and not args.state_dir:
        sys.exit("Task trial chỉ để kiểm thử, cần --state-dir ngoài project.")
    if args.image_step and args.task != "trial":
        sys.exit("--image-step chỉ dùng với task trial.")
    folder = Path(args.pack_dir) if args.pack_dir else ROOT / "data" / "ppe6" / "review" / "cvat_pack_blind" / args.task
    task_id = args.cvat_task_id or cfg["tasks"].get(args.task, 0)
    try:
        session = Session(load_pack(folder), args.task, args.reviewer, Path(args.state_dir) if args.state_dir else ROOT / "data" / "ppe6" / "review", args.image_step)
    except ValueError as e:
        sys.exit(str(e))
    port = args.port or cfg["port"]
    server = build_server(session, folder / "images.zip", cfg, port, task_id, task_id)
    print(f"Mở http://{HOST}:{port} bằng Chrome. Dừng bằng Ctrl + C. Đang duyệt {args.task}, còn {len(session.missing())} ô thiếu.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Đã dừng. Mọi lựa chọn đã được lưu.")


if __name__ == "__main__":
    main()
