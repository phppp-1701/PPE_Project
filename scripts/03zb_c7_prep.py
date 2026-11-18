"""C7 (kế hoạch docs/experiments/2026-11-16_c5_detector_plan.md, mục C7, người dùng chọn phương án a 18/11/2026):
chuẩn bị dữ liệu train cho YOLO11m. Chỉ train; không sửa data/raw, val, test.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03zb_c7_prep.py pred         # c6_ft dự đoán ủng trên ảnh train (gốc C5 + bộ phụ C6, trừ ảnh cắt / thu nhỏ)
    python scripts/03zb_c7_prep.py candidates   # báo thừa ủng (conf >= c7.fp_conf, không trùng nhãn ủng) -> review_items_c7boots.csv
    python scripts/03z_c5_relabel.py sheets --task bootsfp_train_add ...   # bảng ảnh; Claude ghi .dec (g / n / u)
    python scripts/03z_c5_relabel.py collect
    python scripts/03zb_c7_prep.py pack         # bộ phụ C7 + gói data/ppe6/variants/kaggle/c7_extra_pack.zip

Ủng báo thừa (Claude xem, nhãn máy): g = thật ra là ủng / giày bảo hộ (thiếu nhãn) -> thêm nhãn lớp 5; n = giày thường /
vật khác (mẫu âm khó) -> ảnh được lặp thêm `c7.hard_neg_copies` lần để mô hình gặp nhiều hơn; u = không rõ -> che xám.
Sửa ảnh gốc của gói chính bằng cách đặt ảnh + nhãn **cùng tên** vào bộ phụ (04_train.py add_extra chép đè), nên gói chính
`c5_pack.zip` không đổi. Áo: ảnh SH17 train có áo được lặp thêm (`c7.vest_sh17_copies`), vì áo SH17 là chỗ hỏng chính (C7).
Tham số ở configs/ppe6.yaml mục `c7`.
"""

import argparse
import csv
import json
import os
import random
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
C5 = ROOT / "data" / "ppe6" / "c5"
MAIN = C5 / "dataset_c5"
C6X = ROOT / "data" / "ppe6" / "c6" / "c6_extra"
OUT = ROOT / "data" / "ppe6" / "c7"
FILL = (114, 114, 114)


def cfg():
    return yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["c7"]


def imread(p):
    return cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)


def yolo_rows(path):
    out = []
    if Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            t = line.split()
            if t:
                k, cx, cy, w, h = int(t[0]), *map(float, t[1:5])
                out.append([k, [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]])
    return out


