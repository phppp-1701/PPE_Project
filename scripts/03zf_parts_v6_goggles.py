"""B1 (docs/experiments/2026-11-25_close_range_fixes.md): bộ ảnh cắt phân loại bộ phận bản 6 — thêm kính bảo hộ.

Gốc = data/ppe6/parts (bản 4, train + val) chép nguyên. Thêm vào **train/goggles** ảnh cắt mắt từ bộ Roboflow công khai:
- data/raw/goggles_sg, lớp `eyes_with_goggles` (mọi hộp; nhãn gốc của bộ dữ liệu, người dùng kiểm định mẫu 24 hộp, tờ 2);
- data/raw/goggles_safety (`Safety Glasses`) và data/raw/goggles_workplace (`Glass`): chỉ hộp người dùng giữ ở tờ 1
  (outputs/results/parts_cls/b1_review/quyet_dinh.csv).
Bộ PPEs (data/raw/goggles_ppes) bỏ theo quyết định của người dùng (25/11/2026: nhiều kính cận thường).
Ảnh gần trùng ảnh đánh giá (ppe4 val/test, Pictor, test_new; pHash, `parts.v6.dedup_hamming`) và ảnh gần trùng nhau trong
nguồn mới bị bỏ. Mỗi hộp: một ảnh cắt theo hộp (xê dịch như bản 2) và một ảnh cắt theo keypoint mắt (`match_anchor`, hình
học ngẫu nhiên `kp_geom.eye_s`), tăng cường `parts.aug`; như bản 5. Val giữ nguyên bản 4.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03zf_parts_v6_goggles.py

Ghi data/ppe6/parts_v6/{train,val}/<lớp>/, data/ppe6/parts_v6/added_meta.csv, summary.json và gói
data/ppe6/variants/kaggle/parts_v6_pack.zip (cho 04g trên Kaggle). Không sửa data/raw.
"""

import csv
import importlib.util
import json
import random
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
_spec = importlib.util.spec_from_file_location("p03y", ROOT / "scripts" / "03y_ppe6_part_crops.py")
Y = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Y)

SRC = {"goggles_sg": "eyes_with_goggles", "goggles_safety": "Safety Glasses", "goggles_workplace": "Glass"}
REVIEWED = {"goggles_safety", "goggles_workplace"}       # chỉ giữ hộp người dùng chọn ở tờ 1
REVIEW = ROOT / "outputs" / "results" / "parts_cls" / "b1_review"


def kept_reviewed():
    """{(nguồn, đường dẫn ảnh, dòng nhãn)} người dùng giữ (tờ 1)."""
    keep = set()
    for r in csv.DictReader((REVIEW / "quyet_dinh.csv").open(encoding="utf-8")):
        if r["to"] == "1" and r["giu"] == "1":
            keep.add((r["nguon"], Path(r["anh"]).as_posix(), int(r["dong_nhan"])))
    return keep


