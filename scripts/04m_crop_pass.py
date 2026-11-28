"""C9: chạy detector lần hai trên vùng người cắt từ ảnh gốc, gộp hộp lớp nhỏ (găng, kính, ủng) với dự đoán toàn ảnh.

Ảnh val / test có cạnh dài trung vị khoảng 5.800 px; detector thu về 960 nên găng nhỏ mất chi tiết. Script đọc capture.npz
của 04d (dự đoán toàn ảnh), lấy hộp người, cắt vùng người từ ảnh gốc, chạy lại detector, đổi hộp các lớp `classes` về toạ
độ canvas của 04d, nhân conf với `conf_scale`, gộp bằng NMS theo lớp, rồi tính lại tp 10 mức IoU bằng đúng cách ghép của
Ultralytics 8.4.189 (`BaseValidator.match_predictions`). Ghi capture.npz cùng định dạng, nên 04j chấm như mọi bản khác.
Tham số ở `configs/ppe6.yaml` mục `crop_pass`.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04m_crop_pass.py --check --capture outputs/results/c5_eval/c8lab_c6_ft_val
    python scripts/04m_crop_pass.py --split val --capture outputs/results/c5_eval/c8lab_c6_ft_val --weights outputs/train/yolo11s_ppe6_c6_ft/weights/best.pt --out outputs/results/c5_eval/c8lab_c6_ft_crop_val
    python scripts/04j_c5_eval.py --split val --run c6_ft=outputs/results/c5_eval/c8lab_c6_ft_val --run c6_ft_crop=outputs/results/c5_eval/c8lab_c6_ft_crop_val --name c8lab_c6_vs_crop

`--check`: tính lại tp cho dự đoán gốc của capture, phải trùng tp Ultralytics đã lưu (kiểm tra cách ghép), không chạy model.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import yaml

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.detector import letterbox_square, unletterbox  # noqa: E402
EVAL = ROOT / "data" / "ppe6" / "c5" / "eval"
IOUV = np.linspace(0.5, 0.95, 10)


def box_iou(a, b):
    """IoU giữa hai mảng hộp xyxy: [len(a), len(b)]."""
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter + 1e-7)


def match_tp(pbox, pcls, gbox, gcls):
    """Chép BaseValidator.match_predictions (Ultralytics 8.4.189, không scipy). Dự đoán phải xếp conf giảm dần.

    Trả về tp bool [n_pred, 10]."""
    correct = np.zeros((len(pbox), len(IOUV)), dtype=bool)
    if not len(pbox) or not len(gbox):
        return correct
    iou = box_iou(gbox, pbox).astype(np.float32) * (gcls[:, None] == pcls[None, :])
    thr = IOUV.astype(np.float32)
    matched = np.zeros((iou.shape[0], len(thr)), dtype=bool)
    for j in np.flatnonzero((iou >= thr.min()).any(0)):
        available = np.where(matched, 0, iou[:, j, None])
        k = available.argmax(0)
        correct[j] = available[k, range(len(thr))] >= thr
        matched[k, range(len(thr))] |= correct[j]
    return correct


def nms(boxes, scores, iou_thr):
    """NMS thuần numpy (giữ hộp conf cao, bỏ hộp trùng IoU > iou_thr). Trả về chỉ số giữ lại, conf giảm dần."""
    order = np.argsort(-scores, kind="stable")
    keep = []
    while len(order):
        i = order[0]
        keep.append(i)
        if len(order) == 1:
            break
        ious = box_iou(boxes[i:i + 1], boxes[order[1:]])[0]
        order = order[1:][ious <= iou_thr]
    return np.array(keep, dtype=int)


def merge_image(pbox, pconf, pcls, extra, cfg):
    """Gộp dự đoán toàn ảnh với dự đoán từ crop (extra: [k, 6] x1 y1 x2 y2 conf cls, conf đã nhân conf_scale).

    Lớp ngoài `classes` giữ nguyên. Lớp trong `classes`: NMS trên hợp hai nguồn. Cắt còn max_det theo conf."""
    boxes, confs, clss = [pbox], [pconf], [pcls]
    for c in cfg["classes"]:
        e = extra[extra[:, 5] == c] if len(extra) else np.zeros((0, 6))
        if not len(e):
            continue
        m = pcls == c
        b = np.vstack([pbox[m], e[:, :4]])
        s = np.concatenate([pconf[m], e[:, 4]])
        k = nms(b, s, cfg["nms_iou"])
        boxes[0], confs[0], clss[0] = boxes[0][~(clss[0] == c)], confs[0][~(clss[0] == c)], clss[0][~(clss[0] == c)]
        boxes.append(b[k])
        confs.append(s[k])
        clss.append(np.full(len(k), c))
    b, s, c = np.vstack(boxes), np.concatenate(confs), np.concatenate(clss).astype(int)
    o = np.argsort(-s, kind="stable")[: cfg["max_det"]]
    return b[o], s[o], c[o]


def feet_crops(im, pbox, ratio_pad, cfg):
    """Round5 U1: vùng chân = từ feet_top x chiều cao hộp người tới đáy hộp (không có keypoint trên val), nới pad mỗi
    cạnh theo cỡ vùng chân, cắt theo mép ảnh. Bỏ vùng có cạnh dài < min_px (phóng to quá 2 lần không thêm chi tiết)."""
    g, px, py = ratio_pad
    h, w = im.shape[:2]
    crops, offs = [], []
    for b in pbox:
        x1, y1, x2, y2 = (b - [px, py, px, py]) / g
        y1 = y1 + cfg["feet_top"] * (y2 - y1)
        bw, bh = x2 - x1, y2 - y1
        x1, y1 = int(max(x1 - cfg["pad"] * bw, 0)), int(max(y1 - cfg["pad"] * bh, 0))
        x2, y2 = int(min(x2 + cfg["pad"] * bw, w)), int(min(y2 + cfg["pad"] * bh, h))
        if max(x2 - x1, y2 - y1) < cfg["min_px"]:
            continue
        sq, r, dx, dy = letterbox_square(im[y1:y2, x1:x2], cfg["imgsz"])
        crops.append(sq)
        offs.append((r, dx, dy, x1, y1))
    return crops, offs


def person_crops(im, pbox, ratio_pad, cfg):
    """Cắt vùng người (hộp canvas -> ảnh gốc, nới pad mỗi cạnh). Bỏ người có cạnh dài < min_side_ratio * imgsz."""
    g, px, py = ratio_pad
    h, w = im.shape[:2]
    crops, offs = [], []
    for b in pbox:
        x1, y1, x2, y2 = (b - [px, py, px, py]) / g
        bw, bh = x2 - x1, y2 - y1
        x1, y1 = int(max(x1 - cfg["pad"] * bw, 0)), int(max(y1 - cfg["pad"] * bh, 0))
        x2, y2 = int(min(x2 + cfg["pad"] * bw, w)), int(min(y2 + cfg["pad"] * bh, h))
        if max(x2 - x1, y2 - y1) < cfg["min_side_ratio"] * cfg["imgsz"]:
            continue
        sq, r, dx, dy = letterbox_square(im[y1:y2, x1:x2], cfg["imgsz"])   # cùng cỡ đầu vào như pipeline
        crops.append(sq)
        offs.append((r, dx, dy, x1, y1))
    return crops, offs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", required=True, help="thư mục capture.npz của 04d (dự đoán toàn ảnh)")
    ap.add_argument("--check", action="store_true", help="chỉ kiểm tra cách tính tp trên dự đoán gốc")
    ap.add_argument("--split", choices=["val", "test"])
    ap.add_argument("--weights")
    ap.add_argument("--out")
    ap.add_argument("--feet", type=float, nargs=3, metavar=("PAD", "IMGSZ", "TOP"),
                    help="round5 U1: dò ủng trên vùng chân (pad, imgsz, feet_top); --capture là capture đã có zoom")
    ap.add_argument("--classes", type=int, nargs="+", help="ghi đè crop_pass.classes (M1 27/11/2026: thử thêm mũ)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    z = np.load(Path(args.capture) / "capture.npz", allow_pickle=False)
    z = {k: z[k] for k in z.files}
    n_img = len(z["files"])
    if args.check:
        bad = 0
        for i in range(n_img):
            pm, gm = np.nonzero(z["img"] == i)[0], np.nonzero(z["gimg"] == i)[0]
            tp = match_tp(z["box"][pm], z["cls"][pm], z["gbox"][gm], z["gcls"][gm])
            bad += int((tp != z["tp"][pm]).any(1).sum())
        print(f"Kiểm tra tp: {len(z['conf'])} dự đoán, {bad} dự đoán khác tp của Ultralytics")
        sys.exit(1 if bad else 0)
    if not (args.split and args.weights and args.out):
        sys.exit("Cần --split, --weights, --out (hoặc --check)")
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["crop_pass"]
    if args.classes:
        cfg["classes"] = args.classes
    if args.feet:
        cfg.update(pad=args.feet[0], imgsz=int(args.feet[1]), feet_top=args.feet[2], classes=[5],
                   min_px=int(args.feet[1]) // 2)
    import cv2
    from ultralytics import YOLO

    model = YOLO(args.weights)
    img_dir = EVAL / args.split / "images"
    out_rows, n_crops, t_model, t0 = [], 0, 0.0, time.time()
    for i, f in enumerate(z["files"].tolist()):
        pm = np.nonzero(z["img"] == i)[0]
        pbox, pconf, pcls = z["box"][pm].astype(np.float64), z["conf"][pm].astype(np.float64), z["cls"][pm].astype(int)
        persons = pbox[(pcls == 0) & (pconf >= cfg["person_conf"])]
        extra = np.zeros((0, 6))
        if len(persons):
            im = cv2.imread(str(img_dir / f))
            if im is None:
                sys.exit(f"Không đọc được ảnh {img_dir / f}")
            crops, offs = (feet_crops if args.feet else person_crops)(im, persons, z["ratio_pad"][i], cfg)
            if crops:
                g, px, py = z["ratio_pad"][i]
                t1 = time.time()
                res = [model.predict(c, imgsz=cfg["imgsz"], conf=0.001, iou=0.7, verbose=False, device=0,
                                     quantize=16 if cfg["half"] else None)[0] for c in crops]   # từng ảnh, như pipeline
                t_model += time.time() - t1
                n_crops += len(crops)
                rows = []
                for r, off in zip(res, offs):
                    xy = r.boxes.xyxy.cpu().numpy().astype(np.float64)
                    cf = r.boxes.conf.cpu().numpy().astype(np.float64)
                    cl = r.boxes.cls.cpu().numpy().astype(int)
                    m = np.isin(cl, cfg["classes"])
                    q = unletterbox(xy[m], *off) * g + [px, py, px, py]
                    rows.append(np.column_stack([q, cf[m] * cfg["conf_scale"], cl[m]]))
                extra = np.vstack(rows) if rows else extra
        b, s, c = merge_image(pbox, pconf, pcls, extra, cfg)
        gm = np.nonzero(z["gimg"] == i)[0]
        out_rows.append((b, s, c, match_tp(b, c, z["gbox"][gm], z["gcls"][gm])))
        if i % 200 == 0:
            print(f"{i}/{n_img} ảnh, {n_crops} crop, {time.time() - t0:.0f} giây")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    idx = np.concatenate([[i] * len(r[1]) for i, r in enumerate(out_rows)]).astype(int)
    np.savez_compressed(out / "capture.npz", files=z["files"], img=idx, box=np.vstack([r[0] for r in out_rows]).astype(np.float32),
                        conf=np.concatenate([r[1] for r in out_rows]).astype(np.float32), cls=np.concatenate([r[2] for r in out_rows]),
                        tp=np.vstack([r[3] for r in out_rows]), gimg=z["gimg"], gbox=z["gbox"], gcls=z["gcls"], canvas=z["canvas"],
                        ori=z["ori"], ratio_pad=z["ratio_pad"])
    meta = dict(base_capture=str(args.capture), weights=str(args.weights), split=args.split, crop_pass=cfg, images=n_img,
                crops=n_crops, crops_per_image=round(n_crops / n_img, 3), model_seconds=round(t_model, 1),
                ms_per_crop=round(1000 * t_model / max(n_crops, 1), 2), note="thời gian đo trong lúc chấm (gồm tiền xử lý của predict), không thay cho 07")
    (out / "crop_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Đã ghi", out, json.dumps({k: meta[k] for k in ("crops", "crops_per_image", "ms_per_crop")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
