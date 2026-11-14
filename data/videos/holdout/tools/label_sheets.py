"""Ảnh tờ để Claude gán nhãn tham chiếu cho video holdout (không có dự đoán của hệ thống trên ảnh).

Lượt A (--pass A): cả khung, mỗi 0,5 s, vẽ track người do 05f tạo (yolo11s.pt COCO), nhãn T<id>.
Lượt B (--pass B): ảnh cắt sát từng track, mỗi 1/3 s, lệch nửa bước so với khung 0 (khác thời điểm lượt A).
Cách chạy (từ thư mục gốc, .venv):
    python data/videos/holdout/tools/label_sheets.py --pass A --out <thư mục ảnh> h1 h2 ...
Track đọc từ outputs/results/video/holdout/<video>/prefill/annotations.xml, hoặc --labels <thư mục>/<video>/annotations.xml.
"""

import argparse
import re
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[4]


def tracks(v, labels=None):
    src = Path(labels) / v / "annotations.xml" if labels else ROOT / f"outputs/results/video/holdout/{v}/prefill/annotations.xml"
    x = src.read_text(encoding="utf-8")
    out = {}
    for tid, body in re.findall(r'<track id="(\d+)"[^>]*>(.*?)</track>', x, re.S):
        out[int(tid)] = {int(f): None if o == "1" else [float(a), float(b), float(c), float(d)] for f, o, a, b, c, d in re.findall(
            r'frame="(\d+)" keyframe="1" outside="(\d)" occluded="0" xtl="([\d.]+)" ytl="([\d.]+)" xbr="([\d.]+)" ybr="([\d.]+)"', body)}
    return out


def at(bx, f):
    ks = [k for k in bx if k <= f]
    return bx[max(ks)] if ks else None


def grid(tiles, per, rows_per_sheet, prefix):
    rows = []
    for i in range(0, len(tiles), per):
        r = tiles[i:i + per]
        r += [np.zeros_like(tiles[0])] * (per - len(r))
        rows.append(np.hstack(r))
    for j in range(0, len(rows), rows_per_sheet):
        cv2.imwrite(f"{prefix}_{j // rows_per_sheet}.jpg", np.vstack(rows[j:j + rows_per_sheet]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return (len(rows) + rows_per_sheet - 1) // rows_per_sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="p", choices=["A", "B"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--labels", help="thư mục nhãn đã dựng (build_labels.py); lượt B dùng hộp người của nhãn")
    ap.add_argument("videos", nargs="+")
    a = ap.parse_args()
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for v in a.videos:
        T = tracks(v, a.labels)
        cap = cv2.VideoCapture(str(ROOT / f"data/videos/holdout/{v}.mp4"))
        n, fps = int(cap.get(7)), cap.get(5)
        tiles = []
        if a.p == "A":
            step = max(1, round(fps / 2))
            for f in range(0, n, step):
                cap.set(1, f)
                ok, im = cap.read()
                if not ok:
                    continue
                for tid, bx in T.items():
                    b = at(bx, f)
                    if b:
                        cv2.rectangle(im, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 255, 0), 3)
                        cv2.putText(im, f"T{tid}", (int(b[0]) + 5, int(b[1]) + 40), 0, 1.4, (0, 255, 0), 3)
                h, w = im.shape[:2]
                im = cv2.resize(im, (int(360 * w / h), 360))
                cv2.putText(im, f"f{f}", (5, 30), 0, 1.0, (0, 255, 255), 2)
                tiles.append(im)
            per = 4 if tiles[0].shape[1] > 400 else 8
            k = grid(tiles, per, 4, str(out / f"A_{v}"))
        else:
            step = max(1, round(fps / 3))
            for f in range(step // 2, n, step):
                cap.set(1, f)
                ok, im = cap.read()
                if not ok:
                    continue
                for tid, bx in T.items():
                    b = at(bx, f)
                    if not b:
                        continue
                    x1, y1, x2, y2 = [int(q) for q in b]
                    pad = int(0.05 * (x2 - x1))
                    c = im[max(0, y1 - pad):y2, max(0, x1 - pad):x2 + pad]
                    if c.size == 0:
                        continue
                    c = cv2.resize(c, (int(300 * c.shape[1] / c.shape[0]), 300))
                    c = cv2.copyMakeBorder(c, 0, 0, 0, max(0, 300 - c.shape[1]), cv2.BORDER_CONSTANT)[:, :300]
                    cv2.putText(c, f"f{f} T{tid}", (4, 22), 0, 0.7, (0, 255, 255), 2)
                    tiles.append(c)
            k = grid(tiles, 8, 4, str(out / f"B_{v}"))
        print(v, n, "khung", round(fps, 2), "fps", len(tiles), "ô", k, "tấm", "track", sorted(T))


if __name__ == "__main__":
    main()
