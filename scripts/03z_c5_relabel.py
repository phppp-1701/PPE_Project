"""C5 bước B, F (kế hoạch docs/experiments/2026-11-16_c5_detector_plan.md): sửa nhãn găng, ủng, kính; mở rộng val, test
kính, ủng. Nhãn máy: lượt máy (OWLv2, bộ phân loại bộ phận, detector C4) chỉ ĐỀ XUẤT chỗ cần xem; Claude xem ảnh và quyết
định (lượt `machine_pass_claude`). Không phải nhãn người, không vào human_review.csv. Không sửa data/raw, data/ppe4.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv; HF_HUB_OFFLINE=1 vì OWLv2 đã có trong cache):
    python scripts/03z_c5_relabel.py owl         # OWLv2 cả ảnh trên ảnh đánh giá (ppe4 val, test + val_new, test_new) -> owl_eval.json
    python scripts/03z_c5_relabel.py c4pred      # detector C4 trên ảnh train C2 -> c4_train_pred.json (đề xuất cho train)
    python scripts/03z_c5_relabel.py c4pred --eval   # C4 trên ảnh đánh giá -> c4_eval_pred.json (chỉ đề xuất găng)
    python scripts/03z_c5_relabel.py hands       # bộ phân loại tay trên mọi hộp hands SH17 không trùng găng -> sh17_hands.csv

Tham số ở configs/ppe6.yaml mục `c5_relabel`. Kết quả ở `c5_relabel.out` (data/ppe6/c5/).
"""

import argparse
import csv
import json
import os
import random
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
P4 = ROOT / "data" / "ppe4" / "dataset"
P6 = ROOT / "data" / "ppe6" / "dataset"
C2 = ROOT / "data" / "ppe6" / "dataset_c2"
EXTRA = ROOT / "data" / "ppe6" / "c4_extra"
CLASSES = {0: "person", 1: "helmet", 2: "vest", 3: "gloves", 4: "goggles", 5: "boots"}


def cfg():
    return yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["c5_relabel"]


