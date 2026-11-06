"""Thử nghiệm 6 lớp: gom ảnh thành cảnh (scene_id) từ đặc trưng của 03e. Không dùng group_id của ppe4.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03f_ppe6_scene_ids.py --sweep     # thử lưới ngưỡng, in độ phủ cảnh đã biết và cỡ cụm lớn nhất
    python scripts/03f_ppe6_scene_ids.py             # gom theo ngưỡng ở configs/ppe6.yaml mục scene

Hai ảnh cùng cảnh khi pHash cách nhau <= phash_max, hoặc cosine đặc trưng >= emb_min và tương đồng màu >= hist_min,
hoặc cosine >= emb_strong dù khác màu. Cụm là thành phần liên thông của các cặp đó, rồi gộp thêm ảnh đã gắn thẻ cảnh khi duyệt
(mũ cam, ủng đỏ là một cảnh; `scene_snow` là một cảnh).
Ghi data/ppe6/scene/scene_ids.csv (file, scene_id, size), near_threshold.csv (cặp sát ngưỡng để người xem).
"""

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "data" / "ppe6" / "scene"
BITS = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def known_scenes():
    """Ảnh đã gắn thẻ cảnh khi duyệt, chỉ dùng để đo độ phủ, không dùng để gom."""
    stats = {r["image"]: r["file"] for r in csv.DictReader((ROOT / "data" / "ppe4" / "stats.csv").open(encoding="utf-8"))}
    dec = {r["box_id"]: r["note"] for r in csv.DictReader((ROOT / "data" / "ppe6" / "review" / "decisions.csv").open(encoding="utf-8"))}
    out = defaultdict(set)
    for b in csv.DictReader((ROOT / "data" / "ppe6" / "review" / "boxes.csv").open(encoding="utf-8")):
        for tag in ("scene_orange", "scene_red", "scene_snow"):
            if tag in dec[b["box_id"]]:
                out[tag].add(stats[b["image"]])
    return out


def pairs(z, pmax_scan, emin_scan):
    """Mọi cặp có thể vượt ngưỡng trong lưới: (i, j, hamming, cosine, hist)."""
    ph, emb, hs = z["phash"], z["emb"], z["hist"]
    out = []
    n = len(ph)
    for i in range(0, n, 512):
        e = emb[i:i + 512] @ emb.T
        h = BITS[ph[i:i + 512, None, :] ^ ph[None, :, :]].sum(-1, dtype=np.uint16)
        a, b = np.nonzero((e >= emin_scan) | (h <= pmax_scan))
        a = a + i
        keep = a < b
        a, b = a[keep], b[keep]
        hist = (hs[a] * hs[b]).sum(1)
        out.append(np.stack([a, b, h[a - i, b], e[a - i, b], hist], 1).astype(np.float32))
    return np.concatenate(out)


def components(n, edges):
    parent = np.arange(n)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return np.array([find(i) for i in range(n)])


def select(p, pmax, emin, hmin, strong):
    return p[(p[:, 2] <= pmax) | ((p[:, 3] >= emin) & (p[:, 4] >= hmin)) | (p[:, 3] >= strong)]


def tag_edges(key, known):
    idx = {k: i for i, k in enumerate(key)}
    groups = [known["scene_orange"] | known["scene_red"], known["scene_snow"]]
    out = []
    for g in groups:
        ids = sorted(idx[f] for f in g if f in idx)
        out += [(ids[0], j) for j in ids[1:]]
    return np.array(out, dtype=np.float32)


def report(key, comp, known):
    size = Counter(comp.tolist())
    idx = {k: i for i, k in enumerate(key)}
    parts = []
    for tag, files in sorted(known.items()):
        c = Counter(comp[idx[f]] for f in files if f in idx)
        top = c.most_common(1)[0]
        parts.append(f"{tag}: {top[1]}/{sum(c.values())} ảnh ở cụm lớn nhất, cụm đó {size[top[0]]} ảnh, {len(c)} cụm")
    return f"{len(size)} cụm, lớn nhất {max(size.values())}, cụm >=10 ảnh: {sum(v >= 10 for v in size.values())} | " + "; ".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["scene"]
    z = np.load(SCENE / "features.npz", allow_pickle=False)
    z = {k: z[k] for k in z.files}
    keep = np.array([not k.startswith("chvg__") for k in z["key"].tolist()])  # CHVG gom riêng ở bước kiểm tra trùng
    z = {k: v[keep] for k, v in z.items()}
    key = z["key"].tolist()
    p = pairs(z, cfg["phash_max"], min(cfg["emb_min"], min(cfg["sweep"]["emb_strong"])))
    print(f"{len(key)} ảnh, {len(p)} cặp ứng viên")
    known = known_scenes()
    if args.sweep:
        for st in cfg["sweep"]["emb_strong"]:
            e = select(p, cfg["phash_max"], cfg["emb_min"], cfg["hist_min"], st)
            print(f"emb_strong {st}:", report(key, components(len(key), e[:, :2]), known))
        return
    pm, em, hm = cfg["phash_max"], cfg["emb_min"], cfg["hist_min"]
    comp = components(len(key), np.concatenate([select(p, pm, em, hm, cfg["emb_strong"])[:, :2], tag_edges(key, known)]))
    print(report(key, comp, known))
    size = Counter(comp.tolist())
    rank = {c: i for i, (c, _) in enumerate(sorted(size.items(), key=lambda x: (-x[1], x[0])))}
    with (SCENE / "scene_ids.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["file", "scene_id", "size"])
        for k, c in sorted(zip(key, comp.tolist())):
            w.writerow([k, f"s{rank[c]:05d}", size[c]])
    near = p[(comp[p[:, 0].astype(int)] != comp[p[:, 1].astype(int)]) & (p[:, 3] >= em - cfg["near_margin"])]
    near = near[np.argsort(-near[:, 3])][:cfg["near_samples"]]
    with (SCENE / "near_threshold.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["a", "b", "hamming", "cosine", "hist"])
        for a, b, h, e, hh in near:
            w.writerow([key[int(a)], key[int(b)], int(h), f"{e:.4f}", f"{hh:.4f}"])
    print("near_threshold:", len(near))


if __name__ == "__main__":
    main()
