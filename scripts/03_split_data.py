"""Bước 1: chia train/val/test theo nhóm ảnh và tạo bộ dữ liệu huấn luyện (docs/spec.md mục 2.3).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03_split_data.py --dry-run     # chỉ chia và in bảng, không ghi file
    python scripts/03_split_data.py               # chia, chép ảnh, ghi nhãn đã sửa
    python scripts/03_split_data.py --overwrite   # xóa thư mục kết quả cũ (do script này tạo) rồi làm lại

Đọc data/ppe4/converted/<bộ>/index.csv và labels/, data/ppe4/check/groups.csv và fixes.csv;
tham số trong configs/split.yaml. Không sửa converted/ hay data/raw/. Ghi:
    data/ppe4/dataset/      images/{train,val,test}, labels/{train,val,test}, data.yaml, split_summary.json
    data/ppe4/pictor_test/  images/test, labels/test, data.yaml (Pictor-PPE, kiểm thử ngoài)
    data/ppe4/stats.csv     mỗi ảnh một dòng: bộ, ảnh, group_id, tập, lý do buộc vào train, số hộp từng lớp
"""

import argparse
import collections
import csv
import json
import random
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "split.yaml"
CONVERTED = ROOT / "data" / "ppe4" / "converted"
CLASSES = yaml.safe_load((ROOT / "configs" / "label_map.yaml").read_text(encoding="utf-8"))["classes"]
CLASS_ID = {name: c for c, name in CLASSES.items()}
SPLITS = ["train", "val", "test"]


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_label(path):
    """Danh sách dòng nhãn dạng (lớp, [cx, cy, w, h], chuỗi gốc)."""
    boxes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            parts = line.split()
            boxes.append((int(parts[0]), [float(x) for x in parts[1:]], " ".join(parts)))
    return boxes


def apply_fixes(boxes, rows, tol):
    """Áp các dòng fixes.csv lên nhãn một ảnh. Dòng nào không khớp thì báo lỗi, không bỏ qua."""
    boxes = list(boxes)
    for r in rows:
        c = CLASS_ID[r["cls"]]
        xywh = [float(x) for x in r["box"].split()]
        same = [i for i, (bc, bx, _) in enumerate(boxes)
                if bc == c and all(abs(a - b) <= tol for a, b in zip(bx, xywh))]
        if r["action"] == "delete":
            if not same:
                raise ValueError(f"delete không khớp hộp nào: {r['image']} {r['cls']} {r['box']}")
            del boxes[same[0]]  # dòng trùng y hệt: chỉ xóa một bản
        elif r["action"] == "add":
            if same:
                raise ValueError(f"add trùng hộp đã có: {r['image']} {r['cls']} {r['box']}")
            boxes.append((c, xywh, f"{c} {r['box']}"))
        else:
            raise ValueError(f"action lạ: {r['action']}")
    return boxes


def load_images(src, groups, fixes, tol):
    """Ảnh không bị reject của một bộ, kèm nhãn đã áp fixes và lý do buộc vào train (nếu có)."""
    images = []
    for r in read_csv(CONVERTED / src / "index.csv"):
        key = (src, r["image"])
        if r.get("reject") == "1":
            if key in fixes:
                print(f"  bỏ qua {len(fixes[key])} dòng fixes của ảnh reject {r['image']}")
            continue
        rows = fixes.get(key, [])
        boxes = apply_fixes(read_label(ROOT / r["label"]), rows, tol)
        reasons = []
        if r.get("review") == "machine":
            reasons.append("machine_review")
        if any(x["train_only"] == "1" for x in rows):
            reasons.append("fixes_train_only")
        images.append(dict(
            source=src, image=r["image"], group_id=groups[key]["group_id"],
            group_sources=groups[key]["group_sources"], boxes=boxes, forced=";".join(reasons),
            n_add=sum(x["action"] == "add" for x in rows), n_delete=sum(x["action"] == "delete" for x in rows),
            counts=collections.Counter(CLASSES[b[0]] for b in boxes)))
    return images


def vector(imgs):
    """Đóng góp của một nhóm vào các chiều cần cân bằng: số ảnh từng bộ, số hộp từng lớp của từng bộ."""
    v = collections.Counter()
    for im in imgs:
        v[("images", im["source"])] += 1
        for name, n in im["counts"].items():
            v[(name, im["source"])] += n
    return v


