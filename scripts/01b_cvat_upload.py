"""Bước 1 (phụ): tự tạo task trên CVAT cho các phần đã đóng gói bởi 01a_cvat_export.py.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/01b_cvat_upload.py --parts 3-14 --dry-run   # chỉ in ra sẽ làm gì, không cần token
    $env:CVAT_ACCESS_TOKEN = "<mã truy cập CVAT>"                # PowerShell, người dùng tự gán
    python scripts/01b_cvat_upload.py --parts 3                  # chạy thật một phần để kiểm tra
    python scripts/01b_cvat_upload.py --parts 3-14               # các phần còn lại

Với mỗi phần XX: tạo task <bộ>_partXX trong project và Organization đã chọn, tải lên
<bộ>_partXX_images.zip (sắp ảnh theo tên), rồi import nhãn "YOLO 1.1" từ <bộ>_partXX_yolo1.1.zip.
Task cùng tên đã có thì BỎ QUA: import nhãn sẽ ghi đè mọi hộp đã gán trong task đó.
Token chỉ đọc từ biến môi trường CVAT_ACCESS_TOKEN, không in ra và không ghi vào file.
"""

import argparse
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONVERTED = ROOT / "data" / "ppe4" / "converted"
HOST = "https://app.cvat.ai"


def parse_parts(text):
    """'3-14' hoặc '3,5,7' hoặc '3' -> danh sách số phần."""
    parts = []
    for chunk in text.split(","):
        a, _, b = chunk.partition("-")
        parts += range(int(a), int(b or a) + 1)
    return sorted(set(parts))


def zip_counts(images_zip, labels_zip):
    """Số ảnh trong zip ảnh và số hộp trong zip nhãn, để đối chiếu sau khi tạo task."""
    with zipfile.ZipFile(images_zip) as z:
        n_images = sum(1 for n in z.namelist() if not n.endswith("/"))
    n_boxes = 0
    with zipfile.ZipFile(labels_zip) as z:
        for n in z.namelist():
            if n.startswith("obj_train_data/") and n.endswith(".txt"):
                n_boxes += sum(1 for l in z.read(n).decode("utf-8").splitlines() if l.strip())
    return n_images, n_boxes


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parts", required=True, help="vd. 3-14, 3,5,7 hoặc 3")
    p.add_argument("--source", default="chv")
    p.add_argument("--org", default="ppeKhoaLuan", help="short name của Organization trên CVAT")
    p.add_argument("--project", default="CHV gloves")
    p.add_argument("--dry-run", action="store_true", help="chỉ kiểm tra file và in kế hoạch, không gọi CVAT")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")  # thông báo lỗi của sys.exit in ra stderr

    cvat_dir = CONVERTED / args.source / "cvat"
    plan = []
    for k in parse_parts(args.parts):
        name = f"{args.source}_part{k:02d}"
        images_zip, labels_zip = cvat_dir / f"{name}_images.zip", cvat_dir / f"{name}_yolo1.1.zip"
        missing = [f.name for f in (images_zip, labels_zip) if not f.exists()]
        if missing:
            sys.exit(f"Thiếu file cho {name}: {missing}")
        plan.append((name, images_zip, labels_zip, *zip_counts(images_zip, labels_zip)))

    for name, _, _, n_img, n_box in plan:
        print(f"[kế hoạch] {name}: {n_img} ảnh, {n_box} hộp có sẵn")
    if args.dry_run:
        print("--dry-run: không gọi CVAT.")
        return

    token = os.environ.get("CVAT_ACCESS_TOKEN")
    if not token:
        sys.exit("Chưa có biến môi trường CVAT_ACCESS_TOKEN (tự gán trong PowerShell rồi chạy lại).")

    from cvat_sdk import make_client, models  # import muộn để --dry-run chạy được khi chưa cài

    with make_client(HOST, access_token=token) as client:
        client.organization_slug = args.org
        projects = [pr for pr in client.projects.list() if pr.name == args.project]
        if len(projects) != 1:
            sys.exit(f"Tìm thấy {len(projects)} project tên '{args.project}' trong Organization '{args.org}', cần đúng 1.")
        project = projects[0]
        existing = {t.name for t in client.tasks.list() if t.project_id == project.id}
        print(f"Project '{project.name}' (id {project.id}); task đã có: {sorted(existing)}")

        for name, images_zip, labels_zip, n_img, n_box in plan:
            if name in existing:
                print(f"[bỏ qua] {name}: task đã tồn tại, không tạo lại và không import đè.")
                continue
            print(f"[tạo] {name} ...", flush=True)
            task = client.tasks.create_from_data(
                spec=models.TaskWriteRequest(name=name, project_id=project.id),
                resources=[str(images_zip)],
                data_params={"sorting_method": "lexicographical", "image_quality": 70},
                annotation_path=str(labels_zip),
                annotation_format="YOLO 1.1",
            )
            got_img = task.size
            got_box = len(task.get_annotations().shapes)
            ok = got_img == n_img and got_box == n_box
            print(f"[{'ok' if ok else 'LỆCH'}] {name}: task id {task.id}, ảnh {got_img}/{n_img}, hộp {got_box}/{n_box}")
            if not ok:
                sys.exit(f"Dừng lại: {name} không khớp với file zip, kiểm tra trên CVAT trước khi chạy tiếp.")


if __name__ == "__main__":
    main()