def write_yolo(path, rows):
    Path(path).write_text("".join(
        f"{k} {(b[0] + b[2]) / 2:.6f} {(b[1] + b[3]) / 2:.6f} {b[2] - b[0]:.6f} {b[3] - b[1]:.6f}\n" for k, b in rows), encoding="utf-8")


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / max((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i, 1e-12)


def train_images():
    """(ảnh, nhãn) train: gốc C5 + ảnh nguyên của bộ phụ C6 (Construction-PPE mới, ủng ngoài); bỏ ảnh cắt / thu nhỏ."""
    out = [(p, MAIN / "labels" / "train" / (p.stem + ".txt")) for p in sorted((MAIN / "images" / "train").iterdir())]
    for p in sorted((C6X / "images" / "train").iterdir()):
        if p.name.split("__")[0] in ("cppe2", "vf", "nc"):
            out.append((p, C6X / "labels" / "train" / (p.stem + ".txt")))
    return out


def cmd_pred(args):
    from ultralytics import YOLO

    model = YOLO(str(ROOT / cfg()["weights"]))
    imgs = train_images()
    res = {}
    for i in range(0, len(imgs), 16):
        batch = imgs[i:i + 16]
        for (p, _), r in zip(batch, model.predict([str(p) for p, _ in batch], imgsz=960, conf=0.1, device=0, verbose=False, classes=[5])):
            res[p.name] = [(round(float(s), 4), [round(float(v), 5) for v in b]) for s, b in zip(r.boxes.conf.tolist(), r.boxes.xyxyn.tolist())]
        if (i // 16) % 100 == 0:
            print(f"{i + len(batch)}/{len(imgs)}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "c6ft_train_boots_pred.json").write_text(json.dumps(res), encoding="utf-8")


def cmd_candidates(args):
    c = cfg()
    pred = json.loads((OUT / "c6ft_train_boots_pred.json").read_text(encoding="utf-8"))
    items = []
    for p, lab in train_images():
        gt = [b for k, b in yolo_rows(lab) if k == 5]
        for s, b in pred.get(p.name, []):
            if s >= c["fp_conf"] and all(iou(b, g) < c["match_iou"] for g in gt):
                items.append(dict(task="bootsfp_train_add", set="train", file=p.name, img=p.relative_to(ROOT).as_posix(),
                                  target=" ".join(f"{v:.5f}" for v in b), sugg="[]", meta=json.dumps(dict(conf=s, label=lab.relative_to(ROOT).as_posix()))))
    random.Random(c["seed"]).shuffle(items)
    for i, it in enumerate(items):
        it["item"] = f"b{i:05d}"
    with open(C5 / "review_items_c7boots.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["item", "task", "set", "file", "img", "target", "sugg", "meta"])
        w.writeheader()
        w.writerows(items)
    print(len(items), "ô", Counter(it["file"].split("__")[0] for it in items))


def cmd_pack(args):
    c = cfg()
    dec = {r["item"]: r["decision"] for r in csv.DictReader(open(C5 / "machine_pass_claude.csv", encoding="utf-8"))}
    items = [r for r in csv.DictReader(open(C5 / "review_items_c7boots.csv", encoding="utf-8"))]
    miss = [it["item"] for it in items if it["item"] not in dec]
    if miss:
        sys.exit(f"Còn {len(miss)} ô chưa có quyết định")
    out = OUT / "c7_extra"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(C6X, out)
    shutil.rmtree(out / "weights", ignore_errors=True)       # C7-m train từ yolo11m.pt (COCO), không cần trọng số C5
    by_img = {}
    for it in items:
        by_img.setdefault(it["img"], []).append(it)
    stat, hard_neg, log = Counter(), [], []
    for img, its in by_img.items():
        src, lab = ROOT / img, ROOT / json.loads(its[0]["meta"])["label"]
        rows = yolo_rows(lab)
        masks, changed = [], False
        for it in its:
            v = dec[it["item"]]
            b = [float(x) for x in it["target"].split()]
            stat[v] += 1
            log.append((it["file"], it["item"], v, it["target"]))
            if v == "g":
                rows.append([5, b])
                changed = True
            elif v == "u":
                masks.append(b)
                changed = True
        if any(dec[it["item"]] == "n" for it in its):
            hard_neg.append(src.name)
        if changed:   # ảnh + nhãn cùng tên trong bộ phụ: 04_train add_extra chép đè lên ảnh gốc
            im = imread(src)
            h, w = im.shape[:2]
            for b in masks:
                im[max(int(b[1] * h), 0):int(np.ceil(b[3] * h)), max(int(b[0] * w), 0):int(np.ceil(b[2] * w))] = FILL
            dst = out / "images" / "train" / src.name
            if dst.exists():
                dst.unlink()
            ok, buf = cv2.imencode(Path(src.name).suffix or ".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 92])
            buf.tofile(str(dst))
            write_yolo(out / "labels" / "train" / (src.stem + ".txt"), rows)
            stat["anh_sua"] += 1
    vest_sh17 = [p.name for p, lab in train_images() if p.name.startswith("sh17__") and any(k == 2 for k, _ in yolo_rows(lab))]
    rep = [x for x in (C6X / "oversample.txt").read_text(encoding="utf-8").split() if x]
    extra_rep = hard_neg * c["hard_neg_copies"] + vest_sh17 * c["vest_sh17_copies"]   # tên lặp = thêm bản (04_train add_extra)
    (out / "oversample.txt").write_text("".join(x + "\n" for x in rep + extra_rep), encoding="utf-8")
    with open(OUT / "changes_c7.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "item", "decision", "box"])
        w.writerows(log)
    summ = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    summ["c7"] = dict(boots_fp_review=dict(stat), hard_neg_images=len(hard_neg), vest_sh17_images=len(vest_sh17),
                      extra_oversample=len(extra_rep), params=c)
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    pack = ROOT / "data" / "ppe6" / "variants" / "kaggle" / "c7_extra_pack.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, "c7_extra/" + p.relative_to(out).as_posix())
    print(summ["c7"], f"| gói {pack.name} {pack.stat().st_size / 1e6:.1f} MB")


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["pred", "candidates", "pack"])
    args = ap.parse_args()
    dict(pred=cmd_pred, candidates=cmd_candidates, pack=cmd_pack)[args.cmd](args)


if __name__ == "__main__":
    main()
