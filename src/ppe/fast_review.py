"""Công cụ duyệt nhanh: phiên duyệt, đồng bộ CVAT. Chỉ tự động hóa thao tác, không có giá trị mặc định hay đề xuất nhãn.

Chỉ đọc phần gửi người duyệt của gói mù (annotations.xml, images.zip, labels.json). Không đọc thư mục ánh xạ riêng.
Mọi giá trị đến từ một thao tác của người cho đúng một hộp hoặc một ảnh; không có hàm đặt giá trị hàng loạt.
"""

import csv
import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

from ppe.ppe6_data import DECISIONS, NOT_A_PERSON, UNSET, parse_cvat

PERSON_VALUES = ("du_lon", "qua_nho", "khong_ro")
IMAGE_VALUES = ("image_checked", "reject_image")
IMAGE_STEP_TASKS = ("task_b", "task_d")   # hướng dẫn duyệt: mọi ảnh của hai task này phải có tag
LOG_FIELDS = ["reviewer", "time", "task", "target", "field", "before", "after"]
TEST_REVIEWER = "agent_test"


def load_pack(folder):
    """Đọc annotations.xml, labels.json của một task: ảnh theo đúng thứ tự trộn của gói, hộp trong từng ảnh."""
    folder = Path(folder)
    person = any(a["name"] == "person_ok" for lb in json.loads((folder / "labels.json").read_text(encoding="utf-8")) for a in lb.get("attributes", []))
    images = []
    for im in ET.fromstring((folder / "annotations.xml").read_text(encoding="utf-8")).iter("image"):
        boxes = []
        for b in im.findall("box"):
            attrs = {a.get("name"): (a.text or "") for a in b.findall("attribute")}
            boxes.append(dict(item_id=attrs["item_id"], target=b.get("label").replace("_review", ""), xtl=float(b.get("xtl")), ytl=float(b.get("ytl")), xbr=float(b.get("xbr")), ybr=float(b.get("ybr"))))
        images.append(dict(name=im.get("name"), width=int(im.get("width")), height=int(im.get("height")), boxes=boxes))
    return dict(person=person, images=images)


def check_reviewer(name, task):
    """Tên phải là người thật; tên kiểm thử chỉ dùng với task trial."""
    low = name.strip().lower()
    if low in NOT_A_PERSON:
        raise ValueError("Cần tên người duyệt thật.")
    if low.startswith(TEST_REVIEWER) and task != "trial":
        raise ValueError("Tên kiểm thử chỉ dùng cho task trial.")


