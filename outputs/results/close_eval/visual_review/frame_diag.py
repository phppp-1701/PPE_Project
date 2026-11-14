"""Chẩn đoán chỉ đọc các lỗi người dùng ghi bằng mắt (visual_notes.txt) trên video đã vẽ bằng cấu hình đóng băng.

Chạy lại đúng Pipeline (configs/pipeline.yaml, commit nguồn trong ../manifest.json) từ khung 0 tới khung cần xem (để
theo dõi, cửa sổ thời gian có cùng trạng thái), ghi tại mỗi khung đích: hộp detector đã qua ngưỡng, ứng viên dưới
ngưỡng (dò lại cả khung với conf 0,03, chỉ để xem detector có thấy mờ mờ không), người và keypoint, xác suất bộ phân
loại, PPE gán / bị loại (lý do), trạng thái và chi tiết từng PPE. Lưu ảnh khung đã vẽ để đối chiếu.
Không sửa gì, không dùng để chọn tham số.

Cách chạy (từ thư mục gốc, .venv):
    python outputs/results/close_eval/visual_review/frame_diag.py video13:108 video13:240 ...
Ghi outputs/results/close_eval/visual_review/frame_diag.json và <video>_f<khung>.jpg
"""

import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")
import cv2  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
from ppe import load_config  # noqa: E402
from ppe.pipeline import Pipeline  # noqa: E402

KP = {"mui": 0, "mat_T": 1, "mat_P": 2, "tai_T": 3, "tai_P": 4, "vai_T": 5, "vai_P": 6, "co_tay_T": 9, "co_tay_P": 10,
      "hong_T": 11, "hong_P": 12, "mat_ca_T": 15, "mat_ca_P": 16}


def r2(x):
    return [round(float(v), 1) for v in x]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    want = defaultdict(set)
    for a in sys.argv[1:]:
        v, f = a.split(":")
        want[v].add(int(f))
    cfg = load_config()
    cfg["events"]["evidence_dir"] = tempfile.mkdtemp(prefix="ppe_vdiag_")
    names = {p["cls"]: n for n, p in cfg["ppe"].items()}
    res = {}
    for v, frames in want.items():
        pipe = Pipeline("diag", f"diag_{v}", stage="full", cfg=cfg)
        cap = cv2.VideoCapture(str(ROOT / "data" / "videos" / f"{v}.mp4"))
        ann = cv2.VideoCapture(str(HERE.parent / "annotated" / v / "annotated.mp4"))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        i = 0
        while i <= max(frames):
            ok, frame = cap.read()
            ok2, aframe = ann.read()
            if not ok:
                break
            out = pipe.process(frame, i / fps)
            if i in frames:
                low = pipe.detector.model.predict(frame, imgsz=cfg["detector"]["imgsz"], conf=0.03,
                                                  iou=cfg["detector"]["nms_iou"], device=cfg["detector"]["device"],
                                                  verbose=False)[0].boxes.cpu().numpy()
                cand = sorted([dict(ppe=names.get(int(c), "person"), conf=round(float(s), 3), box=r2(b))
                               for c, b, s in zip(low.cls, low.xyxy, low.conf) if int(c) in names],
                              key=lambda d: -d["conf"])
                tracks = []
                for t in out["tracks"]:
                    kps = t.extra.get("kps")
                    st = out["states"][t.track_id]
                    tracks.append(dict(
                        id=t.track_id, box=r2(t.xyxy), det_conf=round(float(t.det_conf), 3), confident=t.confident,
                        kps_conf={k: round(float(kps[j][2]), 2) for k, j in KP.items()} if kps else None,
                        shoulders_reversed=bool(kps and kps[5][0] < kps[6][0]) if kps else None,
                        parts={f"{p}/{s}": round(float(q), 4) for (p, s), q in t.extra.get("parts", {}).items()},
                        owned={f"{p}/{s}": [round(float(d.conf), 3) for d in ds]
                               for (p, s), ds in out["assoc"].owned.get(t.track_id, {}).items() if ds},
                        states={p: dict(state=x["state"], sides={str(s): dict(state=a, **{k: (bool(w) if isinstance(w, (bool,)) else w) for k, w in d.items()})
                                                                    for s, (a, d) in x["sides"].items()})
                                for p, x in st.items()},
                        temporal={p: str(c) for p, c in (out.get("checks", {}).get(t.track_id) or {}).items()}))
                rej = [dict(ppe=p, conf=round(float(d.conf), 3), box=r2(d.xyxy), reason=why,
                            cand=[(round(float(c[0]), 3), c[1], c[2]) for c in cs] if cs and isinstance(cs[0], tuple) else str(cs))
                       for p, d, why, cs in out["assoc"].rejected]
                dets = [dict(ppe=names.get(d.cls), conf=round(float(d.conf), 3), box=r2(d.xyxy)) for d in out["ppe"]]
                res[f"{v}:{i}"] = dict(t=round(i / fps, 3), detections=dets, rejected=rej, tracks=tracks,
                                       low_conf_candidates=cand[:15])
                if ok2:
                    cv2.imwrite(str(HERE / f"{v}_f{i}.jpg"), aframe)
            i += 1
        cap.release()
        ann.release()
    (HERE / "frame_diag.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("Ghi", (HERE / "frame_diag.json").relative_to(ROOT))


if __name__ == "__main__":
    main()
