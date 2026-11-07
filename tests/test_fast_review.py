"""Kiểm tra công cụ duyệt nhanh. Dữ liệu tự tạo trong thư mục tạm, reviewer AGENT_TEST, CVAT giả, không đụng dữ liệu thật."""

import csv
import importlib.util
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from PIL import Image

from ppe.fast_review import Conflict, Cvat, Session, load_pack, plan_boxes, sync, verify_cvat, verify_export
from ppe.ppe6_data import UNSET, leak_tokens

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
FRAMES = ["img_000002.jpg", "img_000005.jpg", "img_000009.jpg"]
ITEMS = [("r00011", 0, 10, 10, 40, 40), ("r00012", 0, 50, 50, 90, 90), ("r00013", 1, 20, 20, 60, 60), ("r00014", 2, 30, 30, 70, 70)]


def make_pack(folder, person=True):
    folder.mkdir(parents=True)
    with zipfile.ZipFile(folder / "images.zip", "w") as z:
        for i, n in enumerate(FRAMES):
            b = io.BytesIO()
            Image.new("RGB", (200, 150), (40 * i, 90, 120)).save(b, "JPEG")
            z.writestr(n, b.getvalue())
    x = ['<annotations><version>1.1</version>']
    for i, n in enumerate(FRAMES):
        x.append(f'<image id="{i}" name="{n}" width="200" height="150">')
        for it, f, a, b, c, d in ITEMS:
            if f == i:
                p = '<attribute name="person_ok">chua_chon</attribute>' if person else ""
                x.append(f'<box label="boots_review" xtl="{a}" ytl="{b}" xbr="{c}" ybr="{d}"><attribute name="item_id">{it}</attribute><attribute name="decision">chua_chon</attribute>{p}</box>')
        x.append("</image>")
    (folder / "annotations.xml").write_text("".join(x) + "</annotations>", encoding="utf-8")
    attrs = [dict(name="item_id"), dict(name="decision")] + ([dict(name="person_ok")] if person else [])
    (folder / "labels.json").write_text(json.dumps([dict(name="boots_review", attributes=attrs), dict(name="image_checked", attributes=[]), dict(name="reject_image", attributes=[]), dict(name="boots_new", attributes=[])]), encoding="utf-8")
    return folder


def session(tmp_path, task="trial", person=True, name="AGENT_TEST"):
    pack = tmp_path / "pack"
    if not pack.exists():
        make_pack(pack, person)
    state = tmp_path / "state"
    state.mkdir(exist_ok=True)
    return Session(load_pack(pack), task, name, state)


def fill(s):
    for i, k in enumerate(sorted(s.items)):
        s.set_box(k, "decision", ["safety", "ordinary", "unclear", "ignore"][i])
        s.set_box(k, "person_ok", ["du_lon", "qua_nho", "khong_ro", "du_lon"][i])


