"""Thử nghiệm 6 lớp: lập danh sách hộp kính, giày gốc và vẽ bảng ảnh để duyệt. Chỉ đọc data/raw/ và data/ppe4/stats.csv.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03c_ppe6_review_sheets.py --summary
    python scripts/03c_ppe6_review_sheets.py --target goggles --source sh17 --n 96 --name goggles_sh17_01
    python scripts/03c_ppe6_review_sheets.py --mark-small boots     # hộp quá nhỏ: ghi `unclear`, note `too_small`
    python scripts/03c_ppe6_review_sheets.py --apply goggles_sh17_01_01 --default ordinary --safety b00001 --unclear b00002

Tham số: configs/ppe6.yaml mục `review`. Ghi vào data/ppe6/review/:
    boxes.csv             mỗi hộp một dòng: box_id, bộ, lớp đích, tập theo ppe4, group_id, ảnh gốc, tọa độ YOLO
    sheets/<name>_NN.jpg  bảng ảnh, hộp đang xét viền đỏ, số ở góc là box_id
    sheets/<name>_NN.txt  các box_id của bảng đó, dùng cho --apply
    decisions.csv         người hoặc máy điền: box_id, label (safety/ordinary/unclear), reviewer (human/claude), note

`--apply` ghi quyết định cho một bảng: mọi hộp lấy nhãn `--default`, trừ các hộp nêu trong --safety, --ordinary, --unclear.
Chỉ lấy ảnh có trong stats.csv, nên ảnh đã loại ở ppe4 không quay lại. Hộp đã có trong decisions.csv không vẽ lại.
"""

import argparse
import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ppe6" / "review"
BOXES = OUT / "boxes.csv"
DECISIONS = OUT / "decisions.csv"
FIELDS = ["box_id", "source", "target", "split", "group_id", "image", "cx", "cy", "w", "h"]


def label_path(image):
    """Nhãn gốc nằm cùng chỗ với ảnh, đổi `images` thành `labels` (Construction-PPE có thêm thư mục tập)."""
    p = Path(image)
    parts = ["labels" if x == "images" else x for x in p.parent.parts]
    return ROOT / Path(*parts) / f"{p.stem}.txt"


def build_index(cfg):
    """Quét nhãn gốc theo thứ tự cố định để box_id không đổi giữa các lần chạy."""
    stats = csv.DictReader((ROOT / "data" / "ppe4" / "stats.csv").open(encoding="utf-8"))
    sources = cfg["review"]["sources"]
    rows = []
    for r in sorted((r for r in stats if r["source"] in sources), key=lambda r: r["image"]):
        lab = label_path(r["image"])
        if not lab.exists():
            continue
        wanted = {str(code): target for target, code in sources[r["source"]].items()}
        for line in lab.read_text(encoding="utf-8").splitlines():
            t = line.split()
            if t and t[0] in wanted:
                rows.append(dict(box_id=f"b{len(rows) + 1:05d}", source=r["source"], target=wanted[t[0]], split=r["split"],
                                 group_id=r["group_id"], image=r["image"], cx=t[1], cy=t[2], w=t[3], h=t[4]))
    OUT.mkdir(parents=True, exist_ok=True)
    with BOXES.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    return rows


def read_decisions():
    if not DECISIONS.exists():
        return {}
    return {r["box_id"]: r for r in csv.DictReader(DECISIONS.open(encoding="utf-8"))}


