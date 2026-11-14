"""Ghép hai lượt nhãn máy (A, B) của video holdout thành nhãn đồng thuận và đo độ đồng thuận.

Hộp người lấy từ spec A (hai lượt dùng chung hộp). Mỗi khung, mỗi thuộc tính: A = B thì giữ, khác thì `chua_xac_dinh`.
Độ đồng thuận tính trên mọi khung có hộp người: tỉ lệ khung trùng nhau và Cohen's kappa (3 giá trị) theo thuộc tính.

Cách chạy (từ thư mục gốc, .venv):
    python data/videos/holdout/tools/consensus.py spec_A.json spec_B_attrs.json spec_consensus.json agreement.json
"""

import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_labels import ORDER, person_boxes, prefill, val  # noqa: E402

VALS = ("co", "thieu", "chua_xac_dinh")


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[v] * cb[v] for v in VALS) / (n * n)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def to_segments(per_frame):
    seg, last = [], None
    for f in sorted(per_frame):
        if per_frame[f] != last:
            seg.append([f, per_frame[f]])
            last = per_frame[f]
    return seg or [[0, "chua_xac_dinh"]]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sa, sb, out_spec, out_agree = sys.argv[1:5]
    A = json.loads(Path(sa).read_text(encoding="utf-8"))
    B = json.loads(Path(sb).read_text(encoding="utf-8"))
    cons, pairs_all, report = {}, collections.defaultdict(list), {}
    for v, sv in A.items():
        T, n, w, h = prefill(v)
        cons[v] = {"persons": []}
        report[v] = {}
        for i, p in enumerate(sv["persons"]):
            frames = sorted(person_boxes(p, T, w, h))
            pb = B[v][i]
            attrs = {}
            for k in ORDER:
                pf, pairs = {}, []
                for f in frames:
                    a, b = val(p["attrs"][k], f), val(pb[k], f)
                    pairs.append((a, b))
                    pf[f] = a if a == b else "chua_xac_dinh"
                attrs[k] = to_segments(pf)
                pairs_all[k] += pairs
                report[v][f"{p['name']}/{k}"] = dict(frames=len(pairs), agree=sum(a == b for a, b in pairs),
                                                     disagree=sum(a != b for a, b in pairs))
            q = {kk: vv for kk, vv in p.items() if kk != "attrs"}
            q["attrs"] = attrs
            cons[v]["persons"].append(q)
    summary = {k: dict(frames=len(ps), agree_frac=round(sum(a == b for a, b in ps) / len(ps), 4), kappa=kappa(ps),
                       confusion={f"{a}|{b}": c for (a, b), c in sorted(collections.Counter(ps).items())})
               for k, ps in pairs_all.items()}
    Path(out_spec).write_text(json.dumps(cons, ensure_ascii=False, indent=1), encoding="utf-8")
    Path(out_agree).write_text(json.dumps(dict(summary=summary, by_video=report), ensure_ascii=False, indent=1),
                               encoding="utf-8")
    for k, s in summary.items():
        print(f"{k:12s} {s['frames']} khung, trùng {s['agree_frac']:.3f}, kappa {s['kappa']}")


if __name__ == "__main__":
    main()
