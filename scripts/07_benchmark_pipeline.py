"""Đo hiệu năng chuỗi xử lý đầy đủ của hai (hoặc nhiều) cấu hình trong cùng điều kiện.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv; không chạy việc GPU khác cùng lúc):
    python scripts/07_benchmark_pipeline.py \
        --config baseline=outputs/results/close_eval/pipeline_baseline_0645f53.yaml --config v4=configs/pipeline.yaml \
        --videos video3 video4 video5 video6 --repeats 3 --out outputs/results/close_eval/benchmark

Phạm vi đo (ghi vào kết quả):
- Mỗi lượt = một tiến trình mới (CUDA, mô hình nạp lại), chạy Pipeline(stage="full") như 05_run_video: phát hiện, theo
  dõi, pose, bộ phân loại bộ phận, ghép PPE, ba trạng thái, cửa sổ thời gian, quản lý sự kiện (kể cả ghi ảnh minh
  chứng, vào thư mục tạm của lượt đo). Không vẽ, không ghi video, không ghi frames.csv, không đẩy sự kiện lên backend.
- Latency một khung = thời gian gọi Pipeline.process (perf_counter), không gồm giải mã khung từ file. FPS xử lý =
  số khung / tổng latency; FPS toàn luồng = số khung / thời gian gồm cả giải mã.
- `warmup` khung đầu mỗi video vẫn chạy (để trạng thái theo dõi như nhau) nhưng không tính vào thống kê.
- GPU: `nvidia-smi` lấy mẫu mỗi `--smi-ms` ms (số liệu lấy mẫu, không phải đo liên tục); memory.used là của cả GPU,
  trừ mức nền đo trước khi nạp mô hình. VRAM của PyTorch: torch.cuda.max_memory_allocated / max_memory_reserved.
- Thứ tự cấu hình đổi chiều mỗi lượt lặp (A,B / B,A / ...) để giảm lệch do máy nóng dần.
Ghi <out>/benchmark.json (từng lượt) và <out>/benchmark.md (bảng tổng).
"""

import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")

ROOT = Path(__file__).resolve().parents[1]


def smi_sampler(ms, stop, out):
    """Lấy mẫu utilization.gpu và memory.used (MiB) bằng nvidia-smi cho tới khi stop được đặt."""
    p = subprocess.Popen(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits",
                          f"--loop-ms={ms}"], stdout=subprocess.PIPE, text=True)
    try:
        for line in p.stdout:
            if stop.is_set():
                break
            try:
                u, m = (float(x) for x in line.strip().split(","))
                out.append((u, m))
            except ValueError:
                pass
    finally:
        p.kill()


def smi_now():
    q = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True)
    return float(q.stdout.strip().splitlines()[0])


