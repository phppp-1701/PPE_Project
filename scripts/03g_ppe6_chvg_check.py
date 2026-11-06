"""Thử nghiệm 6 lớp: giải nén và thống kê CHVG từ bản tải về. Chỉ ghi vào data/ppe6/external/chvg/.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03g_ppe6_chvg_check.py

Đọc download/CHVG-Dataset.zip (figshare, DOI 10.6084/m9.figshare.19625166.v1, CC BY 4.0).
Ghi: extracted/ (ảnh và XML), images.csv (file, image), boxes.csv (file, cls, x1, y1, x2, y2, w, h), summary.json.
Nhãn CHVG chưa được tin dùng: `glass` chỉ là ứng viên, phải duyệt theo định nghĩa trong docs/annotation_rules.md.
"""

import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "ppe6" / "external" / "chvg"
ZIP = BASE / "download" / "CHVG-Dataset.zip"
MD5 = "0239c0b26cf7f25dff4237e7a535a9a2"


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if hashlib.md5(ZIP.read_bytes()).hexdigest() != MD5:
        sys.exit("MD5 của CHVG không khớp với figshare.")
    out = BASE / "extracted"
    with zipfile.ZipFile(ZIP) as z:
        for name in z.namelist():
            p = PurePosixPath(name)
            if name.endswith("/") or p.suffix.lower() not in (".jpg", ".xml") or ".." in p.parts or p.is_absolute():
                continue
            target = out / p.name
            if not target.exists():
                out.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
    images, boxes = [], []
    for x in sorted(out.glob("*.xml")):
        img = x.with_suffix(".jpg")
        if not img.exists():
            continue
        key = f"chvg__{img.name}"
        images.append(dict(file=key, image=str(img.relative_to(ROOT)).replace("\\", "/")))
        root = ET.parse(x).getroot()
        w, h = int(root.findtext("size/width")), int(root.findtext("size/height"))
        for o in root.iter("object"):
            b = o.find("bndbox")
            boxes.append(dict(file=key, cls=o.findtext("name"), x1=b.findtext("xmin"), y1=b.findtext("ymin"), x2=b.findtext("xmax"),
                              y2=b.findtext("ymax"), w=w, h=h))
    for name, rows in (("images.csv", images), ("boxes.csv", boxes)):
        with (BASE / name).open("w", encoding="utf-8", newline="") as f:
            wr = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
            wr.writeheader()
            wr.writerows(rows)
    per_img = {}
    for b in boxes:
        per_img.setdefault(b["cls"], set()).add(b["file"])
    summary = dict(images=len(images), boxes=len(boxes), boxes_by_class=dict(Counter(b["cls"] for b in boxes).most_common()),
                   images_by_class={k: len(v) for k, v in sorted(per_img.items())})
    summary["sizes"] = [str(k) for k, _ in Counter((b["w"], b["h"]) for b in boxes).most_common(3)]
    (BASE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
