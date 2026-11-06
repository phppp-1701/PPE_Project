"""Thử nghiệm 6 lớp: tạo gói duyệt mù từ gói cũ. Không sửa gói cũ, nhãn hay quyết định nào.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv, sau 03k):
    python scripts/03p_ppe6_blind_pack.py            # tạo data/ppe6/review/cvat_pack_blind/
    python scripts/03p_ppe6_blind_pack.py --check    # quét gói đã tạo xem có lộ nhãn không

Các task, tên trung tính để không lộ nhóm:
    task_a  P0a + phần ủng của P1, trộn          task_b  P0b + phần kính của P1 + ảnh CHVG không có hộp, trộn
    task_c  P2                                   task_d  P2_chv (không có hộp)
    trial   khoảng 10 hộp thử, có ca bảo hộ và không bảo hộ
    second  khoảng 50 hộp cho người thứ hai, phân tầng theo lớp, nguồn, nhãn agent

Mỗi task có images.zip, annotations.xml, labels.json để tải lên CVAT. Ảnh đổi tên ngẫu nhiên img_NNNNNN.jpg nên thứ tự theo tên là thứ tự đã trộn,
mọi ảnh đưa về cùng cạnh dài, bỏ EXIF. Hộp dùng mã ngẫu nhiên item_id; `decision`, `person_ok` mặc định `chua_chon`.
_private/<task>_items.csv, _images.csv giữ nhóm gốc, nguồn, giá trị agent để nhập và báo cáo: người duyệt không mở thư mục này.
"""

import argparse
import csv
import json
import random
import re
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import quoteattr

import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import UNSET, leak_tokens  # noqa: E402

BASE = ROOT / "data" / "ppe6"
OLD = BASE / "review" / "cvat_pack"
OUT = BASE / "review" / "cvat_pack_blind"
PPE4 = ROOT / "data" / "ppe4" / "dataset"
CHVG = BASE / "external" / "chvg"
TASKS = ("task_a", "task_b", "task_c", "task_d", "trial", "second")
PERSON_TASKS = ("task_a", "task_b", "trial")
ITEM_KEYS = ["item_id", "box_id", "group", "target", "source", "set", "file", "image_name", "cx", "cy", "w", "h", "agent_label", "agent_note", "person_h_px"]


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8")))


def labels(person):
    attrs = [dict(name="item_id", input_type="text", mutable=False, default_value="", values=[""]),
             dict(name="decision", input_type="select", mutable=True, default_value=UNSET, values=[UNSET, "safety", "ordinary", "unclear", "ignore"])]
    if person:
        attrs.append(dict(name="person_ok", input_type="select", mutable=True, default_value=UNSET, values=[UNSET, "du_lon", "qua_nho", "khong_ro"]))
    return [dict(name=n, type="rectangle", attributes=attrs) for n in ("boots_review", "goggles_review")] + [
        dict(name="boots_new", type="rectangle", attributes=[]), dict(name="goggles_new", type="rectangle", attributes=[]),
        dict(name="image_checked", type="tag", attributes=[]), dict(name="reject_image", type="tag", attributes=[])]


def box_xml(item, w, h, person):
    cx, cy, bw, bh = (float(item[k]) for k in ("cx", "cy", "w", "h"))
    attrs = f'<attribute name="item_id">{item["item_id"]}</attribute><attribute name="decision">{UNSET}</attribute>'
    if person:
        attrs += f'<attribute name="person_ok">{UNSET}</attribute>'
    return (f'<box label="{item["target"]}_review" source="manual" occluded="0" xtl="{(cx - bw / 2) * w:.2f}" ytl="{(cy - bh / 2) * h:.2f}" '
            f'xbr="{(cx + bw / 2) * w:.2f}" ybr="{(cy + bh / 2) * h:.2f}" z_order="0">{attrs}</box>')


