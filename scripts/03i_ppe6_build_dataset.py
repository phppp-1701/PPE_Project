"""Thử nghiệm 6 lớp: sinh bộ dữ liệu 6 lớp vào data/ppe6/dataset/. Không ghi đè ppe4, không sửa data/raw/.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03i_ppe6_build_dataset.py
    python scripts/03i_ppe6_build_dataset.py --check     # chỉ kiểm tra bộ đã sinh

Đầu vào: data/ppe4/{stats.csv,dataset/}, data/ppe6/review/{boxes,decisions_v2}.csv, data/ppe6/review/human_review.csv (nếu có,
do 03l tạo, luôn thắng quyết định của agent), data/ppe6/scene/scene_ids.csv, data/ppe6/eval/{scene_roles,chvg_split}.csv.

Lớp 0-3 giữ nguyên ppe4, 4 goggles, 5 boots. Ảnh là liên kết cứng tới ảnh ppe4, CHVG, không tốn thêm đĩa.
    images/train, labels/train                train 6 lớp
    images/<tập>_draft, labels/<tập>_draft    ứng viên val_new, test_new, chvg_glass_val, chvg_glass_test, nhãn theo agent
    val_new.txt, test_new.txt, chvg_glass_*.txt   chỉ ảnh đã có người chốt xong; rỗng cho tới khi nhập kết quả duyệt
    data.yaml, manifest.json, excluded.csv (lý do loại từng ảnh), eval_status.csv (trạng thái từng ảnh đánh giá)

Bộ CHVG chỉ dùng đo lớp kính. Kết thúc chạy kiểm tra rò rỉ ảnh, rò rỉ cảnh, mã lớp, tọa độ; có lỗi thì dừng.
"""

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.ppe6_data import NEW_CLASS, SAFE, blocks_train, check_label_rows, check_leaks, diverse_pick, effective, eval_status  # noqa: E402

PPE4 = ROOT / "data" / "ppe4" / "dataset"
BASE = ROOT / "data" / "ppe6"
OUT = BASE / "dataset"
OLD = ("person", "helmet", "vest", "gloves")
NAMES = ["person", "helmet", "vest", "gloves", "goggles", "boots"]
SETS = ("val_new", "test_new", "chvg_glass_val", "chvg_glass_test")


def rd(path):
    return list(csv.DictReader(path.open(encoding="utf-8")))


def load_human():
    path = BASE / "review" / "human_review.csv"
    last = {}
    if path.exists():
        for r in rd(path):
            last[r["box_id"]] = r
    return last


def load_added():
    """Hộp người duyệt vẽ thêm (03l): {file: [dict(target, cx, cy, w, h)]}."""
    path = BASE / "review" / "human_added.csv"
    out = defaultdict(list)
    if path.exists():
        for r in rd(path):
            out[r["file"]].append(r)
    return out


def load_scene_reject():
    """Cảnh người duyệt đánh dấu trùng train: loại khỏi đánh giá lớp mới."""
    path = BASE / "review" / "scene_review_done.csv"
    return {r["scene_id"] for r in rd(path) if r["same_as_train"].strip().lower() == "yes"} if path.exists() else set()


def chvg_boxes(cfg):
    """Hộp glass của CHVG trên ảnh sạch, nhãn agent theo kiểm tra sơ bộ. box_id = g<idx>."""
    unclear = set(cfg["chvg_precheck"]["unclear"].split())
    out = []
    size = 640
    for r in rd(BASE / "external" / "chvg" / "glass_order.csv"):
        x1, y1, x2, y2 = (float(r[k]) for k in ("x1", "y1", "x2", "y2"))
        out.append(dict(box_id=f"g{int(r['idx']):05d}", file=r["file"], target="goggles", source="chvg", cx=(x1 + x2) / 2 / size, cy=(y1 + y2) / 2 / size,
                        w=(x2 - x1) / size, h=(y2 - y1) / size, label="unclear" if r["idx"] in unclear else SAFE, note="", decided_by="agent"))
    return out


