"""Bước 1: kiểm tra dữ liệu bốn lớp đã đổi nhãn (docs/spec.md mục 2.2).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/02_check_data.py --technical     # phần 1: lỗi kỹ thuật + thống kê
    python scripts/02_check_data.py --duplicates    # phần 2: tìm cặp ảnh trùng/gần trùng
    (phần 3 --content: viết sau)

Đọc data/ppe4/converted/<bộ>/index.csv và labels/; tham số trong configs/data_check.yaml.
Chỉ đọc, không sửa nhãn. Ghi vào data/ppe4/check/:
    technical_issues.csv   mỗi lỗi một dòng: bộ, ảnh, loại lỗi, chi tiết
    stats.json             số ảnh, số hộp theo lớp, phân bố cỡ hộp, theo từng bộ
    hashes.csv             dấu vân tay dHash của từng ảnh (tính lại nếu ảnh đổi kích thước file)
    duplicate_pairs.csv    các cặp ảnh có khoảng cách Hamming <= scan_hamming
    dup_samples_dXX.jpg    vài cặp mẫu ở mỗi khoảng cách, để chọn ngưỡng max_hamming
"""

import argparse
import collections
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "data_check.yaml"
CONVERTED = ROOT / "data" / "ppe4" / "converted"
CLASSES = yaml.safe_load((ROOT / "configs" / "label_map.yaml").read_text(encoding="utf-8"))["classes"]


def check_image(path):
    """(rộng, cao, lỗi). Mở ảnh và giải mã thật để bắt file hỏng hoặc bị cắt cụt."""
    try:
        with Image.open(path) as im:
            im.load()
            return im.width, im.height, None
    except FileNotFoundError:
        return None, None, "không có file ảnh"
    except Exception as e:  # PIL ném nhiều loại lỗi khác nhau cho ảnh hỏng
        return None, None, f"ảnh không đọc được: {type(e).__name__}"


def check_label(path, tol):
    """(danh sách hộp hợp lệ (lớp, cx, cy, w, h), danh sách lỗi)."""
    if not path.exists():
        return [], ["không có file nhãn"]
    boxes, issues, seen = [], [], set()
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 5:
            issues.append(f"dòng {i}: {len(parts)} cột")
            continue
        try:
            c, cx, cy, w, h = int(parts[0]), *map(float, parts[1:])
        except ValueError:
            issues.append(f"dòng {i}: không phải số")
            continue
        if c not in CLASSES:
            issues.append(f"dòng {i}: mã lớp {c}")
            continue
        if w <= 0 or h <= 0:
            issues.append(f"dòng {i}: hộp kích thước 0")
            continue
        if cx - w / 2 < -tol or cy - h / 2 < -tol or cx + w / 2 > 1 + tol or cy + h / 2 > 1 + tol:
            issues.append(f"dòng {i}: hộp ra ngoài ảnh")
        key = tuple(parts)
        if key in seen:
            issues.append(f"dòng {i}: trùng y hệt dòng trước")
        seen.add(key)
        boxes.append((c, cx, cy, w, h))
    return boxes, issues


