"""Thử nghiệm 6 lớp: bộ dữ liệu phân loại ảnh cắt bộ phận (bước kiểm tra thứ hai cho găng, ủng, kính).

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03y_ppe6_part_crops.py

Ghi data/ppe6/parts/{train,val}/<lớp>/*.jpg (định dạng thư mục của YOLO-cls), summary.json và gói
data/ppe6/variants/kaggle/parts_pack.zip (bản 1) hoặc parts_v2_pack.zip (bản 2). Tham số ở configs/ppe6.yaml mục `parts`.
Không sửa data/raw.

Bản 2 (`parts.version: 2`): ngoài ảnh cắt theo hộp (train: tâm, cỡ xê dịch ngẫu nhiên) còn có ảnh cắt theo keypoint như
pipeline (pose trên ảnh cắt từng người, ghép hộp nhãn với cổ tay / mắt cá / mắt như 05e, hình học ngẫu nhiên ở train, hình
học của configs/pipeline.yaml ở val), và tăng cường giống video cho train (nhòe, tối, nén). Tên file: <nguồn>_<box|kp>_<số>.jpg.

Bản 3 (`parts.version: 3`): thêm thân `vest` / `no_vest` (nhãn ppe4 và Construction-PPE mới, cùng vùng thân cho hai lớp;
train có ảnh áo cắt mất phần dưới), ảnh cắt mắt khi mặt nghiêng (một mắt + mũi), tăng cường trắng đen. Gói parts_v3_pack.zip.

Lớp (7): glove, bare_hand (tay); safety_boot, not_safety_foot (giày thường, dép, chân trần) (chân);
goggles, ordinary_glasses, no_eyewear (mắt).
Nguồn nhãn:
- SH17 (VOC gốc): gloves -> glove; hands không trùng găng -> bare_hand; foot -> not_safety_foot;
  face không chứa hộp glasses nào -> no_eyewear.
- Giày, kính của SH17 và Construction-PPE cũ: quyết định hiệu lực của project (người > nhãn máy bản 3 > agent),
  safety -> safety_boot / goggles; ordinary -> not_safety_foot / ordinary_glasses; unclear và kính không đeo bị bỏ.
- Construction-PPE cũ, bản mới: no_gloves -> bare_hand, no_boots -> not_safety_foot, no_goggle -> no_eyewear;
  găng -> glove; Construction-PPE bản mới: boots từ min_boot_px -> safety_boot, goggles -> goggles.
Chia: train = ảnh ppe4 train không thuộc cảnh đánh giá + Construction-PPE bản mới (không trùng cảnh đánh giá);
val = ảnh ppe4 val không cùng cảnh với ảnh train nào và không thuộc cảnh test_new. ppe4 test, Pictor, video không dùng.
"""

import csv
import json
import random
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.machine_labels import human_box_labels, train_boot_override  # noqa: E402