class FakeCvat:
    """Phần API CVAT mà công cụ dùng, giữ dữ liệu trong bộ nhớ."""

    def __init__(self):
        self.labels = {"boots_review": 1, "image_checked": 2, "reject_image": 3, "boots_new": 4}
        self.specs = {10: "item_id", 11: "decision", 12: "person_ok"}
        self.shapes = [dict(id=n, type="rectangle", frame=f, label_id=1, points=[float(a), float(b), float(c), float(d)], attributes=[dict(spec_id=10, value=it), dict(spec_id=11, value=UNSET), dict(spec_id=12, value=UNSET)]) for n, (it, f, a, b, c, d) in enumerate(ITEMS, 1)]
        self.tags, self.calls = [], []
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, obj, kind="application/json", code=200):
                b = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):
                u = urlparse(self.path)
                if self.headers.get("Authorization") != "Bearer test-token":
                    return self.send({}, code=401)
                if u.path == "/api/labels":
                    res = [dict(id=v, name=k, attributes=[dict(id=i, name=n) for i, n in fake.specs.items()] if k == "boots_review" else []) for k, v in fake.labels.items()]
                    return self.send(dict(results=res))
                if u.path.endswith("/annotations"):
                    return self.send(dict(shapes=fake.shapes, tags=fake.tags, tracks=[], version=0))
                if u.path.endswith("/data/meta"):
                    return self.send(dict(frames=[dict(name=n) for n in FRAMES]))
                if u.path.startswith("/api/requests/"):
                    return self.send(dict(status="finished", result_url=f"http://127.0.0.1:{fake.port}/result.zip"))
                if u.path == "/result.zip":
                    return self.send(fake.export(), "application/zip")
                return self.send({}, code=404)

            def do_POST(self):
                fake.calls.append(("POST", self.path))
                self.send(dict(rq_id="x"), code=202)

            def do_PATCH(self):
                u = urlparse(self.path)
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                action = parse_qs(u.query)["action"][0]
                fake.calls.append((action, len(body["shapes"]), len(body["tags"])))
                if action == "update":
                    for sh in body["shapes"]:
                        i = next(n for n, x in enumerate(fake.shapes) if x["id"] == sh["id"])
                        fake.shapes[i] = sh
                elif action == "create":
                    for n, t in enumerate(body["tags"], len(fake.tags) + 100):
                        fake.tags.append(dict(t, id=n))
                elif action == "delete":
                    gone = {t["id"] for t in body["tags"]}
                    fake.tags = [t for t in fake.tags if t["id"] not in gone]
                self.send({})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def values(self):
        return {[a for a in s["attributes"] if a["spec_id"] == 10][0]["value"]: {self.specs[a["spec_id"]]: a["value"] for a in s["attributes"]} for s in self.shapes}

    def set_value(self, item, spec, value):
        for s in self.shapes:
            if any(a["spec_id"] == 10 and a["value"] == item for a in s["attributes"]):
                next(a for a in s["attributes"] if a["spec_id"] == spec)["value"] = value

    def export(self):
        x = ["<annotations>"]
        names = {v: k for k, v in self.labels.items()}
        for i, n in enumerate(FRAMES):
            x.append(f'<image id="{i}" name="{n}" width="200" height="150">')
            x += [f'<tag label="{names[t["label_id"]]}" source="manual"/>' for t in self.tags if t["frame"] == i]
            for s in self.shapes:
                if s["frame"] == i:
                    p = s["points"]
                    at = "".join(f'<attribute name="{self.specs[a["spec_id"]]}">{a["value"]}</attribute>' for a in s["attributes"])
                    x.append(f'<box label="{names[s["label_id"]]}" xtl="{p[0]}" ytl="{p[1]}" xbr="{p[2]}" ybr="{p[3]}">{at}</box>')
            x.append("</image>")
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("annotations.xml", "".join(x) + "</annotations>")
        return b.getvalue()


@pytest.fixture
def fake():
    f = FakeCvat()
    yield f
    f.server.shutdown()


def client(fake):
    return Cvat(f"http://127.0.0.1:{fake.port}", "test-token", 99)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_ui(tmp_path, port=None, task="trial", extra=()):
    pack = tmp_path / "pack"
    if not pack.exists():
        make_pack(pack)
    (tmp_path / "state").mkdir(exist_ok=True)
    port = port or free_port()
    p = subprocess.Popen([PY, str(ROOT / "scripts" / "03q_ppe6_fast_review.py"), "--task", task, "--reviewer", "AGENT_TEST", "--port", str(port), "--state-dir", str(tmp_path / "state"), "--pack-dir", str(pack), "--cvat-task-id", "99", *extra], cwd=ROOT, stdout=subprocess.PIPE, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    p.stdout.readline()
    return p, port


def call(port, path, body=None, headers=None):
    h = {"Content-Type": "application/json"} if body is not None else {}
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=None if body is None else json.dumps(body).encode(), headers=h | (headers or {}))
    try:
        with urllib.request.urlopen(r, timeout=10) as x:
            return x.status, x.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_new_session_has_no_values_and_cannot_finish(tmp_path):
    s = session(tmp_path)
    assert all(v == UNSET for b in s.s["boxes"].values() for v in b.values())
    assert len(s.missing()) == 8
    with pytest.raises(ValueError):
        s.finish()


