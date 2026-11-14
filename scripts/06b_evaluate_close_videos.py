"""Đánh giá theo khung trên video có nhãn CVAT, so hai (hoặc nhiều) cấu hình, và ghi/kiểm manifest đóng băng.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    # 1. Ghi manifest (sau commit đóng băng): commit nguồn, sha256 cấu hình, trọng số, video, nhãn, môi trường
    python scripts/06b_evaluate_close_videos.py manifest --config configs/pipeline.yaml \
        --baseline-commit 0645f53 --baseline-config outputs/results/close_eval/pipeline_baseline_0645f53.yaml \
        --videos video9 video10 ... --labels "data/videos/{v}_machine_cvat.zip" --out outputs/results/close_eval/manifest.json

    # 2. Chạy và chấm (cấu hình đầu tiên là mốc so sánh)
    python scripts/06b_evaluate_close_videos.py evaluate --videos video3 video4 video5 video6 \
        --labels "data/videos/{v}_cvat.zip" --label-note "..." \
        --config baseline=outputs/results/close_eval/pipeline_baseline_0645f53.yaml --config v4=configs/pipeline.yaml \
        --out outputs/results/close_eval/dev_check [--manifest outputs/results/close_eval/manifest.json] [--skip-run]

evaluate:
- Mỗi cấu hình, mỗi video: gọi scripts/05_run_video.py --config <file> --no-video --api-url "" (đúng chuỗi xử lý đầy đủ,
  không vẽ, không đẩy sự kiện lên backend), ghi <out>/<tên cấu hình>/<video>/frames.csv, events.jsonl, summary.json.
- Nhãn: file zip CVAT for video 1.1 (annotations.xml). Khung nằm giữa hai hộp của một track được nội suy tuyến tính,
  thuộc tính lấy theo hộp trước; hộp có outside=1 kết thúc đoạn. Găng = thieu nếu một tay thieu, co nếu hai tay co.
- Ghép: mỗi hộp nhãn ở mỗi khung lấy người dự đoán có IoU lớn nhất, đạt calibration.video.match_iou
  (configs/pipeline.yaml); không đạt thì trạng thái dự đoán là "khong_ghep" (giữ lại, không bỏ khung nào).
- Bảng nhầm lẫn nhãn x dự đoán cho từng PPE, từng video, tổng; so cấu hình đầu với từng cấu hình sau theo khung
  (chuyển trạng thái), theo dòng frames.csv (người, hộp; Có mới trên người không có nhãn) và theo nội dung sự kiện.
- --manifest: trước khi chạy, kiểm code hiện tại trùng commit nguồn (ngoài outputs/results/close_eval/), không có thay
  đổi chưa commit, sha256 của cấu hình, trọng số, video, nhãn trùng manifest. Sai thì dừng.
Ghi <out>/results.json, <out>/results.md, <out>/transitions.csv.
"""

import argparse
import collections
import csv
import hashlib
import json
import platform
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PPE = ("helmet", "vest", "gloves", "goggles", "boots")
STATES = ("co", "thieu", "chua_xac_dinh")
PRED = STATES + ("khong_ghep",)
FREEZE_EXCLUDE = "outputs/results/close_eval"
# File text: băm sau khi đổi CRLF -> LF (đúng nội dung Git lưu), vì core.autocrlf làm file lấy ra từ Git có CRLF hay LF
# tùy máy. File khác (trọng số, video, zip nhãn): băm nguyên byte.
TEXT_SUFFIX = {".yaml", ".yml", ".py", ".json", ".md", ".csv", ".txt"}


