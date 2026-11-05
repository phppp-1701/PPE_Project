"""Bước 3: gán PPE cho người theo vùng cơ thể (spec 5.2, mục 3.4.3).

Vùng là hình chữ nhật trong tọa độ chuẩn hóa của hộp người (configs/pipeline.yaml: association.regions).
PPE có `sides` (găng) dùng hai nửa vùng: trái x < 0.5, phải x >= 0.5 (theo ảnh).
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from . import require

SIDES = ("left", "right")


def region_box(track_xyxy, reg, side=None):
    """Vùng (x1, y1, x2, y2) theo pixel; side = None (cả vùng), "left" hoặc "right"."""
    x1, y1, x2, y2 = track_xyxy
    w, h = x2 - x1, y2 - y1
    rx0, rx1 = reg["x0"], reg["x1"]
    if side == "left":
        rx1 = 0.5
    elif side == "right":
        rx0 = 0.5
    return np.array([x1 + rx0 * w, y1 + reg["y0"] * h, x1 + rx1 * w, y1 + reg["y1"] * h], dtype=float)


def valid_wrist(track, side, pose):
    """Cổ tay bên `side` nếu có và đạt độ tin cậy `pose.wrist_conf`, ngược lại None (spec 5.2)."""
    q = track.extra.get("wrists", {}).get(side)
    return q if q is not None and q[2] >= pose["wrist_conf"] else None


def wrist_box(track_xyxy, q, pose):
    """Hình chữ nhật bao elip quanh cổ tay q (công thức 3.5)."""
    w, h = track_xyxy[2] - track_xyxy[0], track_xyxy[3] - track_xyxy[1]
    rx, ry = pose["rho_x"] * w, pose["rho_y"] * h
    return np.array([q[0] - rx, q[1] - ry, q[0] + rx, q[1] + ry], dtype=float)


def ellipse_value(c, track_xyxy, q, pose):
    """Căn bậc hai vế trái công thức 3.5: <= 1 là tâm PPE nằm trong elip."""
    w, h = track_xyxy[2] - track_xyxy[0], track_xyxy[3] - track_xyxy[1]
    return math.hypot((c[0] - q[0]) / (pose["rho_x"] * w), (c[1] - q[1]) / (pose["rho_y"] * h))


def norm_distance(c, track_xyxy, rbox):
    """Khoảng cách chuẩn hóa (3.4) từ tâm PPE c tới tâm vùng rbox."""
    w, h = track_xyxy[2] - track_xyxy[0], track_xyxy[3] - track_xyxy[1]
    ax, ay = (rbox[0] + rbox[2]) / 2, (rbox[1] + rbox[3]) / 2
    return math.hypot((c[0] - ax) / w, (c[1] - ay) / h)


@dataclass
class Association:
    owned: dict = field(default_factory=lambda: defaultdict(lambda: defaultdict(list)))   # tid -> (ppe, side) -> [Det]
    contested: dict = field(default_factory=lambda: defaultdict(set))                     # tid -> {(ppe, side)}
    rejected: list = field(default_factory=list)                                          # (ppe, Det, lý do, ứng viên)


class Associator:
    def __init__(self, cfg):
        self.ppe = cfg["ppe"]
        self.regions = {p["region"]: require(cfg, "association", "regions", p["region"]) for p in self.ppe.values()}
        self.max_distance = require(cfg, "association", "max_distance")
        self.margin = cfg["association"]["ambiguity_margin"]   # null: từ 2 ứng viên trở lên là tranh chấp
        self.by_cls = {p["cls"]: name for name, p in self.ppe.items()}
        self.pose = cfg["pose"] if cfg.get("pose", {}).get("enabled") else None

    def limit(self, name):
        """Khoảng cách tối đa: 1 (biên elip) khi dùng cổ tay, còn lại `max_distance` (3.4)."""
        return 1.0 if self.pose and self.ppe[name]["sides"] else self.max_distance[name]

    def candidates(self, name, det, tracks):
        """[(d, track_id, side)] của các vùng chứa tâm PPE, sắp theo d tăng dần."""
        p = self.ppe[name]
        reg = self.regions[p["region"]]
        c = det.center
        out = []
        for t in tracks:
            for side in (SIDES if p["sides"] else (None,)):
                if self.pose and p["sides"]:
                    q = valid_wrist(t, side, self.pose)
                    if q is not None and (v := ellipse_value(c, t.xyxy, q, self.pose)) <= 1:
                        out.append((v, t.track_id, side))
                    continue
                r = region_box(t.xyxy, reg, side)
                if r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3]:
                    out.append((norm_distance(c, t.xyxy, r), t.track_id, side))
        return sorted(out, key=lambda x: x[0])

    def __call__(self, tracks, ppe_dets):
        a = Association()
        for det in ppe_dets:
            name = self.by_cls.get(det.cls)
            if name is None:
                continue
            cand = self.candidates(name, det, tracks)
            if not cand:
                a.rejected.append((name, det, "outside", []))
                continue
            limit = self.limit(name)
            if cand[0][0] > limit:
                a.rejected.append((name, det, "far", cand))
                continue
            near = [x for x in cand if x[0] <= limit]
            if len(near) >= 2 and (self.margin is None or near[1][0] - near[0][0] < self.margin):
                for _, tid, side in near:
                    a.contested[tid].add((name, side))
                a.rejected.append((name, det, "contested", near))
                continue
            _, tid, side = near[0]
            a.owned[tid][(name, side)].append(det)
        return a
