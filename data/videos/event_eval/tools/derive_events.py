"""Ghép hai lượt nhãn máy (spec_A, spec_B) của event_eval, đo đồng thuận, suy sự kiện chuẩn theo spec 7.4.

Lưới thời gian 0,1 s trong khoảng người có mặt (hợp các track của người, khoảng trống <= 2 s coi là liền). Mỗi thời điểm,
mỗi PPE: A = B thì giữ, khác thì `chua_xac_dinh`. Sự kiện chuẩn (PPE bắt buộc: cả 5 món): bắt đầu ở thời điểm đầu tiên có
món Thiếu; kết thúc khi mọi món là Có, hoặc hết đoạn có mặt (rời khung > 2 s), hoặc hết video (`until_end`). Món thiếu
của sự kiện = các món có Thiếu trong khoảng đó. Ghi `labels/events_gt.json`, `labels/agreement.json`.

    python data/videos/event_eval/tools/derive_events.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
L = ROOT / "data" / "videos" / "event_eval" / "labels"
PPE = ("helmet", "vest", "gloves", "goggles", "boots")
VALS = ("co", "thieu", "chua_xac_dinh")
STEP, GAP = 0.1, 2.0


def at(tl, t):
    s = tl[0][1]
    for t0, v in tl:
        if t >= t0 - 1e-9:
            s = v
    return s


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == v for a, _ in pairs) / n) * (sum(b == v for _, b in pairs) / n) for v in VALS)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def segments(tr, tracks, fps):
    fr = sorted({int(f) for t in tracks for f in tr["tracks"].get(t, {})})
    segs, s = [], None
    for f in fr:
        if s and (f - s[1]) / fps <= GAP:
            s[1] = f
        else:
            s = [f, f]
            segs.append(s)
    return [(a / fps, b / fps) for a, b in segs]


def main():
    A = json.loads((L / "work" / "spec_A.json").read_text(encoding="utf-8"))["videos"]
    B = json.loads((L / "work" / "spec_B.json").read_text(encoding="utf-8"))["videos"]
    events, pairs = {}, {p: [] for p in PPE}
    for v, persons in A.items():
        tr = json.loads((L / "work" / f"{v}_tracks.json").read_text(encoding="utf-8"))
        fps, dur = tr["fps"], tr["frames"] / tr["fps"]
        evs = []
        for name, pa in persons.items():
            pb = B[v][name]
            for s0, s1 in segments(tr, pa["tracks"], fps):
                k, cur = 0, None
                while s0 + k * STEP <= s1 + 1e-9:
                    t = s0 + k * STEP
                    st = {}
                    for p in PPE:
                        a, b = at(pa["attrs"][p], t), at(pb["attrs"][p], t)
                        pairs[p].append((a, b))
                        st[p] = a if a == b else "chua_xac_dinh"
                    miss = [p for p in PPE if st[p] == "thieu"]
                    if cur is None and miss:
                        cur = dict(person=name, tracks=pa["tracks"], start=round(t, 2), missing=set(miss))
                    elif cur is not None:
                        if all(st[p] == "co" for p in PPE):
                            cur["end"] = round(t, 2)
                            evs.append(cur)
                            cur = None
                        else:
                            cur["missing"] |= set(miss)
                    k += 1
                if cur is not None:
                    cur["end"] = round(s1, 2)
                    cur["until_end"] = s1 >= dur - 0.2
                    evs.append(cur)
        for e in evs:
            e["missing"] = sorted(e["missing"])
        events[v] = evs
    agree = {p: dict(n=len(x), agree=round(sum(a == b for a, b in x) / len(x), 3), kappa=kappa(x)) for p, x in pairs.items()}
    (L / "events_gt.json").write_text(json.dumps(dict(
        status="machine_consensus (Claude hai lượt), chờ người dùng kiểm định mẫu", required_ppe=list(PPE),
        rule="spec 7.4; khoảng trống có mặt <= 2 s coi là liền", events=events), ensure_ascii=False, indent=1), encoding="utf-8")
    (L / "agreement.json").write_text(json.dumps(agree, ensure_ascii=False, indent=1), encoding="utf-8")
    for v, evs in events.items():
        for e in evs:
            print(v, e["person"], e["start"], "-", e["end"], e["missing"], "(hết video)" if e.get("until_end") else "")
    print(json.dumps(agree, ensure_ascii=False))


if __name__ == "__main__":
    main()
