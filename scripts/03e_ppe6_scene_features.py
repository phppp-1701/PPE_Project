"""Thử nghiệm 6 lớp: tính đặc trưng ảnh để gom cảnh. Chỉ đọc ảnh, không sửa dữ liệu.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03e_ppe6_scene_features.py

Đọc data/ppe4/stats.csv và, nếu có, data/ppe6/external/{chvg,cppe2}/images.csv (cột file, image).
Ghi data/ppe6/scene/features.npz: `key` (tên file), `phash` (64 bit), `emb` (đặc trưng YOLO đã chuẩn hóa), `hist` (biểu đồ màu).
Ảnh đã có đặc trưng thì không tính lại. Tham số ở configs/ppe6.yaml mục `scene`.
"""

import csv
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ppe6" / "scene" / "features.npz"


def read_image(path, side):
    data = np.fromfile(str(path), dtype=np.uint8)
    im = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if im is None:
        return None
    r = side / max(im.shape[:2])
    return cv2.resize(im, (max(round(im.shape[1] * r), 8), max(round(im.shape[0] * r), 8)), interpolation=cv2.INTER_AREA)


def phash(im):
    """pHash 64 bit: DCT của ảnh xám 32x32, so 8x8 tần số thấp với trung vị."""
    g = cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    low = cv2.dct(g)[:8, :8].flatten()
    return np.packbits(low > np.median(low[1:]))


def hist(im):
    h = cv2.calcHist([cv2.cvtColor(im, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256]).flatten()
    return (h / max(np.linalg.norm(h), 1e-9)).astype(np.float32)


def image_list():
    rows = [(r["file"], ROOT / r["image"]) for r in csv.DictReader((ROOT / "data" / "ppe4" / "stats.csv").open(encoding="utf-8"))]
    for name in ("chvg", "cppe2"):   # cppe2: Construction-PPE bản mới (data/raw/construction_ppe_v2)
        extra = ROOT / "data" / "ppe6" / "external" / name / "images.csv"
        if extra.exists():
            rows += [(r["file"], ROOT / r["image"]) for r in csv.DictReader(extra.open(encoding="utf-8"))]
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["scene"]
    rows = image_list()
    old = {}
    if OUT.exists():
        z = np.load(OUT, allow_pickle=False)
        old = {k: i for i, k in enumerate(z["key"].tolist())}
    todo = [r for r in rows if r[0] not in old]
    print(f"{len(rows)} ảnh, cần tính {len(todo)}")
    keys, ph, hs, em = [], [], [], []
    if todo:
        import torch
        from ultralytics import YOLO

        model = YOLO(str(ROOT / cfg["weights"]))
        batch, names = [], []

        def flush():
            out = model.embed(batch, imgsz=cfg["imgsz"], device=0, verbose=False)
            for v in out:
                v = v.detach().float().cpu().numpy().ravel()
                em.append(v / max(np.linalg.norm(v), 1e-9))
            batch.clear()

        for i, (key, path) in enumerate(todo, 1):
            im = read_image(path, cfg["side"])
            if im is None:
                print("Không đọc được", path)
                continue
            keys.append(key)
            ph.append(phash(im))
            hs.append(hist(im))
            batch.append(im)
            if len(batch) == cfg["batch"]:
                flush()
            if i % 500 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
        if batch:
            flush()
        del torch
    if not keys and not old:
        sys.exit("Không có ảnh.")
    key = np.array(keys, dtype=str)
    ph, hs, em = np.array(ph), np.array(hs), np.array(em, dtype=np.float32)
    if old:
        key = np.concatenate([z["key"], key]) if len(keys) else z["key"]
        ph = np.concatenate([z["phash"], ph]) if len(keys) else z["phash"]
        hs = np.concatenate([z["hist"], hs]) if len(keys) else z["hist"]
        em = np.concatenate([z["emb"], em]) if len(keys) else z["emb"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT, key=key, phash=ph, hist=hs, emb=em)
    print("Đã ghi", OUT.relative_to(ROOT), len(key), em.shape)


if __name__ == "__main__":
    main()