def technical(cfg):
    tol = cfg["technical"]["coord_tolerance"]
    small, medium = cfg["stats"]["size_bins_px"]
    issues, stats = [], {}
    for src in cfg["sources"]:
        with open(CONVERTED / src / "index.csv", encoding="utf-8") as f:
            index = list(csv.DictReader(f))
        s = dict(images=len(index), rejected=0, images_with_issue=0, empty_label=0,
                 orig_split=collections.Counter(), boxes=collections.Counter(), images_with_class=collections.Counter(),
                 size_bins={k: collections.Counter() for k in CLASSES.values()},
                 image_size=collections.Counter())
        for n, r in enumerate(index, 1):
            img, lab = ROOT / r["image"], ROOT / r["label"]
            W, H, err = check_image(img)
            found = [err] if err else []
            boxes, lab_issues = check_label(lab, tol)
            found += lab_issues
            counted = collections.Counter(CLASSES[b[0]] for b in boxes)
            for k in CLASSES.values():  # số hộp trong index.csv phải khớp file nhãn
                if k and int(r[f"n_{k}"]) != counted[k]:
                    found.append(f"index.csv ghi n_{k}={r[f'n_{k}']}, file nhãn có {counted[k]}")
            issues += [dict(source=src, image=r["image"], issue=x) for x in found]
            s["images_with_issue"] += bool(found)
            if r.get("reject") == "1":
                s["rejected"] += 1
                continue  # thống kê chỉ tính ảnh được dùng
            s["orig_split"][r["orig_split"]] += 1
            s["empty_label"] += not boxes
            if W:
                s["image_size"]["dài ≥ 1280" if max(W, H) >= 1280 else "dài 640-1279" if max(W, H) >= 640 else "dài < 640"] += 1
            for k in counted:
                s["boxes"][k] += counted[k]
                s["images_with_class"][k] += 1
            if W:
                for c, _, _, w, h in boxes:
                    a = (w * W) * (h * H)
                    s["size_bins"][CLASSES[c]]["nhỏ" if a < small ** 2 else "vừa" if a < medium ** 2 else "lớn"] += 1
            if n % 1000 == 0:
                print(f"  {src}: {n}/{len(index)}", flush=True)
        stats[src] = s
        print(f"[{src}] {s['images']} ảnh, {s['images_with_issue']} ảnh có lỗi, {s['rejected']} ảnh loại, "
              f"hộp {dict(s['boxes'])}")
    return issues, stats


HASH_VERSION = "dhash64-trim1"  # đổi khi cách tính dấu vân tay đổi, để tính lại cache