def sha256(path):
    path = Path(path)
    h = hashlib.sha256()
    if path.suffix.lower() in TEXT_SUFFIX:
        h.update(path.read_bytes().replace(b"\r\n", b"\n"))
        return h.hexdigest()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def weight_files(cfg):
    """Mọi file trọng số mà cấu hình dùng."""
    ws = {cfg["detector"]["weights"]}
    if (cfg.get("pose") or {}).get("enabled"):
        ws.add(cfg["pose"]["weights"])
    pc = cfg.get("part_cls") or {}
    if pc.get("enabled"):
        by = pc.get("weights_by_ppe") or {}
        ws |= {by.get(p, pc["weights"]) for p in (pc.get("thresholds") or {})}
    return sorted(ws)


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-9)


# ---------------------------------------------------------------- nhãn

def load_labels(zip_path):
    """{frame: [(label_track_id, box, {ppe: trạng thái})]} từ CVAT for video 1.1, nội suy giữa các hộp."""
    root = ET.fromstring(zipfile.ZipFile(zip_path).read("annotations.xml"))
    out = collections.defaultdict(list)
    for tr in root.iter("track"):
        ks = []
        for b in tr.iter("box"):
            a = {x.get("name"): (x.text or "").strip() for x in b.iter("attribute")}
            ks.append((int(b.get("frame")), b.get("outside") == "1",
                       [float(b.get(k)) for k in ("xtl", "ytl", "xbr", "ybr")], a))
        ks.sort(key=lambda k: k[0])
        for j, (f0, outside, b0, a0) in enumerate(ks):
            if outside:
                continue
            nxt = ks[j + 1] if j + 1 < len(ks) else None
            f1 = nxt[0] if nxt else f0 + 1
            a = dict(a0)
            gl = [a.get("glove_left"), a.get("glove_right")]
            a["gloves"] = "thieu" if "thieu" in gl else ("co" if all(g == "co" for g in gl) else "chua_xac_dinh")
            for f in range(f0, f1):
                if nxt and not nxt[1]:
                    r = (f - f0) / max(f1 - f0, 1)
                    gb = [b0[i] + (nxt[2][i] - b0[i]) * r for i in range(4)]
                else:
                    gb = b0
                out[f].append((tr.get("id"), gb, {p: a[p] for p in PPE}))
    return out


def load_frames(path):
    rows = collections.defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[int(r["frame"])].append(r)
    return rows


def box_of(r):
    return [float(r[k]) for k in ("x1", "y1", "x2", "y2")]


def match(labels, frames, thr):
    """[(frame, label_track, {ppe: (nhãn, dự đoán)}, pred_track_id hoặc None)] cho mọi hộp nhãn."""
    res = []
    for f in sorted(labels):
        for lt, gb, gs in labels[f]:
            best = max(frames.get(f, []), key=lambda r: iou(gb, box_of(r)), default=None)
            ok = best is not None and iou(gb, box_of(best)) >= thr
            res.append((f, lt, {p: (gs[p], (best[p] or "chua_xac_dinh") if ok else "khong_ghep") for p in PPE},
                        best["track_id"] if ok else None))
    return res


def confusion(matched):
    c = {p: collections.Counter() for p in PPE}
    for _, _, st, _ in matched:
        for p in PPE:
            c[p][st[p]] += 1
    return c


def summary_of(cm):
    """Số đọc nhanh từ bảng nhầm lẫn của một PPE."""
    g = lambda a, b: cm[(a, b)]   # noqa: E731
    return dict(
        nhan_co=sum(g("co", q) for q in PRED), nhan_thieu=sum(g("thieu", q) for q in PRED),
        nhan_chua_xac_dinh=sum(g("chua_xac_dinh", q) for q in PRED),
        co_dung=g("co", "co"), thieu_dung=g("thieu", "thieu"),
        bao_thieu_oan=g("co", "thieu"), bao_co_sai=g("thieu", "co"),
        co_thanh_chua_xd=g("co", "chua_xac_dinh"), thieu_thanh_chua_xd=g("thieu", "chua_xac_dinh"),
        thieu_tren_nhan_chua_xd=g("chua_xac_dinh", "thieu"), co_tren_nhan_chua_xd=g("chua_xac_dinh", "co"),
        khong_ghep=sum(g(a, "khong_ghep") for a in STATES))