def yolo_line(cls, b):
    x1, x2 = max(float(b["cx"]) - float(b["w"]) / 2, 0.0), min(float(b["cx"]) + float(b["w"]) / 2, 1.0)
    y1, y2 = max(float(b["cy"]) - float(b["h"]) / 2, 0.0), min(float(b["cy"]) + float(b["h"]) / 2, 1.0)
    return f"{cls} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}"


def write_item(name, file, src_img, lines):
    folder = OUT / "images" / name
    os.link(src_img, folder / file)
    (OUT / "labels" / name / f"{Path(file).stem}.txt").write_text("".join(x + "\n" for x in lines), encoding="utf-8", newline="\n")


def count(rows_by_set, source_of, scene):
    table = {}
    for name, items in sorted(rows_by_set.items()):
        t = dict(images=Counter(), boxes=Counter(), scenes=defaultdict(set))
        for f, lines in items.items():
            o = source_of[f]
            t["images"][o] += 1
            for x in lines:
                c = NAMES[int(x.split()[0])]
                t["boxes"][f"{c}|{o}"] += 1
                t["scenes"][f"{c}|{o}"].add(scene[f])
        table[name] = dict(images=dict(sorted(t["images"].items())), boxes=dict(sorted(t["boxes"].items())), scenes={k: len(v) for k, v in sorted(t["scenes"].items())})
    return table


def validate(sets, scene, ppe4_split, label_dirs):
    bad = check_leaks(sets, scene, ppe4_split)
    for name, folder in label_dirs.items():
        for p in folder.glob("*.txt"):
            bad += [f"{name}/{p.name}: {e}" for e in check_label_rows(p.read_text(encoding="utf-8").splitlines())]
    return bad


