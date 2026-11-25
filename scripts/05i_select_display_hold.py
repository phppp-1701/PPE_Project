"""A2 (docs/experiments/2026-11-25_close_range_fixes.md): chọn display.hold_s trên video chỉnh tham số từ detail.csv của 05h.

Trạng thái mỗi PPE của một người ở mỗi khung (như compliance: Thiếu nếu một bên Thiếu, Có nếu mọi bên Có, còn lại Chưa xác
định) được đưa qua DisplaySmoother (src/ppe/display.py) với từng hold_s trong lưới. Đếm số lần đổi trạng thái hiển thị giữa hai
khung liền nhau của cùng người, quy về mỗi phút (tổng mọi PPE), so với trạng thái từng khung (không làm mượt).
Chọn hold_s nhỏ nhất đạt giảm >= --target (mặc định 0,8). Lớp hiển thị không đổi trạng thái, sự kiện, chỉ số.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05i_select_display_hold.py outputs/results/close_eval/stepA2/states_current --videos video3 video4 video5 video6

Ghi <thư mục>/display_hold.json.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe import HAVE, MISSING, UNKNOWN  # noqa: E402
from ppe.display import DisplaySmoother  # noqa: E402

CODE = {"co": HAVE, "thieu": MISSING, "cxd": UNKNOWN}
GRID = [0.5, 1.0, 1.5, 2.0]


def frames(path):
    """[(frame, t, {track_id: {ppe: {"state"}}})] theo thứ tự khung, gộp các bên như compliance."""
    rows = defaultdict(lambda: defaultdict(list))
    tt = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        f = int(r["frame"])
        tt[f] = float(r["t"])
        rows[f][(int(r["track_id"]), r["ppe"])].append(CODE[r["state"]])
    out = []
    for f in sorted(rows):
        st = defaultdict(dict)
        for (tid, name), ss in rows[f].items():
            s = MISSING if MISSING in ss else (HAVE if all(x == HAVE for x in ss) else UNKNOWN)
            st[tid][name] = {"state": s}
        out.append((f, tt[f], st))
    return out


def changes(seq_by_frame):
    """seq_by_frame: [(frame, {tid: {ppe: state}})] -> số lần đổi giữa hai khung liền nhau của cùng (người, PPE)."""
    prev, n = {}, 0
    for f, st in seq_by_frame:
        for tid, per in st.items():
            for name, s in per.items():
                k = (tid, name)
                if k in prev and prev[k][0] == f - 1 and prev[k][1] != s:
                    n += 1
                prev[k] = (f, s)
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", help="thư mục --out của 05h (có <video>/detail.csv)")
    ap.add_argument("--videos", nargs="+", required=True)
    ap.add_argument("--target", type=float, default=0.8)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    run = Path(args.run_dir)
    base_n, minutes, by_hold = 0, 0.0, {h: 0 for h in GRID}
    for v in args.videos:
        fr = frames(run / v / "detail.csv")
        s = json.loads((run / v / "summary.json").read_text(encoding="utf-8"))
        cells = sum(len(per) for _, _, st in fr for per in st.values())
        minutes += cells / s["fps"] / 60
        base_n += changes([(f, {tid: {n: x["state"] for n, x in per.items()} for tid, per in st.items()}) for f, _, st in fr])
        for h in GRID:
            sm = DisplaySmoother(h)
            by_hold[h] += changes([(f, sm(t, st)) for f, t, st in fr])
    res = dict(videos=args.videos, phut_nguoi_ppe=round(minutes, 2), doi_tung_khung_moi_phut=round(base_n / minutes, 2),
               luoi={str(h): dict(doi_hien_thi_moi_phut=round(n / minutes, 2), giam=round(1 - n / max(base_n, 1), 4))
                     for h, n in by_hold.items()}, muc_tieu=args.target)
    ok = [h for h in GRID if 1 - by_hold[h] / max(base_n, 1) >= args.target]
    res["chon"] = min(ok) if ok else None
    (run / "display_hold.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
