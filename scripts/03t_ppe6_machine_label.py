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
    python scripts/03t_ppe6_machine_label.py recheck --out <danh sách item_id>   # gói xem lại một phần rest
    python scripts/03t_ppe6_machine_label.py rest-import --reviewer "Tên"    # ghi rest_review.csv, human_reviewed
    python scripts/03t_ppe6_machine_label.py boots-v3    # gói chấm lại mọi hộp ủng val, test theo định nghĩa bản 3
    python scripts/03t_ppe6_machine_label.py boots-v3-import --reviewer "Tên"
    python scripts/03t_ppe6_machine_label.py train-v3 [--dry]   # chấm mù ủng train theo bản 3 (gồm mẫu P2 giày SH17)
    python scripts/03t_ppe6_machine_label.py train-v3-import --reviewer "Tên"
    python scripts/03t_ppe6_machine_label.py machine-c-import --out <thư mục>   # lượt máy c cho train_v3, chv_boots (nhãn máy)
    python scripts/03t_ppe6_machine_label.py chv-boots   # P2_chv: xem cả ảnh CHV train tìm ủng bảo hộ chưa có hộp
    python scripts/03t_ppe6_machine_label.py chv-boots-import --reviewer "Tên"
    python scripts/03t_ppe6_machine_label.py glass-img   # kính cả ảnh: CHVG và ảnh kính val, test (ưu tiên thấp)
    python scripts/03t_ppe6_machine_label.py glass-img-import --reviewer "Tên"
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
from ppe.machine_labels import MACHINE_CHV, MACHINE_TRAIN, MACHINE_CONSENSUS, MACHINE_LABELED, PASS_FIELDS, REPORT_NOTE, audit_tiers, check_labeler, check_pass_row, merge_passes, read_csv, stratified_sample  # noqa: E402
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


