"""Thăm dò điểm yếu tầm gần: độ nhấp nháy của PPE, tracking, lý do một bộ phận không ra Có (người dùng giao 25/11/2026).

Chạy toàn bộ chuỗi xử lý (configs/pipeline.yaml, không đổi tham số) trên video `kiem_thu_gan`, không cần nhãn. Chỉ để
tìm điểm yếu, không dùng để chọn tham số hay ngưỡng (data/videos/README.md).

Mỗi khung, mỗi (người, PPE, bên) ghi trạng thái và lý do khi không phải Có, theo thứ tự ưu tiên:
    hop_bi_bac_bo        có hộp detector gán cho người nhưng bộ phân loại phủ quyết (kính thường, mũ C2, ủng M1)
    hop_chua_ket_luan    có hộp gán nhưng trạng thái không phải Có (mâu thuẫn C2, hộp người dưới ngưỡng...)
    hop_bi_loai_<lý do>  detector có hộp đạt ngưỡng ở gần bộ phận nhưng không gán được (outside / far / contested)
    diem_duoi_nguong     không có hộp đạt ngưỡng, nhưng cả khung có hộp cùng lớp điểm >= --low-conf ở gần bộ phận
    khong_quan_sat       không có hộp nào ở gần, bộ phận không đủ quan sát (cổ tay, mắt cá dưới ngưỡng pose, mép khung...)
    khong_co_hop         bộ phận đủ quan sát mà detector không thấy gì (kể cả ở --low-conf)
"Gần bộ phận": găng có cổ tay thì trong elip cổ tay nới 1,5 lần; còn lại tâm hộp trong vùng cơ thể (association.regions)
tính trên hộp người của detector ở khung này, nới 10% cỡ người. Điểm thấp chỉ dò trên cả khung (không gồm zoom).

Nhấp nháy: số lần đổi trạng thái mỗi phút của từng (người, PPE, bên); số lần "mất ngắn" = đoạn không phải Có dài dưới
--short-gap giây nằm giữa hai đoạn Có (người đứng yên mà hộp PPE tắt rồi bật lại).
Tracking: số ID, tuổi từng ID, tỉ lệ chiều cao hộp người của ByteTrack (lọc Kalman) so với hộp detector ghép với nó
(< 1: hộp dùng để gán PPE nhỏ hơn người thật), tỉ lệ hộp detector nằm trong hộp ByteTrack.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05h_close_range_probe.py data/videos/video18.mp4 data/videos/video19.mp4 ...
    python scripts/05h_close_range_probe.py --ids 18-27            # video18..video27
    python scripts/05h_close_range_probe.py --ids 21 --max-frames 100 --no-video
    python scripts/05h_close_range_probe.py --ids 3-6 --config X.yaml --out outputs/results/close_probe/f2   # cấu hình khác

Ghi outputs/results/close_probe/<video>/: annotated.mp4 (như 05_run_video), detail.csv (mỗi người, PPE, bên, khung),
summary.json; và outputs/results/close_probe/summary.json, summary.md (gộp các video đã chạy lần này).
"""

import argparse
import csv
import importlib.util
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")   # không để Ultralytics tự cài gói

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe import HAVE, MISSING, UNKNOWN  # noqa: E402
from ppe.association import SIDES, ellipse_value, region_box, valid_wrist  # noqa: E402

_spec = importlib.util.spec_from_file_location("run05", ROOT / "scripts" / "05_run_video.py")
RUN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RUN)
OUT = ROOT / "outputs" / "results" / "close_probe"
SHORT_STATE = {HAVE: "co", MISSING: "thieu", UNKNOWN: "cxd"}


def iou(a, b):
    i = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def det_box_of(track, persons):
    """Hộp người của detector ở khung này ghép với track (IoU lớn nhất); None khi không có."""
    best = max(persons, key=lambda p: iou(p.xyxy, track.xyxy), default=None)
    return best.xyxy if best is not None and iou(best.xyxy, track.xyxy) > 0.3 else None