def test_set_one_box_only_and_resume_keeps_it(tmp_path):
    s = session(tmp_path)
    s.set_box("r00012", "decision", "ordinary")
    assert s.s["boxes"]["r00012"]["decision"] == "ordinary" and s.s["boxes"]["r00011"]["decision"] == UNSET
    s.set_cursor(2)
    again = session(tmp_path)
    assert again.s["boxes"]["r00012"]["decision"] == "ordinary" and again.s["cursor"] == 2


def test_back_edit_is_logged_with_before_and_after(tmp_path):
    s = session(tmp_path)
    s.set_box("r00011", "decision", "safety")
    s.set_box("r00011", "decision", "unclear")
    rows = list(csv.DictReader(s.log_path.open(encoding="utf-8")))
    assert [(r["before"], r["after"]) for r in rows] == [(UNSET, "safety"), ("safety", "unclear")]
    assert rows[0]["reviewer"] == "AGENT_TEST" and rows[0]["target"] == "r00011" and rows[0]["time"]


def test_test_name_and_non_person_refused(tmp_path):
    with pytest.raises(ValueError):
        session(tmp_path, task="task_a")
    with pytest.raises(ValueError):
        session(tmp_path, name="Claude")
    session(tmp_path).set_box("r00011", "decision", "safety")
    with pytest.raises(ValueError):
        session(tmp_path, name="AGENT_TEST2")


def test_flag_blocks_finish_and_gives_direct_link(tmp_path):
    s = session(tmp_path)
    fill(s)
    s.set_mark("flags", "box:r00014", True)
    with pytest.raises(ValueError):
        s.finish()
    assert s.flag_links("http://localhost:8080", 5, 5)[0]["url"] == "http://localhost:8080/tasks/5/jobs/5?frame=2"
    s.set_mark("flags", "box:r00014", False)
    s.finish()
    assert s.s["finished_at"]


def test_image_step_required_for_image_tasks(tmp_path):
    make_pack(tmp_path / "pack")
    (tmp_path / "state").mkdir()
    s = Session(load_pack(tmp_path / "pack"), "task_d", "Nguoi That", tmp_path / "state")
    assert [x for x in s.missing() if x.endswith("image")] == [f"{n}: image" for n in FRAMES]
    assert sum(x["type"] == "image" for x in s.steps()) == 3


def test_plan_writes_only_human_values_and_detects_conflict():
    cur = dict(a=dict(decision=UNSET), b=dict(decision="safety"), c=dict(decision="safety"))
    want = dict(a=dict(decision="ordinary"), b=dict(decision="ordinary"), c=dict(decision=UNSET))
    up, bad = plan_boxes(cur, want, dict(c=dict(decision="safety")))
    assert up == dict(a=dict(decision="ordinary"), c=dict(decision=UNSET)) and bad == ["b: decision"]
    assert plan_boxes(dict(a=dict(decision=UNSET)), dict(a=dict(decision=UNSET)), {}) == ({}, [])


def test_sync_writes_exact_cells_keeps_moved_box_and_is_idempotent(tmp_path, fake):
    s = session(tmp_path)
    s.set_box("r00011", "decision", "safety")
    fake.shapes[0]["points"] = [11.0, 12.0, 41.0, 42.0]
    s.set_image(FRAMES[1], "image_checked")
    c = client(fake)
    assert sync(s, c) == (1, 1)
    assert fake.values()["r00011"]["decision"] == "safety" and fake.values()["r00012"]["decision"] == UNSET
    assert fake.shapes[0]["points"] == [11.0, 12.0, 41.0, 42.0]
    calls = len(fake.calls)
    assert sync(s, c) == (0, 0) and len(fake.calls) == calls
    s.set_image(FRAMES[1], "")
    sync(s, c)
    assert fake.tags == []


