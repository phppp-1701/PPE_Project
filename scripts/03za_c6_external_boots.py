"""C6 bước C (kế hoạch docs/experiments/2026-11-16_c5_detector_plan.md, mục C6): đưa hai bộ ủng ngoài (Roboflow) vào
train. Chỉ train; không sửa data/raw.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03za_c6_external_boots.py scan     # pHash + C5-s960 trên ảnh gốc và ảnh xoay 90° -> scan.json
    python scripts/03za_c6_external_boots.py build    # lọc, gán nhãn, ghi data/ppe6/c6/ext/{images,labels}/train
    python scripts/03za_c6_external_boots.py pack     # bộ phụ C6 + gói Kaggle c6_extra_pack.zip
    python scripts/03za_c6_external_boots.py scan --section c8_ext; ... build --section c8_ext   # C8: bộ găng (gói ở 03zc pack)

Tham số ở configs/ppe6.yaml mục `c6_ext`. Cách làm:
- Bộ chỉ có nhãn giày. Hộp ủng / giày bảo hộ của bộ -> lớp 5 (boots); giày thường -> không nhãn (mẫu âm).
- Ảnh bị xoay sẵn (nguồn đã tăng cường): C5-s960 thấy người rõ hơn hẳn khi xoay ảnh 90° -> bỏ ảnh.
- Ảnh gần trùng (pHash, Hamming <= dedup_hamming) trong và giữa hai bộ: giữ ảnh đầu; ảnh gần trùng ảnh đánh giá
  (ppe4 val, test, Pictor, val/test C5 gồm CHVG) -> bỏ.
- Người, mũ, áo không có nhãn trong bộ: **nhãn máy** từ C5-s960 (conf >= pseudo_conf); dự đoán conf trong
  [mask_conf, pseudo_conf) -> che xám (không học). Găng, kính: không gán giả nhãn, mọi dự đoán conf >= mask_conf_small
  -> che xám. Không che vùng trùng hộp ủng (ioa > 0,3).
- Ảnh thu về cạnh dài max_side, JPEG 92. Tên: <tiền tố>__<tên gốc>.jpg.
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SECTION = "c6_ext"   # đổi bằng --section (C8: c8_ext, găng)
OUT = ROOT / "data" / "ppe6" / "c6"


def cfg():
    return yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))[SECTION]


def imread(p):
    return cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)


def phash(im):
    """pHash 64 bit, như 03y."""
    g = cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    d = cv2.dct(g)[:8, :8].flatten()
    bits = d > np.median(d[1:])
    return int(sum(1 << i for i, b in enumerate(bits) if b))


def ham(a, b):
    return bin(a ^ b).count("1")


def images(c):
    out = []
    for name, s in c["sources"].items():
        for p in sorted((ROOT / s["dir"]).glob("*/images/*")):
            out.append((name, p))
    return out


def yolo_rows(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        t = line.split()
        if t:
            k, cx, cy, w, h = int(t[0]), *map(float, t[1:5])
            rows.append((k, [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]))
    return rows


def ioa(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max((a[2] - a[0]) * (a[3] - a[1]), 1e-12)


def cmd_scan(args):
    from ultralytics import YOLO

    c = cfg()
    model = YOLO(str(ROOT / c["weights"]))
    res = {}
    imgs = images(c)
    for n, (src, p) in enumerate(imgs):
        im = imread(p)
        if im is None:
            continue
        views = [im, cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE), cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)]
        rs = model.predict(views, imgsz=960, conf=0.1, device=0, verbose=False)
        pmax = [float(r.boxes.conf[r.boxes.cls == 0].max()) if (r.boxes.cls == 0).any() else 0.0 for r in rs]
        bmax = [float(r.boxes.conf[r.boxes.cls == 5].max()) if (r.boxes.cls == 5).any() else 0.0 for r in rs]
        r0 = rs[0]
        res[f"{src}/{p.parent.parent.name}/{p.name}"] = dict(
            phash=str(phash(im)), size=[im.shape[1], im.shape[0]], person_max=[round(x, 3) for x in pmax], boots_max=[round(x, 3) for x in bmax],
            pred=[(int(k), round(float(s), 3), [round(float(v), 5) for v in b])
                  for k, s, b in zip(r0.boxes.cls.tolist(), r0.boxes.conf.tolist(), r0.boxes.xyxyn.tolist())])
        if (n + 1) % 300 == 0:
            print(f"{n + 1}/{len(imgs)}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "scan.json").write_text(json.dumps(res), encoding="utf-8")
    print(len(res), "ảnh")


def group_of(key):
    """Nhóm cảnh theo tên gốc Roboflow: <nguồn>:<tiền tố trước số khung> (vd vf:Video4, vf:image, nc:construction)."""
    import re
    src, name = key.split("/")[0], key.split("/")[-1]
    m = re.match(r"(.+?)_(\d+)_jpg", name)
    return f"{src}:{m.group(1) if m else name.split('_jpg')[0][:12]}"


def eval_hashes():
    cache = OUT / "eval_hashes.json"
    if cache.exists():
        return [int(h) for h in json.loads(cache.read_text(encoding="utf-8"))]
    paths = []
    for sub in ("dataset/images/val", "dataset/images/test", "pictor_test/images/test"):
        paths += sorted((ROOT / "data" / "ppe4" / sub).glob("*"))
    for sp in ("val", "test"):
        paths += sorted((ROOT / "data" / "ppe6" / "c5" / "eval" / sp / "images").glob("*"))
    hs = []
    for p in paths:
        im = imread(p)
        if im is not None:
            hs.append(phash(im))
    OUT.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps([str(h) for h in hs]), encoding="utf-8")
    return hs


def min_dist(h, ev_bits):
    b = np.unpackbits(np.array([h], dtype=np.uint64).view(np.uint8))
    return int((ev_bits != b).sum(1).min())


def cmd_build(args):
    import shutil

    c = cfg()
    scan = json.loads((OUT / "scan.json").read_text(encoding="utf-8"))
    ev_bits = np.unpackbits(np.array(eval_hashes(), dtype=np.uint64).view(np.uint8).reshape(-1, 8), axis=1)
    # Lọc theo cảnh: nhóm tên gốc nào có ảnh cách ảnh đánh giá <= group_hamming thì bỏ cả nhóm (các bộ Roboflow có khung
    # cắt từ cùng video với Construction-PPE cũ, một phần thuộc val / test)
    dist = {k: min_dist(int(v["phash"]), ev_bits) for k, v in scan.items()}
    bad_groups = {group_of(k) for k, d in dist.items() if d <= c["group_hamming"]}
    out = OUT / "ext"
    if out.exists():
        shutil.rmtree(out)
    (out / "images" / "train").mkdir(parents=True)
    (out / "labels" / "train").mkdir(parents=True)
    stat, kept_h, log = Counter(), [], []
    for (src, p) in images(c):
        key = f"{src}/{p.parent.parent.name}/{p.name}"
        s = scan.get(key)
        if s is None:
            stat["khong_doc_duoc"] += 1
            continue
        sc = c["sources"][src]
        rows = yolo_rows(p.parent.parent / "labels" / (p.stem + ".txt"))
        target = sc.get("target", 5)   # lớp đích của bộ: 5 ủng (C6), 3 găng (C8)
        boots = [b for k, b in rows if k in sc.get("ids", sc.get("boots", []))]
        if not boots:
            stat["khong_co_ung"] += 1
            continue
        pm, bm = s["person_max"], s.get("boots_max", [0, 0, 0])
        # Ảnh xoay sẵn: người hoặc ủng được thấy rõ hơn hẳn khi xoay 90° (spec 2.4: không xoay góc lớn)
        if any(max(v[1], v[2]) >= c["rot_min"] and max(v[1], v[2]) > v[0] + c["rot_margin"] for v in (pm, bm)):
            stat["anh_xoay"] += 1
            continue
        h = int(s["phash"])
        if group_of(key) in bad_groups:
            stat["nhom_canh_danh_gia"] += 1
            continue
        if any(ham(h, k) <= c["dedup_hamming"] for k in kept_h):
            stat["gan_trung"] += 1
            continue
        kept_h.append(h)
        labels = [[target, b] for b in boots]
        masks = []
        for k, conf, b in s["pred"]:
            if k in (0, 1, 2):
                if conf >= c["pseudo_conf"]:
                    labels.append([k, b])
                    stat[f"nhan_may_{k}"] += 1
                elif conf >= c["mask_conf"]:
                    masks.append(b)
            elif k in (3, 4, 5) and k != target and conf >= c["mask_conf_small"]:   # PPE nhỏ khác lớp đích: che
                masks.append(b)
        masks = [m for m in masks if all(ioa(g, m) <= 0.3 for g in boots)]
        im = imread(p)
        H, W = im.shape[:2]
        for b in masks:
            im[max(int(b[1] * H), 0):int(np.ceil(b[3] * H)), max(int(b[0] * W), 0):int(np.ceil(b[2] * W))] = (114, 114, 114)
        f = min(1.0, c["max_side"] / max(H, W))
        if f < 1:
            im = cv2.resize(im, (round(W * f), round(H * f)), interpolation=cv2.INTER_AREA)
        name = f"{sc['prefix']}__{p.parent.parent.name}_{p.stem}"
        cv2.imwrite(str(out / "images" / "train" / f"{name}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        (out / "labels" / "train" / f"{name}.txt").write_text("".join(
            f"{k} {(b[0] + b[2]) / 2:.6f} {(b[1] + b[3]) / 2:.6f} {b[2] - b[0]:.6f} {b[3] - b[1]:.6f}\n" for k, b in labels), encoding="utf-8")
        stat[f"giu_{src}"] += 1
        stat["hop_ung"] += len(boots)
        stat["vung_che"] += len(masks)
        log.append(dict(file=f"{name}.jpg", source=key, boots=len(boots), masks=len(masks)))
    (out / "summary.json").write_text(json.dumps(dict(stat=dict(stat), params=c, bad_groups=sorted(bad_groups), files=log), ensure_ascii=False, indent=1), encoding="utf-8")
    print(dict(stat))


def rotcheck_excluded():
    """Ảnh Claude loại khi xem lại toàn bộ ảnh đã lọc (data/ppe6/c6/rotcheck/rot_<số>.dec: số ô, cách nhau khoảng trắng;
    rot_<số>.txt: ô -> tên ảnh): ảnh xoay / lộn ngược / ảnh ghép, poster mà bộ lọc tự động bỏ sót. Nhãn máy."""
    out = set()
    d = OUT / "rotcheck"
    for dec in sorted(d.glob("rot_*.dec")):
        cells = dict(line.split(None, 1) for line in dec.with_suffix(".txt").read_text(encoding="utf-8").splitlines())
        for line in dec.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                out |= {cells[k] for k in line.split()}
    return out


def cmd_pack(args):
    """Bộ phụ C6 = bộ phụ C5 (c5/c5_extra) + ảnh ủng ngoài (c6/ext); oversample = C5 + ảnh train C5 có ủng + ảnh ủng
    ngoài (mỗi ảnh thêm một bản, như găng); kèm trọng số C5-s960 để tinh chỉnh. Ghi data/ppe6/c6/c6_extra và gói
    data/ppe6/variants/kaggle/c6_extra_pack.zip. Gói chính dùng lại c5_pack.zip (không đổi)."""
    import shutil
    import zipfile

    c = cfg()
    src = ROOT / "data" / "ppe6" / "c5" / "c5_extra"
    ext = OUT / "ext"
    out = OUT / c.get("pack_name", "c6_extra")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    n_ext = 0
    excl = rotcheck_excluded()
    for p in sorted((ext / "images" / "train").iterdir()):
        if p.name in excl:
            continue
        shutil.copy2(p, out / "images" / "train" / p.name)
        shutil.copy2(ext / "labels" / "train" / (p.stem + ".txt"), out / "labels" / "train" / (p.stem + ".txt"))
        n_ext += 1
    rep = [x for x in (src / "oversample.txt").read_text(encoding="utf-8").split() if x]
    main = ROOT / "data" / "ppe6" / "c5" / "dataset_c5"
    boot_main = [p.name for p in sorted((main / "images" / "train").iterdir())
                 if any(r[0] == 5 for r in yolo_rows(main / "labels" / "train" / (p.stem + ".txt")))]
    boot_main += [p.name for p in sorted((src / "images" / "train").iterdir())   # ảnh bộ phụ C5 có ủng (Construction-PPE mới, ảnh cắt)
                  if any(r[0] == 5 for r in yolo_rows(src / "labels" / "train" / (p.stem + ".txt")))]
    boot_ext = sorted(p.name for p in (ext / "images" / "train").iterdir() if p.name not in excl)
    allrep = list(dict.fromkeys(rep + boot_main + boot_ext))
    (out / "oversample.txt").write_text("".join(x + "\n" for x in allrep), encoding="utf-8")
    (out / "weights").mkdir(exist_ok=True)
    shutil.copy2(ROOT / c["weights"], out / "weights" / "c5_s960_best.pt")
    summ = json.loads((src / "summary.json").read_text(encoding="utf-8"))
    summ["c6"] = dict(ext_images=n_ext, rotcheck_excluded=len(excl), oversample_c5=len(rep), oversample_boot_main=len(boot_main), oversample_boot_ext=len(boot_ext),
                      oversample_total=len(allrep), ext_summary=json.loads((ext / "summary.json").read_text(encoding="utf-8"))["stat"])
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    pack = ROOT / "data" / "ppe6" / "variants" / "kaggle" / "c6_extra_pack.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, "c6_extra/" + p.relative_to(out).as_posix())
    print(summ["c6"], f"| gói {pack.name} {pack.stat().st_size / 1e6:.1f} MB")


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["scan", "build", "pack"])
    ap.add_argument("--section", default="c6_ext", help="mục cấu hình: c6_ext (ủng, C6) hoặc c8_ext (găng, C8; chỉ scan, build)")
    args = ap.parse_args()
    global SECTION, OUT
    SECTION = args.section
    OUT = ROOT / cfg().get("out", "data/ppe6/c6")
    dict(scan=cmd_scan, build=cmd_build, pack=cmd_pack)[args.cmd](args)


if __name__ == "__main__":
    main()
