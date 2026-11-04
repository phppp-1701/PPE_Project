"""Bước 3: chạy một video qua chuỗi xử lý (docs/spec.md mục 5.6). Video không bao giờ dùng để huấn luyện.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05_run_video.py data/videos/v01.mp4                  # chạy tới bước xa nhất đã đủ tham số
    python scripts/05_run_video.py data/videos/v01.mp4 --stage track    # chỉ phát hiện + theo dõi
    python scripts/05_run_video.py data/videos/v01.mp4 --max-frames 300 --draw-regions

Tham số trong configs/pipeline.yaml; bước nào còn tham số null thì không chạy được (script báo tên tham số).
Ghi vào outputs/results/video/<tên video>/:
    annotated.mp4    video đã vẽ: hộp người + ID + trạng thái từng PPE, hộp PPE, (tùy chọn) vùng cơ thể
    frames.csv       mỗi người mỗi khung: t, track_id, hộp, confident, trạng thái từng PPE, PPE thiếu
    events.jsonl     mỗi thay đổi của sự kiện (tạo, cập nhật, chờ quan sát, đóng)
    summary.json     bước đã chạy, số khung, FPS toàn luồng, thời gian từng bước (p50/p95), số sự kiện
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")   # không để Ultralytics tự cài gói

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe import HAVE, MISSING, MissingParameter, load_config  # noqa: E402
from ppe.association import SIDES, region_box  # noqa: E402
from ppe.pipeline import STAGES, Pipeline  # noqa: E402

# Màu (BGR). Người: khung dày, màu theo trạng thái; PPE: khung mảnh hơn, mỗi loại một màu, có nhãn chữ.
STATE_COLOR = {HAVE: (0, 200, 0), MISSING: (0, 0, 255)}      # Có: xanh lá, Thiếu: đỏ
UNKNOWN_COLOR = (230, 230, 230)                               # Chưa xác định: trắng
PERSON_COLOR = (255, 140, 0)                                  # người khi chưa có trạng thái (bước < comply): xanh dương
LOST_COLOR = (160, 160, 160)                                  # quỹ đạo mất tạm: xám, nét đứt
PPE_COLOR = {"helmet": (0, 165, 255), "vest": (0, 255, 255), "gloves": (255, 0, 255)}   # cam, vàng, tím
TAG = {"helmet": "Mu", "vest": "Ao", "gloves": "Gang"}
SHORT = {"helmet": "M", "vest": "A", "gloves": "G"}


def build(stage, source_id, session_id, on_event):
    """Tạo Pipeline; stage "auto" = bước xa nhất đủ tham số. Trả về (pipeline, bước, thông báo tham số thiếu)."""
    order = STAGES[::-1] if stage == "auto" else [stage]
    missing = None
    for s in order:
        try:
            return Pipeline(source_id, session_id, stage=s, on_event=on_event), s, missing
        except MissingParameter as e:
            missing = missing or str(e)
    raise SystemExit(f"Không chạy được bước '{stage}': {missing}")


def dashed_rect(img, b, color, thick, dash=10):
    x1, y1, x2, y2 = [int(v) for v in b]
    for xa in range(x1, x2, dash * 2):
        cv2.line(img, (xa, y1), (min(xa + dash, x2), y1), color, thick)
        cv2.line(img, (xa, y2), (min(xa + dash, x2), y2), color, thick)
    for ya in range(y1, y2, dash * 2):
        cv2.line(img, (x1, ya), (x1, min(ya + dash, y2)), color, thick)
        cv2.line(img, (x2, ya), (x2, min(ya + dash, y2)), color, thick)


def tag(img, text, x, y, bg, fg=(0, 0, 0), scale=0.5, above=True):
    """Nhãn chữ có nền đặc tại góc (x, y) của khung; trả về chiều rộng nhãn."""
    (w, h), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    y0 = y - h - base - 4 if above else y
    y0 = max(0, y0)
    cv2.rectangle(img, (x, y0), (x + w + 6, y0 + h + base + 4), bg, -1)
    cv2.putText(img, text, (x + 3, y0 + h + 2), cv2.FONT_HERSHEY_SIMPLEX, scale, fg, 1, cv2.LINE_AA)
    return w + 6


def draw(frame, out, cfg, draw_regions):
    img = frame
    h = img.shape[0]
    s = max(0.45, h / 1080 * 0.7)                       # cỡ chữ theo độ phân giải
    t_person = max(2, round(h / 360))                   # khung người dày hơn khung PPE
    t_ppe = max(1, t_person - 1)
    name_of = {p["cls"]: n for n, p in cfg["ppe"].items()}

    # Ai sở hữu PPE nào (để ghi "Gang>3" trên nhãn PPE).
    owner = {}
    if "assoc" in out:
        for tid, items in out["assoc"].owned.items():
            for dets in items.values():
                for d in dets:
                    owner[id(d)] = tid

    for tid, b in out.get("lost", []):                 # người mất tạm: ByteTrack vẫn giữ ID, khung này không có quan sát
        dashed_rect(img, b, LOST_COLOR, 1)
        tag(img, f"ID {tid} (mat)", int(b[0]), int(b[1]), LOST_COLOR, scale=s * 0.8)

    states = out.get("states", {})
    for t in out.get("tracks", []):
        st = states.get(t.track_id, {})
        overall = [v["state"] for v in st.values()]
        if not st:
            color = PERSON_COLOR
        elif MISSING in overall:
            color = STATE_COLOR[MISSING]
        elif all(x == HAVE for x in overall):
            color = STATE_COLOR[HAVE]
        else:
            color = UNKNOWN_COLOR
        if t.confident:
            cv2.rectangle(img, tuple(t.xyxy[:2].astype(int)), tuple(t.xyxy[2:].astype(int)), color, t_person)
        else:                                           # hộp người dưới ngưỡng conf: chỉ giữ ID, không xét trạng thái
            dashed_rect(img, t.xyxy, color, t_ppe)
        x, y = int(t.xyxy[0]), int(t.xyxy[1])
        x += tag(img, f"ID {t.track_id}", x, y, color, scale=s)
        for name, v in st.items():                       # ô trạng thái: M/A/G, nền theo trạng thái
            x += tag(img, SHORT.get(name, name[0].upper()), x, y, STATE_COLOR.get(v["state"], UNKNOWN_COLOR), scale=s)
        if draw_regions and "assoc" in out:
            for name, p in cfg["ppe"].items():
                reg = cfg["association"]["regions"][p["region"]]
                for side in (SIDES if p["sides"] else (None,)):
                    dashed_rect(img, region_box(t.xyxy, reg, side), PPE_COLOR.get(name, LOST_COLOR), 1, dash=4)

    for d in out["ppe"]:                                 # PPE vẽ sau cùng để không bị khung người đè
        name = name_of.get(d.cls)
        c = PPE_COLOR.get(name, LOST_COLOR)
        x1, y1, x2, y2 = d.xyxy.astype(int)
        tid = owner.get(id(d))
        cv2.rectangle(img, (x1, y1), (x2, y2), c, t_ppe if tid is not None or "assoc" not in out else 1)
        label = TAG.get(name, name) + (f">{tid}" if tid is not None else ("?" if "assoc" in out else ""))
        tag(img, label, x1, y2, c, scale=s * 0.75, above=False)
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--stage", default="auto", choices=["auto"] + STAGES)
    ap.add_argument("--source-id", default="video")
    ap.add_argument("--out", help="thư mục kết quả (mặc định outputs/results/video/<tên video>)")
    ap.add_argument("--max-frames", type=int)
    ap.add_argument("--no-video", action="store_true", help="không ghi annotated.mp4")
    ap.add_argument("--draw-regions", action="store_true", help="vẽ vùng cơ thể của từng người")
    args = ap.parse_args()

    video = Path(args.video)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"Không mở được video {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_dir = Path(args.out) if args.out else ROOT / "outputs" / "results" / "video" / video.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    session_id = f"{video.stem}_{datetime.now():%Y%m%d_%H%M%S}"

    ev_file = open(out_dir / "events.jsonl", "w", encoding="utf-8")

    def on_event(kind, ev):
        ev["system_time"] = datetime.now().isoformat(timespec="seconds")   # tách giờ hệ thống khỏi giờ trong video
        ev_file.write(json.dumps({"change": kind, **ev}, ensure_ascii=False) + "\n")
        ev_file.flush()

    pipe, stage, missing = build(args.stage, args.source_id, session_id, on_event)
    cfg = pipe.cfg
    print(f"Video {video.name}: {w}x{h}, {fps:.2f} FPS, {n_frames} khung. Chạy tới bước: {stage}")
    if missing:
        print(f"  (bước sau chưa chạy được: {missing})")

    writer = None if args.no_video else cv2.VideoWriter(str(out_dir / "annotated.mp4"),
                                                        cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    names = pipe.required
    f_csv = open(out_dir / "frames.csv", "w", newline="", encoding="utf-8")
    wr = csv.writer(f_csv)
    wr.writerow(["frame", "t", "track_id", "x1", "y1", "x2", "y2", "confident"] + names + ["missing_ppe"])
    timings, i, start = [], 0, time.perf_counter()
    while True:
        ok, frame = cap.read()
        if not ok or (args.max_frames and i >= args.max_frames):
            break
        t = i / fps                                   # thời gian trong video (giây)
        out = pipe.process(frame, t)
        timings.append(out["timing"])
        for tr in out.get("tracks", []):
            st = out.get("states", {}).get(tr.track_id, {})
            row = [st[n]["state"] if n in st else "" for n in names]
            wr.writerow([i, round(t, 3), tr.track_id, *np.round(tr.xyxy, 1), int(tr.confident), *row,
                         ";".join(n for n in names if st.get(n, {}).get("state") == MISSING)])
        if writer:
            writer.write(draw(frame, out, cfg, args.draw_regions))
        i += 1
        if i % 100 == 0:
            el = time.perf_counter() - start
            print(f"  {i}/{n_frames} khung, {i / el:.1f} FPS toàn luồng", flush=True)
    elapsed = time.perf_counter() - start
    pipe.close(i / fps)
    cap.release()
    if writer:
        writer.release()
    f_csv.close()
    ev_file.close()

    steps = sorted({k for t in timings for k in t})
    timing = {k: dict(p50=round(float(np.percentile([t[k] for t in timings if k in t], 50)), 2),
                      p95=round(float(np.percentile([t[k] for t in timings if k in t], 95)), 2)) for k in steps}
    n_events = 0
    if stage == "full":
        n_events = len(pipe.events.closed) + len(pipe.events.open)
    summary = dict(video=str(video), session_id=session_id, stage=stage, not_run_reason=missing, frames=i,
                   video_fps=fps, resolution=[w, h], elapsed_s=round(elapsed, 2),
                   pipeline_fps=round(i / elapsed, 2) if elapsed else None, step_ms=timing, events=n_events,
                   weights=cfg["detector"]["weights"], imgsz=cfg["detector"]["imgsz"],
                   note="FPS toàn luồng gồm đọc khung, xử lý và vẽ/ghi video (nếu bật)")
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("stage", "frames", "pipeline_fps", "step_ms", "events")},
                     ensure_ascii=False, indent=1))
    print(f"Đã ghi {out_dir}")


if __name__ == "__main__":
    main()
