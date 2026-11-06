"""Thử nghiệm 6 lớp: nhập kết quả người duyệt từ CVAT. Quyết định của người luôn thắng quyết định của agent.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03l_ppe6_import_review.py --group P0a --file <task_export.zip hoặc annotations.xml> --reviewer "Tên"
    python scripts/03l_ppe6_import_review.py --scenes <scene_review.csv đã điền> --reviewer "Tên"
    python scripts/03l_ppe6_import_review.py --report      # tỉ lệ bất đồng, đề xuất ngưỡng người đủ lớn

Xuất từ CVAT theo định dạng "CVAT for images 1.1". Sau khi nhập, chạy lại 03i để cập nhật val_new, test_new.
Ghi nối thêm vào data/ppe6/review/human_review.csv (giá trị trước, sau, người duyệt, thời gian, gói), human_added.csv (hộp vẽ thêm),
scene_review_done.csv; `--report` ghi disagreement.csv. Nhập lại một hộp thì dòng sau cùng có hiệu lực, các dòng cũ giữ làm dấu vết.
Hộp còn `chua_duyet` bị bỏ qua, không tính là đã duyệt. Script từ chối chạy nếu thiếu tên người duyệt.
"""

import argparse
import csv
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import NOT_A_PERSON, disagreement, merge_review, parse_cvat, scope_threshold  # noqa: E402

REVIEW = ROOT / "data" / "ppe6" / "review"
PACK = REVIEW / "cvat_pack"
FIELDS = ["box_id", "target", "source", "before", "after", "person_ok", "reviewer", "reviewed_at", "pack", "new_cx", "new_cy", "new_w", "new_h"]
ADDED = ["file", "target", "cx", "cy", "w", "h", "reviewer", "pack"]


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8")))


def append(path, fields, rows):
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fields, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(rows)


def read_export(path):
    p = Path(path)
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            name = next(n for n in z.namelist() if n.endswith(".xml"))
            return z.read(name).decode("utf-8")
    return p.read_text(encoding="utf-8")


def report():
    path = REVIEW / "human_review.csv"
    if not path.exists():
        print("Chưa có kết quả người duyệt.")
        return
    rows = rd(path)
    last = {r["box_id"]: r for r in rows}
    d = disagreement(last.values())
    with (REVIEW / "disagreement.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["target", "source", "different", "total", "rate"])
        for (t, s), (a, b) in d.items():
            w.writerow([t, s, a, b, round(a / b, 4)])
            print(f"{t} {s}: khác {a}/{b} ({a / b:.1%})")
    heights = {}
    for g in PACK.iterdir():
        if (g / "index.csv").exists():
            heights.update({r["box_id"]: r["person_h_px"] for r in rd(g / "index.csv")})
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["scope"]
    for target in ("boots", "goggles"):
        pts = [(float(heights[k]), r["person_ok"] == "du_lon") for k, r in last.items()
               if r["target"] == target and r["person_ok"] in ("du_lon", "qua_nho") and heights.get(k)]
        print(f"{target}: {len(pts)} hộp có ý kiến về cỡ người; đề xuất chiều cao người tối thiểu (px, ảnh cạnh dài {cfg['side']}):", scope_threshold(pts, cfg["min_ok_rate"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", choices=["P0a", "P0b", "P1", "P2"])
    ap.add_argument("--file")
    ap.add_argument("--scenes")
    ap.add_argument("--reviewer", default="")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if args.report:
        report()
        return
    if args.reviewer.strip().lower() in NOT_A_PERSON:
        sys.exit("Cần --reviewer là tên người duyệt thật.")
    if args.scenes:
        shutil.copy2(args.scenes, REVIEW / "scene_review_done.csv")
        print("Đã nhập", len(rd(REVIEW / "scene_review_done.csv")), "cảnh")
        return
    if not (args.group and args.file):
        sys.exit("Cần --group và --file.")
    index = {r["box_id"]: r for r in rd(PACK / args.group / "index.csv")}
    index["__images__"] = {r["image_name"]: r["file"] for r in rd(PACK / args.group / "images.csv")}
    images = index.pop("__images__")
    boxes, tags = parse_cvat(read_export(args.file))
    index["__images__"] = images
    index_rows = {k: v for k, v in index.items()}
    rows, added, skipped = merge_review(boxes, tags, IndexView(index_rows), args.reviewer, args.group, datetime.now().isoformat(timespec="seconds"))
    append(REVIEW / "human_review.csv", FIELDS, rows)
    if added:
        append(REVIEW / "human_added.csv", ADDED, added)
    print(f"Đã nhập {len(rows)} dòng, {len(added)} hộp vẽ thêm, bỏ qua {skipped} hộp chưa duyệt. Chạy lại 03i để cập nhật.")


class IndexView(dict):
    """Chỉ để `values()` bỏ qua khóa __images__ khi tạo bảng tên ảnh."""

    def values(self):
        return [v for k, v in self.items() if k != "__images__"]


if __name__ == "__main__":
    main()
