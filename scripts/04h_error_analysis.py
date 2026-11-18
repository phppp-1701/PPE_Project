"""Bước A (kế hoạch 2026-11-16_c5_detector_plan.md): phân tích lỗi detector trên val từ capture.npz của 04d.

Không chạy lại mô hình, không chọn tham số. Tham số ở configs/ppe6.yaml mục `error_analysis`.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04h_error_analysis.py                 # mọi run trong cấu hình
    python scripts/04h_error_analysis.py --run c4_valnew

Ghi outputs/results/error_analysis/<run>/:
    summary.json   mỗi lớp: AP50 (tính lại, đối chiếu 04e), bỏ sót theo cỡ, theo nguồn, theo kiểu lỗi;
                   báo thừa theo kiểu (vật âm của nhãn gốc, lệch hộp, trùng lặp, nhầm lớp, không rõ)
    fn.csv, fp.csv từng hộp bỏ sót / báo thừa (ảnh, hộp, cỡ, nguồn, kiểu)
    sheet_<lớp>_<kiểu>.jpg  bảng ảnh cắt (hộp đỏ = nhãn bị bỏ sót, hộp vàng = dự đoán báo thừa) để người hoặc máy xem
Ghép: dự đoán đã sắp theo conf giảm, tham lam, cùng lớp, IoU >= match_iou (gần như validator của Ultralytics).
"""

import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import ap_from_tp  # noqa: E402

CLASSES = ["person", "helmet", "vest", "gloves", "goggles", "boots"]
OUT = ROOT / "outputs" / "results" / "error_analysis"
RAW_LABELS = {
    "sh17": [ROOT / "data/raw/sh17/labels"],
    "construction_ppe": [ROOT / f"data/raw/construction_ppe/labels/{s}" for s in ("train", "val", "test")],
}