def annotations_xml(pages, person):
    """pages: danh sách (tên ảnh, rộng, cao, các hộp), đã theo thứ tự tên."""
    xml = ['<?xml version="1.0" encoding="utf-8"?>', "<annotations>", "<version>1.1</version>"]
    for i, (name, w, h, items) in enumerate(pages):
        xml.append(f'<image id="{i}" name={quoteattr(name)} width="{w}" height="{h}">')
        xml += [box_xml(it, w, h, person) for it in items]
        xml.append("</image>")
    xml.append("</annotations>")
    return "\n".join(xml) + "\n"


def src_path(file, stats):
    if file.startswith("chvg__"):
        return CHVG / "extracted" / file.replace("chvg__", "")
    return PPE4 / "images" / stats[file]["split"] / file


def render(path, side):
    """Ảnh đầy đủ, cùng cạnh dài, không EXIF, nên kích thước không lộ nguồn ảnh."""
    with Image.open(path) as raw:
        im = ImageOps.exif_transpose(raw).convert("RGB")
    s = side / max(im.size)
    im = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.LANCZOS)
    buf = BytesIO()
    im.save(buf, "JPEG", quality=88)
    return buf.getvalue(), im.size


def stratified_second(items, n, floor, seed):
    """Chọn n hộp theo tầng (lớp, nguồn, nhãn agent): mỗi tầng tối thiểu `floor` nếu có, phần còn lại theo tỉ lệ."""
    rng = random.Random(seed)
    strata = defaultdict(list)
    for it in sorted(items, key=lambda x: x["box_id"]):
        strata[(it["target"], it["source"], it["agent_label"])].append(it)
    for v in strata.values():
        rng.shuffle(v)
    take = {k: min(floor, len(v)) for k, v in strata.items()}
    left = n - sum(take.values())
    total = sum(len(v) - take[k] for k, v in strata.items())
    for k, v in sorted(strata.items(), key=lambda kv: -len(kv[1])):
        extra = min(round(left * (len(v) - take[k]) / max(total, 1)), len(v) - take[k])
        take[k] += extra
    keys = sorted(strata, key=lambda k: -len(strata[k]))
    i = 0
    while sum(take.values()) > n:
        k = keys[i % len(keys)]
        if take[k] > floor:
            take[k] -= 1
        i += 1
    while sum(take.values()) < n and any(take[k] < len(strata[k]) for k in keys):
        k = keys[i % len(keys)]
        if take[k] < len(strata[k]):
            take[k] += 1
        i += 1
    return [it for k in sorted(strata) for it in strata[k][:take[k]]]


def collect(cfg):
    groups = {g: [dict(r, group=g) for r in rd(OLD / g / "index.csv")] for g in ("P0a", "P0b", "P1", "P2")}
    a = groups["P0a"] + [r for r in groups["P1"] if r["target"] == "boots"]
    b = groups["P0b"] + [r for r in groups["P1"] if r["target"] == "goggles"]
    c = groups["P2"]
    chvg_all = [r["file"] for r in rd(BASE / "eval" / "chvg_split.csv")]
    chv = [r["file"] for r in rd(OLD / "P2_chv" / "sample.csv")]
    bp = cfg["blind"]
    rng = random.Random(bp["seed"])
    pool = a + b
    trial = []
    for target, label, n in (("boots", True, 4), ("boots", False, 2), ("goggles", True, 2), ("goggles", False, 2)):
        v = sorted([r for r in pool if r["target"] == target and (r["agent_label"] == "safety") == label], key=lambda x: x["box_id"])
        trial += rng.sample(v, n)
    second = stratified_second(pool, bp["second_boxes"], bp["second_floor"], bp["seed"])
    return dict(task_a=(a, {r["file"] for r in a}), task_b=(b, {r["file"] for r in b} | set(chvg_all)), task_c=(c, {r["file"] for r in c}), task_d=([], set(chv)),
                trial=(trial, {r["file"] for r in trial}), second=(second, {r["file"] for r in second}))