def split_groups(images, ratios, seed):
    """Gán mỗi nhóm vào một tập. Nhóm có ảnh buộc vào train đi train trước; các nhóm còn lại
    lần lượt (lớn trước) vào tập đang thiếu nhiều nhất so với mục tiêu, tính theo tỉ lệ thiếu."""
    by_group = collections.defaultdict(list)
    for im in images:
        by_group[im["group_id"]].append(im)
    total = vector(images)
    target = {s: {d: ratios[s] * n for d, n in total.items()} for s in SPLITS}
    current = {s: collections.Counter() for s in SPLITS}
    assign = {}

    free = []
    for g, imgs in by_group.items():
        if any(im["forced"] for im in imgs):
            assign[g] = "train"
            current["train"].update(vector(imgs))
        else:
            free.append(g)
    random.Random(seed).shuffle(free)
    free.sort(key=lambda g: -len(by_group[g]))  # sort ổn định: nhóm cùng cỡ giữ thứ tự đã xáo

    for g in free:
        v = vector(by_group[g])
        score = {s: sum(n * (target[s][d] - current[s][d]) / max(target[s][d], 1) for d, n in v.items())
                 for s in SPLITS}
        best = max(SPLITS, key=lambda s: score[s])
        assign[g] = best
        current[best].update(v)
    return assign


def summary(images):
    """Bảng số ảnh và số hộp theo tập × bộ, kèm tỉ lệ so với tổng của bộ đó."""
    table = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for im in images:
        t = table[im["split"]][im["source"]]
        t["images"] += 1
        t["forced_train"] += bool(im["forced"])
        t.update(im["counts"])
    return {s: {src: dict(c) for src, c in table[s].items()} for s in table}


def print_summary(table, sources):
    cols = ["images"] + list(CLASSES.values())
    for src in sources + ["ALL"]:
        print(f"\n  {src}")
        print("  " + "tập".ljust(8) + "".join(c.rjust(16) for c in cols))
        tot = collections.Counter()
        rows = {}
        for s in SPLITS:
            c = collections.Counter()
            for name, cnt in table.get(s, {}).items():
                if src in ("ALL", name):
                    c.update(cnt)
            rows[s] = c
            tot.update(c)
        for s in SPLITS:
            cells = "".join(f"{rows[s][c]:>8} ({rows[s][c] / max(tot[c], 1) * 100:4.1f}%)" for c in cols)
            print("  " + s.ljust(8) + cells)


def check_split(images, sources):
    """Kiểm tra theo spec 2.3; trả về danh sách cảnh báo."""
    warns = []
    split_of_group = collections.defaultdict(set)
    for im in images:
        split_of_group[im["group_id"]].add(im["split"])
        if im["forced"] and im["split"] != "train":
            warns.append(f"ảnh buộc vào train lại nằm ở {im['split']}: {im['image']}")
    warns += [f"nhóm {g} nằm ở nhiều tập {sorted(s)}" for g, s in split_of_group.items() if len(s) > 1]
    for s in ["val", "test"]:
        present = {im["source"] for im in images if im["split"] == s}
        warns += [f"tập {s} không có ảnh của {src}" for src in sources if src not in present]
        if not any(im["counts"]["gloves"] for im in images if im["split"] == s):
            warns.append(f"tập {s} không có găng tay")
    return warns


def out_name(im):
    return f"{im['source']}__{Path(im['image']).name}"


def write_set(images, out_dir, split_key, folder=None):
    """Chép ảnh và ghi nhãn đã sửa vào out_dir/images/<tập>, out_dir/labels/<tập> (folder: thư mục cố định)."""
    for i, im in enumerate(images, 1):
        s = folder or im[split_key]
        img_dst = out_dir / "images" / s / out_name(im)
        lbl_dst = out_dir / "labels" / s / (Path(out_name(im)).stem + ".txt")
        img_dst.parent.mkdir(parents=True, exist_ok=True)
        lbl_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / im["image"], img_dst)
        lbl_dst.write_text("".join(b[2] + "\n" for b in im["boxes"]), encoding="utf-8")
        if i % 1000 == 0 or i == len(images):
            print(f"  chép {i}/{len(images)}", flush=True)