# ---------------------------------------------------------------- sự kiện

def load_events(path):
    """Danh sách sự kiện (bản ghi cuối của mỗi event_id), sắp theo (start_time, track_id).
    event_id là UUID sinh ngẫu nhiên mỗi lần chạy nên không so trực tiếp; dùng số thứ tự sau khi sắp."""
    last = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            last[e["event_id"]] = e
    r3 = lambda x: None if x is None else round(float(x), 3)   # noqa: E731
    evs = [dict(track_id=e["track_id"], start_time=r3(e["start_time"]), confirmed_at=r3(e.get("confirmed_at")),
                end_time=r3(e.get("end_time")), close_reason=e.get("close_reason"), event_state=e.get("event_state"),
                missing_items=sorted(e.get("missing_items") or []),
                missing_history=[(r3(h["t"]), sorted(h.get("missing_items") or [])) for h in e.get("history", [])
                                 if "missing_items" in h])
           for e in last.values()]
    evs.sort(key=lambda e: (e["start_time"], e["track_id"]))
    for i, e in enumerate(evs):
        e["index"] = i + 1
    return evs


def compare_events(a, b):
    keys = ("track_id", "start_time", "confirmed_at", "end_time", "close_reason", "missing_items", "missing_history")
    diffs = []
    for i in range(max(len(a), len(b))):
        ea, eb = (a[i] if i < len(a) else None), (b[i] if i < len(b) else None)
        if ea is None or eb is None:
            diffs.append(dict(index=i + 1, field="(thiếu sự kiện)", a=ea, b=eb))
            continue
        for k in keys:
            if ea[k] != eb[k]:
                diffs.append(dict(index=i + 1, field=k, a=ea[k], b=eb[k]))
    return dict(n_a=len(a), n_b=len(b), same=not diffs, diffs=diffs)


# ---------------------------------------------------------------- manifest

def environment():
    env = dict(python=platform.python_version(), platform=platform.platform())
    try:
        import torch
        import ultralytics
        env.update(torch=torch.__version__, cuda=torch.version.cuda, ultralytics=ultralytics.__version__,
                   gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
    except Exception as e:   # noqa: BLE001
        env["import_error"] = str(e)
    q = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
                       capture_output=True, text=True)
    env["nvidia_smi"] = q.stdout.strip()
    return env


def file_entry(rel):
    p = ROOT / rel
    return dict(path=str(rel).replace("\\", "/"), sha256=sha256(p),
                hash_mode="lf_normalized" if p.suffix.lower() in TEXT_SUFFIX else "raw")


def cmd_manifest(args):
    cfg = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))
    dirty = git("status", "--porcelain", "--untracked-files=no")
    if dirty:
        sys.exit("Có thay đổi chưa commit trong file đã theo dõi; commit đóng băng trước rồi mới ghi manifest:\n" + dirty)
    videos = [file_entry(f"data/videos/{v}.mp4") for v in args.videos]
    labels = [file_entry(args.labels.format(v=v)) for v in args.videos]
    m = dict(
        created=datetime.now().isoformat(timespec="seconds"),
        note="source_commit là commit chứa code và cấu hình đánh giá; manifest nằm ở commit sau, không tự ghi mã commit"
             " chứa chính nó. Kiểm tái lập: code ngoài outputs/results/close_eval/ phải trùng source_commit. sha256 file"
             " text (hash_mode lf_normalized) tính sau khi đổi CRLF thành LF; file khác (raw) tính nguyên byte.",
        source_commit=git("rev-parse", "HEAD"), source_commit_subject=git("log", "-1", "--format=%s"),
        config=file_entry(args.config), weights=[file_entry(w) for w in weight_files(cfg)],
        scripts=[file_entry(s) for s in ("scripts/05_run_video.py", "scripts/06b_evaluate_close_videos.py",
                                         "scripts/07_benchmark_pipeline.py")],
        videos=videos, labels=labels, label_pattern=args.labels,
        baseline=dict(commit=git("rev-parse", args.baseline_commit), config=file_entry(args.baseline_config),
                      config_matches_commit=sha256(ROOT / args.baseline_config) == hashlib.sha256(
                          subprocess.run(["git", "show", f"{args.baseline_commit}:configs/pipeline.yaml"], cwd=ROOT,
                                         capture_output=True).stdout.replace(b"\r\n", b"\n")).hexdigest()),
        environment=environment())
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ghi {args.out}: source_commit {m['source_commit'][:10]}, {len(m['weights'])} trọng số, "
          f"{len(videos)} video, baseline khớp commit: {m['baseline']['config_matches_commit']}")