def dhash(path, border_dark):
    """dHash 64 bit sau khi cắt viền tối: ảnh xám 9x8, mỗi bit = điểm trái sáng hơn điểm phải."""
    with Image.open(path) as im:
        im.draft("L", (256, 256))  # JPEG: giải mã thẳng ở cỡ nhỏ, nhanh hơn nhiều
        g = im.convert("L")
        g.thumbnail((256, 256))
    a = np.asarray(g)
    rows, cols = np.nonzero(a.max(axis=1) > border_dark)[0], np.nonzero(a.max(axis=0) > border_dark)[0]
    if len(rows) > 2 and len(cols) > 2:  # ảnh tối hoàn toàn thì giữ nguyên
        g = g.crop((cols[0], rows[0], cols[-1] + 1, rows[-1] + 1))
    px = np.asarray(g.resize((9, 8), Image.Resampling.LANCZOS), dtype=np.int16)
    bits = (px[:, :-1] > px[:, 1:]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def pair_sheet(pairs, title, path, cols=2):
    """Vẽ các cặp ảnh cạnh nhau, mỗi cặp ghi tên và khoảng cách."""
    tiles = []
    for p in pairs:
        row = Image.new("RGB", (610, 320), (200, 200, 200))
        for x, key in ((0, "image_a"), (310, "image_b")):
            with Image.open(ROOT / p[key]) as im:
                im.draft("RGB", (300, 300))
                t = im.convert("RGB")
                t.thumbnail((300, 300))
            pad = Image.new("RGB", (300, 320), "white")
            pad.paste(t, (0, 20))
            label = f"{p.get('no', '')} d{p['hamming']} {Path(p[key]).name}"[:46]
            ImageDraw.Draw(pad).text((3, 3), label, fill="black")
            row.paste(pad, (x, 0))
        tiles.append(row)
    sheet = Image.new("RGB", (cols * 620, ((len(tiles) + cols - 1) // cols) * 330 + 30), "white")
    ImageDraw.Draw(sheet).text((5, 8), title, fill="black")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 620, 30 + (i // cols) * 330))
    sheet.save(path, quality=85)


def build_groups(rows, pairs, d, confirmed):
    """group_id = thành phần liên thông của các cặp đạt ngưỡng (cùng bộ / khác bộ) và cặp người xác nhận."""
    parent = {r["image"]: r["image"] for r in rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    used = collections.Counter()
    for p in pairs:
        same = p["source_a"] == p["source_b"]
        if p["hamming"] <= (d["max_hamming_same_source"] if same else d["max_hamming_cross_source"]):
            parent[find(p["image_a"])] = find(p["image_b"])
            used["cùng bộ" if same else "khác bộ"] += 1
    for a, b in confirmed:
        parent[find(a)] = find(b)
        used["người xác nhận"] += 1
    members = collections.defaultdict(list)
    for r in rows:
        members[find(r["image"])].append(r)
    groups = []
    for gid, (_, ms) in enumerate(sorted(members.items(), key=lambda kv: kv[1][0]["image"])):
        srcs = sorted({m["source"] for m in ms})
        for m in ms:
            groups.append(dict(source=m["source"], image=m["image"], group_id=f"g{gid:05d}",
                               group_size=len(ms), group_sources="+".join(srcs)))
    return groups, used


def popcount64(x):
    """Đếm bit 1 của mảng uint64."""
    x = x - ((x >> 1) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + ((x >> 2) & np.uint64(0x3333333333333333))
    x = (x + (x >> 4)) & np.uint64(0x0F0F0F0F0F0F0F0F)
    return ((x * np.uint64(0x0101010101010101)) >> np.uint64(56)).astype(np.int64)


def duplicates(cfg, out):
    d = cfg["duplicates"]
    cache_path = out / "hashes.csv"
    cache = {}
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            cache = {r["image"]: r for r in csv.DictReader(f)}
    rows = []
    for src in cfg["sources"]:
        with open(CONVERTED / src / "index.csv", encoding="utf-8") as f:
            index = list(csv.DictReader(f))
        for n, r in enumerate(index, 1):
            size = (ROOT / r["image"]).stat().st_size
            c = cache.get(r["image"])
            fresh = c and int(c["bytes"]) == size and c.get("version") == HASH_VERSION
            h = c["dhash"] if fresh else f"{dhash(ROOT / r['image'], d['border_dark']):016x}"
            rows.append(dict(source=src, image=r["image"], bytes=size, version=HASH_VERSION, dhash=h,
                             reject=r.get("reject", "0")))
            if n % 1000 == 0 or n == len(index):
                print(f"  dHash {src}: {n}/{len(index)}", flush=True)
    with open(cache_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    hashes = np.array([int(r["dhash"], 16) for r in rows], dtype=np.uint64)
    pairs = []
    for i in range(len(rows) - 1):
        dist = popcount64(hashes[i + 1:] ^ hashes[i])
        for j in np.nonzero(dist <= d["scan_hamming"])[0]:
            a, b = rows[i], rows[i + 1 + j]
            pairs.append(dict(hamming=int(dist[j]), source_a=a["source"], image_a=a["image"],
                              source_b=b["source"], image_b=b["image"]))
    pairs.sort(key=lambda p: (p["hamming"], p["image_a"]))
    with open(out / "duplicate_pairs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["hamming", "source_a", "image_a", "source_b", "image_b"])
        w.writeheader()
        w.writerows(pairs)

    # số cặp theo khoảng cách và theo cặp nguồn
    print(f"\n{len(rows)} ảnh, {len(pairs)} cặp có khoảng cách <= {d['scan_hamming']}")
    by_dist = collections.Counter(p["hamming"] for p in pairs)
    by_src = collections.defaultdict(collections.Counter)
    for p in pairs:
        by_src[p["hamming"]]["-".join(sorted((p["source_a"], p["source_b"])))] += 1
    for k in sorted(by_dist):
        print(f"  khoảng cách {k:2d}: {by_dist[k]:5d} cặp  {dict(by_src[k])}")

    # tấm mẫu: mỗi khoảng cách vài cặp, nửa khác nguồn, nửa cùng nguồn (chọn ngẫu nhiên cố định)
    rng = np.random.default_rng(0)
    m = d["pairs_per_distance"]
    for k in sorted(by_dist):
        cross = [p for p in pairs if p["hamming"] == k and p["source_a"] != p["source_b"]]
        same = [p for p in pairs if p["hamming"] == k and p["source_a"] == p["source_b"]]
        pick = cross[:m // 2]
        pick += [same[i] for i in rng.permutation(len(same))[:m - len(pick)]]
        pick += cross[m // 2:m // 2 + m - len(pick)]
        pair_sheet(pick, f"Hamming = {k} ({by_dist[k]} cap)", out / f"dup_samples_d{k:02d}.jpg")

    # cặp khác bộ cần người xem: đánh số để ghi vào duplicate_confirmed.csv
    review = [p for p in pairs if p["source_a"] != p["source_b"]
              and d["max_hamming_cross_source"] < p["hamming"] <= d["cross_review_max"]]
    for i, p in enumerate(review, 1):
        p["no"] = i
    for old in out.glob("cross_review_*.jpg"):
        old.unlink()
    for j in range(0, len(review), 8):
        pair_sheet(review[j:j + 8], f"Cap khac bo can xem ({len(review)} cap)", out / f"cross_review_{j // 8 + 1:02d}.jpg")
    with open(out / "cross_review.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["no", "hamming", "source_a", "image_a", "source_b", "image_b"])
        w.writeheader()
        w.writerows(review)

    # group_id
    confirmed = []
    conf_path = out / "duplicate_confirmed.csv"
    if conf_path.exists():
        with open(conf_path, encoding="utf-8") as f:
            confirmed = [(r["image_a"], r["image_b"]) for r in csv.DictReader(f)]
    groups, used = build_groups(rows, pairs, d, confirmed)
    with open(out / "groups.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(groups[0]))
        w.writeheader()
        w.writerows(groups)
    sizes = collections.Counter(g["group_id"] for g in groups)
    multi = [g for g in groups if g["group_size"] > 1]
    print(f"\nCặp dùng để gom nhóm: {dict(used)}")
    print(f"{len(sizes)} nhóm cho {len(groups)} ảnh; {len({g['group_id'] for g in multi})} nhóm có >1 ảnh "
          f"({len(multi)} ảnh); nhóm lớn nhất {max(sizes.values())} ảnh")
    print("  nhóm >1 ảnh theo nguồn:", dict(collections.Counter(g["group_sources"] for g in multi)))
    top = sizes.most_common(5)
    print("  5 nhóm lớn nhất:", [(gid, n, next(g["group_sources"] for g in groups if g["group_id"] == gid)) for gid, n in top])
    pictor_overlap = [g for g in groups if g["source"] == "pictor_ppe" and g["group_sources"] != "pictor_ppe"]
    print(f"  ảnh Pictor trùng với bộ huấn luyện: {len(pictor_overlap)}")
    print(f"Cặp khác bộ cần xem (khoảng cách {d['max_hamming_cross_source'] + 1}-{d['cross_review_max']}): {len(review)}")
    print(f"Đã ghi hashes.csv, duplicate_pairs.csv, groups.csv, cross_review.csv, dup_samples_dXX.jpg, "
          f"cross_review_XX.jpg vào {out.relative_to(ROOT)}")


def xyxy(b):
    _, cx, cy, w, h = b
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


def iou(a, b):
    a, b = xyxy(a), xyxy(b)
    iw, ih = max(0, min(a[2], b[2]) - max(a[0], b[0])), max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = iw * ih
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0


def content(cfg, out):
    """Liệt kê hộp đáng ngờ theo quy tắc; không sửa gì."""
    c = cfg["content"]
    P, H, V, G = (next(k for k, v in CLASSES.items() if v == n) for n in ("person", "helmet", "vest", "gloves"))
    flags = []
    for src in cfg["sources"]:
        with open(CONVERTED / src / "index.csv", encoding="utf-8") as f:
            index = [r for r in csv.DictReader(f) if r.get("reject") != "1"]
        for r in index:
            with Image.open(ROOT / r["image"]) as im:  # chỉ đọc phần đầu file để lấy cỡ ảnh
                W, Hh = im.size
            boxes, _ = check_label(ROOT / r["label"], 1.0)
            scale = c["train_imgsz"] / max(W, Hh)
            persons = [b for b in boxes if b[0] == P]

            def flag(check, b, detail=""):
                flags.append(dict(source=src, image=r["image"], check=check, cls=CLASSES[b[0]],
                                  box=" ".join(f"{v:.6f}" for v in b[1:]), detail=detail))

            def holder(b):
                """Hộp người (đã nới) chứa tâm hộp b; chọn người nhỏ nhất."""
                m = c["inside_margin"]
                cand = [p for p in persons
                        if abs(b[1] - p[1]) <= p[3] * (0.5 + m) and abs(b[2] - p[2]) <= p[4] * (0.5 + m)]
                return min(cand, key=lambda p: p[3] * p[4]) if cand else None

            for i, b in enumerate(boxes):
                short = min(b[3] * W, b[4] * Hh) * scale
                if short < c["tiny_px"]:
                    flag("tiny", b, f"cạnh ngắn {short:.1f} px ở {c['train_imgsz']}")
                for b2 in boxes[i + 1:]:
                    if b2[0] == b[0] and iou(b, b2) >= c["dup_iou"]:
                        flag("dup_box", b, f"IoU {iou(b, b2):.2f} với hộp {' '.join(f'{v:.4f}' for v in b2[1:])}")
                if b[0] in (H, V, G) and persons:
                    p = holder(b)
                    if p is None:
                        flag(f"{CLASSES[b[0]]}_outside_person", b)
                    elif b[0] == G and b[3] * b[4] > c["glove_person_area_ratio"] * p[3] * p[4]:
                        flag("gloves_too_big", b, f"{b[3] * b[4] / (p[3] * p[4]):.2f} diện tích người")
                if b[0] in (H, V, G) and not persons:
                    flag("ppe_no_person_in_image", b)
        print(f"  {src}: {len(index)} ảnh", flush=True)

    with open(out / "content_flags.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "image", "check", "cls", "box", "detail"])
        w.writeheader()
        w.writerows(flags)
    tab = collections.Counter((fl["source"], fl["check"]) for fl in flags)
    imgs = collections.defaultdict(set)
    for fl in flags:
        imgs[(fl["source"], fl["check"])].add(fl["image"])
    print(f"\n{len(flags)} hộp đáng ngờ:")
    for (src, k), v in sorted(tab.items()):
        print(f"  {src:17s} {k:24s} {v:6d} hộp / {len(imgs[(src, k)]):5d} ảnh")
    print(f"Đã ghi {out.relative_to(ROOT)}/content_flags.csv")


def missing_person(cfg, out, rerun):
    """Chạy mô hình COCO tìm người; liệt kê người máy thấy mà chưa có hộp person."""
    m = cfg["missing_person"]
    P = next(k for k, v in CLASSES.items() if v == "person")
    preds_path = out / "person_preds.csv"
    items = []
    for src in m["sources"]:
        with open(CONVERTED / src / "index.csv", encoding="utf-8") as f:
            items += [(src, r) for r in csv.DictReader(f) if r.get("reject") != "1"]

    if rerun or not preds_path.exists():
        import os
        os.environ.setdefault("YOLO_AUTOINSTALL", "False")  # không để Ultralytics tự cài gói
        from ultralytics import YOLO
        model = YOLO(str(ROOT / m["model"]))
        coco_person = next(k for k, v in model.names.items() if v == "person")
        t0 = time.time()
        with open(preds_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["source", "image", "conf", "cx", "cy", "w", "h"])
            for n, (src, r) in enumerate(items, 1):
                res = model.predict(str(ROOT / r["image"]), imgsz=m["imgsz"], conf=m["save_conf"],
                                    classes=[coco_person], verbose=False)[0]
                for (cx, cy, bw, bh), c in zip(res.boxes.xywhn.cpu().numpy(), res.boxes.conf.cpu().numpy()):
                    w.writerow([src, r["image"], f"{c:.3f}", f"{cx:.6f}", f"{cy:.6f}", f"{bw:.6f}", f"{bh:.6f}"])
                if n % 500 == 0 or n == len(items):
                    el = time.time() - t0
                    print(f"  yolo person: {n}/{len(items)}  ({el / 60:.1f} phút, còn ~{el / n * (len(items) - n) / 60:.1f})",
                          flush=True)

    preds = collections.defaultdict(list)
    with open(preds_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            preds[r["image"]].append((float(r["conf"]), P, *(float(r[k]) for k in ("cx", "cy", "w", "h"))))
    rows = []
    for src, r in items:
        with Image.open(ROOT / r["image"]) as im:
            W, Hh = im.size
        scale = m["imgsz"] / max(W, Hh)
        labeled = [b for b in check_label(ROOT / r["label"], 1.0)[0] if b[0] == P]
        for conf, *b in preds[r["image"]]:
            hpx = b[4] * Hh * scale
            if conf < m["list_conf"] or hpx < m["min_height_px"]:
                continue
            best = max((iou(b, l) for l in labeled), default=0.0)
            if best < m["match_iou"]:
                rows.append(dict(source=src, image=r["image"], conf=f"{conf:.3f}", box=" ".join(f"{v:.6f}" for v in b[1:]),
                                 height_px=f"{hpx:.0f}", best_iou=f"{best:.2f}", n_person_labeled=len(labeled)))
    rows.sort(key=lambda x: (x["source"], -float(x["conf"])))
    with open(out / "missing_person.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "image", "conf", "box", "height_px", "best_iou", "n_person_labeled"])
        w.writeheader()
        w.writerows(rows)
    by = collections.Counter(x["source"] for x in rows)
    imgs = collections.Counter(s for s, _ in {(x["source"], x["image"]) for x in rows})
    print(f"\nNgười máy thấy (conf >= {m['list_conf']}) mà chưa có hộp person:")
    for s in m["sources"]:
        print(f"  {s:17s} {by[s]:5d} hộp / {imgs[s]:5d} ảnh")
    print(f"Đã ghi {out.relative_to(ROOT)}/person_preds.csv, missing_person.csv")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--technical", action="store_true")
    p.add_argument("--duplicates", action="store_true")
    p.add_argument("--content", action="store_true")
    p.add_argument("--missing-person", action="store_true")
    p.add_argument("--rerun", action="store_true", help="--missing-person: chạy lại mô hình dù đã có person_preds.csv")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not (args.technical or args.duplicates or args.content or args.missing_person):
        sys.exit("Chọn phần cần chạy, vd. --technical")
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    out = ROOT / cfg["out_dir"]
    out.mkdir(parents=True, exist_ok=True)
    if args.missing_person:
        missing_person(cfg, out, args.rerun)
    if args.content:
        content(cfg, out)
    if args.duplicates:
        duplicates(cfg, out)
    if not args.technical:
        return

    issues, stats = technical(cfg)
    with open(out / "technical_issues.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "image", "issue"])
        w.writeheader()
        w.writerows(issues)
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    kinds = collections.Counter((i["source"], i["issue"].split(":")[-1].strip() if "dòng" in i["issue"] else i["issue"])
                                for i in issues)
    print(f"\nTổng {len(issues)} lỗi:")
    for (src, k), v in sorted(kinds.items()):
        print(f"  {src:17s} {v:6d}  {k}")
    print(f"Đã ghi {out.relative_to(ROOT)}/technical_issues.csv, stats.json")


if __name__ == "__main__":
    main()
