"""RQ3 số phụ (người dùng chọn 28/11/2026): sự kiện chuẩn suy từ nhãn khung của holdout, chấm sự kiện hệ thống đã chạy.

Holdout đã xem kết quả (không còn mù) và nhãn là nhãn máy hai lượt chưa người kiểm định: số ở đây ghi "kiểm tra, không mù".
Sự kiện chuẩn (spec 7.4, PPE bắt buộc cả 5 món như cấu hình mặc định): theo từng track nhãn, bắt đầu ở khung đầu tiên có món
Thiếu; kết thúc khi mọi món là Có, hoặc track nhãn kết thúc / vắng quá 2 s. Ghép cảnh báo như 06e: hộp track hệ thống ở
khung `confirmed_at` với hộp nhãn cùng khung, IoU >= 0,5; trong khoảng sự kiện; ít nhất một PPE trùng. Mốc "theo khung"
như 06e. Đọc kết quả đã chạy của 06b (frames.csv, events.jsonl), không chạy lại hệ thống.

    python scripts/06f_holdout_events.py --run outputs/results/close_eval/final4/holdout_check/final4 --out outputs/results/close_eval/final4/holdout_events.json
"""

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("e06b", ROOT / "scripts" / "06b_evaluate_close_videos.py")
e06b = importlib.util.module_from_spec(_s)
_s.loader.exec_module(e06b)
_s = importlib.util.spec_from_file_location("e06e", ROOT / "scripts" / "06e_event_eval.py")
e06e = importlib.util.module_from_spec(_s)
_s.loader.exec_module(e06e)
PPE = e06b.PPE
VIDEOS = ["h1", "h2", "h3", "h4", "h5", "h7", "h8", "h9"]


def gt_events(labels, fps):
    per = defaultdict(dict)                          # track -> frame -> (box, states)
    for f, rows in labels.items():
        for lt, box, st in rows:
            per[lt][f] = (box, st)
    out = []
    for lt, fr in per.items():
        cur, last = None, None
        for f in sorted(fr):
            box, st = fr[f]
            if cur is not None and last is not None and (f - last) / fps > 2.0:
                cur["end"] = last / fps
                out.append(cur)
                cur = None
            miss = [p for p in PPE if st[p] == "thieu"]
            if cur is None and miss:
                cur = dict(track=lt, start=f / fps, missing=set(miss))
            elif cur is not None:
                if all(st[p] == "co" for p in PPE):
                    cur["end"] = f / fps
                    out.append(cur)
                    cur = None
                else:
                    cur["missing"] |= set(miss)
            last = f
        if cur is not None:
            cur["end"] = last / fps
            out.append(cur)
    return out, per


def score(alerts, gts, per):
    hit, res = set(), dict(tp=0, dup=0, false=0, outside=0, lat=[])
    for t, f, ppe, box in alerts:
        cands = {lt for lt, fr in per.items() if f in fr and e06e.iou(box, fr[f][0]) >= 0.5}
        if not cands:
            res["outside"] += 1
            continue
        ok = next((k for k, e in enumerate(gts) if e["track"] in cands and e["start"] - 1e-6 <= t <= e["end"] + 1e-6
                   and ppe & e["missing"]), None)
        if ok is None:
            res["false"] += 1
        elif ok in hit:
            res["dup"] += 1
        else:
            hit.add(ok)
            res["tp"] += 1
            res["lat"].append(t - gts[ok]["start"])
    res["fn"] = len(gts) - len(hit)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="thư mục cấu hình của 06b (chứa holdout/<video>/)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import cv2
    pv, rng = {}, np.random.default_rng(0)
    for v in VIDEOS:
        cap = cv2.VideoCapture(str(ROOT / "data" / "videos" / "holdout" / f"{v}.mp4"))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        labels = e06b.load_labels(ROOT / f"data/videos/holdout/labels/{v}_machine_cvat.zip")
        gts, per = gt_events(labels, fps)
        d = ROOT / a.run / "holdout" / v
        frames = e06e.load_frames(d / "frames.csv")
        evs = defaultdict(lambda: dict(items=set()))
        for line in (d / "events.jsonl").read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            x = evs[e["event_id"]]
            x.update(track=str(e["track_id"]), t=e["confirmed_at"])
            for h in e.get("history") or []:
                x["items"] |= set(h.get("missing_items") or [])
            x["items"] |= set(e.get("missing_items") or [])
        al_e = []
        for x in evs.values():
            f = int(round(x["t"] * fps))
            r = next((frames[g][x["track"]] for g in [f] + [f + k for k in (-1, 1, -2, 2, -3, 3)] if x["track"] in frames.get(g, {})), None)
            if r:
                al_e.append((x["t"], f, x["items"], [float(r[k]) for k in ("x1", "y1", "x2", "y2")]))
        al_f = [(f / fps, f, set(r["missing_ppe"].split(";")), [float(r[k]) for k in ("x1", "y1", "x2", "y2")])
                for f, rows in frames.items() for r in rows.values() if r["missing_ppe"]]
        pv[v] = dict(gt=len(gts), E=score(al_e, gts, per), frame=score(al_f, gts, per))
    summ = {}
    for k in ("E", "frame"):
        c = {q: sum(pv[v][k][q] for v in VIDEOS) for q in ("tp", "dup", "false", "outside", "fn")}
        lat = [x for v in VIDEOS for x in pv[v][k]["lat"]]
        p, r, f1 = e06e.prf(c)
        summ[k] = dict(**c, precision=round(p, 3), recall=round(r, 3), f1=round(f1, 3),
                       mean_latency_s=round(float(np.mean(lat)), 3) if lat else None)
    b = []
    for _ in range(2000):
        s = rng.choice(VIDEOS, len(VIDEOS))
        fe = e06e.prf({q: sum(pv[v]["E"][q] for v in s) for q in ("tp", "dup", "false", "fn")})[2]
        ff = e06e.prf({q: sum(pv[v]["frame"][q] for v in s) for q in ("tp", "dup", "false", "fn")})[2]
        b.append((fe, fe - ff))
    b = np.array(b)
    summ["ci95"] = dict(E_f1=[round(float(x), 3) for x in np.percentile(b[:, 0], [2.5, 97.5])],
                        diff_E_minus_frame=[round(float(x), 3) for x in np.percentile(b[:, 1], [2.5, 97.5])])
    res = dict(note="holdout: KIỂM TRA, KHÔNG MÙ; nhãn máy hai lượt chưa người kiểm định; sự kiện suy từ nhãn khung (spec 7.4)",
               run=a.run, summary=summ, per_video={v: {k: ({kk: vv for kk, vv in x.items() if kk != "lat"} if isinstance(x, dict) else x)
                                                      for k, x in d.items()} for v, d in pv.items()})
    Path(ROOT / a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
