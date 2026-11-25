"""Bước 1: YOLO11s phát hiện người và PPE (spec 5.1). Tọa độ trả về theo pixel ảnh gốc.

`detector.ppe_source` (configs/pipeline.yaml):
    full: PPE lấy từ lần dò trên cả khung.
    crop: người dò trên cả khung; PPE dò trên ảnh cắt từng người đạt conf person (nới `crop.margin`
          mỗi phía), cùng trọng số, cỡ `crop.imgsz`, ngưỡng `crop.conf`. Giúp người nhỏ (camera xa).
    auto: như crop nhưng chỉ cho người cao dưới `crop.max_person_px` (đo ở đầu vào `imgsz`); người lớn hơn
          dùng PPE dò trên cả khung.

`detector.zoom` (C9, tùy chọn, `enabled`): với `full` / `auto`, người đạt conf person mà vùng cắt (nới `zoom.pad`) có cạnh
dài ≥ `min_side_ratio` × `zoom.imgsz` ở ảnh gốc (không thuộc nhóm người nhỏ của `auto`) được dò lại ở `zoom.imgsz`; hộp
lớp `zoom.classes` nhân conf với `conf_scale`, lọc theo `detector.conf`, rồi gộp với PPE cả khung bằng NMS theo lớp
(`zoom.nms_iou`); chạy mỗi `zoom.every_n_frames` khung (cửa sổ thời gian gộp quan sát). Như `scripts/04m_crop_pass.py` (chấm trên val, `configs/ppe6.yaml` mục `crop_pass`).
"""

import numpy as np

from . import Det, require


