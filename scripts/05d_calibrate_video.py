"""Bước 3c: chọn tham số trên video chỉnh tham số, so với nhãn CVAT (spec 5, 7.3-7.5). Không huấn luyện gì từ video.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05d_calibrate_video.py video2 --tracker    # thử các bộ tham số ByteTrack
    python scripts/05d_calibrate_video.py video2 --state      # thử ambiguity_margin, tau_in, tau_occ, area_min_px
    python scripts/05d_calibrate_video.py video2 --rerun      # bỏ kết quả detector đã lưu, chạy lại

Chỉ dùng video role = chinh_tham_so trong data/videos/video_sources.csv; video khác bị từ chối.
Nhãn: data/videos/<video>_cvat.zip (CVAT for video 1.1). Lưới tham số: configs/pipeline.yaml mục calibration.video.
Script chỉ ghi đề xuất vào outputs/results/pipeline_calib_video/<video>/; người chép giá trị đã duyệt vào
configs/pipeline.yaml.
"""

import argparse
import csv
import itertools
import json
import os
import pickle
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")   # không để Ultralytics tự cài gói

import cv2
import lap
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe import HAVE, MISSING, UNKNOWN, load_config  # noqa: E402
from ppe.association import SIDES, Associator  # noqa: E402
from ppe.compliance import Compliance  # noqa: E402
from ppe.detector import Detector  # noqa: E402
from ppe.pose import PoseEstimator  # noqa: E402
from ppe.tracker import PersonTracker  # noqa: E402

STATES = (HAVE, MISSING, UNKNOWN)


