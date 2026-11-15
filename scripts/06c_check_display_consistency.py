"""Kiểm nhất quán giữa hình vẽ trên video và trạng thái hệ thống báo (người dùng yêu cầu 16/11/2026).

Chạy chuỗi xử lý (không vẽ) trên các video, mỗi khung gọi 05_run_video.display_check (cùng hàm box_status, pl_regions mà
draw() dùng) và đếm vi phạm:
    hop_mau_khong_co      hộp PPE vẽ màu mà không là bằng chứng cho món Có nào của người được gán;
    co_khong_bang_chung   món là Có mà không có hộp màu gán cho người đó và không có vùng (PL) của bộ phân loại.
Đếm thêm hộp xám theo lý do (ngoai, tranh_chap, bac_bo, phan_van, chua_ket_luan, khong_xet). Chỉ đọc video, không chấm
nhãn, không chọn tham số. Không chạy trên holdout khi người dùng chưa cho phép.

Cách chạy (từ thư mục gốc, .venv):
    python scripts/06c_check_display_consistency.py --videos video3 video4 ... --out outputs/results/close_eval/annotated_main/display_audit.json
    (--config mặc định configs/pipeline.yaml)
"""

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppe import load_config  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--videos", nargs="+", required=True, help="tên video trong data/videos (không đuôi)")
    ap.add_argument("--config", default="configs/pipeline.yaml")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = importlib.util.spec_from_file_location("run_video", ROOT / "scripts" / "05_run_video.py")
    rv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rv)
    cfg = load_config(ROOT / args.config)
    total, per = Counter(), {}
    for v in args.videos:
        cap = cv2.VideoCapture(str(ROOT / "data" / "videos" / f"{v}.mp4"))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        pipe, _, _ = rv.build("full", "video", "display_check", None, cfg)
        cnt, i = Counter(), 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            out = pipe.process(frame, i / fps)
            i += 1
            for kind, *_ in rv.display_check(out, cfg, frame.shape):
                cnt[kind] += 1
            for kind, _, _ in rv.box_status(out, cfg).values():
                if kind != "co":
                    cnt["hop_xam_" + kind] += 1
        cap.release()
        cnt.setdefault("hop_mau_khong_co", 0)
        cnt.setdefault("co_khong_bang_chung", 0)
        per[v] = dict(khung=i, **cnt)
        total.update(cnt)
        print(v, per[v], flush=True)
    res = dict(config=args.config, tong=dict(total), video=per,
               dat=total["hop_mau_khong_co"] == 0 and total["co_khong_bang_chung"] == 0)
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("TỔNG:", dict(total), "| nhất quán:", res["dat"])
    print("Ghi", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
