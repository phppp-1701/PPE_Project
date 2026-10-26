"""Bước 0: kiểm tra môi trường.

Cách chạy (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/00_check_env.py                     # kiểm tra GPU + chạy thử nhận diện ảnh mẫu

Kết quả in ra màn hình và lưu vào outputs/results/env_check.json.
"""

import argparse
import json
import platform
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "outputs" / "results"
MIB = 1024**2


def check_gpu():
    """Thông tin phiên bản và GPU mà PyTorch nhìn thấy."""
    import ultralytics

    info = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "ultralytics": ultralytics.__version__,
        "cuda_available": torch.cuda.is_available(),
    }
    if info["cuda_available"]:
        props = torch.cuda.get_device_properties(0)
        free, total = torch.cuda.mem_get_info(0)
        info.update(
            gpu_name=props.name,
            gpu_total_mib=round(total / MIB),
            gpu_free_mib=round(free / MIB),
            compute_capability=f"{props.major}.{props.minor}",
        )
        # Phép nhân ma trận nhỏ trên GPU để chắc chắn CUDA chạy được thật
        x = torch.randn(1024, 1024, device="cuda")
        info["matmul_ok"] = bool(torch.isfinite(x @ x).all())
    return info


def check_predict(weights, n_runs):
    """Tải trọng số (nếu chưa có) và nhận diện ảnh mẫu bus.jpg đi kèm Ultralytics."""
    from ultralytics import YOLO
    from ultralytics.utils import ASSETS

    model = YOLO(weights)
    image = ASSETS / "bus.jpg"
    model.predict(image, device=0, verbose=False)  # lượt đầu để khởi động GPU, không tính giờ
    speeds = []
    for _ in range(n_runs):
        result = model.predict(image, device=0, verbose=False)[0]
        speeds.append(result.speed)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_image = RESULTS_DIR / "env_check_bus.jpg"
    result.save(filename=str(out_image))
    names = [result.names[int(c)] for c in result.boxes.cls]
    return {
        "weights": str(Path(model.ckpt_path).resolve()),
        "image": str(image),
        "orig_shape": result.orig_shape,
        "n_runs": n_runs,
        "detections": {n: names.count(n) for n in sorted(set(names))},
        "mean_ms": {k: round(sum(s[k] for s in speeds) / n_runs, 2) for k in speeds[0]},
        "annotated_image": str(out_image),
    }


def save(key, value):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / "env_check.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data[key] = value
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--weights", default="yolo11s.pt")
    p.add_argument("--n-runs", type=int, default=20, help="số lần nhận diện ảnh mẫu để lấy thời gian trung bình")
    args = p.parse_args()

    gpu = check_gpu()
    print(json.dumps(gpu, indent=2))
    save("environment", gpu)
    if not gpu["cuda_available"]:
        sys.exit("PyTorch không nhìn thấy GPU: kiểm tra lại bản torch đã cài (cần bản +cuXXX).")
    pred = check_predict(args.weights, args.n_runs)
    print(json.dumps(pred, indent=2, ensure_ascii=False))
    save("predict", pred)


if __name__ == "__main__":
    main()