def build(cfg):
    stats = [r for r in rd(ROOT / "data" / "ppe4" / "stats.csv") if r["split"] != "external_test"]
    by_image = {r["image"]: r for r in stats}
    scene = {r["file"]: r["scene_id"] for r in rd(BASE / "scene" / "scene_ids.csv")}
    roles = {r["scene_id"]: r["role"] for r in rd(BASE / "eval" / "scene_roles.csv")}
    agent = {r["box_id"]: r for r in rd(BASE / "review" / "decisions_v2.csv")}
    human = load_human()
    boxes = defaultdict(list)
    for b in rd(BASE / "review" / "boxes.csv"):
        r = by_image.get(b["image"])
        if r is None:
            continue
        lab, note, src = effective(agent[b["box_id"]], human.get(b["box_id"]))
        if b["box_id"] in human and human[b["box_id"]].get("new_cx"):
            hb = human[b["box_id"]]
            b = dict(b, cx=hb["new_cx"], cy=hb["new_cy"], w=hb["new_w"], h=hb["new_h"])
        boxes[r["file"]].append(dict(b, label=lab, note=note, src=src))
    for b in chvg_boxes(cfg):
        h = human.get(b["box_id"])
        lab, note, src = effective(dict(label=b["label"], note="", decided_by="agent"), h)
        boxes[b["file"]].append(dict(b, label=lab, note=note, src=src))

    for f, rows in load_added().items():
        boxes[f] += [dict(r, label=SAFE, note="", src="human", box_id="") for r in rows]
    rejected_scenes = load_scene_reject()

    def final_status(f, base):
        mark = human.get("image:" + f)
        if scene[f] in rejected_scenes or (mark and mark["after"] == "reject"):
            return "rejected"
        return base

    # Phân vai từng ảnh ppe4
    train, excluded, eval_files = [], [], defaultdict(list)
    want = {"val_new": "val", "test_new": "test"}
    for r in sorted(stats, key=lambda x: x["file"]):
        f, role = r["file"], roles.get(scene[r["file"]])
        if role:
            if r["source"] != "chv" and r["split"] in ("train", want[role]):
                eval_files[role].append(r)
            else:
                excluded.append((f, r["split"], "ppe4_only" if r["split"] != "train" else "chv_no_new_labels"))
            continue
        if r["split"] != "train":
            excluded.append((f, r["split"], "ppe4_only"))
        elif r["source"] == "chv":
            excluded.append((f, "train", "chv_no_new_labels"))
        elif any(blocks_train(b["label"], b["note"], b["target"]) for b in boxes[f]):
            excluded.append((f, "train", "unclear_box"))
        else:
            train.append(r)

    # Giới hạn cảnh lặp ở train
    z = np.load(BASE / "scene" / "features.npz", allow_pickle=False)
    index = {k: i for i, k in enumerate(z["key"].tolist())}
    emb = z["emb"]
    per_scene = defaultdict(list)
    for r in train:
        per_scene[scene[r["file"]]].append(r["file"])
    drop = set()
    capped = {}
    for s, files in sorted(per_scene.items()):
        if s in cfg["repeat_scenes"] and len(files) > cfg["train_scene_cap"]:
            files = sorted(files)
            keep = set(diverse_pick(emb[[index[f] for f in files]], files, cfg["train_scene_cap"], cfg["eval"]["seed"]))
            drop |= set(files) - keep
            capped[s] = len(files)
    excluded += [(f, "train", "scene_cap") for f in sorted(drop)]
    train = [r for r in train if r["file"] not in drop]

    if OUT.exists():
        shutil.rmtree(OUT)
    names = ["train"] + [f"{s}_draft" for s in SETS]
    for n in names:
        (OUT / "images" / n).mkdir(parents=True)
        (OUT / "labels" / n).mkdir(parents=True)

    def lines_of(r):
        src = PPE4 / "labels" / r["split"] / f"{Path(r['file']).stem}.txt"
        old = [x for x in src.read_text(encoding="utf-8").splitlines() if x.strip()]
        new = [yolo_line(NEW_CLASS[b["target"]], b) for b in boxes[r["file"]] if b["label"] == SAFE]
        return old + new

    written = defaultdict(dict)
    source_of = {r["file"]: r["source"] for r in stats}
    for r in train:
        written["train"][r["file"]] = lines_of(r)
        write_item("train", r["file"], PPE4 / "images" / r["split"] / r["file"], written["train"][r["file"]])
    status_rows, ready = [], defaultdict(list)
    for role in ("val_new", "test_new"):
        for r in eval_files[role]:
            n = f"{role}_draft"
            written[n][r["file"]] = lines_of(r)
            write_item(n, r["file"], PPE4 / "images" / r["split"] / r["file"], written[n][r["file"]])
            st = final_status(r["file"], eval_status([(b["label"], b["src"]) for b in boxes[r["file"]]]))
            status_rows.append((r["file"], role, r["source"], r["split"], scene[r["file"]], st, sum(b["src"] != "human" for b in boxes[r["file"]])))
            if st == "ready":
                ready[role].append(r["file"])
    for r in rd(BASE / "eval" / "chvg_split.csv"):
        f, n = r["file"], f"{r['split']}_draft"
        source_of[f] = "chvg"
        scene[f] = "chvg_" + r["scene"]
        written[n][f] = [yolo_line(4, b) for b in boxes[f] if b["label"] == SAFE]
        write_item(n, f, BASE / "external" / "chvg" / "extracted" / f.replace("chvg__", ""), written[n][f])
        # CHVG cần người xem cả ảnh không có hộp glass, nên ảnh chưa có dấu người duyệt luôn là pending.
        seen = human.get("image:" + f)
        st = final_status(f, "ready" if seen and eval_status([(b["label"], b["src"]) for b in boxes[f]]) == "ready" else "pending")
        status_rows.append((f, r["split"], "chvg", "external", scene[f], st, sum(b["src"] != "human" for b in boxes[f])))
        if st == "ready":
            ready[r["split"]].append(f)

    for s in SETS:
        (OUT / f"{s}.txt").write_text("".join(f"./images/{s}_draft/{f}\n" for f in sorted(ready[s])), encoding="utf-8", newline="\n")
    (OUT / "data.yaml").write_text("# Bộ 6 lớp thử nghiệm, tạo bởi scripts/03i_ppe6_build_dataset.py. val rỗng cho tới khi người duyệt xong.\n"
                                   "train: images/train\nval: val_new.txt\ntest: test_new.txt\n"
                                   + "names:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(NAMES)), encoding="utf-8", newline="\n")
    with (OUT / "excluded.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["file", "ppe4_split", "reason"])
        w.writerows(sorted(excluded))
    with (OUT / "eval_status.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["file", "set", "source", "ppe4_split", "scene", "status", "pending_boxes"])
        w.writerows(sorted(status_rows))

    all_stats = {r["file"]: r for r in stats}
    lost = defaultdict(Counter)
    for f, sp, why in excluded:
        if sp == "train":
            lost[why]["images"] += 1
            for c in OLD:
                lost[why][c] += int(all_stats[f]["n_" + c])
    for role in ("val_new", "test_new"):
        for r in eval_files[role]:
            if r["split"] == "train":
                lost["eval_scene"]["images"] += 1
                for c in OLD:
                    lost["eval_scene"][c] += int(r["n_" + c])
    ppe4_train = [r for r in stats if r["split"] == "train"]
    manifest = dict(
        commit=subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
        seed=cfg["eval"]["seed"], scene=dict((k, cfg["scene"][k]) for k in ("phash_max", "emb_min", "hist_min", "emb_strong")),
        target_boots=cfg["eval"]["target_boots"], cp_share=cfg["eval"]["cp_share"], max_scene_boots=cfg["eval"]["max_scene_boots"],
        train_scene_cap=cfg["train_scene_cap"], repeat_scenes=cfg["repeat_scenes"], capped_scenes=capped, min_side_px=cfg["review"]["min_side_px"],
        ppe4_train=dict(images=len(ppe4_train), **{c: sum(int(r["n_" + c]) for r in ppe4_train) for c in OLD}),
        lost_from_train={k: dict(v) for k, v in sorted(lost.items())},
        counts=count(written, source_of, scene),
        eval_status={k: dict(v) for k, v in sorted(_status(status_rows).items())},
        human_reviewed_boxes=sum(1 for k in human if not k.startswith("image:")),
    )
    h = hashlib.sha256()
    for n in sorted(written):
        for f in sorted(written[n]):
            h.update(f"{n}|{f}|{'|'.join(written[n][f])}\n".encode())
    for row in sorted(excluded):
        h.update("|".join(row).encode())
    manifest["content_hash"] = h.hexdigest()
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    (OUT / "scene_map.json").write_text(json.dumps({f: scene[f] for v in written.values() for f in v}, sort_keys=True), encoding="utf-8", newline="\n")
    print(json.dumps({k: manifest[k] for k in ("ppe4_train", "lost_from_train", "eval_status", "content_hash", "capped_scenes")}, ensure_ascii=False))
    return manifest


def _status(rows):
    c = defaultdict(Counter)
    for r in rows:
        c[r[1]][r[5]] += 1
    return c


def check():
    scene = json.loads((OUT / "scene_map.json").read_text(encoding="utf-8"))
    split = {r["file"]: r["split"] for r in rd(ROOT / "data" / "ppe4" / "stats.csv")}
    sets = {p.name: {x.name for x in p.iterdir()} for p in (OUT / "images").iterdir()}
    for name in sets:
        for f in sets[name]:
            split.setdefault(f, "external")
    bad = validate(sets, scene, split, {p.name: p for p in (OUT / "labels").iterdir()})
    for name, files in sets.items():
        stems = {Path(f).stem for f in files}
        labs = {p.stem for p in (OUT / "labels" / name).glob("*.txt")}
        if stems != labs:
            bad.append(f"{name}: ảnh và nhãn không khớp")
    st = {(r["file"], r["set"]): r["status"] for r in rd(OUT / "eval_status.csv")}
    for s in SETS:
        for line in (OUT / f"{s}.txt").read_text(encoding="utf-8").splitlines():
            if st.get((Path(line).name, s)) != "ready":
                bad.append(f"{s}: ảnh chưa chốt nằm trong danh sách: {line}")
    print("Kiểm tra:", {k: len(v) for k, v in sorted(sets.items())}, "lỗi", len(bad))
    for b in bad[:20]:
        print(" ", b)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if not args.check:
        build(yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8")))
    if check():
        sys.exit(1)


if __name__ == "__main__":
    main()