class Session:
    """Trạng thái một phiên duyệt, lưu xuống đĩa sau mỗi thao tác."""

    def __init__(self, pack, task, reviewer, folder, image_step=False):
        check_reviewer(reviewer, task)
        self.pack, self.task, self.reviewer = pack, task, reviewer
        self.state_path = Path(folder) / f"fast_{task}_state.json"
        self.log_path = Path(folder) / f"fast_{task}_log.csv"
        self.need_image = task in IMAGE_STEP_TASKS or image_step
        self.items = {b["item_id"]: b for im in pack["images"] for b in im["boxes"]}
        self.names = [im["name"] for im in pack["images"]]
        fields = ["decision"] + (["person_ok"] if pack["person"] else [])
        self.fields = fields
        if self.state_path.exists():
            s = json.loads(self.state_path.read_text(encoding="utf-8"))
            if s["reviewer"] != reviewer:
                raise ValueError("Phiên này thuộc người duyệt khác.")
            if set(s["boxes"]) != set(self.items):
                raise ValueError("Trạng thái không khớp gói duyệt.")
        else:
            s = dict(reviewer=reviewer, task=task, cursor=0, boxes={k: {f: UNSET for f in fields} for k in self.items}, images={}, flags={}, skipped={}, synced_boxes={}, synced_images={}, finished_at=None)
        self.s = s

    def save(self):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.s, ensure_ascii=False, indent=0), encoding="utf-8")
        os.replace(tmp, self.state_path)

    def log(self, target, field, before, after):
        new = not self.log_path.exists()
        with self.log_path.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            if new:
                w.writerow(LOG_FIELDS)
            w.writerow([self.reviewer, datetime.now().isoformat(timespec="seconds"), self.task, target, field, before, after])

    def steps(self):
        out = []
        for i, im in enumerate(self.pack["images"]):
            out += [dict(type="box", image=im["name"], frame=i, item_id=b["item_id"]) for b in im["boxes"]]
            if self.need_image:
                out.append(dict(type="image", image=im["name"], frame=i))
        return out

    def set_box(self, item_id, field, value):
        if item_id not in self.items or field not in self.fields:
            raise ValueError("Hộp hoặc trường không hợp lệ.")
        allowed = DECISIONS if field == "decision" else PERSON_VALUES
        if value != UNSET and value not in allowed:
            raise ValueError("Giá trị không hợp lệ.")
        before = self.s["boxes"][item_id][field]
        if before != value:
            self.s["boxes"][item_id][field] = value
            self.s["finished_at"] = None
            self.log(item_id, field, before, value)
            self.save()

    def set_image(self, name, value):
        if name not in self.names or value not in (*IMAGE_VALUES, ""):
            raise ValueError("Ảnh hoặc giá trị không hợp lệ.")
        before = self.s["images"].get(name, "")
        if before != value:
            self.s["images"][name] = value
            self.s["finished_at"] = None
            self.log(name, "image", before, value)
            self.save()

    def _key_ok(self, key):
        kind, _, ident = key.partition(":")
        return (kind == "box" and ident in self.items) or (kind == "image" and ident in self.names)

    def set_mark(self, table, key, on):
        """table: flags (cần mở CVAT) hoặc skipped (xem sau). Một lần cho một hộp hoặc một ảnh."""
        if table not in ("flags", "skipped") or not self._key_ok(key) or not isinstance(on, bool):
            raise ValueError("Đánh dấu không hợp lệ.")
        before = bool(self.s[table].get(key))
        if before != on:
            if on:
                self.s[table][key] = True
            else:
                self.s[table].pop(key, None)
            self.s["finished_at"] = None
            self.log(key, table, before, on)
            self.save()

    def set_cursor(self, n):
        if not isinstance(n, int) or not 0 <= n < max(len(self.steps()), 1):
            raise ValueError("Vị trí không hợp lệ.")
        self.s["cursor"] = n
        self.save()

    def missing(self):
        out = [f"{k}: {f}" for k, v in self.s["boxes"].items() for f in self.fields if v[f] == UNSET]
        if self.need_image:
            out += [f"{n}: image" for n in self.names if not self.s["images"].get(n)]
        return out

    def open_flags(self):
        return sorted(self.s["flags"])

    def finish(self):
        """Không cho hoàn tất khi còn ô thiếu hoặc còn mục cần mở CVAT."""
        if self.missing() or self.open_flags():
            raise ValueError(f"Còn {len(self.missing())} ô thiếu, {len(self.open_flags())} mục cần mở CVAT.")
        self.s["finished_at"] = datetime.now().isoformat(timespec="seconds")
        self.save()

    def flag_links(self, cvat_url, task_id, job_id):
        frame = {n: i for i, n in enumerate(self.names)}
        image_of = {b["item_id"]: im["name"] for im in self.pack["images"] for b in im["boxes"]}
        rows = []
        for key in self.open_flags():
            kind, _, ident = key.partition(":")
            name = ident if kind == "image" else image_of[ident]
            rows.append(dict(key=key, image=name, url=f"{cvat_url}/tasks/{task_id}/jobs/{job_id}?frame={frame[name]}"))
        return rows

    def view(self, cvat_url, task_id, job_id):
        """Dữ liệu cho giao diện: chỉ mã hộp, tọa độ và thao tác của chính người duyệt."""
        steps = self.steps()
        cells = len(self.items) * len(self.fields) + (len(self.names) if self.need_image else 0)
        return dict(task=self.task, person=self.pack["person"], need_image=self.need_image, cursor=self.s["cursor"], steps=steps, boxes=self.s["boxes"], images=self.s["images"], flags=self.s["flags"], skipped=self.s["skipped"],
                    items=self.items, sizes={im["name"]: [im["width"], im["height"]] for im in self.pack["images"]}, cells=cells, missing=len(self.missing()), links=self.flag_links(cvat_url, task_id, job_id), finished_at=self.s["finished_at"])


class Conflict(Exception):
    """Giá trị trên CVAT khác cả công cụ lẫn lần đồng bộ trước: có người sửa trực tiếp trên CVAT."""

    def __init__(self, items):
        super().__init__(f"{len(items)} xung đột")
        self.items = items


def plan_boxes(current, wanted, synced):
    """So giá trị CVAT với công cụ. Chỉ ghi ô đã do người chọn hoặc đã đồng bộ trước đó. Trả về ({mã: {trường: giá trị}}, xung đột)."""
    updates, conflicts = {}, []
    for item, fields in wanted.items():
        for field, value in fields.items():
            now = current[item].get(field, UNSET)
            last = synced.get(item, {}).get(field, UNSET)
            if now == value:
                continue
            if now != last:
                conflicts.append(f"{item}: {field}")
            elif value != UNSET or last != UNSET:
                updates.setdefault(item, {})[field] = value
    return updates, conflicts


