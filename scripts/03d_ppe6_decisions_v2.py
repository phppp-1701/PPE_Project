"""Thử nghiệm 6 lớp: áp định nghĩa kính phiên bản 2 lên quyết định duyệt, không sửa decisions.csv.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03d_ppe6_decisions_v2.py

Định nghĩa 2 (docs/annotation_rules.md): chỉ xét đặc điểm nhìn thấy của chính chiếc kính, bỏ tiêu chí "đeo cùng mũ".
Đọc data/ppe6/review/{boxes,decisions}.csv và danh sách hộp ở configs/ppe6.yaml mục `goggles_v2`.
Ghi data/ppe6/review/decisions_v2.csv: mỗi hộp một dòng, cột:
    box_id, target, def_version, label, prev_label, note, prev_note, reason, decided_by
`decided_by`: agent (Claude xem ảnh), auto (theo luật), human (chỉ do 06_import, script này không bao giờ ghi human).
Chạy lại cho cùng kết quả. Không có hộp nào được đánh dấu là người đã duyệt.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "data" / "ppe6" / "review"
FIELDS = ["box_id", "target", "def_version", "label", "prev_label", "note", "prev_note", "reason", "decided_by"]


def apply_v2(box, old, rules):
    """Trả về (label, reason, decided_by) theo định nghĩa 2 cho một hộp."""
    actor = "auto" if old["reviewer"] == "auto" else "agent"
    if box["target"] != "goggles":
        return old["label"], "", actor
    bid = box["box_id"]
    if bid in rules["dark_lens"] or "scene_orange" in old["note"] or "dark_wrap_with_helmet" in old["note"]:
        return "unclear", "dark_lens", "agent"
    if bid in rules["plain_frame"]:
        return "unclear", "plain_frame", "agent"
    if bid in rules["not_worn"]:
        return "ordinary", "not_worn", "agent"
    return old["label"], "", actor


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    rules = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["goggles_v2"]
    rules = {k: set(v.split()) for k, v in rules.items()}
    boxes = list(csv.DictReader((REVIEW / "boxes.csv").open(encoding="utf-8")))
    old = {r["box_id"]: r for r in csv.DictReader((REVIEW / "decisions.csv").open(encoding="utf-8"))}
    missing = [b["box_id"] for b in boxes if b["box_id"] not in old]
    if missing:
        sys.exit(f"Thiếu quyết định cho {len(missing)} hộp.")
    rows = []
    for b in boxes:
        o = old[b["box_id"]]
        label, reason, actor = apply_v2(b, o, rules)
        rows.append(dict(box_id=b["box_id"], target=b["target"], def_version=2, label=label, prev_label=o["label"], note=o["note"],
                         prev_note=o["note"], reason=reason, decided_by=actor))
    with (REVIEW / "decisions_v2.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(dict(sorted(Counter((r["target"], r["prev_label"], r["label"], r["reason"]) for r in rows).items())))


if __name__ == "__main__":
    main()
