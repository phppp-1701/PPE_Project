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

Bản 5 (`parts.version: 5`, kế hoạch 2026-11-16_post_holdout_fixes mục 3b): chỉ đổi vùng đầu. (1) Kho `v5.pool`: hộp
đầu từ CHV ppe4 train (mũ mọi màu; bỏ ảnh cùng cảnh với ảnh đánh giá), bộ CC0 data/raw/hard_hat_cc0 (helmet, head) và
SHWD (hat, person); ảnh trùng ảnh đánh giá (pHash) bị bỏ; cắt hộp và keypoint như train v4; người quay lưng (luật D)
có thêm `v5.back_dark.copies` bản làm tối (tên `_dark`, cả hai lớp); `meta.csv` ghi nguồn, kiểu, nhìn từ sau, cỡ, độ
sáng. (2) Tập kiểm riêng `v5.check_out`: `check_frac` ảnh CC0 / SHWD, cắt kiểu val, chỉ để báo cáo. (3) `v5.out` =
`data/ppe6/parts` bản 4 chép nguyên + ảnh kho chọn theo tầng (kiểu cắt × tối × nhỏ, `v5.balance`) để mỗi tầng có mũ ≈
không mũ; `added_meta.csv`, `summary.json` (bảng tầng, kiểm tỉ lệ), gói parts_v5_pack.zip. `--reuse-pool`: bỏ qua (1),
(2) nếu kho đã tạo cùng tham số (chỉ chạy lại bước chọn).

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
import re
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
            # Bản 4: mũ; đầu không chứa hộp mũ nào -> không mũ
            for hm in obj["helmet"]:
                items.append((part, "helmet", img, hm, "sh17"))
            for hd in obj["head"]:
                if not any(ioa(hm, hd) > 0.3 for hm in obj["helmet"]):
                    items.append((part, "no_helmet", img, hd, "sh17"))
        else:
            lab = ROOT / img.replace("/images/", "/labels/").rsplit(".", 1)[0]
            m = {1: "glove", 9: "bare_hand", 10: "not_safety_foot", 8: "no_eyewear", 0: "helmet", 7: "no_helmet"}
            for c, bx in yolo_boxes(str(lab) + ".txt", w, h):
                if c in m:
                    items.append((part, m[c], img, bx, "cppe1"))
    # Construction-PPE bản mới: chỉ train, bỏ ảnh trùng cảnh đánh giá
    if "train" not in only:
        return items
    raw2 = ROOT / "data" / "raw" / "construction_ppe_v2"
    names2 = yaml.safe_load((raw2 / "data.yaml").read_text(encoding="utf-8"))["names"]
    bad = set((ROOT / "data" / "ppe6" / "external" / "cppe2" / "eval_overlap.txt").read_text(encoding="utf-8").split())
    m2 = {"gloves": "glove", "no_gloves": "bare_hand", "no_boots": "not_safety_foot", "no_goggle": "no_eyewear", "goggles": "goggles", "boots": "safety_boot",
          "helmet": "helmet", "no_helmet": "no_helmet"}
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


def phash(im):
    """pHash 64 bit (DCT 32x32, khối 8x8 trừ hệ số DC, so với trung vị)."""
    g = cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    d = cv2.dct(g)[:8, :8].flatten()
    bits = d > np.median(d[1:])
    return int(sum(1 << i for i, b in enumerate(bits) if b))


def eval_hashes():
    """pHash mọi ảnh đánh giá: ppe4 val, test, Pictor, test_new của ppe6 (bản 5 bỏ ảnh nguồn mới trùng các ảnh này)."""
    paths = []
    for sub in ("dataset/images/val", "dataset/images/test", "pictor_test/images/test"):
        paths += sorted((ROOT / "data" / "ppe4" / sub).glob("*"))
    tn = ROOT / "data" / "ppe6" / "dataset" / "test_new.txt"
    if tn.exists():
        for line in tn.read_text(encoding="utf-8").split():
            p = Path(line) if Path(line).is_absolute() else ROOT / "data" / "ppe6" / "dataset" / line
            paths.append(p if p.exists() else ROOT / line)
    hs = []
    for p in paths:
        im = cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR) if p.exists() else None
        if im is not None:
            hs.append(phash(im))
    return np.array(hs, dtype=np.uint64), len(paths)


def hamming_min(h, arr):
    x = np.bitwise_xor(arr, np.uint64(h))
    return int(min(bin(int(v)).count("1") for v in x)) if len(arr) else 64


