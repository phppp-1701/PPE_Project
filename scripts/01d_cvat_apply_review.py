"""Bước 1 (phụ): áp kết quả duyệt tự động lên task CVAT của CHV.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/01d_cvat_apply_review.py --parts 2,3 --dry-run   # chỉ in sẽ làm gì
    python scripts/01d_cvat_apply_review.py --parts 2,3

Đọc trong data/ppe4/converted/<bộ>/cvat/:
    <bộ>_review_boxes.csv    mỗi hộp găng máy vẽ: part, image, shape_id, verdict (glove / not_glove / uncertain)
    <bộ>_review_images.csv   mỗi ảnh: part, image, status (check / machine_reviewed), reason
    <bộ>_partXX_prelabel_uploaded.csv  tọa độ hộp lúc tải lên (để biết hộp đã bị người sửa chưa)
Việc làm trên CVAT:
    1. Thêm nhãn tag `check` vào project nếu chưa có.
    2. Xóa hộp verdict = not_glove, CHỈ khi hộp còn nguyên (cùng id, cùng tọa độ lúc tải lên).
    3. Gắn tag `check` cho ảnh status = check (ảnh đã có tag `check` thì bỏ qua).
Không sửa hộp nào khác. Token đọc từ CVAT_ACCESS_TOKEN hoặc ~/.cvat_token.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "prelabel.yaml"
CONVERTED = ROOT / "data" / "ppe4" / "converted"
CHECK_TAG = "check"


def parse_parts(text):
    parts = []
    for chunk in text.split(","):
        a, _, b = chunk.partition("-")
        parts += range(int(a), int(b or a) + 1)
    return sorted(set(parts))


def read_token():
    token = os.environ.get("CVAT_ACCESS_TOKEN")
    token_file = Path.home() / ".cvat_token"
    if not token and token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        sys.exit("Chưa có token: đặt biến môi trường CVAT_ACCESS_TOKEN hoặc tạo file ~/.cvat_token.")
    return token


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parts", required=True, help="vd. 2,3")
    p.add_argument("--source", default="chv")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    cvat_dir = CONVERTED / args.source / "cvat"
    parts = [f"{args.source}_part{k:02d}" for k in parse_parts(args.parts)]
    with open(cvat_dir / f"{args.source}_review_boxes.csv", encoding="utf-8") as f:
        boxes = [r for r in csv.DictReader(f) if r["part"] in parts]
    with open(cvat_dir / f"{args.source}_review_images.csv", encoding="utf-8") as f:
        images = [r for r in csv.DictReader(f) if r["part"] in parts]
    uploaded = {}
    for part in parts:
        with open(cvat_dir / f"{part}_prelabel_uploaded.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["shape_id"]:  # rỗng: hộp đã bị người xóa (sau 01e_cvat_reorder_task.py)
                    uploaded[int(r["shape_id"])] = [float(r[k]) for k in ("x1", "y1", "x2", "y2")]

    for part in parts:
        n_del = sum(1 for b in boxes if b["part"] == part and b["verdict"] == "not_glove")
        n_chk = sum(1 for i in images if i["part"] == part and i["status"] == CHECK_TAG)
        print(f"[kế hoạch] {part}: xóa {n_del} hộp not_glove, gắn tag '{CHECK_TAG}' cho {n_chk} ảnh")
    if args.dry_run:
        print("--dry-run: không gọi CVAT.")
        return

    from cvat_sdk import make_client, models
    from cvat_sdk.core.proxies.annotations import AnnotationUpdateAction

    with make_client(cfg["cvat"]["host"], access_token=read_token()) as client:
        client.organization_slug = cfg["cvat"]["org"]
        projects = [pr for pr in client.projects.list() if pr.name == cfg["cvat"]["project"]]
        if len(projects) != 1:
            sys.exit(f"Tìm thấy {len(projects)} project tên '{cfg['cvat']['project']}', cần đúng 1.")
        project = projects[0]
        if CHECK_TAG not in {l.name for l in project.get_labels()}:
            client.api_client.projects_api.partial_update(
                project.id, patched_project_write_request=models.PatchedProjectWriteRequest(
                    labels=[models.PatchedLabelRequest(name=CHECK_TAG, type="tag", color="#ff8800")]))
            print(f"Đã thêm nhãn tag '{CHECK_TAG}' vào project.")

        for part in parts:
            task = next(t for t in client.tasks.list() if t.project_id == project.id and t.name == part)
            labels = {l.name: l.id for l in task.get_labels()}
            check_id = labels[CHECK_TAG]
            frame_of = {Path(fr.name).name: i for i, fr in enumerate(task.get_frames_info())}
            ann = task.get_annotations()
            if any(s.source in ("manual", "semi-auto") for s in ann.shapes):
                # người đã duyệt (có thể đã gỡ tag check): áp lại sẽ gắn tag lại vào ảnh đã xem xong
                print(f"[bỏ qua] {part}: task đã có người sửa, không áp lại kết quả duyệt.")
                continue
            current = {s.id: s for s in ann.shapes}

            to_delete, changed = [], 0
            for b in boxes:
                if b["part"] != part or b["verdict"] != "not_glove" or not b["shape_id"]:
                    continue
                s = current.get(int(b["shape_id"]))
                if s is None:
                    continue  # người đã xóa rồi
                if any(abs(a - c) > 0.5 for a, c in zip(s.points, uploaded[s.id])):
                    changed += 1  # người đã sửa hộp này: giữ nguyên
                    continue
                to_delete.append(models.LabeledShapeRequest(**{k: v for k, v in s.to_dict().items()
                                                               if k in ("id", "type", "frame", "label_id", "points")}))
            if to_delete:
                task.update_annotations(models.PatchedLabeledDataRequest(shapes=to_delete),
                                        action=AnnotationUpdateAction.DELETE)

            tagged = {t.frame for t in ann.tags if t.label_id == check_id}
            tags = [models.LabeledImageRequest(frame=frame_of[i["image"]], label_id=check_id, source="auto")
                    for i in images if i["part"] == part and i["status"] == CHECK_TAG
                    and frame_of[i["image"]] not in tagged]
            if tags:
                task.update_annotations(models.PatchedLabeledDataRequest(tags=tags), action=AnnotationUpdateAction.CREATE)

            after = task.get_annotations()
            n_tag = sum(1 for t in after.tags if t.label_id == check_id)
            print(f"[ok] {part}: xóa {len(to_delete)} hộp (giữ {changed} hộp người đã sửa), "
                  f"thêm {len(tags)} tag; hiện có {len(after.shapes)} hộp, {n_tag} ảnh tag '{CHECK_TAG}'")


if __name__ == "__main__":
    main()
