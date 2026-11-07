"""Thử nghiệm 6 lớp: tỷ lệ tự nhất quán của nhãn người trên khung lặp và trên hộp được chấm hai lần. Chỉ đọc, không sửa nhãn.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv, sau 03i):
    python scripts/03u_ppe6_consistency.py

Khung lặp: hai ảnh đánh giá (val_new, test_new, chvg_glass_val, chvg_glass_test) rất giống nhau theo đúng luật nối cảnh của 03f: pHash cách nhau tối đa
`scene.phash_max` hoặc cosine đặc trưng từ `scene.emb_strong` (configs/ppe6.yaml), ví dụ hai khung liền nhau của cùng một cảnh. Hai hộp cùng lớp, IoU tọa độ chuẩn hóa từ `consistency.min_iou` trở lên, coi là cùng một vật.
So nhãn người hiệu lực của hai hộp. Lặp chấm: hộp người chấm hai lần theo cùng định nghĩa (rest, rồi recheck).
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.machine_labels import human_box_labels, read_csv  # noqa: E402
from ppe.ppe6_data import box_iou_xyxy, wilson  # noqa: E402

REVIEW = ROOT / "data" / "ppe6" / "review"
BLIND = REVIEW / "cvat_pack_blind" / "_private"


def xyxy(r):
    cx, cy, w, h = (float(r[k]) for k in ("cx", "cy", "w", "h"))
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    full = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    c = full["consistency"]
    items = {r["box_id"]: r for t in ("task_a", "task_b", "task_c", "task_d") for r in read_csv(BLIND / f"{t}_items.csv")}
    human = human_box_labels(REVIEW)
    by_file = defaultdict(list)
    for k, r in human.items():
        it = items.get(k)
        if it and it["set"] in ("val_new", "test_new", "chvg_glass_val", "chvg_glass_test"):
            by_file[it["file"]].append((it["target"], xyxy(it), r["after"]))
    z = np.load(ROOT / "data" / "ppe6" / "scene" / "features.npz", allow_pickle=False)
    idx = {k: i for i, k in enumerate(z["key"].tolist())}
    files = sorted(f for f in by_file if f in idx)
    bits = np.unpackbits(z["phash"][[idx[f] for f in files]], axis=1)
    emb = z["emb"][[idx[f] for f in files]]
    pairs, frames = [], 0
    for a, b in combinations(range(len(files)), 2):
        if int((bits[a] != bits[b]).sum()) > full["scene"]["phash_max"] and float(emb[a] @ emb[b]) < full["scene"]["emb_strong"]:
            continue
        frames += 1
        for ta, ba, la in by_file[files[a]]:
            for tb, bb, lb in by_file[files[b]]:
                if ta == tb and box_iou_xyxy(ba, bb) >= c["min_iou"]:
                    pairs.append((ta, la, lb))
    res = dict(frame_pairs=frames)
    for t in ("boots", "goggles"):
        v = [p for p in pairs if p[0] == t]
        k = sum(la == lb for _, la, lb in v)
        p, lo, hi = wilson(k, len(v))
        res[t] = dict(pairs=len(v), consistent=k, rate=round(p, 4), ci=[round(lo, 4), round(hi, 4)], differ=dict(Counter(f"{la}|{lb}" for _, la, lb in v if la != lb)))
    rest = {r["item_id"]: r for r in read_csv(REVIEW / "rest_review.csv")}
    first = json.loads((REVIEW / "fast_rest_state.json").read_text(encoding="utf-8"))["boxes"] if (REVIEW / "fast_rest_state.json").exists() else {}
    rmap = {r["audit_id"]: r["item_id"] for r in read_csv(REVIEW / "cvat_pack_audit" / "_private" / "rest_items.csv")}
    again = [(rest[rmap[a]]["target"], v["decision"], rest[rmap[a]]["after"]) for a, v in first.items() if rest.get(rmap.get(a), {}).get("origin") == "rest_recheck"]
    for t in ("boots", "goggles"):
        v = [x for x in again if x[0] == t]
        k = sum(a == b for _, a, b in v)
        p, lo, hi = wilson(k, len(v))
        res[f"lap_cham_{t}"] = dict(boxes=len(v), consistent=k, rate=round(p, 4), ci=[round(lo, 4), round(hi, 4)], note="chỉ hộp đã lệch với kiểm tra mù của agent, không đại diện")
    out = ROOT / "outputs" / "results" / "ppe6_consistency.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
