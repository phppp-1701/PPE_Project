"""Thử nghiệm 6 lớp: bộ phụ C4 = bộ phụ C3 + ảnh Construction-PPE bản mới (data/raw/construction_ppe_v2). Chỉ dùng cho train.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv, sau 03b cho C3 và 03e có ảnh cppe2):
    python scripts/03x_ppe6_c4_extra.py

Ghi data/ppe6/c4_extra/ (cùng cấu trúc bộ phụ của 03b để 04_train.py --extra dùng được) và gói
data/ppe6/variants/kaggle/c4_extra_pack.zip. Không sửa data/raw.
- Bỏ ảnh trùng cảnh với tập đánh giá (data/ppe6/external/cppe2/eval_overlap.txt).
- Đổi lớp về 6 lớp; bỏ forklift và các lớp no_*.
- Hộp ủng cạnh dài dưới `cppe2.min_boot_px` (ở cạnh dài ảnh `cppe2.side`) bị che xám, không thành nhãn: mẫu kiểm tra
  của agent thấy nhãn ủng sai tập trung ở hộp nhỏ. Tham số ở configs/ppe6.yaml mục `cppe2`.
Nhãn là nhãn của bộ gốc (người và máy của Ultralytics), agent chỉ kiểm tra mẫu; ghi đúng như vậy trong báo cáo.
"""

import json
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "construction_ppe_v2"
C3 = ROOT / "data" / "ppe6" / "c3_extra"
OUT = ROOT / "data" / "ppe6" / "c4_extra"
PACK = ROOT / "data" / "ppe6" / "variants" / "kaggle" / "c4_extra_pack.zip"


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["cppe2"]
    names = yaml.safe_load((RAW / "data.yaml").read_text(encoding="utf-8"))["names"]
    to6 = {i: cfg["class_map"][n] for i, n in names.items() if n in cfg["class_map"]}
    bad = set((ROOT / "data" / "ppe6" / "external" / "cppe2" / "eval_overlap.txt").read_text(encoding="utf-8").split())
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(C3, OUT)
    stat = Counter()
    for lab in sorted((RAW / "labels").rglob("*.txt")):
        img = next((RAW / "images" / lab.parent.name).glob(lab.stem + ".*"))
        key = "cppe2__" + img.name
        if key in bad:
            stat["eval_overlap"] += 1
            continue
        im = cv2.imdecode(np.fromfile(str(img), dtype=np.uint8), cv2.IMREAD_COLOR)
        h, w = im.shape[:2]
        s = min(1.0, cfg["side"] / max(h, w))
        if s < 1:
            im = cv2.resize(im, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
            h, w = im.shape[:2]
        rows = []
        for line in lab.read_text(encoding="utf-8").splitlines():
            t = line.split()
            if not t or int(t[0]) not in to6:
                continue
            c, (cx, cy, bw, bh) = to6[int(t[0])], map(float, t[1:5])
            if c == 5 and max(bw * w, bh * h) < cfg["min_boot_px"]:
                x1, y1, x2, y2 = int((cx - bw / 2) * w), int((cy - bh / 2) * h), int(np.ceil((cx + bw / 2) * w)), int(np.ceil((cy + bh / 2) * h))
                im[max(y1, 0):y2, max(x1, 0):x2] = cfg["fill"]
                stat["boots_small_masked"] += 1
                continue
            rows.append(f"{c} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            stat[f"cls{c}"] += 1
        name = f"cppe2__{lab.stem}"
        cv2.imwrite(str(OUT / "images" / "train" / f"{name}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        (OUT / "labels" / "train" / f"{name}.txt").write_text("".join(x + "\n" for x in rows), encoding="utf-8")
        stat["images"] += 1
    summ = json.loads((C3 / "summary.json").read_text(encoding="utf-8"))
    summ["cppe2"] = dict(stat, params=cfg)
    (OUT / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    PACK.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PACK, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                z.write(p, "c4_extra/" + p.relative_to(OUT).as_posix())
    print(json.dumps(dict(stat), ensure_ascii=False), f"| gói {PACK.name} {PACK.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