def extra_head_items(cfg, v5):
    """Bản 5: [(train, lớp, ảnh, hộp pixel, nguồn)] mũ / không mũ từ nguồn bổ sung, thống kê (bỏ vì trùng, nguồn vắng) và
    pHash từng ảnh CC0 / SHWD đã giữ (để tách tập kiểm)."""
    items, info, hashes = [], {}, {}
    srcs = v5["extra_head_sources"]
    if "chv_train" in srcs:
        stats = rd(ROOT / "data" / "ppe4" / "stats.csv")
        scene = {r["file"]: r["scene_id"] for r in rd(ROOT / "data" / "ppe6" / "scene" / "scene_ids.csv")}
        roles = {r["scene_id"]: r["role"] for r in rd(ROOT / "data" / "ppe6" / "eval" / "scene_roles.csv")}
        held = {scene.get(r["file"]) for r in stats if r["split"] != "train"}     # cảnh có ảnh val/test (mọi nguồn)
        n_img, n_skip = 0, 0
        for r in stats:
            if r["source"] != "chv" or r["split"] != "train":
                continue
            s = scene.get(r["file"])
            if s is None or s in held or s in roles:
                n_skip += 1
                continue
            im = cv2.imdecode(np.fromfile(str(ROOT / r["image"]), dtype=np.uint8), cv2.IMREAD_COLOR)
            h, w = im.shape[:2]
            ann = ROOT / "data" / "raw" / "chv" / "annotations" / (Path(r["image"]).stem + ".txt")
            for c, bx in yolo_boxes(ann, w, h):
                if c in (2, 3, 4, 5):               # blue, red, white, yellow helmet
                    items.append(("train", "helmet", r["image"], bx, "chv"))
            n_img += 1
        info["chv_train"] = dict(anh=n_img, bo_vi_cung_canh_danh_gia=n_skip)
    ev, n_ev = (None, 0)
    for name in ("hard_hat_cc0", "shwd"):
        if name not in srcs:
            continue
        base = ROOT / "data" / "raw" / name
        if not base.exists():
            info[name] = "chưa có trên máy"
            continue
        if ev is None:
            ev, n_ev = eval_hashes()
        rows = []
        if name == "hard_hat_cc0":
            for s in json.loads((base / "samples.json").read_text(encoding="utf-8"))["samples"]:
                dets = [(d["label"], d["bounding_box"]) for d in (s.get("ground_truth") or {}).get("detections", [])]
                rows.append((base / s["filepath"], dets, "rel"))
        else:   # SHWD: Pascal VOC (VOC2028/JPEGImages, Annotations)
            for xml in sorted(base.rglob("Annotations/*.xml")):
                img = next(xml.parent.parent.joinpath("JPEGImages").glob(xml.stem + ".*"), None)
                if img is None:
                    continue
                dets = []
                for o in ET.parse(xml).getroot().iter("object"):
                    bb = o.find("bndbox")
                    dets.append(({"hat": "helmet", "person": "head"}.get(o.find("name").text, ""),
                                 [float(bb.find(k).text) for k in ("xmin", "ymin", "xmax", "ymax")]))
                rows.append((img, dets, "abs"))
        n_dup, n_img = 0, 0
        for img, dets, kind in rows:
            im = cv2.imdecode(np.fromfile(str(img), dtype=np.uint8), cv2.IMREAD_COLOR)
            if im is None:
                continue
            ph = phash(im)
            if hamming_min(ph, ev) <= v5["dedup_hamming"]:
                n_dup += 1
                continue
            h, w = im.shape[:2]
            boxes = []
            for lab, b in dets:
                bx = [b[0] * w, b[1] * h, (b[0] + b[2]) * w, (b[1] + b[3]) * h] if kind == "rel" else b
                boxes.append((lab, bx))
            hel = [bx for lab, bx in boxes if lab == "helmet"]
            rel = img.relative_to(ROOT).as_posix()
            hashes[rel] = ph
            for bx in hel:
                items.append(("train", "helmet", rel, bx, name))
            for lab, bx in boxes:
                if lab == "head" and not any(ioa(hm, bx) > 0.3 for hm in hel):
                    items.append(("train", "no_helmet", rel, bx, name))
            n_img += 1
        info[name] = dict(anh=n_img, bo_vi_trung_anh_danh_gia=n_dup, anh_danh_gia_so_sanh=n_ev)
    return items, info, hashes