def test_sync_stops_on_cvat_edit_without_overwriting(tmp_path, fake):
    s = session(tmp_path)
    s.set_box("r00011", "decision", "safety")
    fake.set_value("r00011", 11, "unclear")
    with pytest.raises(Conflict):
        sync(s, client(fake))
    assert fake.values()["r00011"]["decision"] == "unclear" and not fake.calls


def test_sync_stops_when_box_deleted_on_cvat(tmp_path, fake):
    s = session(tmp_path)
    fake.shapes.pop()
    with pytest.raises(Conflict):
        sync(s, client(fake))


def write_private(blind):
    p = blind / "_private"
    p.mkdir(parents=True)
    keys = ["item_id", "box_id", "group", "target", "source", "set", "file", "image_name", "cx", "cy", "w", "h", "agent_label", "agent_note", "person_h_px"]
    with (p / "trial_items.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, keys, restval="")
        w.writeheader()
        for it, fr, a, b, c, d in ITEMS:
            w.writerow(dict(item_id=it, box_id="b" + it[1:], group="P0a", target="boots", source="sh17", file=f"f{fr}.jpg", image_name=FRAMES[fr], cx=(a + c) / 400, cy=(b + d) / 300, w=(c - a) / 200, h=(d - b) / 150, agent_label="safety"))
    (p / "trial_images.csv").write_text("image_name,file\n" + "".join(f"{n},f{i}.jpg\n" for i, n in enumerate(FRAMES)), encoding="utf-8")


def finish(tmp_path, fake, *extra):
    env = dict(os.environ, CVAT_LOCAL_TOKEN="test-token", PYTHONIOENCODING="utf-8")
    return subprocess.run([PY, str(ROOT / "scripts" / "03r_ppe6_fast_finish.py"), "--task", "trial", "--reviewer", "AGENT_TEST", "--state-dir", str(tmp_path / "state"), "--review-dir", str(tmp_path / "rev"), "--blind-dir", str(tmp_path / "blind"),
                           "--pack-dir", str(tmp_path / "pack"), "--cvat-task-id", "99", "--cvat-url", f"http://127.0.0.1:{fake.port}", *extra], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)


def test_finish_compares_every_box_and_reimport_adds_nothing(tmp_path, fake):
    s = session(tmp_path)
    (tmp_path / "rev").mkdir()
    write_private(tmp_path / "blind")
    s.set_cursor(0)
    r = finish(tmp_path, fake)
    assert r.returncode == 2 and "8 ô thiếu" in r.stdout and not fake.calls
    fill(s)
    r = finish(tmp_path, fake)
    assert r.returncode == 0, r.stdout + r.stderr
    rows = list(csv.DictReader((tmp_path / "rev" / "trial_review.csv").open(encoding="utf-8")))
    got = {"r" + x["box_id"][1:]: dict(decision=x["after"], person_ok=x["person_ok"]) for x in rows}
    assert got == s.s["boxes"] == {k: {f: v[f] for f in ("decision", "person_ok")} for k, v in fake.values().items()}
    assert all(x["reviewer"] == "AGENT_TEST" for x in rows) and not (tmp_path / "rev" / "human_review.csv").exists()
    export = next((tmp_path / "rev").glob("export_trial_*.zip"))
    with zipfile.ZipFile(export) as z:
        assert verify_export(s, z.read("annotations.xml").decode()) == []
    assert verify_cvat(s, client(fake)) == ([], 0)
    r = finish(tmp_path, fake)
    assert r.returncode == 0 and len(list(csv.DictReader((tmp_path / "rev" / "trial_review.csv").open(encoding="utf-8")))) == 4


def test_partial_imports_only_chosen_and_flag_stops_without_it(tmp_path, fake):
    s = session(tmp_path)
    (tmp_path / "rev").mkdir()
    write_private(tmp_path / "blind")
    fill(s)
    s.set_mark("flags", "image:" + FRAMES[0], True)
    r = finish(tmp_path, fake)
    assert r.returncode == 2 and "1 mục cần mở CVAT" in r.stdout and "frame=0" in r.stdout
    s.set_mark("flags", "image:" + FRAMES[0], False)
    s.set_box("r00014", "decision", UNSET)
    s.set_box("r00014", "person_ok", UNSET)
    r = finish(tmp_path, fake, "--partial")
    assert r.returncode == 0, r.stdout + r.stderr
    rows = list(csv.DictReader((tmp_path / "rev" / "trial_review.csv").open(encoding="utf-8")))
    assert len(rows) == 3 and "b00014" not in {x["box_id"] for x in rows}


def test_token_never_printed_or_stored(tmp_path, fake):
    s = session(tmp_path)
    (tmp_path / "rev").mkdir()
    write_private(tmp_path / "blind")
    fill(s)
    r = finish(tmp_path, fake)
    assert "test-token" not in r.stdout + r.stderr
    for f in [*(tmp_path / "state").iterdir(), *(tmp_path / "rev").glob("*.csv")]:
        assert b"test-token" not in f.read_bytes()


def test_no_private_access_in_review_code():
    for name in ("src/ppe/fast_review.py", "src/ppe/fast_review_ui.html", "scripts/03q_ppe6_fast_review.py"):
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        assert "_private" not in text and "agent_label" not in text and "decisions_v2" not in text


def test_ui_has_no_default_or_bulk_code():
    text = (ROOT / "src" / "ppe" / "fast_review_ui.html").read_text(encoding="utf-8").lower()
    for word in ("select all", "apply_all", "bulk", "suggest", "chọn tất cả", "áp dụng cho tất cả", "đề xuất", "predict"):
        assert word not in text


def test_server_binds_localhost_rejects_bulk_and_leaks_nothing(tmp_path):
    p, port = start_ui(tmp_path)
    try:
        page = call(port, "/")[1].decode("utf-8")
        state = call(port, "/api/state")[1].decode("utf-8")
        assert leak_tokens(page, allow_decisions=True) == [] and leak_tokens(state, allow_decisions=True) == []
        assert "AGENT_TEST" not in state
        for bad in ({"kind": "box", "item_id": ["r00011", "r00012"], "field": "decision", "value": "safety"}, {"kind": "box", "items": ["r00011"], "field": "decision", "value": "safety"},
                    {"kind": "all", "value": "safety"}, {"kind": "box", "item_id": "*", "field": "decision", "value": "safety"}, [{"kind": "box", "item_id": "r00011", "field": "decision", "value": "safety"}]):
            assert call(port, "/api/action", bad)[0] == 400
        assert call(port, "/api/bulk", {"value": "safety"})[0] == 404
        assert call(port, "/api/action", {"kind": "box", "item_id": "r00011", "field": "decision", "value": "safety"}, {"Origin": "http://evil.example"})[0] == 403
        assert call(port, "/api/state", headers={"Host": "evil.example"})[0] == 403
        assert all(v == UNSET for b in json.loads(call(port, "/api/state")[1])["boxes"].values() for v in b.values())
        assert call(port, "/image/..%2f..%2fconfigs")[0] == 404
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
        listen = [x.split()[1] for x in out.splitlines() if f":{port} " in x and "LISTENING" in x]
        assert listen == [f"127.0.0.1:{port}"]
    finally:
        p.kill()


CHROME = shutil.which("chrome") or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
NODE = shutil.which("node") or "E:/Node/node.exe"


@pytest.mark.skipif(not (Path(NODE).exists() and Path(CHROME).exists()), reason="cần Node và Chrome")
def test_real_keys_in_browser(tmp_path):
    p, port = start_ui(tmp_path)
    plan = [dict(read=1), dict(key="1"), dict(read=1), dict(key="8"), dict(read=1), dict(key="ArrowLeft"), dict(read=1), dict(key="2"), dict(read=1), dict(key="ArrowRight"), dict(key="s"), dict(read=1), dict(key="c"), dict(reload=1), dict(read=1),
            dict(finish=1), dict(read=1), dict(key="Delete"), dict(read=1)]
    try:
        r = subprocess.run([NODE, str(ROOT / "tests" / "fast_review_browser.mjs"), CHROME, f"http://127.0.0.1:{port}/", str(free_port()), json.dumps(plan)], capture_output=True, text=True, encoding="utf-8", timeout=90)
        assert r.returncode == 0, r.stderr
        v = json.loads(r.stdout)
        st = json.loads(call(port, "/api/state")[1])
    finally:
        p.kill()
    assert v[0]["cursor"] == 0 and v[0]["on"] == [] and v[0]["full"] > 0
    assert v[1]["cursor"] == 0 and v[1]["on"] == ["1"]            # mới có decision, chưa sang hộp khác
    assert v[2]["cursor"] == 1 and v[2]["on"] == []               # đủ hai ô thì sang hộp sau, hộp sau không có giá trị
    assert v[3]["cursor"] == 0 and sorted(v[3]["on"]) == ["1", "8"]
    assert v[4]["cursor"] == 1                                    # sửa ở hộp đã đủ
    assert v[5]["cursor"] == 3 and "Xem sau 1" in v[5]["count"]
    assert v[6]["cursor"] == 3 and "Cần mở CVAT 1" in v[6]["count"]
    assert "Còn" in v[7]["msg"]                                   # không cho hoàn tất
    first = st["steps"][0]["item_id"]
    assert st["boxes"][first] == dict(decision="ordinary", person_ok="qua_nho")
    assert sum(b["decision"] != UNSET for b in st["boxes"].values()) == 1
    assert st["finished_at"] is None
    assert leak_tokens(v[0]["text"], allow_decisions=True) == []


@pytest.mark.skipif(not (Path(NODE).exists() and Path(CHROME).exists()), reason="cần Node và Chrome")
def test_image_step_keys_in_browser(tmp_path):
    p, port = start_ui(tmp_path, extra=["--image-step"])
    plan = [dict(key="1"), dict(key="7"), dict(read=1), dict(key="2"), dict(key="9"), dict(read=1), dict(key="1"), dict(read=1), dict(key="v"), dict(read=1), dict(key="ArrowLeft"), dict(key="r"), dict(read=1), dict(key="m"), dict(read=1)]
    try:
        r = subprocess.run([NODE, str(ROOT / "tests" / "fast_review_browser.mjs"), CHROME, f"http://127.0.0.1:{port}/", str(free_port()), json.dumps(plan)], capture_output=True, text=True, encoding="utf-8", timeout=90)
        assert r.returncode == 0, r.stderr
        v = json.loads(r.stdout)
        st = json.loads(call(port, "/api/state")[1])
    finally:
        p.kill()
    assert v[1]["cursor"] == 2 and "xem ảnh" in v[1]["pos"]                  # hết hộp của ảnh thì tới bước xem ảnh
    assert v[2]["cursor"] == 2 and st["boxes"]["r00011"]["decision"] == "safety"   # phím số ở bước ảnh không ghi gì
    assert sum(b["decision"] != UNSET for b in st["boxes"].values()) == 2
    assert v[3]["cursor"] == 3                                                 # V xong thì sang ảnh sau
    assert st["images"] == {FRAMES[0]: "reject_image"}                          # chỉ đúng ảnh đó, R thay cho V
    assert list(st["flags"]) == ["image:" + FRAMES[1]] and "frame=1" in st["links"][0]["url"]   # R xong đã sang ảnh sau, M đánh dấu ảnh đang xem

