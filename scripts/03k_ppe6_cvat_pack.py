"""Thử nghiệm 6 lớp: tạo gói duyệt CVAT trong data/ppe6/review/cvat_pack/. Không tải lên CVAT, không ghi quyết định nào.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv, sau 03i và 03j):
    python scripts/03k_ppe6_cvat_pack.py

Mỗi nhóm (P0a, P0b, P1, P2) có: images.zip (ảnh đầy đủ, cạnh dài tối đa `pack.side`), annotations.xml (CVAT for images 1.1),
index.csv (box_id, giá trị agent, chiều cao người), labels.json (khai báo nhãn khi tạo task CVAT).
Mọi hộp để `decision = chua_duyet`. `scene_review/`: bảng cụm cảnh, scene_review.csv để người điền.
summary.json: số hộp, ảnh, thời gian ước tính. Hướng dẫn: docs/ppe6_review_guide.md.
"""

import csv
import json
import random
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "ppe6"
PPE4 = ROOT / "data" / "ppe4" / "dataset"
OUT = BASE / "review" / "cvat_pack"
CHVG = BASE / "external" / "chvg"
LABELS = [dict(name=n, type="rectangle", attributes=[
    dict(name="box_id", input_type="text", mutable=False, default_value="", values=[""]),
    dict(name="agent_label", input_type="text", mutable=False, default_value="", values=[""]),
    dict(name="decision", input_type="select", mutable=True, default_value="chua_duyet", values=["chua_duyet", "safety", "ordinary", "unclear", "ignore"]),
    dict(name="person_ok", input_type="select", mutable=True, default_value="chua_xem", values=["chua_xem", "du_lon", "qua_nho", "khong_ro"]),
]) for n in ("boots_review", "goggles_review")] + [dict(name="boots_new", type="rectangle", attributes=[]), dict(name="goggles_new", type="rectangle", attributes=[]),
                                                  dict(name="image_checked", type="tag", attributes=[]), dict(name="reject_image", type="tag", attributes=[])]


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8")))


def person_height(file, split_dir, cx, cy, w, h, side):
    """Chiều cao hộp người nhỏ nhất chứa tâm hộp, quy về ảnh có cạnh dài `side`. Không có người thì rỗng."""
    path = PPE4 / "labels" / split_dir / f"{Path(file).stem}.txt"
    if not path.exists():
        return ""
    best = None
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.split()
        if t and t[0] == "0":
            px, py, pw, ph = map(float, t[1:])
            if abs(cx - px) <= pw * 0.6 and abs(cy - py) <= ph * 0.6 and (best is None or ph < best):
                best = ph
    return "" if best is None else round(best * h * side / max(w, h), 1)


def collect(cfg):
    stats = {r["file"]: r for r in rd(ROOT / "data" / "ppe4" / "stats.csv")}
    by_image = {r["image"]: r for r in stats.values()}
    dec = {r["box_id"]: r for r in rd(BASE / "review" / "decisions_v2.csv")}
    status = {r["file"]: r for r in rd(BASE / "dataset" / "eval_status.csv")}
    groups = {g: [] for g in ("P0a", "P0b", "P1", "P2")}
    images = {g: set() for g in groups}
    for b in rd(BASE / "review" / "boxes.csv"):
        r = by_image.get(b["image"])
        if r is None:
            continue
        d = dec[b["box_id"]]
        item = dict(box_id=b["box_id"], target=b["target"], source=b["source"], file=r["file"], cx=b["cx"], cy=b["cy"], w=b["w"], h=b["h"], agent_label=d["label"], note=d["note"])
        st = status.get(r["file"])
        if st and st["set"] in ("val_new", "test_new"):
            item["set"] = st["set"]
            g = "P1" if d["label"] != "safety" else "P0a" if b["target"] == "boots" else "P0b"
            groups[g].append(item)
            images[g].add(r["file"])
    p2 = {r["box_id"] for r in rd(BASE / "review" / "p2_shoe_sample.csv")}
    for b in rd(BASE / "review" / "boxes.csv"):
        if b["box_id"] in p2:
            r = by_image[b["image"]]
            d = dec[b["box_id"]]
            groups["P2"].append(dict(box_id=b["box_id"], target="boots", source="sh17", file=r["file"], cx=b["cx"], cy=b["cy"], w=b["w"], h=b["h"], agent_label=d["label"], note=d["note"], set="train"))
            images["P2"].add(r["file"])
    # CHVG: tập đánh giá vào P0b, mẫu ngoài tập đánh giá vào P2
    split = {r["file"]: r["split"] for r in rd(BASE / "eval" / "chvg_split.csv")}
    unclear = set(cfg["chvg_precheck"]["unclear"].split())
    rest = []
    for r in rd(CHVG / "glass_order.csv"):
        x1, y1, x2, y2 = (float(r[k]) / 640 for k in ("x1", "y1", "x2", "y2"))
        item = dict(box_id=f"g{int(r['idx']):05d}", target="goggles", source="chvg", file=r["file"], cx=(x1 + x2) / 2, cy=(y1 + y2) / 2, w=x2 - x1, h=y2 - y1,
                    agent_label="unclear" if r["idx"] in unclear else "safety", note="", set=split.get(r["file"], "outside"))
        if r["file"] in split:
            groups["P0b"].append(item)
        else:
            rest.append(item)
    images["P0b"] |= set(split)
    for it in random.Random(cfg["eval"]["seed"]).sample(sorted(rest, key=lambda x: x["box_id"]), cfg["pack"]["p2_chvg"]):
        groups["P2"].append(it)
        images["P2"].add(it["file"])
    return groups, images, stats