OUT = ROOT / "data" / "ppe6" / "parts"
PACK = ROOT / "data" / "ppe6" / "variants" / "kaggle" / "parts_pack.zip"
REVIEW = ROOT / "data" / "ppe6" / "review"


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def ioa(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max((a[2] - a[0]) * (a[3] - a[1]), 1e-9)


def yolo_boxes(path, w, h):
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        t = line.split()
        if t:
            c, cx, cy, bw, bh = int(t[0]), *map(float, t[1:5])
            out.append((c, [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h]))
    return out


def torso_items(persons, vests, reg):
    """[(lớp, vùng thân)] cho từng người: có tâm hộp áo trong hộp người (đúng một người) -> vest; không hộp áo nào
    -> no_vest; áo nằm trong nhiều người thì bỏ (không chắc của ai). Vùng thân lấy theo association.regions.torso
    cho cả hai lớp, để ảnh cắt hai lớp giống cách cắt (không học mẹo theo hình dạng hộp)."""
    out = []
    owner = []
    for v in vests:
        c = ((v[0] + v[2]) / 2, (v[1] + v[3]) / 2)
        owner.append([i for i, q in enumerate(persons) if q[0] <= c[0] <= q[2] and q[1] <= c[1] <= q[3]])
    for i, q in enumerate(persons):
        mine = [o for o in owner if i in o]
        if any(len(o) > 1 for o in mine):
            continue
        w, h = q[2] - q[0], q[3] - q[1]
        box = [q[0] + reg["x0"] * w, q[1] + reg["y0"] * h, q[0] + reg["x1"] * w, q[1] + reg["y1"] * h]
        out.append(("vest" if mine else "no_vest", box))
    return out


def collect_items(cfg, only=("train", "val"), chv_torso=False):
    """Danh sách (phần, lớp, ảnh, hộp pixel, nguồn) của mọi hộp bộ phận thuộc các phần `only`, chưa giới hạn số lượng.
    05e dùng lại với only=("val",). chv_torso: thêm ảnh CHV (cùng luật chia cảnh) nhưng chỉ lấy áo / không áo, vì CHV
    không có nhãn tay, chân, kính thường (05e dùng để có thêm áo trong val, 14/11/2026)."""
    cppe2_cfg = cfg["cppe2"]
    stats = rd(ROOT / "data" / "ppe4" / "stats.csv")
    scene = {r["file"]: r["scene_id"] for r in rd(ROOT / "data" / "ppe6" / "scene" / "scene_ids.csv")}
    roles = {r["scene_id"]: r["role"] for r in rd(ROOT / "data" / "ppe6" / "eval" / "scene_roles.csv")}
    train_scenes = {scene[r["file"]] for r in stats if r["split"] == "train"}
    split = {}
    for r in stats:
        s = scene.get(r["file"])
        if r["source"] not in ("sh17", "construction_ppe", *(("chv",) if chv_torso else ())) or s is None:
            continue
        if r["split"] == "train" and s not in roles:
            split[r["image"]] = ("train", r["file"])
        elif r["split"] == "val" and s not in train_scenes and roles.get(s) != "test_new":
            split[r["image"]] = ("val", r["file"])

    # Quyết định hiệu lực cho giày, kính (boxes.csv)
    dec = {r["box_id"]: (r["label"], r["note"]) for r in rd(REVIEW / "decisions_v2.csv")}
    for k, (lab, _) in train_boot_override(REVIEW).items():
        dec[k] = (lab, "")
    for k, r in human_box_labels(REVIEW).items():
        dec[k] = (r["after"], "")
    by_img = defaultdict(list)   # ảnh gốc -> [(lớp đích, hộp chuẩn hóa)]
    for b in rd(REVIEW / "boxes.csv"):
        lab, note = dec.get(b["box_id"], ("", ""))
        if note == "not_worn":
            continue
        cls = {("boots", "safety"): "safety_boot", ("boots", "ordinary"): "not_safety_foot",
               ("goggles", "safety"): "goggles", ("goggles", "ordinary"): "ordinary_glasses"}.get((b["target"], lab))
        if cls:
            by_img[b["image"]].append((cls, tuple(float(b[k]) for k in ("cx", "cy", "w", "h"))))

    items = []   # (phần, lớp, đường dẫn ảnh, hộp pixel, nguồn)
    reg = yaml.safe_load((ROOT / "configs" / "pipeline.yaml").read_text(encoding="utf-8"))["association"]["regions"]["torso"]
    for img, (part, fname) in split.items():
        if part not in only:
            continue
        p = ROOT / img
        im = cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)
        if im is None:
            continue
        h, w = im.shape[:2]
        torso_only = img.startswith("data/raw/chv/")
        for cls, (cx, cy, bw, bh) in ([] if torso_only else by_img.get(img, [])):
            items.append((part, cls, img, [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h], "decision"))
        # Áo / không áo theo nhãn ppe4 (0 người, 2 áo; nhãn ppe4 đã sửa ở bước 02-03)
        lab4 = ROOT / "data" / "ppe4" / "dataset" / "labels" / ("train" if part == "train" else "val") / (Path(fname).stem + ".txt")
        if lab4.exists():
            b4 = yolo_boxes(lab4, w, h)
            for cls, bx in torso_items([b for c, b in b4 if c == 0], [b for c, b in b4 if c == 2], reg):
                items.append((part, cls, img, bx, "ppe4"))
        if torso_only:
            continue
        if img.startswith("data/raw/sh17/"):
            voc = ROOT / "data" / "raw" / "sh17" / "voc_labels" / (Path(img).stem + ".xml")
            obj = defaultdict(list)
            for o in ET.parse(voc).getroot().iter("object"):
                bb = o.find("bndbox")
                obj[o.find("name").text].append([float(bb.find(k).text) for k in ("xmin", "ymin", "xmax", "ymax")])
            for g in obj["gloves"]:
                items.append((part, "glove", img, g, "sh17"))
            for hd in obj["hands"]:
                if not any(ioa(hd, g) > 0.5 for g in obj["gloves"]):
                    items.append((part, "bare_hand", img, hd, "sh17"))
            for f in obj["foot"]:
                items.append((part, "not_safety_foot", img, f, "sh17"))
            for fc in obj["face"]:
                if not any(ioa(gl, fc) > 0.3 for gl in obj["glasses"]):
                    items.append((part, "no_eyewear", img, fc, "sh17"))
        else:
            lab = ROOT / img.replace("/images/", "/labels/").rsplit(".", 1)[0]
            m = {1: "glove", 9: "bare_hand", 10: "not_safety_foot", 8: "no_eyewear"}
            for c, bx in yolo_boxes(str(lab) + ".txt", w, h):
                if c in m:
                    items.append((part, m[c], img, bx, "cppe1"))
    # Construction-PPE bản mới: chỉ train, bỏ ảnh trùng cảnh đánh giá
    if "train" not in only:
        return items
    raw2 = ROOT / "data" / "raw" / "construction_ppe_v2"
    names2 = yaml.safe_load((raw2 / "data.yaml").read_text(encoding="utf-8"))["names"]
    bad = set((ROOT / "data" / "ppe6" / "external" / "cppe2" / "eval_overlap.txt").read_text(encoding="utf-8").split())
    m2 = {"gloves": "glove", "no_gloves": "bare_hand", "no_boots": "not_safety_foot", "no_goggle": "no_eyewear", "goggles": "goggles", "boots": "safety_boot"}
    for lab in sorted((raw2 / "labels").rglob("*.txt")):
        img = next((raw2 / "images" / lab.parent.name).glob(lab.stem + ".*"))
        if "cppe2__" + img.name in bad:
            continue
        im = cv2.imdecode(np.fromfile(str(img), dtype=np.uint8), cv2.IMREAD_COLOR)
        h, w = im.shape[:2]
        s = min(1.0, cppe2_cfg["side"] / max(h, w))
        b2 = yolo_boxes(lab, w, h)
        for cls, bx in torso_items([b for c, b in b2 if names2[c] == "Person"], [b for c, b in b2 if names2[c] == "vest"], reg):
            items.append(("train", cls, img.relative_to(ROOT).as_posix(), bx, "cppe2"))
        for c, bx in b2:
            cls = m2.get(names2[c])
            if cls == "safety_boot" and max(bx[2] - bx[0], bx[3] - bx[1]) * s < cppe2_cfg["min_boot_px"]:
                continue
            if cls:
                items.append(("train", cls, img.relative_to(ROOT).as_posix(), bx, "cppe2"))
    return items


