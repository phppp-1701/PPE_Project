"""Thử nghiệm 6 lớp: lệnh cuối buổi của công cụ duyệt nhanh.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv; token do bạn đặt trong phiên PowerShell):
    python scripts/03r_ppe6_fast_finish.py --task task_a --reviewer "Tên bạn"
    python scripts/03r_ppe6_fast_finish.py --task task_a --reviewer "Tên bạn" --partial     # cố ý nhập dở

Thứ tự: kiểm ô thiếu, mục cần mở CVAT; đồng bộ lên CVAT; đối chiếu từng ô; xuất CVAT for images 1.1 và giữ file; đối chiếu XML; nhập bằng 03l;
chạy 03l --report; chạy 03i; in điều kiện dừng từ 03n gates. Thiếu ô hoặc còn mục cần mở CVAT thì dừng, trừ khi có --partial.
Token đọc từ biến môi trường CVAT_LOCAL_TOKEN, không in, không ghi. File xuất giữ ở data/ppe6/review/export_<task>_<thời gian>.zip.
Mã thoát: 0 xong, 2 dừng vì thiếu hoặc xung đột, 3 lỗi đối chiếu hoặc nhập.
"""

import argparse
import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.fast_review import Conflict, Cvat, Session, load_pack, sync, verify_cvat, verify_export  # noqa: E402

REAL_TASKS = ("task_a", "task_b", "task_c", "task_d")


def stop(code, title, items=()):
    print(title)
    for x in list(items)[:40]:
        print(" ", x)
    sys.exit(code)


def run(*a):
    r = subprocess.run([sys.executable, *a], cwd=ROOT)
    return r.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", required=True, choices=[*REAL_TASKS, "trial"])
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--partial", action="store_true")
    ap.add_argument("--state-dir", help="chỉ để kiểm thử")
    ap.add_argument("--review-dir", help="chỉ để kiểm thử")
    ap.add_argument("--blind-dir", help="chỉ để kiểm thử")
    ap.add_argument("--pack-dir", help="chỉ để kiểm thử")
    ap.add_argument("--cvat-task-id", type=int, help="chỉ để kiểm thử")
    ap.add_argument("--cvat-url", help="chỉ để kiểm thử")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["fast_review"]
    testing = args.task == "trial"
    if testing and not (args.state_dir and args.review_dir and args.cvat_task_id):
        sys.exit("Task trial chỉ để kiểm thử, cần --state-dir, --review-dir, --cvat-task-id.")
    review = Path(args.review_dir) if args.review_dir else ROOT / "data" / "ppe6" / "review"
    state_dir = Path(args.state_dir) if args.state_dir else review
    folder = Path(args.pack_dir) if args.pack_dir else ROOT / "data" / "ppe6" / "review" / "cvat_pack_blind" / args.task
    try:
        session = Session(load_pack(folder), args.task, args.reviewer, state_dir)
    except ValueError as e:
        sys.exit(str(e))
    if not session.state_path.exists():
        sys.exit("Chưa có phiên duyệt nào cho task này.")
    missing, flags = session.missing(), session.flag_links(cfg["cvat_url"], args.cvat_task_id or cfg["tasks"].get(args.task), args.cvat_task_id or cfg["tasks"].get(args.task))
    if (missing or flags) and not args.partial:
        print(f"Dừng: còn {len(missing)} ô thiếu, {len(flags)} mục cần mở CVAT. Không đồng bộ gì.")
        stop(2, "Xử lý xong rồi chạy lại, hoặc thêm --partial nếu cố ý nhập dở.", [*missing, *(f"{x['key']} {x['url']}" for x in flags)])
    token = os.environ.get(cfg["token_env"])
    if not token:
        sys.exit(f"Chưa đặt biến môi trường {cfg['token_env']} trong phiên này.")
    cvat = Cvat(args.cvat_url or cfg["cvat_url"], token, args.cvat_task_id or cfg["tasks"][args.task])
    try:
        cells, tags = sync(session, cvat)
    except Conflict as e:
        stop(2, "Dừng: CVAT có giá trị khác với công cụ, không ghi đè. Sửa lại cho khớp rồi chạy lại.", e.items)
    print(f"Đồng bộ xong: ghi {cells} ô, {tags} tag.")
    diff, left = verify_cvat(session, cvat)
    if diff:
        stop(3, "Lỗi: CVAT không khớp công cụ.", diff)
    if left and not args.partial:
        stop(2, f"Dừng: CVAT còn {left} ô chua_chon.")
    path = review / f"export_{args.task}_{datetime.now():%Y%m%d_%H%M%S}.zip"
    cvat.export(path)
    print(f"Đã xuất và giữ file: {path}")
    with zipfile.ZipFile(path) as z:
        xml = z.read(next(n for n in z.namelist() if n.endswith(".xml"))).decode("utf-8")
    diff = verify_export(session, xml)
    if diff:
        stop(3, "Lỗi: file xuất không khớp công cụ.", diff)
    print("Đối chiếu từng ô giữa công cụ, CVAT, file xuất: khớp.")
    tool = str(ROOT / "scripts" / "03l_ppe6_import_review.py")
    extra = [*(["--review-dir", args.review_dir] if args.review_dir else []), *(["--blind-dir", args.blind_dir] if args.blind_dir else [])]
    code = run(tool, "--task", args.task, "--file", str(path), "--reviewer", args.reviewer, *(["--partial"] if args.partial else []), *extra)
    if code:
        sys.exit(3)
    print("\n--- Báo cáo bất đồng ---")
    run(tool, "--report", *extra)
    if testing:
        print("Task kiểm thử: bỏ qua 03i và gates.")
        return
    print("\n--- Cập nhật tập đánh giá ---")
    if run(str(ROOT / "scripts" / "03i_ppe6_build_dataset.py")):
        sys.exit(3)
    print("\n--- Điều kiện dừng ---")
    run(str(ROOT / "scripts" / "03n_ppe6_readiness.py"), "gates")
    print("Mục [stop] hoặc [action]: dừng và gửi kết quả trước khi duyệt tiếp.")


if __name__ == "__main__":
    main()
