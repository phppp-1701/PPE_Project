"""Bước 3 (phụ): vẽ sẵn hộp người cho task video trên CVAT, nối tiếp phần người gán đã vẽ.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05c_cvat_prefill_people.py video2 --task 2741542              # chỉ chạy trên máy, ghi bản xem trước
    python scripts/05c_cvat_prefill_people.py video2 --task 2741542 --upload     # ghi lên CVAT

Đọc nhãn hiện có của task, giữ nguyên mọi mốc người gán đã vẽ, rồi từ khung vẽ cuối cùng dò người bằng yolo11s.pt
gốc (tham số: configs/prelabel.yaml, mục video_people) và nối tiếp vào đúng các track đó. Người mới thành track mới.
Mốc máy thêm mang thuộc tính của mốc trước (như CVAT tự làm khi người gán đi tiếp); track mới để chua_xac_dinh.
Không dùng r2, ByteTrack hay dự đoán PPE. Chỉ dùng cho video chỉnh tham số, không dùng cho video đánh giá cuối.

Ghi vào outputs/results/video/<video>/prefill/: preview.mp4, review.csv (khung cần xem kỹ), tracks.json.
Trước khi ghi: sao lưu nhãn vào data/videos/<video>_cvat_backup_<giờ>.json; nhãn trên CVAT đổi so với lúc đọc thì dừng.
Token đọc từ CVAT_ACCESS_TOKEN hoặc ~/.cvat_token; không in ra, không ghi vào project.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")

import cv2
import lap
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
HOST = "https://app.cvat.ai"
SHAPE_KEYS = ("type", "frame", "occluded", "outside", "z_order", "rotation", "points", "attributes")


def read_token():
    token = os.environ.get("CVAT_ACCESS_TOKEN")
    token_file = Path.home() / ".cvat_token"
    if not token and token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        sys.exit("Chưa có token: đặt biến môi trường CVAT_ACCESS_TOKEN hoặc tạo file ~/.cvat_token.")
    return token


def iou(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    inter = w * h
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def area(b):
    return max(b[2] - b[0], 0) * max(b[3] - b[1], 0)


class Person:
    """Một người đang theo. `boxes`: {khung: hộp}; `held`: các khung giữ nguyên hộp vì không thấy người."""

    def __init__(self, name, frame, box, seed=None):
        self.name, self.seed = name, seed
        self.boxes, self.held = {frame: list(box)}, set()
        self.last, self.miss, self.end, self.hits = list(box), 0, None, 1
        self.joins = []                          # các khung nối tự động với đoạn sau


def detect_all(path, cfg, first):
    """{khung: [hộp người]} từ khung `first` tới hết video, và tổng số khung."""
    from ultralytics import YOLO

    model = YOLO(str(ROOT / cfg["weights"]))
    cap = cv2.VideoCapture(str(path))
    out, f = {}, 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        if f >= first:
            r = model.predict(im, imgsz=cfg["imgsz"], conf=cfg["conf"], iou=cfg["nms_iou"], device=cfg["device"],
                              classes=[cfg["person_cls"]], verbose=False)[0]
            out[f] = r.boxes.xyxy.cpu().numpy().tolist()
        f += 1
    cap.release()
    return out, f


def propagate(seeds, dets, start, n_frames, cfg):
    """Nối hộp qua các khung bằng ghép IoU. `seeds`: [(track_id, hộp ở khung start)]."""
    people = [Person(f"cvat{tid}", start, box, seed=tid) for tid, box in seeds]
    tentative, new_id = [], 0
    for f in range(start + 1, n_frames):
        boxes = dets.get(f, [])
        active = [p for p in people if p.end is None] + tentative
        used = set()
        if active and boxes:
            cost = np.array([[1 - iou(p.last, b) for b in boxes] for p in active])
            _, match, _ = lap.lapjv(cost, extend_cost=True, cost_limit=1 - cfg["match_iou"])
            for i, j in enumerate(match):
                if j >= 0:
                    p = active[i]
                    p.last, p.miss, p.hits = list(boxes[j]), 0, p.hits + 1
                    p.boxes[f] = list(boxes[j])
                    used.add(int(j))
        for p in active:
            if f in p.boxes:
                continue
            p.miss += 1
            if p in tentative:
                continue
            if p.miss > cfg["max_hold"]:
                p.end = f - p.miss + 1          # Outside từ khung đầu tiên mất dấu
                for k in [k for k in p.boxes if k >= p.end]:
                    del p.boxes[k]
                p.held = {k for k in p.held if k < p.end}
            else:
                p.boxes[f] = list(p.last)
                p.held.add(f)
        kept = []
        for p in tentative:
            if p.miss > 0:
                continue                         # người mới phải thấy liên tiếp
            if p.hits >= cfg["min_new_frames"]:
                new_id += 1
                p.name = f"new{new_id}"
                people.append(p)
            else:
                kept.append(p)
        tentative = kept + [Person("?", f, boxes[j]) for j in range(len(boxes)) if j not in used]
    return people


def center(b):
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def stitch(people, cfg):
    """Nối đoạn đã mất dấu với đoạn mới bắt đầu gần đó về thời gian và vị trí, ưu tiên cặp gần nhất."""
    while True:
        best = None
        for a in people:
            if a.end is None:
                continue
            fa = max(a.boxes)
            for b in people:
                if b is a or b.seed is not None:
                    continue
                fb = min(b.boxes)
                gap = fb - fa
                if not -cfg["stitch_max_overlap"] <= gap <= cfg["stitch_max_gap"]:
                    continue
                (ax, ay), (bx, by) = center(a.boxes[fa]), center(b.boxes[fb])
                h = max(a.boxes[fa][3] - a.boxes[fa][1], b.boxes[fb][3] - b.boxes[fb][1])
                d = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 / h
                if d <= cfg["stitch_max_dist"] and (best is None or d < best[0]):
                    best = (d, a, b, fb)
        if best is None:
            return people
        _, a, b, fb = best
        a.boxes = {k: v for k, v in a.boxes.items() if k < fb}
        a.held = {k for k in a.held if k < fb} | b.held
        a.boxes.update(b.boxes)
        a.end, a.joins = b.end, a.joins + [fb] + b.joins
        people = [p for p in people if p is not b]


def review_rows(people, cfg):
    rows = []
    for p in people:
        fs = sorted(p.boxes)
        for k in p.joins:
            rows.append((k, p.name, "máy tự nối hai đoạn: kiểm tra đúng là cùng một người"))
        if p.seed is None:
            rows.append((fs[0], p.name, "người mới, cần gán PPE"))
        if p.end is not None:
            rows.append((p.end, p.name, "mất dấu: kiểm tra người đã khuất thật chưa, có quay lại không"))
        for k in sorted(p.held):
            if k - 1 not in p.held:
                rows.append((k, p.name, "máy không thấy người, hộp giữ nguyên"))
        for a, b in zip(fs, fs[1:]):
            ra, rb = area(p.boxes[a]), area(p.boxes[b])
            if ra and rb and max(ra, rb) / min(ra, rb) >= cfg["jump_ratio"]:
                rows.append((b, p.name, "hộp đổi cỡ đột ngột: có thể ôm 2 người hoặc tráo ID"))
    for i, p in enumerate(people):
        for q in people[i + 1:]:
            near = False
            for f in sorted(set(p.boxes) & set(q.boxes)):
                hit = iou(p.boxes[f], q.boxes[f]) >= cfg["overlap_iou"]
                if hit and not near:
                    rows.append((f, f"{p.name}+{q.name}", "hai người chồng nhau: kiểm tra có tráo ID sau đó không"))
                near = hit
    return sorted(rows)


def write_preview(path, people, out_path):
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vw = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    colors = [(0, 255, 0), (0, 200, 255), (255, 100, 0), (255, 0, 255), (0, 0, 255), (255, 255, 0), (120, 255, 120),
              (200, 120, 255), (0, 120, 255), (255, 255, 255)]
    f = 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        for i, p in enumerate(people):
            b = p.boxes.get(f)
            if b is None:
                continue
            c = colors[i % len(colors)]
            x1, y1, x2, y2 = map(int, b)
            cv2.rectangle(im, (x1, y1), (x2, y2), c, 1 if f in p.held else 2)
            cv2.putText(im, f"{i + 1}{'h' if f in p.held else ''}", (x1, max(y1 - 4, 14)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, c, 2)
        cv2.putText(im, f"frame {f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        vw.write(im)
        f += 1
    cap.release()
    vw.release()


def rect_shape(frame, box, attrs, outside=False):
    return {"type": "rectangle", "frame": frame, "occluded": False, "outside": outside, "z_order": 0, "rotation": 0.0,
            "points": [float(v) for v in box], "attributes": attrs}


def merged_tracks(current, people, start, n_frames, step, default_attrs, label_id):
    """Bản nhãn mới: giữ nguyên mọi mốc cũ, thêm mốc máy sau khung `start`."""
    by_seed = {p.seed: p for p in people if p.seed is not None}
    tracks = []
    for tr in current["tracks"]:
        shapes = [{k: s[k] for k in SHAPE_KEYS} for s in tr["shapes"]]
        attrs = shapes[-1]["attributes"]
        if shapes[-1]["frame"] < start:         # chốt hộp ở khung start để phần người gán không bị nội suy lại
            shapes.append(rect_shape(start, shapes[-1]["points"], attrs))
        p = by_seed[tr["id"]]
        fs = sorted(p.boxes)
        marks = [f for f in fs if f > start and (f - start) % step == 0]
        if fs[-1] > start and fs[-1] not in marks:
            marks.append(fs[-1])
        shapes += [rect_shape(f, p.boxes[f], attrs) for f in marks]
        if fs[-1] + 1 < n_frames:
            shapes.append(rect_shape(fs[-1] + 1, p.boxes[fs[-1]], attrs, outside=True))
        tracks.append({"label_id": tr["label_id"], "frame": tr["frame"], "group": tr.get("group", 0),
                       "source": tr.get("source", "manual"), "attributes": tr.get("attributes", []), "shapes": shapes})
    for p in people:
        if p.seed is not None:
            continue
        fs = sorted(p.boxes)
        marks = [f for f in fs if (f - fs[0]) % step == 0]
        if fs[-1] not in marks:
            marks.append(fs[-1])
        shapes = [rect_shape(f, p.boxes[f], default_attrs) for f in marks]
        if fs[-1] + 1 < n_frames:
            shapes.append(rect_shape(fs[-1] + 1, p.boxes[fs[-1]], default_attrs, outside=True))
        tracks.append({"label_id": label_id, "frame": fs[0], "group": 0, "source": "semi-auto", "attributes": [],
                       "shapes": shapes})
    return tracks


def to_request(models, tracks):
    def attr(a):
        return models.AttributeValRequest(spec_id=a["spec_id"], value=a["value"])

    return models.LabeledDataRequest(
        version=0, tags=[], shapes=[],
        tracks=[models.LabeledTrackRequest(
            frame=t["frame"], label_id=t["label_id"], group=t["group"], source=t["source"],
            attributes=[attr(a) for a in t["attributes"]],
            shapes=[models.TrackedShapeRequest(
                type=models.ShapeType(s["type"]), frame=s["frame"], occluded=s["occluded"], outside=s["outside"],
                z_order=s["z_order"], rotation=s["rotation"], points=s["points"],
                attributes=[attr(a) for a in s["attributes"]]) for s in t["shapes"]],
        ) for t in tracks],
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video", help="video_id, vd. video2")
    p.add_argument("--task", type=int, required=True, help="id task trên CVAT")
    p.add_argument("--org", default="", help="short name Organization; \"\" = không gian cá nhân")
    p.add_argument("--upload", action="store_true", help="ghi lên CVAT; không có cờ này thì chỉ tạo bản xem trước")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    cfg = yaml.safe_load((ROOT / "configs" / "prelabel.yaml").read_text(encoding="utf-8"))["video_people"]
    path = ROOT / "data" / "videos" / f"{args.video}.mp4"
    out_dir = ROOT / "outputs" / "results" / "video" / args.video / "prefill"
    out_dir.mkdir(parents=True, exist_ok=True)

    from cvat_sdk import make_client, models

    with make_client(HOST, access_token=read_token()) as client:
        client.organization_slug = args.org
        task = client.tasks.retrieve(args.task)
        current = task.get_annotations().to_dict()
        labels = task.get_labels()
        tracks = current["tracks"]
        if not tracks:
            sys.exit("Task chưa có track nào: cần vẽ người ở khung đầu tiên trước.")
        if any(t["shapes"][-1]["outside"] for t in tracks):
            sys.exit("Có track đã bật Outside ở mốc cuối: script chưa xử lý trường hợp này, xem lại trước khi nối tiếp.")
        start = max(s["frame"] for t in tracks for s in t["shapes"])
        seeds = [(t["id"], t["shapes"][-1]["points"]) for t in tracks]
        print(f"Task {args.task}: {len(tracks)} track, mốc người gán tới khung {start}", flush=True)

        dets, n_frames = detect_all(path, cfg, start + 1)
        people = stitch(propagate(seeds, dets, start, n_frames, cfg), cfg)
        rows = review_rows(people, cfg)
        print(f"{n_frames} khung; sau nối: {sum(x.seed is not None for x in people)} track cũ, "
              f"{sum(x.seed is None for x in people)} track mới; {len(rows)} chỗ cần xem", flush=True)
        for x in people:
            fs = sorted(x.boxes)
            print(f"  {x.name}: khung {fs[0]}-{fs[-1]}, giữ hộp {len(x.held)} khung, nối ở {x.joins}")
        write_preview(path, people, out_dir / "preview.mp4")
        with open(out_dir / "review.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["frame", "track", "note"])
            w.writerows(rows)
        attrs = [{"spec_id": a.id, "value": a.default_value} for a in labels[0].attributes]
        merged = merged_tracks(current, people, start, n_frames, cfg["keyframe_step"], attrs, labels[0].id)
        (out_dir / "tracks.json").write_text(json.dumps(merged, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"Bản xem trước: {out_dir}", flush=True)
        if not args.upload:
            return

        now = task.get_annotations().to_dict()
        if json.dumps(now["tracks"], default=str, sort_keys=True) != json.dumps(tracks, default=str, sort_keys=True):
            sys.exit("Nhãn trên CVAT vừa thay đổi trong lúc chạy, dừng lại, không ghi đè.")
        backup = ROOT / "data" / "videos" / f"{args.video}_cvat_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
        backup.write_text(json.dumps(now, ensure_ascii=False, default=str, indent=1), encoding="utf-8")
        task.set_annotations(to_request(models, merged))
        after = task.get_annotations().to_dict()
        print(f"Đã ghi: {len(after['tracks'])} track, {sum(len(t['shapes']) for t in after['tracks'])} mốc "
              f"(trước đó {sum(len(t['shapes']) for t in tracks)} mốc); sao lưu {backup.name}")


if __name__ == "__main__":
    main()
