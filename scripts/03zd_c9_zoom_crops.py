"""C9 (kế hoạch docs/experiments/2026-11-16_c5_detector_plan.md, mục C9; người dùng đồng ý 20/11/2026): bộ phụ ảnh cắt
người ở độ phân giải gốc, để detector học găng, kính, ủng ở độ chi tiết như lượt zoom lúc chạy (`detector.zoom`, 04m).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03zd_c9_zoom_crops.py build --dry-run   # chỉ đếm
    python scripts/03zd_c9_zoom_crops.py build             # ghi data/ppe6/c9/zoom (ảnh zoom__*, nhãn, summary.json)
    python scripts/03zd_c9_zoom_crops.py pack              # c9_extra = c6_extra (bộ phụ của c6_ft) + zoom; gói Kaggle

Ảnh nguồn: train C5 (`data/ppe6/c5/dataset_c5`, đã che các vùng ignore), nhãn của train C5 (nhãn máy có kiểm định mẫu của
người, như các bước trước). Không đụng val, test, Pictor, video.
Vùng cắt như lúc chạy: hộp người (nhãn) nới `pad` mỗi cạnh; lấy khi cạnh dài ≥ `min_side` px ảnh gốc và ≤ `max_frac` cạnh dài
ảnh (người gần kín ảnh thì ảnh cắt không thêm chi tiết). Hộp bị mép ảnh cắt: phần còn thấy ≥ `min_visible_ppe` (lớp 1-5)
hoặc ≥ `min_visible_person` (người) thì giữ hộp đã cắt; lớp 1-5 thấy ít hơn thì che xám (114) phần còn thấy, người thấy ít
hơn thì bỏ nhãn. Mỗi ảnh tối đa `max_per_image` người, ưu tiên người có găng / kính / ủng trong vùng cắt; tổng tối đa
`max_crops`. Ảnh cắt lớn hơn `max_side` được thu về cạnh dài `max_side` (cách của 04_train). Tham số: configs/ppe6.yaml mục `c9`.
"""

import argparse
import json
import math
import os
import random
import shutil
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
import numpy as np  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
C5 = ROOT / "data" / "ppe6" / "c5" / "dataset_c5"
C6X = ROOT / "data" / "ppe6" / "c6" / "c6_extra"
OUT = ROOT / "data" / "ppe6" / "c9"
SMALL = (3, 4, 5)


def cfg():
    return yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["c9"]


def read_rows(path):
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        t = line.split()
        if t:
            out.append((int(t[0]), *map(float, t[1:5])))
    return out