def near(cfg, name, side, c, track, box):
    """Tâm c có ở gần bộ phận (name, side) của người không (xem docstring đầu file)."""
    p = cfg["ppe"][name]
    pose = cfg["pose"] if cfg.get("pose", {}).get("enabled") else None
    if pose and p["sides"]:
        q = valid_wrist(track, side, pose)
        if q is not None:
            return ellipse_value(c, track.xyxy, q, pose) <= 1.5
    r = region_box(box, cfg["association"]["regions"][p["region"]], side)
    mx, my = 0.1 * (box[2] - box[0]), 0.1 * (box[3] - box[1])
    return r[0] - mx <= c[0] <= r[2] + mx and r[1] - my <= c[1] <= r[3] + my


def reason(cfg, name, side, track, box, out, low, veto):
    """Lý do (người, PPE, bên) không phải Có ở khung này (thứ tự ưu tiên trong docstring)."""
    st, d = out["states"][track.track_id][name]["sides"][side]
    owned = out["assoc"].owned.get(track.track_id, {}).get((name, side))
    if owned:
        if d.get("c2") == "veto" or (name in veto and d.get("vote") == "neg"):
            return "hop_bi_bac_bo"
        return "hop_chua_ket_luan"
    cls = cfg["ppe"][name]["cls"]
    for n2, det, why, _ in out["assoc"].rejected:
        if n2 == name and near(cfg, name, side, det.center, track, box):
            return f"hop_bi_loai_{why}"
    for c2, xy, s in low:
        if c2 == cls and near(cfg, name, side, ((xy[0] + xy[2]) / 2, (xy[1] + xy[3]) / 2), track, box):
            return "diem_duoi_nguong"
    return "khong_co_hop" if d.get("observable") else "khong_quan_sat"


def runs(seq):
    """[(giá trị, độ dài)] các đoạn liên tiếp."""
    out = []
    for v in seq:
        if out and out[-1][0] == v:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return out


