"""Thử nghiệm 6 lớp: dùng OWLv2 (nhận diện theo chữ, không train) soát ảnh train tìm khung ủng, kính bị sót hoặc sai.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03w_ppe6_owl_scan.py --variant c2 --limit 100      # chạy thử trên 100 ảnh có khung ủng hoặc kính
    python scripts/03w_ppe6_owl_scan.py --variant c2                  # toàn bộ ảnh train

Chỉ đọc ảnh, nhãn của data/ppe6/dataset_<variant>/; không sửa nhãn. Ghi outputs/results/ppe6_owl/<variant>_<limit|all>.json:
mỗi ảnh các dự đoán (lớp, điểm, hộp chuẩn hóa) và tóm tắt: tỉ lệ tìm lại khung đã có, số chỗ nghi sót theo ngưỡng điểm.
Kết quả chỉ để chọn chỗ cần xem lại; không dùng trực tiếp làm nhãn. Tham số ở configs/ppe6.yaml mục `owl_scan`.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import box_iou_xyxy  # noqa: E402

OUT = ROOT / "outputs" / "results" / "ppe6_owl"


def gt_of(path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.split()
        if t and t[0] in ("4", "5"):
            c, x, y, w, h = int(t[0]), *map(float, t[1:5])
            out.append((c, (x - w / 2, y - h / 2, x + w / 2, y + h / 2)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variant", default="c2", choices=["c1", "c2"])
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["owl_scan"]
    from transformers import Owlv2ForObjectDetection, Owlv2Processor

    base = ROOT / "data" / "ppe6" / f"dataset_{args.variant}"
    imgs = sorted((base / "images" / "train").iterdir())
    if args.limit:
        has = [p for p in imgs if gt_of(base / "labels" / "train" / f"{p.stem}.txt")]
        random.Random(cfg["seed"]).shuffle(has)
        imgs = sorted(has[:args.limit])
    queries = [q for c in ("goggles", "boots") for q in cfg["queries"][c]]
    qcls = [4 if q in cfg["queries"]["goggles"] else 5 for q in queries]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = Owlv2Processor.from_pretrained(cfg["model"], use_fast=True)   # bản nhanh dùng torchvision, không cần scipy
    model = Owlv2ForObjectDetection.from_pretrained(cfg["model"], torch_dtype=torch.float16 if dev == "cuda" else torch.float32).to(dev).eval()
    res, t0 = {}, time.time()
    for n, p in enumerate(imgs):
        with Image.open(p) as im:
            im = im.convert("RGB")
            w, h = im.size
        inp = proc(text=[queries], images=im, return_tensors="pt").to(dev)
        if dev == "cuda":
            inp["pixel_values"] = inp["pixel_values"].half()
        with torch.no_grad():
            o = model(**inp)
        s = max(w, h)   # OWLv2 đệm ảnh thành hình vuông ở góc trên trái
        r = proc.post_process_object_detection(o, threshold=cfg["min_score"], target_sizes=torch.tensor([[s, s]]))[0]
        preds = []
        for sc, lab, b in zip(r["scores"].tolist(), r["labels"].tolist(), r["boxes"].tolist()):
            bb = (max(b[0], 0) / w, max(b[1], 0) / h, min(b[2], w) / w, min(b[3], h) / h)
            if bb[2] > bb[0] and bb[3] > bb[1]:
                preds.append((qcls[lab], round(sc, 4), [round(v, 5) for v in bb]))
        keep = []   # NMS đơn giản theo lớp
        for c, sc, bb in sorted(preds, key=lambda x: -x[1]):
            if all(c != k[0] or box_iou_xyxy(bb, k[2]) < cfg["nms_iou"] for k in keep):
                keep.append((c, sc, bb))
        res[p.name] = dict(gt=[[c, list(b)] for c, b in gt_of(base / "labels" / "train" / f"{p.stem}.txt")], pred=keep)
        if (n + 1) % 50 == 0:
            print(f"{n + 1}/{len(imgs)} ảnh, {(time.time() - t0) / (n + 1):.2f} giây mỗi ảnh", flush=True)
    sec = (time.time() - t0) / max(len(imgs), 1)
    summ = {}
    for c, name in ((4, "goggles"), (5, "boots")):
        for thr in cfg["report_scores"]:
            gt = found = miss = 0
            for v in res.values():
                g = [b for k, b in v["gt"] if k == c]
                pr = [b for k, s, b in v["pred"] if k == c and s >= thr]
                gt += len(g)
                found += sum(any(box_iou_xyxy(a, b) >= cfg["match_iou"] for b in pr) for a in g)
                miss += sum(not any(box_iou_xyxy(a, b) >= cfg["match_iou"] for a in g) for b in pr)
            summ[f"{name}@{thr}"] = dict(gt=gt, recall=round(found / max(gt, 1), 3), unmatched_preds=miss)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{args.variant}_{args.limit or 'all'}.json"
    out.write_text(json.dumps(dict(model=cfg["model"], queries=queries, sec_per_image=round(sec, 3), images=len(imgs), summary=summ, results=res)), encoding="utf-8")
    print(json.dumps(dict(sec_per_image=round(sec, 3), images=len(imgs), summary=summ), ensure_ascii=False))


if __name__ == "__main__":
    main()
