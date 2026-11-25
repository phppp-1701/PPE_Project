"""Bước 3: gán PPE cho người theo vùng cơ thể (spec 5.2, mục 3.4.3).

Vùng là hình chữ nhật trong tọa độ chuẩn hóa của hộp người (configs/pipeline.yaml: association.regions).
PPE có `sides` (găng) dùng hai nửa vùng: trái x < 0.5, phải x >= 0.5 (theo ảnh).
Áo (vùng torso), khi có `association.torso_pose`: thêm vùng thân theo khung xương (vai, hông), cắt theo hộp người;
tâm áo trong vùng cũ hoặc vùng này đều là ứng viên (bước B, 14/11/2026: người sát camera bị cắt ở ngực).
Bước B lần 1 đã tắt (15/11/2026). Bước B2 (`association.torso_strict`): chỉ cho người chạm mép dưới khung, vùng
khung xương không rộng hơn vùng cũ theo chiều ngang, có cổng hình học pose và cổng cỡ áo (kế hoạch ppe6 mục B2).
Không được bật đồng thời B1 và B2; thiếu `torso_strict` hoặc không có kích thước khung: ghép như bản 4.
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


def torso_pose_box(track, tp):
    """Vùng thân theo khung xương (x1, y1, x2, y2), cắt theo hộp người; None khi không đủ điểm.

    sw = khoảng cách hai vai (COCO 5, 6), (mx, my) = trung điểm vai, cả hai vai cần độ tin cậy >= tp["kp_conf"].
    x trong [mx - kx*sw, mx + kx*sw]; y từ my - ky0*sw tới (trung điểm hông + kh*sw) nếu thấy hai hông (11, 12),
    ngược lại tới my + ky1*sw. Người bị cắt ở ngực: phần dưới vùng nằm ngoài hộp người, bị cắt theo hộp."""
    kps = getattr(track, "extra", {}).get("kps")
    if not kps:
        return None
    c = tp["kp_conf"]
    (ax, ay, ac), (bx, by, bc) = kps[5], kps[6]
    if ac < c or bc < c:
        return None
    sw = math.hypot(ax - bx, ay - by)
    if sw < 1.0:
        return None
    mx, my = (ax + bx) / 2, (ay + by) / 2
    if kps[11][2] >= c and kps[12][2] >= c:
        bottom = (kps[11][1] + kps[12][1]) / 2 + tp["kh"] * sw
    else:
        bottom = my + tp["ky1"] * sw
    x1, y1, x2, y2 = track.xyxy
    r = [max(mx - tp["kx"] * sw, x1), max(my - tp["ky0"] * sw, y1), min(mx + tp["kx"] * sw, x2), min(bottom, y2)]
    if r[2] <= r[0] or r[3] <= r[1]:
        return None
    return np.array(r, dtype=float)


def torso_strict_box(track, ts, old_box, frame_shape):
    """Bước B2: (vùng R (x1, y1, x2, y2), sw) khi qua cổng G2-G4, ngược lại None (ghép như bản 4).

    G2 hai vai (COCO 5, 6) có độ tin cậy >= ts["kp_conf"]. G3 hình học: (a) hai vai trong hộp người; (b) góc đường
    vai so với phương ngang <= ts["slope_max_deg"]; (c) thấy hai hông (11, 12) thì trung điểm hông thấp hơn trung điểm
    vai; (d) sw >= 1 px. G4 có kích thước khung và đáy hộp người y2 >= H - ts["edge_px"].
    R: ngang [max(mép trái vùng cũ, mx - kx*sw), min(mép phải vùng cũ, mx + kx*sw)] (không rộng hơn vùng cũ);
    dọc từ my - ky0*sw tới đáy hộp người, thấy hông thì tới min(đáy hộp, hông + kh*sw); cắt theo hộp người."""
    if frame_shape is None:
        return None
    g = shoulder_geometry(track, ts["kp_conf"])                                  # G2, G3a, G3c, G3d
    if g is None or g["angle"] > ts["slope_max_deg"]:                            # G3b
        return None
    x1, y1, x2, y2 = track.xyxy
    edge = frame_shape[0] * ts["edge_frac"] if "edge_frac" in ts else ts["edge_px"]   # bước F2: theo tỉ lệ khung
    if y2 < frame_shape[0] - edge:                                               # G4
        return None
    sw, mx, my, hy = g["sw"], g["mx"], g["my"], g["hy"]
    r = [max(old_box[0], mx - ts["kx"] * sw, x1), max(my - ts["ky0"] * sw, y1),
         min(old_box[2], mx + ts["kx"] * sw, x2), y2 if hy is None else min(hy + ts["kh"] * sw, y2)]
    if r[2] <= r[0] or r[3] <= r[1]:
        return None
    return np.array(r, dtype=float), sw


def shoulder_geometry(track, kp_conf):
    """Cổng G2, G3(a)(c)(d) của B2 (dùng chung cho chuỗi xử lý và 05a --torso-strict).

    Trả về dict(sw, mx, my, angle (độ, đường vai so với phương ngang), hy (trung điểm hông y, None khi không thấy hai
    hông)) hoặc None khi: một vai dưới kp_conf (G2); vai ngoài hộp người (G3a); thấy hai hông mà hông không thấp hơn
    vai (G3c); sw < 1 px (G3d)."""
    kps = getattr(track, "extra", {}).get("kps")
    if not kps:
        return None
    (ax, ay, ac), (bx, by, bc) = kps[5], kps[6]
    if ac < kp_conf or bc < kp_conf:                                             # G2
        return None
    x1, y1, x2, y2 = track.xyxy
    if not all(x1 <= qx <= x2 and y1 <= qy <= y2 for qx, qy in ((ax, ay), (bx, by))):   # G3a
        return None
    dx, dy = abs(ax - bx), abs(ay - by)
    sw = math.hypot(dx, dy)
    if sw < 1.0:                                                                 # G3d
        return None
    mx, my = (ax + bx) / 2, (ay + by) / 2
    hy = None
    if kps[11][2] >= kp_conf and kps[12][2] >= kp_conf:
        hy = (kps[11][1] + kps[12][1]) / 2
        if hy <= my:                                                             # G3c (y ảnh tăng xuống dưới)
            return None
    return dict(sw=sw, mx=mx, my=my, angle=math.degrees(math.atan2(dy, dx)), hy=hy)


def eye_anchor_distance(track, c, ea):
    """Bước F1: (khoảng cách từ c tới trung điểm hai mắt / khoảng cách hai mắt) / k_eye nếu <= 1, ngược lại None.
    Cần hai mắt (COCO 1, 2) >= ea["kp_conf"] và khoảng cách hai mắt >= 1 px."""
    kps = getattr(track, "extra", {}).get("kps")
    if not kps or kps[1][2] < ea["kp_conf"] or kps[2][2] < ea["kp_conf"]:
        return None
    ed = math.hypot(kps[1][0] - kps[2][0], kps[1][1] - kps[2][1])
    if ed < 1.0:
        return None
    r = math.hypot(c[0] - (kps[1][0] + kps[2][0]) / 2, c[1] - (kps[1][1] + kps[2][1]) / 2) / ed / ea["k_eye"]
    return r if r <= 1 else None


def limb_anchor_distance(track, c, end, joint, kp_conf, k):
    """Bước F1 tầm gần (2026-11-25): khoảng cách từ c tới điểm khớp `end` chia cho (độ dài đoạn joint-end × k) nếu <= 1,
    ngược lại None. Ủng: end = mắt cá, joint = gối (ống chân); găng: end = cổ tay, joint = khuỷu (cẳng tay).
    Cần hai điểm >= kp_conf và đoạn dài >= 1 px. Thang theo chi, không theo hộp người, nên đúng cả khi người bị khung cắt."""
    kps = getattr(track, "extra", {}).get("kps")
    if not kps or kps[end][2] < kp_conf or kps[joint][2] < kp_conf:
        return None
    s = math.hypot(kps[end][0] - kps[joint][0], kps[end][1] - kps[joint][1])
    if s < 1.0:
        return None
    r = math.hypot(c[0] - kps[end][0], c[1] - kps[end][1]) / (s * k)
    return r if r <= 1 else None


def wrist_index(track, side):
    """Chỉ số COCO (9 hoặc 10) của cổ tay mang tên `side` (left/right theo ảnh, pose.py sắp theo x); None nếu không có."""
    kps = getattr(track, "extra", {}).get("kps")
    q = getattr(track, "extra", {}).get("wrists", {}).get(side)
    if not kps or q is None:
        return None
    return min((9, 10), key=lambda i: math.hypot(kps[i][0] - q[0], kps[i][1] - q[1]))


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
        # Vùng thân theo khung xương cho áo (bước B); vắng mục này -> như bản 4.
        self.torso_pose = (require(cfg, "association", "torso_pose")
                           if self.pose and cfg["association"].get("torso_pose") is not None else None)
        # Bước B2: vùng thân theo khung xương bản chặt cho áo; vắng mục này -> như bản 4. Không bật cùng B1.
        if cfg["association"].get("torso_pose") is not None and cfg["association"].get("torso_strict") is not None:
            raise ValueError("configs/pipeline.yaml: association.torso_pose (B1) và association.torso_strict (B2) "
                             "không được bật đồng thời")
        self.torso_strict = (require(cfg, "association", "torso_strict")
                             if self.pose and cfg["association"].get("torso_strict") is not None else None)
        # Bước F1: kính theo mắt; F3: găng dự phòng theo vùng tay khi cổ tay không hợp lệ. Vắng khóa -> như bản chính.
        self.eye_anchor = (require(cfg, "association", "eye_anchor")
                           if self.pose and cfg["association"].get("eye_anchor") is not None else None)
        self.gloves_fallback = bool(self.pose and cfg["association"].get("gloves_region_fallback"))
        # Bước F1 tầm gần (kế hoạch 2026-11-25_close_range_fixes): ủng theo mắt cá, găng theo cổ tay (thang theo chi).
        self.ankle_anchor = (require(cfg, "association", "ankle_anchor")
                             if self.pose and cfg["association"].get("ankle_anchor") is not None else None)
        self.wrist_anchor = (require(cfg, "association", "wrist_anchor")
                             if self.pose and cfg["association"].get("wrist_anchor") is not None else None)

    def limit(self, name):
        """Khoảng cách tối đa: 1 (biên elip) khi dùng cổ tay, còn lại `max_distance` (3.4)."""
        p = self.ppe[name]
        return 1.0 if self.pose and p["sides"] and p["region"] == "hands" else self.max_distance[name]

    def candidates(self, name, det, tracks, frame_shape=None):
        """[(d, track_id, side)] của các vùng chứa tâm PPE, sắp theo d tăng dần. frame_shape (H, W, ...) chỉ dùng
        cho B2 (G4); None -> B2 không bật."""
        p = self.ppe[name]
        reg = self.regions[p["region"]]
        c = det.center
        out = []
        for t in tracks:
            for side in (SIDES if p["sides"] else (None,)):
                if self.pose and p["sides"] and p["region"] == "hands":
                    q = valid_wrist(t, side, self.pose)
                    vals = []
                    if q is not None and (v := ellipse_value(c, t.xyxy, q, self.pose)) <= 1:
                        vals.append(v)
                    if self.wrist_anchor and (wi := wrist_index(t, side)) is not None:   # F1 tầm gần: thang cẳng tay
                        a = limb_anchor_distance(t, c, wi, wi - 2, self.wrist_anchor["kp_conf"], self.wrist_anchor["k_wrist"])
                        if a is not None:
                            vals.append(a)
                    if vals:
                        out.append((min(vals), t.track_id, side))
                        continue
                    if q is not None or not self.gloves_fallback:
                        continue
                    # Bước F3: cổ tay bên này không hợp lệ -> nửa vùng tay cũ; khoảng cách quy về thang elip (1 = giới hạn)
                    r = region_box(t.xyxy, reg, side)
                    if r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3]:
                        out.append((norm_distance(c, t.xyxy, r) / self.max_distance[name], t.track_id, side))
                    continue
                r = region_box(t.xyxy, reg, side)
                d = norm_distance(c, t.xyxy, r) if r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3] else None
                if self.torso_pose and p["region"] == "torso" and side is None:
                    rp = torso_pose_box(t, self.torso_pose)
                    if rp is not None and rp[0] <= c[0] <= rp[2] and rp[1] <= c[1] <= rp[3]:
                        dp = norm_distance(c, t.xyxy, rp)
                        d = dp if d is None else min(d, dp)
                if self.torso_strict and name == "vest" and p["region"] == "torso" and side is None:   # G1
                    g = torso_strict_box(t, self.torso_strict, r, frame_shape)
                    if g is not None:
                        rs, sw = g
                        in_old = r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3]
                        # G5 chỉ cho áo vào được nhờ R (tâm ngoài vùng cũ)
                        size_ok = in_old or (det.xyxy[2] - det.xyxy[0]) >= self.torso_strict["s_min"] * sw
                        if size_ok and rs[0] <= c[0] <= rs[2] and rs[1] <= c[1] <= rs[3]:
                            ds = norm_distance(c, t.xyxy, rs)
                            d = ds if d is None else min(d, ds)
                if self.eye_anchor and name == "goggles" and side is None:                         # bước F1
                    de = eye_anchor_distance(t, c, self.eye_anchor)
                    if de is not None:
                        de *= self.max_distance[name]
                        d = de if d is None else min(d, de)
                if self.ankle_anchor and name == "boots" and side is None:                         # F1 tầm gần
                    aa = self.ankle_anchor
                    ds = [x for end, joint in ((15, 13), (16, 14))
                          if (x := limb_anchor_distance(t, c, end, joint, aa["kp_conf"], aa["k_ankle"])) is not None]
                    if ds:
                        da = min(ds) * self.max_distance[name]
                        d = da if d is None else min(d, da)
                if d is not None:
                    out.append((d, t.track_id, side))
        return sorted(out, key=lambda x: x[0])

    def __call__(self, tracks, ppe_dets, frame_shape=None):
        a = Association()
        for det in ppe_dets:
            name = self.by_cls.get(det.cls)
            if name is None:
                continue
            cand = self.candidates(name, det, tracks, frame_shape)
            if not cand:
                a.rejected.append((name, det, "outside", []))
                continue
            track_by_id = {t.track_id: t for t in tracks}
            limit = self.limit(name)
            t_first = track_by_id.get(cand[0][1])
            if t_first is not None:
                pw = max(t_first.xyxy[2] - t_first.xyxy[0], 1.0)
                ph = max(t_first.xyxy[3] - t_first.xyxy[1], 1.0)
                aspect = ph / pw
                if aspect < 2.8:
                    limit *= (1.0 + 0.5 * (2.8 - aspect))
            if cand[0][0] > limit:
                a.rejected.append((name, det, "far", cand))
                continue
            near = [x for x in cand if x[0] <= limit]
            _, tid, side = near[0]
            other_people = [x for x in near[1:] if x[1] != tid]
            if other_people and (self.margin is None or other_people[0][0] - near[0][0] < self.margin):
                for _, t_id, s in near:
                    a.contested[t_id].add((name, s))
                a.rejected.append((name, det, "contested", near))
                continue
            if a.owned[tid][(name, side)]:
                alt = [x for x in near[1:] if x[1] == tid and x[2] != side and not a.owned[tid][(name, x[2])]]
                if alt:
                    side = alt[0][2]
            a.owned[tid][(name, side)].append(det)
            track_by_id = {t.track_id: t for t in tracks}
            for _, t_id, s in near[1:]:
                if t_id == tid and s != side:
                    t_obj = track_by_id.get(tid)
                    q1 = valid_wrist(t_obj, side, self.pose) if self.pose and t_obj else None
                    q2 = valid_wrist(t_obj, s, self.pose) if self.pose and t_obj else None
                    box_span = max(det.xyxy[2] - det.xyxy[0], det.xyxy[3] - det.xyxy[1])
                    if q1 is not None and q2 is not None and box_span > math.hypot(q1[0] - q2[0], q1[1] - q2[1]):
                        a.owned[tid][(name, s)].append(det)
                    else:
                        a.contested[tid].add((name, s))
        return a
