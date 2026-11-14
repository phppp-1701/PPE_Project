"""Vẽ sẵn track người (chỉ hộp người, PPE để chua_xac_dinh) cho một video, ghi file CVAT for video 1.1 để tải lên
CVAT cục bộ bằng giao diện (Actions -> Upload annotations), không cần token.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05f_cvat_prefill_xml.py video9 video10 ...

Dò người bằng yolo11s.pt gốc (COCO, không phải mô hình của đề tài; tham số configs/prelabel.yaml mục video_people),
nối qua các khung bằng chính hàm của 05c (ghép IoU, giữ hộp khi mất ít khung, nối đoạn). Không dùng detector PPE,
ByteTrack hay bất kỳ dự đoán trạng thái PPE nào của hệ thống: người gán tự đặt thuộc tính, không thấy kết quả hệ thống.
Người dùng duyệt 14/11/2026 dùng cho video `kiem_thu_gan` (trước đó vẽ sẵn chỉ dùng cho video chỉnh tham số).

Ghi outputs/results/video/<video>/prefill/annotations.xml, review.csv (khung cần xem kỹ), preview.mp4.
Thuộc tính lấy từ khối JSON nhãn trong docs/video_labeling.md.
"""

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

import cv2
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_05c():
    spec = importlib.util.spec_from_file_location("p05c", ROOT / "scripts" / "05c_cvat_prefill_people.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def labels():
    block = re.search(r"```json\n(.*?)```", (ROOT / "docs" / "video_labeling.md").read_text(encoding="utf-8"), re.S)
    return json.loads(block.group(1))


def box_xml(f, b, w, h, attrs, outside=0):
    x1, y1, x2, y2 = max(0, b[0]), max(0, b[1]), min(w, b[2]), min(h, b[3])
    a = "".join(f'<attribute name="{k}">{v}</attribute>' for k, v in attrs)
    return (f'    <box frame="{f}" keyframe="1" outside="{outside}" occluded="0" xtl="{x1:.2f}" ytl="{y1:.2f}" '
            f'xbr="{x2:.2f}" ybr="{y2:.2f}" z_order="0">{a}</box>\n')


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p05c = load_05c()
    cfg = yaml.safe_load((ROOT / "configs" / "prelabel.yaml").read_text(encoding="utf-8"))["video_people"]
    lab = labels()[0]
    attrs = [(a["name"], a["default_value"]) for a in lab["attributes"]]
    for video in sys.argv[1:]:
        path = ROOT / "data" / "videos" / f"{video}.mp4"
        cap = cv2.VideoCapture(str(path))
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        dets, n = p05c.detect_all(path, cfg, 0)
        people = p05c.stitch(p05c.propagate([], dets, -1, n, cfg), cfg)
        people = [q for q in people if len(q.boxes) >= cfg["min_track_frames"]]
        people.sort(key=lambda q: -len(q.boxes))
        kept = []
        for q in people:            # bỏ track trùng với track dài hơn đã giữ
            dup = any(sum(p05c.iou(q.boxes[f], k.boxes[f]) >= cfg["dup_iou"] for f in q.boxes if f in k.boxes)
                      >= cfg["dup_frac"] * len(q.boxes) for k in kept)
            if not dup:
                kept.append(q)
        people = kept
        out = ROOT / "outputs" / "results" / "video" / video / "prefill"
        out.mkdir(parents=True, exist_ok=True)
        xml = ['<?xml version="1.0" encoding="utf-8"?>\n<annotations>\n  <version>1.1</version>\n',
               f'  <meta><task><name>{video}</name><size>{n}</size><mode>interpolation</mode><start_frame>0</start_frame>'
               f'<stop_frame>{n - 1}</stop_frame><original_size><width>{w}</width><height>{h}</height></original_size>'
               f'<labels><label><name>{lab["name"]}</name></label></labels></task></meta>\n']
        for i, person in enumerate(people):
            fs = sorted(person.boxes)
            keys = sorted(set(fs[::cfg["keyframe_step"]]) | {fs[-1]})
            xml.append(f'  <track id="{i}" label={quoteattr(lab["name"])} source="auto">\n')
            xml += [box_xml(f, person.boxes[f], w, h, attrs) for f in keys]
            if fs[-1] + 1 < n:      # sau khung cuối: Outside, để CVAT không nội suy tiếp
                xml.append(box_xml(fs[-1] + 1, person.boxes[fs[-1]], w, h, attrs, outside=1))
            xml.append("  </track>\n")
        xml.append("</annotations>\n")
        (out / "annotations.xml").write_text("".join(xml), encoding="utf-8")
        rows = p05c.review_rows(people, cfg)
        with open(out / "review.csv", "w", newline="", encoding="utf-8-sig") as f:
            wr = csv.writer(f)
            wr.writerow(["frame", "track", "note"])
            wr.writerows(rows)
        p05c.write_preview(path, people, out / "preview.mp4")
        print(f"{video}: {n} khung, {len(people)} track, {len(rows)} chỗ cần xem -> {out.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
