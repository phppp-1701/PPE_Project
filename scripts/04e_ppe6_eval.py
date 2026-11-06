"""Bộ đánh giá duy nhất cho baseline và ứng viên, đọc capture.npz của 04d. Chỉ dùng val cho tới khi chốt bản.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04e_ppe6_eval.py old --baseline outputs/results/ppe6_eval/r2_ppe4val --candidate outputs/results/ppe6_eval/r1_ppe4val --name r1_vs_r2
    python scripts/04e_ppe6_eval.py new --capture <thư mục capture> --name ... # lớp mới, xử lý hộp `ignore`

`old`: 4 lớp cũ trên val gốc và val sạch theo cảnh, ứng viên trừ baseline, bootstrap ghép cặp theo cảnh (cùng mẫu cảnh cho hai mô hình).
Val sạch = ảnh ppe4 val mà cảnh không có ảnh ppe4 train; C0, C1, C2 đều là tập con của ppe4 train nên phần này sạch với mọi ứng viên, theo ngưỡng hiện tại.
Quyết định theo val sạch; val gốc chỉ để đối chiếu. Mốc ở configs/ppe6.yaml mục `decision`.
Kết luận: dat; chua_du_bang_chung (quá mốc nhưng khoảng tin cậy còn chứa mức đạt, không tính là đạt); khong_dat; han_che_gang (chỉ găng không đạt).
`new`: kính, ủng; dự đoán sai trùng vùng `ignore` không tính đúng, không tính sai. Bootstrap theo cảnh.
AP và tp là của Ultralytics (tp bắt từ validator, AP chép compute_ap). Ghi outputs/results/ppe6_eval/<name>.json.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import ap_from_tp, ignore_filter, old_decision  # noqa: E402

CLASSES = ["person", "helmet", "vest", "gloves", "goggles", "boots"]
OUT = ROOT / "outputs" / "results" / "ppe6_eval"


def load(path):
    z = np.load(Path(path) / "capture.npz", allow_pickle=False)
    return {k: z[k] for k in z.files}


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8")))


def scenes():
    stats = rd(ROOT / "data" / "ppe4" / "stats.csv")
    scene = {r["file"]: r["scene_id"] for r in rd(ROOT / "data" / "ppe6" / "scene" / "scene_ids.csv")}
    return scene, {scene[r["file"]] for r in stats if r["split"] == "train"}


def class_ap(z, weight, classes):
    w, g = weight[z["img"]], weight[z["gimg"]]
    out = {}
    for c in classes:
        m = (z["cls"] == c) & (w > 0)
        out[c] = ap_from_tp(z["tp"][m], z["conf"][m], g[z["gcls"] == c].sum(), w[m])[0]
    return out


def resample(groups, keys, n, rng):
    w = np.zeros(n)
    for k in rng.integers(0, len(keys), len(keys)):
        w[groups[keys[k]]] += 1
    return w


def ci(v):
    return [round(float(x), 4) for x in np.percentile(v, [2.5, 97.5])]


def compare_old(a, b, cfg):
    files = a["files"].tolist()
    if files != b["files"].tolist():
        order = {f: i for i, f in enumerate(b["files"].tolist())}
        if sorted(order) != sorted(files):
            sys.exit("Hai capture không cùng tập ảnh.")
        b = dict(b, img=np.array([files.index(b["files"][i]) for i in b["img"]]), gimg=np.array([files.index(b["files"][i]) for i in b["gimg"]]))
    scene, train = scenes()
    clean = np.array([scene[f] not in train for f in files], dtype=float)
    groups = defaultdict(list)
    for i, f in enumerate(files):
        groups[scene[f]].append(i)
    keys = sorted(groups)
    cl = list(range(4))
    rng = np.random.default_rng(cfg["seed"])
    res = dict(images=len(files), clean_images=int(clean.sum()), scenes=len(keys), n_boot=cfg["n_boot"], note="sạch theo ngưỡng hiện tại; số rò rỉ đo được là mức thấp")
    boot = defaultdict(list)
    for _ in range(cfg["n_boot"]):
        w = resample(groups, keys, len(files), rng)
        for name, ww in (("full", w), ("clean", w * clean)):
            pa, pb = class_ap(a, ww, cl), class_ap(b, ww, cl)
            for c in cl:
                boot[(name, c, "a")].append(pa[c])
                boot[(name, c, "b")].append(pb[c])
                boot[(name, c, "d")].append(pb[c] - pa[c])
            boot[(name, "mean", "d")].append(np.mean([pb[c] - pa[c] for c in cl]))
            boot[(name, "mean", "a")].append(np.mean([pa[c] for c in cl]))
            boot[(name, "mean", "b")].append(np.mean([pb[c] for c in cl]))
    for name, ww in (("full", np.ones(len(files))), ("clean", clean)):
        pa, pb = class_ap(a, ww, cl), class_ap(b, ww, cl)
        t = {}
        for c in cl:
            t[CLASSES[c]] = dict(baseline=round(pa[c], 4), candidate=round(pb[c], 4), diff=round(pb[c] - pa[c], 4), ci_baseline=ci(boot[(name, c, "a")]), ci_candidate=ci(boot[(name, c, "b")]), ci_diff=ci(boot[(name, c, "d")]))
        ma, mb = float(np.mean(list(pa.values()))), float(np.mean(list(pb.values())))
        t["mean"] = dict(baseline=round(ma, 4), candidate=round(mb, 4), diff=round(mb - ma, 4), ci_baseline=ci(boot[(name, "mean", "a")]), ci_candidate=ci(boot[(name, "mean", "b")]), ci_diff=ci(boot[(name, "mean", "d")]))
        res[name] = t
    res["decision"] = old_decision(res["clean"], CLASSES[:4], cfg["max_mean_drop"], cfg["max_class_drop"])
    return res


def load_ignore():
    """Hộp người duyệt chốt `ignore`: {file: [(lớp, cx, cy, w, h)]}."""
    path = ROOT / "data" / "ppe6" / "review" / "human_review.csv"
    out = defaultdict(list)
    if not path.exists():
        return out
    last = {r["box_id"]: r for r in rd(path)}
    index = {}
    for g in (ROOT / "data" / "ppe6" / "review" / "cvat_pack").iterdir():
        if (g / "index.csv").exists():
            index.update({r["box_id"]: r for r in rd(g / "index.csv")})
    for k, r in last.items():
        if r["after"] == "ignore" and k in index:
            b = index[k]
            out[b["file"]].append((4 if b["target"] == "goggles" else 5, float(b["cx"]), float(b["cy"]), float(b["w"]), float(b["h"])))
    return out


def to_canvas(box, ori, ratio_pad):
    """Hộp chuẩn hóa ở ảnh gốc sang không gian letterbox của capture."""
    _, cx, cy, w, h = box
    oh, ow = ori
    gain, px, py = ratio_pad
    return ((cx - w / 2) * ow * gain + px, (cy - h / 2) * oh * gain + py, (cx + w / 2) * ow * gain + px, (cy + h / 2) * oh * gain + py)


def apply_ignore(z, ignore):
    """Bỏ dự đoán sai trùng vùng ignore. Hộp ignore không phải nhãn nên không làm tăng số nhãn."""
    keep = np.ones(len(z["conf"]), dtype=bool)
    for i, f in enumerate(z["files"].tolist()):
        if f not in ignore:
            continue
        m = np.nonzero(z["img"] == i)[0]
        reg = [(b[0], *to_canvas(b, z["ori"][i], z["ratio_pad"][i])) for b in ignore[f]]
        keep[m] = ignore_filter(z["tp"][m], z["box"][m], z["cls"][m], reg)
    return {k: (v[keep] if k in ("img", "box", "conf", "cls", "tp") else v) for k, v in z.items()}, int((~keep).sum())


def eval_new(z, cfg):
    z, dropped = apply_ignore(z, load_ignore())
    scene, _ = scenes()
    files = z["files"].tolist()
    groups = defaultdict(list)
    for i, f in enumerate(files):
        groups[scene.get(f, f)].append(i)
    keys = sorted(groups)
    cl = [4, 5]
    point = class_ap(z, np.ones(len(files)), cl)
    rng = np.random.default_rng(cfg["seed"])
    boot = defaultdict(list)
    for _ in range(cfg["n_boot"]):
        p = class_ap(z, resample(groups, keys, len(files), rng), cl)
        for c in cl:
            boot[c].append(p[c])
    res = dict(images=len(files), scenes=len(keys), ignored_predictions=dropped, classes={})
    for c in cl:
        lo, hi = ci(boot[c])
        res["classes"][CLASSES[c]] = dict(gt=int((z["gcls"] == c).sum()), map50=round(point[c], 4), ci=[lo, hi], enough_evidence=not (lo < cfg["new_class_target"] < hi))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["old", "new"])
    ap.add_argument("--baseline")
    ap.add_argument("--candidate")
    ap.add_argument("--capture")
    ap.add_argument("--name", required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["decision"]
    res = compare_old(load(args.baseline), load(args.candidate), cfg) if args.mode == "old" else eval_new(load(args.capture), cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
