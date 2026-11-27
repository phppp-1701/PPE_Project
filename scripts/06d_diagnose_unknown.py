"""Chẩn đoán lý do "Chưa xác định" (CXĐ) trên video phát triển (chỉ đo, không đổi trạng thái, không chọn tham số).

Chạy 05_run_video --reasons với một cấu hình trên các video có nhãn, ghép người với nhãn như 06b (IoU >= 0,5), rồi đếm
lý do (`why` trong compliance) của các khung-người mà nhãn là Có hoặc Thiếu nhưng hệ thống ra CXĐ. Cột `nearby` tách
"detector không có hộp PPE trong hộp người" với "có hộp nhưng không gán/không dùng được".

Không chạy trên holdout hay video kiem_thu_gan (quy tắc data/videos/README.md).

    python scripts/06d_diagnose_unknown.py --config configs/pipeline.yaml \
        --videos video3 video4 video5 video6 --labels "data/videos/{v}_cvat.zip" \
        --videos-machine video9 ... video17 --labels-machine "data/videos/{v}_machine_cvat.zip" \
        --out outputs/results/close_eval/diag_unknown
"""
import argparse
import collections
import csv
import importlib.util
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("e06b", ROOT / "scripts" / "06b_evaluate_close_videos.py")
e06b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e06b)
PPE = e06b.PPE


def run(cfg, video, out_dir, skip):
    if skip and (out_dir / "reasons.csv").exists():
        return
    import subprocess
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ROOT / "scripts" / "05_run_video.py"), str(ROOT / "data" / "videos" / f"{video}.mp4"),
           "--config", str(ROOT / cfg), "--no-video", "--api-url", "", "--out", str(out_dir), "--stage", "full",
           "--reasons"]
    print(video, "|", cfg, flush=True)
    if subprocess.run(cmd, cwd=ROOT).returncode:
        sys.exit(f"05_run_video lỗi cho {video}")


def load_reasons(path):
    r = collections.defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            r[(int(row["frame"]), row["track_id"], row["ppe"])].append(row)
    return r


def diagnose(video, label_zip, out_dir):
    labels = e06b.load_labels(ROOT / label_zip)
    frames = e06b.load_frames(out_dir / "frames.csv")
    reasons = load_reasons(out_dir / "reasons.csv")
    cnt = collections.Counter()      # (ppe, nhãn, lý do, có hộp gần) -> số khung-người
    for f, _, st, tid in e06b.match(labels, frames, 0.5):
        if tid is None:
            continue
        for p in PPE:
            lab, pred = st[p]
            if pred != "chua_xac_dinh":
                continue
            rows = [r for r in reasons.get((f, tid, p), []) if r["state"] == "chua_xac_dinh"]
            why = "+".join(sorted({r["why"] or "?" for r in rows})) or "?"
            near = "+".join(sorted({r.get("near_status") or "khong_hop" for r in rows})) or "khong_hop"
            cnt[(p, lab, why, near)] += 1
    return cnt


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--videos", nargs="*", default=[])
    ap.add_argument("--labels", default="data/videos/{v}_cvat.zip")
    ap.add_argument("--videos-machine", nargs="*", default=[])
    ap.add_argument("--labels-machine", default="data/videos/{v}_machine_cvat.zip")
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-run", action="store_true", help="dùng lại reasons.csv đã có")
    a = ap.parse_args()
    out = ROOT / a.out
    jobs = [(v, a.labels.format(v=v), "nhan_nguoi") for v in a.videos] + \
           [(v, a.labels_machine.format(v=v), "nhan_may") for v in a.videos_machine]
    total = {"nhan_nguoi": collections.Counter(), "nhan_may": collections.Counter()}
    per_video = {}
    for v, lz, kind in jobs:
        run(a.config, v, out / v, a.skip_run)
        c = diagnose(v, lz, out / v)
        total[kind].update(c)
        per_video[v] = {"|".join(k): n for k, n in c.items()}
    res = {"config": a.config, "label_note": "video3-6 nhãn người; video9-17 nhãn máy",
           "total": {k: {"|".join(x): n for x, n in c.most_common()} for k, c in total.items()},
           "per_video": per_video}
    (out / "diag.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Lý do Chưa xác định khi nhãn là Có/Thiếu ({a.config})", ""]
    for kind, c in total.items():
        lines += [f"## {kind}", "", "| PPE | Nhãn | Lý do | Hộp PPE trong người | Khung-người |", "|---|---|---|---|---|"]
        lines += [f"| {p} | {lab} | {why} | {near} | {n} |" for (p, lab, why, near), n in
                  sorted(c.items(), key=lambda kv: (kv[0][0], kv[0][1], -kv[1]))]
        lines.append("")
    (out / "diag.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
