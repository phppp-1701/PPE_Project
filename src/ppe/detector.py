"""Bước 1: YOLO11s phát hiện người và PPE (spec 5.1). Tọa độ trả về theo pixel ảnh gốc."""

import numpy as np

from . import Det, require


class Detector:
    def __init__(self, cfg, root):
        from ultralytics import YOLO

        d = cfg["detector"]
        self.conf = require(cfg, "detector", "conf")
        self.nms_iou = require(cfg, "detector", "nms_iou")
        self.imgsz, self.device = d["imgsz"], d["device"]
        self.person_cls = cfg["person_cls"]
        self.names = {cfg["person_cls"]: "person", **{p["cls"]: name for name, p in cfg["ppe"].items()}}
        # Hộp người dưới ngưỡng conf vẫn cần cho bước ghép thứ hai của ByteTrack (track_low_thresh).
        self.person_min = min(self.conf["person"], cfg["tracker"]["track_low_thresh"])
        self.predict_conf = min([self.person_min] + [self.conf[n] for n in self.names.values()])
        self.model = YOLO(root / d["weights"])
        bad = {c: n for c, n in self.names.items() if self.model.names.get(c) != n}
        assert not bad, f"lớp của mô hình {self.model.names} khác cấu hình {bad}"

    def __call__(self, frame):
        """(danh sách hộp người kể cả conf thấp, danh sách hộp PPE đã lọc theo conf từng lớp)."""
        r = self.model.predict(frame, imgsz=self.imgsz, conf=self.predict_conf, iou=self.nms_iou,
                               device=self.device, verbose=False)[0]
        boxes = r.boxes.cpu().numpy()
        persons, ppe = [], []
        for c, xyxy, s in zip(boxes.cls.astype(int), boxes.xyxy, boxes.conf):
            name = self.names.get(int(c))
            if name is None:
                continue
            det = Det(int(c), np.asarray(xyxy, dtype=float), float(s))
            if c == self.person_cls:
                if s >= self.person_min:
                    persons.append(det)
            elif s >= self.conf[name]:
                ppe.append(det)
        return persons, ppe