def verify_manifest(path, configs, videos, label_pattern):
    m = json.loads(Path(path).read_text(encoding="utf-8"))
    errs = []
    head = git("rev-parse", "HEAD")
    code_diff = git("diff", "--name-only", m["source_commit"], "HEAD", "--", ".", f":(exclude){FREEZE_EXCLUDE}")
    if code_diff:
        errs.append(f"code khác source_commit {m['source_commit'][:10]}: {code_diff}")
    dirty = git("status", "--porcelain", "--untracked-files=no", "--", ".", f":(exclude){FREEZE_EXCLUDE}")
    if dirty:
        errs.append("có thay đổi chưa commit:\n" + dirty)
    want = {e["path"]: e["sha256"] for e in [m["config"], m["baseline"]["config"], *m["weights"], *m["videos"], *m["labels"]]}
    for rel, h in want.items():
        if not (ROOT / rel).exists() or sha256(ROOT / rel) != h:
            errs.append(f"sha256 không khớp: {rel}")
    for name, c in configs:
        if str(c).replace("\\", "/") not in want:
            errs.append(f"cấu hình {name} ({c}) không có trong manifest")
        cfg = yaml.safe_load((ROOT / c).read_text(encoding="utf-8"))
        for w in weight_files(cfg):
            if w not in want:
                errs.append(f"trọng số {w} của {name} không có trong manifest")
    for v in videos:
        for rel in (f"data/videos/{v}.mp4", label_pattern.format(v=v)):
            if rel not in want:
                errs.append(f"{rel} không có trong manifest")
    if errs:
        sys.exit("Manifest không khớp, dừng:\n- " + "\n- ".join(errs))
    return dict(path=str(path), source_commit=m["source_commit"], head=head)


# ---------------------------------------------------------------- evaluate

def run_one(cfg_path, video, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ROOT / "scripts" / "05_run_video.py"), str(ROOT / "data" / "videos" / f"{video}.mp4"),
           "--config", str(ROOT / cfg_path), "--no-video", "--api-url", "", "--out", str(out_dir), "--stage", "full"]
    print(" ".join(cmd[1:3]), "|", cfg_path, flush=True)
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode:
        sys.exit(f"05_run_video lỗi ({r.returncode}) cho {video}, {cfg_path}")


