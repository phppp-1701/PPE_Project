"""Thử nghiệm 6 lớp: bộ dữ liệu phân loại ảnh cắt bộ phận (bước kiểm tra thứ hai cho găng, ủng, kính).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03y_ppe6_part_crops.py

Ghi data/ppe6/parts/{train,val}/<lớp>/*.jpg (định dạng thư mục của YOLO-cls), summary.json và gói
data/ppe6/variants/kaggle/parts_pack.zip. Tham số ở configs/ppe6.yaml mục `parts`. Không sửa data/raw.

Lớp (7): glove, bare_hand (tay); safety_boot, not_safety_foot (giày thường, dép, chân trần) (chân);
goggles, ordinary_glasses, no_eyewear (mắt).
Nguồn nhãn:
- SH17 (VOC gốc): gloves -> glove; hands không trùng găng -> bare_hand; foot -> not_safety_foot;
  face không chứa hộp glasses nào -> no_eyewear.
- Giày, kính của SH17 và Construction-PPE cũ: quyết định hiệu lực của project (người > nhãn máy bản 3 > agent),
  safety -> safety_boot / goggles; ordinary -> not_safety_foot / ordinary_glasses; unclear và kính không đeo bị bỏ.
- Construction-PPE cũ, bản mới: no_gloves -> bare_hand, no_boots -> not_safety_foot, no_goggle -> no_eyewear;
  găng -> glove; Construction-PPE bản mới: boots từ min_boot_px -> safety_boot, goggles -> goggles.
Chia: train = ảnh ppe4 train không thuộc cảnh đánh giá + Construction-PPE bản mới (không trùng cảnh đánh giá);
val = ảnh ppe4 val không cùng cảnh với ảnh train nào và không thuộc cảnh test_new. ppe4 test, Pictor, video không dùng.
"""

import csv
import json
import random
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.machine_labels import human_box_labels, train_boot_override  # noqa: E402

