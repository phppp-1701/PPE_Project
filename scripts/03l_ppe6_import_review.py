"""Thử nghiệm 6 lớp: nhập kết quả người duyệt từ CVAT. Quyết định của người luôn thắng quyết định của agent.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03l_ppe6_import_review.py --task task_a --file <export.zip> --reviewer "Tên"
    python scripts/03l_ppe6_import_review.py --task task_a --file <export.zip> --reviewer "Tên" --partial   # nhập phần đã chọn, liệt kê phần còn thiếu
    python scripts/03l_ppe6_import_review.py --task second --file <export.zip> --second-reviewer "Tên"
    python scripts/03l_ppe6_import_review.py --scenes <scene_review.csv> --reviewer "Tên"
    python scripts/03l_ppe6_import_review.py --report       # bất đồng agent, người theo nhóm gốc, lớp, nguồn
    python scripts/03l_ppe6_import_review.py --agreement    # đồng thuận người chính, người thứ hai

Xuất từ CVAT theo định dạng "CVAT for images 1.1". Sau khi nhập, chạy lại 03i.
Gói mù ở data/ppe6/review/cvat_pack_blind/ (03p). Ô còn `chua_chon` hoặc hộp bị xóa làm lệnh dừng, không ghi gì và liệt kê mã hộp; `--partial` nhập phần
đã chọn. Không bao giờ coi ô chưa chọn là đồng ý với agent. Nhập lại một hộp thì dòng sau cùng có hiệu lực, dòng cũ giữ làm dấu vết.

Nơi ghi trong data/ppe6/review/:
    task_a, task_b, task_c  human_review.csv, human_added.csv
    task_d                  chv_boots_seen.csv, chv_boots_added.csv (chỉ để đo ủng thiếu nhãn)
    trial                   trial_review.csv (không tính là đã duyệt)
    second                  second_review.csv (kiểm tra chất lượng, không ảnh hưởng dataset, gates, checklist, không ghi đè người chính)
`--group`: gói cũ có hiện nhãn agent, chỉ dùng khi thêm `--old-pack`.
"""

import argparse
import csv
import json
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import NOT_A_PERSON, UnsetError, agreement, disagreement, merge_blind, merge_review, parse_cvat, scope_threshold  # noqa: E402

REVIEW = ROOT / "data" / "ppe6" / "review"
PACK = REVIEW / "cvat_pack"
BLIND = REVIEW / "cvat_pack_blind"
FIELDS = ["box_id", "target", "source", "before", "after", "person_ok", "reviewer", "reviewed_at", "pack", "new_cx", "new_cy", "new_w", "new_h"]
ADDED = ["file", "target", "cx", "cy", "w", "h", "reviewer", "pack"]
PERSON_TASKS = ("task_a", "task_b", "trial")
TARGET = dict(task_a=("human_review.csv", "human_added.csv"), task_b=("human_review.csv", "human_added.csv"), task_c=("human_review.csv", "human_added.csv"),
              task_d=("chv_boots_seen.csv", "chv_boots_added.csv"), trial=("trial_review.csv", "trial_added.csv"), second=("second_review.csv", "second_added.csv"))


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def append(path, fields, rows):
    if not rows:
        return
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


def import_blind(task, xml_text, reviewer, now, partial=False, blind=BLIND, review=REVIEW):
    """Nhập một task gói mù. Người thứ hai chỉ ghi second_review.csv, không đụng kết quả người chính."""
    primary = {r["reviewer"].strip().lower() for r in rd(review / "human_review.csv")}
    if task == "second" and reviewer.strip().lower() in primary:
        raise ValueError("Người thứ hai phải khác người duyệt chính.")
    items = {r["item_id"]: r for r in rd(blind / "_private" / f"{task}_items.csv")}
    images = {r["image_name"]: r["file"] for r in rd(blind / "_private" / f"{task}_images.csv")}
    boxes, tags = parse_cvat(xml_text)
    rows, added, unset = merge_blind(boxes, tags, items, images, reviewer, task, now, task in PERSON_TASKS, partial)
    main_file, add_file = TARGET[task]
    append(review / main_file, FIELDS, rows)
    append(review / add_file, ADDED, added)
    return rows, added, unset


