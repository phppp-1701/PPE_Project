"""Bước phụ của gán PPE: tìm cổ tay bằng YOLO11n-pose (spec 5.2, công thức 3.5). Giữ trọng số tiền huấn luyện.

Chạy theo lô trên ảnh cắt từng người rồi ghi cổ tay vào track.extra["wrists"] = {"left": (x, y, conf), "right": ...}.
`left`, `right` theo ảnh, như vùng tay: cổ tay có x nhỏ hơn là `left`. Không tìm được thì không có khóa "wrists".
"""

import numpy as np

LEFT_WRIST, RIGHT_WRIST = 9, 10    # chỉ số điểm khớp COCO


class PoseEstimator:
    def __init__(self, cfg, root):
        from ultralytics import YOLO

        p = cfg["pose"]
        self.margin, self.imgsz, self.conf = p["margin"], p["imgsz"], p["conf"]
        self.device = cfg["detector"]["device"]
        self.model = YOLO(root / p["weights"])

    def __call__(self, frame, tracks):
        h, w = frame.shape[:2]
        crops, kept = [], []
        for t in tracks:
            x1, y1, x2, y2 = t.xyxy
            mw, mh = self.margin * (x2 - x1), self.margin * (y2 - y1)
            a, b, c, d = int(max(x1 - mw, 0)), int(max(y1 - mh, 0)), int(min(x2 + mw, w)), int(min(y2 + mh, h))
            if c - a >= 2 and d - b >= 2:
                crops.append(frame[b:d, a:c])
                kept.append((t, a, b, c - a))
        if not crops:
            return
        results = self.model.predict(crops, imgsz=self.imgsz, conf=self.conf, device=self.device, verbose=False)
        for (t, ox, oy, cw), r in zip(kept, results):
            if r.keypoints is None or not len(r.keypoints.data):
                continue
            boxes = r.boxes.xyxy.cpu().numpy()
            # Ảnh cắt có thể có người khác: lấy người lớn và gần giữa ảnh cắt nhất.
            k = int(np.argmax([(b[2] - b[0]) * (b[3] - b[1]) - abs((b[0] + b[2]) / 2 - cw / 2) * 50 for b in boxes]))
            kp = r.keypoints.data[k].cpu().numpy()
            pts = sorted(((float(kp[i][0]) + ox, float(kp[i][1]) + oy, float(kp[i][2]))
                          for i in (LEFT_WRIST, RIGHT_WRIST)), key=lambda q: q[0])
            t.extra["wrists"] = {"left": pts[0], "right": pts[1]}
