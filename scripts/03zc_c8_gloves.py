"""C8 (kế hoạch docs/experiments/2026-11-16_c5_detector_plan.md, mục C8, người dùng chọn phương án a 19/11/2026):
găng. Chỉ đề xuất ô cho Claude xem; quyết định ghi bằng 03z (`sheets`, `.dec`, `collect`).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03zc_c8_gloves.py pred-train      # c6_ft dự đoán găng trên ảnh train (gốc C5 + ảnh nguyên bộ phụ C7)
    python scripts/03zc_c8_gloves.py pred-test       # test: chỉ predict (không tính điểm) của C4-C7, làm vị trí ứng viên
    python scripts/03zc_c8_gloves.py candidates      # review_items_c8.csv: (1) train: găng báo thừa -> gloves8_train_add;
                                                     # (2) val, test: găng báo thừa của C4-C7 (gộp) -> gloves8_eval_add
    python scripts/03z_c5_relabel.py sheets --task gloves8_train_add ...;  ... --task gloves8_eval_add ...
    python scripts/03z_c5_relabel.py collect

Mã: g = hộp bao sát đúng MỘT chiếc găng (tiêu chí chặt, sau kiểm định lần 1); n = không phải găng (tay trần, dụng cụ, vật
khác) -> train: mẫu âm khó; u = không rõ / hộp không đạt -> che (train) hoặc ignore (val, test).
Val, test: ứng viên gộp từ dự đoán của **mọi** bản C4, C5-s960, C6-ft, C7-m (conf >= c8.eval_conf), cùng hộp gộp theo IoU,
để nhãn mới không nghiêng về một mô hình; ô đã có quyết định ở lượt trước (gloves_eval_add) vẫn được xem lại theo tiêu chí
chặt. Tham số ở configs/ppe6.yaml mục `c8`.
"""

import argparse
import csv
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
import numpy as np  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
C5 = ROOT / "data" / "ppe6" / "c5"
OUT = ROOT / "data" / "ppe6" / "c8"
sys.path.insert(0, str(ROOT / "scripts"))


