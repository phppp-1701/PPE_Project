"""Bước 4: kiểm tra khả năng quan sát và kết luận ba trạng thái (spec 5.3, mục 3.4.4, Bảng 3.5).

Không phát hiện được PPE không đồng nghĩa với Thiếu: chỉ kết luận Thiếu khi vùng đủ quan sát (O = 1),
không có PPE gán hợp lệ và không còn tranh chấp.
"""

import math

import numpy as np

from . import HAVE, MISSING, UNKNOWN, box_area, intersect, require
from .association import SIDES, region_box, valid_wrist, wrist_box

GRID = 100   # số ô tối đa mỗi chiều khi tính diện tích bị người khác che (xấp xỉ, đủ cho tỉ lệ)


def occluded_fraction(r, others):
    """Tỉ lệ diện tích vùng r nằm trong hợp các hộp người khác (o trong công thức 3.6)."""
    if not others or box_area(r) <= 0:
        return 0.0
    step = max(1.0, math.ceil(max(r[2] - r[0], r[3] - r[1]) / GRID))
    xs = np.arange(r[0] + step / 2, r[2], step)
    ys = np.arange(r[1] + step / 2, r[3], step)
    if len(xs) == 0 or len(ys) == 0:
        return 0.0
    gx, gy = np.meshgrid(xs, ys)
    covered = np.zeros(gx.shape, dtype=bool)
    for b in others:
        covered |= (gx >= b[0]) & (gx <= b[2]) & (gy >= b[1]) & (gy <= b[3])
    return float(covered.mean())


class Compliance:
    def __init__(self, cfg):
        self.ppe = cfg["ppe"]
        self.regions = {p["region"]: require(cfg, "association", "regions", p["region"]) for p in self.ppe.values()}
        self.tau_in = require(cfg, "compliance", "tau_in")
        self.tau_occ = require(cfg, "compliance", "tau_occ")
        self.area_min = require(cfg, "compliance", "area_min_px")
        self.pose = cfg["pose"] if cfg.get("pose", {}).get("enabled") else None

    def side_state(self, name, track, side, assoc, frame_box, others):
        p = self.ppe[name]
        if self.pose and p["sides"] and p["region"] == "hands":
            # Có pose: không thấy cổ tay đạt ngưỡng thì tay đó không quan sát được (G = 0), không suy ra Thiếu.
            q = valid_wrist(track, side, self.pose)
            if q is None:
                return UNKNOWN, dict(v=0.0, o=0.0, area=0, observable=False, has=False, contested=False)
            r = wrist_box(track.xyxy, q, self.pose)
        else:
            r = region_box(track.xyxy, self.regions[self.ppe[name]["region"]], side)
        area_r = box_area(r)
        visible = box_area(intersect(r, frame_box))
        v = visible / area_r if area_r > 0 else 0.0
        o = occluded_fraction(r, others)
        observable = (v >= self.tau_in[name] and o <= self.tau_occ[name] and visible >= self.area_min[name]
                      and track.confident)
        has = bool(assoc.owned.get(track.track_id, {}).get((name, side)))
        contested = (name, side) in assoc.contested.get(track.track_id, set())
        if track.confident and has:
            state = HAVE
        elif observable and not contested:
            state = MISSING
        else:
            state = UNKNOWN
        return state, dict(v=round(v, 3), o=round(o, 3), area=round(visible), observable=observable,
                           has=has, contested=contested)

    def __call__(self, tracks, assoc, frame_shape, names=None):
        """{track_id: {ppe: {"state", "sides": {side: (state, chi tiết)}}}} cho các PPE trong `names`."""
        h, w = frame_shape[:2]
        frame_box = np.array([0, 0, w, h], dtype=float)
        out = {}
        for t in tracks:
            others = [o.xyxy for o in tracks if o.track_id != t.track_id]
            res = {}
            for name in (names or self.ppe):
                sides = SIDES if self.ppe[name]["sides"] else (None,)
                per = {s: self.side_state(name, t, s, assoc, frame_box, others) for s in sides}
                states = [st for st, _ in per.values()]
                if MISSING in states:          # găng: một tay nhìn rõ mà không có găng -> Thiếu
                    state = MISSING
                elif all(st == HAVE for st in states):
                    state = HAVE
                else:
                    state = UNKNOWN
                res[name] = {"state": state, "sides": per}
            out[t.track_id] = res
        return out
