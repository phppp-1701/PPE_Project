"""Tạo task video trên CVAT cục bộ và tải nhãn nháp lên (CVAT for video 1.1), mỗi video một task.

Cách chạy (PowerShell của người dùng, từ thư mục gốc project, đã kích hoạt .venv):
    $s = Read-Host "Token CVAT" -AsSecureString
    $env:CVAT_LOCAL_TOKEN = [Net.NetworkCredential]::new('', $s).Password
    python scripts/05g_cvat_local_tasks.py video9 video10 ...            # tải annotations_claude.xml (nhãn nháp)
    python scripts/05g_cvat_local_tasks.py video9 --ann annotations.xml # chỉ track người, chưa có thuộc tính

Địa chỉ CVAT và tên biến token ở configs/ppe6.yaml mục fast_review (cvat_url, token_env). Token chỉ đọc từ biến
môi trường, không in, không ghi. Bộ nhãn: khối JSON trong docs/video_labeling.md. Video: data/videos/<video>.mp4.
Nhãn: outputs/results/video/<video>/prefill/<--ann> (05f tạo track người; nhãn nháp do Claude gán là machine_labeled).
Task cùng tên đã có thì bỏ qua video đó, không tạo trùng, không ghi đè phần đã gán.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import cv2
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--ann", default="annotations_claude.xml", help="tên file nhãn trong thư mục prefill")
    ap.add_argument("--org", default="", help="short name Organization; \"\" = không gian cá nhân")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["fast_review"]
    token = os.environ.get(cfg["token_env"])
    if not token:
        sys.exit(f"Chưa đặt biến môi trường {cfg['token_env']} trong phiên này (xem cách chạy ở đầu file).")
    block = re.search(r"```json\n(.*?)```", (ROOT / "docs" / "video_labeling.md").read_text(encoding="utf-8"), re.S)
    labels = json.loads(block.group(1))

    from cvat_sdk import make_client, models

    spec_labels = [models.PatchedLabelRequest(
        name=lb["name"], type=lb["type"],
        attributes=[models.AttributeRequest(name=a["name"], mutable=a["mutable"], input_type=models.InputTypeEnum(a["input_type"]),
                                            default_value=a["default_value"], values=a["values"]) for a in lb["attributes"]])
        for lb in labels]
    with make_client(cfg["cvat_url"], access_token=token) as client:
        client.organization_slug = args.org
        have = {t.name for t in client.tasks.list()}
        for v in args.videos:
            path = ROOT / "data" / "videos" / f"{v}.mp4"
            ann = ROOT / "outputs" / "results" / "video" / v / "prefill" / args.ann
            if v in have:
                print(f"[bỏ qua] task '{v}' đã có", flush=True)
                continue
            if not path.exists() or not ann.exists():
                print(f"[thiếu file] {path.name if not path.exists() else ann}", flush=True)
                continue
            cap = cv2.VideoCapture(str(path))
            n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            task = client.tasks.create_from_data(spec=models.TaskWriteRequest(name=v, labels=spec_labels),
                                                 resources=[str(path)], data_params={"image_quality": 100})
            if task.size != n:
                print(f"[LỆCH] {v}: task {task.id} có {task.size} khung, video {n} khung; chưa tải nhãn", flush=True)
                continue
            task.import_annotations("CVAT 1.1", str(ann))
            got = task.get_annotations().to_dict()
            print(f"[ok] {v}: task {task.id}, {task.size} khung, {len(got['tracks'])} track -> {cfg['cvat_url']}/tasks/{task.id}",
                  flush=True)


if __name__ == "__main__":
    main()
