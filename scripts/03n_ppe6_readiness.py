"""Thử nghiệm 6 lớp: chấm các quy tắc sau duyệt và kiểm tra sẵn sàng train. Không sửa bộ dữ liệu đã có.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/03n_ppe6_readiness.py gates                 # chấm P0a, P2, P2_chv theo quy tắc đã khóa
    python scripts/03n_ppe6_readiness.py scope                 # tính ngưỡng người đủ lớn từ cột person_ok; --write ghi vào config
    python scripts/03n_ppe6_readiness.py monitor --variant c2  # dựng val_monitor từ nhãn đã duyệt, ghi gói <c>_final_pack.zip
    python scripts/03n_ppe6_readiness.py checklist             # in checklist, thoát mã 1 nếu chưa sẵn sàng

Quy tắc: docs/experiments/2026-11-06_ppe6_plan.md mục "Quyết định train và quy tắc sau duyệt". Mốc: configs/ppe6.yaml mục `gates`.
`monitor` báo lỗi nếu lớp mới trong val_monitor còn dùng nhãn agent. Gói cuối có ready.json; 04_train từ chối train thật nếu thiếu.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe.machine_labels import MACHINE_CHV, MACHINE_TRAIN, human_box_labels  # noqa: E402
from ppe.ppe6_data import check_monitor, scope_threshold, stratified_rate, wilson  # noqa: E402

BASE = ROOT / "data" / "ppe6"
REVIEW = BASE / "review"
PACK = REVIEW / "cvat_pack"
KAGGLE = BASE / "variants" / "kaggle"
CONFIG = ROOT / "configs" / "ppe6.yaml"
OLD = ("person", "helmet", "vest", "gloves")


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def cfg():
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def last_review():
    """Nhãn người hiệu lực: human_review.csv và các file duyệt mới (audit, rest, boots_v3), không nhãn máy.
    `before` là nhãn agent cũ trong file ánh xạ của gói mù, chỉ để đo bất đồng agent, người."""
    out = {r["box_id"]: r for r in rd(REVIEW / "human_review.csv")} if (REVIEW / "human_review.csv").exists() else {}
    agent = {r["box_id"]: r["agent_label"] for p in (REVIEW / "cvat_pack_blind" / "_private").glob("task_*_items.csv") for r in rd(p)}
    for k, r in human_box_labels(REVIEW).items():
        out[k] = dict(r, before=r.get("before") or agent.get(k, ""))
    return out


def pct(x):
    return f"{100 * x:.1f}%"


def strata_of_chv(files):
    """Tầng theo chiều cao người lớn nhất, như lúc lấy mẫu ở 03k."""
    out = defaultdict(list)
    for f in sorted(files):
        p = ROOT / "data" / "ppe4" / "dataset" / "labels" / "train" / f"{Path(f).stem}.txt"
        hs = [float(x.split()[4]) for x in p.read_text(encoding="utf-8").splitlines() if x.startswith("0 ")]
        top = max(hs, default=0)
        out["nho" if top < 0.3 else "vua" if top < 0.6 else "lon"].append(f)
    return out


def gate_p0a(c):
    """Trả về (trạng thái, chi tiết). Trạng thái: pending, pass, action, stop."""
    index = rd(PACK / "P0a" / "index.csv")
    last = last_review()
    done = [last[r["box_id"]] for r in index if r["box_id"] in last]
    if len(done) < len(index):
        return "pending", f"mới duyệt {len(done)}/{len(index)} hộp"
    diff = sum(r["before"] != r["after"] for r in done)
    rate = diff / len(done)
    by = {}
    for s in sorted({r["source"] for r in done}):
        v = [r for r in done if r["source"] == s]
        by[s] = f"{sum(r['before'] != r['after'] for r in v)}/{len(v)}"
    counts = {}
    for name in ("val_new", "test_new"):
        lines = (BASE / "dataset" / f"{name}.txt").read_text(encoding="utf-8").splitlines()
        n = 0
        for x in lines:
            lab = BASE / "dataset" / "labels" / f"{name}_draft" / f"{Path(x).stem}.txt"
            n += sum(1 for row in lab.read_text(encoding="utf-8").splitlines() if row.startswith("5 "))
        counts[name] = n
    detail = f"bất đồng {diff}/{len(done)} = {pct(rate)}, theo nguồn {by}; ủng đã chốt {counts}"
    if min(counts.values()) < c["min_boots_eval"]:
        return "stop", detail + f". Dưới {c['min_boots_eval']} hộp: dừng, chờ người dùng."
    if rate >= c["max_disagreement"]:
        return "action", detail + ". Đề xuất lấy mẫu kiểm tra nhãn train, tách theo nguồn."
    return "pass", detail


def gate_p2(c):
    sample = {r["box_id"]: r for r in rd(REVIEW / "p2_shoe_sample.csv")}
    last = last_review()
    done = {k: last[k] for k in sample if k in last}
    src = "người"
    if len(done) < len(sample):
        mc = {r["box_id"]: dict(r, after=r["decision"]) for r in rd(REVIEW / MACHINE_TRAIN)} if (REVIEW / MACHINE_TRAIN).exists() else {}
        if all(k in mc for k in sample):
            done, src = {k: mc[k] for k in sample}, "NHÃN MÁY machine_pass_c, chưa kiểm định"
    if len(done) < len(sample):
        return "pending", f"mới duyệt {len(done)}/{len(sample)} hộp giày"
    noise = json.loads((ROOT / "outputs" / "results" / "ppe6_noise" / "noise.json").read_text(encoding="utf-8"))["strata"]
    rows = []
    for st, n_pop in sorted(noise.items()):
        ks = [done[k]["after"] == "safety" for k, v in sample.items() if v["stratum"] == st]
        rows.append((n_pop, sum(ks), len(ks)))
    p, lo, hi = stratified_rate(rows)
    k = sum(r[1] for r in rows)
    n = sum(r[2] for r in rows)
    raw = wilson(k, n)
    detail = f"[{src}] có trọng số {pct(p)} (KTC 95% {pct(lo)}; {pct(hi)}), thô {k}/{n} = {pct(k / n)} (KTC {pct(raw[1])}; {pct(raw[2])})"
    if p >= c["min_shoe_rate"]:
        return "action", detail + ". Đề xuất che vùng thay vì giữ làm nền, tạo phiên bản train mới."
    return "pass", detail


def gate_chv(c, full):
    sample = {r["file"]: r["stratum"] for r in rd(PACK / "P2_chv" / "sample.csv")}
    src = "người"
    if (REVIEW / "chv_boots_seen.csv").exists():
        seen = {r["box_id"].replace("image:", ""): r for r in rd(REVIEW / "chv_boots_seen.csv") if r["box_id"].startswith("image:")}
        seen = {f: r for f, r in seen.items() if r["after"] == "checked"}
        added = Counter(r["file"] for r in rd(REVIEW / "chv_boots_added.csv"))
    elif (REVIEW / MACHINE_CHV).exists():
        mc = rd(REVIEW / MACHINE_CHV)
        seen = {r["file"]: r for r in mc}
        added = Counter(r["file"] for r in mc if r["image_result"] == "missing_box")
        src = "NHÃN MÁY machine_pass_c, chưa kiểm định"
    else:
        seen, added = {}, Counter()
    if not sample:
        return "pending", "chưa có mẫu"
    if len([f for f in sample if f in seen]) < len(sample):
        return "pending", f"mới xem {len([f for f in sample if f in seen])}/{len(sample)} ảnh"
    pop = strata_of_chv(p.name for p in (BASE / "dataset_c2" / "images" / "train").iterdir() if p.name.startswith("chv__"))
    stats = {r["file"]: r for r in rd(ROOT / "data" / "ppe4" / "stats.csv")}
    lines, bad = [f"[{src}]"], False
    for st in sorted(set(sample.values())):
        files = [f for f, s in sample.items() if s == st]
        k = sum(added[f] > 0 for f in files)
        p, lo, hi = wilson(k, len(files))
        lines.append(f"{st}: {k}/{len(files)} = {pct(p)} (KTC {pct(lo)}; {pct(hi)})")
        if p >= c["min_chv_rate"]:
            bad = True
            n = len(pop[st])
            per = sum(added[f] for f in files) / max(k, 1)
            minutes = round(n * full["pack"]["sec_per_chv_image"] / 60)
            old = {x: sum(int(stats[f]["n_" + x]) for f in pop[st]) for x in OLD}
            lines.append(f"  tầng {st}, {n} ảnh ở C2. Gán thủ công: khoảng {round(n * p * per)} hộp (ước tính), {minutes} phút (ước tính). "
                         f"Che vùng: cần xem cùng số ảnh, {minutes} phút, không thêm nhãn ủng. Bỏ ảnh: mất {n} ảnh, {old}. Chờ người dùng chọn.")
    return ("action" if bad else "pass"), "; ".join(lines)


def cmd_gates():
    full = cfg()
    c = full["gates"]
    out = {}
    for name, (st, detail) in (("P0a", gate_p0a(c)), ("P2 giày SH17", gate_p2(c)), ("P2_chv ủng", gate_chv(c, full))):
        out[name] = st
        print(f"[{st}] {name}: {detail}")
    return out


def compute_scope():
    full = cfg()["scope"]
    last = last_review()
    heights = {}
    for g in PACK.iterdir():
        if (g / "index.csv").exists() and g.name != "TRIAL":
            heights.update({r["box_id"]: r["person_h_px"] for r in rd(g / "index.csv")})
    res = {}
    for t in ("boots", "goggles"):
        pts = [(float(heights[k]), r["person_ok"] == "du_lon") for k, r in last.items() if r["target"] == t and r["person_ok"] in ("du_lon", "qua_nho") and heights.get(k)]
        res[t] = (len(pts), scope_threshold(pts, full["min_ok_rate"]) if len(pts) >= full["min_boxes"] else None)
    return res


def cmd_scope(write):
    res = compute_scope()
    full = cfg()["scope"]
    for t, (n, v) in res.items():
        print(f"{t}: {n} hộp có ý kiến (cần {full['min_boxes']}); ngưỡng đề xuất {v} px ở ảnh cạnh dài {full['side']}")
    if any(v is None for _, v in res.values()):
        sys.exit("Chưa đủ dữ liệu để chốt ngưỡng người đủ lớn.")
    if write:
        s = CONFIG.read_text(encoding="utf-8")
        new, n = re.subn(r"min_person_px: \{boots: [^,]+, goggles: [^}]+\}", f"min_person_px: {{boots: {res['boots'][1]}, goggles: {res['goggles'][1]}}}", s)
        if n != 1:
            sys.exit("Không tìm thấy min_person_px trong config.")
        CONFIG.write_text(new, encoding="utf-8")
        print("Đã ghi vào configs/ppe6.yaml")


def cmd_monitor(variant):
    full = cfg()
    src = KAGGLE / f"{variant}_pack.zip"
    if not src.exists():
        sys.exit(f"Thiếu {src}")
    status = {r["file"]: r["status"] for r in rd(BASE / "dataset" / "eval_status.csv") if r["set"] == "val_new"}
    stats = {r["file"]: r for r in rd(ROOT / "data" / "ppe4" / "stats.csv")}
    with zipfile.ZipFile(src) as z:
        rows = z.read("manifest.tsv").decode("utf-8").splitlines()
        monitor = {x.split("\t")[2] for x in rows if x.startswith("val_monitor\t")}
        labels = {Path(f).stem: z.read(f"labels/val_monitor/{Path(f).stem}.txt").decode("utf-8") for f in monitor}
    keep, errors = {}, []
    for f in sorted(monitor | {k for k, v in status.items() if v == "ready"}):
        st = status.get(f)
        if st in ("pending", "rejected"):
            continue
        if st == "ready":
            keep[f] = (BASE / "dataset" / "labels" / "val_new_draft" / f"{Path(f).stem}.txt").read_text(encoding="utf-8")
        else:
            keep[f] = labels[Path(f).stem]
    errors = check_monitor({f: t.splitlines() for f, t in keep.items()}, status)
    n_ready = sum(status.get(f) == "ready" and any(x.split()[0] in ("4", "5") for x in t.splitlines()) for f, t in keep.items())
    if errors or not n_ready:
        print(f"Không dựng được val_monitor: {len(errors)} lỗi, {n_ready} ảnh có nhãn lớp mới đã duyệt.")
        for e in errors[:5]:
            print(" ", e)
        sys.exit("val_monitor còn dùng nhãn agent hoặc chưa có nhãn người duyệt cho lớp mới.")
    scope = full["scope"]["min_person_px"]
    if any(v is None for v in scope.values()):
        sys.exit("Chưa có ngưỡng người đủ lớn: chạy `03n scope --write` trước.")
    out = KAGGLE / f"{variant}_final_pack.zip"
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    with zipfile.ZipFile(src) as a, zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as b:
        for item in a.infolist():
            if item.filename == "manifest.tsv" or item.filename.startswith("labels/val_monitor/"):
                continue
            b.writestr(item, a.read(item.filename))
        new = [x for x in rows if not x.startswith("val_monitor\t")] + [f"val_monitor\t{stats[f]['split']}\t{f}\tlink" for f in sorted(keep)]
        b.writestr("manifest.tsv", "\n".join(new) + "\n")
        for f, t in keep.items():
            b.writestr(f"labels/val_monitor/{Path(f).stem}.txt", t)
        b.writestr("ready.json", json.dumps(dict(variant=variant, monitor_source="human", min_person_px=scope, commit=commit, monitor_images=len(keep), new_class_images=n_ready), ensure_ascii=False, indent=2))
    print(f"Đã ghi {out}: val_monitor {len(keep)} ảnh, {n_ready} ảnh có nhãn lớp mới đã duyệt.")


def group_progress():
    last = last_review()
    rows = {}
    for g in ("P0a", "P0b", "P1", "P2"):
        idx = rd(PACK / g / "index.csv")
        rows[g] = (sum(r["box_id"] in last for r in idx), len(idx))
    chvg = [r["file"] for r in rd(BASE / "eval" / "chvg_split.csv")]
    rows["P0b ảnh CHVG"] = (sum("image:" + f in last for f in chvg), len(chvg))
    sample = rd(PACK / "P2_chv" / "sample.csv")
    seen = {r["box_id"] for r in rd(REVIEW / "chv_boots_seen.csv")}
    rows["P2_chv"] = (sum("image:" + r["file"] in seen for r in sample), len(sample))
    scenes = rd(REVIEW / "scene_review_done.csv")
    want = rd(PACK / "scene_review" / "scene_review.csv")
    rows["Bảng cảnh"] = (sum(r["same_as_train"].strip().lower() in ("yes", "no") for r in scenes), len(want))
    return rows


# Kính là thử nghiệm, không chặn ủng (CLAUDE.md): CHVG chỉ đo kính, không vào train; chưa xong thì kính báo riêng, không chặn train ủng.
NOT_BLOCKING = "(kính, không chặn train) "


def machine_items():
    """Checklist của quy trình máy gán, người kiểm định."""
    out = [((REVIEW / f"machine_pass_{p}.csv").exists(), f"Lượt máy {p} đã khóa") for p in ("a", "b")]
    out.append(((REVIEW / "machine_merged.csv").exists(), "Đã gộp hai lượt máy"))
    out.append(((REVIEW / "audit_review.csv").exists(), "Người đã kiểm định gói audit"))
    rep = REVIEW / "audit_report.json"
    tiers = json.loads(rep.read_text(encoding="utf-8"))["tiers"] if rep.exists() else {}
    out.append((bool(tiers) and all(v["passed"] for v in tiers.values()), f"(nhãn máy không dùng cho val, test, train, không chặn train) Các tầng nhãn máy đạt kiểm định: {sum(v['passed'] for v in tiers.values())}/{len(tiers)}"))
    out.append(((REVIEW / "train_v3_review.csv").exists(), "Ủng ở train đã chấm theo định nghĩa bản 3 (train_v3)"))
    full = cfg()
    gate = {n: s for n, (s, _) in (("P0a", gate_p0a(full["gates"])), ("P2", gate_p2(full["gates"])), ("P2_chv", gate_chv(full["gates"], full)))}
    out.append((all(s != "pending" for s in gate.values()), f"03n gates đã có kết quả, chờ người dùng chọn nếu có action/stop: {gate}"))
    man = BASE / "dataset" / "manifest.json"
    m = json.loads(man.read_text(encoding="utf-8")) if man.exists() else {}
    out.append(("eval_counts" in m and (BASE / "dataset" / "ignore.csv").exists(), "03i đọc nhãn người mới, ghi vùng bỏ qua ignore.csv"))
    st = m.get("eval_status", {})
    for s in ("val_new", "test_new", "chvg_glass_val", "chvg_glass_test"):
        v = st.get(s, {})
        soft = NOT_BLOCKING if s.startswith("chvg") else ""
        out.append((bool(v) and set(v) == {"ready"}, f"{soft}{s}: mọi ảnh đã có người chốt {v}"))
    return out


def cmd_checklist():
    full = cfg()
    items = []
    if full["labeling"]["mode"] == "machine_audit":
        items += machine_items()
    else:
        for name, (a, b) in group_progress().items():
            items.append((a == b and b > 0, f"Duyệt và nhập {name}: {a}/{b}"))
        human = REVIEW / "human_review.csv"
        manifest = BASE / "dataset" / "manifest.json"
        fresh = human.exists() and manifest.stat().st_mtime >= human.stat().st_mtime
        items.append((fresh, "Đã chạy lại 03i sau lần nhập cuối"))
    ok = subprocess.run([sys.executable, str(ROOT / "scripts" / "03i_ppe6_build_dataset.py"), "--check"], cwd=ROOT, capture_output=True).returncode == 0
    items.append((ok, "03i --check không lỗi"))
    scope = full["scope"]["min_person_px"]
    items.append((all(v is not None for v in scope.values()), f"Ngưỡng người đủ lớn đã chốt: {scope}"))
    if full["labeling"]["mode"] != "machine_audit":
        gates = cmd_gates()
        items.append((all(v == "pass" for v in gates.values()), f"Các quy tắc sau duyệt: {gates}"))
    fin = full["final"]
    items.append((bool(fin["data_locked"]), f"Bản dữ liệu đã chốt: chính {fin['main']}, đối chứng {fin['control']}, data_locked {fin['data_locked']}"))
    for v in (fin["main"], fin["control"]):
        items.append(((KAGGLE / f"{v}_final_pack.zip").exists(), f"Có gói cuối {v}_final_pack.zip (03n monitor)"))
    items.append(((BASE / "variants" / "kaggle_smoke.json").exists(), "Đã chạy thử Kaggle và kiểm tra best.pt (04f --save)"))
    r3 = ROOT / "outputs" / "train" / "yolo11s_ppe4_r3" / "weights" / "best.pt"
    cap = ROOT / "outputs" / "results" / "ppe6_eval" / "r3_ppe4val" / "capture.npz"
    items.append((r3.exists(), "r3 đã train xong, có best.pt trên máy"))
    items.append((cap.exists(), "r3 đã đánh giá bằng 04d"))
    print()
    for good, text in items:
        print(("[x] " if good else "[ ] ") + text)
    missing = sum(not g for g, t in items if not t.startswith(NOT_BLOCKING) and "không chặn train" not in t)
    print(f"\nCòn thiếu {missing}/{len(items)} mục." if missing else "\nSẵn sàng train.")
    sys.exit(1 if missing else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["gates", "scope", "monitor", "checklist"])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--variant", choices=["c1", "c2"])
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if args.cmd == "gates":
        cmd_gates()
    elif args.cmd == "scope":
        cmd_scope(args.write)
    elif args.cmd == "monitor":
        if not args.variant:
            sys.exit("Cần --variant c1 hoặc c2.")
        cmd_monitor(args.variant)
    else:
        cmd_checklist()


if __name__ == "__main__":
    main()