def probe(video, args):
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"Không mở được video {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    od = OUT / video.stem
    od.mkdir(parents=True, exist_ok=True)
    from ppe import load_config
    pipe, stage, missing = RUN.build("full", "probe", f"probe_{video.stem}", None,
                                     load_config(args.config) if args.config else None)
    cfg = pipe.cfg
    det = pipe.detector
    pc = cfg.get("part_cls") or {}
    veto = set(pc.get("veto") or []) if pc.get("enabled") else set()
    names = pipe.required
    writer = None if args.no_video else cv2.VideoWriter(str(od / "annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"),
                                                        fps, (w, h))
    f = open(od / "detail.csv", "w", newline="", encoding="utf-8")
    wr = csv.writer(f)
    wr.writerow(["frame", "t", "track_id", "ppe", "side", "state", "reason", "observable", "vote", "box_on"])
    series = defaultdict(list)          # (tid, ppe, side) -> [(frame, state, box_on)]
    reasons = defaultdict(Counter)      # ppe -> Counter(lý do) trên khung không phải Có
    first_seen, last_seen = {}, {}
    h_ratio, cover, untracked = [], [], 0
    i, start = 0, time.perf_counter()
    while True:
        ok, frame = cap.read()
        if not ok or (args.max_frames and i >= args.max_frames):
            break
        out = pipe.process(frame, i / fps)
        r = det.model.predict(frame, imgsz=det.imgsz, conf=args.low_conf, iou=det.nms_iou, device=det.device,
                              verbose=False)[0]
        low = [(c, xy, s) for c, xy, s in det._boxes(r) if c != det.person_cls]
        status = RUN.box_status(out, cfg)
        colored = Counter()             # (tid, ppe) -> số hộp màu (bằng chứng Có) vẽ ở khung này
        for d in out["ppe"]:
            kind, tid, _ = status[id(d)]
            if kind == "co":
                colored[(tid, det.names[d.cls])] += 1
        confident = [p for p in out["persons"] if p.conf >= det.conf["person"]]
        matched = 0
        for tr in out["tracks"]:
            first_seen.setdefault(tr.track_id, i)
            last_seen[tr.track_id] = i
            box = det_box_of(tr, out["persons"])
            if box is not None:
                matched += 1
                h_ratio.append((tr.xyxy[3] - tr.xyxy[1]) / max(box[3] - box[1], 1.0))
                ib = [max(tr.xyxy[0], box[0]), max(tr.xyxy[1], box[1]), min(tr.xyxy[2], box[2]), min(tr.xyxy[3], box[3])]
                cover.append(max(0, ib[2] - ib[0]) * max(0, ib[3] - ib[1]) / max((box[2] - box[0]) * (box[3] - box[1]), 1.0))
            box = box if box is not None else tr.xyxy
            for name in names:
                sides = SIDES if cfg["ppe"][name]["sides"] else (None,)
                for side in sides:
                    st, d = out["states"][tr.track_id][name]["sides"][side]
                    why = "" if st == HAVE else reason(cfg, name, side, tr, box, out, low, veto)
                    on = int((colored[(tr.track_id, name)] > 0 or bool(d.get("held"))) and st == HAVE)
                    if why:
                        reasons[name][why] += 1
                    series[(tr.track_id, name, side)].append((i, st, on))
                    wr.writerow([i, round(i / fps, 3), tr.track_id, name, side or "", SHORT_STATE[st], why,
                                 int(bool(d.get("observable"))), d.get("vote") or "", on])
        untracked += max(0, len(confident) - matched)
        if writer:
            writer.write(RUN.draw(frame, out, cfg, False))
        i += 1
        if i % 100 == 0:
            print(f"  {video.stem}: {i}/{n} khung, {i / (time.perf_counter() - start):.1f} FPS", flush=True)
    elapsed = time.perf_counter() - start
    pipe.close(i / fps)
    cap.release()
    f.close()
    if writer:
        writer.release()

    short = max(1, round(args.short_gap * fps))
    per_ppe = {}
    for name in names:
        keys = [k for k in series if k[1] == name]
        frames = sum(len(series[k]) for k in keys)
        if not frames:
            continue
        cnt = Counter(st for k in keys for _, st, _ in series[k])
        trans = drops = box_toggles = 0
        for k in keys:
            seq = series[k]
            # chỉ tính đổi trạng thái giữa hai khung liền nhau của cùng người (người mất khung thì không tính)
            for (f0, s0, b0), (f1, s1, b1) in zip(seq, seq[1:]):
                if f1 == f0 + 1:
                    trans += s0 != s1
                    box_toggles += b0 == 1 and b1 == 0
            rr = runs([s == HAVE for _, s, _ in seq])
            drops += sum(1 for j in range(1, len(rr) - 1) if not rr[j][0] and rr[j][1] < short)
        minutes = frames / fps / 60
        per_ppe[name] = dict(
            khung_bo_phan=frames, co=round(cnt[HAVE] / frames, 3), thieu=round(cnt[MISSING] / frames, 3),
            cxd=round(cnt[UNKNOWN] / frames, 3), doi_trang_thai_moi_phut=round(trans / minutes, 1),
            mat_ngan=drops, hop_mau_tat=box_toggles, hop_mau_tat_moi_phut=round(box_toggles / minutes, 1),
            ly_do=dict(reasons[name].most_common()))
    life = {tid: last_seen[tid] - first_seen[tid] + 1 for tid in first_seen}
    late = sum(1 for tid, f0 in first_seen.items() if f0 > fps)   # ID sinh sau giây đầu (người mới vào hoặc đổi ID)
    pct = (lambda a, q: round(float(np.percentile(a, q)), 3) if a else None)
    s = dict(video=video.name, frames=i, fps=round(fps, 2), resolution=[w, h], pipeline_fps=round(i / elapsed, 2),
             config=args.config or "configs/pipeline.yaml", weights=cfg["detector"]["weights"], zoom=cfg["detector"].get("zoom", {}).get("enabled"),
             low_conf=args.low_conf, short_gap_s=args.short_gap,
             tracking=dict(so_id=len(life), id_sinh_sau_giay_dau=late,
                           tuoi_id_khung=dict(sorted(life.items())),
                           nguoi_detector_khong_co_track=untracked,
                           ty_le_cao_track_tren_detector=dict(p10=pct(h_ratio, 10), p50=pct(h_ratio, 50), p90=pct(h_ratio, 90)),
                           ty_le_hop_detector_nam_trong_track=dict(p10=pct(cover, 10), p50=pct(cover, 50))),
             ppe=per_ppe,
             note="khong co nhan; chi de tim diem yeu, khong chon tham so")
    (od / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    return s


def write_md(all_s, path):
    names = ["helmet", "vest", "gloves", "goggles", "boots"]
    L = ["# Thăm dò tầm gần (05h)", "", "Không có nhãn: chỉ để tìm điểm yếu. Số do script đo trên cấu hình hiện tại.", "",
         "## Tracking", "", "| Video | Khung | FPS luồng | Số ID | ID sinh sau giây đầu | Cao track/detector p10 / p50 | Hộp detector trong track p10 |",
         "|---|---|---|---|---|---|---|"]
    for s in all_s:
        t = s["tracking"]
        L.append(f"| {s['video']} | {s['frames']} | {s['pipeline_fps']} | {t['so_id']} | {t['id_sinh_sau_giay_dau']} | "
                 f"{t['ty_le_cao_track_tren_detector']['p10']} / {t['ty_le_cao_track_tren_detector']['p50']} | "
                 f"{t['ty_le_hop_detector_nam_trong_track']['p10']} |")
    L += ["", "## Trạng thái và nhấp nháy theo PPE", "",
          "Ô: tỉ lệ Có / Thiếu / Chưa xác định; đổi trạng thái mỗi phút; số lần mất ngắn.", "",
          "| Video | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    for s in all_s:
        cells = []
        for nm in names:
            p = s["ppe"].get(nm)
            cells.append("-" if not p else f"{p['co']:.2f}/{p['thieu']:.2f}/{p['cxd']:.2f}; {p['doi_trang_thai_moi_phut']}/ph; "
                                           f"{p['mat_ngan']} ngắn")
        L.append(f"| {s['video']} | " + " | ".join(cells) + " |")
    L += ["", "## Lý do không ra Có (số khung bộ phận, gộp mọi video)", ""]
    tot = defaultdict(Counter)
    for s in all_s:
        for nm, p in s["ppe"].items():
            tot[nm].update(p["ly_do"])
    for nm in names:
        if tot[nm]:
            L.append(f"- **{nm}**: " + ", ".join(f"{k} {v}" for k, v in tot[nm].most_common()))
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="*")
    ap.add_argument("--ids", help="khoảng số video trong data/videos, vd 18-27")
    ap.add_argument("--max-frames", type=int)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--low-conf", type=float, default=0.02, help="ngưỡng dò điểm thấp (chỉ để phân loại lý do)")
    ap.add_argument("--config", help="file cấu hình khác (mặc định configs/pipeline.yaml)")
    ap.add_argument("--out", help="thư mục kết quả (mặc định outputs/results/close_probe)")
    ap.add_argument("--short-gap", type=float, default=1.0, help="đoạn mất Có ngắn hơn mức này (giây) là mất ngắn")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    global OUT
    if args.out:
        OUT = Path(args.out)
    vids = [Path(v) for v in args.videos]
    if args.ids:
        a, _, b = args.ids.partition("-")
        vids += [ROOT / "data" / "videos" / f"video{k}.mp4" for k in range(int(a), int(b or a) + 1)]
    if not vids:
        raise SystemExit("Chưa chọn video")
    all_s = []
    for v in vids:
        s = probe(v, args)
        all_s.append(s)
        print(json.dumps({k: s[k] for k in ("video", "frames", "pipeline_fps")}, ensure_ascii=False), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(all_s, ensure_ascii=False, indent=1), encoding="utf-8")
    write_md(all_s, OUT / "summary.md")
    print(f"Đã ghi {OUT}")


if __name__ == "__main__":
    main()
