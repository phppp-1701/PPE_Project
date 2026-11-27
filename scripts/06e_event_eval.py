"""RQ3 / H3 trên tập event_eval (video độc lập, nhãn máy hai lượt có kiểm định của người; data/videos/event_eval/README.md).

Chạy 05_run_video với một cấu hình trên các video (một lần), rồi chấm theo spec 7.4:
- Cảnh báo của hệ thống (E) = mỗi sự kiện `created` trong events.jsonl, thời điểm `confirmed_at`, PPE = hợp `missing_items`
  trong lịch sử sự kiện.
- Người: hộp track của sự kiện ở khung `confirmed_at` (frames.csv) ghép với hộp người nhãn (track COCO của người, khung gần
  nhất trong ±1 s) khi IoU >= 0,5.
- Khớp sự kiện chuẩn khi cùng người, `start <= confirmed_at <= end`, có ít nhất một PPE trùng. Khớp đầu tiên = TP, khớp sau
  cùng đợt = trùng; không khớp = sai; người không có trong nhãn = ngoài nhãn (báo riêng). Hai mức PPE: chặt (nhãn máy) và
  theo kiểm định (nhãn máy hợp món người kiểm định ghi thêm).
- Mốc so sánh "theo khung" (cùng trạng thái của hệ thống, không cửa sổ thời gian, không sự kiện): mỗi khung-người có
  `missing_ppe` là một cảnh báo; chấm cùng luật. Đây không phải cấu hình A (YOLO thuần) của 06; ghi rõ khi báo cáo.
- Khoảng tin cậy 95% của Event F1 (E) và hiệu E - theo khung: bootstrap theo video (2.000 lần, hạt giống 0).

    python scripts/06e_event_eval.py --config configs/pipeline.yaml --out outputs/results/event_eval/final
    python scripts/06e_event_eval.py --config ... --out ... --skip-run    # chỉ chấm lại
"""

import argparse
import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "data" / "videos" / "event_eval"
LAB = EV / "labels"
VN = {"găng": "gloves", "ủng": "boots", "giày": "boots", "kính": "goggles", "mũ": "helmet", "áo": "vest"}


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-9)


def audit_extra():
    """{(video, person): set(ppe)} món người kiểm định ghi thêm (đọc ghi chú tiếng Việt)."""
    out = defaultdict(set)
    p = LAB / "audit_result.json"
    if not p.exists():
        return out
    for it in json.loads(p.read_text(encoding="utf-8"))["items"]:
        v, person = it["id"].split("_")[:2]
        for k, ppe in VN.items():
            if k in (it.get("note") or "").lower():
                out[(v, person)].add(ppe)
    return out


def gt_box(tr, tracks, f):
    """Hộp người nhãn ở khung gần f nhất (trong ±1 s) trên các track của người đó."""
    for d in range(0, int(tr["fps"]) + 1):
        for g in (f - d, f + d):
            for tid in tracks:
                b = tr["tracks"].get(tid, {}).get(str(g))
                if b:
                    return b
    return None


def load_frames(path):
    rows = defaultdict(dict)
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[int(r["frame"])][r["track_id"]] = r
    return rows


def score(alerts, gt_events, persons, tr, fps, extra, v, mode):
    """alerts: [(t, track_id, frame, set(ppe))]. Trả về số đếm và độ trễ."""
    hit, res = set(), dict(tp=0, dup=0, false=0, outside=0, lat=[])
    for t, tid, f, ppe, box in alerts:
        cands = [name for name, pa in persons.items()
                 if (b := gt_box(tr, pa["tracks"], f)) is not None and iou(box, b) >= 0.5]
        if not cands:
            res["outside"] += 1
            continue
        ok = None
        for k, e in enumerate(gt_events):
            if e["person"] in cands and e["start"] - 1e-6 <= t <= e["end"] + 1e-6:
                acc = set(e["missing"]) | (extra.get((v, e["person"]), set()) if mode == "audit" else set())
                if ppe & acc:
                    ok = k
                    break
        if ok is None:
            res["false"] += 1
        elif ok in hit:
            res["dup"] += 1
        else:
            hit.add(ok)
            res["tp"] += 1
            res["lat"].append(t - gt_events[ok]["start"])
    res["fn"] = len(gt_events) - len(hit)
    return res