def report():
    rows = rd(REVIEW / "human_review.csv")
    if not rows:
        print("Chưa có kết quả người duyệt.")
        return
    last = {r["box_id"]: r for r in rows}
    d = disagreement(last.values())
    groups = sorted({r["pack"] for r in last.values() if not r["box_id"].startswith("image:")})
    with (REVIEW / "disagreement.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["group", "target", "source", "different", "total", "rate"])
        for g in ["tat_ca", *groups]:
            part = d if g == "tat_ca" else disagreement([r for r in last.values() if r["pack"] == g])
            for (t, s), (a, b) in part.items():
                w.writerow([g, t, s, a, b, round(a / b, 4)])
                print(f"{g} {t} {s}: khác {a}/{b} ({a / b:.1%})")
    heights = {}
    for p in BLIND.glob("_private/*_items.csv"):
        heights.update({r["box_id"]: r["person_h_px"] for r in rd(p)})
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["scope"]
    for target in ("boots", "goggles"):
        pts = [(float(heights[k]), r["person_ok"] == "du_lon") for k, r in last.items() if r["target"] == target and r["person_ok"] in ("du_lon", "qua_nho") and heights.get(k)]
        print(f"{target}: {len(pts)} hộp có ý kiến về cỡ người; đề xuất chiều cao người tối thiểu (px, ảnh cạnh dài {cfg['side']}):", scope_threshold(pts, cfg["min_ok_rate"]))


def agreement_report(review=REVIEW):
    first = {r["box_id"]: r for r in rd(review / "human_review.csv") if not r["box_id"].startswith("image:")}
    second = {r["box_id"]: r for r in rd(review / "second_review.csv") if not r["box_id"].startswith("image:")}
    both = sorted(set(first) & set(second))
    print(f"Người thứ hai {len(second)} hộp, trùng người chính {len(both)} hộp. Đây là kiểm tra chất lượng, không phải quyết định nhãn cuối.")
    if not both:
        return None
    res = agreement([first[k]["after"] for k in both], [second[k]["after"] for k in both], np.random.default_rng(0))
    res["by_target"] = {}
    for t in sorted({first[k]["target"] for k in both}):
        ks = [k for k in both if first[k]["target"] == t]
        res["by_target"][t] = agreement([first[k]["after"] for k in ks], [second[k]["after"] for k in ks], np.random.default_rng(0))
    (review / "agreement.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", choices=sorted(TARGET))
    ap.add_argument("--group", choices=["P0a", "P0b", "P1", "P2"])
    ap.add_argument("--old-pack", action="store_true")
    ap.add_argument("--file")
    ap.add_argument("--scenes")
    ap.add_argument("--reviewer", default="")
    ap.add_argument("--second-reviewer", default="")
    ap.add_argument("--partial", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--agreement", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if args.report:
        report()
        return
    if args.agreement:
        agreement_report()
        return
    name = args.second_reviewer if args.task == "second" else args.reviewer
    if args.task == "second" and args.reviewer:
        sys.exit("Task second chỉ dùng --second-reviewer.")
    if args.second_reviewer and args.task != "second":
        sys.exit("--second-reviewer chỉ dùng với --task second.")
    if name.strip().lower() in NOT_A_PERSON:
        sys.exit("Cần tên người duyệt thật.")
    if args.scenes:
        shutil.copy2(args.scenes, REVIEW / "scene_review_done.csv")
        print("Đã nhập", len(rd(REVIEW / "scene_review_done.csv")), "cảnh")
        return
    if args.group:
        if not args.old_pack:
            sys.exit("Gói cũ hiện nhãn agent. Dùng --task với gói mù, hoặc thêm --old-pack nếu thật sự cần.")
        index = {r["box_id"]: r for r in rd(PACK / args.group / "index.csv")}
        index["__images__"] = {r["image_name"]: r["file"] for r in rd(PACK / args.group / "images.csv")}
        boxes, tags = parse_cvat(read_export(args.file))
        rows, added, skipped = merge_review(boxes, tags, index, name, args.group, datetime.now().isoformat(timespec="seconds"))
        append(REVIEW / "human_review.csv", FIELDS, rows)
        append(REVIEW / "human_added.csv", ADDED, added)
        print(f"Đã nhập {len(rows)} dòng, {len(added)} hộp vẽ thêm, bỏ qua {skipped} hộp chưa duyệt.")
        return
    if not (args.task and args.file):
        sys.exit("Cần --task và --file.")
    try:
        rows, added, unset = import_blind(args.task, read_export(args.file), name, datetime.now().isoformat(timespec="seconds"), args.partial)
    except UnsetError as e:
        print(f"Không nhập gì: còn {len(e.items)} ô chưa chọn hoặc hộp bị xóa.")
        for x in e.items[:40]:
            print(" ", x)
        sys.exit("Chọn đủ rồi xuất lại, hoặc thêm --partial để nhập phần đã chọn.")
    if args.task == "trial":
        for r in rows:
            print(" ", r["box_id"], r["before"], "->", r["after"], r["person_ok"], r["reviewer"])
    print(f"Đã nhập {len(rows)} dòng, {len(added)} hộp vẽ thêm vào {TARGET[args.task][0]}; còn {len(unset)} ô chưa chọn.")
    for x in unset[:40]:
        print(" ", x)
    if args.task in ("task_a", "task_b", "task_c"):
        print("Chạy lại 03i để cập nhật.")


if __name__ == "__main__":
    main()