def cmd_recheck(list_file):
    """Gói `recheck`: các hộp rest người xem lại (danh sách item_id, mỗi dòng một mã). Không hiện lựa chọn cũ."""
    c = cfg()["audit"]
    if (AUDIT / "recheck").exists():
        sys.exit("Gói recheck đã có, không ghi đè.")
    want = [x.strip() for x in Path(list_file).read_text(encoding="utf-8").split() if x.strip()]
    rest = {r["item_id"] for r in read_csv(AUDIT / "_private" / "rest_items.csv")}
    if not want or not set(want) <= rest:
        sys.exit("Danh sách rỗng hoặc có mã không thuộc gói rest.")
    sizes, where = {}, {}
    for t in TASKS:
        for im in load_pack(BLIND / t)["images"]:
            sizes[im["name"]] = (t, im["width"], im["height"])
            for b in im["boxes"]:
                where[b["item_id"]] = dict(b, image=im["name"])
    its = [where[k] for k in sorted(set(want))]
    mapped, imgs = build_pack("recheck", its, {i["image"]: sizes[i["image"]] for i in its}, True, c["seed"] + 4)
    with (AUDIT / "_private" / "recheck_items.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["audit_id", "item_id", "origin"], lineterminator="\n")
        w.writeheader()
        w.writerows(dict(m, origin="recheck") for m in mapped)
    bad = leak_tokens((AUDIT / "recheck" / "annotations.xml").read_text(encoding="utf-8"))
    print(f"recheck: {len(mapped)} hộp, {len(imgs)} ảnh | kiểm tra lộ nhãn: lỗi", len(bad))
    if bad:
        sys.exit(1)


def cmd_boots_v3():
    """Gói `boots_v3`: mọi hộp ủng val, test, chấm lại theo định nghĩa bản 3. Không hiện lựa chọn cũ, không ghi đè gói cũ."""
    c = cfg()["audit"]
    if (AUDIT / "boots_v3").exists():
        sys.exit("Gói boots_v3 đã có, không ghi đè.")
    items = private_items()
    sizes, where = {}, {}
    for t in TASKS:
        for im in load_pack(BLIND / t)["images"]:
            sizes[im["name"]] = (t, im["width"], im["height"])
            for b in im["boxes"]:
                where[b["item_id"]] = dict(b, image=im["name"])
    todo = sorted(k for k, it in items.items() if it["set"] in EVAL_SETS and it["target"] == "boots")
    its = [where[k] for k in todo]
    mapped, imgs = build_pack("boots_v3", its, {i["image"]: sizes[i["image"]] for i in its}, True, c["seed"] + 5)
    with (AUDIT / "_private" / "boots_v3_items.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["audit_id", "item_id", "origin"], lineterminator="\n")
        w.writeheader()
        w.writerows(dict(m, origin="boots_v3") for m in mapped)
    bad = leak_tokens((AUDIT / "boots_v3" / "annotations.xml").read_text(encoding="utf-8"))
    print(f"boots_v3: {len(mapped)} hộp, {len(imgs)} ảnh, theo tập", dict(Counter(items[k]["set"] for k in todo)), "| kiểm tra lộ nhãn: lỗi", len(bad))
    if bad:
        sys.exit(1)


def cmd_boots_v3_import(reviewer):
    """Ghi boots_v3_review.csv (human_reviewed, guide_version 3). Không ghi human_review.csv, không sửa file bản 2."""
    if reviewer.strip().lower() in NOT_A_PERSON or reviewer.lower().startswith("machine"):
        sys.exit("Cần tên người thật.")
    rows, missing = read_box_session("boots_v3", "boots_v3_items.csv", reviewer)
    if missing:
        sys.exit(f"Còn {missing} mục chưa chọn, chưa ghi gì.")
    rows = [dict(r, guide_version=3) for r in rows]
    with (REVIEW / "boots_v3_review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Đã ghi boots_v3_review.csv: {len(rows)} dòng, human_reviewed, định nghĩa bản 3. Không ghi human_review.csv.")


def train_boot_rows():
    """Hộp ủng ở train C2 cần chấm theo bản 3: mọi hộp agent `safety`, mọi hộp Construction-PPE `ordinary`, `unclear`,
    và mẫu P2 giày SH17 (p2_shoe_sample.csv). Giày SH17 `unclear` còn lại do P2 đại diện, không chấm hết."""
    stats = {r["image"]: r for r in read_csv(ROOT / "data" / "ppe4" / "stats.csv")}
    c2 = {p.name for p in (ROOT / "data" / "ppe6" / "dataset_c2" / "images" / "train").iterdir()}
    dec = {r["box_id"]: r for r in read_csv(REVIEW / "decisions_v2.csv")}
    p2 = {r["box_id"] for r in read_csv(REVIEW / "p2_shoe_sample.csv")}
    out = []
    for b in read_csv(REVIEW / "boxes.csv"):
        s = stats.get(b["image"])
        if b["target"] != "boots" or s is None or s["file"] not in c2:
            continue
        lab = dec[b["box_id"]]["label"]
        origin = "p2" if b["box_id"] in p2 else "agent_safety" if lab == "safety" else f"cp_{lab}" if b["source"] == "construction_ppe" else None
        if origin:
            out.append(dict(b, file=s["file"], origin=origin, agent_label=lab))
    return out


def cmd_train_v3(dry):
    """Gói `train_v3`: chấm mù hộp ủng train theo định nghĩa bản 3. Ảnh lấy từ data/raw (chỉ đọc), mã hóa lại, tên mới."""
    c = cfg()["audit"]
    pk = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["pack"]
    rows = train_boot_rows()
    sec = cfg()["sec_per_box_measured"]
    print("train_v3:", len(rows), "hộp,", len({r["file"] for r in rows}), "ảnh, theo nhóm", dict(sorted(Counter((r["source"], r["origin"]) for r in rows).items())),
          f"ước tính {round(len(rows) * sec / 60)} phút ({sec} giây mỗi hộp)")
    if dry:
        return
    if (AUDIT / "train_v3").exists():
        sys.exit("Gói train_v3 đã có, không ghi đè.")
    rng = random.Random(c["seed"] + 6)
    files = sorted({r["image"] for r in rows})
    rng.shuffle(files)
    nums = rng.sample(range(100000, 999999), len(files) + len(rows))
    folder = AUDIT / "train_v3"
    folder.mkdir(parents=True)
    by = defaultdict(list)
    for r in rows:
        by[r["image"]].append(r)
    xml = ['<?xml version="1.0" encoding="utf-8"?>', "<annotations>", "<version>1.1</version>"]
    mapped, k = [], len(files)
    pages = sorted((f"img_{nums[i]:06d}.jpg", src) for i, src in enumerate(files))
    with zipfile.ZipFile(folder / "images.zip", "w", zipfile.ZIP_STORED) as z:
        for fi, (new, src) in enumerate(pages):
            with Image.open(ROOT / src) as im:
                im = im.convert("RGB")
                s = min(1.0, pk["side"] / max(im.size))
                if s < 1:
                    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
                buf = BytesIO()
                im.save(buf, "JPEG", quality=92)
                w, h = im.size
            z.writestr(zipfile.ZipInfo(new, date_time=(2026, 1, 1, 0, 0, 0)), buf.getvalue())
            xml.append(f'<image id="{fi}" name={quoteattr(new)} width="{w}" height="{h}">')
            group = by[src]
            rng.shuffle(group)
            for r in group:
                iid = f"a{nums[k]:06d}"
                k += 1
                cx, cy, bw, bh = (float(r[x]) for x in ("cx", "cy", "w", "h"))
                at = f'<attribute name="item_id">{iid}</attribute><attribute name="decision">{UNSET}</attribute><attribute name="person_ok">{UNSET}</attribute>'
                xml.append(f'<box label="boots_review" source="manual" occluded="0" xtl="{(cx - bw / 2) * w:.2f}" ytl="{(cy - bh / 2) * h:.2f}" xbr="{(cx + bw / 2) * w:.2f}" ybr="{(cy + bh / 2) * h:.2f}" z_order="0">{at}</box>')
                mapped.append(dict(audit_id=iid, box_id=r["box_id"], target="boots", source=r["source"], origin=r["origin"], agent_label=r["agent_label"]))
            xml.append("</image>")
    xml.append("</annotations>")
    (folder / "annotations.xml").write_text("\n".join(xml) + "\n", encoding="utf-8", newline="\n")
    attrs = [dict(name="item_id"), dict(name="decision"), dict(name="person_ok")]
    (folder / "labels.json").write_text(json.dumps([dict(name="boots_review", attributes=attrs)]), encoding="utf-8", newline="\n")
    with (AUDIT / "_private" / "train_v3_items.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(mapped[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(mapped)
    bad = leak_tokens((folder / "annotations.xml").read_text(encoding="utf-8")) + leak_tokens((folder / "labels.json").read_text(encoding="utf-8"))
    print(f"Đã tạo train_v3: {len(mapped)} hộp, {len(pages)} ảnh | kiểm tra lộ nhãn: lỗi", len(bad), bad[:5])
    if bad:
        sys.exit(1)


def cmd_train_v3_import(reviewer):
    """Ghi train_v3_review.csv (human_reviewed, ủng bản 3). Không ghi human_review.csv."""
    if reviewer.strip().lower() in NOT_A_PERSON or reviewer.lower().startswith("machine"):
        sys.exit("Cần tên người thật.")
    p = REVIEW / "fast_train_v3_state.json"
    if not p.exists():
        sys.exit("Chưa có phiên train_v3.")
    s = json.loads(p.read_text(encoding="utf-8"))
    if s["reviewer"] != reviewer:
        sys.exit("Phiên train_v3 thuộc người khác.")
    mapping = {r["audit_id"]: r for r in read_csv(AUDIT / "_private" / "train_v3_items.csv")}
    now = datetime.now().isoformat(timespec="seconds")
    rows, missing = [], 0
    for k, v in s["boxes"].items():
        if UNSET in v.values():
            missing += 1
            continue
        m = mapping[k]
        rows.append(dict(box_id=m["box_id"], item_id=k, kind="box", target="boots", source=m["source"], origin=m["origin"], after=v["decision"], person_ok=v["person_ok"], reviewer=reviewer, reviewed_at=now, guide_version=3))
    if missing:
        sys.exit(f"Còn {missing} mục chưa chọn, chưa ghi gì.")
    with (REVIEW / "train_v3_review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Đã ghi train_v3_review.csv: {len(rows)} dòng, human_reviewed, ủng bản 3.", dict(Counter((r["origin"], mapping[r["item_id"]]["agent_label"], r["after"]) for r in rows)))


def image_pack(name, task, ask_target, skip=()):
    """Gói xem cả ảnh: ảnh của một task gói mù, vẽ hộp đã có, ghi lớp được hỏi. skip: tên ảnh gốc đã có người xem."""
    c = cfg()["audit"]
    if (AUDIT / name).exists():
        sys.exit(f"Gói {name} đã có, không ghi đè.")
    p = load_pack(BLIND / task)
    names = {r["image_name"]: r["file"] for r in read_csv(BLIND / "_private" / f"{task}_images.csv")}
    sizes = {im["name"]: (task, im["width"], im["height"]) for im in p["images"] if names[im["name"]] not in skip}
    shown = {im["name"]: im["boxes"] for im in p["images"]}
    _, imgs = build_pack(name, [], sizes, False, c["seed"] + 7, shown, {k: ask_target for k in sizes})
    with (AUDIT / "_private" / f"{name}_images.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["audit_image", "image", "task", "file"], lineterminator="\n")
        w.writeheader()
        w.writerows(dict(i, file=names[i["image"]]) for i in imgs)
    bad = leak_tokens((AUDIT / name / "annotations.xml").read_text(encoding="utf-8"))
    sec = cfg()["sec_per_image_measured"]
    print(f"{name}: {len(imgs)} ảnh, ước tính {round(len(imgs) * sec / 60)} phút | kiểm tra lộ nhãn: lỗi", len(bad))
    if bad:
        sys.exit(1)


def read_image_session(name, reviewer):
    p = REVIEW / f"fast_{name}_state.json"
    if not p.exists():
        sys.exit(f"Chưa có phiên {name}.")
    s = json.loads(p.read_text(encoding="utf-8"))
    if s["reviewer"] != reviewer:
        sys.exit(f"Phiên {name} thuộc người khác.")
    out, missing = [], 0
    for r in read_csv(AUDIT / "_private" / f"{name}_images.csv"):
        n = r["audit_image"]
        flagged, val = bool(s["flags"].get("image:" + n)), s["images"].get(n, "")
        if not flagged and not val:
            missing += 1
            continue
        out.append((r["file"], "missing_box" if flagged else "reject" if val == "reject_image" else "no_missing"))
    if missing:
        sys.exit(f"Còn {missing} ảnh chưa chọn, chưa ghi gì.")
    return out


def cmd_chv_boots_import(reviewer):
    """P2_chv: ghi chv_boots_seen.csv, chv_boots_added.csv cho 03n gates. Ảnh có ủng bảo hộ chưa có hộp ghi một dòng (chưa vẽ hộp)."""
    if reviewer.strip().lower() in NOT_A_PERSON or reviewer.lower().startswith("machine"):
        sys.exit("Cần tên người thật.")
    res = read_image_session("chv_boots", reviewer)
    now = datetime.now().isoformat(timespec="seconds")
    with (REVIEW / "chv_boots_seen.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["box_id", "after", "result", "reviewer", "reviewed_at"])
        w.writerows([f"image:{fn}", "checked", r, reviewer, now] for fn, r in res)
    with (REVIEW / "chv_boots_added.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["file", "note"])
        w.writerows([fn, "co_ung_bao_ho_chua_co_hop"] for fn, r in res if r == "missing_box")
    print(f"P2_chv: {len(res)} ảnh,", dict(Counter(r for _, r in res)))


def cmd_glass_img_import(reviewer):
    """Kính cả ảnh: ghi glass_img_review.csv (dấu ảnh image:<file>), gồm cả 42 ảnh task_b đã xem ở audit_img2."""
    if reviewer.strip().lower() in NOT_A_PERSON or reviewer.lower().startswith("machine"):
        sys.exit("Cần tên người thật.")
    res = read_image_session("glass_img", reviewer)
    names = {r["image_name"]: r["file"] for r in read_csv(BLIND / "_private" / "task_b_images.csv")}
    old = [(names[r["item_id"]], r["after"]) for r in read_csv(REVIEW / "audit_review.csv") if r["kind"] == "image" and r["target"] == "task_b"]
    now = datetime.now().isoformat(timespec="seconds")
    with (REVIEW / "glass_img_review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["box_id", "after", "origin", "reviewer", "reviewed_at"])
        w.writerows([f"image:{fn}", r, "glass_img", reviewer, now] for fn, r in res)
        w.writerows([f"image:{fn}", r, "audit_img2", reviewer, now] for fn, r in old)
    print(f"glass_img: {len(res)} ảnh + {len(old)} ảnh audit_img2,", dict(Counter(r for _, r in res + old)))


def cmd_machine_c_import(work):
    """Lượt máy c (agent xem từng ô bảng ảnh của gói train_v3, chv_boots): ghi nhãn máy, tên machine_pass_c. Không phải nhãn người."""
    labeler = "machine_pass_c"
    check_labeler(labeler)
    work = Path(work)
    now = datetime.now().isoformat(timespec="seconds")
    m1 = json.loads((work / "map_train_v3.json").read_text(encoding="utf-8"))
    items = {r["audit_id"]: r for r in read_csv(AUDIT / "_private" / "train_v3_items.csv")}
    got = {r["code"]: r["decision"] for r in read_csv(work / "train_v3.csv")}
    if set(got) != set(m1) or any(v not in ("safety", "ordinary", "unclear", "ignore") for v in got.values()):
        sys.exit("train_v3.csv thiếu ô hoặc có giá trị lạ.")
    rows = [dict(labeler=labeler, guide_version=3, labeled_at=now, box_id=items[m1[c]]["box_id"], source=items[m1[c]]["source"], origin=items[m1[c]]["origin"], decision=v) for c, v in sorted(got.items())]
    with (REVIEW / MACHINE_TRAIN).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    m2 = json.loads((work / "map_chv_boots.json").read_text(encoding="utf-8"))
    files = {r["audit_image"]: r["file"] for r in read_csv(AUDIT / "_private" / "chv_boots_images.csv")}
    got2 = {r["code"]: r["image_result"] for r in read_csv(work / "chv_boots.csv")}
    if set(got2) != set(m2) or any(v not in ("no_missing", "missing_box", "reject") for v in got2.values()):
        sys.exit("chv_boots.csv thiếu ô hoặc có giá trị lạ.")
    rows2 = [dict(labeler=labeler, labeled_at=now, file=files[m2[c]], image_result=v) for c, v in sorted(got2.items())]
    with (REVIEW / MACHINE_CHV).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows2[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows2)
    print(f"{REPORT_NOTE.split(',')[0]} (machine_pass_c, chưa kiểm định): train_v3 {len(rows)} hộp", dict(Counter((r["origin"], r["decision"]) for r in rows)),
          f"| chv_boots {len(rows2)} ảnh", dict(Counter(r["image_result"] for r in rows2)))


def cmd_rest_import(reviewer):
    """Ghi rest_review.csv, trạng thái human_reviewed (người xem từng hộp, không qua nhãn máy). Không ghi human_review.csv."""
    if reviewer.strip().lower() in NOT_A_PERSON or reviewer.lower().startswith("machine"):
        sys.exit("Cần tên người thật.")
    rows, missing = read_box_session("rest", "rest_items.csv", reviewer)
    if missing:
        sys.exit(f"Còn {missing} mục chưa chọn, chưa ghi gì.")
    # Lần xem lại (recheck) của cùng người thay lựa chọn lần đầu; lần đầu vẫn nằm trong fast_rest_state.json, fast_rest_log.csv.
    if (AUDIT / "_private" / "recheck_items.csv").exists():
        again, miss2 = read_box_session("recheck", "recheck_items.csv", reviewer)
        if miss2:
            sys.exit(f"recheck còn {miss2} mục chưa chọn, chưa ghi gì.")
        new = {r["item_id"]: r for r in again}
        rows = [dict(r, after=new[r["item_id"]]["after"], person_ok=new[r["item_id"]]["person_ok"], origin="rest_recheck", reviewed_at=new[r["item_id"]]["reviewed_at"]) if r["item_id"] in new else r for r in rows]
    with (REVIEW / "rest_review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Đã ghi rest_review.csv: {len(rows)} dòng, trạng thái human_reviewed. Không ghi human_review.csv.")


def cmd_eval_count():
    """Số hộp bảo hộ theo tập, chỉ từ nhãn người (audit_review.csv, rest_review.csv)."""
    items = private_items()
    human = {r["item_id"]: r for f in ("audit_review.csv", "rest_review.csv") for r in read_csv(REVIEW / f) if r["kind"] == "box"}
    v3 = {r["item_id"]: r for r in read_csv(REVIEW / "boots_v3_review.csv")}
    # Ủng chỉ đếm theo bản 3 khi đã có; chưa có thì báo, không trộn hai bản.
    human = {k: v for k, v in human.items() if items[k]["target"] != "boots"} | v3 if v3 else human
    print("Ủng theo định nghĩa", "bản 3" if v3 else "bản 2 (chưa chấm lại bản 3)")
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
    ap.add_argument("cmd", choices=["sheets", "collect", "merge", "compare", "audit", "audit-img2", "audit-import", "audit-report", "rest", "recheck", "rest-import", "eval-count", "boots-v3", "boots-v3-import", "train-v3", "train-v3-import", "chv-boots", "chv-boots-import", "glass-img", "glass-img-import", "machine-c-import"])
    ap.add_argument("--pass", dest="which", choices=["a", "b"])
    ap.add_argument("--out")
    ap.add_argument("--reviewer", default="")
    ap.add_argument("--dry", action="store_true", help="train-v3: chỉ đếm, không tạo gói")
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
    elif args.cmd == "recheck":
        cmd_recheck(args.out or sys.exit("Cần --out <file danh sách item_id>."))
    elif args.cmd == "machine-c-import":
        cmd_machine_c_import(args.out or sys.exit("Cần --out <thư mục lượt máy c>."))
    elif args.cmd == "train-v3":
        cmd_train_v3(args.dry)
    elif args.cmd == "train-v3-import":
        cmd_train_v3_import(args.reviewer)
    elif args.cmd == "chv-boots":
        image_pack("chv_boots", "task_d", "boots")
    elif args.cmd == "chv-boots-import":
        cmd_chv_boots_import(args.reviewer)
    elif args.cmd == "glass-img":
        names = {r["image_name"]: r["file"] for r in read_csv(BLIND / "_private" / "task_b_images.csv")}
        done = {names[r["item_id"]] for r in read_csv(REVIEW / "audit_review.csv") if r["kind"] == "image" and r["target"] == "task_b"}
        image_pack("glass_img", "task_b", "goggles", done)
    elif args.cmd == "glass-img-import":
        cmd_glass_img_import(args.reviewer)
    elif args.cmd == "boots-v3":
        cmd_boots_v3()
    elif args.cmd == "boots-v3-import":
        cmd_boots_v3_import(args.reviewer)
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
