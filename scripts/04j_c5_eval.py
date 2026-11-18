"""Chấm detector trên val / test đã sửa nhãn của C5 (03z build-eval), đọc capture.npz của 04d. Chọn bản trên val; test
chỉ chạy một lần cho bản đã chọn (như các bước trước).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04d_capture_val.py --weights outputs/train/yolo11s_ppe6_c4/weights/best.pt --data data/ppe6/c5/eval/val/data.yaml --out outputs/results/c5_eval/c4_val
    python scripts/04j_c5_eval.py --split val --run c4=outputs/results/c5_eval/c4_val [--run c5=...] --name c4_vs_c5_val

Tập con (data/ppe6/c5/eval/files.json):
- `ppe4`: ảnh của ppe4 val (test), cho 4 lớp cũ, so được với số cũ trên nhãn gốc;
- `new`: ảnh đánh giá kính, ủng (val_new, test_new + ảnh SH17, Construction-PPE cảnh sạch), cho mọi lớp.
- `chvg`: ảnh CHVG đánh giá kính, chỉ lớp kính; `goggles_all` = `new` + `chvg`, chỉ lớp kính.
Vùng `ignore.csv` (luật configs/ppe6.yaml mục eval_ignore): dự đoán sai trùng vùng không tính đúng, không tính sai.
Bootstrap theo cảnh (scene_ids), `decision.n_boot`, seed `decision.seed`; có hai run thì thêm hiệu ghép cặp (run sau trừ
run đầu, cùng mẫu cảnh). Ghi outputs/results/c5_eval/<name>.json. Nhãn là nhãn máy, chưa người kiểm định.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import ap_from_tp, ignore_filter  # noqa: E402

CLASSES = ["person", "helmet", "vest", "gloves", "goggles", "boots"]
EVAL = ROOT / "data" / "ppe6" / "c5" / "eval"
OUT = ROOT / "outputs" / "results" / "c5_eval"
SUBSETS = {"ppe4": [0, 1, 2, 3], "new": [0, 1, 2, 3, 4, 5], "chvg": [4], "goggles_all": [4]}


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def load(path):
    z = np.load(Path(path) / "capture.npz", allow_pickle=False)
    return {k: z[k] for k in z.files}


def to_canvas(b, ori, rp):
    cx, cy, w, h = b
    oh, ow = ori
    g, px, py = rp
    return ((cx - w / 2) * ow * g + px, (cy - h / 2) * oh * g + py, (cx + w / 2) * ow * g + px, (cy + h / 2) * oh * g + py)


def apply_ignore(z, ignore, min_overlap):
    keep = np.ones(len(z["conf"]), dtype=bool)
    for i, f in enumerate(z["files"].tolist()):
        if f not in ignore:
            continue
        m = np.nonzero(z["img"] == i)[0]
        reg = [(c, *to_canvas(b, z["ori"][i], z["ratio_pad"][i])) for c, b in ignore[f]]
        keep[m] = ignore_filter(z["tp"][m], z["box"][m], z["cls"][m], reg, min_overlap)
    return {k: (v[keep] if k in ("img", "box", "conf", "cls", "tp") else v) for k, v in z.items()}, int((~keep).sum())


def class_ap(z, w_img, c):
    w, g = w_img[z["img"]], w_img[z["gimg"]]
    m = (z["cls"] == c) & (w > 0)
    return ap_from_tp(z["tp"][m], z["conf"][m], g[z["gcls"] == c].sum(), w[m])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["val", "test"], required=True)
    ap.add_argument("--run", action="append", required=True, help="tên=thư mục capture (04d)")
    ap.add_argument("--name", required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    full = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    cfg, min_ov = full["decision"], full["eval_ignore"]["min_overlap"]
    files = json.loads((EVAL / "files.json").read_text(encoding="utf-8"))[args.split]
    ppe4 = {p.name for p in (ROOT / "data" / "ppe4" / "dataset" / "images" / args.split).iterdir()}
    chvg = set(files.get("chvg_files", []))
    sub_files = {"ppe4": set(files["all"]) & ppe4, "new": set(files["new_class_files"]), "chvg": chvg,
                 "goggles_all": set(files["new_class_files"]) | chvg}
    ignore = defaultdict(list)
    for r in rd(EVAL / "ignore.csv"):
        if r["split"] == args.split:
            ignore[r["file"]].append((int(r["cls"]), tuple(float(r[k]) for k in ("cx", "cy", "w", "h"))))
    scene = {r["file"]: r["scene_id"] for r in rd(ROOT / "data" / "ppe6" / "scene" / "scene_ids.csv")}
    for r in rd(ROOT / "data" / "ppe6" / "dataset" / "eval_status.csv"):   # cảnh của ảnh CHVG (03h)
        scene.setdefault(r["file"], r["scene"])
    runs = []
    for spec in args.run:
        name, path = spec.split("=", 1)
        z, dropped = apply_ignore(load(path), ignore, min_ov)
        runs.append((name, z, dropped))
    flist = runs[0][1]["files"].tolist()
    for _, z, _ in runs[1:]:
        if z["files"].tolist() != flist:
            sys.exit("Các capture phải cùng danh sách ảnh, cùng thứ tự")
    res = dict(split=args.split, note="nhãn máy (03z), chưa người kiểm định", runs={n: dict(ignored_predictions=d) for n, _, d in runs}, subsets={})
    rng = np.random.default_rng(cfg["seed"])
    for sub, classes in SUBSETS.items():
        if not sub_files[sub]:
            continue
        base = np.array([1.0 if f in sub_files[sub] else 0.0 for f in flist])
        groups = defaultdict(list)
        for i, f in enumerate(flist):
            if base[i]:
                groups[scene.get(f, f)].append(i)
        keys = sorted(groups)
        boots = [np.zeros(len(flist)) for _ in range(cfg["n_boot"])]
        for b in boots:
            for k in rng.integers(0, len(keys), len(keys)):
                b[groups[keys[k]]] += 1
        t = dict(images=int(base.sum()), scenes=len(keys), classes={})
        for c in classes:
            row = dict(gt=int(base[runs[0][1]["gimg"]][runs[0][1]["gcls"] == c].sum()))
            pts = {}
            for n, z, _ in runs:
                a50, a5095 = class_ap(z, base, c)
                bs = [class_ap(z, b, c)[0] for b in boots]
                pts[n] = bs
                row[n] = dict(map50=round(a50, 4), map50_95=round(a5095, 4), ci50=[round(float(x), 4) for x in np.percentile(bs, [2.5, 97.5])])
            if len(runs) == 2:
                (n0, _, _), (n1, _, _) = runs
                dd = np.array(pts[n1]) - np.array(pts[n0])
                row["diff50"] = dict(point=round(row[n1]["map50"] - row[n0]["map50"], 4), ci=[round(float(x), 4) for x in np.percentile(dd, [2.5, 97.5])])
            t["classes"][CLASSES[c]] = row
        res["subsets"][sub] = t
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for sub, t in res["subsets"].items():
        print(f"[{sub}] {t['images']} ảnh, {t['scenes']} cảnh")
        for c, row in t["classes"].items():
            print(f"  {c:8s} gt={row['gt']:5d} " + " | ".join(f"{n}: {row[n]['map50']:.4f} {row[n]['ci50']}" for n, _, _ in runs) +
                  (f" | diff {row['diff50']['point']:+.4f} {row['diff50']['ci']}" if "diff50" in row else ""))


if __name__ == "__main__":
    main()