def write_task(name, items, files, stats, cfg, ids, nums):
    bp = cfg["blind"]
    rng = random.Random(f"{bp['seed']}-{name}")
    folder = OUT / name
    folder.mkdir(parents=True)
    order = sorted(files)
    rng.shuffle(order)
    by_file = defaultdict(list)
    for it in items:
        by_file[it["file"]].append(dict(it, item_id=f"r{next(ids):05d}"))
    pages, rows, img_rows = [], [], []
    with zipfile.ZipFile(folder / "images.zip", "w", zipfile.ZIP_STORED) as z:
        for f in order:
            image_name = f"img_{next(nums):06d}.jpg"
            data, (w, h) = render(src_path(f, stats), bp["side"])
            info = zipfile.ZipInfo(image_name, date_time=(2026, 1, 1, 0, 0, 0))
            z.writestr(info, data)
            its = by_file[f]
            rng.shuffle(its)
            pages.append((image_name, w, h, its))
            img_rows.append(dict(image_name=image_name, file=f))
            rows += [dict({k: it.get(k, "") for k in ITEM_KEYS}, image_name=image_name) for it in its]
    pages.sort(key=lambda p: p[0])
    (folder / "annotations.xml").write_text(annotations_xml(pages, name in PERSON_TASKS), encoding="utf-8", newline="\n")
    (folder / "labels.json").write_text(json.dumps(labels(name in PERSON_TASKS), ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    priv = OUT / "_private"
    with (priv / f"{name}_items.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ITEM_KEYS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with (priv / f"{name}_images.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["image_name", "file"], lineterminator="\n")
        w.writeheader()
        w.writerows(img_rows)
    c = Counter((r["group"], r["target"], r["agent_label"]) for r in rows)
    print(name, len(rows), "hộp,", len(order), "ảnh", flush=True)
    return dict(boxes=len(rows), images=len(order), by={"|".join(k): v for k, v in sorted(c.items())})


def check():
    bad = []
    for t in TASKS:
        folder = OUT / t
        names = sorted(p.name for p in folder.iterdir())
        if names != ["annotations.xml", "images.zip", "labels.json"]:
            bad.append(f"{t}: file lạ {names}")
        xml = (folder / "annotations.xml").read_text(encoding="utf-8")
        bad += [f"{t}/annotations.xml: {x}" for x in leak_tokens(xml)]
        bad += [f"{t}/labels.json: {x}" for x in leak_tokens((folder / "labels.json").read_text(encoding="utf-8"), allow_decisions=True)]
        with zipfile.ZipFile(folder / "images.zip") as z:
            zn = z.namelist()
            bad += [f"{t}: tên ảnh lộ {n}" for n in zn if not re.fullmatch(r"img_\d{6}\.jpg", n)]
            if len({z.getinfo(n).date_time for n in zn}) > 1:
                bad.append(f"{t}: thời gian file khác nhau")
            with Image.open(BytesIO(z.read(zn[0]))) as im:
                if im.getexif():
                    bad.append(f"{t}: ảnh còn EXIF")
    print("Kiểm tra lộ nhãn: lỗi", len(bad))
    for b in bad[:20]:
        print(" ", b)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if args.check:
        sys.exit(1 if check() else 0)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    stats = {r["file"]: r for r in rd(ROOT / "data" / "ppe4" / "stats.csv")}
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "_private").mkdir(parents=True)
    plan = collect(cfg)
    pool = list(range(1, 200000))
    random.Random(cfg["blind"]["seed"]).shuffle(pool)
    ids, nums = iter(pool[:100000]), iter(pool[100000:])
    summary = {}
    for t in TASKS:
        items, files = plan[t]
        # Mỗi task đánh số ảnh riêng theo thứ tự trộn, nên tên ảnh không phản ánh bộ nguồn.
        summary[t] = write_task(t, items, files, stats, cfg, ids, nums)
    pk = cfg["pack"]
    for t, s in summary.items():
        s["minutes_estimate"] = round((s["boxes"] * pk["sec_per_box"] + s["images"] * pk["sec_per_chv_image" if t == "task_d" else "sec_per_image"]) / 60)
    (OUT / "_private" / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    if check():
        sys.exit(1)


if __name__ == "__main__":
    main()
