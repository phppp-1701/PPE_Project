"""Bước 2 (r3): tạo bộ phụ cho train từ ảnh train đã có. Không đụng val, test, Pictor hay video.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03b_make_extra_train.py --dry-run    # chỉ đếm
    python scripts/03b_make_extra_train.py

Tham số: configs/train.yaml mục `extra`. Ghi vào data/ppe4/r3_extra/:
    images/train, labels/train   ảnh cắt từng người nhỏ và nhãn YOLO của ảnh cắt, tên crop__<ảnh>__<số>.jpg
    oversample.txt               ảnh train có găng được thêm một bản khi huấn luyện (lấy mẫu nhiều hơn, spec 2.4)
    summary.json                 số lượng, tham số đã dùng

Ảnh cắt mô phỏng lúc chạy (detector chế độ crop): thu ảnh về cạnh dài `video_side` như khung video, rồi cắt hộp người
nới `margin` mỗi phía. Chỉ lấy người cao dưới `max_person_px` đo ở đầu vào `imgsz`, tức nhóm hệ thống dò trên ảnh cắt.
Train có ít người nhỏ, nên phần còn thiếu tới `max_crops` lấy từ người lớn có PPE, thu nhỏ ảnh cắt về chiều cao ngẫu nhiên
trong `shrink_px` (tính ở khung video), mô phỏng người ở xa. Tên shrink__<ảnh>__<số>.jpg.
Hộp còn ít hơn `min_visible` diện tích trong ảnh cắt thì bỏ nhãn (spec 2.4).
"""

import argparse
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "ppe4" / "dataset"
OUT = ROOT / "data" / "ppe4" / "r3_extra"
PERSON, HELMET, VEST, GLOVES = 0, 1, 2, 3


def image_size(path):
    """(rộng, cao) sau khi xoay theo EXIF, không giải nén ảnh."""
    with Image.open(path) as im:
        w, h = im.size
        if im.getexif().get(274, 1) in (5, 6, 7, 8):
            w, h = h, w
    return w, h


def read_labels(path):
    rows = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [(int(r[0]), *map(float, r[1:5])) for r in rows]