def write_data_yaml(path, splits, comment):
    # Không ghi khóa `path`: Ultralytics lấy thư mục chứa data.yaml làm gốc, chạy được cả trên máy lẫn Kaggle.
    lines = [f"# {comment}"] + [f"{k}: {v}" for k, v in splits.items()] + ["names:"]
    lines += [f"  {c}: {name}" for c, name in CLASSES.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="chỉ chia và in bảng, không ghi file")
    ap.add_argument("--overwrite", action="store_true", help="xóa thư mục kết quả cũ rồi ghi lại")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    ratios = cfg["ratios"]
    if abs(sum(ratios.values()) - 1) > 1e-9 or set(ratios) != set(SPLITS):
        sys.exit(f"ratios phải có đủ {SPLITS} và cộng lại bằng 1: {ratios}")
    sources, ext = cfg["sources"], cfg["external_test"]
    out_dir, ext_dir = ROOT / cfg["out_dir"], ROOT / cfg["external_out_dir"]

    groups = {(r["source"], r["image"]): r for r in read_csv(ROOT / cfg["groups"])}
    fixes = collections.defaultdict(list)
    for r in read_csv(ROOT / cfg["fixes"]):
        fixes[(r["source"], r["image"])].append(r)

    print("Đọc nhãn và áp fixes.csv")
    images = [im for src in sources for im in load_images(src, groups, fixes, cfg["box_match_tol"])]
    external = load_images(ext, groups, fixes, cfg["box_match_tol"])
    known = {(src, r["image"]) for src in sources + [ext] for r in read_csv(CONVERTED / src / "index.csv")}
    unused = [k for k in fixes if k not in known]
    if unused:
        sys.exit(f"{len(unused)} ảnh trong fixes.csv không có trong index.csv, vd {unused[0]}")
    print(f"  {len(images)} ảnh để chia, {len(external)} ảnh {ext}; "
          f"áp {sum(im['n_add'] for im in images + external)} add, "
          f"{sum(im['n_delete'] for im in images + external)} delete")

    names = [out_name(im) for im in images + external]
    stems = [Path(n).stem for n in names]
    if len(set(stems)) != len(stems):
        dup = [n for n, k in collections.Counter(stems).items() if k > 1]
        sys.exit(f"{len(dup)} tên file trùng sau khi thêm tiền tố bộ, vd {dup[0]}")

    assign = split_groups(images, ratios, cfg["seed"])
    for im in images:
        im["split"] = assign[im["group_id"]]
    # Pictor: loại ảnh cùng nhóm với ảnh của bộ khác (trùng với dữ liệu huấn luyện).
    for im in external:
        im["split"] = "external_test" if im["group_sources"] == ext else "excluded_duplicate"

    table = summary(images)
    print("\nKết quả chia (số lượng và % so với tổng của bộ / lớp đó):")
    print_summary(table, sources)
    n_excl = sum(im["split"] != "external_test" for im in external)
    print(f"\n  {ext}: {len(external) - n_excl} ảnh kiểm thử ngoài, loại {n_excl} ảnh trùng dữ liệu huấn luyện")

    warns = check_split(images, sources)
    print("\nKiểm tra:", "không có cảnh báo" if not warns else "")
    for w in warns[:20]:
        print("  CẢNH BÁO:", w)
    if args.dry_run:
        print("\n--dry-run: không ghi file.")
        return

    for d in (out_dir, ext_dir):
        if d.exists() and any(d.iterdir()):
            if not args.overwrite:
                sys.exit(f"{d} đã có dữ liệu; chạy lại với --overwrite để ghi đè.")
            shutil.rmtree(d)

    print(f"\nGhi {out_dir.relative_to(ROOT)}")
    write_set(images, out_dir, "split")
    write_data_yaml(out_dir / "data.yaml", {s: f"images/{s}" for s in SPLITS},
                    "Bộ 4 lớp SH17 + CHV + Construction-PPE, tạo bởi scripts/03_split_data.py")
    (out_dir / "split_summary.json").write_text(
        json.dumps(dict(config=cfg, table=table, warnings=warns), ensure_ascii=False, indent=2), encoding="utf-8")

    kept = [im for im in external if im["split"] == "external_test"]
    print(f"Ghi {ext_dir.relative_to(ROOT)}")
    write_set(kept, ext_dir, "split", folder="test")
    write_data_yaml(ext_dir / "data.yaml", {s: "images/test" for s in SPLITS},
                    f"{ext}: chỉ kiểm thử ngoài, không có nhãn găng tay. train/val trỏ vào test chỉ để "
                    "Ultralytics chấp nhận file; dùng model.val(split='test'), không huấn luyện trên tập này")

    stats_path = ROOT / cfg["stats_csv"]
    with open(stats_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "image", "file", "group_id", "split", "train_only_reason", "fix_add", "fix_delete"]
                   + [f"n_{c}" for c in CLASSES.values()])
        for im in images + external:
            w.writerow([im["source"], im["image"], out_name(im), im["group_id"], im["split"], im["forced"],
                        im["n_add"], im["n_delete"]] + [im["counts"][c] for c in CLASSES.values()])
    print(f"Ghi {stats_path.relative_to(ROOT)}\nXong.")


if __name__ == "__main__":
    main()