def cmd_evaluate(args):
    configs = [tuple(c.split("=", 1)) for c in args.config]
    out = ROOT / args.out
    mf = verify_manifest(args.manifest, configs, args.videos, args.labels) if args.manifest else None
    thr = yaml.safe_load((ROOT / "configs" / "pipeline.yaml").read_text(encoding="utf-8"))["calibration"]["video"]["match_iou"]
    if not args.skip_run:
        for v in args.videos:
            for name, c in configs:
                run_one(c, v, out / name / v)
    res = dict(created=datetime.now().isoformat(timespec="seconds"), label_note=args.label_note, match_iou=thr,
               manifest=mf, configs={n: c for n, c in configs}, videos={}, totals={}, compare={})
    trans_rows = []
    total_cm = {n: {p: collections.Counter() for p in PPE} for n, _ in configs}
    base = configs[0][0]
    for v in args.videos:
        labels = load_labels(ROOT / args.labels.format(v=v))
        per, matched, frames, events = {}, {}, {}, {}
        for name, _ in configs:
            d = out / name / v
            frames[name] = load_frames(d / "frames.csv")
            matched[name] = match(labels, frames[name], thr)
            events[name] = load_events(d / "events.jsonl")
            summ = json.loads((d / "summary.json").read_text(encoding="utf-8"))
            cm = confusion(matched[name])
            for p in PPE:
                total_cm[name][p].update(cm[p])
            per[name] = dict(frames=summ["frames"], stage=summ["stage"], rows=sum(len(x) for x in frames[name].values()),
                             label_boxes=len(matched[name]),
                             label_boxes_unmatched=sum(1 for m in matched[name] if m[3] is None),
                             summary={p: summary_of(cm[p]) for p in PPE},
                             confusion={p: {f"{a}->{b}": cm[p][(a, b)] for a in STATES for b in PRED} for p in PPE},
                             events=events[name])
        res["videos"][v] = per
        for name, _ in configs[1:]:
            key = f"{base}_vs_{name}"
            cmpv = dict(events=compare_events(events[base], events[name]))
            # theo khung có nhãn: chuyển trạng thái (nhãn, mốc, cấu hình này)
            tr = {p: collections.Counter() for p in PPE}
            for ma, mb in zip(matched[base], matched[name]):
                assert ma[:2] == mb[:2]
                for p in PPE:
                    (g, pa), (_, pb) = ma[2][p], mb[2][p]
                    if pa != pb:
                        tr[p][(g, pa, pb)] += 1
                        trans_rows.append([key, v, ma[0], ma[1], p, g, pa, pb])
            cmpv["label_transitions"] = {p: {f"{g}|{a}->{b}": n for (g, a, b), n in sorted(tr[p].items())} for p in PPE}
            # theo dòng frames.csv: cùng người, cùng hộp? Có mới trên người không ghép được nhãn?
            ra = {(f, r["track_id"]): r for f, rs in frames[base].items() for r in rs}
            rb = {(f, r["track_id"]): r for f, rs in frames[name].items() for r in rs}
            labeled = {(m[0], m[3]) for m in matched[name] if m[3] is not None}
            same_box = sum(1 for k in ra.keys() & rb.keys() if box_of(ra[k]) == box_of(rb[k]))
            new_co_unlabeled = {p: sum(1 for k in ra.keys() & rb.keys() if k not in labeled
                                       and rb[k][p] == "co" and ra[k][p] != "co") for p in PPE}
            cmpv["rows"] = dict(rows_base=len(ra), rows_other=len(rb), only_base=len(ra.keys() - rb.keys()),
                                only_other=len(rb.keys() - ra.keys()), same_box=same_box,
                                new_co_on_unlabeled_rows=new_co_unlabeled)
            res["compare"].setdefault(key, {})[v] = cmpv
    res["totals"] = {n: {p: summary_of(total_cm[n][p]) for p in PPE} for n, _ in configs}
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "transitions.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["compare", "video", "frame", "label_track", "ppe", "label", "base_pred", "other_pred"])
        w.writerows(trans_rows)
    (out / "results.md").write_text(render_md(res, configs, args.videos), encoding="utf-8")
    print(f"Ghi {out.relative_to(ROOT)}/results.json, results.md, transitions.csv")


COLS = [("co_dung", "Có đúng"), ("nhan_co", "/nhãn Có"), ("thieu_dung", "Thiếu đúng"), ("nhan_thieu", "/nhãn Thiếu"),
        ("bao_thieu_oan", "Báo thiếu oan"), ("bao_co_sai", "Báo Có sai"), ("co_thanh_chua_xd", "Có→CXĐ"),
        ("thieu_thanh_chua_xd", "Thiếu→CXĐ"), ("thieu_tren_nhan_chua_xd", "Thiếu trên nhãn CXĐ"), ("khong_ghep", "Không ghép")]