def crop_labels(rows, w, h, box, c):
    """Nhãn trong vùng cắt box (x1, y1, x2, y2, px ảnh gốc). Trả về (hộp giữ [(lớp, x1, y1, x2, y2) px ảnh cắt], vùng che
    [(x1, y1, x2, y2) px ảnh cắt], số hộp bỏ theo lớp)."""
    X1, Y1, X2, Y2 = box
    keep, masks, dropped = [], [], Counter()
    for k, cx, cy, bw, bh in rows:
        x1, y1, x2, y2 = (cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h
        ix1, iy1, ix2, iy2 = max(x1, X1), max(y1, Y1), min(x2, X2), min(y2, Y2)
        if ix2 <= ix1 or iy2 <= iy1:
            continue
        vis = (ix2 - ix1) * (iy2 - iy1) / max((x2 - x1) * (y2 - y1), 1e-9)
        b = (ix1 - X1, iy1 - Y1, ix2 - X1, iy2 - Y1)
        if vis >= (c["min_visible_person"] if k == 0 else c["min_visible_ppe"]):
            keep.append((k, *b))
        elif k == 0:
            dropped[k] += 1
        else:
            masks.append(b)
            dropped[k] += 1
    return keep, masks, dropped


def candidates(c):
    """Mọi người đủ điều kiện trong train C5: (ảnh, chỉ số người, vùng cắt, có lớp nhỏ trong vùng)."""
    from PIL import Image

    out = []
    for p in sorted((C5 / "images" / "train").iterdir()):
        rows = read_rows(C5 / "labels" / "train" / (p.stem + ".txt"))
        persons = [r for r in rows if r[0] == 0]
        if not persons:
            continue
        with Image.open(p) as im:   # cỡ sau khi xoay EXIF, như Ultralytics
            w, h = im.size
            if im.getexif().get(274, 1) in (5, 6, 7, 8):
                w, h = h, w
        for j, (_, cx, cy, bw, bh) in enumerate(persons):
            x1, y1, x2, y2 = (cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h
            pw, ph = x2 - x1, y2 - y1
            box = (max(0.0, x1 - c["pad"] * pw), max(0.0, y1 - c["pad"] * ph), min(float(w), x2 + c["pad"] * pw), min(float(h), y2 + c["pad"] * ph))
            side = max(box[2] - box[0], box[3] - box[1])
            if side < c["min_side"] or side > c["max_frac"] * max(w, h):
                continue
            has_small = any(k in SMALL and box[0] <= (bx * w) <= box[2] and box[1] <= (by * h) <= box[3] for k, bx, by, _, _ in rows)
            out.append((p, j, box, has_small, (w, h)))
    return out


def cmd_build(args):
    import cv2
    from ultralytics.utils.patches import imread, imwrite   # cùng cách đọc (xoay EXIF) với Ultralytics

    c = cfg()
    rng = random.Random(c["seed"])
    cand = candidates(c)
    by_img = {}
    for x in cand:
        by_img.setdefault(x[0], []).append(x)
    chosen = []
    for p, xs in sorted(by_img.items()):
        rng.shuffle(xs)
        xs.sort(key=lambda x: not x[3])   # ưu tiên người có găng / kính / ủng trong vùng cắt (sort ổn định)
        chosen += xs[: c["max_per_image"]]
    rng.shuffle(chosen)
    chosen.sort(key=lambda x: not x[3])
    chosen = chosen[: c["max_crops"]]
    src = Counter(x[0].name.split("__")[0] for x in chosen)
    print(f"Ứng viên {len(cand)} người / {len(by_img)} ảnh; chọn {len(chosen)} (có lớp nhỏ {sum(x[3] for x in chosen)}); theo nguồn {dict(src)}")
    if args.dry_run:
        return
    out = OUT / "zoom"
    if out.exists():
        shutil.rmtree(out)
    (out / "images" / "train").mkdir(parents=True)
    (out / "labels" / "train").mkdir(parents=True)
    boxes, dropped, masked, files = Counter(), Counter(), 0, []
    for n, (p, j, box, _, (w, h)) in enumerate(sorted(chosen, key=lambda x: (x[0].name, x[1]))):
        im = imread(str(p))
        if im is None or im.shape[1] != w or im.shape[0] != h:
            sys.exit(f"Ảnh {p}: đọc được {None if im is None else im.shape[:2]}, cỡ theo EXIF {(h, w)}")
        X1, Y1, X2, Y2 = int(box[0]), int(box[1]), int(math.ceil(box[2])), int(math.ceil(box[3]))
        keep, masks, drop = crop_labels(read_rows(C5 / "labels" / "train" / (p.stem + ".txt")), w, h, (X1, Y1, X2, Y2), c)
        cr = im[Y1:Y2, X1:X2].copy()
        for b in masks:
            cr[int(b[1]):int(math.ceil(b[3])), int(b[0]):int(math.ceil(b[2]))] = (114, 114, 114)
        masked += len(masks)
        dropped.update(drop)
        ch, cw = cr.shape[:2]
        if max(ch, cw) > c["max_side"]:   # như writable_copy của 04_train (ceil, INTER_LINEAR)
            r = c["max_side"] / max(ch, cw)
            cr = cv2.resize(cr, (min(math.ceil(cw * r), c["max_side"]), min(math.ceil(ch * r), c["max_side"])), interpolation=cv2.INTER_LINEAR)
        name = f"zoom__{p.stem}__{j}"
        if not imwrite(str(out / "images" / "train" / f"{name}.jpg"), cr, [cv2.IMWRITE_JPEG_QUALITY, c["jpeg_quality"]]):
            sys.exit(f"Không ghi được {name}")
        (out / "labels" / "train" / f"{name}.txt").write_text("".join(
            f"{k} {(a + b2) / 2 / cw:.6f} {(b + d) / 2 / ch:.6f} {(b2 - a) / cw:.6f} {(d - b) / ch:.6f}\n" for k, a, b, b2, d in keep), encoding="utf-8")
        boxes.update(k for k, *_ in keep)
        files.append(dict(file=f"{name}.jpg", source=p.name, person=j, crop=[X1, Y1, X2, Y2]))
        if (n + 1) % 500 == 0:
            print(f"  {n + 1}/{len(chosen)}", flush=True)
    summ = dict(params=c, candidates=len(cand), source_images=len(by_img), crops=len(chosen), by_source=dict(src),
                boxes={str(k): v for k, v in sorted(boxes.items())}, dropped_or_masked={str(k): v for k, v in sorted(dropped.items())},
                masked_regions=masked, note="nhãn của train C5 (nhãn máy có kiểm định mẫu của người), cắt theo vùng người", files=files)
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Đã ghi {len(chosen)} ảnh cắt vào {out}; hộp {dict(sorted(boxes.items()))}; che {masked} vùng; bỏ / che theo lớp {dict(sorted(dropped.items()))}")


def cmd_pack(args):
    import zipfile

    c = cfg()
    zoom = OUT / "zoom"
    if not (zoom / "summary.json").exists():
        sys.exit("Chạy build trước")
    out = OUT / "c9_extra"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(C6X, out)
    shutil.rmtree(out / "weights")
    for kind in ("images", "labels"):
        for p in (zoom / kind / "train").iterdir():
            shutil.copy2(p, out / kind / "train" / p.name)
    (out / "weights").mkdir()
    shutil.copy2(ROOT / c["weights"], out / "weights" / "c6_ft_best.pt")
    summ = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    z = json.loads((zoom / "summary.json").read_text(encoding="utf-8"))
    summ["c9"] = {k: v for k, v in z.items() if k != "files"}
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    pack = ROOT / "data" / "ppe6" / "variants" / "kaggle" / "c9_extra_pack.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as zf:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                zf.write(p, "c9_extra/" + p.relative_to(out).as_posix())
    n_img = sum(1 for _ in (out / "images" / "train").iterdir())
    n_rep = sum(1 for x in (out / "oversample.txt").read_text(encoding="utf-8").split("\n") if x)
    print(f"c9_extra: {n_img} ảnh ({z['crops']} zoom), {n_rep} bản lặp (của c6_extra) | gói {pack.name} {pack.stat().st_size / 1e6:.0f} MB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--dry-run", action="store_true")
    sub.add_parser("pack")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    {"build": cmd_build, "pack": cmd_pack}[args.cmd](args)


if __name__ == "__main__":
    main()
