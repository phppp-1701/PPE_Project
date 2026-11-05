"""Bước 3: tạo task CVAT để gán nhãn một video (quy tắc: docs/video_labeling.md).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/05b_cvat_video_task.py video2 --dry-run   # chỉ in kế hoạch, không gọi CVAT
    python scripts/05b_cvat_video_task.py video2
    python scripts/05b_cvat_video_task.py video2 --org ""     # không gian cá nhân (Organization hết hạn mức task)

Tạo task tên <video> trong Organization, không thuộc project nào, bộ nhãn lấy từ khối JSON trong
docs/video_labeling.md, chất lượng ảnh 100. Task cùng tên đã có thì dừng, không tạo lại.
Chỉ tải video lên, không tải kèm dự đoán của hệ thống (nhãn phải độc lập với dự đoán, spec 2.5).
Token đọc từ CVAT_ACCESS_TOKEN hoặc ~/.cvat_token; không in ra, không ghi vào project.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
HOST = "https://app.cvat.ai"
RULES = ROOT / "docs" / "video_labeling.md"


def read_token():
    token = os.environ.get("CVAT_ACCESS_TOKEN")
    token_file = Path.home() / ".cvat_token"
    if not token and token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        sys.exit("Chưa có token: đặt biến môi trường CVAT_ACCESS_TOKEN hoặc tạo file ~/.cvat_token.")
    return token


def read_labels():
    """Bộ nhãn là khối ```json đầu tiên trong quy tắc gán nhãn."""
    block = re.search(r"```json\n(.*?)```", RULES.read_text(encoding="utf-8"), re.S)
    if not block:
        sys.exit(f"Không thấy khối JSON nhãn trong {RULES}")
    return json.loads(block.group(1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video", help="video_id, vd. video2 (file data/videos/<video_id>.mp4)")
    p.add_argument("--org", default="ppeKhoaLuan", help="short name của Organization trên CVAT; \"\" = không gian cá nhân")
    p.add_argument("--dry-run", action="store_true", help="chỉ kiểm tra file và in kế hoạch, không gọi CVAT")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    path = ROOT / "data" / "videos" / f"{args.video}.mp4"
    if not path.exists():
        sys.exit(f"Không thấy {path}")
    cap = cv2.VideoCapture(str(path))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    labels = read_labels()
    names = [a["name"] for a in labels[0]["attributes"]]
    print(f"[kế hoạch] task {args.video}: {path.name}, {n_frames} khung, nhãn {labels[0]['name']} {names}")
    if args.dry_run:
        print("--dry-run: không gọi CVAT.")
        return

    from cvat_sdk import make_client, models  # import muộn để --dry-run chạy được khi chưa cài

    spec_labels = [
        models.PatchedLabelRequest(
            name=lb["name"],
            type=lb["type"],
            attributes=[
                models.AttributeRequest(
                    name=a["name"],
                    mutable=a["mutable"],
                    input_type=models.InputTypeEnum(a["input_type"]),
                    default_value=a["default_value"],
                    values=a["values"],
                )
                for a in lb["attributes"]
            ],
        )
        for lb in labels
    ]
    with make_client(HOST, access_token=read_token()) as client:
        client.organization_slug = args.org
        if any(t.name == args.video for t in client.tasks.list()):
            sys.exit(f"Task '{args.video}' đã có trong '{args.org}', không tạo lại để tránh trùng với phần đã gán.")
        print(f"[tạo] {args.video} ...", flush=True)
        task = client.tasks.create_from_data(
            spec=models.TaskWriteRequest(name=args.video, labels=spec_labels),
            resources=[str(path)],
            data_params={"image_quality": 100},
        )
        jobs = [j.id for j in task.get_jobs()]
        ok = task.size == n_frames
        print(f"[{'ok' if ok else 'LỆCH'}] task id {task.id}, khung {task.size}/{n_frames}, job {jobs}")
        print(f"Mở task: {HOST}/tasks/{task.id}")
        if not ok:
            sys.exit("Số khung trên CVAT khác file video, kiểm tra trước khi gán nhãn.")


if __name__ == "__main__":
    main()