def table(rows):
    head = "| Video | PPE | Cấu hình | " + " | ".join(c[1] for c in COLS) + " |"
    sep = "|" + "---|" * (3 + len(COLS))
    return "\n".join([head, sep] + rows)


def render_md(res, configs, videos):
    L = [f"# Kết quả theo khung ({res['created']})", "", f"**Nhãn:** {res['label_note']}", "",
         f"Ghép người: IoU ≥ {res['match_iou']}. CXĐ = Chưa xác định. \"Không ghép\" = hộp nhãn không ghép được người "
         "dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.", ""]
    if res["manifest"]:
        L += [f"Manifest: `{res['manifest']['path']}`, commit nguồn `{res['manifest']['source_commit'][:10]}`, "
              f"HEAD `{res['manifest']['head'][:10]}`.", ""]
    L += ["Cấu hình: " + ", ".join(f"`{n}` = `{c}`" for n, c in configs), "", "## Tổng", ""]
    rows = [f"| tổng | {p} | {n} | " + " | ".join(str(res["totals"][n][p][k]) for k, _ in COLS) + " |"
            for p in PPE for n, _ in configs]
    L += [table(rows), "", "## Từng video", ""]
    rows = [f"| {v} | {p} | {n} | " + " | ".join(str(res["videos"][v][n]["summary"][p][k]) for k, _ in COLS) + " |"
            for v in videos for p in PPE for n, _ in configs]
    L += [table(rows), "", "## Sự kiện", ""]
    for v in videos:
        for n, _ in configs:
            evs = res["videos"][v][n]["events"]
            L.append(f"- {v}, {n}: {len(evs)} sự kiện: " + "; ".join(
                f"#{e['index']} người {e['track_id']} {e['start_time']}-{e['end_time']}s {','.join(e['missing_items'])}"
                f" ({e['close_reason']})" for e in evs))
    L += ["", "## So sánh với cấu hình mốc", ""]
    for key, per in res["compare"].items():
        L.append(f"### {key}")
        for v, c in per.items():
            ev = c["events"]
            L.append(f"- {v}: sự kiện {'giống nhau' if ev['same'] else 'KHÁC: ' + json.dumps(ev['diffs'], ensure_ascii=False)}"
                     f" ({ev['n_a']} / {ev['n_b']}); dòng frames.csv {c['rows']['rows_base']} / {c['rows']['rows_other']},"
                     f" chỉ ở mốc {c['rows']['only_base']}, chỉ ở bản kia {c['rows']['only_other']}, cùng hộp"
                     f" {c['rows']['same_box']}; Có mới trên người không có nhãn {c['rows']['new_co_on_unlabeled_rows']}")
            for p, t in c["label_transitions"].items():
                if t:
                    L.append(f"  - {p} (nhãn|mốc->bản kia): {t}")
    return "\n".join(L) + "\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("--config", required=True)
    m.add_argument("--baseline-commit", required=True)
    m.add_argument("--baseline-config", required=True)
    m.add_argument("--videos", nargs="+", required=True)
    m.add_argument("--labels", required=True, help='mẫu đường dẫn nhãn, vd "data/videos/{v}_machine_cvat.zip"')
    m.add_argument("--out", required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--videos", nargs="+", required=True)
    e.add_argument("--labels", required=True)
    e.add_argument("--label-note", required=True, help="nguồn và trạng thái nhãn, ghi vào đầu kết quả")
    e.add_argument("--config", action="append", required=True, help="tên=đường dẫn; cái đầu tiên là mốc")
    e.add_argument("--out", required=True)
    e.add_argument("--manifest")
    e.add_argument("--skip-run", action="store_true", help="chỉ chấm lại kết quả đã có")
    args = ap.parse_args()
    {"manifest": cmd_manifest, "evaluate": cmd_evaluate}[args.cmd](args)


if __name__ == "__main__":
    main()
