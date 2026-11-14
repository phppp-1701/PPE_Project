"""Chọn hình học ảnh cắt và ngưỡng của bộ phân loại bộ phận (phương án 2) trên val. Không đụng test, video.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv, có outputs/train/yolo11n_cls_parts/weights/best.pt):
    python scripts/05e_select_part_cls.py
    python scripts/05e_select_part_cls.py --weights outputs/train/yolo11n_cls_parts_v4/weights/best.pt --out val_select_v4.json
    (--weights mặc định part_cls.weights; --out là tên file trong outputs/results/parts_cls/, mặc định val_select.json)

1. Lấy các hộp bộ phận của val như 03y (collect_items, only val): găng/tay trần, ủng/giày thường, kính BH/kính thường/không kính.
2. Tìm người bằng YOLO11n-pose trên cả ảnh, rồi chạy PoseEstimator của pipeline trên ảnh cắt từng người (như khi chạy thật).
3. Mỗi hộp nhãn ghép với điểm gốc gần tâm hộp nhất (cổ tay có khuỷu, mắt cá có gối, trung điểm hai mắt), cách tâm
   không quá cạnh dài của hộp. Không ghép được: ghi vào độ phủ, không vào phần chọn.
4. Với từng hình học trong `calibration.part_geom_grid`: cắt theo parts.py, phân loại, tính độ chính xác cân bằng
   (trung bình độ nhạy lớp có PPE và lớp không có PPE, ngưỡng 0,5). Chọn hình học cao nhất.
5. Với hình học đã chọn: t_pos = ngưỡng nhỏ nhất trong `part_thr_grid` mà p >= t_pos đạt độ chính xác
   `part_cls.precision_target.pos`; t_neg tương tự cho 1 - p với mục tiêu `neg`. Không đạt: null.
Ghi outputs/results/parts_cls/val_select.json; in khối YAML gợi ý, người chép vào configs/pipeline.yaml mục part_cls.
"""

import argparse
import importlib.util
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe import load_config  # noqa: E402
from ppe.parts import PART_CLASSES, cut, match_anchor, people_keypoints, ppe_prob  # noqa: E402
from ppe.pose import PoseEstimator  # noqa: E402

OUT_DIR = ROOT / "outputs" / "results" / "parts_cls"
CLS2PPE = {c: ppe for ppe, (pos, negs) in PART_CLASSES.items() for c in (pos, *negs)}


