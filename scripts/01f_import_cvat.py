"""Bước 1 (phụ): nhập nhãn đã gán trên CVAT về data/ppe4/converted/<bộ>/.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/01f_import_cvat.py --dry-run   # chỉ đọc và in thống kê, không ghi file
    python scripts/01f_import_cvat.py

Đọc trong data/ppe4/converted/<bộ>/cvat/:
    <bộ>_partXX_done_cvat.zip   bản export "CVAT for images 1.1" của từng task (giữ nguồn hộp và tag)
    <bộ>_review_images.csv      ảnh nào chỉ có máy duyệt (status = machine_reviewed)
    <bộ>_reject.csv             ảnh bị loại (ảnh mờ, tối hoặc găng thiếu hộp)
Ghi ra:
    labels/*.txt                nhãn YOLO 4 lớp mới, có găng tay (ghi đè bản của 01_convert_labels.py)
    labels_before_cvat/         bản sao nhãn cũ chưa có găng, chỉ tạo ở lần chạy đầu
    index.csv                   thêm cột review (human / machine) và reject (1 = loại), gloves_labeled = 1
    cvat/<bộ>_cvat_changes.csv  hộp person/helmet/vest được người thêm hoặc xóa so với nhãn gốc
    cvat/<bộ>_cvat_import.json  thống kê
Chạy lại 01_convert_labels.py sẽ ghi đè labels/ và index.csv: khi đó chạy lại script này.
"""

import argparse
import collections
import csv
import json
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONVERTED = ROOT / "data" / "ppe4" / "converted"
LABEL_MAP = ROOT / "configs" / "label_map.yaml"
TAGS_IGNORED = {"check"}  # tag dùng trong lúc duyệt, không mang nghĩa nhãn