def out_dir():
    d = ROOT / cfg()["out"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def imread(p):
    return cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / max((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i, 1e-12)


def ioa(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max((a[2] - a[0]) * (a[3] - a[1]), 1e-12)


def yolo_rows(path):
    """[(lớp, [x0, y0, x1, y1] chuẩn hóa)] của một file nhãn YOLO."""
    out = []
    if not Path(path).exists():
        return out
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        t = line.split()
        if t:
            c, cx, cy, w, h = int(t[0]), *map(float, t[1:5])
            out.append((c, [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]))
    return out


def eval_images():
    """Ảnh đánh giá: {file: (tập, đường dẫn ảnh, đường dẫn nhãn gốc)}. tập: val (ppe4 val), test (ppe4 test),
    val_new, test_new (ảnh của cảnh đánh giá lớp mới lấy từ ppe4 train). Ảnh val_new/test_new trùng ppe4 val/test giữ
    tập ppe4 nhưng nhãn lớp mới lấy từ bản _draft."""
    out = {}
    for s in ("val", "test"):
        for p in sorted((P4 / "images" / s).iterdir()):
            out[p.name] = (s, p, P4 / "labels" / s / (p.stem + ".txt"))
    for s in ("val_new", "test_new"):
        for p in sorted((P6 / "images" / f"{s}_draft").iterdir()):
            if p.name not in out:
                out[p.name] = (s, p, P6 / "labels" / f"{s}_draft" / (p.stem + ".txt"))
    return out


def chvg_images():
    """Ảnh CHVG đánh giá kính (bước F, kính): {file: (chvg_val | chvg_test, ảnh, nhãn _draft)}. Hộp kính trong nhãn đã có
    người chốt (07/11/2026); ảnh còn pending vì chưa xem cả ảnh tìm kính sót. Chỉ dùng cho lớp kính."""
    out = {}
    for s in ("val", "test"):
        for p in sorted((P6 / "images" / f"chvg_glass_{s}_draft").iterdir()):
            out[p.name] = (f"chvg_{s}", p, P6 / "labels" / f"chvg_glass_{s}_draft" / (p.stem + ".txt"))
    return out


def sh17_objects(raw_image):
    """{tên lớp SH17: [hộp chuẩn hóa]} từ nhãn VOC gốc."""
    root = ET.parse(ROOT / "data" / "raw" / "sh17" / "voc_labels" / (Path(raw_image).stem + ".xml")).getroot()
    w, h = float(root.find("size/width").text), float(root.find("size/height").text)
    obj = {}
    for o in root.iter("object"):
        bb = o.find("bndbox")
        x0, y0, x1, y1 = (float(bb.find(k).text) for k in ("xmin", "ymin", "xmax", "ymax"))
        obj.setdefault(o.find("name").text, []).append([x0 / w, y0 / h, x1 / w, y1 / h])
    return obj


def cmd_owl(args):
    """OWLv2 cả ảnh, mọi câu hỏi của c5_relabel.owl.queries; lưu dự đoán >= min_score sau NMS theo lớp."""
    import torch
    from PIL import Image
    from transformers import Owlv2ForObjectDetection, Owlv2Processor

    c = cfg()["owl"]
    queries = [(k, q) for k, qs in c["queries"].items() for q in qs]
    proc = Owlv2Processor.from_pretrained(c["model"], use_fast=True)   # bản nhanh dùng torchvision, không cần scipy
    model = Owlv2ForObjectDetection.from_pretrained(c["model"], dtype=torch.float16).to("cuda").eval()
    path = out_dir() / "owl_eval.json"
    res = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}   # chạy tiếp nếu bị ngắt
    imgs = [(f, v) for f, v in (chvg_images() if args.chvg else eval_images()).items() if f not in res]
    t0 = time.time()
    for n, (f, (s, p, _)) in enumerate(imgs):
        with Image.open(p) as im:
            im = im.convert("RGB")
            w, h = im.size
        inp = proc(text=[[q for _, q in queries]], images=im, return_tensors="pt").to("cuda")
        inp["pixel_values"] = inp["pixel_values"].half()
        with torch.no_grad():
            o = model(**inp)
        side = max(w, h)   # OWLv2 đệm ảnh thành hình vuông ở góc trên trái
        r = proc.post_process_object_detection(o, threshold=c["min_score"], target_sizes=torch.tensor([[side, side]]))[0]
        keep = []
        for sc, lab, b in sorted(zip(r["scores"].tolist(), r["labels"].tolist(), r["boxes"].tolist()), key=lambda x: -x[0]):
            cls = queries[lab][0]
            bb = [max(b[0], 0) / w, max(b[1], 0) / h, min(b[2], w) / w, min(b[3], h) / h]
            if bb[2] > bb[0] and bb[3] > bb[1] and all(k[0] != cls or iou(bb, k[2]) < c["nms_iou"] for k in keep):
                keep.append((cls, round(sc, 4), [round(v, 5) for v in bb]))
        res[f] = dict(set=s, pred=keep)
        if (n + 1) % 100 == 0 or n + 1 == len(imgs):
            path.write_text(json.dumps(res), encoding="utf-8")
            print(f"{n + 1}/{len(imgs)} ảnh, {(time.time() - t0) / (n + 1):.2f} giây/ảnh", flush=True)
    path.write_text(json.dumps(res), encoding="utf-8")


def cmd_c5pred_sh17(args):
    """C6 (kế hoạch mục C6): detector C5-s960 trên ảnh SH17 của train C5 (dataset_c5), lưu dự đoán ủng conf >= 0,1
    -> c5_sh17_boots_pred.json. Chỉ để chọn hộp giày SH17 cần Claude xem."""
    from ultralytics import YOLO

    model = YOLO(str(ROOT / "outputs" / "train" / "yolo11s_ppe6_c5_s960" / "weights" / "best.pt"))
    imgs = sorted((out_dir() / "dataset_c5" / "images" / "train").glob("sh17__*"))
    res = {}
    for i in range(0, len(imgs), 16):
        batch = imgs[i:i + 16]
        for p, r in zip(batch, model.predict([str(p) for p in batch], imgsz=960, conf=0.1, device=0, verbose=False, classes=[5])):
            res[p.name] = [(round(float(s_), 4), [round(float(v), 5) for v in b]) for s_, b in zip(r.boxes.conf.tolist(), r.boxes.xyxyn.tolist())]
        if (i // 16) % 50 == 0:
            print(f"{i + len(batch)}/{len(imgs)}", flush=True)
    (out_dir() / "c5_sh17_boots_pred.json").write_text(json.dumps(res), encoding="utf-8")


def candidates_sh17boots(c, d):
    """C6: hộp shoes / foot của SH17 train (ảnh trong dataset_c5) không trùng hộp ủng đã có (IoU < new_iou). Đề xuất cho
    Claude xem khi C5-s960 có hộp ủng trùng (IoU >= new_iou, conf >= 0,1) hoặc bộ phân loại chân p >= hand_p. Mã s....."""
    pred = json.loads((d / "c5_sh17_boots_pred.json").read_text(encoding="utf-8"))
    raw_of = {Path(r["file"]).stem: r["image"] for r in rd(ROOT / "data" / "ppe4" / "stats.csv")}   # ảnh che lưu .jpg
    base = d / "dataset_c5"
    allc = []
    for p in sorted((base / "images" / "train").glob("sh17__*")):
        gt = [b for k, b in yolo_rows(base / "labels" / "train" / (p.stem + ".txt")) if k == 5]
        obj = sh17_objects(raw_of[p.stem])
        shoes = obj.get("shoes", [])
        boxes = shoes + [b for b in obj.get("foot", []) if all(iou(b, q) < 0.5 for q in shoes)]
        for b in boxes:
            if all(iou(b, g) < c["new_iou"] for g in gt):
                hit = max([s_ for s_, q in pred.get(p.name, []) if iou(b, q) >= c["new_iou"]], default=0.0)
                allc.append(dict(task="shoes_cls_train", set="train", file=p.name, img=p.relative_to(ROOT).as_posix(),
                                 target=fmt(b), sugg="[]", meta=json.dumps(dict(c5_conf=hit))))
    probs = part_probs([dict(it, item=f"x{i}") for i, it in enumerate(allc)])
    items = [it for i, it in enumerate(allc) if json.loads(it["meta"])["c5_conf"] > 0 or probs.get(f"x{i}", 0) >= c["hand_p"]]
    print("hộp giày SH17 train", len(allc), "-> đưa xem", len(items))
    rng = random.Random(cfg()["seed"] + 3)
    rng.shuffle(items)
    for i, it in enumerate(items):
        it["item"] = f"s{i:05d}"
    with open(d / "review_items_sh17boots.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ITEM_COLS)
        w.writeheader()
        w.writerows(items)


def cmd_c4pred(args):
    """Detector C4 trên ảnh train C2 (imgsz 960 như lúc train), lưu dự đoán găng, kính, ủng conf >= 0,1."""
    from ultralytics import YOLO

    model = YOLO(str(ROOT / "outputs" / "train" / "yolo11s_ppe6_c4" / "weights" / "best.pt"))
    if args.eval:   # ảnh đánh giá: chỉ là một nguồn đề xuất găng thiếu nhãn, gộp với OWLv2 và bộ phân loại tay (kế hoạch mục 2B)
        imgs = [p for _, p, _ in eval_images().values()]
    else:   # train C2 + ảnh Construction-PPE bản mới của bộ phụ C4 (ảnh crop, shrink sinh lại từ nhãn đã sửa)
        imgs = sorted((C2 / "images" / "train").iterdir()) + sorted(EXTRA.glob("images/train/cppe2__*"))
    res = {}
    t0 = time.time()
    for i in range(0, len(imgs), 16):
        batch = imgs[i:i + 16]
        for p, r in zip(batch, model.predict([str(p) for p in batch], imgsz=960, conf=0.1, device=0, verbose=False, classes=[3, 4, 5])):
            res[p.name] = [(int(c), round(float(s), 4), [round(float(v), 5) for v in b])
                           for c, s, b in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxyn.tolist())]
        if (i // 16) % 50 == 0:
            print(f"{i + len(batch)}/{len(imgs)} ảnh, {time.time() - t0:.0f} giây", flush=True)
    (out_dir() / ("c4_eval_pred.json" if args.eval else "c4_train_pred.json")).write_text(json.dumps(res), encoding="utf-8")


def cmd_hands(args):
    """Mọi hộp hands SH17 không trùng găng (ioa > 0,5), mọi phần chia ppe4; p găng của bộ phân loại tay."""
    from ultralytics import YOLO

    c = cfg()["propose"]
    model = YOLO(str(ROOT / c["hands_weights"]))
    idx = {v: k for k, v in model.names.items()}
    rows = []
    for r in rd(ROOT / "data" / "ppe4" / "stats.csv"):
        if r["source"] != "sh17" or r["split"] not in ("train", "val", "test"):
            continue
        obj = sh17_objects(r["image"])
        for k, hd in enumerate(obj.get("hands", [])):
            if not any(ioa(hd, g) > 0.5 for g in obj.get("gloves", [])):
                rows.append(dict(file=r["file"], split=r["split"], raw=r["image"], k=k, box=hd))
    print(len(rows), "hộp hands", flush=True)
    cache = {}
    for i in range(0, len(rows), 128):
        crops, ok = [], []
        for j, r in enumerate(rows[i:i + 128]):
            if r["raw"] not in cache:
                cache.clear()
                cache[r["raw"]] = imread(ROOT / r["raw"])
            im = cache[r["raw"]]
            H, W = im.shape[:2]
            b = [r["box"][0] * W, r["box"][1] * H, r["box"][2] * W, r["box"][3] * H]
            side = max(b[2] - b[0], b[3] - b[1]) * c["context"]
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            crop = im[int(max(cy - side / 2, 0)):int(min(cy + side / 2, H)), int(max(cx - side / 2, 0)):int(min(cx + side / 2, W))]
            if crop.size:
                crops.append(crop)
                ok.append(i + j)
        for j, pr in zip(ok, model.predict(crops, imgsz=160, device=0, verbose=False)):
            p = pr.probs.data.cpu().numpy()
            rows[j]["p_glove"] = round(float(p[idx["glove"]] / max(p[idx["glove"]] + p[idx["bare_hand"]], 1e-9)), 4)
        if (i // 128) % 20 == 0:
            print(f"{i}/{len(rows)}", flush=True)
    with open(out_dir() / "sh17_hands.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "split", "k", "x0", "y0", "x1", "y1", "p_glove"])
        for r in rows:
            w.writerow([r["file"], r["split"], r["k"], *[round(v, 5) for v in r["box"]], r.get("p_glove", "")])


# ---------------------------------------------------------------------------------------------------------------
# Ứng viên cần Claude xem. Mỗi ứng viên: một hộp đích (target) và các hộp gợi ý (sugg) đánh số 1..k trên bảng ảnh.
# Bảng ảnh không ghi nguồn đề xuất, điểm mô hình hay p của bộ phân loại (lượt Claude xem mù với các lượt máy).
# Nhiệm vụ (task) và mã quyết định:
#   *_add    (găng, ủng, kính thiếu nhãn):   g = đúng vật đó, dùng hộp đích; n = không phải; u = không rõ
#   *_check  (hộp có sẵn, kiểm tra hình học): k = giữ; s1, s1+s2 = thay bằng gợi ý; n = không phải vật đó (bỏ hộp);
#                                             u = không rõ / không vẽ được hộp đúng
#   shoes_cls (giày SH17):  b = ủng / giày bảo hộ nhìn rõ; o = giày thường, dép, chân trần; u = không rõ
#   glasses_cls (kính SH17): g = kính bảo hộ đang đeo; o = kính thường / kính râm đang đeo; x = không đeo; u = không rõ
CODES = {"add": {"g", "n", "u"}, "check": {"k", "n", "u"}, "shoes_cls": {"b", "o", "u"}, "glasses_cls": {"g", "o", "x", "u"}}
ITEM_COLS = ["item", "task", "set", "file", "img", "target", "sugg", "meta"]


def kind_of(task):
    for k in ("shoes_cls", "glasses_cls"):
        if task.startswith(k):
            return k
    return "add" if task.endswith("_add") else "check"


def scene_clean_eval():
    """{file: tập} ảnh dùng đánh giá kính, ủng: val_new, test_new + ảnh SH17, Construction-PPE của ppe4 val, test có cảnh
    không có ảnh train nào và không thuộc cảnh đánh giá của tập kia (như 03y)."""
    stats = rd(ROOT / "data" / "ppe4" / "stats.csv")
    scene = {r["file"]: r["scene_id"] for r in rd(ROOT / "data" / "ppe6" / "scene" / "scene_ids.csv")}
    roles = {r["scene_id"]: r["role"] for r in rd(ROOT / "data" / "ppe6" / "eval" / "scene_roles.csv")}
    train_sc = {scene.get(r["file"]) for r in stats if r["split"] == "train" and scene.get(r["file"]) not in roles}
    out = {}
    for s in ("val_new", "test_new"):
        for f in (P6 / f"{s}.txt").read_text(encoding="utf-8").split():
            out[Path(f).name] = s
    for r in stats:
        s, sc = r["split"], scene.get(r["file"])
        if s not in ("val", "test") or r["source"] not in ("sh17", "construction_ppe") or sc is None or r["file"] in out:
            continue
        other = "test_new" if s == "val" else "val_new"
        if sc not in train_sc and roles.get(sc) != other:
            out[r["file"]] = s
    return out


def raw_cppe_rows(raw_image):
    """Nhãn gốc Construction-PPE bản cũ: [(tên lớp, hộp chuẩn hóa)]."""
    names = yaml.safe_load((ROOT / "data" / "raw" / "construction_ppe" / "data.yaml").read_text(encoding="utf-8"))["names"]
    lab = ROOT / raw_image.replace("/images/", "/labels/").rsplit(".", 1)[0]
    return [(names[c], b) for c, b in yolo_rows(str(lab) + ".txt")]


def cluster(props, thr):
    """props: [(ưu tiên, hộp, nguồn, điểm)]; gộp đề xuất trùng (IoU >= thr), giữ hộp ưu tiên cao nhất (số nhỏ)."""
    keep = []
    for p in sorted(props, key=lambda x: (x[0], -x[3])):
        for k in keep:
            if iou(p[1], k["box"]) >= thr:
                k["src"].append(f"{p[2]}:{p[3]}")
                break
        else:
            keep.append(dict(box=p[1], src=[f"{p[2]}:{p[3]}"]))
    return keep


def fmt(b):
    return " ".join(f"{v:.5f}" for v in b)


def candidates_chvg(c, d):
    """Kính thiếu nhãn trên ảnh CHVG: đề xuất OWLv2 (câu hỏi kính) không trùng hộp kính đã có (IoU < new_iou). Mã c....."""
    owl = json.loads((d / "owl_eval.json").read_text(encoding="utf-8"))
    items = []
    for f, (s, p, lab) in chvg_images().items():
        if f not in owl:
            sys.exit(f"Chưa chạy OWLv2 cho {f} (03z owl --chvg)")
        gt = [b for k, b in yolo_rows(lab) if k == 4]
        props = [(1, b, "owl", sc) for k, sc, b in owl[f]["pred"] if k == "goggles" and sc >= c["owl_score"]]
        props = [x for x in props if all(iou(x[1], g) < c["new_iou"] for g in gt)]
        for k in cluster(props, c["new_iou"]):
            items.append(dict(task="goggles_chvg_add", set=s, file=f, img=p.relative_to(ROOT).as_posix(), target=fmt(k["box"]),
                              sugg="[]", meta=json.dumps(dict(src=k["src"]))))
    rng = random.Random(cfg()["seed"] + 2)
    rng.shuffle(items)
    for i, it in enumerate(items):
        it["item"] = f"c{i:05d}"
    with open(d / "review_items_chvg.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ITEM_COLS)
        w.writeheader()
        w.writerows(items)
    print(Counter((it["task"], it["set"]) for it in items))


def cmd_candidates(args):
    """Tạo review_items_<part>.csv: mọi ứng viên cho Claude xem (mục 2B kế hoạch). part = train (cần c4_train_pred,
    sh17_hands) hoặc eval (cần thêm owl_eval, c4_eval_pred). Mã item: t..... (train), e..... (eval)."""
    c = cfg()["propose"]
    d = out_dir()
    stats = rd(ROOT / "data" / "ppe4" / "stats.csv")
    raw_of = {r["file"]: r["image"] for r in stats}
    if args.part == "chvg":
        return candidates_chvg(c, d)
    if args.part == "sh17boots":
        return candidates_sh17boots(c, d)
    ev_part = args.part == "eval"
    owl = json.loads((d / "owl_eval.json").read_text(encoding="utf-8")) if ev_part else {}
    c4e = json.loads((d / "c4_eval_pred.json").read_text(encoding="utf-8")) if ev_part else {}
    c4t = {} if ev_part else json.loads((d / "c4_train_pred.json").read_text(encoding="utf-8"))
    hands = defaultdict(list)
    for r in rd(d / "sh17_hands.csv"):
        if r["p_glove"] and float(r["p_glove"]) >= c["hand_p"]:
            hands[r["file"]].append(([float(r[k]) for k in ("x0", "y0", "x1", "y1")], float(r["p_glove"])))
    items = []

    def add(task, s, f, img, target, sugg=(), meta=None):
        items.append(dict(task=task, set=s, file=f, img=Path(img).relative_to(ROOT).as_posix(), target=fmt(target) if target else "",
                          sugg=json.dumps([[round(v, 5) for v in b] for b in sugg]), meta=json.dumps(meta or {})))

    # Găng thiếu nhãn, ảnh đánh giá: OWLv2 + C4 + hộp hands SH17 (bộ phân loại tay), ưu tiên hình học hands > OWLv2 > C4
    ev = eval_images()
    for f, (s, p, lab) in (ev.items() if ev_part else []):
        gt = [b for k, b in yolo_rows(lab) if k == 3]
        props = [(0, b, "hands", pg) for b, pg in hands.get(f, [])]
        props += [(1, b, "owl", sc) for k, sc, b in owl.get(f, {}).get("pred", []) if k == "gloves" and sc >= c["owl_score"]]
        props += [(2, b, "c4", sc) for k, sc, b in c4e.get(f, []) if k == 3 and sc >= c["c4_conf"]]
        props = [x for x in props if all(iou(x[1], g) < c["new_iou"] for g in gt)]
        for k in cluster(props, c["new_iou"]):
            add("gloves_eval_add", s, f, p, k["box"], meta=dict(src=k["src"]))
    # Găng thiếu nhãn, train: C4 + hands SH17
    train_imgs = [] if ev_part else sorted((C2 / "images" / "train").iterdir()) + sorted(EXTRA.glob("images/train/cppe2__*"))
    for p in train_imgs:
        lab = p.parent.parent.parent / "labels" / "train" / (p.stem + ".txt")
        gt = [b for k, b in yolo_rows(lab) if k == 3]
        props = [(0, b, "hands", pg) for b, pg in hands.get(p.name, [])]
        props += [(2, b, "c4", sc) for k, sc, b in c4t.get(p.name, []) if k == 3 and sc >= c["c4_conf"]]
        props = [x for x in props if all(iou(x[1], g) < c["new_iou"] for g in gt)]
        for k in cluster(props, c["new_iou"]):
            add("gloves_train_add", "train", p.name, p, k["box"], meta=dict(src=k["src"]))

    # Ảnh đánh giá kính, ủng (bước F)
    clean = scene_clean_eval() if ev_part else {}
    for f, s in sorted(clean.items()):
        sset, p, lab = ev[f]
        src = f.split("__")[0]
        in_new = s in ("val_new", "test_new")
        owl_b = [b for k, sc, b in owl.get(f, {}).get("pred", []) if k == "boots" and sc >= c["owl_score"]]
        owl_g = [b for k, sc, b in owl.get(f, {}).get("pred", []) if k == "goggles" and sc >= c["owl_score"]]
        if in_new:
            draft = P6 / "labels" / f"{s}_draft" / (Path(f).stem + ".txt")
            gt5 = [b for k, b in yolo_rows(draft) if k == 5]
            gt4 = [b for k, b in yolo_rows(draft) if k == 4]
        elif src == "construction_ppe":
            rows = raw_cppe_rows(raw_of[f])
            gt5 = [b for n, b in rows if n == "boots"]
            gt4 = [b for n, b in rows if n == "goggles"]
        else:
            gt5 = gt4 = []
        if src == "construction_ppe":
            # mọi hộp ủng, kính có sẵn: kiểm hình học, gợi ý chỉ từ OWLv2 (không dùng C4 để nhãn đánh giá không nghiêng về C4)
            for t, gts, sug in (("boots_eval_check", gt5, owl_b), ("goggles_eval_check", gt4, owl_g)):
                for g in gts:
                    near = [b for b in sug if ioa(b, [g[0] - (g[2] - g[0]), g[1] - (g[3] - g[1]), g[2] + (g[2] - g[0]), g[3] + (g[3] - g[1])]) > 0.5]
                    add(t, s, f, p, g, near[:4], dict(in_new=in_new))
            for t, gts, sug in (("boots_eval_add", gt5, owl_b), ("goggles_eval_add", gt4, owl_g)):
                for k in cluster([(1, b, "owl", 0) for b in sug if all(iou(b, g) < c["new_iou"] for g in gts)], c["new_iou"]):
                    add(t, s, f, p, k["box"], meta=dict(src=k["src"]))
        elif not in_new:
            obj = sh17_objects(raw_of[f])
            shoes = obj.get("shoes", [])
            feet = [b for b in obj.get("foot", []) if all(iou(b, q) < 0.5 for q in shoes)]
            for b in shoes + feet:
                add("shoes_cls", s, f, p, b)
            for b in obj.get("glasses", []):
                add("glasses_cls", s, f, p, b)

    # Hộp ủng train của Construction-PPE (C2 và bản mới): không khớp dự đoán C4 (IoU >= 0,5) hoặc hộp rộng (có thể cả đôi)
    for p in [q for q in train_imgs if q.name.startswith(("construction_ppe__", "cppe2__"))]:
        lab = p.parent.parent.parent / "labels" / "train" / (p.stem + ".txt")
        pr = [b for k, sc, b in c4t.get(p.name, []) if k == 5 and sc >= c["c4_conf"]]
        for k, g in yolo_rows(lab):
            if k != 5:
                continue
            wide = (g[2] - g[0]) > 1.3 * (g[3] - g[1])
            if wide or not any(iou(g, b) >= 0.5 for b in pr):
                near = [b for b in pr if ioa(b, [g[0] - (g[2] - g[0]), g[1] - (g[3] - g[1]), g[2] + (g[2] - g[0]), g[3] + (g[3] - g[1])]) > 0.5]
                add("boots_train_check", "train", p.name, p, g, near[:4], dict(wide=wide))

    rng = random.Random(cfg()["seed"])
    rng.shuffle(items)
    for i, it in enumerate(items):
        it["item"] = f"{args.part[0]}{i:05d}"
    with open(d / f"review_items_{args.part}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ITEM_COLS)
        w.writeheader()
        w.writerows(sorted(items, key=lambda x: x["item"]))
    print(Counter((it["task"], it["set"]) for it in items))


COLORS = [(0, 200, 0), (255, 140, 0), (255, 0, 255), (0, 220, 255)]   # gợi ý 1..4 (BGR)


def tile(im, target, sugg, T, ctx):
    H, W = im.shape[:2]
    bs = [b for b in [target] + list(sugg) if b]
    x0, y0 = min(b[0] for b in bs) * W, min(b[1] for b in bs) * H
    x1, y1 = max(b[2] for b in bs) * W, max(b[3] for b in bs) * H
    side = max(x1 - x0, y1 - y0, 24) * ctx
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a, b_ = int(max(cx - side / 2, 0)), int(max(cy - side / 2, 0))
    crop = im[b_:int(min(cy + side / 2, H)), a:int(min(cx + side / 2, W))].copy()
    f = T / max(crop.shape[:2])
    crop = cv2.resize(crop, (max(1, round(crop.shape[1] * f)), max(1, round(crop.shape[0] * f))),
                      interpolation=cv2.INTER_AREA if f < 1 else cv2.INTER_CUBIC)
    def pt(x, y):
        return int((x * W - a) * f), int((y * H - b_) * f)
    for j, s in enumerate(sugg):
        cv2.rectangle(crop, pt(s[0], s[1]), pt(s[2], s[3]), COLORS[j % 4], 1)
        cv2.putText(crop, str(j + 1), pt(s[2], s[1])[0:1] + (pt(s[2], s[1])[1] + 10,), 0, 0.35, COLORS[j % 4], 1)
    if target:
        cv2.rectangle(crop, pt(target[0], target[1]), pt(target[2], target[3]), (0, 0, 255), 1)
    return crop


def all_items(d):
    return {r["item"]: r for p in sorted(d.glob("review_items_*.csv")) for r in rd(p)}


def cmd_sheets(args):
    """Bảng ảnh cho một nhiệm vụ: review/<task>_<số>.jpg và .txt (ô -> item). Ô: ảnh cắt có ngữ cảnh, hộp đích đỏ,
    gợi ý màu đánh số. Không ghi nguồn, điểm. Thứ tự theo mã item (đã xáo trộn ngẫu nhiên, seed cố định)."""
    d = out_dir()
    rv = d / "review"
    rv.mkdir(exist_ok=True)
    items = [r for r in all_items(d).values() if r["task"] == args.task]
    T, ncol, nrow = args.tile, args.cols, args.rows
    per = ncol * nrow
    cache = {}
    for s0 in range(0, len(items), per):
        sheet = np.full((nrow * (T + 16), ncol * T + (ncol - 1) * 4, 3), 255, np.uint8)
        part = items[s0:s0 + per]
        for k, it in enumerate(part):
            if it["img"] not in cache:
                cache.clear()
                cache[it["img"]] = imread(ROOT / it["img"])
            tgt = [float(v) for v in it["target"].split()] if it["target"] else None
            t = tile(cache[it["img"]], tgt, json.loads(it["sugg"]), T, args.ctx)
            r_, c_ = divmod(k, ncol)
            y, x = r_ * (T + 16) + 16, c_ * (T + 4)
            sheet[y:y + t.shape[0], x:x + t.shape[1]] = t
            cv2.putText(sheet, str(k), (x + 2, y - 3), 0, 0.45, (0, 0, 200), 1)
        n = s0 // per
        cv2.imwrite(str(rv / f"{args.task}_{n:03d}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
        (rv / f"{args.task}_{n:03d}.txt").write_text("\n".join(f"{k} {it['item']}" for k, it in enumerate(part)), encoding="utf-8")
    print(args.task, len(items), "ô,", (len(items) + per - 1) // per, "bảng")


def cmd_collect(args):
    """Đọc review/<task>_<số>.dec (Claude viết: dòng đầu `default=<mã>`, sau đó `<ô> <mã>`), kiểm đủ ô, mã hợp lệ;
    ghi machine_pass_claude.csv (labeler machine_pass_claude, nhãn máy)."""
    d = out_dir()
    rv = d / "review"
    items = all_items(d)
    out, bad = [], []
    for txt in sorted(rv.glob("*.txt")):
        dec = txt.with_suffix(".dec")
        if not dec.exists():
            continue
        cells = dict(line.split() for line in txt.read_text(encoding="utf-8").splitlines())
        lines = [x.strip() for x in dec.read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]
        default = lines[0].split("=", 1)[1] if lines and lines[0].startswith("default=") else None
        got = {}
        for x in lines[1 if default else 0:]:
            k, v = x.split(None, 1)
            got[k] = v.strip()
        for k in got:
            if k not in cells:
                bad.append(f"{dec.name}: ô lạ {k}")
        for k, it in cells.items():
            v = got.get(k, default)
            task = items[it]["task"]
            kind = kind_of(task)
            ok = v in CODES[kind] or (kind == "check" and v and all(s.startswith("s") and s[1:].isdigit() and
                                                                     int(s[1:]) <= len(json.loads(items[it]["sugg"])) for s in v.split("+")))
            if not ok:
                bad.append(f"{dec.name}: ô {k} mã '{v}' không hợp lệ cho {task}")
            out.append(dict(labeler="machine_pass_claude", item=it, task=task, decision=v, sheet=txt.stem, cell=k))
    if bad:
        sys.exit("\n".join(bad))
    with open(d / "machine_pass_claude.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["labeler", "item", "task", "decision", "sheet", "cell"])
        w.writeheader()
        w.writerows(out)
    print(Counter((r["task"], r["decision"]) for r in out))


FILL = (114, 114, 114)   # màu che, như dataset_c2 và c4_extra


def decisions(d):
    """{item: quyết định} của machine_pass_claude.csv và {item: dòng item}."""
    return {r["item"]: r["decision"] for r in rd(d / "machine_pass_claude.csv")}, all_items(d)


RECHECK = ("boots_eval_recheck", "gloves_train_recheck")


def rechecks(dec, items):
    """Lượt xem lại sau kiểm định lần 1 (kế hoạch mục "Kiểm định của người lần 1"): {item gốc: [(hộp, quyết định)]}.
    Tiêu chí chặt: hộp phải bao sát đúng MỘT chiếc găng / ủng bảo hộ (k), không thì n / u."""
    out = defaultdict(list)
    for it in items.values():
        if it["task"] in RECHECK and it["item"] in dec:
            out[json.loads(it["meta"])["orig"]].append(([float(x) for x in it["target"].split()], dec[it["item"]]))
    return out


def apply_train(rows, its, dec, rc=None):
    """rows: [(lớp, hộp)] nhãn gốc của một ảnh; its: các item train của ảnh. Trả về (rows mới, vùng che, log).
    rc: kết quả xem lại; găng thêm mà lượt xem lại không giữ (k) thì che xám thay vì thành nhãn."""
    rows = [list(r) for r in rows]
    masks, log = [], []
    rc = rc or {}
    for it in its:
        v = dec.get(it["item"])
        if v is None or it["task"] in RECHECK:
            continue
        t = [float(x) for x in it["target"].split()]
        if it["task"] == "gloves_train_add":
            if v == "g" and it["item"] in rc and rc[it["item"]][0][1] != "k":
                v = "g>" + rc[it["item"]][0][1]   # găng có thật nhưng hộp không đạt tiêu chí chặt: che
                masks.append(t)
            elif v == "g":
                rows.append([3, t])
            elif v == "u":
                masks.append(t)
            if v[0] in ("g", "u"):
                log.append((it["item"], it["task"], v, fmt(t), fmt(t) if v == "g" else ""))
        elif it["task"] == "boots_train_check" and v != "k":
            hit = [r for r in rows if r[0] == 5 and iou(r[1], t) > 0.999]
            if not hit:
                sys.exit(f"Không thấy hộp ủng của {it['item']} trong nhãn")
            rows.remove(hit[0])
            new = []
            if v.startswith("s"):
                sug = json.loads(it["sugg"])
                new = [sug[int(s[1:]) - 1] for s in v.split("+")]
                rows += [[5, b] for b in new]
            elif v == "u":
                masks.append(t)
            log.append((it["item"], it["task"], v, fmt(t), ";".join(fmt(b) for b in new)))
    return rows, masks, log


def write_yolo(path, rows):
    out = []
    for c, b in rows:
        b = [min(max(v, 0.0), 1.0) for v in b]
        out.append(f"{c} {(b[0] + b[2]) / 2:.6f} {(b[1] + b[3]) / 2:.6f} {b[2] - b[0]:.6f} {b[3] - b[1]:.6f}")
    Path(path).write_text("".join(x + "\n" for x in out), encoding="utf-8")


MAX_SIDE = 2048   # ảnh che mới thu về cạnh dài này (train ở imgsz <= 1280, nên không mất thông tin dùng được)


def mask_image(src, masks):
    im = imread(src)
    h, w = im.shape[:2]
    for b in masks:
        im[max(int(b[1] * h), 0):int(np.ceil(b[3] * h)), max(int(b[0] * w), 0):int(np.ceil(b[2] * w))] = FILL
    if max(h, w) > MAX_SIDE:
        f = MAX_SIDE / max(h, w)
        im = cv2.resize(im, (round(w * f), round(h * f)), interpolation=cv2.INTER_AREA)
    return im


def link_or_copy(src, dst):
    try:
        os.link(src, dst)
    except OSError:
        import shutil
        shutil.copy2(src, dst)


def cmd_build_train(args):
    """Bộ train C5 = train C2 + sửa của Claude (găng thêm / che; ủng thay / bỏ / che), ghi c5.out/dataset_c5 và
    changes_train.csv; gói Kaggle cùng định dạng 03m (manifest.tsv, labels, masked, ready.json) ở
    data/ppe6/variants/kaggle/c5_pack.zip. Ảnh Construction-PPE bản mới (bộ phụ) xử lý ở build-extra."""
    import shutil
    import zipfile

    d = out_dir()
    dec, items = decisions(d)
    by_file = defaultdict(list)
    for it in items.values():
        if it["set"] == "train":
            by_file[it["file"]].append(it)
    out = d / "dataset_c5"
    if out.exists():
        shutil.rmtree(out)
    for k in ("images", "labels"):
        for part in ("train", "val_monitor"):
            (out / k / part).mkdir(parents=True)
    log, new_masked = [], set()
    for p in sorted((C2 / "images" / "train").iterdir()):
        rows, masks, lg = apply_train(yolo_rows(C2 / "labels" / "train" / (p.stem + ".txt")), by_file.get(p.name, []), dec, rechecks(dec, items))
        log += [(p.name, *x) for x in lg]
        write_yolo(out / "labels" / "train" / (p.stem + ".txt"), rows)
        if masks:
            cv2.imwrite(str(out / "images" / "train" / (p.stem + ".jpg")), mask_image(p, masks), [cv2.IMWRITE_JPEG_QUALITY, 92])
            new_masked.add(p.name)
        else:
            link_or_copy(p, out / "images" / "train" / p.name)
    for p in sorted((C2 / "images" / "val_monitor").iterdir()):
        link_or_copy(p, out / "images" / "val_monitor" / p.name)
        shutil.copy2(C2 / "labels" / "val_monitor" / (p.stem + ".txt"), out / "labels" / "val_monitor" / (p.stem + ".txt"))
    (out / "data.yaml").write_text((C2 / "data.yaml").read_text(encoding="utf-8").replace("Train c2", "Train c5 (C2 + sửa nhãn 03z)"), encoding="utf-8")
    with open(d / "changes_train.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "item", "task", "decision", "old_box", "new_box"])
        w.writerows(log)
    # Gói Kaggle: như c2_final_pack.zip, nhãn mới; ảnh có vùng che mới vào masked/
    src_pack = ROOT / "data" / "ppe6" / "variants" / "kaggle" / "c2_final_pack.zip"
    dst_pack = ROOT / "data" / "ppe6" / "variants" / "kaggle" / "c5_pack.zip"
    with zipfile.ZipFile(src_pack) as zin:
        man = zin.read("manifest.tsv").decode("utf-8").splitlines()
        ready = json.loads(zin.read("ready.json"))
        old_masked = {n.split("/", 1)[1] for n in zin.namelist() if n.startswith("masked/")}
    rows_m = []
    for line in man:
        part, split, f, how = line.split("\t")
        if part == "train" and f in new_masked:
            how = "masked"
        rows_m.append("\t".join((part, split, f, how)))
    ready.update(variant="c5", base="c2_final_pack + 03z", note="nhãn máy (machine_pass_claude), chưa người kiểm định")
    with zipfile.ZipFile(dst_pack, "w", zipfile.ZIP_STORED) as z:
        z.writestr("manifest.tsv", "\n".join(rows_m) + "\n")
        z.writestr("ready.json", json.dumps(ready, ensure_ascii=False, indent=1))
        z.write(out / "data.yaml", "data.yaml")
        for p in sorted((out / "labels").rglob("*.txt")):
            z.write(p, p.relative_to(out).as_posix())
        for line in rows_m:
            part, split, f, how = line.split("\t")
            if part == "train" and how == "masked":
                z.write(out / "images" / "train" / (Path(f).stem + ".jpg"), f"masked/{Path(f).stem}.jpg")
    print(Counter((x[2], x[3]) for x in log), "ảnh che mới", len(new_masked), "(C2 đã che", len(old_masked), ")",
          f"| gói {dst_pack.name} {dst_pack.stat().st_size / 1e6:.1f} MB")


def cmd_build_extra(args):
    """Bộ phụ C5: chạy trước `python scripts/03b_make_extra_train.py --dataset data/ppe6/c5/dataset_c5 --out
    data/ppe6/c5/c5_extra` (ảnh cắt, thu nhỏ, oversample từ train đã sửa), rồi lệnh này thêm ảnh Construction-PPE bản
    mới của c4_extra với nhãn đã sửa, ghi changes_extra.csv và gói data/ppe6/variants/kaggle/c5_extra_pack.zip."""
    import shutil
    import zipfile

    d = out_dir()
    dec, items = decisions(d)
    by_file = defaultdict(list)
    for it in items.values():
        if it["set"] == "train":
            by_file[it["file"]].append(it)
    out = d / "c5_extra"
    if not (out / "oversample.txt").exists():
        sys.exit("Chạy 03b trước (xem docstring)")
    log = []
    for p in sorted(EXTRA.glob("images/train/cppe2__*")):
        rows, masks, lg = apply_train(yolo_rows(EXTRA / "labels" / "train" / (p.stem + ".txt")), by_file.get(p.name, []), dec, rechecks(dec, items))
        log += [(p.name, *x) for x in lg]
        write_yolo(out / "labels" / "train" / (p.stem + ".txt"), rows)
        if masks:
            cv2.imwrite(str(out / "images" / "train" / p.name), mask_image(p, masks), [cv2.IMWRITE_JPEG_QUALITY, 92])
        else:
            shutil.copy2(p, out / "images" / "train" / p.name)
    summ = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    summ["cppe2"] = dict(json.loads((EXTRA / "summary.json").read_text(encoding="utf-8"))["cppe2"], c5_changes=dict(Counter(f"{x[2]}:{x[3]}" for x in log)))
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(d / "changes_extra.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "item", "task", "decision", "old_box", "new_box"])
        w.writerows(log)
    pack = ROOT / "data" / "ppe6" / "variants" / "kaggle" / "c5_extra_pack.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, "c5_extra/" + p.relative_to(out).as_posix())
    print(Counter((x[2], x[3]) for x in log), f"| gói {pack.name} {pack.stat().st_size / 1e6:.1f} MB")


PART_OF_TASK = {"gloves_eval_add": "gloves", "shoes_cls": "boots", "boots_eval_add": "boots", "glasses_cls": "goggles",
                "goggles_eval_add": "goggles", "goggles_chvg_add": "goggles", "shoes_cls_train": "boots", "gloves8_eval_add": "gloves"}


def part_probs(items):
    """Lượt máy thứ hai cho val, test: bộ phân loại bộ phận (c5_relabel.propose.hands_weights, bản 4 có tay, chân, mắt)
    trên ảnh cắt vuông quanh hộp đích (cạnh dài * context, như ảnh cắt theo hộp của val 03y). {item: p có PPE}."""
    from ultralytics import YOLO
    sys.path.insert(0, str(ROOT / "src"))
    from ppe.parts import ppe_prob

    c = cfg()["propose"]
    model = YOLO(str(ROOT / c["hands_weights"]))
    todo = [it for it in items if it["task"] in PART_OF_TASK]
    out, cache = {}, {}
    for i in range(0, len(todo), 64):
        crops, ids = [], []
        for it in todo[i:i + 64]:
            if it["img"] not in cache:
                cache.clear()
                cache[it["img"]] = imread(ROOT / it["img"])
            im = cache[it["img"]]
            H, W = im.shape[:2]
            t = [float(x) for x in it["target"].split()]
            side = max((t[2] - t[0]) * W, (t[3] - t[1]) * H) * c["context"]
            cx, cy = (t[0] + t[2]) / 2 * W, (t[1] + t[3]) / 2 * H
            crop = im[int(max(cy - side / 2, 0)):int(min(cy + side / 2, H)), int(max(cx - side / 2, 0)):int(min(cx + side / 2, W))]
            if crop.size:
                crops.append(crop.copy())
                ids.append(it)
        for it, r in zip(ids, model.predict(crops, imgsz=160, device=0, verbose=False) if crops else []):
            out[it["item"]] = round(ppe_prob(r.probs.data.cpu().numpy(), model.names, PART_OF_TASK[it["task"]]), 4)
    return out


def merge_eval(it, v, p):
    """Gộp lượt Claude (v) và lượt bộ phân loại (p) cho một item đánh giá. Trả về (hành động, hộp, trạng thái):
    hành động: add (thêm nhãn), keep, replace, ignore (vùng bỏ qua), none (không có gì).
    Luật CLAUDE.md: hai lượt khác nhau, hoặc Claude không rõ -> không dùng làm nhãn val, test, thành vùng ignore."""
    kind = kind_of(it["task"])
    t = [float(x) for x in it["target"].split()]
    if kind == "check":   # lượt 1 = nhãn gốc (người của bộ gốc / người chốt), lượt 2 = Claude, gợi ý hình học = OWLv2
        if v == "k":
            return "keep", [t], "machine_consensus"
        if v.startswith("s"):
            sug = json.loads(it["sugg"])
            return "replace", [sug[int(s[1:]) - 1] for s in v.split("+")], "machine_consensus"
        return "ignore", [t], "machine_labeled"
    pos = {"add": "g", "shoes_cls": "b", "glasses_cls": "g"}[kind]
    if v == "u" or p is None:
        return "ignore", [t], "machine_labeled"
    if v == pos:
        return ("add", [t], "machine_consensus") if p >= 0.5 else ("ignore", [t], "machine_labeled")
    return ("none", [t], "machine_consensus") if p < 0.5 else ("ignore", [t], "machine_labeled")


def cmd_build_eval(args):
    """Val, test đã sửa ở c5.out/eval/{val,test}: ảnh (liên kết), nhãn 6 lớp, ignore.csv, files.json, changes_eval.csv,
    data.yaml. Lớp 0-3: nhãn ppe4 (ảnh từ ppe4 train của cảnh đánh giá: bản _draft) + găng đã sửa. Lớp 4, 5: chỉ ảnh
    `scene_clean_eval` (files.json mục new_class_files); val_new, test_new giữ nhãn người chốt và ignore.csv cũ, cộng sửa."""
    import shutil

    d = out_dir()
    dec, items = decisions(d)
    rc = rechecks(dec, items)
    ev_items = [it for it in items.values() if it["set"] != "train" and it["item"] in dec and it["task"] not in RECHECK]
    missing = [it["item"] for it in items.values() if it["set"] != "train" and it["item"] not in dec]
    if missing:
        sys.exit(f"Còn {len(missing)} item đánh giá chưa có quyết định của Claude")
    probs = part_probs(ev_items)
    ev = eval_images()
    clean = scene_clean_eval()
    split_of = {"val": "val", "val_new": "val", "test": "test", "test_new": "test"}
    old_ign = defaultdict(list)
    for r in rd(P6 / "ignore.csv"):
        old_ign[r["file"]].append(r)
    by_file = defaultdict(list)
    for it in ev_items:
        by_file[it["file"]].append(it)
    stats = rd(ROOT / "data" / "ppe4" / "stats.csv")
    raw_of = {r["file"]: r["image"] for r in stats}
    root = d / "eval"
    if root.exists():
        shutil.rmtree(root)
    log, ign_rows = [], []
    files = {"val": dict(all=[], new_class_files=[]), "test": dict(all=[], new_class_files=[])}
    for f, (s, p, lab) in sorted(ev.items()):
        sp = split_of[s]
        (root / sp / "images").mkdir(parents=True, exist_ok=True)
        (root / sp / "labels").mkdir(parents=True, exist_ok=True)
        link_or_copy(p, root / sp / "images" / p.name)
        files[sp]["all"].append(f)
        rows = [[c, b] for c, b in yolo_rows(lab) if c <= 3]
        ign = []
        cset = clean.get(f)
        if cset:
            files[sp]["new_class_files"].append(f)
            if cset in ("val_new", "test_new"):
                draft = P6 / "labels" / f"{cset}_draft" / (Path(f).stem + ".txt")
                rows += [[c, b] for c, b in yolo_rows(draft) if c in (4, 5)]
                for r in old_ign.get(f, []):
                    cx, cy, w, h = (float(r[k]) for k in ("cx", "cy", "w", "h"))
                    ign.append((int(r["cls"]), [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], f"cu_{r['label']}"))
            elif f.startswith("construction_ppe__"):
                for n, b in raw_cppe_rows(raw_of[f]):
                    if n in ("boots", "goggles"):
                        rows.append([5 if n == "boots" else 4, b])
        for it in by_file.get(f, []):
            v = dec[it["item"]]
            act, boxes, status = merge_eval(it, v, probs.get(it["item"]))
            cls = {"gloves": 3, "boots": 5, "goggles": 4}[PART_OF_TASK.get(it["task"]) or it["task"].split("_")[0]]
            t = [float(x) for x in it["target"].split()]
            # Sau kiểm định lần 1 (găng không đạt, lỗi hệ thống hình học hộp): hộp găng máy thêm ở val, test thành ignore.
            if it["task"] == "gloves_eval_add" and act == "add":
                act, status, v = "ignore", "machine_labeled", v + ">audit1_fail"
            # Ủng: hộp giữ / nắn / thêm mà lượt xem lại chặt không giữ (k) thì thành ignore.
            if cls == 5 and act in ("keep", "replace", "add") and it["item"] in rc:
                bad = [b for b, x in rc[it["item"]] if x != "k"]
                if bad:
                    if act == "keep":
                        act = "replace"   # bỏ hộp gốc
                    boxes = [b for b, x in rc[it["item"]] if x == "k"]
                    v = v + ">recheck"
                    for b in bad:
                        ign.append((cls, b, f"{it['task']}:{v}"))
            if act in ("replace", "ignore") and kind_of(it["task"]) == "check":
                hit = [r for r in rows if r[0] == cls and iou(r[1], t) > 0.999]
                if hit:
                    rows.remove(hit[0])
            if act in ("add", "replace"):
                rows += [[cls, b] for b in boxes]
            if act == "ignore":
                ign.append((cls, t, f"{it['task']}:{v}:p={probs.get(it['item'])}"))
            if act != "none" and not (act == "keep"):
                log.append((sp, f, it["item"], it["task"], v, probs.get(it["item"], ""), act, status, fmt(t), ";".join(fmt(b) for b in boxes)))
        write_yolo(root / sp / "labels" / (Path(f).stem + ".txt"), rows)
        for c, b, why in ign:
            ign_rows.append([sp, f, c, why, f"{(b[0] + b[2]) / 2:.6f}", f"{(b[1] + b[3]) / 2:.6f}", f"{b[2] - b[0]:.6f}", f"{b[3] - b[1]:.6f}"])
        (root / sp / "data.yaml").write_text(
            f"# Val/test C5 đã sửa nhãn (03z build-eval), nhãn máy, chưa người kiểm định\npath: {(root / sp).as_posix()}\n"
            f"train: images\nval: images\ntest: images\nnames:\n" + "".join(f"  {k}: {v}\n" for k, v in CLASSES.items()), encoding="utf-8")
    # Ảnh CHVG: chỉ dùng cho kính (04j tập con chvg). Nhãn = hộp kính người chốt + kính thêm (hai lượt đồng ý); khác
    # nhau / không rõ thành ignore; vùng unclear cũ (ignore.csv của 03i) giữ.
    for f, (s, p, lab) in sorted(chvg_images().items()):
        sp = s.split("_")[1]
        link_or_copy(p, root / sp / "images" / p.name)
        files[sp].setdefault("chvg_files", []).append(f)
        rows = [[c, b] for c, b in yolo_rows(lab) if c == 4]
        ign = []
        for r in old_ign.get(f, []):
            cx, cy, w, h = (float(r[k]) for k in ("cx", "cy", "w", "h"))
            ign.append((int(r["cls"]), [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], f"cu_{r['label']}"))
        for it in by_file.get(f, []):
            v = dec[it["item"]]
            act, boxes, status = merge_eval(it, v, probs.get(it["item"]))
            t = [float(x) for x in it["target"].split()]
            if act == "add":
                rows += [[4, b] for b in boxes]
            elif act == "ignore":
                ign.append((4, t, f"{it['task']}:{v}:p={probs.get(it['item'])}"))
            if act in ("add", "ignore"):
                log.append((sp, f, it["item"], it["task"], v, probs.get(it["item"], ""), act, status, fmt(t), ";".join(fmt(b) for b in boxes)))
        write_yolo(root / sp / "labels" / (Path(f).stem + ".txt"), rows)
        for c, b, why in ign:
            ign_rows.append([sp, f, c, why, f"{(b[0] + b[2]) / 2:.6f}", f"{(b[1] + b[3]) / 2:.6f}", f"{b[2] - b[0]:.6f}", f"{b[3] - b[1]:.6f}"])
    with open(root / "ignore.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["split", "file", "cls", "reason", "cx", "cy", "w", "h"])
        w.writerows(ign_rows)
    with open(d / "changes_eval.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["split", "file", "item", "task", "decision_claude", "p_part_cls", "action", "status", "target", "boxes"])
        w.writerows(log)
    (root / "files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    print(Counter((x[0], x[3], x[6]) for x in log))
    print({s: {k: len(v) for k, v in x.items()} for s, x in files.items()}, "ignore", Counter((r[0], r[2]) for r in ign_rows))


def cmd_recheck(args):
    """Tạo review_items_recheck.csv: mỗi hộp ủng cuối cùng (giữ / nắn / thêm) của val, test và mỗi hộp găng Claude đã thêm
    ở train, để Claude xem lại theo tiêu chí chặt (hộp bao sát đúng một chiếc găng / ủng bảo hộ). Mã item r....."""
    d = out_dir()
    dec, items = decisions(d)
    probs = part_probs([it for it in items.values() if it["set"] != "train" and it["task"] not in RECHECK])
    out = []
    for it in items.values():
        v = dec.get(it["item"])
        if it["task"] in RECHECK or v is None:
            continue
        if it["set"] == "train":
            if it["task"] == "gloves_train_add" and v == "g":
                out.append(dict(it, task="gloves_train_recheck", sugg="[]", meta=json.dumps(dict(orig=it["item"]))))
            continue
        cls = PART_OF_TASK.get(it["task"]) or it["task"].split("_")[0]
        if cls != "boots":
            continue
        act, boxes, _ = merge_eval(it, v, probs.get(it["item"]))
        if act in ("keep", "replace", "add"):
            for b in boxes:
                out.append(dict(it, task="boots_eval_recheck", target=fmt(b), sugg="[]", meta=json.dumps(dict(orig=it["item"]))))
    rng = random.Random(cfg()["seed"] + 1)
    rng.shuffle(out)
    for i, it in enumerate(out):
        it["item"] = f"r{i:05d}"
    with open(d / "review_items_recheck.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ITEM_COLS)
        w.writeheader()
        w.writerows(out)
    print(Counter(it["task"] for it in out))


AUDIT_Q = {
    "gloves": "Trong hộp đỏ có găng tay (đang đeo hoặc cầm) không?",
    "boots": "Hộp đỏ có khoanh đúng một chiếc ủng / giày bảo hộ nhìn rõ không? (giày thường, dép, hộp lệch hẳn = Sai)",
    "goggles": "Trong hộp đỏ có kính bảo hộ đang đeo không? (kính cận, kính râm = Sai)",
}


def cmd_audit(args):
    """Gói kiểm định của người (kế hoạch mục 2B, người dùng đồng ý 17/11/2026): mẫu phân tầng các item val, test có trạng
    thái machine_consensus, mỗi tầng (lớp, máy nói có / không) `--per` ô, seed c5_relabel.seed. Ghi audit/audit.html (một
    file, ảnh nhúng; người bấm Đúng / Sai / Không rõ, cuối trang tải về audit_results.json) và audit/_private/key.csv (đáp
    án máy, người kiểm định không mở). Trang không hiện quyết định máy, nguồn hay điểm."""
    import base64
    d = out_dir()
    dec, items = decisions(d)
    ev = [it for it in items.values() if it["set"] != "train" and it["task"] not in RECHECK]
    probs = part_probs(ev)
    rc = rechecks(dec, items)
    strata = defaultdict(list)
    for it in ev:
        act, boxes, status = merge_eval(it, dec[it["item"]], probs.get(it["item"]))
        if status != "machine_consensus":
            continue
        cls = PART_OF_TASK.get(it["task"]) or it["task"].split("_")[0]
        if args.only and cls not in args.only.split(","):
            continue
        if args.task and it["task"] != args.task:
            continue
        if it["task"] == "gloves_eval_add" and act == "add":
            continue   # sau kiểm định lần 1: hộp găng thêm ở val, test đã thành ignore
        if cls == "boots" and act in ("keep", "replace", "add") and it["item"] in rc:
            boxes = [b for b, x in rc[it["item"]] if x == "k"]   # chỉ hộp lượt xem lại giữ
        machine_yes = act in ("add", "keep", "replace")
        for b in boxes:
            strata[(cls, machine_yes)].append((it, b))
    rng = random.Random(cfg()["seed"])
    pick = []
    for k in sorted(strata):
        v = strata[k][:]
        rng.shuffle(v)
        pick += [(k, it, b) for it, b in v[:args.per]]
    rng.shuffle(pick)
    out = d / f"audit{args.tag}"
    (out / "_private").mkdir(parents=True, exist_ok=True)
    cells, key = [], []
    cache = {}
    for n, ((cls, yes), it, b) in enumerate(pick):
        if it["img"] not in cache:
            cache.clear()
            cache[it["img"]] = imread(ROOT / it["img"])
        im = cache[it["img"]]
        H, W = im.shape[:2]
        t = tile(im, b, [], 360, 3.0)
        ok, buf = cv2.imencode(".jpg", t, [cv2.IMWRITE_JPEG_QUALITY, 88])
        aid = f"a{n:03d}"
        cells.append(dict(id=aid, q=AUDIT_Q[cls], img="data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()))
        key.append(dict(audit_id=aid, item=it["item"], task=it["task"], set=it["set"], cls=cls, machine_yes=int(yes), box=fmt(b)))
    with open(out / "_private" / "key.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(key[0]))
        w.writeheader()
        w.writerows(key)
    html = (ROOT / "scripts" / "c5_audit_template.html").read_text(encoding="utf-8").replace("__CELLS__", json.dumps(cells)).replace("c5_audit_v1", f"c5_audit_v1{args.tag}")
    (out / "audit.html").write_text(html, encoding="utf-8")
    print(len(cells), "ô", Counter(f"{k[0]}:{'co' if k[1] else 'khong'}" for k, _, _ in pick), "|", out / "audit.html")


def cmd_audit_report(args):
    """Đọc audit/audit_results.json (người kiểm định tải về), so với _private/key.csv: bất đồng theo lớp và theo máy nói
    có / không, khoảng tin cậy Wilson; tiêu chí quy trình 07/11: < 10% và không lỗi hệ thống thì tầng đạt. Ghi audit/report.json."""
    sys.path.insert(0, str(ROOT / "src"))
    from ppe.ppe6_data import wilson

    d = out_dir() / f"audit{args.tag}"
    res = json.loads((d / "audit_results.json").read_text(encoding="utf-8"))
    ans = {r["id"]: r["answer"] for r in res["answers"]}
    rep = {}
    groups = defaultdict(list)
    for k in rd(d / "_private" / "key.csv"):
        a = ans.get(k["audit_id"])
        if a in ("yes", "no"):
            dis = int((a == "yes") != bool(int(k["machine_yes"])))
            groups[k["cls"]].append(dis)
            groups[f"{k['cls']}:{'co' if int(k['machine_yes']) else 'khong'}"].append(dis)
        groups["unclear_" + k["cls"]].append(int(a == "unsure"))
    for g, v in sorted(groups.items()):
        p, lo, hi = wilson(sum(v), len(v))
        rep[g] = dict(n=len(v), k=sum(v), rate=round(p, 4), ci=[round(lo, 4), round(hi, 4)],
                      pass_lt_10pct=(p < 0.10) if not g.startswith("unclear_") else None)
    rep["reviewer"] = res.get("reviewer", "")
    rep["note"] = "k = số ô người khác máy (hoặc số ô Không rõ với unclear_*); tiêu chí: bất đồng < 10% và không lỗi hệ thống"
    (d / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False, indent=1))


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["owl", "c4pred", "hands", "candidates", "sheets", "collect", "build-train", "build-extra", "build-eval", "audit", "audit-report", "recheck", "c5pred-sh17"])
    ap.add_argument("--eval", action="store_true", help="c4pred: chạy trên ảnh đánh giá thay vì ảnh train")
    ap.add_argument("--task", help="sheets: nhiệm vụ trong review_items_*.csv")
    ap.add_argument("--part", choices=["train", "eval", "chvg", "sh17boots"], help="candidates: phần ảnh")
    ap.add_argument("--chvg", action="store_true", help="owl: quét ảnh CHVG đánh giá kính")
    ap.add_argument("--only", help="audit: chỉ các lớp này (vd boots)")
    ap.add_argument("--tag", default="", help="audit, audit-report: hậu tố thư mục (vd 2 -> audit2)")
    ap.add_argument("--per", type=int, default=50, help="audit: số ô mỗi tầng (lớp x máy nói có / không)")
    ap.add_argument("--tile", type=int, default=144)
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--rows", type=int, default=6)
    ap.add_argument("--ctx", type=float, default=2.5, help="sheets: cạnh ảnh cắt = cạnh dài vùng hộp * ctx")
    args = ap.parse_args()
    dict(owl=cmd_owl, c4pred=cmd_c4pred, hands=cmd_hands, candidates=cmd_candidates, sheets=cmd_sheets, collect=cmd_collect,
         **{"build-train": cmd_build_train, "build-extra": cmd_build_extra, "build-eval": cmd_build_eval, "audit": cmd_audit, "audit-report": cmd_audit_report, "recheck": cmd_recheck, "c5pred-sh17": cmd_c5pred_sh17})[args.cmd](args)


if __name__ == "__main__":
    main()
