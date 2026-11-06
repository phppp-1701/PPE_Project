"""Thử nghiệm 6 lớp: chọn cảnh cho val_new, test_new và tách CHVG. Chỉ đọc dữ liệu, ghi vào data/ppe6/eval/.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03h_ppe6_select_eval.py --sweep    # thử các mức mục tiêu ủng, in bảng đánh đổi, ghi tradeoff.csv
    python scripts/03h_ppe6_select_eval.py            # chọn theo `eval.target_boots`, ghi scene_roles.csv, chvg_split.csv

Quy tắc (configs/ppe6.yaml mục `eval`):
- Vai trò tính theo scene_id: cảnh được chọn thì không ảnh nào của nó ở train 6 lớp.
- val_new lấy ảnh ppe4 val và ppe4 train của cảnh; test_new lấy ảnh ppe4 test và ppe4 train. Ảnh ppe4 ở tập kia bị bỏ qua.
- Chỉ SH17, Construction-PPE vì CHV không có nhãn kính, ủng.
- Cảnh không có ảnh train được lấy trước vì không tốn gì. Sau đó chọn tham lam, tối thiểu theo thứ tự: hộp kính train mất,
  hộp ủng train mất, ảnh train mất, hộp 4 lớp cũ mất. Không dùng cảnh quá lớn (`max_scene_boots`) để trải trên nhiều cảnh.
- Số hộp là hộp `safety` theo decisions_v2, do Claude duyệt, chưa phải số sau người duyệt.
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ppe6" / "eval"
OLD = ("person", "helmet", "vest", "gloves")
SOURCES = ("sh17", "construction_ppe")


def load():
    stats = [r for r in csv.DictReader((ROOT / "data" / "ppe4" / "stats.csv").open(encoding="utf-8")) if r["split"] != "external_test"]
    scene = {r["file"]: r["scene_id"] for r in csv.DictReader((ROOT / "data" / "ppe6" / "scene" / "scene_ids.csv").open(encoding="utf-8"))}
    dec = {r["box_id"]: r for r in csv.DictReader((ROOT / "data" / "ppe6" / "review" / "decisions_v2.csv").open(encoding="utf-8"))}
    boxes = list(csv.DictReader((ROOT / "data" / "ppe6" / "review" / "boxes.csv").open(encoding="utf-8")))
    return stats, scene, dec, boxes


def scene_table(stats, scene, dec, boxes):
    """Mỗi cảnh: ảnh theo tập, hộp `safety` theo (lớp, tập, nguồn), hộp 4 lớp cũ ở train."""
    image_file = {r["image"]: r for r in stats}
    t = defaultdict(lambda: dict(imgs=Counter(), safe=Counter(), old=0, cp=0, files=[]))
    for r in stats:
        s = t[scene[r["file"]]]
        s["imgs"][r["split"]] += 1
        s["files"].append(r["file"])
        s["cp"] += r["source"] == "construction_ppe"
        s["chv_only"] = s.get("chv_only", True) and r["source"] == "chv"
        if r["split"] == "train":
            s["old"] += sum(int(r["n_" + c]) for c in OLD)
    for b in boxes:
        r = image_file.get(b["image"])
        if r is not None and dec[b["box_id"]]["label"] == "safety":
            t[scene[r["file"]]]["safe"][(b["target"], b["split"], b["source"])] += 1
    return t


def gain(s, role):
    """Hộp ủng thu được nếu cảnh nhận vai trò `role`, theo nguồn."""
    src = {"val_new": "val", "test_new": "test"}[role]
    return {o: s["safe"][("boots", src, o)] + s["safe"][("boots", "train", o)] for o in SOURCES}


def cost(s):
    gog = sum(v for k, v in s["safe"].items() if k[0] == "goggles" and k[1] == "train")
    boots = sum(v for k, v in s["safe"].items() if k[0] == "boots" and k[1] == "train")
    return gog, boots, s["imgs"]["train"], s["old"]


def natural_role(s):
    return "val_new" if s["imgs"]["val"] >= s["imgs"]["test"] else "test_new"


def select(t, target, cp_share, cfg, big):
    """Trả về {scene_id: role}. Lấy cảnh miễn phí, rồi thêm tới khi đủ hộp và đủ tỉ lệ Construction-PPE ở mỗi tập."""
    roles = {}
    usable = {k: s for k, s in t.items() if k not in big and not s.get("chv_only") and sum(v for q, v in s["safe"].items() if q[0] == "boots") <= cfg["max_scene_boots"]}
    for k, s in usable.items():
        if s["imgs"]["train"] == 0 and (s["imgs"]["val"] or s["imgs"]["test"]) and any(s["safe"].values()):
            roles[k] = natural_role(s)

    def totals(role):
        c = Counter()
        for k, r in roles.items():
            if r == role:
                c.update(gain(t[k], role))
        return c

    def need(role):
        c = totals(role)
        return max(0, target - sum(c.values())), max(0, round(target * cp_share) - c["construction_ppe"])

    pool = sorted(k for k, s in usable.items() if k not in roles and sum(v for q, v in s["safe"].items() if q[0] == "boots"))
    while True:
        wants = [(r, *need(r)) for r in ("val_new", "test_new")]
        wants = [w for w in wants if w[1] or w[2]]
        if not wants:
            break
        best = None
        for k in pool:
            s = t[k]
            for role, n_all, n_cp in wants:
                if s["imgs"][{"val_new": "test", "test_new": "val"}[role]] > s["imgs"][{"val_new": "val", "test_new": "test"}[role]]:
                    continue
                g = gain(s, role)
                useful = min(g["construction_ppe"], n_cp) * 3 + min(sum(g.values()), n_all)
                if not useful:
                    continue
                c = cost(s)
                score = (c[0], c[1] / useful, c[2] / useful, c[3] / useful, k, role)
                if best is None or score < best[0]:
                    best = (score, k, role)
        if best is None:
            break
        roles[best[1]] = best[2]
        pool.remove(best[1])
    return roles


def summarize(t, roles, stats_by_scene_files, photographers, target):
    row = dict(target=target)
    lost = Counter()
    scenes = Counter()
    for k, role in roles.items():
        s = t[k]
        c = cost(s)
        lost.update(dict(goggles=c[0], boots=c[1], images=c[2], old=c[3]))
        g = gain(s, role)
        src = {"val_new": "val", "test_new": "test"}[role]
        for o in SOURCES:
            row[f"{role}_boots_{o}"] = row.get(f"{role}_boots_{o}", 0) + g[o]
        row[f"{role}_goggles"] = row.get(f"{role}_goggles", 0) + s["safe"][("goggles", src, "sh17")] + s["safe"][("goggles", src, "construction_ppe")] + \
            sum(v for q, v in s["safe"].items() if q[0] == "goggles" and q[1] == "train")
        if sum(g.values()):
            scenes[role] += 1
    for role in ("val_new", "test_new"):
        row[f"{role}_boots"] = sum(row.get(f"{role}_boots_{o}", 0) for o in SOURCES)
        row[f"{role}_boot_scenes"] = scenes[role]
    row.update({f"lost_{k}": lost[k] for k in ("goggles", "boots", "images", "old")})
    return row


def split_chvg(cfg):
    """Ảnh CHVG không trùng ppe4, Pictor theo ngưỡng cảnh: gom cụm rồi chia theo cụm, cân số hộp glass."""
    sc = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["scene"]
    z = np.load(ROOT / "data" / "ppe6" / "scene" / "features.npz", allow_pickle=False)
    key, ph, em, hs = z["key"].tolist(), z["phash"], z["emb"], z["hist"]
    bits = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)
    chv = {Path(r["image"]).stem for r in csv.DictReader((ROOT / "data" / "ppe4" / "stats.csv").open(encoding="utf-8")) if r["source"] == "chv"}
    ci = [i for i, k in enumerate(key) if k.startswith("chvg__") and k[6:].split("_jpg.rf.")[0] not in chv]
    oi = [i for i, k in enumerate(key) if not k.startswith("chvg__")]

    def linked(i, others):
        h = bits[ph[i][None, :] ^ ph[others]].sum(1)
        e = em[others] @ em[i]
        c = hs[others] @ hs[i]
        return (h <= sc["phash_max"]) | ((e >= sc["emb_min"]) & (c >= sc["hist_min"])) | (e >= sc["emb_strong"]) | (e >= sc["emb_min"])

    clean = [i for i in ci if not linked(i, oi).any()]
    parent = {i: i for i in clean}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    arr = np.array(clean)
    for n, i in enumerate(clean):
        for j in arr[n + 1:][linked(i, arr[n + 1:])]:
            parent[find(int(j))] = find(i)
    glass = Counter(r["file"] for r in csv.DictReader((ROOT / "data" / "ppe6" / "external" / "chvg" / "boxes.csv").open(encoding="utf-8")) if r["cls"] == "glass")
    clusters = defaultdict(list)
    for i in clean:
        clusters[find(i)].append(key[i])
    groups = sorted(clusters.values(), key=lambda v: sorted(v)[0])
    random.Random(cfg["seed"]).shuffle(groups)
    groups.sort(key=lambda v: -sum(glass[f] for f in v))
    load_ = Counter(chvg_glass_val=0, chvg_glass_test=0)
    rows = []
    for n, g in enumerate(groups):
        side = min(load_, key=lambda s: (load_[s], s))
        load_[side] += sum(glass[f] for f in g) + 0.001 * len(g)
        rows += [dict(file=f, split=side, scene=f"c{n:04d}", n_glass=glass[f]) for f in sorted(g)]
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["eval"]
    stats, scene, dec, boxes = load()
    t = scene_table(stats, scene, dec, boxes)
    tagged = set()
    image_file = {r["image"]: r["file"] for r in stats}
    for b in boxes:
        if b["image"] in image_file and "scene_" in dec[b["box_id"]]["note"]:
            tagged.add(scene[image_file[b["image"]]])
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for target, share in cfg["levels"] if args.sweep else [(cfg["target_boots"], cfg["cp_share"])]:
        roles = select(t, target, share, cfg, tagged)
        row = summarize(t, roles, None, None, target)
        row["cp_share"] = share
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))
    if args.sweep:
        keys = sorted({k for r in rows for k in r})
        with (OUT / "tradeoff.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, keys, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        return
    with (OUT / "scene_roles.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["scene_id", "role"])
        w.writerows(sorted(roles.items()))
    chvg = split_chvg(cfg)
    with (OUT / "chvg_split.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(chvg[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(chvg)
    c = Counter()
    for r in chvg:
        c[(r["split"], "images")] += 1
        c[(r["split"], "glass")] += int(r["n_glass"])
    print("CHVG:", dict(sorted(c.items())), "cụm", len({r["scene"] for r in chvg}))


if __name__ == "__main__":
    main()