def read_cvat_zip(path):
    """Mỗi ảnh: (rộng, cao, danh sách hộp (nhãn, x1, y1, x2, y2, nguồn), danh sách tag)."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("annotations.xml"))
    images = {}
    for im in root.iter("image"):
        boxes = [(b.get("label"), *(float(b.get(k)) for k in ("xtl", "ytl", "xbr", "ybr")), b.get("source"))
                 for b in im.iter("box")]
        tags = [t.get("label") for t in im.iter("tag")]
        if any(True for _ in im.iter("polygon")) or any(True for _ in im.iter("points")):
            sys.exit(f"{path.name}: ảnh {im.get('name')} có hình không phải hộp, script chỉ hỗ trợ hộp.")
        images[Path(im.get("name")).name] = (float(im.get("width")), float(im.get("height")), boxes, tags)
    return images


def to_yolo(x1, y1, x2, y2, w, h):
    """Cắt hộp vào trong ảnh rồi đổi sang (x tâm, y tâm, rộng, cao) chuẩn hóa; None nếu hộp rỗng."""
    x1, x2 = max(0.0, min(x1, w)), max(0.0, min(x2, w))
    y1, y2 = max(0.0, min(y1, h)), max(0.0, min(y2, h))
    if x2 - x1 < 1 or y2 - y1 < 1:
        return None
    return (x1 + x2) / 2 / w, (y1 + y2) / 2 / h, (x2 - x1) / w, (y2 - y1) / h


def read_yolo(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c, *v = line.split()
            rows.append((int(c), *map(float, v)))
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="chv")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    classes = yaml.safe_load(LABEL_MAP.read_text(encoding="utf-8"))["classes"]
    class_id = {v: k for k, v in classes.items()}
    out = CONVERTED / args.source
    cvat_dir = out / "cvat"

    # 1. đọc các bản export
    zips = sorted(cvat_dir.glob(f"{args.source}_part[0-9][0-9]_done_cvat.zip"))
    if not zips:
        sys.exit(f"Không thấy {args.source}_partXX_done_cvat.zip trong {cvat_dir}")
    cvat, part_of = {}, {}
    for z in zips:
        part = z.name.replace("_done_cvat.zip", "")
        for name, v in read_cvat_zip(z).items():
            if name in cvat:
                sys.exit(f"Ảnh {name} có trong nhiều task ({part_of[name]}, {part}).")
            cvat[name], part_of[name] = v, part
    with open(out / "index.csv", encoding="utf-8") as f:
        index = list(csv.DictReader(f))
    names = {Path(r["image"]).name for r in index}
    if names != set(cvat):
        sys.exit(f"Số ảnh không khớp: index.csv {len(names)}, CVAT {len(cvat)}; "
                 f"thiếu trên CVAT {sorted(names - set(cvat))[:5]}, thừa {sorted(set(cvat) - names)[:5]}")

    # 2. trạng thái duyệt và danh sách loại
    machine = set()
    review_csv = cvat_dir / f"{args.source}_review_images.csv"
    if review_csv.exists():
        with open(review_csv, encoding="utf-8") as f:
            machine = {r["image"] for r in csv.DictReader(f) if r["status"] == "machine_reviewed"}
    reject = {}
    reject_csv = cvat_dir / f"{args.source}_reject.csv"
    if reject_csv.exists():
        with open(reject_csv, encoding="utf-8") as f:
            reject = {r["image"]: r["kind"] for r in csv.DictReader(f)}
    tag_reject = {n for n, v in cvat.items() if "reject" in v[3]}
    unknown_tags = {t for v in cvat.values() for t in v[3]} - TAGS_IGNORED - {"reject"}
    if unknown_tags:
        sys.exit(f"Có tag lạ trên CVAT: {unknown_tags}")
    if missing := (set(reject) | machine) - set(cvat):
        sys.exit(f"Ảnh trong CSV không có trên CVAT: {sorted(missing)[:5]}")

    # 3. đổi sang YOLO, so với nhãn gốc
    old_dir = out / "labels_before_cvat" if (out / "labels_before_cvat").exists() else out / "labels"
    new_labels, changes = {}, []
    count = collections.Counter()
    for name, (w, h, boxes, _) in sorted(cvat.items()):
        lines = []
        for label, x1, y1, x2, y2, src in boxes:
            yolo = to_yolo(x1, y1, x2, y2, w, h)
            if yolo is None:
                count["bỏ hộp rỗng"] += 1
                continue
            lines.append((class_id[label], *yolo))
            count[(label, src)] += 1
        new_labels[name] = lines
        # hộp person/helmet/vest gốc so với hộp cùng lớp hiện tại (sai lệch tối đa 1 px)
        old = [r for r in read_yolo(old_dir / f"{Path(name).stem}.txt") if r[0] != class_id["gloves"]]
        cur = [r for r in lines if r[0] != class_id["gloves"]]
        tol = max(1 / w, 1 / h) * 1.5
        for kind, a, b in (("removed", old, cur), ("added", cur, old)):
            pool = list(b)
            for r in a:
                m = next((q for q in pool if q[0] == r[0] and max(abs(x - y) for x, y in zip(r[1:], q[1:])) <= tol), None)
                if m:
                    pool.remove(m)
                else:
                    changes.append(dict(part=part_of[name], image=name, change=kind, label=classes[r[0]],
                                        x=f"{r[1]:.6f}", y=f"{r[2]:.6f}", w=f"{r[3]:.6f}", h=f"{r[4]:.6f}"))

    # 4. bảng index mới
    rows = []
    for r in index:
        name = Path(r["image"]).name
        c = collections.Counter(classes[l[0]] for l in new_labels[name])
        r.update({f"n_{k}": c[k] for k in classes.values()}, gloves_labeled=1,
                 review="machine" if name in machine else "human",
                 reject=1 if name in reject or name in tag_reject else 0)
        rows.append(r)

    kept = [r for r in rows if not r["reject"]]
    summary = {
        "zips": [z.name for z in zips],
        "images": len(rows),
        "rejected": {"total": sum(r["reject"] for r in rows),
                     "by_kind": dict(collections.Counter(reject.values())), "tag_reject_on_cvat": len(tag_reject)},
        "kept_by_review": dict(collections.Counter(r["review"] for r in kept)),
        "boxes_all": {k: sum(int(r[f"n_{k}"]) for r in rows) for k in classes.values()},
        "boxes_kept": {k: sum(int(r[f"n_{k}"]) for r in kept) for k in classes.values()},
        "boxes_by_source": {f"{k[0]}/{k[1]}": v for k, v in sorted(count.items(), key=str) if isinstance(k, tuple)},
        "empty_boxes_dropped": count["bỏ hộp rỗng"],
        "person_helmet_vest_changes": dict(collections.Counter(f"{c['label']}/{c['change']}" for c in changes)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if args.dry_run:
        print("--dry-run: không ghi file.")
        return

    # 5. ghi
    if not (out / "labels_before_cvat").exists():
        shutil.copytree(out / "labels", out / "labels_before_cvat")
        shutil.copy(out / "index.csv", out / "labels_before_cvat" / "index.csv")
        print("Đã sao lưu nhãn cũ vào labels_before_cvat/")
    for name, lines in new_labels.items():
        (out / "labels" / f"{Path(name).stem}.txt").write_text(
            "".join(f"{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n" for c, x, y, w, h in lines), encoding="utf-8")
    with open(out / "index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(cvat_dir / f"{args.source}_cvat_changes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["part", "image", "change", "label", "x", "y", "w", "h"])
        w.writeheader()
        w.writerows(changes)
    (cvat_dir / f"{args.source}_cvat_import.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Đã ghi {len(new_labels)} file nhãn, index.csv, {args.source}_cvat_changes.csv ({len(changes)} dòng), "
          f"{args.source}_cvat_import.json")


if __name__ == "__main__":
    main()
