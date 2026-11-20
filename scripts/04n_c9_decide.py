"""C9: áp tiêu chí đã khóa `configs/ppe6.yaml` mục `c9_decision` lên hai file kết quả của 04j. Viết 20/11/2026, TRƯỚC khi có
kết quả C9-ft, để cách đọc tiêu chí cố định trước khi thấy số.

Cách đọc tiêu chí (dùng điểm ước lượng `diff50.point` của 04j, như khi áp c6 / c7 / c8_decision):
- Có zoom: găng (tập ppe4) của C9-ft + zoom trừ c6_ft + zoom >= `min_gloves_gain`.
- Cả ảnh: người, mũ, áo, găng (tập ppe4), kính (goggles_all), ủng (tập new) của C9-ft trừ c6_ft >= −`max_drop`.
- Có zoom: kính (goggles_all), ủng (new) của C9-ft + zoom trừ c6_ft + zoom >= −`max_drop`.
Đạt cả ba thì C9-ft đạt; người dùng quyết định cuối. Khoảng tin cậy chỉ in ra để tham khảo, không dùng để quyết định.

Các bước khi đã tải run Kaggle về outputs/train/yolo11s_ppe6_c9_ft (từ thư mục gốc project, đã kích hoạt .venv):
    python scripts/04d_capture_val.py --weights outputs/train/yolo11s_ppe6_c9_ft/weights/best.pt --data data/ppe6/c5/eval/val/data.yaml --out outputs/results/c5_eval/c8lab_c9_ft_val
    python scripts/04m_crop_pass.py --split val --capture outputs/results/c5_eval/c8lab_c9_ft_val --weights outputs/train/yolo11s_ppe6_c9_ft/weights/best.pt --out outputs/results/c5_eval/c8lab_c9_ft_crop_val
    python scripts/04j_c5_eval.py --split val --run c6_ft=outputs/results/c5_eval/c8lab_c6_ft_val --run c9_ft=outputs/results/c5_eval/c8lab_c9_ft_val --name c8lab_c6_vs_c9
    python scripts/04j_c5_eval.py --split val --run c6_ft_crop=outputs/results/c5_eval/c8lab_c6_ft_crop_val --run c9_ft_crop=outputs/results/c5_eval/c8lab_c9_ft_crop_val --name c8lab_c6crop_vs_c9crop
    python scripts/04n_c9_decide.py

Ghi outputs/results/c5_eval/c9_decision.json. Nhãn val là nhãn máy, có kiểm định mẫu của người.
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "results" / "c5_eval"
# lớp -> tập con dùng để chấm (như c8_decision, c9_decision)
FULL = {"person": "ppe4", "helmet": "ppe4", "vest": "ppe4", "gloves": "ppe4", "goggles": "goggles_all", "boots": "new"}
ZOOM_GUARD = {"goggles": "goggles_all", "boots": "new"}


def diff(res, sub, cls):
    """Hiệu mAP50 (run sau − run đầu) của 04j, kèm KTC 95%."""
    row = res["subsets"][sub]["classes"][cls]
    if "diff50" not in row:
        sys.exit(f"{sub}/{cls}: file 04j phải có đúng hai run")
    return row["diff50"]["point"], row["diff50"]["ci"]


def decide(full, zoom, cfg):
    """Trả về danh sách điều kiện (tên, hiệu, ngưỡng, đạt) và kết luận chung."""
    checks = []
    d, ci = diff(zoom, "ppe4", "gloves")
    checks.append(dict(check="có zoom: găng tăng", cls="gloves", subset="ppe4", diff=d, ci=ci, need=f">= {cfg['min_gloves_gain']}",
                       ok=d >= cfg["min_gloves_gain"]))
    for c, sub in FULL.items():
        d, ci = diff(full, sub, c)
        checks.append(dict(check="cả ảnh: không tụt", cls=c, subset=sub, diff=d, ci=ci, need=f">= -{cfg['max_drop']}", ok=d >= -cfg["max_drop"]))
    for c, sub in ZOOM_GUARD.items():
        d, ci = diff(zoom, sub, c)
        checks.append(dict(check="có zoom: không tụt", cls=c, subset=sub, diff=d, ci=ci, need=f">= -{cfg['max_drop']}", ok=d >= -cfg["max_drop"]))
    return checks, all(x["ok"] for x in checks)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", default="c8lab_c6_vs_c9", help="tên file 04j: c6_ft rồi C9-ft, cả ảnh")
    ap.add_argument("--zoom", default="c8lab_c6crop_vs_c9crop", help="tên file 04j: c6_ft + zoom rồi C9-ft + zoom")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = yaml.safe_load((ROOT / "configs" / "ppe6.yaml").read_text(encoding="utf-8"))["c9_decision"]
    full, zoom = (json.loads((OUT / f"{n}.json").read_text(encoding="utf-8")) for n in (args.full, args.zoom))
    for name, res in ((args.full, full), (args.zoom, zoom)):
        runs = list(res["runs"])
        if res["split"] != "val" or len(runs) != 2 or not runs[0].startswith(cfg["baseline"]):
            sys.exit(f"{name}: cần split val, hai run, run đầu là {cfg['baseline']} (thấy {res['split']}, {runs})")
    checks, ok = decide(full, zoom, cfg)
    for x in checks:
        print(f"{x['check']:20s} {x['cls']:8s} ({x['subset']:11s}) {x['diff']:+.4f} {x['ci']}  cần {x['need']:7s} -> {'đạt' if x['ok'] else 'KHÔNG ĐẠT'}")
    print("Kết luận:", "C9-ft ĐẠT c9_decision" if ok else "C9-ft KHÔNG ĐẠT c9_decision", "(người dùng quyết định cuối)")
    out = dict(criteria=cfg, full=args.full, zoom=args.zoom, checks=checks, passed=ok, note="nhãn máy, có kiểm định mẫu của người; điểm ước lượng mAP50 val")
    (OUT / "c9_decision.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