def cfg():
    return yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["c8"]


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / max((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i, 1e-12)


def yolo_rows(path):
    out = []
    if Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            t = line.split()
            if t:
                k, cx, cy, w, h = int(t[0]), *map(float, t[1:5])
                out.append((k, [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]))
    return out


def train_images():
    main = C5 / "dataset_c5"
    c7x = ROOT / "data" / "ppe6" / "c7" / "c7_extra"
    over = {p.name for p in (c7x / "images" / "train").iterdir()}
    out = []
    for p in sorted((main / "images" / "train").iterdir()):
        if p.name in over:   # ảnh đã sửa ở C7 (bộ phụ thay ảnh gốc)
            out.append((ROOT / "data" / "ppe6" / "c7" / "c7_extra" / "images" / "train" / p.name, c7x / "labels" / "train" / (p.stem + ".txt")))
        else:
            out.append((p, main / "labels" / "train" / (p.stem + ".txt")))
    for p in sorted((c7x / "images" / "train").iterdir()):
        if p.name.split("__")[0] in ("cppe2", "vf", "nc"):
            out.append((p, c7x / "labels" / "train" / (p.stem + ".txt")))
    return out


def cmd_pred_train(args):
    from ultralytics import YOLO

    model = YOLO(str(ROOT / cfg()["weights"]))
    imgs = train_images()
    res = {}
    for i in range(0, len(imgs), 16):
        batch = imgs[i:i + 16]
        for (p, _), r in zip(batch, model.predict([str(p) for p, _ in batch], imgsz=960, conf=0.1, device=0, verbose=False, classes=[3])):
            res[p.name] = [(round(float(s), 4), [round(float(v), 5) for v in b]) for s, b in zip(r.boxes.conf.tolist(), r.boxes.xyxyn.tolist())]
        if (i // 16) % 100 == 0:
            print(f"{i + len(batch)}/{len(imgs)}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "c6ft_train_gloves_pred.json").write_text(json.dumps(res), encoding="utf-8")


def cmd_pred_test(args):
    """Test: chỉ chạy predict (không tính điểm, không xem số) của các bản trong c8.test_weights trên ảnh ppe4 test của
    c5/eval/test, lưu găng conf >= eval_conf -> c8/test_gloves_pred.json. Chỉ dùng làm vị trí ứng viên cho Claude xem."""
    from ultralytics import YOLO

    c = cfg()
    ev = C5 / "eval" / "test" / "images"
    ppe4 = {q.name for q in (ROOT / "data" / "ppe4" / "dataset" / "images" / "test").iterdir()}
    imgs = [p for p in sorted(ev.iterdir()) if p.name in ppe4]
    res = {}
    for w in c["test_weights"]:
        model = YOLO(str(ROOT / w))
        for i in range(0, len(imgs), 16):
            batch = imgs[i:i + 16]
            for p, r in zip(batch, model.predict([str(p) for p in batch], imgsz=960, conf=c["eval_conf"], device=0, verbose=False, classes=[3])):
                res.setdefault(p.name, []).extend((round(float(s_), 4), [round(float(v), 5) for v in b]) for s_, b in zip(r.boxes.conf.tolist(), r.boxes.xyxyn.tolist()))
        print("xong", w, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "test_gloves_pred.json").write_text(json.dumps(res), encoding="utf-8")


def eval_preds(c):
    """{(split, file): [(conf, hộp chuẩn hóa)]} găng của mọi capture val / test của C4-C7 (04d), conf >= eval_conf."""
    out = {}
    for cap in c["eval_captures"]:
        d = ROOT / cap
        if not (d / "capture.npz").exists():
            print("Bỏ qua (chưa có capture):", cap)
            continue
        z = np.load(d / "capture.npz")
        split = "test" if "_test" in cap else "val"
        files = z["files"].tolist()
        for k in np.nonzero((z["cls"] == 3) & (z["conf"] >= c["eval_conf"]))[0]:
            i = int(z["img"][k])
            oh, ow = z["ori"][i]
            g, px, py = z["ratio_pad"][i]
            x1, y1, x2, y2 = z["box"][k]
            b = [max((x1 - px) / g / ow, 0), max((y1 - py) / g / oh, 0), min((x2 - px) / g / ow, 1), min((y2 - py) / g / oh, 1)]
            out.setdefault((split, files[i]), []).append((float(z["conf"][k]), b))
    tp = OUT / "test_gloves_pred.json"
    if tp.exists():
        for f, ps in json.loads(tp.read_text(encoding="utf-8")).items():
            out.setdefault(("test", f), []).extend((s_, b) for s_, b in ps)
    else:
        print("Chưa có test_gloves_pred.json (03zc pred-test): bỏ qua test")
    return out


def cmd_candidates(args):
    c = cfg()
    items = []
    pred = json.loads((OUT / "c6ft_train_gloves_pred.json").read_text(encoding="utf-8"))
    for p, lab in train_images():
        gt = [b for k, b in yolo_rows(lab) if k == 3]
        for s, b in pred.get(p.name, []):
            if s >= c["train_conf"] and all(iou(b, g) < c["match_iou"] for g in gt):
                items.append(dict(task="gloves8_train_add", set="train", file=p.name, img=p.relative_to(ROOT).as_posix(),
                                  target=" ".join(f"{v:.5f}" for v in b), sugg="[]", meta=json.dumps(dict(conf=s, label=lab.relative_to(ROOT).as_posix()))))
    ev = C5 / "eval"
    files = json.loads((ev / "files.json").read_text(encoding="utf-8"))
    ppe4 = {s: {q.name for q in (ROOT / "data" / "ppe4" / "dataset" / "images" / s).iterdir()} for s in ("val", "test")}
    for (split, f), preds in sorted(eval_preds(c).items()):
        if f not in ppe4[split] or f not in files[split]["all"]:
            continue
        gt = [b for k, b in yolo_rows(ev / split / "labels" / (Path(f).stem + ".txt")) if k == 3]
        keep = []
        for s, b in sorted(preds, key=lambda x: -x[0]):
            if all(iou(b, g) < c["match_iou"] for g in gt) and all(iou(b, q) < c["merge_iou"] for _, q in keep):
                keep.append((s, b))
        for s, b in keep:
            items.append(dict(task="gloves8_eval_add", set=split, file=f, img=(ev / split / "images" / f).relative_to(ROOT).as_posix(),
                              target=" ".join(f"{v:.5f}" for v in b), sugg="[]", meta=json.dumps(dict(conf=s))))
    rng = random.Random(c["seed"])
    rng.shuffle(items)
    for i, it in enumerate(items):
        it["item"] = f"g{i:05d}"
    with open(C5 / "review_items_c8.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["item", "task", "set", "file", "img", "target", "sugg", "meta"])
        w.writeheader()
        w.writerows(items)
    print(len(items), "ô", Counter((it["task"], it["set"]) for it in items))


def cmd_pack(args):
    """Bộ phụ C8 = bộ phụ C7 + ảnh găng ngoài (data/ppe6/c8/ext, 03za --section c8_ext) + quyết định của Claude trên găng
    báo thừa ở train (gloves8_train_add): g -> thêm nhãn găng, u -> che xám (ảnh cùng tên thay ảnh gốc), n -> mẫu âm khó lặp
    `hard_neg_copies` lần; ảnh găng ngoài lặp thêm 1 lần. Gói data/ppe6/variants/kaggle/c8_extra_pack.zip, kèm trọng số c6_ft
    để tinh chỉnh."""
    import shutil
    import zipfile

    import cv2

    c = cfg()
    c7x = ROOT / "data" / "ppe6" / "c7" / "c7_extra"
    out = OUT / "c8_extra"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(c7x, out)
    ext = OUT / "ext"
    n_ext = 0
    if (ext / "images" / "train").exists():
        for p in sorted((ext / "images" / "train").iterdir()):
            shutil.copy2(p, out / "images" / "train" / p.name)
            shutil.copy2(ext / "labels" / "train" / (p.stem + ".txt"), out / "labels" / "train" / (p.stem + ".txt"))
            n_ext += 1
    else:
        print("Chưa có ảnh găng ngoài (03za --section c8_ext): gói chỉ có mẫu âm khó")
    dec = {r["item"]: r["decision"] for r in csv.DictReader(open(C5 / "machine_pass_claude.csv", encoding="utf-8"))}
    items = [r for r in csv.DictReader(open(C5 / "review_items_c8.csv", encoding="utf-8")) if r["task"] == "gloves8_train_add"]
    by_img, stat = {}, Counter()
    for it in items:
        by_img.setdefault(it["img"], []).append(it)
    hard = []
    for img, its in by_img.items():
        src, lab = ROOT / img, ROOT / json.loads(its[0]["meta"])["label"]
        rows = [[k, b] for k, b in yolo_rows(lab)]
        masks, changed = [], False
        for it in its:
            v = dec.get(it["item"])
            stat[v] += 1
            b = [float(x) for x in it["target"].split()]
            if v == "g":
                rows.append([3, b]); changed = True
            elif v == "u":
                masks.append(b); changed = True
        if any(dec.get(it["item"]) == "n" for it in its):
            hard.append(src.name)
        if changed:
            im = cv2.imdecode(np.fromfile(str(src), dtype=np.uint8), cv2.IMREAD_COLOR)
            h, w = im.shape[:2]
            for b in masks:
                im[max(int(b[1] * h), 0):int(np.ceil(b[3] * h)), max(int(b[0] * w), 0):int(np.ceil(b[2] * w))] = (114, 114, 114)
            dst = out / "images" / "train" / src.name
            if dst.exists():
                dst.unlink()
            cv2.imencode(Path(src.name).suffix or ".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tofile(str(dst))
            (out / "labels" / "train" / (src.stem + ".txt")).write_text("".join(
                f"{k} {(b[0] + b[2]) / 2:.6f} {(b[1] + b[3]) / 2:.6f} {b[2] - b[0]:.6f} {b[3] - b[1]:.6f}\n" for k, b in rows), encoding="utf-8")
            stat["anh_sua"] += 1
    ext_names = sorted(p.name for p in (ext / "images" / "train").iterdir()) if (ext / "images" / "train").exists() else []
    rep = [x for x in (c7x / "oversample.txt").read_text(encoding="utf-8").split() if x]
    rep += hard * c["hard_neg_copies"] + ext_names
    (out / "oversample.txt").write_text("".join(x + "\n" for x in rep), encoding="utf-8")
    (out / "weights").mkdir(exist_ok=True)
    shutil.copy2(ROOT / c["weights"], out / "weights" / "c6_ft_best.pt")
    summ = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    summ["c8"] = dict(gloves_train_review=dict(stat), hard_neg_images=len(hard), ext_images=n_ext, oversample_total=len(rep))
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    pack = ROOT / "data" / "ppe6" / "variants" / "kaggle" / "c8_extra_pack.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, "c8_extra/" + p.relative_to(out).as_posix())
    print(summ["c8"], f"| gói {pack.name} {pack.stat().st_size / 1e6:.1f} MB")


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["pred-train", "pred-test", "candidates", "pack"])
    args = ap.parse_args()
    dict(**{"pred-train": cmd_pred_train, "pred-test": cmd_pred_test, "candidates": cmd_candidates, "pack": cmd_pack})[args.cmd](args)


if __name__ == "__main__":
    main()
