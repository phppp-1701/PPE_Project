"""Bước 3: chạy một video qua chuỗi xử lý (docs/spec.md mục 5.6). Video không bao giờ dùng để huấn luyện.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05_run_video.py data/videos/v01.mp4                  # chạy tới bước xa nhất đã đủ tham số
    python scripts/05_run_video.py data/videos/v01.mp4 --stage track    # chỉ phát hiện + theo dõi
    python scripts/05_run_video.py data/videos/v01.mp4 --max-frames 300 --draw-regions
    python scripts/05_run_video.py data/videos/v01.mp4 --config path/to/pipeline.yaml   # cấu hình khác (vd bản cũ)

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
from ppe.parts import part_boxes  # noqa: E402
from ppe.pipeline import STAGES, Pipeline  # noqa: E402

# Màu (BGR). Người: khung dày, màu theo trạng thái; PPE: khung mảnh hơn, mỗi loại một màu, có nhãn chữ.
STATE_COLOR = {HAVE: (0, 200, 0), MISSING: (0, 0, 255)}      # Có: xanh lá, Thiếu: đỏ
UNKNOWN_COLOR = (230, 230, 230)                               # Chưa xác định: trắng
PERSON_COLOR = (255, 140, 0)                                  # người khi chưa có trạng thái (bước < comply): xanh dương
LOST_COLOR = (160, 160, 160)                                  # quỹ đạo mất tạm: xám, nét đứt
PPE_COLOR = {
    "helmet": (0, 165, 255),    # cam
    "vest": (0, 255, 255),      # vàng
    "gloves": (255, 0, 255),    # tím
    "goggles": (255, 255, 0),   # xanh lơ
    "boots": (255, 180, 0),     # xanh biển sáng
}
TAG = {"helmet": "Mu", "vest": "Ao", "gloves": "Gang", "goggles": "Kinh", "boots": "Ung"}
SHORT = {"helmet": "M", "vest": "A", "gloves": "G", "goggles": "K", "boots": "U"}
VETO_TAG = {"goggles": "Kinh thuong", "helmet": "Mu (bac bo)"}   # nhãn hộp bị bộ phân loại phủ quyết
PL_TAG = " (PL)"   # vùng ảnh cắt bộ phân loại đã xét (không phải hộp detector), vẽ nét đứt


def build(stage, source_id, session_id, on_event, cfg=None):
    """Tạo Pipeline; stage "auto" = bước xa nhất đủ tham số. Trả về (pipeline, bước, thông báo tham số thiếu)."""
    order = STAGES[::-1] if stage == "auto" else [stage]
    missing = None
    for s in order:
        try:
            return Pipeline(source_id, session_id, stage=s, cfg=cfg, on_event=on_event), s, missing
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


GRAY_TAG = {   # lý do một hộp detector KHÔNG được dùng làm bằng chứng Có (vẽ xám)
    "bac_bo": " (bac bo)",            # bộ phân loại phủ quyết (kính thường; mũ khi nhìn thẳng, bước C2)
    "phan_van": " (?)",               # bước C2: detector thấy mũ, bộ phân loại phân vân -> Chưa xác định
    "chua_ket_luan": " (?)",          # gán cho người nhưng trạng thái món đó không phải Có
    "tranh_chap": " (tranh chap)",    # nằm giữa hai người, không gán
    "ngoai": " (ngoai)",              # ngoài vùng cơ thể / quá xa, không gán
    "khong_xet": " (khong xet)",      # PPE không nằm trong danh sách kiểm của nguồn này
}


def box_status(out, cfg):
    """Mỗi hộp PPE của detector -> (loại, track_id, nhãn). Quy tắc hiển thị nhất quán (người dùng yêu cầu 16/11/2026):
    hộp có màu PPE (loại "co") CHỈ KHI được gán cho một người VÀ món đó (bên đó) của người đó là Có; mọi hộp khác vẽ
    xám kèm lý do (GRAY_TAG). Chưa tới bước trạng thái (stage < comply): hộp gán được vẽ màu như trước."""
    name_of = {p["cls"]: n for n, p in cfg["ppe"].items()}
    pc = cfg.get("part_cls") or {}
    veto = set(pc.get("veto") or []) if pc.get("enabled") else set()
    states = out.get("states")
    owner, reason = {}, {}     # owner: id hộp -> [(track_id, ppe, bên)]; một hộp găng phủ hai tay gán cho cả hai bên
    if "assoc" in out:
        for tid, items in out["assoc"].owned.items():
            for (name, side), dets in items.items():
                for d in dets:
                    owner.setdefault(id(d), []).append((tid, name, side))
        for name, d, why, _ in out["assoc"].rejected:
            reason[id(d)] = "tranh_chap" if why == "contested" else "ngoai"
    res = {}
    for d in out["ppe"]:
        name = name_of.get(d.cls)
        tag_ = TAG.get(name, name)
        if "assoc" not in out:                                   # chỉ phát hiện / theo dõi: chưa có gán, chưa có trạng thái
            res[id(d)] = ("phat_hien", None, tag_)
            continue
        if id(d) not in owner:
            k = reason.get(id(d), "ngoai")
            res[id(d)] = (k, None, tag_ + GRAY_TAG[k])
            continue
        tid, nm, _ = owner[id(d)][0]
        if states is None:                                       # đã gán, chưa xét trạng thái
            res[id(d)] = ("co", tid, f"{tag_}>{tid}")
            continue
        sides = [(t, n, sd, states[t][n]["sides"][sd]) for t, n, sd in owner[id(d)] if n in states.get(t, {})]
        if not sides:
            res[id(d)] = ("khong_xet", tid, tag_ + GRAY_TAG["khong_xet"])
            continue
        have = [x for x in sides if x[3][0] == HAVE]
        if have:                                                 # hộp là bằng chứng cho ít nhất một bên đang Có
            res[id(d)] = ("co", have[0][0], f"{tag_}>{have[0][0]}")
            continue
        state, det = sides[0][3]
        if (nm in veto and det.get("vote") == "neg") or det.get("c2") == "veto":
            res[id(d)] = ("bac_bo", tid, VETO_TAG.get(nm, tag_ + GRAY_TAG["bac_bo"]))
        elif det.get("c2") == "conflict":
            res[id(d)] = ("phan_van", tid, tag_ + GRAY_TAG["phan_van"])
        else:
            res[id(d)] = ("chua_ket_luan", tid, f"{tag_}>{tid}" + GRAY_TAG["chua_ket_luan"])
    return res


def pl_regions(out, cfg, shape):
    """Bằng chứng của bộ phân loại (bước A): [(track_id, ppe, bên, hộp)] cho món là Có vì phiếu pos mà không có hộp
    detector gán. Vùng ảnh cắt đã xét (hình học part_cls.geometry như parts.py), không phải vị trí vật thể."""
    pc = cfg.get("part_cls") or {}
    if not (pc.get("enabled") and pc.get("geometry")):
        return []
    hh, ww = shape[:2]
    res = []
    for tr in out.get("tracks", []):
        kps = getattr(tr, "extra", {}).get("kps")
        if not kps:
            continue
        crops = part_boxes(kps, pc["geometry"], pc["kp_conf"])
        for name, v in out.get("states", {}).get(tr.track_id, {}).items():
            for side, (state, d) in v["sides"].items():
                if state != HAVE or d.get("vote") != "pos" or d.get("has"):
                    continue
                for n2, s2, (cx, cy, sz) in crops:
                    if n2 != name or (side is not None and s2 != side):
                        continue
                    b = (max(0, cx - sz / 2), max(0, cy - sz / 2), min(ww - 1, cx + sz / 2), min(hh - 1, cy + sz / 2))
                    res.append((tr.track_id, name, side, b))
    return res


def display_check(out, cfg, shape):
    """Kiểm nhất quán giữa hình vẽ và trạng thái (dùng cho kiểm tự động): trả về danh sách vi phạm
    ("hop_mau_khong_co", ...) hộp có màu PPE mà món đó của người không phải Có;
    ("co_khong_bang_chung", ...) món là Có mà không có hộp màu gán cho người đó và không có vùng (PL)."""
    st = box_status(out, cfg)
    bad = []
    colored = set()
    for d in out["ppe"]:
        k, tid, _ = st[id(d)]
        if k != "co":
            continue
        own = [(t, n, s_) for t, items in out["assoc"].owned.items() for (n, s_), ds in items.items() for x in ds if x is d]
        have = [(t, n, s_) for t, n, s_ in own if out["states"].get(t, {}).get(n, {}).get("sides", {}).get(s_, (None,))[0] == HAVE]
        colored.update(have)
        if not have:
            bad.append(("hop_mau_khong_co", tid, own[0][1] if own else None, own[0][2] if own else None))
    pl = {(t, n, s) for t, n, s, _ in pl_regions(out, cfg, shape)}
    for tid, per in out.get("states", {}).items():
        for nm, v in per.items():
            for side, (state, _) in v["sides"].items():
                if state == HAVE and (tid, nm, side) not in colored and (tid, nm, side) not in pl:
                    bad.append(("co_khong_bang_chung", tid, nm, side))
    return bad


def draw(frame, out, cfg, draw_regions):
    img = frame
    h = img.shape[0]
    s = max(0.45, h / 1080 * 0.7)                       # cỡ chữ theo độ phân giải
    t_person = max(2, round(h / 360))                   # khung người dày hơn khung PPE
    t_ppe = max(1, t_person - 1)
    name_of = {p["cls"]: n for n, p in cfg["ppe"].items()}
    status = box_status(out, cfg)

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
        kind, tid, label = status[id(d)]
        colored = kind in ("co", "phat_hien")
        c = PPE_COLOR.get(name, LOST_COLOR) if colored else LOST_COLOR
        x1, y1, x2, y2 = d.xyxy.astype(int)
        cv2.rectangle(img, (x1, y1), (x2, y2), c, t_ppe if colored or tid is not None else 1)
        tag(img, label, x1, y2, c, scale=s * 0.75, above=False)

    # Bằng chứng của bộ phân loại (bước A, 14/11/2026): nét đứt, nhãn "(PL)". Chỉ vẽ, không đổi dữ liệu kết quả.
    for _, name, _, b in pl_regions(out, cfg, img.shape):
        c = PPE_COLOR.get(name, LOST_COLOR)
        dashed_rect(img, b, c, t_ppe, dash=6)
        tag(img, TAG.get(name, name) + PL_TAG, int(b[0]), int(b[3]), c, scale=s * 0.75, above=False)
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
    ap.add_argument("--api-url", default="http://127.0.0.1:8000/api", help="địa chỉ Backend API để đẩy sự kiện trực tiếp")
    ap.add_argument("--config", help="file cấu hình (mặc định configs/pipeline.yaml)")
    args = ap.parse_args()
    cfg_in = load_config(args.config) if args.config else None

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
        if args.api_url:
            try:
                import urllib.request
                if kind == "created":
                    data = json.dumps(ev).encode("utf-8")
                    req = urllib.request.Request(f"{args.api_url}/events", data=data, headers={"Content-Type": "application/json"}, method="POST")
                    urllib.request.urlopen(req, timeout=0.5)
                else:
                    patch_data = json.dumps({
                        "last_seen_time": ev.get("last_seen_time"),
                        "missing_items": ev.get("missing_items"),
                        "event_state": ev.get("event_state"),
                        "end_time": ev.get("end_time"),
                        "close_reason": ev.get("close_reason"),
                        "last_change_time": ev.get("last_change_time"),
                        "change_type": kind
                    }).encode("utf-8")
                    req = urllib.request.Request(f"{args.api_url}/events/{ev['event_id']}", data=patch_data, headers={"Content-Type": "application/json"}, method="PATCH")
                    urllib.request.urlopen(req, timeout=0.5)
            except Exception:
                pass

    pipe, stage, missing = build(args.stage, args.source_id, session_id, on_event, cfg_in)
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
                   weights=cfg["detector"]["weights"], imgsz=cfg["detector"]["imgsz"], config=args.config or "configs/pipeline.yaml",
                   note="FPS toàn luồng gồm đọc khung, xử lý và vẽ/ghi video (nếu bật)")
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("stage", "frames", "pipeline_fps", "step_ms", "events")},
                     ensure_ascii=False, indent=1))
    print(f"Đã ghi {out_dir}")


if __name__ == "__main__":
    main()
