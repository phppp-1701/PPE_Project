"""Bước 1 (phụ): gán trước găng tay bằng YOLOE cho các phần CHV, rồi (tùy chọn) thêm hộp vào task CVAT.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/01c_prelabel_gloves.py --parts 2,3              # chỉ chạy mô hình, lưu CSV, không gọi CVAT
    python scripts/01c_prelabel_gloves.py --parts 2,3 --upload     # thêm hộp trong CSV vào task chv_partXX trên CVAT

Tham số mô hình và CVAT trong configs/prelabel.yaml. Đọc ảnh gốc trong data/raw/, danh sách ảnh từng phần
trong data/ppe4/converted/<bộ>/cvat/parts.csv. Ghi vào cùng thư mục cvat/:
    <bộ>_partXX_prelabel_gloves.csv    hộp máy vẽ: image, conf, cx, cy, w, h (chuẩn hóa)
    <bộ>_partXX_prelabel_uploaded.csv  (sau --upload) id hộp trên CVAT, frame, ảnh, tọa độ pixel
--upload chỉ THÊM hộp (nguồn "auto"), không sửa hay xóa hộp có sẵn; task đã có hộp "auto" thì dừng.
Token CVAT đọc từ biến môi trường CVAT_ACCESS_TOKEN hoặc file ~/.cvat_token; không in ra, không ghi vào project.
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


def parse_parts(text):
    parts = []
    for chunk in text.split(","):
        a, _, b = chunk.partition("-")
        parts += range(int(a), int(b or a) + 1)
    return sorted(set(parts))


def predict_part(model, keep_ids, cfg, images, out_csv):
    """Chạy YOLOE trên danh sách ảnh, ghi hộp găng ra CSV; trả về (số hộp, số ảnh có hộp)."""
    n_box, n_img = 0, 0
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["image", "conf", "cx", "cy", "w", "h"])
        for name, path in images:
            r = model.predict(path, conf=cfg["conf"], imgsz=cfg["imgsz"], classes=keep_ids,
                              device=cfg["device"], verbose=False)[0]
            boxes = r.boxes.xywhn.cpu().numpy()
            confs = r.boxes.conf.cpu().numpy()
            for (cx, cy, bw, bh), c in zip(boxes, confs):
                w.writerow([name, f"{c:.3f}", f"{cx:.6f}", f"{cy:.6f}", f"{bw:.6f}", f"{bh:.6f}"])
            n_box += len(boxes)
            n_img += bool(len(boxes))
    return n_box, n_img


def iou_xyxy(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def read_token():
    token = os.environ.get("CVAT_ACCESS_TOKEN")
    token_file = Path.home() / ".cvat_token"
    if not token and token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        sys.exit("Chưa có token: đặt biến môi trường CVAT_ACCESS_TOKEN hoặc tạo file ~/.cvat_token.")
    return token


def upload_part(client, models, project, cfg, part, pred_csv, out_csv):
    """Thêm hộp trong pred_csv vào task `part` (chỉ CREATE), ghi lại id các hộp đã thêm."""
    tasks = [t for t in client.tasks.list() if t.project_id == project.id and t.name == part]
    if len(tasks) != 1:
        sys.exit(f"Tìm thấy {len(tasks)} task tên {part} trong project, cần đúng 1.")
    task = tasks[0]
    label_id = {l.name: l.id for l in task.get_labels()}[cfg["target_label"]]
    frames = task.get_frames_info()
    frame_of = {Path(fr.name).name: (i, fr.width, fr.height) for i, fr in enumerate(frames)}

    ann = task.get_annotations()
    if any(s.label_id == label_id and s.source == cfg["source_tag"] for s in ann.shapes):
        sys.exit(f"{part}: task đã có hộp {cfg['target_label']} nguồn '{cfg['source_tag']}' (đã tải lên trước đó?), dừng.")
    existing = {}  # frame -> các hộp gloves đã có (người vẽ)
    for s in ann.shapes:
        if s.label_id == label_id and s.type.value == "rectangle":
            existing.setdefault(s.frame, []).append(s.points)

    shapes, skipped = [], 0
    with open(pred_csv, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["image"] not in frame_of:
                sys.exit(f"{part}: ảnh {r['image']} không có trong task.")
            i, W, H = frame_of[r["image"]]
            cx, cy, bw, bh = (float(r[k]) for k in ("cx", "cy", "w", "h"))
            pts = [(cx - bw / 2) * W, (cy - bh / 2) * H, (cx + bw / 2) * W, (cy + bh / 2) * H]
            if any(iou_xyxy(pts, e) >= cfg["skip_if_iou_with_existing"] for e in existing.get(i, [])):
                skipped += 1
                continue
            shapes.append(models.LabeledShapeRequest(type="rectangle", frame=i, label_id=label_id,
                                                     points=pts, source=cfg["source_tag"]))
    if shapes:
        from cvat_sdk.core.proxies.annotations import AnnotationUpdateAction
        task.update_annotations(models.PatchedLabeledDataRequest(shapes=shapes), action=AnnotationUpdateAction.CREATE)

    # Đọc lại để ghi id các hộp vừa thêm và đối chiếu số lượng
    added = [s for s in task.get_annotations().shapes if s.label_id == label_id and s.source == cfg["source_tag"]]
    name_of = {i: n for n, (i, _, _) in frame_of.items()}
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["shape_id", "frame", "image", "x1", "y1", "x2", "y2"])
        for s in sorted(added, key=lambda s: (s.frame, s.id)):
            w.writerow([s.id, s.frame, name_of[s.frame], *(f"{p:.1f}" for p in s.points)])
    return task.id, len(shapes), skipped, len(added)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parts", required=True, help="vd. 2,3 hoặc 2-3")
    p.add_argument("--source", default="chv")
    p.add_argument("--upload", action="store_true", help="thêm hộp trong CSV đã lưu vào task CVAT (không chạy lại mô hình)")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.environ.setdefault("YOLO_AUTOINSTALL", "False")  # không để Ultralytics tự cài gói

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    cvat_dir = CONVERTED / args.source / "cvat"
    with open(cvat_dir / "parts.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    parts = [f"{args.source}_part{k:02d}" for k in parse_parts(args.parts)]

    if not args.upload:
        from ultralytics import YOLOE

        model = YOLOE(cfg["model"])
        keep_ids = [k for k, v in model.names.items() if cfg["class_keyword"] in v.lower()]
        print(f"Mô hình {cfg['model']}, lớp giữ lại: {[model.names[k] for k in keep_ids]}, "
              f"imgsz {cfg['imgsz']}, conf {cfg['conf']}")
        for part in parts:
            images = [(r["image"], ROOT / "data" / "raw" / args.source / "images" / r["image"])
                      for r in rows if r["part"] == part]
            out = cvat_dir / f"{part}_prelabel_gloves.csv"
            n_box, n_img = predict_part(model, keep_ids, cfg, images, out)
            print(f"[dự đoán] {part}: {len(images)} ảnh, {n_box} hộp găng trên {n_img} ảnh -> {out.name}")
        return

    from cvat_sdk import make_client, models

    with make_client(cfg["cvat"]["host"], access_token=read_token()) as client:
        client.organization_slug = cfg["cvat"]["org"]
        projects = [pr for pr in client.projects.list() if pr.name == cfg["cvat"]["project"]]
        if len(projects) != 1:
            sys.exit(f"Tìm thấy {len(projects)} project tên '{cfg['cvat']['project']}', cần đúng 1.")
        for part in parts:
            pred = cvat_dir / f"{part}_prelabel_gloves.csv"
            if not pred.exists():
                sys.exit(f"Chưa có {pred.name}; chạy không có --upload trước.")
            tid, n_sent, n_skip, n_added = upload_part(client, models, projects[0], cfg, part, pred,
                                                       cvat_dir / f"{part}_prelabel_uploaded.csv")
            ok = n_added == n_sent
            print(f"[{'ok' if ok else 'LỆCH'}] {part}: task {tid}, thêm {n_sent} hộp, bỏ {n_skip} hộp trùng hộp đã có, "
                  f"trên CVAT có {n_added} hộp '{cfg['source_tag']}'")
            if not ok:
                sys.exit(f"Dừng lại: số hộp trên CVAT khác số hộp đã gửi ở {part}.")


if __name__ == "__main__":
    main()
