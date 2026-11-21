"""mAP50 theo nguồn ảnh (SH17, CHV, Construction-PPE, CHVG) cho capture của 04d / 04m, cùng đường tính với 04j.

Dùng để so với số của bài gốc trên cùng nguồn ảnh (docs/experiments/2026-11-21_compare_prior_work.md). Cùng luật ignore,
cùng tập con mỗi lớp như 04j / c9_decision: người, mũ, áo, găng trên tập `ppe4`; kính trên `goggles_all`; ủng trên `new`.
Nguồn = tiền tố tên file trước `__`. Bỏ ô có < 10 hộp nhãn. Không bootstrap (chỉ để đối chiếu, không dùng để chọn bản).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04o_eval_by_source.py --split val --run c6_ft=outputs/results/c5_eval/c8lab_c6_ft_val --run c6_ft_zoom=outputs/results/c5_eval/c8lab_c6_ft_crop_val --name by_source_c6_ft

Ghi outputs/results/c5_eval/<name>.json. Nhãn val là nhãn máy, có kiểm định mẫu của người.
"""

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("eval04j", ROOT / "scripts" / "04j_c5_eval.py")
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
WHICH = {"person": "ppe4", "helmet": "ppe4", "vest": "ppe4", "gloves": "ppe4", "goggles": "goggles_all", "boots": "new"}
MIN_GT = 10


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["val", "test"], required=True)
    ap.add_argument("--run", action="append", required=True, help="tên=thư mục capture")
    ap.add_argument("--name", required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    full = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    files = json.loads((E.EVAL / "files.json").read_text(encoding="utf-8"))[args.split]
    ppe4 = {p.name for p in (ROOT / "data" / "ppe4" / "dataset" / "images" / args.split).iterdir()}
    chvg = set(files.get("chvg_files", []))
    subs = {"ppe4": set(files["all"]) & ppe4, "new": set(files["new_class_files"]), "goggles_all": set(files["new_class_files"]) | chvg}
    ignore = defaultdict(list)
    for r in E.rd(E.EVAL / "ignore.csv"):
        if r["split"] == args.split:
            ignore[r["file"]].append((int(r["cls"]), tuple(float(r[k]) for k in ("cx", "cy", "w", "h"))))
    res = dict(split=args.split, note="nhãn máy, có kiểm định mẫu của người; không bootstrap, chỉ để đối chiếu", runs={})
    for spec in args.run:
        name, path = spec.split("=", 1)
        z, _ = E.apply_ignore(E.load(path), ignore, full["eval_ignore"]["min_overlap"])
        flist = z["files"].tolist()
        src = [f.split("__")[0] if "__" in f else "khac" for f in flist]
        rows = {}
        for cname, sub in WHICH.items():
            c = E.CLASSES.index(cname)
            for s in sorted(set(src)):
                w = np.array([1.0 if (f in subs[sub] and src[i] == s) else 0.0 for i, f in enumerate(flist)])
                gt = int(w[z["gimg"]][z["gcls"] == c].sum())
                if gt >= MIN_GT:
                    rows[f"{cname}|{s}"] = dict(subset=sub, gt=gt, map50=round(E.class_ap(z, w, c)[0], 4))
        res["runs"][name] = rows
    (E.OUT / f"{args.name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    keys = sorted({k for r in res["runs"].values() for k in r})
    print("lớp|nguồn".ljust(26) + "".join(n.rjust(14) for n in res["runs"]))
    for k in keys:
        gt = next(r[k]["gt"] for r in res["runs"].values() if k in r)
        print(f"{k} ({gt})".ljust(26) + "".join((f"{r[k]['map50']:.4f}" if k in r else "-").rjust(14) for r in res["runs"].values()))


if __name__ == "__main__":
    main()