def src_path(file, stats):
    if file.startswith("chvg__"):
        return CHVG / "extracted" / file.replace("chvg__", ""), None
    r = stats[file]
    return PPE4 / "images" / r["split"] / file, r["split"]


def write_group(name, items, files, stats, side, person):
    folder = OUT / name
    folder.mkdir(parents=True)
    by_file = defaultdict(list)
    for it in items:
        by_file[it["file"]].append(it)
    xml = ['<?xml version="1.0" encoding="utf-8"?>', "<annotations>", "<version>1.1</version>"]
    rows, img_rows = [], []
    with zipfile.ZipFile(folder / "images.zip", "w", zipfile.ZIP_STORED) as z:
        for i, f in enumerate(sorted(files)):
            path, split_dir = src_path(f, stats)
            with Image.open(path) as raw:
                im = ImageOps.exif_transpose(raw).convert("RGB")
            ow, oh = im.size
            s = min(side / max(ow, oh), 1.0)
            if s < 1:
                im = im.resize((round(ow * s), round(oh * s)), Image.LANCZOS)
            w, h = im.size
            buf = BytesIO()
            im.save(buf, "JPEG", quality=88)
            image_name = f"{Path(f).stem}.jpg"
            z.writestr(image_name, buf.getvalue())
            img_rows.append(dict(file=f, image_name=image_name))
            xml.append(f'<image id="{i}" name={quoteattr(image_name)} width="{w}" height="{h}">')
            for it in by_file[f]:
                cx, cy, bw, bh = (float(it[k]) for k in ("cx", "cy", "w", "h"))
                ph = person(f, split_dir, cx, cy, ow, oh, side)
                rows.append(dict(box_id=it["box_id"], target=it["target"], source=it["source"], set=it["set"], file=f, image_name=image_name, cx=f"{cx:.6f}", cy=f"{cy:.6f}", w=f"{bw:.6f}", h=f"{bh:.6f}",
                                 agent_label=it["agent_label"], agent_note=it["note"], person_h_px=ph))
                xml.append(f'<box label="{it["target"]}_review" source="manual" occluded="0" xtl="{(cx - bw / 2) * w:.2f}" ytl="{(cy - bh / 2) * h:.2f}" xbr="{(cx + bw / 2) * w:.2f}" ybr="{(cy + bh / 2) * h:.2f}" z_order="0">')
                xml.append(f'<attribute name="box_id">{escape(it["box_id"])}</attribute><attribute name="agent_label">{escape(it["agent_label"])}</attribute>'
                           '<attribute name="decision">chua_duyet</attribute><attribute name="person_ok">chua_xem</attribute></box>')
            xml.append("</image>")
    xml.append("</annotations>")
    (folder / "annotations.xml").write_text("\n".join(xml) + "\n", encoding="utf-8", newline="\n")
    (folder / "labels.json").write_text(json.dumps(LABELS, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    keys = ["box_id", "target", "source", "set", "file", "image_name", "cx", "cy", "w", "h", "agent_label", "agent_note", "person_h_px"]
    with (folder / "index.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, keys, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with (folder / "images.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["file", "image_name"], lineterminator="\n")
        w.writeheader()
        w.writerows(img_rows)
    return rows


def scene_sheets(cfg, stats):
    """Mỗi cảnh đánh giá một hàng: tối đa 5 ảnh của cảnh, 3 ảnh train gần nhất để người xem có trùng cảnh không."""
    folder = OUT / "scene_review"
    folder.mkdir(parents=True)
    st = rd(BASE / "dataset" / "eval_status.csv")
    scenes = defaultdict(list)
    for r in st:
        if r["set"] in ("val_new", "test_new"):
            scenes[(r["set"], r["scene"])].append(r["file"])
    z = np.load(BASE / "scene" / "features.npz", allow_pickle=False)
    key = z["key"].tolist()
    idx = {k: i for i, k in enumerate(key)}
    train = sorted(p.name for p in (BASE / "dataset" / "images" / "train").iterdir())
    te = z["emb"][[idx[f] for f in train]]
    T, per = 150, 6
    order = sorted(scenes)
    rows = []
    for n in range(0, len(order), per):
        page = Image.new("RGB", (9 * T, per * T), "white")
        for i, k in enumerate(order[n:n + per]):
            files = sorted(scenes[k])[:5]
            near = np.argsort(-(te @ z["emb"][[idx[f] for f in scenes[k]]].T).max(1))[:3]
            sim = float((te @ z["emb"][[idx[f] for f in scenes[k]]].T).max())
            paths = [src_path(f, stats)[0] for f in files] + [None] * (5 - len(files)) + [PPE4 / "images" / "train" / train[j] for j in near]
            for j, p in enumerate(paths[:9]):
                if p is None:
                    continue
                with Image.open(p) as raw:
                    im = ImageOps.exif_transpose(raw).convert("RGB")
                im.thumbnail((T - 4, T - 4))
                page.paste(im, (j * T, i * T))
            d = ImageDraw.Draw(page)
            d.rectangle((0, i * T, 118, i * T + 12), fill="black")
            d.text((2, i * T), f"{k[1]} {k[0]} n={len(scenes[k])}", fill="yellow")
            d.line((5 * T - 2, i * T, 5 * T - 2, (i + 1) * T), fill="red", width=3)
            rows.append(dict(sheet=f"scene_{n // per + 1:02d}.jpg", scene_id=k[1], set=k[0], images=len(scenes[k]), max_cosine_train=round(sim, 3), same_as_train="", note=""))
        page.save(folder / f"scene_{n // per + 1:02d}.jpg", quality=85)
    with (folder / "scene_review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    sample = BASE / "scene" / "big_sample.jpg"
    if sample.exists():
        shutil.copy2(sample, folder / "repeat_scene_check.jpg")
    return len(rows)


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    pk = cfg["pack"]
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    groups, images, stats = collect(cfg)
    chvg_person = defaultdict(list)
    for r in rd(CHVG / "boxes.csv"):
        if r["cls"] == "person":
            chvg_person[r["file"]].append(tuple(float(r[k]) / 640 for k in ("x1", "y1", "x2", "y2")))

    def person(file, split_dir, cx, cy, w, h, side):
        if split_dir is None:
            c = [p for p in chvg_person[file] if p[0] <= cx <= p[2] and p[1] <= cy <= p[3]]
            return round(min(p[3] - p[1] for p in c) * h * side / max(w, h), 1) if c else ""
        return person_height(file, split_dir, cx, cy, w, h, side)

    summary = {}
    for g in groups:
        rows = write_group(g, groups[g], images[g], stats, pk["side"], person)
        c = Counter((r["target"], r["source"], r["set"]) for r in rows)
        boxes, n_img = len(rows), len(images[g])
        minutes = (boxes * pk["sec_per_box"] + n_img * pk["sec_per_image"]) / 60
        summary[g] = dict(boxes=boxes, images=n_img, minutes_estimate=round(minutes), by={"|".join(k): v for k, v in sorted(c.items())})
        print(g, summary[g], flush=True)
    n = scene_sheets(cfg, stats)
    summary["scene_review"] = dict(scenes=n, minutes_estimate=round(n * pk["sec_per_scene"] / 60))
    summary["assumptions"] = {k: pk[k] for k in ("sec_per_box", "sec_per_image", "sec_per_scene")}
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(summary["scene_review"], ensure_ascii=False))


if __name__ == "__main__":
    main()