def load_03y():
    spec = importlib.util.spec_from_file_location("p03y", ROOT / "scripts" / "03y_ppe6_part_crops.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def geoms(grid, part):
    """Mọi tổ hợp tham số của lưới bộ phận (k, s cho tay chân; s cho mắt; s, h cho thân)."""
    g = grid[part]
    keys = sorted(g)
    return [dict(zip(keys, vals)) for vals in itertools.product(*(g[k] for k in keys))]


def precision_at(p, y, t):
    sel = p >= t
    n = int(sel.sum())
    return (float((y[sel] == 1).mean()) if n else None), n, float(sel[y == 1].mean()) if (y == 1).any() else None


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=None, help="trọng số bộ phân loại; mặc định part_cls.weights")
    ap.add_argument("--out", default="val_select.json", help="tên file kết quả trong outputs/results/parts_cls/")
    args = ap.parse_args()
    OUT = OUT_DIR / args.out
    from ultralytics import YOLO

    cfg = load_config()
    pc = cfg["part_cls"]
    cal = cfg["calibration"]
    ppe6 = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    items = [it for it in load_03y().collect_items(ppe6, only=("val",), chv_torso=True) if it[0] == "val"]
    by_img = defaultdict(list)
    for _, cls, img, bx, src in items:
        by_img[img].append((cls, bx, src))
    print(f"val: {len(items)} hộp bộ phận, {len(by_img)} ảnh")

    person_model = YOLO(ROOT / cfg["pose"]["weights"])
    pose = PoseEstimator(cfg, ROOT)
    clf = YOLO(ROOT / (args.weights or pc["weights"]))
    names = clf.names
    part_of = {"gloves": "hand", "boots": "foot", "goggles": "eye"}
    if "vest" in names.values():   # bản 3 có áo
        part_of["vest"] = "torso"
    if "helmet" in names.values():   # bản 4 có mũ
        part_of["helmet"] = "head"
    items = [it for it in items if CLS2PPE[it[1]] in part_of]
    by_img = defaultdict(list)
    for _, cls, img, bx, src in items:
        by_img[img].append((cls, bx, src))
    grid = {part: geoms(cal["part_geom_grid"], part) for part in part_of.values()}
    probs = defaultdict(list)       # (part, chỉ số hình học) -> [(p, y)]
    cover = defaultdict(lambda: [0, 0])  # lớp -> [ghép được, tổng]
    for n, (img, objs) in enumerate(sorted(by_img.items())):
        im = cv2.imdecode(np.fromfile(str(ROOT / img), dtype=np.uint8), cv2.IMREAD_COLOR)
        people = people_keypoints(im, person_model, pose, cfg["detector"]["device"])
        crops, keys = [], []
        for cls, bx, _ in objs:
            ppe = CLS2PPE[cls]
            cover[cls][1] += 1
            mk = match_anchor(people, ppe, bx, pc["kp_conf"])
            if mk is None:
                continue
            cover[cls][0] += 1
            part = part_of[ppe]
            y = int(cls == PART_CLASSES[ppe][0])
            for gi, g in enumerate(grid[part]):
                cr = cut(im, mk(g), pc["min_px"])
                if cr is not None:
                    crops.append(cr)
                    keys.append((part, gi, ppe, y))
        if crops:
            for (part, gi, ppe, y), rr in zip(keys, clf.predict(crops, imgsz=pc["imgsz"], device=cfg["detector"]["device"], verbose=False)):
                probs[(part, gi)].append((ppe_prob(rr.probs.data.cpu().numpy(), names, ppe), y))
        if (n + 1) % 200 == 0:
            print(f"  {n + 1}/{len(by_img)} ảnh")

    res = dict(weights=args.weights or pc["weights"], coverage={c: dict(matched=a, total=b) for c, (a, b) in sorted(cover.items())}, parts={})
    tg = cal["part_thr_grid"]
    ts = np.round(np.arange(tg["start"], tg["stop"] + 1e-9, tg["step"]), 4)
    chosen_geom, chosen_thr = {}, {}
    for ppe, part in part_of.items():
        rows = []
        for gi, g in enumerate(grid[part]):
            v = np.array(probs[(part, gi)]) if probs[(part, gi)] else np.zeros((0, 2))
            if not len(v):
                continue
            p, y = v[:, 0], v[:, 1].astype(int)
            rp = float((p[y == 1] >= 0.5).mean()) if (y == 1).any() else 0.0
            rn = float((p[y == 0] < 0.5).mean()) if (y == 0).any() else 0.0
            rows.append(dict(geom=g, n=len(v), n_pos=int(y.sum()), recall_pos=round(rp, 4), recall_neg=round(rn, 4),
                             bal_acc=round((rp + rn) / 2, 4), gi=gi))
        best = max(rows, key=lambda r: r["bal_acc"])
        v = np.array(probs[(part, best["gi"])])
        p, y = v[:, 0], v[:, 1].astype(int)
        thr = {}
        for kind, score, lab in (("pos", p, 1), ("neg", 1 - p, 0)):
            yy = (y == lab).astype(int)
            pick = None
            for t in ts:
                prec, cnt, rec = precision_at(score, yy, t)
                if prec is not None and prec >= pc["precision_target"][kind]:
                    pick = dict(t=float(t), precision=round(prec, 4), n_selected=cnt, recall=round(rec, 4))
                    break
            thr[kind] = pick
            bm = max(((precision_at(score, yy, t)[0] or 0, float(t)) for t in ts if precision_at(score, yy, t)[1] >= 10), default=None)
            thr[kind + "_max_precision"] = bm and dict(precision=round(bm[0], 4), t=bm[1])   # để biết còn cách mục tiêu bao xa
        res["parts"][ppe] = dict(grid=rows, chosen=best, thresholds=thr)
        chosen_geom[part] = best["geom"]
        chosen_thr[ppe] = {"t_pos": thr["pos"] and thr["pos"]["t"], "t_neg": thr["neg"] and thr["neg"]["t"]}
    res["suggest"] = dict(geometry=chosen_geom, thresholds=chosen_thr, precision_target=pc["precision_target"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res["coverage"], ensure_ascii=False))
    for ppe, d in res["parts"].items():
        print(ppe, "chọn", d["chosen"], "| ngưỡng", d["thresholds"])
    print("Gợi ý cho configs/pipeline.yaml:\n" + yaml.safe_dump(res["suggest"], allow_unicode=True, sort_keys=False))
    print("Ghi", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
