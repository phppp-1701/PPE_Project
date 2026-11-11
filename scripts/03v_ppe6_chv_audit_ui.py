"""Web app kiểm tra và duyệt các ảnh nghi ngờ (khung trùng, nghi ngờ thiếu khung) cho ảnh CHV vẽ ủng.
Khởi động:
    python scripts/03v_ppe6_chv_audit_ui.py --port 8888
Sau đó mở http://127.0.0.1:8888 trong trình duyệt.
"""
import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SP = Path(r"C:\Users\HP\.gemini\antigravity\brain\bf0b4b9b-49af-453f-883e-3556e686a077\scratch\chvd")
DATA_JSON = SP / "audit_data.json"
DECISIONS_FILE = ROOT / "data" / "ppe6" / "review" / "chv_audit_decisions.json"
DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

HTML_FILE = ROOT / "scripts" / "chv_audit_template.html"

class AuditHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Giảm ồn console

    def reply(self, code, body, content_type="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(self.path.split("?")[0])
        if path in ("/", "/index.html"):
            if HTML_FILE.exists():
                content = HTML_FILE.read_bytes()
                self.reply(200, content, "text/html; charset=utf-8")
            else:
                self.reply(404, b"HTML file not found", "text/plain")
        elif path == "/api/data":
            if DATA_JSON.exists():
                self.reply(200, DATA_JSON.read_bytes(), "application/json")
            else:
                self.reply(404, b"{}", "application/json")
        elif path == "/api/decisions":
            if DECISIONS_FILE.exists():
                self.reply(200, DECISIONS_FILE.read_bytes(), "application/json")
            else:
                self.reply(200, b"{}", "application/json")
        elif path.startswith("/img/"):
            filename = path[5:]
            img_path = ROOT / "data" / "ppe4" / "dataset" / "images" / "train" / filename
            if img_path.exists():
                mime, _ = mimetypes.guess_type(str(img_path))
                self.reply(200, img_path.read_bytes(), mime or "image/jpeg")
            else:
                self.reply(404, b"Image not found", "text/plain")
        else:
            self.reply(404, b"Not found", "text/plain")

    def do_POST(self):
        path = unquote(self.path.split("?")[0])
        if path == "/api/save_decisions":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                DECISIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                self.reply(200, json.dumps({"status": "ok", "count": len(data)}).encode("utf-8"), "application/json")
            except Exception as e:
                self.reply(500, json.dumps({"error": str(e)}).encode("utf-8"), "application/json")
        else:
            self.reply(404, b"Not found", "text/plain")

def run(port=8888):
    server = ThreadingHTTPServer(("127.0.0.1", port), AuditHandler)
    print(f"Server audit CHV dang chay tai http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDa dung server.")
        server.server_close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()
    run(args.port)