def worker(args):
    """Một lượt đo: một cấu hình, một video, trong tiến trình này."""
    import cv2
    import numpy as np
    import torch

    sys.path.insert(0, str(ROOT / "src"))
    from ppe import load_config
    from ppe.pipeline import Pipeline

    idle_mib = smi_now()
    cfg = load_config(ROOT / args.worker_config)
    tmp = Path(tempfile.mkdtemp(prefix="ppe_bench_"))
    cfg["events"]["evidence_dir"] = str(tmp)          # ảnh minh chứng vẫn ghi (như thật), vào thư mục tạm
    pipe = Pipeline("bench", f"bench_{Path(args.worker_video).stem}", stage="full", cfg=cfg, on_event=None)
    cap = cv2.VideoCapture(str(ROOT / args.worker_video))
    fps_src = cap.get(cv2.CAP_PROP_FPS) or 30.0
    samples, stop = [], threading.Event()
    th = threading.Thread(target=smi_sampler, args=(args.smi_ms, stop, samples), daemon=True)
    torch.cuda.reset_peak_memory_stats()
    lat, steps, i = [], {}, 0
    th.start()
    t_all = time.perf_counter()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        s = time.perf_counter()
        out = pipe.process(frame, i / fps_src)
        dt = (time.perf_counter() - s) * 1000
        if i >= args.warmup:
            lat.append(dt)
            for k, v in out["timing"].items():
                steps.setdefault(k, []).append(v)
        i += 1
    wall = time.perf_counter() - t_all
    stop.set()
    pipe.close(i / fps_src)
    n_events = len(pipe.events.closed) + len(pipe.events.open)
    cap.release()
    th.join(timeout=3)
    shutil.rmtree(tmp, ignore_errors=True)
    lat_a = np.array(lat)
    res = dict(frames=i, measured_frames=len(lat), events=n_events, wall_s=round(wall, 3),
               latency_ms=dict(mean=float(lat_a.mean()), p50=float(np.percentile(lat_a, 50)),
                               p95=float(np.percentile(lat_a, 95)), max=float(lat_a.max())),
               process_fps=len(lat) / (lat_a.sum() / 1000), end_to_end_fps=i / wall,
               step_ms_mean={k: float(np.mean(v)) for k, v in sorted(steps.items())},
               gpu_samples=len(samples), gpu_util_mean=statistics.fmean(u for u, _ in samples) if samples else None,
               gpu_mem_used_peak_mib=max(m for _, m in samples) if samples else None, gpu_mem_idle_mib=idle_mib,
               torch_max_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
               torch_max_reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
    Path(args.worker_out).write_text(json.dumps(res), encoding="utf-8")


def agg(runs, key):
    vals = [r[key] for r in runs]
    return statistics.fmean(vals), (statistics.stdev(vals) if len(vals) > 1 else 0.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", action="append", help="tên=đường dẫn cấu hình")
    ap.add_argument("--videos", nargs="+", default=["video3", "video4", "video5", "video6"])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=30)
    ap.add_argument("--smi-ms", type=int, default=500)
    ap.add_argument("--out", default="outputs/results/close_eval/benchmark")
    ap.add_argument("--worker-config")
    ap.add_argument("--worker-video")
    ap.add_argument("--worker-out")
    args = ap.parse_args()
    if args.worker_config:
        return worker(args)
    sys.stdout.reconfigure(encoding="utf-8")
    configs = [tuple(c.split("=", 1)) for c in args.config]
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    runs = []
    for r in range(args.repeats):
        order = configs if r % 2 == 0 else configs[::-1]
        for name, c in order:
            for v in args.videos:
                tmp = out / f"_run_{r}_{name}_{v}.json"
                cmd = [sys.executable, str(Path(__file__).resolve()), "--worker-config", c,
                       "--worker-video", f"data/videos/{v}.mp4", "--worker-out", str(tmp),
                       "--warmup", str(args.warmup), "--smi-ms", str(args.smi_ms)]
                t0 = time.time()
                p = subprocess.run(cmd, cwd=ROOT)
                if p.returncode:
                    sys.exit(f"Lượt đo lỗi: {name} {v} lặp {r}")
                d = json.loads(tmp.read_text(encoding="utf-8"))
                tmp.unlink()
                d.update(repeat=r, config=name, video=v)
                runs.append(d)
                print(f"lặp {r} {name:10s} {v}: {d['frames']} khung, latency TB {d['latency_ms']['mean']:.1f} ms, "
                      f"p95 {d['latency_ms']['p95']:.1f} ms, {d['process_fps']:.2f} FPS xử lý "
                      f"({time.time() - t0:.0f} s)", flush=True)
    # kiểm cùng số khung, cùng số sự kiện giữa các lượt của cùng video
    checks = {}
    for v in args.videos:
        fr = {r["frames"] for r in runs if r["video"] == v}
        checks[v] = dict(frames_equal=len(fr) == 1, frames=sorted(fr),
                         events_by_config={n: sorted({r["events"] for r in runs if r["video"] == v and r["config"] == n})
                                           for n, _ in configs})
    # gộp mỗi lượt lặp: tổng trên mọi video (latency theo khung, gộp thời gian)
    per_rep = {}
    for name, _ in configs:
        rows = []
        for r in range(args.repeats):
            rs = [x for x in runs if x["config"] == name and x["repeat"] == r]
            n = sum(x["measured_frames"] for x in rs)
            tot_ms = sum(x["latency_ms"]["mean"] * x["measured_frames"] for x in rs)
            rows.append(dict(latency_mean=tot_ms / n, process_fps=n / (tot_ms / 1000),
                             end_to_end_fps=sum(x["frames"] for x in rs) / sum(x["wall_s"] for x in rs),
                             latency_p95_max_video=max(x["latency_ms"]["p95"] for x in rs),
                             gpu_util=statistics.fmean(x["gpu_util_mean"] for x in rs if x["gpu_util_mean"] is not None),
                             gpu_mem_delta=max(x["gpu_mem_used_peak_mib"] - x["gpu_mem_idle_mib"] for x in rs),
                             torch_reserved=max(x["torch_max_reserved_mib"] for x in rs),
                             torch_allocated=max(x["torch_max_allocated_mib"] for x in rs)))
        per_rep[name] = rows
    import torch
    import ultralytics
    env = dict(python=platform.python_version(), torch=torch.__version__, cuda=torch.version.cuda,
               ultralytics=ultralytics.__version__, gpu=torch.cuda.get_device_name(0),
               nvidia_smi=subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                                          "--format=csv,noheader"], capture_output=True, text=True).stdout.strip(),
               cpu=platform.processor())
    res = dict(created=datetime.now().isoformat(timespec="seconds"), configs=dict(configs), videos=args.videos,
               repeats=args.repeats, warmup=args.warmup, smi_ms=args.smi_ms, environment=env,
               scope="Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, "
                     "ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm "
                     "giải mã khung; GPU từ nvidia-smi lấy mẫu",
               checks=checks, per_repeat=per_rep, runs=runs)
    (out / "benchmark.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    keys = [("latency_mean", "Latency TB (ms)", 1), ("latency_p95_max_video", "P95 latency, video cao nhất (ms)", 1),
            ("process_fps", "FPS xử lý", 2), ("end_to_end_fps", "FPS gồm giải mã", 2), ("gpu_util", "GPU util TB (%)", 1),
            ("gpu_mem_delta", "VRAM GPU tăng so với nền, đỉnh (MiB)", 0),
            ("torch_reserved", "PyTorch reserved đỉnh (MiB)", 0), ("torch_allocated", "PyTorch allocated đỉnh (MiB)", 0)]
    L = [f"# Benchmark ({res['created']})", "", f"Phạm vi: {res['scope']}.", "",
         f"Video {', '.join(args.videos)}; {args.repeats} lượt lặp; bỏ {args.warmup} khung đầu mỗi video khỏi thống kê; "
         f"nvidia-smi mỗi {args.smi_ms} ms. Môi trường: {env['gpu']}, torch {env['torch']}, ultralytics {env['ultralytics']}.",
         "", "Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.", "",
         "| Chỉ số | " + " | ".join(n for n, _ in configs) + " | Chênh (sau − đầu) |", "|---|" + "---|" * (len(configs) + 1)]
    for k, label, nd in keys:
        cells = []
        means = []
        for name, _ in configs:
            m, s = agg(per_rep[name], k)
            means.append(m)
            cells.append(f"{m:.{nd}f} ± {s:.{nd}f}")
        diff = means[-1] - means[0]
        rel = f" ({diff / means[0] * 100:+.1f}%)" if means[0] else ""
        L.append(f"| {label} | " + " | ".join(cells) + f" | {diff:+.{nd}f}{rel} |")
    L += ["", "Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):", "",
          "| Bước | " + " | ".join(n for n, _ in configs) + " |", "|---|" + "---|" * len(configs)]
    steps = sorted({k for x in runs for k in x["step_ms_mean"]})
    for st in steps:
        cells = []
        for name, _ in configs:
            rs = [x for x in runs if x["config"] == name and st in x["step_ms_mean"]]
            n = sum(x["measured_frames"] for x in rs)
            cells.append(f"{sum(x['step_ms_mean'][st] * x['measured_frames'] for x in rs) / n:.2f}" if n else "-")
        L.append(f"| {st} | " + " | ".join(cells) + " |")
    L += ["", "Kiểm tra: " + "; ".join(f"{v}: cùng số khung {c['frames_equal']} ({c['frames']}), số sự kiện "
                                         f"{c['events_by_config']}" for v, c in checks.items())]
    (out / "benchmark.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