OUT = ROOT / "data" / "ppe6" / "parts"
PACK = ROOT / "data" / "ppe6" / "variants" / "kaggle" / "parts_pack.zip"
REVIEW = ROOT / "data" / "ppe6" / "review"


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def ioa(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max((a[2] - a[0]) * (a[3] - a[1]), 1e-9)


def yolo_boxes(path, w, h):
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        t = line.split()
        if t:
            c, cx, cy, bw, bh = int(t[0]), *map(float, t[1:5])
            out.append((c, [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h]))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    pc, cppe2_cfg = cfg["parts"], cfg["cppe2"]
    rng = random.Random(pc["seed"])
    stats = rd(ROOT / "data" / "ppe4" / "stats.csv")
    scene = {r["file"]: r["scene_id"] for r in rd(ROOT / "data" / "ppe6" / "scene" / "scene_ids.csv")}
    roles = {r["scene_id"]: r["role"] for r in rd(ROOT / "data" / "ppe6" / "eval" / "scene_roles.csv")}
    train_scenes = {scene[r["file"]] for r in stats if r["split"] == "train"}
    split = {}
    for r in stats:
        s = scene.get(r["file"])
        if r["source"] not in ("sh17", "construction_ppe") or s is None:
            continue
        if r["split"] == "train" and s not in roles:
            split[r["image"]] = ("train", r["file"])
        elif r["split"] == "val" and s not in train_scenes and roles.get(s) != "test_new":
            split[r["image"]] = ("val", r["file"])

    # Quyết định hiệu lực cho giày, kính (boxes.csv)
    dec = {r["box_id"]: (r["label"], r["note"]) for r in rd(REVIEW / "decisions_v2.csv")}
    for k, (lab, _) in train_boot_override(REVIEW).items():
        dec[k] = (lab, "")
    for k, r in human_box_labels(REVIEW).items():
        dec[k] = (r["after"], "")
    by_img = defaultdict(list)   # ảnh gốc -> [(lớp đích, hộp chuẩn hóa)]
    for b in rd(REVIEW / "boxes.csv"):
        lab, note = dec.get(b["box_id"], ("", ""))
        if note == "not_worn":
            continue
        cls = {("boots", "safety"): "safety_boot", ("boots", "ordinary"): "not_safety_foot",
               ("goggles", "safety"): "goggles", ("goggles", "ordinary"): "ordinary_glasses"}.get((b["target"], lab))
        if cls:
            by_img[b["image"]].append((cls, tuple(float(b[k]) for k in ("cx", "cy", "w", "h"))))

    items = []   # (phần, lớp, đường dẫn ảnh, hộp pixel, nguồn)
    for img, (part, _) in split.items():
        p = ROOT / img
        im = cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)
        if im is None:
            continue
        h, w = im.shape[:2]
        for cls, (cx, cy, bw, bh) in by_img.get(img, []):
            items.append((part, cls, img, [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h], "decision"))
        if img.startswith("data/raw/sh17/"):
            voc = ROOT / "data" / "raw" / "sh17" / "voc_labels" / (Path(img).stem + ".xml")
            obj = defaultdict(list)
            for o in ET.parse(voc).getroot().iter("object"):
                bb = o.find("bndbox")
                obj[o.find("name").text].append([float(bb.find(k).text) for k in ("xmin", "ymin", "xmax", "ymax")])
            for g in obj["gloves"]:
                items.append((part, "glove", img, g, "sh17"))
            for hd in obj["hands"]:
                if not any(ioa(hd, g) > 0.5 for g in obj["gloves"]):
                    items.append((part, "bare_hand", img, hd, "sh17"))
            for f in obj["foot"]:
                items.append((part, "not_safety_foot", img, f, "sh17"))
            for fc in obj["face"]:
                if not any(ioa(gl, fc) > 0.3 for gl in obj["glasses"]):
                    items.append((part, "no_eyewear", img, fc, "sh17"))
        else:
            lab = ROOT / img.replace("/images/", "/labels/").rsplit(".", 1)[0]
            m = {1: "glove", 9: "bare_hand", 10: "not_safety_foot", 8: "no_eyewear"}
            for c, bx in yolo_boxes(str(lab) + ".txt", w, h):
                if c in m:
                    items.append((part, m[c], img, bx, "cppe1"))
    # Construction-PPE bản mới: chỉ train, bỏ ảnh trùng cảnh đánh giá
    raw2 = ROOT / "data" / "raw" / "construction_ppe_v2"
    names2 = yaml.safe_load((raw2 / "data.yaml").read_text(encoding="utf-8"))["names"]
    bad = set((ROOT / "data" / "ppe6" / "external" / "cppe2" / "eval_overlap.txt").read_text(encoding="utf-8").split())
    m2 = {"gloves": "glove", "no_gloves": "bare_hand", "no_boots": "not_safety_foot", "no_goggle": "no_eyewear", "goggles": "goggles", "boots": "safety_boot"}
    for lab in sorted((raw2 / "labels").rglob("*.txt")):
        img = next((raw2 / "images" / lab.parent.name).glob(lab.stem + ".*"))
        if "cppe2__" + img.name in bad:
            continue
        im = cv2.imdecode(np.fromfile(str(img), dtype=np.uint8), cv2.IMREAD_COLOR)
        h, w = im.shape[:2]
        s = min(1.0, cppe2_cfg["side"] / max(h, w))
        for c, bx in yolo_boxes(lab, w, h):
            cls = m2.get(names2[c])
            if cls == "safety_boot" and max(bx[2] - bx[0], bx[3] - bx[1]) * s < cppe2_cfg["min_boot_px"]:
                continue
            if cls:
                items.append(("train", cls, img.relative_to(ROOT).as_posix(), bx, "cppe2"))

    # Giới hạn số ảnh mỗi lớp ở train để không lệch quá
    rng.shuffle(items)
    keep, per = [], Counter()
    for it in items:
        k = (it[0], it[1])
        if it[0] == "train" and per[k] >= pc["max_per_class"]:
            continue
        per[k] += 1
        keep.append(it)
    if OUT.exists():
        shutil.rmtree(OUT)
    done, skipped = Counter(), Counter()
    cache = {}
    for i, (part, cls, img, bx, src) in enumerate(sorted(keep, key=lambda x: x[2])):
        if img not in cache:
            cache.clear()
            cache[img] = cv2.imdecode(np.fromfile(str(ROOT / img), dtype=np.uint8), cv2.IMREAD_COLOR)
        im = cache[img]
        h, w = im.shape[:2]
        side = max(bx[2] - bx[0], bx[3] - bx[1]) * pc["context"]
        if side < pc["min_px"]:
            skipped["small"] += 1
            continue
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        a, b = int(max(cx - side / 2, 0)), int(max(cy - side / 2, 0))
        crop = im[b:int(min(cy + side / 2, h)), a:int(min(cx + side / 2, w))]
        if min(crop.shape[:2]) < pc["min_px"] // 2:
            skipped["edge"] += 1
            continue
        if max(crop.shape[:2]) > pc["save_px"]:
            f = pc["save_px"] / max(crop.shape[:2])
            crop = cv2.resize(crop, (round(crop.shape[1] * f), round(crop.shape[0] * f)), interpolation=cv2.INTER_AREA)
        d = OUT / part / cls
        d.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(d / f"{src}_{i:06d}.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
        done[(part, cls)] += 1
    summ = dict(counts={f"{p}/{c}": n for (p, c), n in sorted(done.items())}, skipped=dict(skipped), params=pc)
    (OUT / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    PACK.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PACK, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                z.write(p, "parts/" + p.relative_to(OUT).as_posix())
    print(json.dumps(summ["counts"], ensure_ascii=False), summ["skipped"], f"| gói {PACK.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
