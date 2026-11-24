"""C8 thử nghiệm (kế hoạch docs/experiments/2026-11-16_c5_detector_plan.md, mục C8): chấm lại hộp găng của detector bằng bộ
phân loại tay (glove / bare_hand) rồi tính lại AP găng trên val đã sửa. Không train; chỉ val (test để dành).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04l_gloves_rescore.py --capture outputs/results/c5_eval/c6_ft_val --weights outputs/train/yolo11n_cls_parts_v2/weights/best.pt --name c6ft_cls_v2

Mỗi dự đoán găng (conf >= min_conf) được cắt vuông quanh hộp (cạnh dài * context, như ảnh cắt theo hộp của 03y), bộ phân
loại cho p = P(glove) / (P(glove) + P(bare_hand)). Điểm mới = conf^(1-w) * p^w với w trong lưới `weights_grid`. AP@0.5 tính
lại với tp gốc của validator (hộp, ghép không đổi; chỉ đổi thứ tự điểm), ignore như 04j. Ghi
outputs/results/c5_eval/rescore_<name>.json: AP theo w, theo nguồn. Tham số ở configs/ppe6.yaml mục `c8_rescore`.
"""

import argparse
import csv
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import ap_from_tp  # noqa: E402

GLOVES = 3


def load_04j():
    spec = importlib.util.spec_from_file_location("e04j", ROOT / "scripts" / "04j_c5_eval.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", default="val", choices=["val", "test"])
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    c = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["c8_rescore"]
    e = load_04j()
    z = e.load(ROOT / args.capture)
    ign = defaultdict(list)
    for r in csv.DictReader(open(ROOT / "data" / "ppe6" / "c5" / "eval" / "ignore.csv", encoding="utf-8")):
        if r["split"] == args.split:
            ign[r["file"]].append((int(r["cls"]), tuple(float(r[k]) for k in ("cx", "cy", "w", "h"))))
    z, _ = e.apply_ignore(z, ign, 0.5)
    files = z["files"].tolist()
    ppe4 = {p.name for p in (ROOT / "data" / "ppe4" / "dataset" / "images" / args.split).iterdir()}
    img_dir = ROOT / "data" / "ppe6" / "c5" / "eval" / args.split / "images"
    sel = np.nonzero((z["cls"] == GLOVES) & (z["conf"] >= c["min_conf"]) & np.array([files[i] in ppe4 for i in z["img"]]))[0]
    from ultralytics import YOLO
    model = YOLO(str(ROOT / args.weights))
    idx = {v: k for k, v in model.names.items()}
    p = np.full(len(z["conf"]), np.nan)
    by_img = defaultdict(list)
    for k in sel:
        by_img[int(z["img"][k])].append(k)
    for n, (i, ks) in enumerate(by_img.items()):
        im = cv2.imdecode(np.fromfile(str(img_dir / files[i]), dtype=np.uint8), cv2.IMREAD_COLOR)
        H, W = im.shape[:2]
        g, px, py = z["ratio_pad"][i]
        crops, kk = [], []
        for k in ks:
            x1, y1, x2, y2 = z["box"][k]
            x1, x2 = (x1 - px) / g, (x2 - px) / g
            y1, y2 = (y1 - py) / g, (y2 - py) / g
            side = max(x2 - x1, y2 - y1) * c["context"]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            a, b = int(max(cx - side / 2, 0)), int(max(cy - side / 2, 0))
            cr = im[b:int(min(cy + side / 2, H)), a:int(min(cx + side / 2, W))]
            if min(cr.shape[:2]) >= 4:
                crops.append(cr)
                kk.append(k)
        for k, r in zip(kk, model.predict(crops, imgsz=c["imgsz"], device=0, verbose=False) if crops else []):
            pr = r.probs.data.cpu().numpy()
            p[k] = pr[idx["glove"]] / max(pr[idx["glove"]] + pr[idx["bare_hand"]], 1e-9)
        if (n + 1) % 300 == 0:
            print(f"{n + 1}/{len(by_img)} ảnh", flush=True)
    src_of = lambda f: f.split("__")[0]
    res = dict(capture=args.capture, weights=args.weights, n_pred=int(len(sel)), params=c, by_w={})
    for w in c["weights_grid"]:
        out = {}
        for name, keep in [("all", lambda f: f in ppe4), ("sh17", lambda f: f in ppe4 and src_of(f) == "sh17"),
                           ("chv", lambda f: f in ppe4 and src_of(f) == "chv"),
                           ("construction_ppe", lambda f: f in ppe4 and src_of(f) == "construction_ppe")]:
            im_ok = np.array([keep(f) for f in files])
            m = np.nonzero((z["cls"] == GLOVES) & im_ok[z["img"]])[0]
            conf = z["conf"][m].astype(float)
            pp = p[m]
            sc = np.where(np.isnan(pp), conf * (1 - w), conf ** (1 - w) * np.nan_to_num(pp) ** w)   # hộp không chấm (conf thấp) xếp cuối
            ngt = int((im_ok[z["gimg"]] & (z["gcls"] == GLOVES)).sum())
            out[name] = round(ap_from_tp(z["tp"][m], sc, ngt)[0], 4)
        res["by_w"][str(w)] = out
        print(f"w={w}: " + "  ".join(f"{k} {v:.4f}" for k, v in out.items()))
    dst = ROOT / "outputs" / "results" / "c5_eval" / f"rescore_{args.name}.json"
    dst.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("Đã ghi", dst.relative_to(ROOT))


if __name__ == "__main__":
    main()
