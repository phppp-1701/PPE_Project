"""Thử nghiệm 6 lớp: máy gán nhãn hai lượt, gộp, tạo gói kiểm định. Nhãn máy không phải nhãn người, không vào human_review.csv.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03t_ppe6_machine_label.py sheets --pass a --out <thư mục làm việc>   # bảng ảnh, chỉ đọc phần công khai của gói mù
    python scripts/03t_ppe6_machine_label.py collect --pass a --out <thư mục làm việc>  # kiểm đủ từng ô, khóa machine_pass_a.csv
    python scripts/03t_ppe6_machine_label.py merge       # gộp hai lượt, ghi machine_merged.csv; không xem nhãn cũ
    python scripts/03t_ppe6_machine_label.py compare     # sau khi khóa: so với nhãn agent cũ, chỉ in số tổng hợp
    python scripts/03t_ppe6_machine_label.py audit       # tạo gói audit, audit_img trong data/ppe6/review/cvat_pack_audit/
    python scripts/03t_ppe6_machine_label.py audit-img2  # gói ảnh làm lại, có hộp đã có và lớp được hỏi
    python scripts/03t_ppe6_machine_label.py audit-import --reviewer "Tên"   # đọc phiên 03q, ghi audit_review.csv
    python scripts/03t_ppe6_machine_label.py audit-report
    python scripts/03t_ppe6_machine_label.py rest        # kiểm định không đạt: gói mọi hộp val, test người chưa xem
    python scripts/03t_ppe6_machine_label.py rest-import --reviewer "Tên"    # ghi rest_review.csv, human_reviewed
    python scripts/03t_ppe6_machine_label.py eval-count  # số hộp theo tập, chỉ từ nhãn người

Tham số ở configs/ppe6.yaml mục `labeling`. Quy trình ở docs/experiments/2026-11-06_ppe6_plan.md.
"""

import argparse
import csv
import json
import random
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import quoteattr

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.fast_review import load_pack  # noqa: E402
from ppe.machine_labels import MACHINE_CONSENSUS, MACHINE_LABELED, PASS_FIELDS, REPORT_NOTE, audit_tiers, check_labeler, check_pass_row, merge_passes, read_csv, stratified_sample  # noqa: E402
from ppe.ppe6_data import NOT_A_PERSON, UNSET, leak_tokens  # noqa: E402

REVIEW = ROOT / "data" / "ppe6" / "review"
BLIND = REVIEW / "cvat_pack_blind"
AUDIT = REVIEW / "cvat_pack_audit"
TASKS = ("task_a", "task_b", "task_c", "task_d")
PERSON_TASKS = ("task_a", "task_b")
FONT = ImageFont.truetype("arial.ttf", 20)
TARGET_OF_IMAGE = dict(task_b="goggles", task_d="boots")


def cfg():
    return yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["labeling"]


def units():
    """Mọi hộp và mọi ảnh cần xem cả ảnh, chỉ từ annotations.xml của gói."""
    out = []
    for t in TASKS:
        pack = load_pack(BLIND / t)
        for im in pack["images"]:
            out += [dict(task=t, kind="box", id=b["item_id"], image=im["name"], box=b, boxes=im["boxes"]) for b in im["boxes"]]
            if t in TARGET_OF_IMAGE:
                out.append(dict(task=t, kind="image", id=im["name"], image=im["name"], box=None, boxes=im["boxes"]))
    return out


def picture(zips, u):
    with Image.open(BytesIO(zips[u["task"]].read(u["image"]))) as im:
        return im.convert("RGB")


def draw_boxes(im, boxes, current, scale=1.0, off=(0, 0)):
    d = ImageDraw.Draw(im)
    for b in boxes:
        on = current is not None and b["item_id"] == current["item_id"]
        p = [(b["xtl"] - off[0]) * scale, (b["ytl"] - off[1]) * scale, (b["xbr"] - off[0]) * scale, (b["ybr"] - off[1]) * scale]
        d.rectangle(p, outline="red" if on else "white", width=3 if on else 1)


