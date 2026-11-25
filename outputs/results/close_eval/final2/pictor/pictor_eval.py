"""Kiểm thử ngoài detector trên Pictor-PPE (RQ1), đánh giá cuối 26/11/2026 (c6_ft; C4 để đối chiếu). Bản chép từ final/pictor (16/11). Chỉ kiểm thử: không chọn ngưỡng, không huấn luyện.

Dữ liệu: data/ppe4/pictor_test (774 ảnh, đã loại ảnh trùng nhóm với dữ liệu huấn luyện ở 03_split_data; nhãn
worker->person, hat->helmet, vest->vest; không có găng, kính, ủng). Ultralytics ghi file .cache cạnh thư mục nhãn, nên
script chép ảnh và nhãn sang --work (thư mục tạm) rồi đánh giá trên bản chép, không ghi gì vào data/ppe4/. Bản chép
được so sha256 từng file nhãn với bản gốc trước khi chạy.

Tham số như test chính thức của C4 (04d_capture_val.py): imgsz 960, batch 4, conf và iou mặc định của model.val.
Chỉ báo các lớp có nhãn trên Pictor (person, helmet, vest). P, R là của Ultralytics (ở conf cho F1 trung bình lớn
nhất của mô hình đó, nên đây là số mô tả, không phải ngưỡng của hệ thống). Khoảng tin cậy 95% của AP50: bootstrap theo
ảnh (Pictor không có mã cảnh), 2.000 lần, hạt giống 0; AP tính bằng ap_from_tp (chép compute_ap của Ultralytics).

Chạy (từ thư mục gốc, .venv):
    python outputs/results/close_eval/final2/pictor/pictor_eval.py --work <thư mục tạm>
Ghi pictor_eval.json, pictor_eval.md cạnh script.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import yaml

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import ap_from_tp  # noqa: E402

SRC = ROOT / "data" / "ppe4" / "pictor_test"
MODELS = {
    "c6_ft (6 lớp, bản cuối 26/11)": "outputs/train/yolo11s_ppe6_c6_ft/weights/best.pt",
    "C4 (6 lớp, bản cuối 16/11)": "outputs/train/yolo11s_ppe6_c4/weights/best.pt",
    "r2 (4 lớp, đối chứng)": "outputs/train/yolo11s_ppe4_r2/weights/best.pt",
}
EVAL_CLASSES = ["person", "helmet", "vest"]
N_BOOT, SEED = 2000, 0


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def copy_set(work):
    dst = work / "pictor_test"
    for sub in ("images/test", "labels/test"):
        (dst / sub).mkdir(parents=True, exist_ok=True)
        for f in sorted((SRC / sub).iterdir()):
            t = dst / sub / f.name
            if not t.exists() or t.stat().st_size != f.stat().st_size:
                shutil.copy2(f, t)
    lab_src, lab_dst = sorted((SRC / "labels/test").iterdir()), sorted((dst / "labels/test").glob("*.txt"))
    assert [f.name for f in lab_src] == [f.name for f in lab_dst], "nhãn chép khác bản gốc"
    assert all(sha(a) == sha(b) for a, b in zip(lab_src, lab_dst)), "sha256 nhãn chép khác bản gốc"
    n_img = len(list((dst / "images/test").iterdir()))
    assert n_img == len(list((SRC / "images/test").iterdir())), "số ảnh chép khác bản gốc"
    return dst, n_img, len(lab_src)


def run_model(weights, data_yaml, work, tag):
    from ultralytics import YOLO
    from ultralytics.models.yolo.detect.val import DetectionValidator

    rows, original = [], DetectionValidator._process_batch

    def hooked(self, preds, batch):
        out = original(self, preds, batch)
        rows.append(dict(conf=preds["conf"].float().cpu().numpy(), cls=preds["cls"].cpu().numpy().astype(int),
                         tp=out["tp"], gc=batch["cls"].cpu().numpy().reshape(-1).astype(int)))
        return out

    DetectionValidator._process_batch = hooked
    try:
        model = YOLO(str(ROOT / weights))
        names = model.names
        m = model.val(data=str(data_yaml(names)), split="test", imgsz=960, batch=4, plots=False, device=0,
                      verbose=False, project=str(work / "runs"), name=tag, exist_ok=True)
    finally:
        DetectionValidator._process_batch = original
    inv = {v: k for k, v in names.items()}
    res = {}
    idx = list(m.box.ap_class_index)
    for c in EVAL_CLASSES:
        ci = inv[c]
        n_gt = int(sum((r["gc"] == ci).sum() for r in rows))
        if ci not in idx:
            res[c] = dict(n_gt=n_gt, note="Ultralytics không trả lớp này")
            continue
        j = idx.index(ci)
        p, r = float(m.box.p[j]), float(m.box.r[j])
        res[c] = dict(n_gt=n_gt, P=p, R=r, F1=float(2 * p * r / max(p + r, 1e-16)),
                      AP50=float(m.box.ap50[j]), AP50_95=float(m.box.ap[j]))
        # Bootstrap theo ảnh
        per = [(r_["tp"][r_["cls"] == ci], r_["conf"][r_["cls"] == ci], int((r_["gc"] == ci).sum())) for r_ in rows]
        tp = np.concatenate([x[0] for x in per]) if per else np.zeros((0, 10), bool)
        conf = np.concatenate([x[1] for x in per])
        img = np.concatenate([[i] * len(x[1]) for i, x in enumerate(per)] or [[]]).astype(int)
        gt = np.array([x[2] for x in per])
        ap_full = ap_from_tp(tp, conf, gt.sum())[0]
        rng = np.random.default_rng(SEED)
        boots = []
        for _ in range(N_BOOT):
            w_img = np.bincount(rng.integers(0, len(per), len(per)), minlength=len(per)).astype(float)
            boots.append(ap_from_tp(tp, conf, float((gt * w_img).sum()), w_img[img])[0])
        res[c].update(AP50_recomputed=float(ap_full), AP50_ci95=[float(np.percentile(boots, 2.5)),
                                                                   float(np.percentile(boots, 97.5))])
    speed = {k: float(v) for k, v in m.speed.items()}
    mean_ap50 = float(np.mean([res[c]["AP50"] for c in EVAL_CLASSES if "AP50" in res[c]]))
    mean_ap5095 = float(np.mean([res[c]["AP50_95"] for c in EVAL_CLASSES if "AP50_95" in res[c]]))
    return dict(weights=weights, sha256=sha(ROOT / weights), names={int(k): v for k, v in names.items()},
                n_images=len(rows), classes=res, mean_AP50_3_lop=mean_ap50, mean_AP50_95_3_lop=mean_ap5095,
                speed_ms_per_image=speed)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True, help="thư mục tạm để chép tập Pictor (không nằm trong data/)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    work = Path(args.work).resolve()
    assert ROOT / "data" not in work.parents, "--work không được nằm trong data/"
    dst, n_img, n_lab = copy_set(work)

    def data_yaml(names):
        p = work / f"pictor_{len(names)}cls.yaml"
        p.write_text(yaml.safe_dump(dict(path=str(dst), train="images/test", val="images/test", test="images/test",
                                         names={int(k): v for k, v in names.items()}), allow_unicode=True), encoding="utf-8")
        return p

    import torch
    import ultralytics
    out = dict(ngay="2026-11-26", muc_dich="kiểm thử ngoài RQ1; không chọn ngưỡng, không huấn luyện",
               du_lieu=dict(nguon=str(SRC.relative_to(ROOT)), anh=n_img, file_nhan=n_lab,
                            ghi_chu="đã loại ảnh trùng nhóm với dữ liệu huấn luyện (stats.csv: 774 external_test, 0 nhóm chung)"),
               tham_so=dict(imgsz=960, batch=4, conf="mặc định model.val", iou="mặc định model.val",
                            bootstrap=dict(don_vi="ảnh", lan=N_BOOT, seed=SEED)),
               moi_truong=dict(torch=torch.__version__, ultralytics=ultralytics.__version__,
                               gpu=torch.cuda.get_device_name(0)),
               models={})
    for i, (name, w) in enumerate(MODELS.items()):
        print("Đánh giá", name, w)
        out["models"][name] = run_model(w, data_yaml, work, f"m{i}")
    here = Path(__file__).parent
    (here / "pictor_eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    f = lambda x: f"{x:.3f}".replace(".", ",")  # noqa: E731
    lines = ["# Pictor-PPE: kiểm thử ngoài detector (RQ1)", "",
             f"{n_img} ảnh (`data/ppe4/pictor_test`, đã loại ảnh trùng với dữ liệu huấn luyện). imgsz 960, conf/iou mặc định "
             "`model.val`. Chỉ kiểm thử, không dùng để chọn ngưỡng. Pictor không có nhãn găng, kính, ủng. "
             "P, R ở conf cho F1 lớn nhất của từng mô hình (số mô tả, không phải ngưỡng hệ thống). "
             f"KTC 95% của AP50: bootstrap theo ảnh, {N_BOOT} lần.", ""]
    for name, r in out["models"].items():
        lines += [f"## {name}", "", f"`{r['weights']}`", "",
                  "| Lớp | Số hộp | P | R | F1 | AP50 [KTC 95%] | AP50-95 |", "|---|---|---|---|---|---|---|"]
        for c in EVAL_CLASSES:
            x = r["classes"][c]
            if "AP50" not in x:
                lines.append(f"| {c} | {x['n_gt']} | | | | {x.get('note', '')} | |")
                continue
            lo, hi = x["AP50_ci95"]
            lines.append(f"| {c} | {x['n_gt']} | {f(x['P'])} | {f(x['R'])} | {f(x['F1'])} | "
                         f"{f(x['AP50'])} [{f(lo)}; {f(hi)}] | {f(x['AP50_95'])} |")
        sp = r["speed_ms_per_image"]
        lines += ["", f"TB 3 lớp: AP50 {f(r['mean_AP50_3_lop'])}, AP50-95 {f(r['mean_AP50_95_3_lop'])}. "
                  f"Thời gian (ms/ảnh, batch 4, trong model.val): tiền xử lý {sp.get('preprocess', 0):.1f}, "
                  f"suy luận {sp.get('inference', 0):.1f}, hậu xử lý {sp.get('postprocess', 0):.1f}.", ""]
    (here / "pictor_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
