"""Nhãn máy cho tập event_eval (người dùng chọn 28/11/2026 thay cho gán tay): hộp người + ảnh tờ cho Claude gán hai lượt.

Không dùng mô hình của đề tài: hộp người từ yolo11s.pt gốc COCO (lớp person) + ByteTrack của Ultralytics (`model.track`,
chỉ cho công cụ gán nhãn này). Không chạy chuỗi xử lý của đề tài trên các video này cho tới khi nhãn được niêm phong.

Lệnh (từ thư mục gốc, .venv):
    python data/videos/event_eval/tools/machine_label.py tracks e1 e3 ...      # -> labels/work/<v>_tracks.json
    python data/videos/event_eval/tools/machine_label.py sheets --pass A e1 ...  # cả khung mỗi 0,5 s, vẽ T<id>
    python data/videos/event_eval/tools/machine_label.py sheets --pass B e1 ...  # ảnh cắt từng track mỗi 1/3 s, lệch 1/6 s
Ảnh tờ ghi vào thư mục --out (mặc định scratchpad do người chạy chỉ định).
"""

import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
ROOT = Path(__file__).resolve().parents[4]
EV = ROOT / "data" / "videos" / os.environ.get("EV_SET", "event_eval")   # EV_SET=event_eval_2 cho tập thứ hai
WORK = EV / "labels" / "work"


def cmd_tracks(videos):
    from ultralytics import YOLO
    WORK.mkdir(parents=True, exist_ok=True)
    for v in videos:
        model = YOLO(str(ROOT / "yolo11s.pt"))
        cap = cv2.VideoCapture(str(EV / f"{v}.mp4"))
        fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        tr, i = {}, 0
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            r = model.track(fr, persist=True, classes=[0], conf=0.3, tracker="bytetrack.yaml", verbose=False)[0]
            if r.boxes.id is not None:
                for tid, b in zip(r.boxes.id.int().tolist(), r.boxes.xyxy.tolist()):
                    tr.setdefault(str(tid), {})[str(i)] = [round(x, 1) for x in b]
            i += 1
        cap.release()
        keep = {t: fb for t, fb in tr.items()        # bỏ track ngắn hơn 1 s hoặc thấp hơn 10% khung
                if len(fb) >= fps and max(b[3] - b[1] for b in fb.values()) >= 0.1 * h}
        (WORK / f"{v}_tracks.json").write_text(json.dumps(dict(video=v, fps=fps, frames=i, width=w, height=h,
                                                               tracks=keep)), encoding="utf-8")
        print(v, i, "khung,", len(tr), "track,", len(keep), "giữ:", {t: (min(map(int, fb)), max(map(int, fb))) for t, fb in keep.items()})


def load(v):
    return json.loads((WORK / f"{v}_tracks.json").read_text(encoding="utf-8"))


def grid(ims, cols, cell_w):
    ims = [cv2.resize(im, (cell_w, int(cell_w * im.shape[0] / im.shape[1]))) for im in ims]
    hmax = max(im.shape[0] for im in ims)
    ims = [cv2.copyMakeBorder(im, 0, hmax - im.shape[0], 0, 0, cv2.BORDER_CONSTANT) for im in ims]
    while len(ims) % cols:
        ims.append(np.zeros_like(ims[0]))
    return np.vstack([np.hstack(ims[k:k + cols]) for k in range(0, len(ims), cols)])


def cmd_sheets(p, videos, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for v in videos:
        d = load(v)
        fps, n = d["fps"], d["frames"]
        cap = cv2.VideoCapture(str(EV / f"{v}.mp4"))
        if p == "A":
            idx = [int(round(k * 0.5 * fps)) for k in range(int(n / (0.5 * fps)) + 1) if int(round(k * 0.5 * fps)) < n]
        else:
            idx = [int(round((k / 3 + 1 / 6) * fps)) for k in range(int(n / (fps / 3)) + 1) if int(round((k / 3 + 1 / 6) * fps)) < n]
        frames = {}
        for f in idx:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, im = cap.read()
            if ok:
                frames[f] = im
        cap.release()
        if p == "A":
            cells = []
            for f, im in frames.items():
                im = im.copy()
                lw = max(2, im.shape[1] // 400)
                for t, fb in d["tracks"].items():
                    b = fb.get(str(f))
                    if b:
                        x1, y1, x2, y2 = map(int, b)
                        cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 255), lw)
                        cv2.putText(im, "T" + t, (x1 + 4, y1 + 12 * lw), 0, 0.5 * lw, (0, 255, 255), lw)
                cv2.putText(im, f"{v} t={f / fps:.1f}s", (10, 20 * lw), 0, 0.6 * lw, (0, 0, 255), lw)
                cells.append(im)
            for k in range(0, len(cells), 6):
                cv2.imwrite(str(out / f"{v}_A_{k // 6:02d}.jpg"), grid(cells[k:k + 6], 3, 640))
        else:
            for t, fb in d["tracks"].items():
                cells = []
                for f, im in frames.items():
                    b = fb.get(str(f))
                    if not b:
                        continue
                    x1, y1, x2, y2 = b
                    mx, my = 0.15 * (x2 - x1), 0.05 * (y2 - y1)
                    c = im[max(0, int(y1 - my)):int(y2 + my), max(0, int(x1 - mx)):int(x2 + mx)].copy()
                    c = cv2.resize(c, (int(400 * c.shape[1] / c.shape[0]), 400))
                    cv2.putText(c, f"T{t} {f / fps:.2f}s", (4, 18), 0, 0.55, (0, 0, 255), 2)
                    cells.append(c)
                for k in range(0, len(cells), 12):
                    cv2.imwrite(str(out / f"{v}_B_T{t}_{k // 12:02d}.jpg"), grid(cells[k:k + 12], 6, 220))
        print(v, p, len(frames), "khung")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("tracks")
    a.add_argument("videos", nargs="+")
    b = sub.add_parser("sheets")
    b.add_argument("--pass", dest="p", choices=["A", "B"], required=True)
    b.add_argument("--out", required=True)
    b.add_argument("videos", nargs="+")
    x = ap.parse_args()
    cmd_tracks(x.videos) if x.cmd == "tracks" else cmd_sheets(x.p, x.videos, x.out)


if __name__ == "__main__":
    main()