def items():
    """[(nguồn, ảnh, dòng nhãn, hộp xyxy pixel)] hộp kính bảo hộ của các nguồn dùng."""
    keep = kept_reviewed()
    out = []
    for src, cname in SRC.items():
        d = ROOT / "data" / "raw" / src
        names = yaml.safe_load((d / "data.yaml").read_text(encoding="utf-8"))["names"]
        ci = names.index(cname)
        for lab in sorted(d.rglob("labels/*.txt")):
            img = next(iter(lab.parent.parent.joinpath("images").glob(lab.stem + ".*")), None)
            if img is None:
                continue
            rel = img.relative_to(ROOT).as_posix()
            for i, line in enumerate(lab.read_text().splitlines()):
                r = line.split()
                if len(r) != 5 or int(r[0]) != ci:
                    continue
                if src in REVIEWED and (src, rel, i) not in keep:
                    continue
                out.append((src, rel, i, tuple(map(float, r[1:]))))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    from ultralytics import YOLO

    from ppe import load_config
    from ppe.parts import cut, match_anchor
    from ppe.pose import PoseEstimator

    pc = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["parts"]
    v6 = pc["v6"]
    rng = random.Random(pc["seed"])
    base, out = ROOT / v6["base_from"], ROOT / v6["out"]
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(base, out, ignore=shutil.ignore_patterns("*.json", "*.csv", "*.zip"))
    its = items()
    print("hộp kính nguồn mới:", dict(Counter(s for s, *_ in its)), flush=True)
    ev, n_ev = Y.eval_hashes()
    seen, info, rows = [], Counter(), []
    pcfg = load_config()
    person_model, pose = YOLO(ROOT / pcfg["pose"]["weights"]), PoseEstimator(pcfg, ROOT)
    kp_conf, dev = pcfg["part_cls"]["kp_conf"], pcfg["detector"]["device"]
    kg, j = pc["kp_geom"], pc["box_jitter"]
    dst = out / "train" / "goggles"
    by_img = {}
    for src, rel, i, b in its:
        by_img.setdefault((src, rel), []).append((i, b))
    n = 0
    for (src, rel), boxes in sorted(by_img.items()):
        im = cv2.imdecode(np.fromfile(str(ROOT / rel), dtype=np.uint8), cv2.IMREAD_COLOR)
        if im is None:
            info["anh_loi"] += 1
            continue
        h = Y.phash(im)
        if Y.hamming_min(h, ev) <= v6["dedup_hamming"]:
            info["bo_gan_trung_anh_danh_gia"] += 1
            continue
        if seen and Y.hamming_min(h, np.array(seen, dtype=np.uint64)) <= v6["dedup_hamming"]:
            info["bo_gan_trung_nguon_moi"] += 1
            continue
        seen.append(h)
        H, W = im.shape[:2]
        people = Y.people_boxes_kps(im, person_model, pose, dev)
        kps = [k for _, k in people]
        for i, (cx, cy, bw, bh) in boxes:
            bx = ((cx - bw / 2) * W, (cy - bh / 2) * H, (cx + bw / 2) * W, (cy + bh / 2) * H)
            for kind in ("box", "kp"):
                if kind == "box":
                    box = Y.square(bx, rng.uniform(*j["context"]), (rng.uniform(-j["shift"], j["shift"]), rng.uniform(-j["shift"], j["shift"])))
                    crop = cut(im, box, pc["min_px"] // 2) if box[2] >= pc["min_px"] else None
                else:
                    mk = match_anchor(kps, "goggles", bx, kp_conf)
                    if mk is None:
                        info["kp_khong_ghep"] += 1
                        continue
                    crop = cut(im, mk(dict(s=rng.uniform(*kg["eye_s"]))), pc["min_px"])
                if crop is None:
                    info[f"{kind}_qua_nho_hoac_mep"] += 1
                    continue
                crop = Y.augment(Y.fit(crop, pc), rng, pc["aug"])
                dst.mkdir(parents=True, exist_ok=True)
                f = dst / f"{src}_{kind}_v6_{n:05d}.jpg"
                n += 1
                cv2.imwrite(str(f), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
                rows.append(dict(file=Y.relp(f), src=src, kind=kind, image=rel, line=i))
                info[f"them_{src}_{kind}"] += 1
    Y.write_csv(out / "added_meta.csv", rows, ["file", "src", "kind", "image", "line"])
    counts = {sp: {c.name: len(list(c.glob("*.jpg"))) for c in sorted((out / sp).iterdir()) if c.is_dir()} for sp in ("train", "val")}
    summary = dict(ngay=__import__("datetime").date.today().isoformat(), base=v6["base_from"], them=len(rows),
                   chi_tiet=dict(info), anh_danh_gia_so_sanh=n_ev, so_anh=counts,
                   ghi_chu="Chỉ thêm train/goggles; val như bản 4. Nhãn: nhãn gốc bộ dữ liệu (goggles_sg, người dùng kiểm "
                           "định mẫu) và hộp người dùng giữ (goggles_safety, goggles_workplace).")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    pack = ROOT / v6["pack"]
    pack.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as z:
        for f in sorted(out.rglob("*.jpg")):
            z.write(f, f.relative_to(out).as_posix())
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("Gói", pack.relative_to(ROOT), pack.stat().st_size, "byte")


if __name__ == "__main__":
    main()
