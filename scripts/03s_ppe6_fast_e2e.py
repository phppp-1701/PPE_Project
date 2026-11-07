"""Thử nghiệm 6 lớp: kiểm thử công cụ duyệt nhanh trên CVAT thật, bằng bản sao. Không phải duyệt nhãn.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv, đã đặt CVAT_LOCAL_TOKEN trong phiên):
    python scripts/03s_ppe6_fast_e2e.py

Tạo task mới `fast_agent_test` từ gói trial, đặt giá trị giả theo vị trí qua giao diện, reviewer AGENT_TEST, rồi chạy 03r, so từng hộp giữa giao diện, CVAT, XML, 03l.
Mọi kết quả ghi vào thư mục tạm của hệ thống. Không ghi human_review.csv, không đụng task khác; kiểm tra task đã có không đổi, rồi xóa task kiểm thử.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.fast_review import Cvat, Session, load_pack  # noqa: E402
from ppe.ppe6_data import parse_cvat  # noqa: E402

PACK = ROOT / "data" / "ppe6" / "review" / "cvat_pack_blind" / "trial"
NAME = "fast_agent_test"
DEC = ["safety", "ordinary", "unclear", "ignore"]
PER = ["du_lon", "qua_nho", "khong_ro"]


def ok(r):
    if not r.ok:
        raise RuntimeError(f"CVAT trả {r.status_code}: {r.text[:200]}")
    return r


def wait(h, url, rq):
    for _ in range(300):
        d = ok(h.get(f"{url}/api/requests/{rq}", timeout=60)).json()
        if d["status"] == "finished":
            return
        if d["status"] == "failed":
            raise RuntimeError(str(d.get("message"))[:200])
        time.sleep(1)
    raise TimeoutError(rq)


def fingerprint(h, url):
    out = {}
    for t in ok(h.get(f"{url}/api/tasks", params=dict(page_size=50), timeout=60)).json()["results"]:
        if t["name"] != NAME:
            a = ok(h.get(f"{url}/api/tasks/{t['id']}/annotations", timeout=120)).json()
            out[t["id"]] = (t["name"], t["updated_date"], hashlib.sha256(json.dumps([a["shapes"], a["tags"]], sort_keys=True).encode()).hexdigest())
    return out


def create(h, url):
    tid = ok(h.post(f"{url}/api/tasks", json=dict(name=NAME, labels=json.loads((PACK / "labels.json").read_text(encoding="utf-8"))), timeout=60)).json()["id"]
    with (PACK / "images.zip").open("rb") as f:
        r = ok(h.post(f"{url}/api/tasks/{tid}/data", data=dict(image_quality=95, sorting_method="lexicographical", use_cache="true"), files={"client_files[0]": ("images.zip", f, "application/zip")}, timeout=300))
    wait(h, url, r.json()["rq_id"])
    with (PACK / "annotations.xml").open("rb") as f:
        r = ok(h.post(f"{url}/api/tasks/{tid}/annotations", params=dict(format="CVAT 1.1"), files=dict(annotation_file=("annotations.xml", f, "application/xml")), timeout=120))
    wait(h, url, r.json()["rq_id"])
    return tid


def post(port, body):
    r = urllib.request.Request(f"http://127.0.0.1:{port}/api/action", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=20) as x:
        return json.loads(x.read())


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["fast_review"]
    token = os.environ.get(cfg["token_env"])
    if not token:
        sys.exit(f"Chưa đặt {cfg['token_env']}.")
    url = cfg["cvat_url"]
    h = requests.Session()
    h.headers["Authorization"] = f"Bearer {token}"
    tmp = Path(tempfile.mkdtemp(prefix="fast_e2e_"))
    state, review = tmp / "state", tmp / "review"
    state.mkdir()
    review.mkdir()
    human = ROOT / "data" / "ppe6" / "review" / "human_review.csv"
    before = fingerprint(h, url)
    if any(v[0] == NAME for v in before.values()):
        sys.exit("Đã có task kiểm thử trùng tên.")
    tid = create(h, url)
    print("Task kiểm thử", tid, "; thư mục tạm", tmp)
    port = cfg["port"] + 1
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    ui = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "03q_ppe6_fast_review.py"), "--task", "trial", "--reviewer", "AGENT_TEST", "--port", str(port), "--state-dir", str(state), "--cvat-task-id", str(tid)], cwd=ROOT, stdout=subprocess.PIPE, text=True, encoding="utf-8", env=env)
    ui.stdout.readline()
    failed = []
    try:
        items = sorted(Session(load_pack(PACK), "trial", "AGENT_TEST", state).items)
        view = None
        for i, k in enumerate(items):
            post(port, dict(kind="box", item_id=k, field="decision", value=DEC[i % 4]))
            view = post(port, dict(kind="box", item_id=k, field="person_ok", value=PER[i % 3]))
        ui_values = view["boxes"]
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "03r_ppe6_fast_finish.py"), "--task", "trial", "--reviewer", "AGENT_TEST", "--state-dir", str(state), "--review-dir", str(review), "--cvat-task-id", str(tid)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
        print("03r mã thoát", r.returncode)
        print("\n".join(x for x in r.stdout.splitlines() if "->" not in x))
        if r.returncode:
            print(r.stderr[-500:])
            failed.append("03r")
        lines = {x.split()[0]: x.split() for x in r.stdout.splitlines() if "->" in x}
        c = Cvat(url, token, tid)
        _, by_item, _, _ = c.read()
        export = next(review.glob("export_trial_*.zip"))
        with zipfile.ZipFile(export) as z:
            boxes, _ = parse_cvat(z.read(next(n for n in z.namelist() if n.endswith(".xml"))).decode("utf-8"))
        xml = {b["attrs"]["item_id"]: b["attrs"] for b in boxes if "item_id" in b["attrs"]}
        same = 0
        imported = sorted((x[-3], x[-2]) for x in lines.values())
        for k in items:
            want = ui_values[k]
            same += all(by_item[k][1][f]["value"] == want[f] == xml[k][f] for f in ("decision", "person_ok"))
        expect = sorted((v["decision"], v["person_ok"]) for v in ui_values.values())
        print(f"Từng hộp giao diện, CVAT, XML khớp {same}/{len(items)}; 03l khớp {imported == expect}")
        if same != len(items) or imported != expect:
            failed.append("so sánh")
        r2 = subprocess.run([sys.executable, str(ROOT / "scripts" / "03r_ppe6_fast_finish.py"), "--task", "trial", "--reviewer", "AGENT_TEST", "--state-dir", str(state), "--review-dir", str(review), "--cvat-task-id", str(tid)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
        n = sum(1 for _ in (review / "trial_review.csv").open(encoding="utf-8")) - 1
        print(f"Chạy lại: mã {r2.returncode}, {n} dòng")
        if r2.returncode or n != len(items):
            failed.append("nhập lại")
    finally:
        ui.kill()
        ok(h.delete(f"{url}/api/tasks/{tid}", timeout=60))
    if fingerprint(h, url) != before:
        failed.append("task khác bị đổi")
    if human.exists():
        failed.append("human_review.csv xuất hiện")
    print("KẾT QUẢ:", "ĐẠT" if not failed else f"KHÔNG ĐẠT {failed}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