def load_04e():
    spec = importlib.util.spec_from_file_location("e04", ROOT / "scripts" / "04e_ppe6_eval.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def iou(a, b):
    """a: [4], b: [n, 4] -> [n]"""
    if len(b) == 0:
        return np.zeros(0)
    x1 = np.maximum(a[0], b[:, 0]); y1 = np.maximum(a[1], b[:, 1])
    x2 = np.minimum(a[2], b[:, 2]); y2 = np.minimum(a[3], b[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1]) - inter
    return inter / np.maximum(ua, 1e-9)


def source_of(f):
    return f.split("__", 1)[0] if "__" in f else "khac"


def raw_negatives(f, ori, rp, cfg, to_canvas):
    """Hộp vật âm của nhãn gốc (theo lớp PPE) ở không gian capture: {ppe: [[x1,y1,x2,y2]]}."""
    src, stem = source_of(f), Path(f.split("__", 1)[-1]).stem
    neg = cfg["negatives"].get(src)
    if not neg:
        return {}
    path = next((d / f"{stem}.txt" for d in RAW_LABELS.get(src, []) if (d / f"{stem}.txt").exists()), None)
    if path is None:
        return {}
    out = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        p = line.split()
        if len(p) < 5:
            continue
        c = int(float(p[0]))
        for ppe, ids in neg.items():
            if c in ids:
                out[ppe].append(to_canvas((c, *map(float, p[1:5])), ori, rp))
    return {k: np.array(v, dtype=float) for k, v in out.items()}


def size_bin(side, bins):
    for b in bins:
        if side < b:
            return f"<{b}"
    return f">={bins[-1]}"


def subset_capture(z, keep):
    """Giữ các ảnh trong keep, đánh lại chỉ số ảnh."""
    files = z["files"].tolist()
    idx = [i for i, f in enumerate(files) if f in keep]
    remap = -np.ones(len(files), dtype=int)
    remap[idx] = np.arange(len(idx))
    pm, gm = remap[z["img"]] >= 0, remap[z["gimg"]] >= 0
    out = dict(z)
    for k in ("img", "box", "conf", "cls", "tp"):
        out[k] = z[k][pm]
    out["img"] = remap[z["img"][pm]]
    for k in ("gbox", "gcls"):
        out[k] = z[k][gm]
    out["gimg"] = remap[z["gimg"][gm]]
    for k in ("files", "canvas", "ori", "ratio_pad"):
        out[k] = z[k][idx]
    return out


def analyze(run, cfg, e04):
    z = e04.load(ROOT / run["capture"])
    full = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    if run.get("ignore") == "c5":   # val / test đã sửa của C5 (03z build-eval): ignore.csv riêng, có cột split
        ign = defaultdict(list)
        for r in csv.DictReader(open(ROOT / "data" / "ppe6" / "c5" / "eval" / "ignore.csv", encoding="utf-8")):
            if r["split"] == run["split"]:
                ign[r["file"]].append((int(r["cls"]), *(float(r[k]) for k in ("cx", "cy", "w", "h"))))
        z, dropped = e04.apply_ignore(z, ign, full["eval_ignore"]["min_overlap"])
    elif run.get("ignore"):
        z, dropped = e04.apply_ignore(z, e04.load_ignore(), full["eval_ignore"]["min_overlap"])
    else:
        dropped = 0
    if run.get("subset"):   # chỉ ảnh của một tập con trong data/ppe6/c5/eval/files.json (vd new_class_files)
        fj = json.loads((ROOT / "data" / "ppe6" / "c5" / "eval" / "files.json").read_text(encoding="utf-8"))[run["split"]]
        keep = fj["all"] if run["subset"] == "ppe4" else fj[run["subset"]]
        if run["subset"] == "ppe4":
            keep = set(keep) & {q.name for q in (ROOT / "data" / "ppe4" / "dataset" / "images" / run["split"]).iterdir()}
        z = subset_capture(z, set(keep))
    files = z["files"].tolist()
    bins = cfg["size_bins_px"]
    res = dict(run=run["name"], capture=run["capture"], images=len(files), ignored_predictions=dropped, classes={})
    fn_rows, fp_rows = [], []
    for name in run["classes"]:
        c = CLASSES.index(name)
        ap50 = ap_from_tp(z["tp"][z["cls"] == c], z["conf"][z["cls"] == c], int((z["gcls"] == c).sum()))[0]
        fn_by = defaultdict(Counter)
        fp_kind = Counter()
        n_gt = 0
        for i, f in enumerate(files):
            g = z["gbox"][(z["gimg"] == i) & (z["gcls"] == c)]
            g_other = z["gbox"][(z["gimg"] == i) & (z["gcls"] != c)]
            g_other_cls = z["gcls"][(z["gimg"] == i) & (z["gcls"] != c)]
            pm = (z["img"] == i) & (z["cls"] == c)
            pb, pc = z["box"][pm], z["conf"][pm]
            order = np.argsort(-pc)
            pb, pc = pb[order], pc[order]
            matched_g = np.zeros(len(g), dtype=bool)
            pred_ok = np.zeros(len(pb), dtype=bool)
            for j, b in enumerate(pb):
                if len(g) == 0:
                    break
                ov = iou(b, g)
                ov[matched_g] = -1
                k = int(np.argmax(ov))
                if ov[k] >= cfg["match_iou"]:
                    matched_g[k] = pred_ok[j] = True
            src = source_of(f)
            negs = None
            # Bỏ sót
            n_gt += len(g)
            for k, gb in enumerate(g):
                side = float(min(gb[2] - gb[0], gb[3] - gb[1]))
                sb = size_bin(side, bins)
                found = bool(matched_g[k])
                fn_by["size"][(sb, found)] += 1
                fn_by["source"][(src, found)] += 1
                if found:
                    continue
                any_pred = z["box"][z["img"] == i]
                any_cls = z["cls"][z["img"] == i]
                any_conf = z["conf"][z["img"] == i]
                ov_all = iou(gb, any_pred)
                same = (any_cls == c) & (ov_all >= cfg["loc_iou"])
                other = (any_cls != c) & (ov_all >= cfg["match_iou"]) & (any_conf >= cfg["conf"])
                kind = "lech_hop" if same.any() else ("nham_lop" if other.any() else "khong_thay")
                fn_by["kind"][kind] += 1
                fn_rows.append(dict(run=run["name"], cls=name, file=f, source=src, side=round(side, 1), size_bin=sb, kind=kind,
                                    other=CLASSES[int(any_cls[other][np.argmax(any_conf[other])])] if other.any() else "",
                                    box=[round(float(v), 1) for v in gb], img_idx=i))
            # Báo thừa (dự đoán conf >= ngưỡng không ghép được)
            for j, b in enumerate(pb):
                if pred_ok[j] or pc[j] < cfg["conf"]:
                    continue
                ov_same = iou(b, g)
                if len(g) and (ov_same >= cfg["match_iou"]).any():
                    kind = "trung_lap"
                elif len(g) and (ov_same >= cfg["loc_iou"]).any():
                    kind = "lech_hop"
                else:
                    if negs is None:
                        negs = raw_negatives(f, z["ori"][i], z["ratio_pad"][i], cfg, e04.to_canvas)
                    nb = negs.get(name, np.zeros((0, 4)))
                    if len(nb) and (iou(b, nb) >= cfg["neg_iou"]).any():
                        kind = "vat_am"
                    elif len(g_other) and (iou(b, g_other) >= cfg["match_iou"]).any():
                        kind = "nham_lop"
                    else:
                        kind = "khong_ro"
                fp_kind[kind] += 1
                fp_rows.append(dict(run=run["name"], cls=name, file=f, source=src, conf=round(float(pc[j]), 3), kind=kind,
                                    side=round(float(min(b[2] - b[0], b[3] - b[1])), 1),
                                    box=[round(float(v), 1) for v in b], img_idx=i))
        sizes = sorted({k[0] for k in fn_by["size"]}, key=lambda s: (s.startswith(">="), float(s.strip("<>="))))
        res["classes"][name] = dict(
            ap50=round(ap50, 4), gt=n_gt,
            recall=round(sum(v for (s, ok), v in fn_by["size"].items() if ok) / max(n_gt, 1), 4),
            by_size={s: dict(found=fn_by["size"][(s, True)], total=fn_by["size"][(s, True)] + fn_by["size"][(s, False)],
                             recall=round(fn_by["size"][(s, True)] / max(1, fn_by["size"][(s, True)] + fn_by["size"][(s, False)]), 3))
                     for s in sizes},
            by_source={s: dict(found=fn_by["source"][(s, True)], total=fn_by["source"][(s, True)] + fn_by["source"][(s, False)],
                               recall=round(fn_by["source"][(s, True)] / max(1, fn_by["source"][(s, True)] + fn_by["source"][(s, False)]), 3))
                       for s in sorted({k[0] for k in fn_by["source"]})},
            missed_by_kind=dict(fn_by["kind"]),
            false_pos_by_kind=dict(fp_kind),
            false_pos_total=sum(fp_kind.values()),
        )
    return res, z, fn_rows, fp_rows


def crop_sheet(rows, z, img_dir, path, n, seed, color):
    """Bảng ảnh cắt có ngữ cảnh: hộp (không gian capture) đổi về ảnh gốc qua ratio_pad."""
    if not rows:
        return 0
    rng = np.random.default_rng(seed)
    pick = rows if len(rows) <= n else [rows[k] for k in sorted(rng.choice(len(rows), n, replace=False))]
    tiles = []
    for r in pick:
        im = cv2.imread(str(img_dir / r["file"]))
        if im is None:
            continue
        gain, px, py = z["ratio_pad"][r["img_idx"]]
        x1, y1, x2, y2 = [(v - (px if k % 2 == 0 else py)) / gain for k, v in enumerate(r["box"])]
        w, h = x2 - x1, y2 - y1
        m = max(w, h) * 1.5 + 20
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        X1, Y1 = int(max(0, cx - m)), int(max(0, cy - m))
        X2, Y2 = int(min(im.shape[1], cx + m)), int(min(im.shape[0], cy + m))
        tile = im[Y1:Y2, X1:X2].copy()
        cv2.rectangle(tile, (int(x1 - X1), int(y1 - Y1)), (int(x2 - X1), int(y2 - Y1)), color, 2)
        tile = cv2.resize(tile, (200, 200))
        label = f"{r.get('conf', '')} {r['kind']} {r['source'][:6]}".strip()
        cv2.rectangle(tile, (0, 182), (200, 200), (0, 0, 0), -1)
        cv2.putText(tile, label[:30], (3, 196), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(tile)
    cols = 8
    while len(tiles) % cols:
        tiles.append(np.zeros((200, 200, 3), np.uint8))
    sheet = np.vstack([np.hstack(tiles[k:k + cols]) for k in range(0, len(tiles), cols)])
    cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return len(pick)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["error_analysis"]
    e04 = load_04e()
    for run in cfg["runs"]:
        if args.run and run["name"] != args.run:
            continue
        res, z, fn_rows, fp_rows = analyze(run, cfg, e04)
        out = OUT / run["name"]
        out.mkdir(parents=True, exist_ok=True)
        for fname, rows in (("fn.csv", fn_rows), ("fp.csv", fp_rows)):
            with open(out / fname, "w", newline="", encoding="utf-8") as fh:
                if rows:
                    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)
        img_dir = ROOT / run["images"]
        sheets = {}
        for name in run["classes"]:
            if name in ("helmet", "vest"):
                continue      # chỉ để đối chiếu số, không vẽ
            fn_c = [r for r in fn_rows if r["cls"] == name]
            big = sorted([r for r in fn_c if r["side"] >= cfg["size_bins_px"][1]], key=lambda r: -r["side"])
            sheets[f"{name}_bo_sot_lon"] = crop_sheet(big[:cfg["n_samples"]], z, img_dir, out / f"sheet_{name}_bo_sot_lon.jpg", cfg["n_samples"], cfg["seed"], (0, 0, 255))
            sheets[f"{name}_bo_sot_ngau_nhien"] = crop_sheet(fn_c, z, img_dir, out / f"sheet_{name}_bo_sot_ngau_nhien.jpg", cfg["n_samples"], cfg["seed"], (0, 0, 255))
            for kind in ("khong_ro", "vat_am"):
                fp_c = sorted([r for r in fp_rows if r["cls"] == name and r["kind"] == kind], key=lambda r: -r["conf"])
                sheets[f"{name}_thua_{kind}"] = crop_sheet(fp_c[:cfg["n_samples"]], z, img_dir, out / f"sheet_{name}_thua_{kind}.jpg", cfg["n_samples"], cfg["seed"], (0, 255, 255))
        res["sheets"] = sheets
        (out / "summary.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