def letterbox_square(img, size):
    """Thu ảnh về cạnh dài `size`, đệm xám (114) thành vuông size x size. Trả về (ảnh, tỉ lệ, dx, dy).

    Mọi ảnh cắt cùng một cỡ đầu vào: đo 20/11/2026, ảnh cắt chữ nhật mỗi lần một cỡ làm một lần dò lâu tới khoảng 0,9 giây."""
    import cv2

    h, w = img.shape[:2]
    r = size / max(h, w)
    nw, nh = max(1, round(w * r)), max(1, round(h * r))
    out = np.full((size, size, 3), 114, dtype=img.dtype)
    dx, dy = (size - nw) // 2, (size - nh) // 2
    out[dy:dy + nh, dx:dx + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    return out, r, dx, dy


def unletterbox(xyxy, r, dx, dy, ox, oy):
    """Hộp trên ảnh vuông của letterbox_square -> toạ độ khung gốc (ảnh cắt bắt đầu ở ox, oy)."""
    return (np.asarray(xyxy, dtype=float) - [dx, dy, dx, dy]) / r + [ox, oy, ox, oy]


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
        z = d.get("zoom") or {}
        self.zoom = require(cfg, "detector", "zoom") if z.get("enabled") else None
        if self.zoom is not None:
            assert self.source in ("full", "auto"), "detector.zoom chỉ dùng với ppe_source full / auto"
            self.zoom_names = {c: self.names[c] for c in self.zoom["classes"]}
        if self.source == "crop":
            self.predict_conf = self.person_min       # khung đầy đủ: chỉ cần người
        else:
            self.predict_conf = min([self.person_min] + [self.conf[n] for n in self.names.values()])
        self.model = YOLO(root / d["weights"])
        # Bản mô hình riêng cho zoom: một đối tượng YOLO đổi qua lại cỡ ảnh / FP16 giữa hai lần gọi thì Ultralytics dựng lại
        # bộ suy luận mỗi lần (đo 20/11/2026 trên video4: 240 ms/khung với FP16, 60 ms/khung với FP32).
        self.zoom_model = YOLO(root / d["weights"]) if self.zoom is not None else None
        if self.zoom_model is not None:   # lần dò đầu (và mỗi cỡ lô mới) mất khoảng 1,8 giây: khởi động trước, dò từng ảnh
            self._zoom_predict(np.zeros((self.zoom["imgsz"], self.zoom["imgsz"], 3), dtype=np.uint8), 0.5)
        self.frame_idx = -1
        # F2 (2026-11-25_close_range_fixes): hộp PPE điểm thấp (hold_conf <= điểm < ngưỡng lớp) cho bước nhớ PPE.
        mem = (cfg.get("compliance") or {}).get("ppe_memory")
        self.hold_conf = mem["hold_conf"] if mem else None
        if self.hold_conf is not None:
            assert self.hold_conf >= self.predict_conf or self.source == "crop", \
                "compliance.ppe_memory.hold_conf phải >= mức dò thấp nhất của detector"
        self.weak = []
        bad ={c: n for c, n in self.names.items() if self.model.names.get(c) != n}
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

    def _zoom_box(self, p, w, h):
        m = self.zoom["pad"]
        pw, ph = p.xyxy[2] - p.xyxy[0], p.xyxy[3] - p.xyxy[1]
        return (int(max(0, p.xyxy[0] - m * pw)), int(max(0, p.xyxy[1] - m * ph)),
                int(min(w, p.xyxy[2] + m * pw)), int(min(h, p.xyxy[3] + m * ph)))

    def _zoom_predict(self, img, conf):
        """Một ảnh vuông mỗi lần (lô cỡ 1 cố định): đo 20/11/2026, lô 2 ảnh mất gần bằng hai lần lô 1 ảnh, còn mỗi cỡ lô
        mới làm lần dò đó chậm khoảng 1,8 giây."""
        return self.zoom_model.predict(img, imgsz=self.zoom["imgsz"], conf=conf, iou=self.nms_iou, device=self.device,
                                       verbose=False, quantize=16 if self.zoom["half"] else None)[0]

    def _zoom_ppe(self, frame, persons, ppe):
        """C9: dò lại lớp `zoom.classes` trên ảnh cắt của người lớn, gộp với `ppe` (đã lọc conf) bằng NMS theo lớp."""
        h, w = frame.shape[:2]
        crops, offs = [], []
        for p in persons:
            x1, y1, x2, y2 = self._zoom_box(p, w, h)
            if max(x2 - x1, y2 - y1) >= self.zoom["min_side_ratio"] * self.zoom["imgsz"]:
                sq, r, dx, dy = letterbox_square(frame[y1:y2, x1:x2], self.zoom["imgsz"])
                crops.append(sq)
                offs.append((r, dx, dy, x1, y1))
        if not crops:
            return ppe
        scale = self.zoom["conf_scale"]
        min_conf = min(self.conf[n] for n in self.zoom_names.values()) / scale
        res = [self._zoom_predict(c, min_conf) for c in crops]
        add = [Det(c, unletterbox(b, *off), s * scale) for off, r in zip(offs, res) for c, b, s in self._boxes(r)
               if c in self.zoom_names and s * scale >= self.conf[self.zoom_names[c]]]
        if not add:
            return ppe
        import torch
        from torchvision.ops import batched_nms

        keep_other = [d for d in ppe if d.cls not in self.zoom_names]
        pool = [d for d in ppe if d.cls in self.zoom_names] + add
        xy = torch.tensor(np.array([d.xyxy for d in pool]), dtype=torch.float32)
        sc = torch.tensor([d.conf for d in pool], dtype=torch.float32)
        cl = torch.tensor([d.cls for d in pool])
        keep = batched_nms(xy, sc, cl, self.zoom["nms_iou"]).numpy()
        return keep_other + [pool[i] for i in keep]

    def __call__(self, frame):
        """(danh sách hộp người kể cả conf thấp, danh sách hộp PPE đã lọc theo conf từng lớp)."""
        r = self.model.predict(frame, imgsz=self.imgsz, conf=self.predict_conf, iou=self.nms_iou,
                               device=self.device, verbose=False)[0]
        persons, ppe = [], []
        self.weak = []
        for c, xyxy, s in self._boxes(r):
            name = self.names.get(c)
            if name is None:
                continue
            if c == self.person_cls:
                if s >= self.person_min:
                    persons.append(Det(c, xyxy, s))
            elif self.source != "crop" and s >= self.conf[name]:
                ppe.append(Det(c, xyxy, s))
            elif self.source != "crop" and self.hold_conf is not None and s >= self.hold_conf:
                self.weak.append(Det(c, xyxy, s))
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
        self.frame_idx += 1
        if self.zoom is not None and self.frame_idx % self.zoom["every_n_frames"] == 0:
            if self.source == "auto":
                scale = self.imgsz / max(frame.shape[:2])
                large = [p for p in confident if (p.xyxy[3] - p.xyxy[1]) * scale >= self.crop["max_person_px"]]
            else:
                large = confident
            if large:
                ppe = self._zoom_ppe(frame, large, ppe)
        return persons, ppe
