"""Bước 1 (phụ): tạo lại một task CVAT để các ảnh mang tag `check` nằm ở đầu, GIỮ NGUYÊN mọi nhãn đã gán.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv; không ai được mở task này trong lúc chạy):
    python scripts/01e_cvat_reorder_task.py --part 2 --dry-run
    python scripts/01e_cvat_reorder_task.py --part 2

CVAT không đổi được thứ tự ảnh của task đã tạo, nên script:
    1. Đọc toàn bộ hộp và tag của task (giữ nguồn file/auto/manual), sao lưu ra
       data/ppe4/converted/<bộ>/cvat/<task>_backup_before_reorder_<giờ>_cvat.zip.
    2. Đọc lại lần nữa; nếu khác lần đầu (có người đang sửa) thì dừng.
    3. Xóa task, tạo lại cùng tên với ảnh mang tag `check` ở đầu (thứ tự tên), rồi ghi lại từng hộp, tag.
    4. Đối chiếu số lượng và tọa độ; đổi id hộp cũ sang id mới trong <task>_prelabel_uploaded.csv
       và <bộ>_review_boxes.csv (bản cũ giữ lại với hậu tố _old_task<id>).
Token đọc từ CVAT_ACCESS_TOKEN hoặc ~/.cvat_token.
"""

import argparse
import collections
import csv
import datetime
import os
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "prelabel.yaml"
CONVERTED = ROOT / "data" / "ppe4" / "converted"
CHECK_TAG = "check"


def read_token():
    token = os.environ.get("CVAT_ACCESS_TOKEN")
    token_file = Path.home() / ".cvat_token"
    if not token and token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        sys.exit("Chưa có token: đặt biến môi trường CVAT_ACCESS_TOKEN hoặc tạo file ~/.cvat_token.")
    return token


def snapshot(task, names):
    """Toàn bộ nhãn của task dưới dạng không phụ thuộc id/frame: (ảnh, nhãn, kiểu, tọa độ, nguồn, ...)."""
    fr = {i: Path(f.name).name for i, f in enumerate(task.get_frames_info())}
    ann = task.get_annotations()
    if ann.tracks:
        sys.exit("Task có track (video), script không hỗ trợ.")
    shapes = [{"id": s.id, "image": fr[s.frame], "label": names[s.label_id], "type": s.type.value,
               "points": list(s.points), "source": s.source, "occluded": s.occluded, "z_order": s.z_order,
               "rotation": s.rotation, "attributes": [a.to_dict() for a in s.attributes]} for s in ann.shapes]
    tags = [{"image": fr[t.frame], "label": names[t.label_id], "source": t.source,
             "attributes": [a.to_dict() for a in t.attributes]} for t in ann.tags]
    return fr, shapes, tags