def fit(im, size):
    s = min(size / im.width, size / im.height)
    out = im.resize((max(round(im.width * s), 1), max(round(im.height * s), 1)), Image.LANCZOS)
    return out, s


def box_tile(im, u, code, sc):
    px = sc["panel_px"]
    tile = Image.new("RGB", (2 * px + 12, px + 30), (32, 32, 32))
    b = u["box"]
    full, s = fit(im, px)
    draw_boxes(full, u["boxes"], b, s)
    tile.paste(full, ((px - full.width) // 2, 28))
    m = max(b["xbr"] - b["xtl"], b["ybr"] - b["ytl"]) * (0.5 + sc["zoom_context"])
    cx, cy = (b["xtl"] + b["xbr"]) / 2, (b["ytl"] + b["ybr"]) / 2
    x, y = max(cx - m, 0), max(cy - m, 0)
    crop = im.crop((int(x), int(y), int(min(cx + m, im.width)), int(min(cy + m, im.height))))
    zoom, z = fit(crop, px)
    draw_boxes(zoom, u["boxes"], b, z, (int(x), int(y)))
    tile.paste(zoom, (px + 12 + (px - zoom.width) // 2, 28))
    ImageDraw.Draw(tile).text((4, 2), f"{code}  {'UNG/GIAY' if b['target'] == 'boots' else 'KINH'}", fill="yellow", font=FONT)
    return tile


def image_tile(im, u, code, sc):
    px = sc["image_px"]
    tile = Image.new("RGB", (px, px + 30), (32, 32, 32))
    full, s = fit(im, px)
    draw_boxes(full, u["boxes"], None, s)
    tile.paste(full, ((px - full.width) // 2, 28))
    ImageDraw.Draw(tile).text((4, 2), f"{code}  CA ANH: {'UNG/GIAY' if TARGET_OF_IMAGE[u['task']] == 'boots' else 'KINH'}", fill="cyan", font=FONT)
    return tile


def sheet(tiles, cols):
    w, h = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    page = Image.new("RGB", (cols * (w + 8), rows * (h + 8)), (0, 0, 0))
    for i, t in enumerate(tiles):
        page.paste(t, ((i % cols) * (w + 8), (i // cols) * (h + 8)))
    return page


def cmd_sheets(p, out):
    c = cfg()
    sc = c["sheet"]
    rng = random.Random(c["passes"][p])
    zips = {t: zipfile.ZipFile(BLIND / t / "images.zip") for t in TASKS}
    work = Path(out) / f"pass_{p}"
    if work.exists():
        shutil.rmtree(work)
    all_units = units()
    boxes = [u for u in all_units if u["kind"] == "box"]
    images = [u for u in all_units if u["kind"] == "image"]
    rng.shuffle(boxes)
    rng.shuffle(images)
    codes = rng.sample(range(10000, 99999), len(all_units))
    groups = []
    per = sc["box_cols"] * sc["box_rows"]
    groups += [("box", boxes[i:i + per]) for i in range(0, len(boxes), per)]
    per = sc["image_cols"] * sc["image_rows"]
    groups += [("image", images[i:i + per]) for i in range(0, len(images), per)]
    rng.shuffle(groups)
    mapping, n = {}, 0
    for gi, (kind, group) in enumerate(groups):
        folder = work / f"batch_{gi // c['batch_sheets'] + 1:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        tiles = []
        for u in group:
            code = f"T{codes[n]}"
            n += 1
            mapping[code] = dict(task=u["task"], kind=u["kind"], id=u["id"])
            im = picture(zips, u)
            tiles.append(box_tile(im, u, code, sc) if kind == "box" else image_tile(im, u, code, sc))
        sheet(tiles, sc["box_cols"] if kind == "box" else sc["image_cols"]).save(folder / f"sheet_{gi + 1:03d}.jpg", quality=88)
    (Path(out) / f"map_{p}.json").write_text(json.dumps(mapping), encoding="utf-8")
    print(f"Lượt {p}: {len(mapping)} ô, {len(groups)} bảng, {len(list(work.iterdir()))} nhóm")


def cmd_collect(p, out):
    c = cfg()
    labeler = f"machine_pass_{p}"
    check_labeler(labeler)
    mapping = json.loads((Path(out) / f"map_{p}.json").read_text(encoding="utf-8"))
    rows, seen, bad = [], set(), []
    for f in sorted((Path(out) / f"pass_{p}").glob("batch_*/result.csv")):
        at = datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")
        for r in csv.DictReader(f.open(encoding="utf-8")):
            code = r["code"].strip()
            if code not in mapping or code in seen:
                bad.append(f"{f.parent.name}: mã lạ hoặc trùng {code}")
                continue
            seen.add(code)
            m = mapping[code]
            person = r.get("person_ok", "").strip() if m["task"] in PERSON_TASKS and m["kind"] == "box" else ""
            row = dict(labeler=labeler, guide_version=c["guide_version"], labeled_at=at, task=m["task"], kind=m["kind"], id=m["id"], decision=r.get("decision", "").strip() if m["kind"] == "box" else "", person_ok=person,
                       image_result=r.get("image_result", "").strip() if m["kind"] == "image" else "", reason=r.get("reason", "").strip())
            e = check_pass_row(row)
            if m["task"] in PERSON_TASKS and m["kind"] == "box" and not person:
                e.append("person_ok")
            if e:
                bad.append(f"{code}: {e}")
            rows.append(row)
    lost = sorted(set(mapping) - seen)
    print(f"Lượt {p}: {len(rows)}/{len(mapping)} ô, thiếu {len(lost)}, lỗi {len(bad)}")
    for x in bad[:20]:
        print(" ", x)
    if lost:
        print("  thiếu:", lost[:20])
    if bad or lost:
        sys.exit(1)
    path = REVIEW / f"machine_pass_{p}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, PASS_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["task"], r["kind"], r["id"])))
    print("Đã khóa", path.name)


def private_items():
    """Chỉ dùng sau khi đã khóa nhãn máy, cho số tổng hợp và lấy mẫu."""
    out = {}
    for t in TASKS:
        for r in read_csv(BLIND / "_private" / f"{t}_items.csv"):
            out[r["item_id"]] = dict(r, task=t)
    return out


def cmd_merge():
    a = {(r["task"], r["kind"], r["id"]): r for r in read_csv(REVIEW / "machine_pass_a.csv")}
    b = {(r["task"], r["kind"], r["id"]): r for r in read_csv(REVIEW / "machine_pass_b.csv")}
    if not a or not b:
        sys.exit("Thiếu kết quả một lượt.")
    rows = merge_passes(a, b)
    with (REVIEW / "machine_merged.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{REPORT_NOTE} (chưa kiểm định). Ô: {len(rows)}", dict(Counter(r["status"] for r in rows)))


def table(rows, keyf):
    c = defaultdict(Counter)
    for r in rows:
        c[keyf(r)][r["status"]] += 1
    for k in sorted(c):
        n = sum(c[k].values())
        print(f"  {k}: đồng thuận {c[k][MACHINE_CONSENSUS]}/{n} ({c[k][MACHINE_CONSENSUS] / n:.1%}), khác {c[k][MACHINE_LABELED]}")


def tier_of(it):
    return f"{it['target']}|{it['source']}"


def cmd_compare():
    """Sau khi khóa: tỉ lệ đồng thuận theo lớp, nguồn, task; khác biệt với nhãn agent cũ. Chỉ in số tổng hợp."""
    rows = read_csv(REVIEW / "machine_merged.csv")
    if not rows:
        sys.exit("Chưa gộp.")
    items = private_items()
    box = [r for r in rows if r["kind"] == "box"]
    img = [r for r in rows if r["kind"] == "image"]
    print("Theo task, hộp:")
    table(box, lambda r: r["task"])
    print("Theo lớp, nguồn, hộp:")
    table(box, lambda r: tier_of(items[r["id"]]))
    print("Theo task, ảnh:")
    table(img, lambda r: r["task"])
    print("Kiểu khác nhau:", dict(Counter(r["differ"] for r in rows if r["differ"])))
    print("Kết luận đồng thuận, hộp:", dict(sorted(Counter((items[r["id"]]["target"], r["decision_a"]) for r in box if r["status"] == MACHINE_CONSENSUS).items())))
    print("Kết luận đồng thuận, ảnh:", dict(sorted(Counter((r["task"], r["image_a"]) for r in img if r["status"] == MACHINE_CONSENSUS).items())))
    diff, total = Counter(), Counter()
    for r in box:
        if r["status"] == MACHINE_CONSENSUS:
            it = items[r["id"]]
            total[tier_of(it)] += 1
            diff[tier_of(it)] += r["decision_a"] != it["agent_label"]
    print("So nhãn agent cũ, trên hộp đồng thuận:")
    for k in sorted(total):
        print(f"  {k}: khác {diff[k]}/{total[k]} ({diff[k] / total[k]:.1%})")


def build_pack(name, items, images, person, seed, shown=None, ask=None):
    """items: dòng ánh xạ có cx, cy.. theo pixel gói gốc. images: {tên ảnh gốc: (task, rộng, cao)}. Đặt tên mới ngẫu nhiên, trộn.

    shown: {tên ảnh gốc: [hộp]} hộp đã có, chỉ để vẽ (không item_id, không nhãn). ask: {tên ảnh gốc: lớp được hỏi ở bước xem ảnh}."""
    shown, ask = shown or {}, ask or {}
    rng = random.Random(seed)
    folder = AUDIT / name
    folder.mkdir(parents=True)
    order = sorted(images)
    rng.shuffle(order)
    nums = rng.sample(range(100000, 999999), len(order) + len(items))
    zips = {t: zipfile.ZipFile(BLIND / t / "images.zip") for t in TASKS}
    by = defaultdict(list)
    for it in items:
        by[it["image"]].append(it)
    xml = ['<?xml version="1.0" encoding="utf-8"?>', "<annotations>", "<version>1.1</version>"]
    mapped, imgs, pages = [], [], []
    for i, src in enumerate(order):
        new = f"img_{nums[i]:06d}.jpg"
        pages.append((new, src))
    pages.sort()
    k = len(order)
    with zipfile.ZipFile(folder / "images.zip", "w", zipfile.ZIP_STORED) as z:
        for fi, (new, src) in enumerate(pages):
            task, w, h = images[src]
            z.writestr(zipfile.ZipInfo(new, date_time=(2026, 1, 1, 0, 0, 0)), zips[task].read(src))
            q = f" ask={quoteattr(ask[src])}" if src in ask else ""
            xml.append(f'<image id="{fi}" name={quoteattr(new)} width="{w}" height="{h}"{q}>')
            for b in shown.get(src, []):
                xml.append(f'<box label="shown" source="manual" occluded="0" xtl="{b["xtl"]:.2f}" ytl="{b["ytl"]:.2f}" xbr="{b["xbr"]:.2f}" ybr="{b["ybr"]:.2f}" z_order="0"></box>')
            group = by[src]
            rng.shuffle(group)
            for it in group:
                iid = f"a{nums[k]:06d}"
                k += 1
                at = f'<attribute name="item_id">{iid}</attribute><attribute name="decision">{UNSET}</attribute>' + (f'<attribute name="person_ok">{UNSET}</attribute>' if person else "")
                xml.append(f'<box label="{it["target"]}_review" source="manual" occluded="0" xtl="{it["xtl"]:.2f}" ytl="{it["ytl"]:.2f}" xbr="{it["xbr"]:.2f}" ybr="{it["ybr"]:.2f}" z_order="0">{at}</box>')
                mapped.append(dict(audit_id=iid, item_id=it["item_id"]))
            xml.append("</image>")
            imgs.append(dict(audit_image=new, image=src, task=task))
    xml.append("</annotations>")
    (folder / "annotations.xml").write_text("\n".join(xml) + "\n", encoding="utf-8", newline="\n")
    attrs = [dict(name="item_id"), dict(name="decision")] + ([dict(name="person_ok")] if person else [])
    (folder / "labels.json").write_text(json.dumps([dict(name=n, attributes=attrs) for n in ("boots_review", "goggles_review")]), encoding="utf-8", newline="\n")
    return mapped, imgs


def cmd_audit():
    c = cfg()["audit"]
    if list(REVIEW.glob("fast_audit*_state.json")):
        sys.exit("Đã có phiên kiểm định của người, không tạo lại gói audit (sẽ mất ánh xạ).")
    rows = read_csv(REVIEW / "machine_merged.csv")
    if not rows:
        sys.exit("Chưa gộp.")
    items = private_items()
    box = [r for r in rows if r["kind"] == "box"]
    queue = [r for r in box if r["status"] == MACHINE_LABELED]
    queue_img = [r for r in rows if r["kind"] == "image" and r["status"] == MACHINE_LABELED]
    if len(queue) > c["max_queue_boxes"]:
        print(f"Dừng: hàng đợi {len(queue)} hộp, quá mức {c['max_queue_boxes']}. Cần đề xuất cách lấy mẫu.")
        sys.exit(2)
    cons = [r for r in box if r["status"] == MACHINE_CONSENSUS]
    # Ưu tiên val, test: hộp thuộc task_a, task_b được tính tầng riêng, train (task_c) chỉ lấy tối thiểu.
    pool = [r for r in cons if r["task"] != "task_c"]
    key = lambda r: (items[r["id"]]["target"], items[r["id"]]["source"], r["decision_a"])  # noqa: E731
    sample = stratified_sample(pool, c["consensus_sample"], c["floor"], c["seed"], key)
    extra = stratified_sample([r for r in cons if r["task"] == "task_c"], 2 * c["floor"], 2, c["seed"], key)
    chosen = {r["id"]: "queue" for r in queue} | {r["id"]: "sample" for r in [*sample, *extra]}
    packs = {t: load_pack(BLIND / t) for t in TASKS}
    where = {}
    sizes = {}
    for t, p in packs.items():
        for im in p["images"]:
            sizes[im["name"]] = (t, im["width"], im["height"])
            for b in im["boxes"]:
                where[b["item_id"]] = dict(b, image=im["name"])
    if AUDIT.exists():
        shutil.rmtree(AUDIT)
    (AUDIT / "_private").mkdir(parents=True)
    its = [where[k] for k in chosen]
    mapped, imgs = build_pack("audit", its, {i["image"]: sizes[i["image"]] for i in its}, True, c["seed"])
    with (AUDIT / "_private" / "audit_items.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["audit_id", "item_id", "origin"], lineterminator="\n")
        w.writeheader()
        w.writerows(dict(m, origin=chosen[m["item_id"]]) for m in mapped)
    img_sample = stratified_sample([r for r in rows if r["kind"] == "image" and r["status"] == MACHINE_CONSENSUS], c["image_sample"], 10, c["seed"], lambda r: (r["task"], r["image_a"]))
    img_chosen = {r["id"]: "queue" for r in queue_img} | {r["id"]: "sample" for r in img_sample}
    _, imgs2 = build_pack("audit_img", [], {k: sizes[k] for k in img_chosen}, False, c["seed"] + 1)
    with (AUDIT / "_private" / "audit_img_images.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["audit_image", "image", "task", "origin"], lineterminator="\n")
        w.writeheader()
        w.writerows(dict(i, origin=img_chosen[i["image"]]) for i in imgs2)
    pk = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["pack"]
    s = dict(queue=len(queue), consensus_sample=len(sample) + len(extra), boxes=len(chosen), images=len(imgs), image_queue=len(queue_img), image_sample=len(img_sample), image_tiles=len(imgs2),
             minutes_estimate=round((2 * len(chosen) * pk["sec_per_box"] / 2 + len(imgs) * pk["sec_per_image"] + len(imgs2) * pk["sec_per_chv_image"]) / 60))
    (AUDIT / "_private" / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    print(s)
    print("Mẫu theo tầng:", dict(sorted(Counter(key(r) for r in sample).items())))
    bad = []
    for n in ("audit", "audit_img"):
        bad += leak_tokens((AUDIT / n / "annotations.xml").read_text(encoding="utf-8")) + leak_tokens((AUDIT / n / "labels.json").read_text(encoding="utf-8"))
    print("Kiểm tra lộ nhãn: lỗi", len(bad), bad[:5])
    if bad:
        sys.exit(1)


def cmd_audit_img2():
    """Gói ảnh làm lại: cùng ảnh với audit_img, có vẽ hộp đã có và ghi lớp được hỏi như hai lượt máy đã thấy.

    audit_img bản đầu thiếu hai thứ này nên câu hỏi với người khác câu hỏi với máy; giữ nguyên phiên đã chấm, không dùng để kết luận.
    Không xóa hay ghi đè audit, audit_img, _private hiện có."""
    c = cfg()["audit"]
    old = read_csv(AUDIT / "_private" / "audit_img_images.csv")
    if not old:
        sys.exit("Chưa có audit_img.")
    if (AUDIT / "audit_img2").exists():
        sys.exit("audit_img2 đã có, không ghi đè.")
    sizes, shown, ask = {}, {}, {}
    for t in TASKS:
        for im in load_pack(BLIND / t)["images"]:
            sizes[im["name"]] = (t, im["width"], im["height"])
            shown[im["name"]] = im["boxes"]
            if t in TARGET_OF_IMAGE:
                ask[im["name"]] = TARGET_OF_IMAGE[t]
    origin = {r["image"]: r["origin"] for r in old}
    _, imgs = build_pack("audit_img2", [], {k: sizes[k] for k in origin}, False, c["seed"] + 2, shown, ask)
    with (AUDIT / "_private" / "audit_img2_images.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["audit_image", "image", "task", "origin"], lineterminator="\n")
        w.writeheader()
        w.writerows(dict(i, origin=origin[i["image"]]) for i in imgs)
    text = (AUDIT / "audit_img2" / "annotations.xml").read_text(encoding="utf-8")
    bad = leak_tokens(text) + leak_tokens((AUDIT / "audit_img2" / "labels.json").read_text(encoding="utf-8"))
    n_shown = text.count('label="shown"')
    print(f"audit_img2: {len(imgs)} ảnh, {n_shown} hộp có sẵn, hỏi", dict(Counter(ask[i["image"]] for i in imgs)), "| kiểm tra lộ nhãn: lỗi", len(bad), bad[:5])
    if bad:
        sys.exit(1)


EVAL_SETS = ("val_new", "test_new", "chvg_glass_val", "chvg_glass_test")


def cmd_rest():
    """Gói `rest`: mọi hộp val, test chưa có người xem trong `audit`, để val, test hoàn toàn là nhãn người (human_reviewed).

    Dùng khi kiểm định không đạt. Không xóa hay ghi đè gói, ánh xạ hay phiên đã có."""
    c = cfg()["audit"]
    if (AUDIT / "rest").exists():
        sys.exit("Gói rest đã có, không ghi đè.")
    seen = {r["item_id"] for r in read_csv(AUDIT / "_private" / "audit_items.csv")}
    if not seen:
        sys.exit("Chưa có gói audit.")
    items = private_items()
    sizes, where = {}, {}
    for t in TASKS:
        for im in load_pack(BLIND / t)["images"]:
            sizes[im["name"]] = (t, im["width"], im["height"])
            for b in im["boxes"]:
                where[b["item_id"]] = dict(b, image=im["name"])
    todo = sorted(k for k, it in items.items() if it["set"] in EVAL_SETS and k not in seen)
    its = [where[k] for k in todo]
    mapped, imgs = build_pack("rest", its, {i["image"]: sizes[i["image"]] for i in its}, True, c["seed"] + 3)
    with (AUDIT / "_private" / "rest_items.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["audit_id", "item_id", "origin"], lineterminator="\n")
        w.writeheader()
        w.writerows(dict(m, origin="rest") for m in mapped)
    bad = leak_tokens((AUDIT / "rest" / "annotations.xml").read_text(encoding="utf-8")) + leak_tokens((AUDIT / "rest" / "labels.json").read_text(encoding="utf-8"))
    print(f"rest: {len(mapped)} hộp, {len(imgs)} ảnh, theo tập", dict(sorted(Counter((items[k]["set"], items[k]["target"]) for k in todo).items())), "| kiểm tra lộ nhãn: lỗi", len(bad), bad[:5])
    if bad:
        sys.exit(1)


def read_box_session(task, mapping_file, reviewer, origin_default=None):
    """Đọc phiên hộp của 03q, trả về (dòng, số ô chưa chọn). Từ chối phiên của người khác."""
    p = REVIEW / f"fast_{task}_state.json"
    if not p.exists():
        sys.exit(f"Chưa có phiên {task}.")
    s = json.loads(p.read_text(encoding="utf-8"))
    if s["reviewer"] != reviewer:
        sys.exit(f"Phiên {task} thuộc người khác.")
    mapping = {r["audit_id"]: r for r in read_csv(AUDIT / "_private" / mapping_file)}
    items = private_items()
    now = datetime.now().isoformat(timespec="seconds")
    rows, missing = [], 0
    for k, v in s["boxes"].items():
        if v["decision"] == UNSET or v["person_ok"] == UNSET:
            missing += 1
            continue
        it = items[mapping[k]["item_id"]]
        rows.append(dict(box_id=it["box_id"], item_id=mapping[k]["item_id"], kind="box", target=it["target"], source=it["source"], origin=mapping[k]["origin"], after=v["decision"], person_ok=v["person_ok"], reviewer=reviewer, reviewed_at=now))
    return rows, missing


def cmd_rest_import(reviewer):
    """Ghi rest_review.csv, trạng thái human_reviewed (người xem từng hộp, không qua nhãn máy). Không ghi human_review.csv."""
    if reviewer.strip().lower() in NOT_A_PERSON or reviewer.lower().startswith("machine"):
        sys.exit("Cần tên người thật.")
    rows, missing = read_box_session("rest", "rest_items.csv", reviewer)
    if missing:
        sys.exit(f"Còn {missing} mục chưa chọn, chưa ghi gì.")
    with (REVIEW / "rest_review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Đã ghi rest_review.csv: {len(rows)} dòng, trạng thái human_reviewed. Không ghi human_review.csv.")


def cmd_eval_count():
    """Số hộp bảo hộ theo tập, chỉ từ nhãn người (audit_review.csv, rest_review.csv)."""
    items = private_items()
    human = {r["item_id"]: r for f in ("audit_review.csv", "rest_review.csv") for r in read_csv(REVIEW / f) if r["kind"] == "box"}
    c, left = Counter(), Counter()
    for k, it in items.items():
        if it["set"] in EVAL_SETS:
            if k in human:
                c[(it["set"], it["target"], human[k]["after"])] += 1
            else:
                left[(it["set"], it["target"])] += 1
    for k in sorted(c):
        print(" ", k, c[k])
    print("Chưa có người xem:", dict(sorted(left.items())))


def cmd_audit_import(reviewer):
    if reviewer.strip().lower() in NOT_A_PERSON or reviewer.lower().startswith("machine"):
        sys.exit("Cần tên người thật.")
    rows, missing = [], 0
    p = REVIEW / "fast_audit_state.json"
    if not p.exists():
        sys.exit("Chưa có phiên audit.")
    s = json.loads(p.read_text(encoding="utf-8"))
    if s["reviewer"] != reviewer:
        sys.exit("Phiên này thuộc người khác.")
    mapping = {r["audit_id"]: r for r in read_csv(AUDIT / "_private" / "audit_items.csv")}
    items = private_items()
    now = datetime.now().isoformat(timespec="seconds")
    for k, v in s["boxes"].items():
        if v["decision"] == UNSET or v["person_ok"] == UNSET:
            missing += 1
            continue
        it = items[mapping[k]["item_id"]]
        rows.append(dict(box_id=it["box_id"], item_id=mapping[k]["item_id"], kind="box", target=it["target"], source=it["source"], origin=mapping[k]["origin"], after=v["decision"], person_ok=v["person_ok"], reviewer=reviewer, reviewed_at=now))
    # Chỉ dùng audit_img2; phiên audit_img bản đầu (thiếu hộp có sẵn, thiếu lớp được hỏi) giữ nguyên trên đĩa, không nhập.
    p2 = REVIEW / "fast_audit_img2_state.json"
    if not p2.exists():
        sys.exit("Chưa có phiên audit_img2.")
    if p2.exists():
        s2 = json.loads(p2.read_text(encoding="utf-8"))
        if s2["reviewer"] != reviewer:
            sys.exit("Phiên audit_img2 thuộc người khác.")
        names = {r["audit_image"]: r for r in read_csv(AUDIT / "_private" / "audit_img2_images.csv")}
        for n, r in names.items():
            flagged, val = bool(s2["flags"].get("image:" + n)), s2["images"].get(n, "")
            if not flagged and not val:
                missing += 1
                continue
            res = "missing_box" if flagged else "reject" if val == "reject_image" else "no_missing"
            rows.append(dict(box_id="image:" + r["image"], item_id=r["image"], kind="image", target=r["task"], source="", origin=r["origin"], after=res, person_ok="", reviewer=reviewer, reviewed_at=now))
    if missing:
        sys.exit(f"Còn {missing} mục chưa chọn, chưa ghi gì.")
    with (REVIEW / "audit_review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Đã ghi audit_review.csv: {len(rows)} dòng, trạng thái human_audited. Không ghi human_review.csv.")


def cmd_audit_report():
    c = cfg()["audit"]
    merged = {r["id"]: r for r in read_csv(REVIEW / "machine_merged.csv")}
    rows = []
    for r in read_csv(REVIEW / "audit_review.csv"):
        m = merged[r["item_id"]]
        if r["origin"] != "sample":
            continue
        machine = m["decision_a"] if r["kind"] == "box" else m["image_a"]
        rows.append(dict(tier=f"{r['target']}|{r['source']}" if r["kind"] == "box" else f"anh|{r['target']}", machine=machine, human=r["after"]))
    t = audit_tiers(rows, c["max_disagreement"])
    (REVIEW / "audit_report.json").write_text(json.dumps(dict(note=REPORT_NOTE, tiers=t), ensure_ascii=False, indent=1), encoding="utf-8")
    print(REPORT_NOTE)
    for k, v in t.items():
        print(f"  {k}: {'ĐẠT' if v['passed'] else 'KHÔNG ĐẠT'} khác {v['different']}/{v['n']} = {v['rate']:.1%}, KTC {v['ci']}, kiểu sai {v['pattern']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["sheets", "collect", "merge", "compare", "audit", "audit-img2", "audit-import", "audit-report", "rest", "rest-import", "eval-count"])
    ap.add_argument("--pass", dest="which", choices=["a", "b"])
    ap.add_argument("--out")
    ap.add_argument("--reviewer", default="")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if args.cmd in ("sheets", "collect") and not (args.which and args.out):
        sys.exit("Cần --pass và --out.")
    if args.cmd == "sheets":
        cmd_sheets(args.which, args.out)
    elif args.cmd == "collect":
        cmd_collect(args.which, args.out)
    elif args.cmd == "merge":
        cmd_merge()
    elif args.cmd == "compare":
        cmd_compare()
    elif args.cmd == "audit":
        cmd_audit()
    elif args.cmd == "audit-img2":
        cmd_audit_img2()
    elif args.cmd == "rest":
        cmd_rest()
    elif args.cmd == "rest-import":
        cmd_rest_import(args.reviewer)
    elif args.cmd == "eval-count":
        cmd_eval_count()
    elif args.cmd == "audit-import":
        cmd_audit_import(args.reviewer)
    else:
        cmd_audit_report()


if __name__ == "__main__":
    main()
