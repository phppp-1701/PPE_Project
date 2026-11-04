"""Bước 1: YOLO11s phát hiện người và PPE (spec 5.1). Tọa độ trả về theo pixel ảnh gốc.

`detector.ppe_source` (configs/pipeline.yaml):
    full: PPE lấy từ lần dò trên cả khung.
    crop: người dò trên cả khung; PPE dò trên ảnh cắt từng người đạt conf person (nới `crop.margin`
          mỗi phía), cùng trọng số, cỡ `crop.imgsz`, ngưỡng `crop.conf`. Giúp người nhỏ (camera xa).
    auto: như crop nhưng chỉ cho người cao dưới `crop.max_person_px` (đo ở đầu vào `imgsz`); người lớn hơn
          dùng PPE dò trên cả khung.
"""

import numpy as np

from . import Det, require


class Detector:
    def __init__(self, cfg, root):
        from ultralytics import YOLO

        d = cfg["detector"]
        self.conf = require(cfg, "detector", "conf")
        self.nms_iou = require(cfg, "detector", "nms_iou")
        self.source = require(cfg, "detector", "ppe_source")
        self.imgsz, self.device = d["imgsz"], d["device"]
        self.person_cls = cfg["person_cls"]
        self.names = {cfg["person_cls"]: "person", **{p["cls"]: name for name, p in cfg["ppe"].items()}}
        # Hộp người dưới ngưỡng conf vẫn cần cho bước ghép thứ hai của ByteTrack (track_low_thresh).
        self.person_min = min(self.conf["person"], cfg["tracker"]["track_low_thresh"])
        if self.source in ("crop", "auto"):
            self.crop = require(cfg, "detector", "crop")
            self.crop_conf = require(cfg, "detector", "crop", "conf")
        if self.source == "crop":
            self.predict_conf = self.person_min       # khung đầy đủ: chỉ cần người
        else:
            self.predict_conf = min([self.person_min] + [self.conf[n] for n in self.names.values()])
        self.model = YOLO(root / d["weights"])
        bad = {c: n for c, n in self.names.items() if self.model.names.get(c) != n}
        assert not bad, f"lớp của mô hình {self.model.names} khác cấu hình {bad}"

    def _boxes(self, r, offset=(0, 0)):
        b = r.boxes.cpu().numpy()
        off = np.array([offset[0], offset[1], offset[0], offset[1]], dtype=float)
        return [(int(c), np.asarray(xy, dtype=float) + off, float(s)) for c, xy, s in zip(b.cls, b.xyxy, b.conf)]

    def _crop_box(self, p, w, h):
        m = self.crop["margin"]
        pw, ph = p.xyxy[2] - p.xyxy[0], p.xyxy[3] - p.xyxy[1]
        return (int(max(0, p.xyxy[0] - m * pw)), int(max(0, p.xyxy[1] - m * ph)),
                int(min(w, p.xyxy[2] + m * pw)), int(min(h, p.xyxy[3] + m * ph)))

    def _crop_ppe(self, frame, persons):
        """PPE dò trên ảnh cắt của các người cho trước; tọa độ quy về khung gốc."""
        h, w = frame.shape[:2]
        crops, offs = [], []
        for p in persons:
            x1, y1, x2, y2 = self._crop_box(p, w, h)
            if x2 - x1 >= 2 and y2 - y1 >= 2:
                crops.append(frame[y1:y2, x1:x2])
                offs.append((x1, y1))
        if not crops:
            return []
        min_conf = min(self.crop_conf[n] for n in self.crop_conf)
        res = self.model.predict(crops, imgsz=self.crop["imgsz"], conf=min_conf, iou=self.nms_iou,
                                 device=self.device, verbose=False)
        dets = [x for off, r in zip(offs, res) for x in self._boxes(r, off) if x[0] != self.person_cls]
        if not dets:
            return []
        # Người đứng gần nhau có ảnh cắt chồng lên nhau -> cùng một PPE bị dò hai lần: NMS lại theo lớp.
        import torch
        from torchvision.ops import batched_nms

        xy = torch.tensor(np.array([d[1] for d in dets]), dtype=torch.float32)
        sc = torch.tensor([d[2] for d in dets], dtype=torch.float32)
        cl = torch.tensor([d[0] for d in dets])
        keep = batched_nms(xy, sc, cl, self.nms_iou).numpy()
        out = []
        for i in keep:
            c, b, s = dets[i]
            name = self.names.get(c)
            if name is not None and s >= self.crop_conf[name]:
                out.append(Det(c, b, s))
        return out

    def __call__(self, frame):
        """(danh sách hộp người kể cả conf thấp, danh sách hộp PPE đã lọc theo conf từng lớp)."""
        r = self.model.predict(frame, imgsz=self.imgsz, conf=self.predict_conf, iou=self.nms_iou,
                               device=self.device, verbose=False)[0]
        persons, ppe = [], []
        for c, xyxy, s in self._boxes(r):
            name = self.names.get(c)
            if name is None:
                continue
            if c == self.person_cls:
                if s >= self.person_min:
                    persons.append(Det(c, xyxy, s))
            elif self.source != "crop" and s >= self.conf[name]:
                ppe.append(Det(c, xyxy, s))
        confident = [p for p in persons if p.conf >= self.conf["person"]]
        if self.source == "crop":
            ppe = self._crop_ppe(frame, confident)
        elif self.source == "auto":
            scale = self.imgsz / max(frame.shape[:2])
            small = [p for p in confident if (p.xyxy[3] - p.xyxy[1]) * scale < self.crop["max_person_px"]]
            if small:
                h, w = frame.shape[:2]
                areas = [self._crop_box(p, w, h) for p in small]
                small_ids = {id(p) for p in small}
                big = [p.xyxy for p in confident if id(p) not in small_ids]

                def in_box(c, b):
                    return b[0] <= c[0] <= b[2] and b[1] <= c[1] <= b[3]

                # PPE cả khung nằm trong vùng người nhỏ (và không thuộc người lớn nào) được thay bằng PPE ảnh cắt.
                ppe = [d for d in ppe if not any(in_box(d.center, a) for a in areas)
                       or any(in_box(d.center, b) for b in big)]
                ppe += self._crop_ppe(frame, small)
        return persons, ppe