def people_boxes_kps(im, person_model, pose, device):
    """Như ppe.parts.people_keypoints nhưng giữ hộp người (cần cho luật quay lưng)."""
    from types import SimpleNamespace

    r = person_model.predict(im, imgsz=640, conf=0.25, device=device, verbose=False)[0]
    tracks = [SimpleNamespace(xyxy=b, extra={}) for b in r.boxes.xyxy.cpu().numpy()]
    pose(im, tracks)
    return [(t.xyxy, t.extra["kps"]) for t in tracks if t.extra.get("kps")]


def is_back(people, bx, kp_conf, bv):
    """Người có điểm gốc đầu gần tâm hộp nhãn nhất (như match_anchor) có quay lưng theo luật D không."""
    from ppe.compliance import back_view_now
    from ppe.parts import anchors
    c = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
    lim = max(bx[2] - bx[0], bx[3] - bx[1])
    best = None
    for box, kps in people:
        for pt, _ in anchors(kps, "helmet", kp_conf):
            d = float(np.hypot(pt[0] - c[0], pt[1] - c[1]))
            if d <= lim and (best is None or d < best[0]):
                best = (d, box, kps)
    return bool(best and back_view_now(best[2], best[1], bv))


def darken(crop, rng, a):
    """Bản 5: ảnh tối (nhân kênh V với hệ số trong a["v"]), đôi khi trắng đen."""
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 2] *= rng.uniform(*a["v"])
    out = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)
    if rng.random() < a["gray"]:
        out = cv2.cvtColor(cv2.cvtColor(out, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    return out


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


HEAD_CLS = ("helmet", "no_helmet")
NAME_RE = re.compile(r"^(?P<src>.+?)_(?P<kind>box|kp)(?P<dark>_dark\d)?_(?P<i>p?\d+)\.jpg$")
META_COLS = ["file", "cls", "src", "kind", "back", "synth", "uid", "size", "v", "image"]


def relp(p):
    """Đường dẫn so với gốc project (tuyệt đối nếu nằm ngoài)."""
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def head_stats(crop):
    """(cạnh dài ảnh lưu, V trung bình HSV của nửa giữa ảnh): dùng để chia tầng tối / nhỏ."""
    h, w = crop.shape[:2]
    c = crop[int(h * .25):int(h * .75) + 1, int(w * .25):int(w * .75) + 1]
    return max(h, w), round(float(cv2.cvtColor(c, cv2.COLOR_BGR2HSV)[..., 2].mean()), 1)


def fit(crop, pc):
    if max(crop.shape[:2]) > pc["save_px"]:
        f = pc["save_px"] / max(crop.shape[:2])
        crop = cv2.resize(crop, (round(crop.shape[1] * f), round(crop.shape[0] * f)), interpolation=cv2.INTER_AREA)
    return crop


def write_csv(path, rows, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def v5_crops(cfg, pc, v5, rng):
    """Bản 5, phần 1: kho ảnh đầu nguồn mới (train, như train v4) và tập kiểm riêng (kiểu val). Ghi meta.csv mỗi nơi."""
    from ultralytics import YOLO

    from ppe import load_config
    from ppe.parts import cut, match_anchor
    from ppe.pose import PoseEstimator

    items, info, hashes = extra_head_items(cfg, v5)
    print("bản 5, nguồn bổ sung:", json.dumps(info, ensure_ascii=False), len(items), "hộp", flush=True)
    # Tập kiểm: check_frac ảnh mỗi nguồn trong check_sources, chọn theo ảnh
    check = set()
    for src in v5["check_sources"]:
        imgs = sorted({it[2] for it in items if it[4] == src})
        rng.shuffle(imgs)
        check |= set(imgs[: round(v5["check_frac"] * len(imgs))])
    ch = np.array([hashes[i] for i in sorted(check) if i in hashes], dtype=np.uint64)
    near = {i for i in sorted({it[2] for it in items} - check)
            if i in hashes and hamming_min(hashes[i], ch) <= v5["dedup_hamming"]}
    info["tap_kiem"] = dict(anh=len(check), anh_train_bo_vi_gan_trung_tap_kiem=len(near))
    pool_items = [it for it in items if it[2] not in check and it[2] not in near]
    check_items = [it for it in items if it[2] in check]
    # Giới hạn kho: mỗi (nguồn, lớp) tối đa pool_max_per_src_cls hộp, ngẫu nhiên
    rng.shuffle(pool_items)
    per, kept = Counter(), []
    tiny = lambda it: max(it[3][2] - it[3][0], it[3][3] - it[3][1]) * pc["context"] < pc["min_px"]   # noqa: E731
    info["bo_hop_qua_nho"] = sum(1 for it in pool_items if tiny(it))
    for it in pool_items:
        if tiny(it):
            continue
        if per[(it[4], it[1])] < v5["pool_max_per_src_cls"]:
            per[(it[4], it[1])] += 1
            kept.append(it)
    info["kho_hop"] = {f"{s}/{c}": n for (s, c), n in sorted(per.items())}
    info["tap_kiem_hop"] = dict(Counter(f"{it[4]}/{it[1]}" for it in check_items))
    pcfg = load_config()
    person_model, pose = YOLO(ROOT / pcfg["pose"]["weights"]), PoseEstimator(pcfg, ROOT)
    kp_conf, dev = pcfg["part_cls"]["kp_conf"], pcfg["detector"]["device"]
    head_geom = pcfg["part_cls"]["geometry"]["head"]
    kg, j = pc["kp_geom"], pc["box_jitter"]
    pool_dir, check_dir = ROOT / v5["pool"], ROOT / v5["check_out"]
    for d in (pool_dir, check_dir):
        if d.exists():
            shutil.rmtree(d)
    work = defaultdict(list)
    for it in kept:
        work[it[2]].append(("pool", it))
    for it in check_items:
        work[it[2]].append(("check", it))
    meta, meta_check, skipped, n_out = [], [], Counter(), 0
    for n, img in enumerate(sorted(work)):
        im = cv2.imdecode(np.fromfile(str(ROOT / img), dtype=np.uint8), cv2.IMREAD_COLOR)
        pb = people_boxes_kps(im, person_model, pose, dev)
        people = [k for _, k in pb]
        for where, (_, cls, _, bx, src) in work[img]:
            back = int(is_back(pb, bx, kp_conf, v5["back_view"]))
            for kind in ("box", "kp"):
                if kind == "box":
                    box = (square(bx, pc["context"]) if where == "check" else
                           square(bx, rng.uniform(*j["context"]), (rng.uniform(-j["shift"], j["shift"]), rng.uniform(-j["shift"], j["shift"]))))
                    if box[2] < pc["min_px"]:
                        skipped[f"{where}_small"] += 1
                        continue
                    crop = cut(im, box, pc["min_px"] // 2)
                else:
                    mk = match_anchor(people, "helmet", bx, kp_conf)
                    if mk is None:
                        skipped[f"{where}_kp_unmatched"] += 1
                        continue
                    g = head_geom if where == "check" else dict(k=rng.uniform(*kg["head_k"]), s=rng.uniform(*kg["head_s"]))
                    crop = cut(im, mk(g), pc["min_px"])
                if crop is None:
                    skipped[f"{where}_edge"] += 1
                    continue
                crop = fit(crop, pc)
                if where == "pool":
                    crop = augment(crop, rng, pc["aug"])
                base = pool_dir if where == "pool" else check_dir
                d = base / cls
                d.mkdir(parents=True, exist_ok=True)
                uid = f"{src}_{kind}_p{n_out:06d}"
                n_out += 1
                f = d / f"{uid}.jpg"
                cv2.imwrite(str(f), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
                size, v = head_stats(crop)
                row = dict(file=relp(f), cls=cls, src=src, kind=kind, back=back, synth=0, uid=uid,
                           size=size, v=v, image=img)
                (meta if where == "pool" else meta_check).append(row)
                if where == "pool" and back:
                    # Người quay lưng -> bản làm tối (mũ và không mũ như nhau)
                    for c in range(v5["back_dark"]["copies"]):
                        dk = darken(crop, rng, v5["back_dark"])
                        fd = d / f"{src}_{kind}_dark{c}_p{n_out - 1:06d}.jpg"
                        cv2.imwrite(str(fd), dk, [cv2.IMWRITE_JPEG_QUALITY, 92])
                        size, v = head_stats(dk)
                        meta.append(dict(row, file=relp(fd), synth=1, size=size, v=v))
        if (n + 1) % 500 == 0:
            print(f"  {n + 1}/{len(work)} ảnh", flush=True)
    write_csv(pool_dir / "meta.csv", meta, META_COLS)
    write_csv(check_dir / "meta.csv", meta_check, META_COLS)
    info["bo_qua"] = dict(skipped)
    (pool_dir / "pool_info.json").write_text(json.dumps(dict(info=info, params=pc), ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    return info


def v5_select(pc, v5, rng):
    """Bản 5, phần 2: gốc v4 + ảnh kho chọn theo tầng (kế hoạch 2026-11-16_post_holdout_fixes mục 3b)."""
    bal = v5["balance"]
    base_dir, pool_dir = ROOT / v5["base_from"], ROOT / v5["pool"]

    def stratum(r):
        return (r["kind"], int(float(r["v"]) < bal["dark_v"]), int(int(r["size"]) < bal["small_px"]))

    base = []
    for cls in HEAD_CLS:
        for f in sorted((base_dir / "train" / cls).glob("*.jpg")):
            m = NAME_RE.match(f.name)
            im = cv2.imdecode(np.fromfile(str(f), dtype=np.uint8), cv2.IMREAD_COLOR)
            size, v = head_stats(im)
            base.append(dict(cls=cls, src=m["src"], kind=m["kind"], size=size, v=v))
    meta = list(csv.DictReader((pool_dir / "meta.csv").open(encoding="utf-8")))
    synth_of = defaultdict(list)
    pool = defaultdict(list)
    for r in meta:
        if r["synth"] == "1":
            synth_of[(r["cls"], r["uid"])].append(r)
        else:
            pool[(r["cls"], stratum(r))].append(r)
    for k in sorted(pool):
        rng.shuffle(pool[k])
    cnt = Counter((r["cls"], stratum(r)) for r in base)
    strata = sorted({stratum(r) for r in base} | {s for _, s in pool})
    chosen, short = [], {}

    def take(cls, s, n, back_first):
        """Lấy n ảnh thật lớp cls ở tầng s; mỗi nguồn tối đa cap_src * n; back_first: ưu tiên nhìn từ sau, ngược lại tránh."""
        lst = sorted(pool[(cls, s)], key=lambda r: -int(r["back"]) if back_first else int(r["back"]))
        cap = max(1, int(bal["cap_src"] * n))
        got, per, rest = [], Counter(), []
        for r in lst:
            if len(got) < n and per[r["src"]] < cap:
                per[r["src"]] += 1
                got.append(r)
            else:
                rest.append(r)
        pool[(cls, s)] = rest
        return got

    first = []
    for s in strata:
        t = int(round(bal["g"] * max(cnt[("helmet", s)], cnt[("no_helmet", s)])))
        for c in HEAD_CLS:
            need = t - cnt[(c, s)]
            if need > 0:
                got = take(c, s, need, True)
                first += got
                cnt[(c, s)] += len(got)
                if len(got) < need:
                    short[f"{c}/{s}"] = need - len(got)
    syn = [x for r in first if r["back"] == "1" for x in synth_of[(r["cls"], r["uid"])]]
    for x in syn:
        cnt[(x["cls"], stratum(x))] += 1
    second = []
    for s in strata:
        if s[1] == 1:
            h, n = cnt[("helmet", s)], cnt[("no_helmet", s)]
            c, need = ("helmet", n - h) if n > h else ("no_helmet", h - n)
            if need > 0:
                got = [r for r in take(c, s, need, False)]
                # Ảnh nhìn từ sau lấy ở vòng này không kéo bản làm tối (để không lệch lại tầng tối)
                second += got
                cnt[(c, s)] += len(got)
                if len(got) < need:
                    short[f"{c}/{s}/can_lai_tang_toi"] = need - len(got)
    # Cân bản làm tối (mục 3b, người dùng chọn 16/11/2026): mỗi tầng tối, tỉ lệ ảnh làm tối của không mũ = của mũ (mũ
    # cần bản làm tối vì thiếu mũ tối thật). Thiếu: thay ảnh không mũ thật đã thêm bằng bản làm tối của ảnh không mũ
    # sáng trong kho (cùng kiểu cắt, cùng cỡ); thừa: thay bản làm tối bằng ảnh không mũ tối thật. Tổng tầng giữ nguyên,
    # gốc v4 không đổi.
    new_syn, drop, synth_balance = [], set(), {}
    for s in strata:
        if s[1] != 1:
            continue
        h_s = cnt[("helmet", s)]
        n_s = cnt[("no_helmet", s)]
        f = sum(1 for x in syn if x["cls"] == "helmet" and stratum(x) == s) / h_s if h_s else 0.0
        base_n = sum(1 for r in base if r["cls"] == "no_helmet" and stratum(r) == s)
        syn_n = [x for x in syn if x["cls"] == "no_helmet" and stratum(x) == s]
        real_n = [r for r in first + second if r["cls"] == "no_helmet" and stratum(r) == s]
        target = min(round(f * n_s), n_s - base_n)
        made = 0
        if target > len(syn_n):
            want = target - len(syn_n)
            rng.shuffle(real_n)
            removable = sorted(real_n, key=lambda r: int(r["back"]))[:want]   # bỏ ảnh không kéo bản làm tối trước
            src_list = sorted(pool[("no_helmet", (s[0], 0, s[2]))], key=lambda r: int(r["back"]))
            used = set()
            for r in src_list:
                if made >= len(removable):
                    break
                im = cv2.imdecode(np.fromfile(str(ROOT / r["file"]), dtype=np.uint8), cv2.IMREAD_COLOR)
                dk = darken(im, rng, v5["back_dark"])
                size, v = head_stats(dk)
                if v >= bal["dark_v"] or (int(size) < bal["small_px"]) != bool(s[2]):
                    continue
                used.add(r["uid"])
                new_syn.append(dict(r, synth=1, size=size, v=v, _img=dk,
                                    file=f"{r['src']}_{r['kind']}_dark2_{r['uid'].rsplit('_', 1)[-1]}.jpg"))
                made += 1
            pool[("no_helmet", (s[0], 0, s[2]))] = [r for r in pool[("no_helmet", (s[0], 0, s[2]))] if r["uid"] not in used]
            drop |= {id(r) for r in removable[:made]}
        elif target < len(syn_n):
            want = len(syn_n) - target
            got = take("no_helmet", s, want, False)
            second += got
            rng.shuffle(syn_n)
            drop |= {id(x) for x in syn_n[:len(got)]}
            made = -len(got)
        synth_balance[str(s)] = dict(ti_le_tao_mu=round(f, 3), dich_khong_mu=target, truoc=len(syn_n),
                                     sau=len(syn_n) + made)
    first = [r for r in first if id(r) not in drop]
    second = [r for r in second if id(r) not in drop]
    syn = [x for x in syn if id(x) not in drop] + new_syn
    chosen = first + second + syn
    # Ghi: chép nguyên gốc v4 rồi thêm ảnh đã chọn
    out = ROOT / v5["out"]
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(base_dir, out, ignore=shutil.ignore_patterns("summary.json"))
    for r in chosen:
        dst = out / "train" / r["cls"] / Path(r["file"]).name
        if "_img" in r:
            cv2.imwrite(str(dst), r.pop("_img"), [cv2.IMWRITE_JPEG_QUALITY, 92])
            r["file"] = relp(dst)
        else:
            shutil.copy2(ROOT / r["file"], dst)
    write_csv(out / "added_meta.csv", chosen, META_COLS)
    # Bảng tầng và kiểm tỉ lệ
    final = base + chosen
    table, ok = [], True
    lo, hi = bal["ratio_ok"]
    for s in strata:
        h = sum(1 for r in final if r["cls"] == "helmet" and stratum(r) == s)
        n = sum(1 for r in final if r["cls"] == "no_helmet" and stratum(r) == s)
        ratio = h / n if n else None
        good = (h == n == 0) or (ratio is not None and lo <= ratio <= hi)   # tầng trống: không lệch
        ok &= good
        table.append(dict(tang=dict(kieu=s[0], toi=s[1], nho=s[2]), mu=h, khong_mu=n, ti_le=ratio and round(ratio, 3), dat=good,
                          mu_goc=sum(1 for r in base if r["cls"] == "helmet" and stratum(r) == s),
                          khong_mu_goc=sum(1 for r in base if r["cls"] == "no_helmet" and stratum(r) == s),
                          mu_tao_them=sum(1 for r in syn if r["cls"] == "helmet" and stratum(r) == s),
                          khong_mu_tao_them=sum(1 for r in syn if r["cls"] == "no_helmet" and stratum(r) == s)))
    per_cls = {}
    for c in HEAD_CLS:
        f = [r for r in final if r["cls"] == c]
        real = [r for r in f if str(r.get("synth", "0")) == "0"]
        per_cls[c] = dict(tong=len(f), goc_v4=sum(1 for r in base if r["cls"] == c),
                          them_that=sum(1 for r in first + second if r["cls"] == c),
                          them_tao=sum(1 for r in syn if r["cls"] == c),
                          nguon=dict(Counter(r["src"] for r in f).most_common()),
                          kieu=dict(Counter(r["kind"] for r in f)),
                          ti_le_toi=round(sum(float(r["v"]) < bal["dark_v"] for r in f) / len(f), 3),
                          ti_le_toi_anh_that=round(sum(float(r["v"]) < bal["dark_v"] for r in real) / len(real), 3),
                          ti_le_nho=round(sum(int(r["size"]) < bal["small_px"] for r in f) / len(f), 3),
                          nhin_tu_sau_them=sum(1 for r in first + second if r["cls"] == c and r["back"] == "1"),
                          nhin_tu_sau_them_toi=sum(1 for r in first + second if r["cls"] == c and r["back"] == "1"
                                                   and float(r["v"]) < bal["dark_v"]))
    counts = Counter()
    for p in sorted(out.rglob("*.jpg")):
        counts[f"{p.parent.parent.name}/{p.parent.name}"] += 1
    return dict(counts=dict(sorted(counts.items())), tang=table, ti_le_dat=ok, lop_dau=per_cls, thieu_anh=short,
                can_ban_lam_toi=synth_balance)


def build_v5(cfg, pc, v5):
    """Bản 5 (kế hoạch 2026-11-16_post_holdout_fixes mục 3b). `--reuse-pool`: dùng lại kho và tập kiểm đã tạo (cùng tham số)."""
    rng = random.Random(pc["seed"])
    pool_info = ROOT / v5["pool"] / "pool_info.json"
    if "--reuse-pool" in sys.argv and pool_info.exists():
        old = json.loads(pool_info.read_text(encoding="utf-8"))
        keys = ("extra_head_sources", "check_sources", "check_frac", "pool_max_per_src_cls", "back_view", "back_dark", "dedup_hamming")
        if any(old["params"]["v5"].get(k) != v5.get(k) for k in keys) or old["params"]["seed"] != pc["seed"]:
            raise SystemExit("tham số kho khác lần tạo trước: chạy lại không có --reuse-pool")
        info = old["info"]
        print("dùng lại kho", v5["pool"], flush=True)
    else:
        info = v5_crops(cfg, pc, v5, rng)
    sel = v5_select(pc, v5, random.Random(pc["seed"] + 1))
    out = ROOT / v5["out"]
    check_n = Counter(r["cls"] + ("/nhin_tu_sau" if r["back"] == "1" else "") for r in
                      csv.DictReader((ROOT / v5["check_out"] / "meta.csv").open(encoding="utf-8")))
    summ = dict(sel, nguon_moi=info, tap_kiem=dict(check_n), params=pc,
                note="train = train bản 4 chép nguyên + ảnh đầu chọn theo tầng (added_meta.csv); val = val bản 4")
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    pack = PACK.with_name("parts_v5_pack.zip")
    pack.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file() and p.suffix == ".jpg" or p.name == "summary.json":
                z.write(p, "parts/" + p.relative_to(out).as_posix())
    for t in sel["tang"]:
        print(" ", t)
    print(json.dumps(sel["lop_dau"], ensure_ascii=False))
    print("tỉ lệ mọi tầng đạt:", sel["ti_le_dat"], "| thiếu ảnh:", sel["thieu_anh"], "| tập kiểm:", dict(check_n),
          f"| gói {pack.name} {pack.stat().st_size / 1e6:.1f} MB")


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))
    pc = cfg["parts"]
    if pc.get("version", 1) >= 5:
        return build_v5(cfg, pc, pc["v5"])
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
                key = {"goggles": "eye", "gloves": "hand", "boots": "foot", "vest": "torso", "helmet": "head"}[ppe]
                if part == "val":
                    # Val: hình học của pipeline; vùng chưa có trong pipeline -> giữa khoảng của kp_geom
                    mid = {"torso": dict(s=sum(kg["torso_s"]) / 2, h=sum(kg["torso_h"]) / 2),
                           "head": dict(k=sum(kg["head_k"]) / 2, s=sum(kg["head_s"]) / 2)}
                    g = val_geom.get(key) or mid[key]
                elif ppe == "helmet":
                    g = dict(k=rng.uniform(*kg["head_k"]), s=rng.uniform(*kg["head_s"]))
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
