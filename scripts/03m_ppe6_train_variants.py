"""Thử nghiệm 6 lớp: tạo các phiên bản train C1, C2 từ C0 (data/ppe6/dataset). Không sửa ppe4, C0 hay tập đánh giá.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv, sau 03i):
    python scripts/03m_ppe6_train_variants.py            # sinh C1, C2, bảng so sánh, gói Kaggle
    python scripts/03m_ppe6_train_variants.py --check    # chỉ kiểm tra

C0: train hiện tại. C1: C0 + ảnh CHV thuộc train ppe4, nhãn 4 lớp của nhóm + hộp kính CHVG đã duyệt theo định nghĩa 2.
C2: C1 + ảnh train từng bị loại vì kính, giày không rõ, nay che vùng đó trên bản sao ảnh. Nếu che mất hơn `mask.max_cover` một hộp
đã gán nhãn thì vẫn loại ảnh. Ảnh trùng cảnh với tập đánh giá bị bỏ khỏi train. Cảnh lặp vẫn giữ tối đa `train_scene_cap` ảnh.

Ghi data/ppe6/dataset_<c1,c2>/: images/train (liên kết cứng, ảnh che là file mới), labels/train, images/val_monitor, labels/val_monitor,
data.yaml, manifest.json, mask_map.csv (ảnh gốc, ảnh che, vùng che). data/ppe6/variants/: loss_table.csv, compare.csv, chv_merge.csv,
kaggle/<c>_pack.zip. `val_monitor` chỉ để theo dõi khi train, không dùng báo cáo: ảnh ppe4 val và val_new có cảnh không ở train đó.
"""

import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.machine_labels import train_boot_override  # noqa: E402
from ppe.ppe6_data import (NEW_CLASS, SAFE, blocks_train, box_iou_xyxy, check_label_rows, check_leaks, cover_fraction, mask_decision, merge_glass_status, parse_yolo)  # noqa: E402

BASE = ROOT / "data" / "ppe6"
C0 = BASE / "dataset"
PPE4 = ROOT / "data" / "ppe4" / "dataset"
VAR = BASE / "variants"
CHVG = BASE / "external" / "chvg"
OLD = ("person", "helmet", "vest", "gloves")
NAMES = ["person", "helmet", "vest", "gloves", "goggles", "boots"]
HELMET = {"white", "yellow", "blue", "red"}


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8")))