def tile(im, box, size, context):
    """Ô vuông quanh hộp, viền đỏ, số box_id ở góc."""
    w, h = im.size
    cx, cy, bw, bh = (float(box[k]) for k in ("cx", "cy", "w", "h"))
    x1, y1, x2, y2 = (cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h
    half = max(x2 - x1, y2 - y1) * (0.5 + context)
    a, b = cx * w - half, cy * h - half
    s = size / (2 * half)
    out = im.crop((int(a), int(b), int(a + 2 * half), int(b + 2 * half))).resize((size, size))
    d = ImageDraw.Draw(out)
    d.rectangle(((x1 - a) * s, (y1 - b) * s, (x2 - a) * s, (y2 - b) * s), outline="red", width=2)
    d.rectangle((0, 0, 46, 12), fill="black")
    d.text((2, 0), box["box_id"], fill="yellow")
    return out


def draw_sheets(picked, name, sheet):
    cols, rows, size = sheet["cols"], sheet["rows"], sheet["tile_px"]
    tiles = {}
    by_image = defaultdict(list)
    for b in picked:
        by_image[b["image"]].append(b)
    for image, boxes in by_image.items():
        with Image.open(ROOT / image) as raw:
            im = ImageOps.exif_transpose(raw).convert("RGB")
        for b in boxes:
            tiles[b["box_id"]] = tile(im, b, size, sheet["context"])
    (OUT / "sheets").mkdir(parents=True, exist_ok=True)
    per = cols * rows
    for n in range(0, len(picked), per):
        page = Image.new("RGB", (cols * size, rows * size), "white")
        for i, b in enumerate(picked[n:n + per]):
            page.paste(tiles[b["box_id"]], ((i % cols) * size, (i // cols) * size))
        path = OUT / "sheets" / f"{name}_{n // per + 1:02d}.jpg"
        page.save(path, quality=88)
        path.with_suffix(".txt").write_text("".join(b["box_id"] + "\n" for b in picked[n:n + per]), encoding="utf-8")
        print(path.relative_to(ROOT), flush=True)


def mark_small(boxes, target, min_side, imgsz):
    """Hộp có cạnh dài dưới `min_side` px ở đầu vào `imgsz` không nhìn ra loại gì. Không gán nhãn, nhưng không loại ảnh."""
    done = read_decisions()
    sizes = {}
    rows = []
    for b in boxes:
        if b["target"] != target or b["box_id"] in done:
            continue
        if b["image"] not in sizes:
            with Image.open(ROOT / b["image"]) as im:
                w, h = im.size
                if im.getexif().get(274, 1) in (5, 6, 7, 8):
                    w, h = h, w
            sizes[b["image"]] = (w, h)
        w, h = sizes[b["image"]]
        if max(float(b["w"]) * w, float(b["h"]) * h) * imgsz / max(w, h) < min_side:
            rows.append((b["box_id"], "unclear", "auto", "too_small"))
    with DECISIONS.open("a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"Đánh dấu too_small: {len(rows)} hộp {target}")


def apply_sheet(args):
    """Ghi quyết định của một bảng vào decisions.csv. Hộp đã có quyết định thì giữ nguyên."""
    ids = (OUT / "sheets" / f"{args.apply}.txt").read_text(encoding="utf-8").split()
    chosen = {b: "safety" for b in args.safety + args.snow} | {b: "ordinary" for b in args.ordinary} | {b: "unclear" for b in args.unclear}
    wrong = set(chosen) - set(ids)
    if wrong:
        sys.exit(f"Không thuộc bảng {args.apply}: {sorted(wrong)}")
    done = read_decisions()
    new = [(b, chosen.get(b, args.default)) for b in ids if b not in done]
    is_new = not DECISIONS.exists()
    with DECISIONS.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["box_id", "label", "reviewer", "note"])
        w.writerows((b, label, args.reviewer, "scene_snow" if b in args.snow else "" if b in chosen else args.note) for b, label in new)
    print(args.apply, dict(Counter(x[1] for x in new)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", action="store_true", help="chỉ in số hộp đã và chưa duyệt")
    ap.add_argument("--target", choices=["goggles", "boots"])
    ap.add_argument("--source", choices=["sh17", "construction_ppe"])
    ap.add_argument("--n", type=int, default=48, help="số hộp chưa duyệt lấy ngẫu nhiên")
    ap.add_argument("--name", help="tiền tố tên bảng ảnh")
    ap.add_argument("--mark-small", choices=["goggles", "boots"])
    ap.add_argument("--apply", help="tên bảng, vd goggles_sh17_01_01")
    ap.add_argument("--default", choices=["safety", "ordinary", "unclear"], default="ordinary")
    ap.add_argument("--safety", nargs="*", default=[])
    ap.add_argument("--snow", nargs="*", default=[], help="safety, thuộc một cảnh lặp nhiều lần (note scene_snow)")
    ap.add_argument("--ordinary", nargs="*", default=[])
    ap.add_argument("--unclear", nargs="*", default=[])
    ap.add_argument("--reviewer", choices=["human", "claude"], default="claude")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if args.apply:
        apply_sheet(args)
        return
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))

    boxes = list(csv.DictReader(BOXES.open(encoding="utf-8"))) if BOXES.exists() else build_index(cfg)
    done = read_decisions()
    if args.mark_small:
        mark_small(boxes, args.mark_small, cfg["review"]["min_side_px"], cfg["review"]["imgsz"])
        done = read_decisions()
    print("Hộp theo bộ, lớp, tập:", dict(sorted(Counter((b["source"], b["target"], b["split"]) for b in boxes).items())))
    print("Đã duyệt:", dict(sorted(Counter((d["label"], d["reviewer"]) for d in done.values()).items())), f"/ {len(boxes)}")
    if args.summary or not args.name:
        return
    todo = [b for b in boxes if b["box_id"] not in done and b["target"] == args.target and b["source"] == args.source]
    picked = random.Random(cfg["review"]["seed"]).sample(todo, min(args.n, len(todo)))
    picked.sort(key=lambda b: b["image"])   # ảnh cùng cảnh nằm cạnh nhau, duyệt nhất quán hơn
    draw_sheets(picked, args.name, cfg["review"]["sheet"])


if __name__ == "__main__":
    main()