def key(s):
    return (s["image"], s["label"], s["type"], tuple(round(p, 2) for p in s["points"]), s["source"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--part", type=int, required=True)
    p.add_argument("--source", default="chv")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    from cvat_sdk import make_client, models
    from cvat_sdk.core.proxies.annotations import AnnotationUpdateAction

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    name = f"{args.source}_part{args.part:02d}"
    cvat_dir = CONVERTED / args.source / "cvat"

    with make_client(cfg["cvat"]["host"], access_token=read_token()) as client:
        client.organization_slug = cfg["cvat"]["org"]
        project = next(pr for pr in client.projects.list() if pr.name == cfg["cvat"]["project"])
        tasks = [t for t in client.tasks.list() if t.project_id == project.id and t.name == name]
        if len(tasks) != 1:
            sys.exit(f"Tìm thấy {len(tasks)} task tên {name}, cần đúng 1.")
        old = tasks[0]
        names = {l.id: l.name for l in old.get_labels()}
        fr, shapes, tags = snapshot(old, names)
        images = [fr[i] for i in sorted(fr)]
        check = sorted({t["image"] for t in tags if t["label"] == CHECK_TAG})
        ordered = check + [n for n in sorted(images) if n not in set(check)]
        print(f"{name} (task {old.id}): {len(images)} ảnh, {len(shapes)} hộp, {len(tags)} tag; "
              f"{len(check)} ảnh '{CHECK_TAG}' sẽ ở frame 0-{len(check) - 1}")
        print("  hộp theo (nhãn, nguồn):", dict(collections.Counter((s["label"], s["source"]) for s in shapes)))
        if args.dry_run:
            print("--dry-run: không đổi gì.")
            return

        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        backup = cvat_dir / f"{name}_backup_before_reorder_{stamp}_cvat.zip"
        old.export_dataset("CVAT for images 1.1", str(backup), include_images=False)
        _, shapes2, tags2 = snapshot(old, names)
        if sorted(map(key, shapes)) != sorted(map(key, shapes2)) or len(tags) != len(tags2):
            sys.exit("Task vừa thay đổi trong lúc đọc (có người đang sửa?), dừng, không xóa gì.")
        print(f"Đã sao lưu {backup.name}")

        old_id = old.id
        old.remove()
        print(f"Đã xóa task cũ {old_id}, tạo lại ...", flush=True)
        task = client.tasks.create_from_data(
            spec=models.TaskWriteRequest(name=name, project_id=project.id),
            resources=[str(ROOT / "data" / "raw" / args.source / "images" / n) for n in ordered],
            data_params={"sorting_method": "predefined", "image_quality": 70},
        )
        label_id = {l.name: l.id for l in task.get_labels()}
        frame_of = {Path(f.name).name: i for i, f in enumerate(task.get_frames_info())}
        assert [Path(f.name).name for f in task.get_frames_info()] == ordered, "thứ tự frame không đúng"

        new_shapes = [models.LabeledShapeRequest(
            type=s["type"], frame=frame_of[s["image"]], label_id=label_id[s["label"]], points=s["points"],
            source=s["source"], occluded=s["occluded"], z_order=s["z_order"], rotation=s["rotation"],
            attributes=[models.AttributeValRequest(**a) for a in s["attributes"]]) for s in shapes]
        new_tags = [models.LabeledImageRequest(
            frame=frame_of[t["image"]], label_id=label_id[t["label"]], source=t["source"],
            attributes=[models.AttributeValRequest(**a) for a in t["attributes"]]) for t in tags]
        task.update_annotations(models.PatchedLabeledDataRequest(shapes=new_shapes, tags=new_tags),
                                action=AnnotationUpdateAction.CREATE)

        names_new = {v: k for k, v in label_id.items()}
        _, shapes3, tags3 = snapshot(task, names_new)
        ok = sorted(map(key, shapes)) == sorted(map(key, shapes3)) and \
            collections.Counter((t["image"], t["label"]) for t in tags) == collections.Counter((t["image"], t["label"]) for t in tags3)
        print(f"[{'ok' if ok else 'LỆCH'}] task mới {task.id}: {len(shapes3)} hộp, {len(tags3)} tag")
        if not ok:
            sys.exit(f"Nhãn task mới không khớp bản cũ; bản sao lưu ở {backup}")

        # đổi id hộp cũ -> id mới trong các file theo dõi hộp máy vẽ
        new_by_key = collections.defaultdict(list)
        for s in shapes3:
            new_by_key[key(s)].append(s["id"])
        id_map = {s["id"]: new_by_key[key(s)].pop() for s in shapes}
        for f, col in ((cvat_dir / f"{name}_prelabel_uploaded.csv", "shape_id"),
                       (cvat_dir / f"{args.source}_review_boxes.csv", "shape_id")):
            if not f.exists():
                continue
            shutil.copy(f, f.with_name(f"{f.stem}_old_task{old_id}{f.suffix}"))
            with open(f, encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            n = 0
            for r in rows:
                if r.get("part", name) == name and int(r[col]) in id_map:
                    r[col] = str(id_map[int(r[col])]); n += 1
                elif r.get("part", name) == name:
                    r[col] = ""  # hộp này đã bị người xóa trước khi tạo lại task
            with open(f, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            print(f"  {f.name}: đổi {n} id sang task mới")


if __name__ == "__main__":
    main()