def wr(p, rows, keys=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    keys = keys or list(rows[0])
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, keys, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def load():
    stats = {r["file"]: r for r in rd(ROOT / "data" / "ppe4" / "stats.csv") if r["split"] != "external_test"}
    scene = {r["file"]: r["scene_id"] for r in rd(BASE / "scene" / "scene_ids.csv")}
    roles = {r["scene_id"]: r["role"] for r in rd(BASE / "eval" / "scene_roles.csv")}
    dec = {r["box_id"]: r for r in rd(BASE / "review" / "decisions_v2.csv")}
    for k, (lab, _src) in train_boot_override(BASE / "review").items():   # ủng train bản 3, như 03i
        dec[k] = dict(dec[k], label=lab, note="")
    by_image = {r["image"]: r["file"] for r in stats.values()}
    boxes = defaultdict(list)
    for b in rd(BASE / "review" / "boxes.csv"):
        if b["image"] in by_image:
            d = dec[b["box_id"]]
            boxes[by_image[b["image"]]].append(dict(b, label=d["label"], note=d["note"]))
    return stats, scene, roles, boxes


def counts(files, stats):
    c = Counter(images=len(files))
    for f in files:
        for k in OLD:
            c[k] += int(stats[f]["n_" + k])
    return c


def loss_table(stats, scene, roles, boxes, cap_dropped):
    """Mỗi ảnh ppe4 train một lý do chính, thứ tự: CHV, hộp không rõ, giới hạn cảnh, chuyển sang đánh giá, khác."""
    c0 = {p.name for p in (C0 / "images" / "train").iterdir()}
    reason = {}
    for f, r in stats.items():
        if r["split"] != "train":
            continue
        if f in c0:
            reason[f] = "keep"
        elif r["source"] == "chv":
            reason[f] = "bo_chv"
        elif any(blocks_train(b["label"], b["note"], b["target"]) for b in boxes[f]):
            reason[f] = "hop_khong_ro"
        elif f in cap_dropped:
            reason[f] = "gioi_han_canh"
        elif scene[f] in roles:
            reason[f] = "chuyen_danh_gia"
        else:
            reason[f] = "khac"
    rows = []
    groups = defaultdict(list)
    for f, k in reason.items():
        groups[k].append(f)
    total = counts(list(reason), stats)
    rows.append(dict(step="ppe4_train", **{k: total[k] for k in ("images",) + OLD}))
    for k in ("bo_chv", "hop_khong_ro", "gioi_han_canh", "chuyen_danh_gia", "khac"):
        c = counts(groups[k], stats)
        rows.append(dict(step=k, **{x: -c[x] for x in ("images",) + OLD}))
    c = counts(groups["keep"], stats)
    rows.append(dict(step="c0", **{x: c[x] for x in ("images",) + OLD}))
    wr(VAR / "loss_table.csv", rows)
    return rows, reason


def merge_chv(stats, scene, roles, cfg):
    """Ghép kính CHVG vào ảnh CHV train. Trả về {file ppe4: [hộp kính]}, bảng kiểm tra từng ảnh."""
    match = {r["file"]: r for r in rd(CHVG / "chv_match.csv")}
    unclear = set(cfg["chv_merge"]["unclear"].split())
    glass = defaultdict(list)
    for r in rd(CHVG / "glass_order.csv"):
        glass[re.sub(r"_jpg\.rf\..*", "", r["file"].replace("chvg__", ""))].append(r)
    src = defaultdict(list)
    images = {re.sub(r"_jpg\.rf\..*", "", r["file"].replace("chvg__", "")): r["file"] for r in rd(CHVG / "images.csv")}
    for r in rd(CHVG / "boxes.csv"):
        src[r["file"]].append(r)
    out, table = {}, []
    for f, r in sorted(stats.items()):
        if r["source"] != "chv" or r["split"] != "train":
            continue
        s = Path(f).stem.replace("chv__", "")
        m = match.get(f)
        if m is None or m["match"] != "name" or s not in images:
            table.append(dict(file=f, status="no_chvg", corr="", ham="", helmet_median_iou="", glass=0))
            out[f] = []
            continue
        gt = [(c, x - w / 2, y - h / 2, x + w / 2, y + h / 2) for c, x, y, w, h in parse_yolo((PPE4 / "labels" / "train" / f"{Path(f).stem}.txt").read_text(encoding="utf-8"))]
        hel = [q[1:] for q in gt if q[0] == 1]
        ious = []
        for q in src[images[s]]:
            if q["cls"] in HELMET:
                b = tuple(float(q[k]) / 640 for k in ("x1", "y1", "x2", "y2"))
                ious.append(max([box_iou_xyxy(b, h) for h in hel], default=0.0))
        med = float(np.median(ious)) if ious else None
        status = merge_glass_status(float(m["corr"]), int(m["ham"]), med, cfg["chv_merge"])
        boxes = []
        if status == "ok":
            for q in glass.get(s, []):
                x1, y1, x2, y2 = (float(q[k]) / 640 for k in ("x1", "y1", "x2", "y2"))
                boxes.append(dict(box_id=f"g{int(q['idx']):05d}", target="goggles", cx=(x1 + x2) / 2, cy=(y1 + y2) / 2, w=x2 - x1, h=y2 - y1,
                                  label="unclear" if q["idx"] in unclear else SAFE, note=""))
        out[f] = boxes
        table.append(dict(file=f, status=status, corr=m["corr"], ham=m["ham"], helmet_median_iou="" if med is None else round(med, 3), glass=len(boxes)))
    wr(VAR / "chv_merge.csv", table)
    return out, table


def old_lines(r):
    return [x for x in (PPE4 / "labels" / r["split"] / f"{Path(r['file']).stem}.txt").read_text(encoding="utf-8").splitlines() if x.strip()]


def yline(cls, b):
    x1, x2 = max(float(b["cx"]) - float(b["w"]) / 2, 0.0), min(float(b["cx"]) + float(b["w"]) / 2, 1.0)
    y1, y2 = max(float(b["cy"]) - float(b["h"]) / 2, 0.0), min(float(b["cy"]) + float(b["h"]) / 2, 1.0)
    return f"{cls} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}"


def write_mask(src, dst, regions, cfg):
    with Image.open(src) as raw:
        im = ImageOps.exif_transpose(raw).convert("RGB")
    w, h = im.size
    s = min(cfg["side"] / max(w, h), 1.0)
    if s < 1:
        im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    w, h = im.size
    a = np.array(im)
    for x1, y1, x2, y2 in regions:
        a[max(int(y1 * h), 0):min(int(np.ceil(y2 * h)), h), max(int(x1 * w), 0):min(int(np.ceil(x2 * w)), w)] = cfg["fill"]
    Image.fromarray(a).save(dst, "JPEG", quality=cfg["quality"])


def build_variant(name, files, labels, masked, stats, scene, cfg):
    out = BASE / f"dataset_{name}"
    if out.exists():
        shutil.rmtree(out)
    for k in ("images", "labels"):
        for s in ("train", "val_monitor"):
            (out / k / s).mkdir(parents=True)
    for f in sorted(files):
        r = stats[f]
        dst = out / "images" / "train" / f
        if f in masked:
            dst = dst.with_suffix(".jpg")
            write_mask(PPE4 / "images" / "train" / f, dst, masked[f], cfg["mask"])
        else:
            os.link(PPE4 / "images" / r["split"] / f, dst)
        (out / "labels" / "train" / f"{Path(f).stem}.txt").write_text("".join(x + "\n" for x in labels[f]), encoding="utf-8", newline="\n")
    train_scenes = {scene[f] for f in files}
    test_scenes = {r["scene"] for r in rd(C0 / "eval_status.csv") if r["set"] == "test_new"}
    monitor = []
    draft = {p.name: p for p in (C0 / "images" / "val_new_draft").iterdir()}
    for f, r in sorted(stats.items()):
        keep = (r["split"] == "val" or f in draft) and scene[f] not in train_scenes and scene[f] not in test_scenes
        if keep:
            monitor.append(f)
            src = draft.get(f, PPE4 / "images" / r["split"] / f)
            os.link(src, out / "images" / "val_monitor" / f)
            lab = C0 / "labels" / "val_new_draft" / f"{Path(f).stem}.txt"
            if not lab.exists():
                lab = PPE4 / "labels" / r["split"] / f"{Path(f).stem}.txt"
            shutil.copy2(lab, out / "labels" / "val_monitor" / lab.name)
    (out / "data.yaml").write_text(f"# Train {name}, tạo bởi scripts/03m_ppe6_train_variants.py. val_monitor chỉ để theo dõi khi train.\ntrain: images/train\nval: images/val_monitor\n"
                                   "names:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(NAMES)), encoding="utf-8", newline="\n")
    return monitor


def table_rows(name, files, labels, stats):
    c = Counter()
    for f in files:
        o = stats[f]["source"]
        c[("images", o)] += 1
        for line in labels[f]:
            c[(NAMES[int(line.split()[0])], o)] += 1
    return [dict(variant=name, cls=k[0], source=k[1], n=v) for k, v in sorted(c.items())]


def pack(name, files, labels, masked, monitor, stats):
    """Gói nhỏ cho Kaggle: nhãn, danh sách, ảnh đã che; ảnh còn lại lấy từ dataset chính."""
    out = VAR / "kaggle" / f"{name}_pack.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    src = BASE / f"dataset_{name}"
    rows = [f"train\t{stats[f]['split']}\t{f}\t{'masked' if f in masked else 'link'}" for f in sorted(files)]
    rows += [f"val_monitor\t{stats[f]['split']}\t{f}\tlink" for f in sorted(monitor)]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        z.writestr("manifest.tsv", "\n".join(rows) + "\n")
        z.write(src / "data.yaml", "data.yaml")
        for p in sorted((src / "labels").rglob("*.txt")):
            z.write(p, p.relative_to(src).as_posix())
        for f in sorted(masked):
            if f in files:
                p = src / "images" / "train" / f"{Path(f).stem}.jpg"
                z.write(p, f"masked/{p.name}")
    return out


def check(names, stats, scene):
    eval_sets = {s: {p.name for p in (C0 / "images" / f"{s}_draft").iterdir()} for s in ("val_new", "test_new", "chvg_glass_val", "chvg_glass_test")}
    m = json.loads((C0 / "scene_map.json").read_text(encoding="utf-8"))
    sc = dict(scene) | m
    split = {f: r["split"] for f, r in stats.items()}
    bad = []
    for n in names:
        out = BASE / f"dataset_{n}"
        mm = {r["masked"]: r["source"] for r in rd(out / "mask_map.csv")} if (out / "mask_map.csv").exists() else {}
        train = {mm.get(p.name, p.name) for p in (out / "images" / "train").iterdir()}
        sets = dict(eval_sets, train=train)
        for f in train:
            split.setdefault(f, "train")
        for s in eval_sets.values():
            for f in s:
                split.setdefault(f, "external")
        bad += [f"{n}: {x}" for x in check_leaks(sets, sc, split)]
        for p in (out / "labels" / "train").glob("*.txt"):
            bad += [f"{n}/{p.name}: {e}" for e in check_label_rows(p.read_text(encoding="utf-8").splitlines())]
        if {Path(x).stem for x in os.listdir(out / "images" / "train")} != {p.stem for p in (out / "labels" / "train").glob("*.txt")}:
            bad.append(f"{n}: ảnh và nhãn không khớp")
        mon = {p.name for p in (out / "images" / "val_monitor").iterdir()}
        if {sc[f] for f in mon} & {sc[f] for f in train}:
            bad.append(f"{n}: val_monitor trùng cảnh với train")
        if {sc[f] for f in mon} & {sc[f] for f in eval_sets["test_new"]}:
            bad.append(f"{n}: val_monitor trùng cảnh với test_new")
    z = np.load(BASE / "scene" / "features.npz", allow_pickle=False)
    idx = {k: i for i, k in enumerate(z["key"].tolist())}
    chvg = [idx[f] for s in ("chvg_glass_val", "chvg_glass_test") for f in eval_sets[s]]
    for n in names:
        out = BASE / f"dataset_{n}"
        mm = {r["masked"]: r["source"] for r in rd(out / "mask_map.csv")} if (out / "mask_map.csv").exists() else {}
        t = [idx[mm.get(p.name, p.name)] for p in (out / "images" / "train").iterdir()]
        top = float((z["emb"][chvg] @ z["emb"][t].T).max())
        print(f"{n}: cosine lớn nhất giữa train và CHVG đánh giá {top:.3f}")
        if top >= yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["scene"]["emb_min"]:
            bad.append(f"{n}: train gần trùng CHVG đánh giá")
    print("Kiểm tra lỗi:", len(bad))
    for b in bad[:20]:
        print(" ", b)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    stats, scene, roles, boxes = load()
    if args.check:
        sys.exit(1 if check(("c1", "c2"), stats, scene) else 0)
    VAR.mkdir(parents=True, exist_ok=True)
    c0 = {p.name for p in (C0 / "images" / "train").iterdir()}
    cap_dropped = {r["file"] for r in rd(C0 / "excluded.csv") if r["reason"] == "scene_cap"}
    loss, reason = loss_table(stats, scene, roles, boxes, cap_dropped)
    print(json.dumps(loss, ensure_ascii=False))

    labels = {f: [x for x in (C0 / "labels" / "train" / f"{Path(f).stem}.txt").read_text(encoding="utf-8").splitlines() if x.strip()] for f in c0}
    merged, table = merge_chv(stats, scene, roles, cfg)
    print("Ghép CHV:", dict(Counter(r["status"] for r in table)))

    # C1
    c1, drop1, unclear_chv = set(c0), Counter(), {}
    raw_glass = Counter()
    for r in rd(CHVG / "glass_order.csv"):
        raw_glass[re.sub(r"_jpg\.rf\..*", "", r["file"].replace("chvg__", ""))] += 1

    def glass_count(f):
        return raw_glass[Path(f).stem.replace("chv__", "")]

    for f, gl in merged.items():
        if scene[f] in roles:
            drop1["eval_scene"] += 1
            continue
        st = next(r for r in table if r["file"] == f)["status"]
        # box_mismatch: hai nhóm vẽ mũ lệch nhau. Ảnh đã xác nhận trùng; chỉ không tin hộp kính, nên ảnh có kính mới phải bỏ.
        if st == "box_mismatch" and glass_count(f):
            drop1["box_mismatch_with_glass"] += 1
            continue
        if st in ("image_mismatch", "no_chvg") and glass_count(f):
            drop1[st] += 1
            continue
        if any(b["label"] == "unclear" for b in gl):
            drop1["chv_glass_unclear"] += 1
            unclear_chv[f] = gl
            continue
        c1.add(f)
        labels[f] = old_lines(stats[f]) + [yline(NEW_CLASS["goggles"], b) for b in gl if b["label"] == SAFE]
    print("C1 bỏ:", dict(drop1), "ảnh", len(c1))
    build_variant("c1", c1, labels, {}, stats, scene, cfg)
    monitor1 = sorted(p.name for p in (BASE / "dataset_c1" / "images" / "val_monitor").iterdir())

    # C2: che vùng không rõ
    cand = {f: [b for b in boxes[f] if blocks_train(b["label"], b["note"], b["target"])] for f, k in reason.items() if k == "hop_khong_ro"}
    cand.update({f: [b for b in gl if b["label"] == "unclear"] for f, gl in unclear_chv.items()})
    c2, masked, status, mask_rows = set(c1), {}, Counter(), []
    per_scene = Counter(scene[f] for f in c1)
    rng = random.Random(cfg["eval"]["seed"])
    order = sorted(cand)
    rng.shuffle(order)
    for f in order:
        if scene[f] in roles:
            status["eval_scene"] += 1
            continue
        r = stats[f]
        lines = old_lines(r)
        extra = [yline(NEW_CLASS[b["target"]], b) for b in boxes[f] if b["label"] == SAFE] + [yline(4, b) for b in merged.get(f, []) if b["label"] == SAFE]
        regions = []
        for b in cand[f]:
            cx, cy, w, h = (float(b[k]) for k in ("cx", "cy", "w", "h"))
            m = cfg["mask"]["margin"]
            regions.append((cx - w / 2 * (1 + m), cy - h / 2 * (1 + m), cx + w / 2 * (1 + m), cy + h / 2 * (1 + m)))
        labelled = [(c, x - w / 2, y - h / 2, x + w / 2, y + h / 2) for c, x, y, w, h in parse_yolo("\n".join(lines + extra))]
        ok, worst = mask_decision(regions, labelled, cfg["mask"]["max_cover"])
        if not ok:
            status["hits_label"] += 1
            mask_rows.append(dict(file=f, status="hits_label", worst_cover=round(worst, 3), regions=len(regions)))
            continue
        if scene[f] in cfg["repeat_scenes"] and per_scene[scene[f]] >= cfg["train_scene_cap"]:
            status["scene_cap"] += 1
            mask_rows.append(dict(file=f, status="scene_cap", worst_cover=round(worst, 3), regions=len(regions)))
            continue
        per_scene[scene[f]] += 1
        c2.add(f)
        masked[f] = regions
        labels[f] = lines + extra
        status["saved"] += 1
        mask_rows.append(dict(file=f, status="saved", worst_cover=round(worst, 3), regions=len(regions)))
    print("C2:", dict(status), "ảnh", len(c2))
    build_variant("c2", c2, labels, masked, stats, scene, cfg)
    wr(BASE / "dataset_c2" / "mask_map.csv", [dict(source=f, masked=f"{Path(f).stem}.jpg", regions=json.dumps([[round(v, 6) for v in q] for q in masked[f]])) for f in sorted(masked)])
    wr(VAR / "mask_status.csv", sorted(mask_rows, key=lambda r: r["file"]))
    monitor2 = sorted(p.name for p in (BASE / "dataset_c2" / "images" / "val_monitor").iterdir())

    rows = table_rows("c0", c0, labels, stats) + table_rows("c1", c1, labels, stats) + table_rows("c2", c2, labels, stats)
    wr(VAR / "compare.csv", rows)
    pack("c1", c1, labels, {}, monitor1, stats)
    pack("c2", c2, labels, masked, monitor2, stats)
    h = hashlib.sha256()
    for n, s in (("c1", c1), ("c2", c2)):
        for f in sorted(s):
            h.update(f"{n}|{f}|{'|'.join(labels[f])}|{json.dumps(masked.get(f, []) if n == 'c2' else [])}\n".encode())
    man = dict(commit=subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(), seed=cfg["eval"]["seed"], mask=cfg["mask"],
               chv_merge={k: v for k, v in cfg["chv_merge"].items() if k != "unclear"}, c1_dropped=dict(drop1), c2_status=dict(status), monitor=dict(c1=len(monitor1), c2=len(monitor2)), content_hash=h.hexdigest())
    (VAR / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(man["content_hash"], man["monitor"])
    if check(("c1", "c2"), stats, scene):
        sys.exit(1)


if __name__ == "__main__":
    main()