def to_px(row, w, h):
    c, cx, cy, bw, bh = row
    return c, (cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h


def crop_box(person, w, h, margin):
    _, x1, y1, x2, y2 = person
    mw, mh = margin * (x2 - x1), margin * (y2 - y1)
    return max(0.0, x1 - mw), max(0.0, y1 - mh), min(float(w), x2 + mw), min(float(h), y2 + mh)


def crop_labels(boxes, box, min_visible):
    """Nhãn YOLO của các hộp trong ảnh cắt `box`. boxes: hộp pixel (c, x1, y1, x2, y2) trên ảnh gốc."""
    a, b, c2, d = box
    w, h = c2 - a, d - b
    out = []
    for c, x1, y1, x2, y2 in boxes:
        ix1, iy1, ix2, iy2 = max(x1, a), max(y1, b), min(x2, c2), min(y2, d)
        if ix2 <= ix1 or iy2 <= iy1:
            continue
        area = max((x2 - x1) * (y2 - y1), 1e-9)
        if (ix2 - ix1) * (iy2 - iy1) / area < min_visible:
            continue
        out.append((c, ((ix1 + ix2) / 2 - a) / w, ((iy1 + iy2) / 2 - b) / h, (ix2 - ix1) / w, (iy2 - iy1) / h))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "train.yaml").read_text(encoding="utf-8"))
    e, imgsz = cfg["extra"], cfg["train"]["imgsz"]
    rng = random.Random(e["seed"])

    images = {p.stem: p for p in (DATASET / "images" / "train").iterdir()}
    candidates, big, glove_images = [], [], []
    for i, lab in enumerate(sorted((DATASET / "labels" / "train").glob("*.txt")), 1):
        rows = read_labels(lab)
        if any(r[0] == GLOVES for r in rows):
            glove_images.append(images[lab.stem].name)
        persons = [r for r in rows if r[0] == PERSON]
        if persons:
            w, h = image_size(images[lab.stem])
            boxes = [to_px(r, w, h) for r in rows]
            s = imgsz / max(w, h)
            for k, r in enumerate(boxes):
                size = (r[4] - r[2]) * s
                if r[0] != PERSON or size < e["min_person_px"]:
                    continue
                labs = crop_labels(boxes, crop_box(r, w, h, e["margin"]), e["min_visible"])
                kinds = {x[0] for x in labs}
                rank = 0 if GLOVES in kinds else 1 if VEST in kinds or HELMET in kinds else 2
                if size < e["max_person_px"]:
                    candidates.append((rank, lab.stem, k))
                elif rank < 2:
                    big.append((rank, lab.stem, k))
        if i % 2000 == 0:
            print(f"  đã đọc {i} nhãn", flush=True)

    # Ưu tiên ảnh cắt có găng, rồi mũ/áo; giữ một phần không PPE làm mẫu âm; giới hạn số ảnh cắt mỗi ảnh gốc.
    rng.shuffle(candidates)
    chosen, per_image = [], Counter()
    quota = {0: e["max_crops"], 1: e["max_crops"], 2: int(e["max_crops"] * e["no_ppe_share"])}
    used = Counter()
    for rank, stem, k in sorted(candidates, key=lambda x: x[0]):
        if len(chosen) >= e["max_crops"] or per_image[stem] >= e["max_per_image"] or used[rank] >= quota[rank]:
            continue
        if rank < 2 and len(chosen) >= e["max_crops"] - quota[2]:
            continue
        chosen.append((rank, stem, k))
        per_image[stem] += 1
        used[rank] += 1
    # Phần còn thiếu: thu nhỏ người lớn có PPE, ưu tiên có găng.
    rng.shuffle(big)
    shrink = {}
    for rank, stem, k in sorted(big, key=lambda x: x[0]):
        if len(chosen) >= e["max_crops"]:
            break
        if per_image[stem] >= e["max_per_image"]:
            continue
        shrink[(stem, k)] = rng.uniform(*e["shrink_px"])
        chosen.append((rank, stem, k))
        per_image[stem] += 1
    rep = sorted(rng.sample(glove_images, min(e["oversample_gloves"], len(glove_images))))
    print(f"Ứng viên {len(candidates)} người nhỏ theo nhóm {Counter(c[0] for c in candidates)}; "
          f"người lớn có PPE {len(big)}; chọn {len(chosen)} (thu nhỏ {len(shrink)}) {dict(used)} từ {len(per_image)} ảnh; ảnh có găng {len(glove_images)}, lấy thêm {len(rep)}")
    if args.dry_run:
        return

    from ultralytics.utils.patches import imread  # cùng cách đọc (xoay EXIF) với Ultralytics

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "images" / "train").mkdir(parents=True)
    (OUT / "labels" / "train").mkdir(parents=True)
    by_image = defaultdict(list)
    for _, stem, k in chosen:
        by_image[stem].append(k)
    boxes_out = Counter()
    for i, (stem, ks) in enumerate(sorted(by_image.items()), 1):
        im = imread(str(images[stem]))
        h, w = im.shape[:2]
        side = e["video_side"]
        if max(h, w) > side:
            r = side / max(h, w)
            im = cv2.resize(im, (round(w * r), round(h * r)), interpolation=cv2.INTER_AREA)
            h, w = im.shape[:2]
        boxes = [to_px(r, w, h) for r in read_labels(DATASET / "labels" / "train" / f"{stem}.txt")]
        for k in ks:
            box = crop_box(boxes[k], w, h, e["margin"])
            a, b, c2, d = [int(round(v)) for v in box]
            if c2 - a < 8 or d - b < 8:
                continue
            labs = crop_labels(boxes, (a, b, c2, d), e["min_visible"])
            name = f"{'shrink' if (stem, k) in shrink else 'crop'}__{stem}__{k}"
            piece = im[b:d, a:c2]
            target = shrink.get((stem, k))
            if target and target < piece.shape[0]:
                f = target / piece.shape[0]
                piece = cv2.resize(piece, (max(round(piece.shape[1] * f), 8), round(target)), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(OUT / "images" / "train" / f"{name}.jpg"), piece, [cv2.IMWRITE_JPEG_QUALITY, 95])
            (OUT / "labels" / "train" / f"{name}.txt").write_text(
                "".join(f"{c} {x:.6f} {y:.6f} {bw:.6f} {bh:.6f}\n" for c, x, y, bw, bh in labs), encoding="utf-8")
            boxes_out.update(x[0] for x in labs)
        if i % 500 == 0:
            print(f"  đã cắt {i}/{len(by_image)} ảnh", flush=True)
    (OUT / "oversample.txt").write_text("".join(n + "\n" for n in rep), encoding="utf-8")
    n = len(list((OUT / "images" / "train").iterdir()))
    summary = dict(crops=n, shrunk=len(shrink), boxes={str(k): v for k, v in sorted(boxes_out.items())}, source_images=len(by_image),
                   oversample=len(rep), params=e)
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