def iou(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    inter = w * h
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def merge_gloves(left, right):
    """Như compliance: một tay Thiếu -> Thiếu; cả hai tay Có -> Có; còn lại Chưa xác định."""
    if MISSING in (left, right):
        return MISSING
    return HAVE if left == HAVE and right == HAVE else UNKNOWN


def read_labels(path):
    """{khung: [{id, box, occluded, helmet, vest, gloves, glove_left, glove_right}]} từ CVAT for video 1.1."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("annotations.xml"))
    frames = defaultdict(list)
    for tr in root.iter("track"):
        for b in tr.iter("box"):
            if b.get("outside") == "1":
                continue
            a = {x.get("name"): x.text for x in b.iter("attribute")}
            frames[int(b.get("frame"))].append({
                "id": int(tr.get("id")),
                "box": [float(b.get(k)) for k in ("xtl", "ytl", "xbr", "ybr")],
                "occluded": b.get("occluded") == "1",
                "helmet": a["helmet"], "vest": a["vest"],
                "glove_left": a["glove_left"], "glove_right": a["glove_right"],
                "gloves": merge_gloves(a["glove_left"], a["glove_right"]),
            })
    return frames


def match_frame(gts, boxes, min_iou):
    """Ghép một-một theo IoU >= min_iou. Trả về [(chỉ số nhãn, chỉ số hộp)]."""
    if not gts or not boxes:
        return []
    cost = np.array([[1 - iou(g["box"], b) for b in boxes] for g in gts])
    _, x, _ = lap.lapjv(cost, extend_cost=True, cost_limit=1 - min_iou)
    return [(i, int(j)) for i, j in enumerate(x) if j >= 0]


def tracking_metrics(labels, tracks_by_frame, n_frames, min_iou):
    """MOTA, IDF1, IDSW (spec 7.3). tracks_by_frame: {khung: [(track_id, hộp)]}."""
    n_gt = fp = fn = idsw = 0
    last = {}
    pair = Counter()
    gt_n, tr_n = Counter(), Counter()
    for f in range(n_frames):
        gts, trs = labels.get(f, []), tracks_by_frame.get(f, [])
        m = match_frame(gts, [t[1] for t in trs], min_iou)
        n_gt += len(gts)
        fp += len(trs) - len(m)
        fn += len(gts) - len(m)
        for g in gts:
            gt_n[g["id"]] += 1
        for t in trs:
            tr_n[t[0]] += 1
        for i, j in m:
            gid, tid = gts[i]["id"], trs[j][0]
            pair[(gid, tid)] += 1
            if gid in last and last[gid] != tid:
                idsw += 1
            last[gid] = tid
    gids, tids = sorted(gt_n), sorted(tr_n)
    idtp = 0
    if gids and tids:
        cost = np.array([[-pair[(g, t)] for t in tids] for g in gids], dtype=float)
        _, x, _ = lap.lapjv(cost, extend_cost=True)
        idtp = sum(pair[(gids[i], tids[j])] for i, j in enumerate(x) if j >= 0)
    idfp, idfn = sum(tr_n.values()) - idtp, sum(gt_n.values()) - idtp
    return {"MOTA": 1 - (fn + fp + idsw) / max(n_gt, 1),
            "IDF1": 2 * idtp / max(2 * idtp + idfp + idfn, 1),
            "IDSW": idsw, "FP": fp, "FN": fn, "n_gt": n_gt, "ids": len(tids)}


def detections(video, cfg, out_dir, rerun):
    """Chạy detector một lần, lưu lại: [(persons, ppe)] theo khung và cỡ ảnh."""
    cache = out_dir / "detections.pkl"
    if cache.exists() and not rerun:
        return pickle.loads(cache.read_bytes())
    det = Detector(cfg, ROOT)
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames, shape = [], None
    while True:
        ok, im = cap.read()
        if not ok:
            break
        shape = im.shape
        frames.append(det(im))
        if len(frames) % 20 == 0:
            print(f"  detector: {len(frames)} khung", flush=True)
    cap.release()
    data = {"frames": frames, "shape": shape, "fps": fps}
    cache.write_bytes(pickle.dumps(data))
    return data


def run_tracker(cfg, data):
    """{khung: [Track]} với tham số tracker trong cfg."""
    tracker = PersonTracker(cfg)
    blank = np.zeros(data["shape"], dtype=np.uint8)
    return {f: tracker.update(persons, blank) for f, (persons, _) in enumerate(data["frames"])}


def tune_tracker(cfg, data, labels, out_dir):
    grid = cfg["calibration"]["video"]["tracker_grid"]
    keys = list(grid)
    n, min_iou = len(data["frames"]), cfg["calibration"]["video"]["match_iou"]
    rows = []
    for vals in itertools.product(*grid.values()):
        c = deepcopy(cfg)
        c["tracker"].update(dict(zip(keys, vals)))
        tr = run_tracker(c, data)
        m = tracking_metrics(labels, {f: [(t.track_id, t.xyxy) for t in v] for f, v in tr.items()}, n, min_iou)
        rows.append({**dict(zip(keys, vals)), **m})
    rows.sort(key=lambda r: (-r["IDF1"], r["IDSW"], -r["MOTA"]))
    with open(out_dir / "tracker_grid.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    base = tracking_metrics(labels, {f: [(t.track_id, t.xyxy) for t in v] for f, v in run_tracker(cfg, data).items()},
                            n, min_iou)
    print("Hiện tại:", {k: round(v, 3) if isinstance(v, float) else v for k, v in base.items()})
    for r in rows[:8]:
        print({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()})
    print(f"Thử {len(rows)} bộ, ghi {out_dir / 'tracker_grid.csv'}")


def add_pose(cfg, tracks, video):
    """Ghi cổ tay vào các Track nếu pose bật."""
    if not cfg.get("pose", {}).get("enabled"):
        return
    pose = PoseEstimator(cfg, ROOT)
    cap = cv2.VideoCapture(str(video))
    for f in sorted(tracks):
        ok, im = cap.read()
        if ok:
            pose(im, tracks[f])
    cap.release()


def observations(cfg, data, labels, margin, video):
    """Mỗi cặp (nhãn, track) ghép được ở mỗi khung: số đo vùng của từng PPE/bên, để thử ngưỡng không cần chạy lại."""
    c = deepcopy(cfg)
    c["association"]["ambiguity_margin"] = margin
    for k in ("tau_in", "tau_occ", "area_min_px"):
        c["compliance"][k] = {p: {"tau_in": 0.0, "tau_occ": 1.0, "area_min_px": 0.0}[k] for p in c["ppe"]}
    assoc, comp = Associator(c), Compliance(c)
    min_iou = c["calibration"]["video"]["match_iou"]
    tracks = run_tracker(c, data)
    add_pose(c, tracks, video)
    obs, missed = [], 0
    for f, (_, ppe) in enumerate(data["frames"]):
        gts, trs = labels.get(f, []), tracks[f]
        m = match_frame(gts, [t.xyxy for t in trs], min_iou)
        missed += len(gts) - len(m)
        a = assoc(trs, ppe)
        st = comp(trs, a, data["shape"])
        for i, j in m:
            tid = trs[j].track_id
            obs.append({"frame": f, "gt": gts[i], "track": tid, "confident": trs[j].confident,
                        "sides": {p: {s: d for s, (_, d) in st[tid][p]["sides"].items()} for p in c["ppe"]}})
    return obs, missed


def state_of(sides, confident, tau_in, tau_occ, area_min):
    """Như compliance.side_state và phần gộp bên, từ số đo đã lưu."""
    states = []
    for d in sides.values():
        ok = d["v"] >= tau_in and d["o"] <= tau_occ and d["area"] >= area_min and confident
        states.append(HAVE if ok and d["has"] else MISSING if ok and not d["contested"] else UNKNOWN)
    if MISSING in states:
        return MISSING
    return HAVE if all(s == HAVE for s in states) else UNKNOWN


def score(pairs):
    """pairs: [(nhãn, dự đoán)]. Ma trận 3x3, F1 từng trạng thái, macro-F1 trên trạng thái có trong nhãn, Coverage."""
    conf = Counter(pairs)
    f1 = {}
    for s in STATES:
        tp = conf[(s, s)]
        fp = sum(conf[(g, s)] for g in STATES if g != s)
        fn = sum(conf[(s, p)] for p in STATES if p != s)
        if tp + fn:
            f1[s] = 2 * tp / max(2 * tp + fp + fn, 1)
    n = len(pairs)
    cover = sum(1 for _, p in pairs if p != UNKNOWN) / max(n, 1)
    decided = [(g, p) for g, p in pairs if p != UNKNOWN]
    wrong = sum(1 for g, p in decided if g != p and g != UNKNOWN)
    return {"macro_f1": float(np.mean(list(f1.values()))) if f1 else 0.0, "coverage": cover,
            "F1_co": f1.get(HAVE), "F1_thieu": f1.get(MISSING), "F1_chua": f1.get(UNKNOWN),
            "sai_co_thieu": wrong, "n": n, "conf": {f"{g}>{p}": v for (g, p), v in sorted(conf.items())}}


def tune_state(cfg, data, labels, out_dir, video):
    v = cfg["calibration"]["video"]
    results = {}
    rows = []
    for margin in v["ambiguity_margin_grid"]:
        obs, missed = observations(cfg, data, labels, margin, video)
        for p in cfg["ppe"]:
            for ti, to, am in itertools.product(v["tau_in_grid"], v["tau_occ_grid"], v["area_min_grid"][p]):
                pairs = [(o["gt"][p], state_of(o["sides"][p], o["confident"], ti, to, am)) for o in obs]
                s = score(pairs)
                rows.append({"ppe": p, "margin": margin, "tau_in": ti, "tau_occ": to, "area_min": am,
                             "missed_people": missed, **{k: x for k, x in s.items() if k != "conf"},
                             "conf": json.dumps(s["conf"], ensure_ascii=False)})
    with open(out_dir / "state_grid.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    for p in cfg["ppe"]:
        r = sorted([x for x in rows if x["ppe"] == p], key=lambda x: (-x["macro_f1"], -x["coverage"]))
        print(f"--- {p}: nhãn {Counter(o['gt'][p] for o in obs)}")
        for x in r[:4]:
            print({k: (round(y, 3) if isinstance(y, float) else y) for k, y in x.items() if k != "ppe"})
    print(f"Thử {len(rows)} dòng, ghi {out_dir / 'state_grid.csv'}")
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video", help="video_id, vd. video2")
    p.add_argument("--tracker", action="store_true")
    p.add_argument("--state", action="store_true")
    p.add_argument("--rerun", action="store_true", help="chạy lại detector")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    with open(ROOT / "data" / "videos" / "video_sources.csv", encoding="utf-8") as f:
        role = {r["video_id"]: r["role"] for r in csv.DictReader(f)}.get(args.video)
    if role != "chinh_tham_so":
        sys.exit(f"{args.video} có role '{role}': chỉ được chọn tham số trên video chinh_tham_so.")

    cfg = load_config()
    labels = read_labels(ROOT / "data" / "videos" / f"{args.video}_cvat.zip")
    out_dir = ROOT / "outputs" / "results" / "pipeline_calib_video" / args.video
    out_dir.mkdir(parents=True, exist_ok=True)
    data = detections(ROOT / "data" / "videos" / f"{args.video}.mp4", cfg, out_dir, args.rerun)
    n_people = len({g["id"] for v in labels.values() for g in v})
    print(f"{args.video}: {len(data['frames'])} khung, {data['fps']} FPS, {n_people} người trong nhãn, "
          f"{sum(len(v) for v in labels.values())} hộp nhãn", flush=True)
    if args.tracker:
        tune_tracker(cfg, data, labels, out_dir)
    if args.state:
        tune_state(cfg, data, labels, out_dir, ROOT / "data" / "videos" / f"{args.video}.mp4")


if __name__ == "__main__":
    main()