class Cvat:
    """Gọi API CVAT cục bộ. Token chỉ nằm trong header của phiên, không in và không ghi."""

    def __init__(self, url, token, task_id):
        self.url, self.task_id = url.rstrip("/"), task_id
        self.http = requests.Session()
        self.http.headers["Authorization"] = f"Bearer {token}"

    def _ok(self, r):
        if not r.ok:
            raise RuntimeError(f"CVAT trả {r.status_code} ở {r.request.path_url}: {r.text[:200]}")
        return r

    def _get(self, path, **params):
        return self._ok(self.http.get(f"{self.url}{path}", params=params, timeout=120))

    def _patch(self, action, body):
        base = dict(version=0, tags=[], shapes=[], tracks=[])
        self._ok(self.http.patch(f"{self.url}/api/tasks/{self.task_id}/annotations", params=dict(action=action), json=base | body, timeout=300))

    def read(self):
        labels, attrs = {}, {}
        for lb in self._get("/api/labels", task_id=self.task_id, page_size=50).json()["results"]:
            labels[lb["name"]] = lb["id"]
            for a in lb["attributes"]:
                attrs[a["id"]] = a["name"]
        ann = self._get(f"/api/tasks/{self.task_id}/annotations").json()
        frames = [f["name"] for f in self._get(f"/api/tasks/{self.task_id}/data/meta").json()["frames"]]
        by_item = {}
        for sh in ann["shapes"]:
            m = {attrs[a["spec_id"]]: a for a in sh["attributes"]}
            if "item_id" in m:
                by_item[m["item_id"]["value"]] = (sh, m)
        return labels, by_item, ann["tags"], frames

    def export(self, path):
        r = self._ok(self.http.post(f"{self.url}/api/tasks/{self.task_id}/dataset/export", params={"format": "CVAT for images 1.1", "save_images": "false"}, timeout=120))
        rq = r.json()["rq_id"]
        for _ in range(600):
            d = self._get(f"/api/requests/{rq}").json()
            if d["status"] == "finished":
                Path(path).write_bytes(self._ok(self.http.get(d["result_url"], timeout=300)).content)
                return
            if d["status"] == "failed":
                raise RuntimeError(str(d.get("message"))[:200])
            time.sleep(1)
        raise TimeoutError("Xuất CVAT quá lâu.")


def sync(session, cvat):
    """Ghi lựa chọn của người lên CVAT. Giữ nguyên tọa độ hiện có, chỉ đổi thuộc tính và tag. Trả về số ô, số tag đã ghi."""
    labels, by_item, tags, frames = cvat.read()
    lost = sorted(set(session.items) - set(by_item))
    if lost:
        raise Conflict([f"{k}: hộp bị xóa trên CVAT" for k in lost])
    current = {k: {f: m[f]["value"] for f in session.fields} for k, (_, m) in by_item.items() if k in session.items}
    updates, conflicts = plan_boxes(current, session.s["boxes"], session.s["synced_boxes"])
    names = {v: k for k, v in labels.items()}
    frame = {n: i for i, n in enumerate(frames)}
    have = {}
    for t in tags:
        have.setdefault((t["frame"], names[t["label_id"]]), t)
    add, drop = [], []
    for name in session.names:
        want, last = session.s["images"].get(name, ""), session.s["synced_images"].get(name, "")
        if name not in frame:
            conflicts.append(f"{name}: ảnh không có trên CVAT")
            continue
        if last and last != want and (frame[name], last) in have:
            drop.append(have[(frame[name], last)])
        if want and (frame[name], want) not in have:
            add.append(dict(frame=frame[name], label_id=labels[want], group=0, source="manual", attributes=[]))
    if conflicts:
        raise Conflict(conflicts)
    shapes = []
    for item, change in updates.items():
        sh, m = by_item[item]
        for f, v in change.items():
            m[f]["value"] = v
        shapes.append(sh)
    if shapes:
        cvat._patch("update", dict(shapes=shapes))
    if drop:
        cvat._patch("delete", dict(tags=drop))
    if add:
        cvat._patch("create", dict(tags=add))
    session.s["synced_boxes"] = json.loads(json.dumps(session.s["boxes"]))
    session.s["synced_images"] = dict(session.s["images"])
    session.save()
    return sum(len(v) for v in updates.values()), len(add) + len(drop)


def verify_cvat(session, cvat):
    """Sau đồng bộ: từng ô trên CVAT phải bằng công cụ. Trả về (lệch, số ô còn chua_chon trên CVAT)."""
    _, by_item, _, _ = cvat.read()
    diff, left = [], 0
    for k, v in session.s["boxes"].items():
        for f, val in v.items():
            now = by_item[k][1][f]["value"]
            left += now == UNSET
            if now != val:
                diff.append(f"{k}: {f}")
    return diff, left


def verify_export(session, xml_text):
    """Từng ô trong XML xuất phải bằng công cụ. Trả về danh sách lệch."""
    boxes, tags = parse_cvat(xml_text)
    got = {b["attrs"].get("item_id"): b["attrs"] for b in boxes if b["attrs"].get("item_id")}
    diff = [f"{k}: {f}" for k, v in session.s["boxes"].items() for f, val in v.items() if got.get(k, {}).get(f) != val]
    have = set(tags)
    diff += [f"{n}: tag" for n, want in session.s["images"].items() if want and (n, want) not in have]
    return diff
