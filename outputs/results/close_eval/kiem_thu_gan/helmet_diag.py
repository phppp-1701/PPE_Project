"""Phân tích chỉ đọc (giai đoạn 5): vì sao mũ bản 4 không đổi kết quả trên một video kiem_thu_gan.

Chạy lại đúng Pipeline của cấu hình đóng băng (configs/pipeline.yaml ở commit nguồn trong manifest.json), không sửa
gì, chỉ ghi thêm chi tiết của PPE mũ mỗi khung: có ảnh cắt vùng đầu không (track.extra["parts"]), p có mũ, phiếu
(pos/neg/unsure/None), detector có hộp mũ gán cho người không (has), vùng đầu quan sát được không (observable).
Không dùng để chỉnh ngưỡng hay logic (tập kiem_thu_gan chỉ báo).

Cách chạy (từ thư mục gốc, .venv): python outputs/results/close_eval/kiem_thu_gan/helmet_diag.py video17
Ghi outputs/results/close_eval/kiem_thu_gan/helmet_diag_<video>.json (và .jpg: tối đa 8 ảnh cắt vùng đầu, mỗi 60 khung)
"""

import collections
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
import cv2  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from ppe import load_config  # noqa: E402
from ppe.parts import cut, part_boxes  # noqa: E402
from ppe.pipeline import Pipeline  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    video = sys.argv[1]
    sp = importlib.util.spec_from_file_location("e", ROOT / "scripts" / "06b_evaluate_close_videos.py")
    e = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(e)
    cfg = load_config()
    cfg["events"]["evidence_dir"] = tempfile.mkdtemp(prefix="ppe_diag_")
    labels = e.load_labels(ROOT / f"data/videos/{video}_machine_cvat.zip")
    thr = cfg["calibration"]["video"]["match_iou"]
    pipe = Pipeline("diag", f"diag_{video}", stage="full", cfg=cfg)
    cap = cv2.VideoCapture(str(ROOT / "data" / "videos" / f"{video}.mp4"))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    c = collections.Counter()
    rows, i, sheet = [], 0, []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        out = pipe.process(frame, i / fps)
        for t in out["tracks"]:
            st = out["states"][t.track_id]["helmet"]
            d = st["sides"][None][1]
            p = t.extra.get("parts", {}).get(("helmet", None))
            gl = None
            for _, gb, gs in labels.get(i, []):
                if e.iou(gb, list(t.xyxy)) >= thr:
                    gl = gs["helmet"]
            kps = t.extra.get("kps")
            hb = [b for n, _, b in part_boxes(kps, cfg["part_cls"]["geometry"], cfg["part_cls"]["kp_conf"])
                  if n == "helmet"] if kps else []
            if hb and i % 60 == 0 and len(sheet) < 8:     # ảnh cắt đúng như PartClassifier đưa vào mô hình
                cr = cut(frame, hb[0], cfg["part_cls"]["min_px"])
                if cr is not None:
                    sheet.append((i, p, cv2.resize(cr, (200, 200))))
            key = dict(label=gl, pred=st["state"], crop=p is not None, vote=d.get("vote"), has=d["has"],
                       observable=d["observable"], kps=kps is not None)
            c[tuple(key.items())] += 1
            rows.append(dict(frame=i, track=t.track_id, p=None if p is None else round(p, 4),
                             head_box=[round(float(x), 1) for x in hb[0]] if hb else None, **key))
        i += 1
    pipe.close(i / fps)
    summary = [dict(dict(k), frames=n) for k, n in c.most_common()]
    out = ROOT / "outputs" / "results" / "close_eval" / "kiem_thu_gan" / f"helmet_diag_{video}.json"
    out.write_text(json.dumps(dict(video=video, note="phân tích chỉ đọc, cấu hình đóng băng", summary=summary,
                                   rows=rows), ensure_ascii=False, indent=1), encoding="utf-8")
    if sheet:
        import numpy as np
        tiles = []
        for f, pv, im in sheet:
            im = im.copy()
            cv2.putText(im, f"f{f} p={pv:.3f}", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
            tiles.append(im)
        while len(tiles) % 4:
            tiles.append(np.zeros_like(tiles[0]))
        grid = np.vstack([np.hstack(tiles[k:k + 4]) for k in range(0, len(tiles), 4)])
        cv2.imwrite(str(out.with_suffix(".jpg")), grid)
    for s in summary:
        print(s)
    ps = [r["p"] for r in rows if r["p"] is not None and r["label"] == "co"]
    if ps:
        ps.sort()
        print(f"p có mũ trên khung nhãn Có có ảnh cắt: n={len(ps)}, min {ps[0]}, trung vị {ps[len(ps) // 2]}, max {ps[-1]}")
    print("Ghi", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