def prf(c):
    tp, fp = c["tp"], c["false"] + c["dup"]
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + c["fn"]) if tp + c["fn"] else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-run", action="store_true")
    a = ap.parse_args()
    out = ROOT / a.out
    gt = json.loads((LAB / "events_gt.json").read_text(encoding="utf-8"))["events"]
    spec_a = json.loads((LAB / "work" / "spec_A.json").read_text(encoding="utf-8"))["videos"]
    extra = audit_extra()
    per_video = {}
    for v in spec_a:
        d = out / v
        if not a.skip_run:
            d.mkdir(parents=True, exist_ok=True)
            cmd = [sys.executable, str(ROOT / "scripts" / "05_run_video.py"), str(EV / f"{v}.mp4"), "--config", str(ROOT / a.config),
                   "--no-video", "--api-url", "", "--out", str(d), "--stage", "full"]
            print(v, flush=True)
            if subprocess.run(cmd, cwd=ROOT).returncode:
                sys.exit(f"05_run_video lỗi: {v}")
        tr = json.loads((LAB / "work" / f"{v}_tracks.json").read_text(encoding="utf-8"))
        fps = tr["fps"]
        frames = load_frames(d / "frames.csv")
        evs = defaultdict(lambda: dict(items=set()))
        for line in (d / "events.jsonl").read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            x = evs[e["event_id"]]
            x.update(track=str(e["track_id"]), t=e["confirmed_at"])
            for h in e.get("history") or []:
                x["items"] |= set(h.get("missing_items") or [])
            x["items"] |= set(e.get("missing_items") or [])
        alerts_e = []
        for x in evs.values():
            f = int(round(x["t"] * fps))
            r = frames.get(f, {}).get(x["track"]) or next((frames[g][x["track"]] for g in range(f - 3, f + 4)
                                                           if x["track"] in frames.get(g, {})), None)
            if r:
                alerts_e.append((x["t"], x["track"], f, x["items"], [float(r[k]) for k in ("x1", "y1", "x2", "y2")]))
        alerts_f = [(int(f) / fps, tid, f, set(r["missing_ppe"].split(";")), [float(r[k]) for k in ("x1", "y1", "x2", "y2")])
                    for f, rows in frames.items() for tid, r in rows.items() if r["missing_ppe"]]
        g = gt.get(v, [])
        per_video[v] = {m: dict(E=score(alerts_e, g, spec_a[v], tr, fps, extra, v, m),
                                frame=score(alerts_f, g, spec_a[v], tr, fps, extra, v, m)) for m in ("strict", "audit")}
    res = dict(config=a.config, label_note="nhãn máy hai lượt (Claude), người dùng kiểm định 12/12 thẻ (11 Đúng, 1 Không chắc)",
               baseline_note="theo khung = cùng trạng thái của hệ thống, mỗi khung-người có Thiếu là một cảnh báo (không phải A của 06)",
               per_video={v: {m: {k: {kk: vv for kk, vv in c.items() if kk != "lat"} | dict(mean_latency_s=round(float(np.mean(c["lat"])), 3) if c["lat"] else None)
                                  for k, c in x.items()} for m, x in pv.items()} for v, pv in per_video.items()}, summary={})
    vids = list(per_video)
    rng = np.random.default_rng(0)
    for m in ("strict", "audit"):
        for k in ("E", "frame"):
            c = {q: sum(per_video[v][m][k][q] for v in vids) for q in ("tp", "dup", "false", "outside", "fn")}
            lat = [x for v in vids for x in per_video[v][m][k]["lat"]]
            p, r, f1 = prf(c)
            res["summary"][f"{m}_{k}"] = dict(**c, alerts=c["tp"] + c["dup"] + c["false"] + c["outside"], precision=round(p, 3),
                                              recall=round(r, 3), f1=round(f1, 3), mean_latency_s=round(float(np.mean(lat)), 3) if lat else None)
        boots = []
        for _ in range(2000):
            s = rng.choice(vids, len(vids))
            fe = prf({q: sum(per_video[v][m]["E"][q] for v in s) for q in ("tp", "dup", "false", "fn")})[2]
            ff = prf({q: sum(per_video[v][m]["frame"][q] for v in s) for q in ("tp", "dup", "false", "fn")})[2]
            boots.append((fe, fe - ff))
        b = np.array(boots)
        res["summary"][f"{m}_ci95"] = dict(E_f1=[round(float(x), 3) for x in np.percentile(b[:, 0], [2.5, 97.5])],
                                           diff_E_minus_frame=[round(float(x), 3) for x in np.percentile(b[:, 1], [2.5, 97.5])])
    (out / "event_eval.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["summary"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