def augment(crop, rng, a):
    """Tăng cường giống video (chỉ train): nhòe chuyển động, tối hơn, nén JPEG mạnh; mỗi kiểu xảy ra với xác suất a["prob"]."""
    if rng.random() < a["prob"]:
        n = rng.randint(*a["blur_px"])
        k = np.zeros((n, n), np.float32)
        k[n // 2, :] = 1.0 / n
        rot = cv2.getRotationMatrix2D((n / 2 - 0.5, n / 2 - 0.5), rng.uniform(0, 180), 1.0)
        k = cv2.warpAffine(k, rot, (n, n))
        crop = cv2.filter2D(crop, -1, k / max(k.sum(), 1e-6))
    if rng.random() < a["prob"]:
        crop = np.clip(crop.astype(np.float32) * rng.uniform(*a["dark"]), 0, 255).astype(np.uint8)
    if rng.random() < a["prob"]:
        ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(*a["jpeg"])])
        crop = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if rng.random() < a.get("gray", 0):   # bản 3: ảnh trắng đen (camera đen trắng, kính trong suốt)
        crop = cv2.cvtColor(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    return crop


def square(bx, context, shift=(0.0, 0.0)):
    """(cx, cy, cạnh) quanh hộp bx: cạnh = cạnh dài * context, tâm lệch shift * cạnh."""
    side = max(bx[2] - bx[0], bx[3] - bx[1]) * context
    return ((bx[0] + bx[2]) / 2 + shift[0] * side, (bx[1] + bx[3]) / 2 + shift[1] * side, side)


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    pc = cfg["parts"]
    v2 = pc.get("version", 1) >= 2
    rng = random.Random(pc["seed"])
    items = collect_items(cfg)

    # Giới hạn số ảnh mỗi lớp ở train để không lệch quá
    rng.shuffle(items)
    keep, per = [], Counter()
    for it in items:
        k = (it[0], it[1])
        if it[0] == "train" and per[k] >= pc["max_per_class"]:
            continue
        per[k] += 1
        keep.append(it)
    # Bản 2: ảnh cắt theo keypoint. Train: chọn ngẫu nhiên trước tới 1,6 lần mức giới hạn mỗi lớp (khoảng 1/3 hộp không
    # ghép được keypoint), rồi dừng ở max_per_class khi lưu. Val: lấy hết.
    kp_items, kp_per = [], Counter()
    for it in (items if v2 else []):
        k = (it[0], it[1])
        if it[0] == "train" and kp_per[k] >= 1.6 * pc["max_per_class"]:
            continue
        kp_per[k] += 1
        kp_items.append(it)
    if OUT.exists():
        shutil.rmtree(OUT)
    done, skipped = Counter(), Counter()
    from ppe.parts import PART_CLASSES, cut, match_anchor, people_keypoints
    cls2ppe = {c: ppe for ppe, (pos, negs) in PART_CLASSES.items() for c in (pos, *negs)}
    if v2:
        from ultralytics import YOLO

        from ppe import load_config
        from ppe.pose import PoseEstimator
        pcfg = load_config()
        person_model, pose = YOLO(ROOT / pcfg["pose"]["weights"]), PoseEstimator(pcfg, ROOT)
        kp_conf, val_geom, dev = pcfg["part_cls"]["kp_conf"], pcfg["part_cls"]["geometry"], pcfg["detector"]["device"]
    work = defaultdict(list)    # ảnh -> [(phần, lớp, hộp, nguồn, kiểu)]
    for part, cls, img, bx, src in keep:
        work[img].append((part, cls, bx, src, "box"))
    for part, cls, img, bx, src in kp_items:
        work[img].append((part, cls, bx, src, "kp"))
    kp_count = Counter()
    for n, img in enumerate(sorted(work)):
        im = cv2.imdecode(np.fromfile(str(ROOT / img), dtype=np.uint8), cv2.IMREAD_COLOR)
        people = None
        for part, cls, bx, src, kind in work[img]:
            if kind == "box":
                if not v2 or part == "val":
                    box = square(bx, pc["context"])
                else:
                    j = pc["box_jitter"]
                    box = square(bx, rng.uniform(*j["context"]), (rng.uniform(-j["shift"], j["shift"]), rng.uniform(-j["shift"], j["shift"])))
                if box[2] < pc["min_px"]:
                    skipped["small"] += 1
                    continue
                crop = cut(im, box, pc["min_px"] // 2)
            else:
                if part == "train" and kp_count[(part, cls)] >= pc["max_per_class"]:
                    continue
                if people is None:
                    people = people_keypoints(im, person_model, pose, dev)
                ppe = cls2ppe[cls]
                mk = match_anchor(people, ppe, bx, kp_conf)
                if mk is None:
                    skipped["kp_unmatched"] += 1
                    continue
                kg = pc["kp_geom"]
                key = {"goggles": "eye", "gloves": "hand", "boots": "foot", "vest": "torso"}[ppe]
                if part == "val":
                    # Val: hình học của pipeline; vùng thân chưa có trong pipeline -> giữa khoảng của kp_geom
                    g = val_geom.get(key) or dict(s=sum(kg["torso_s"]) / 2, h=sum(kg["torso_h"]) / 2)
                elif ppe == "goggles":
                    g = dict(s=rng.uniform(*kg["eye_s"]))
                elif ppe == "vest":
                    g = dict(s=rng.uniform(*kg["torso_s"]), h=rng.uniform(*kg["torso_h"]))
                else:
                    g = dict(k=rng.uniform(*kg["k"]), s=rng.uniform(*kg["s"]))
                crop = cut(im, mk(g), pc["min_px"])
                if crop is not None:
                    kp_count[(part, cls)] += 1
            if crop is None:
                skipped["edge" if kind == "box" else "kp_small"] += 1
                continue
            if max(crop.shape[:2]) > pc["save_px"]:
                f = pc["save_px"] / max(crop.shape[:2])
                crop = cv2.resize(crop, (round(crop.shape[1] * f), round(crop.shape[0] * f)), interpolation=cv2.INTER_AREA)
            tr = pc["aug"].get("trunc")
            if v2 and part == "train" and tr and cls2ppe[cls] == "vest" and rng.random() < tr["prob"]:
                # Người sát camera: khung cắt mất phần dưới thân, chỉ còn ngực hoặc vai
                crop = crop[: max(pc["min_px"] // 2, int(crop.shape[0] * rng.uniform(*tr["keep"])))]
            if v2 and part == "train":
                crop = augment(crop, rng, pc["aug"])
            d = OUT / part / cls
            d.mkdir(parents=True, exist_ok=True)
            i = sum(done.values())
            cv2.imwrite(str(d / f"{src}_{kind}_{i:06d}.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
            done[(part, cls, kind)] += 1
        if (n + 1) % 500 == 0:
            print(f"  {n + 1}/{len(work)} ảnh")
    summ = dict(counts={f"{p}/{c}/{k}": v for (p, c, k), v in sorted(done.items())}, skipped=dict(skipped), params=pc)
    (OUT / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    ver = pc.get("version", 1)
    pack = PACK.with_name(f"parts_v{ver}_pack.zip") if ver >= 2 else PACK
    pack.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                z.write(p, "parts/" + p.relative_to(OUT).as_posix())
    print(json.dumps(summ["counts"], ensure_ascii=False, indent=1), summ["skipped"], f"| gói {pack.name} {pack.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
