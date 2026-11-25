"""Bước 4: kiểm tra khả năng quan sát và kết luận ba trạng thái (spec 5.3, mục 3.4.4, Bảng 3.5).

Không phát hiện được PPE không đồng nghĩa với Thiếu: chỉ kết luận Thiếu khi vùng đủ quan sát (O = 1),
không có PPE gán hợp lệ và không còn tranh chấp.

Bước C (`part_cls.veto_frontal`): bộ phân loại chắc không có mũ phủ quyết hộp mũ của detector, chỉ khi nhìn thẳng chắc.
Bước C2 (thêm `t_veto`): rất chắc không mũ -> phủ quyết (Thiếu); phân vân -> mâu thuẫn, Chưa xác định (không Có).
Bước D (`compliance.back_view`): nhận quay lưng (vai ngược, không mặt rõ, giữ theo thời gian); khi quay lưng kính
Chưa xác định, mũ không có hộp detector Chưa xác định. Vắng khóa: như bản 4 (kế hoạch ppe6 mục C, D, 16/11/2026).
"""

import math

import numpy as np

from . import HAVE, MISSING, UNKNOWN, box_area, intersect, require
from .association import SIDES, region_box, valid_wrist, wrist_box

GRID = 100   # số ô tối đa mỗi chiều khi tính diện tích bị người khác che (xấp xỉ, đủ cho tỉ lệ)


def _iou(a, b):
    i = box_area(intersect(a, b))
    u = box_area(a) + box_area(b) - i
    return i / u if u > 0 else 0.0


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


def frontal_strict(kps, face_conf, kp_conf):
    """Bước C: nhìn thẳng chắc. Mũi (0), hai mắt (1, 2) >= face_conf; hai vai (5, 6) >= kp_conf và không ngược
    (nhìn về camera thì vai trái COCO ở bên phải ảnh: x5 > x6)."""
    if not kps:
        return False
    if any(kps[i][2] < face_conf for i in (0, 1, 2)):
        return False
    if kps[5][2] < kp_conf or kps[6][2] < kp_conf:
        return False
    return kps[5][0] > kps[6][0]


def back_view_now(kps, xyxy, bv):
    """Bước D, một khung: hai vai >= bv["kp_conf"] và ngược (x5 < x6), cách nhau theo ngang >= bv["min_sep"] x rộng
    hộp người, và không "mặt rõ" (mũi, hai mắt đều >= bv["face_strong"]). Quy ước heuristic, không chọn trên val."""
    if not kps:
        return False
    c = bv["kp_conf"]
    if kps[5][2] < c or kps[6][2] < c:
        return False
    x5, x6 = kps[5][0], kps[6][0]
    if not x5 < x6 or (x6 - x5) < bv["min_sep"] * (xyxy[2] - xyxy[0]):
        return False
    return not all(kps[i][2] >= bv["face_strong"] for i in (0, 1, 2))


class Compliance:
    def __init__(self, cfg):
        self.ppe = cfg["ppe"]
        self.regions = {p["region"]: require(cfg, "association", "regions", p["region"]) for p in self.ppe.values()}
        self.tau_in = require(cfg, "compliance", "tau_in")
        self.tau_occ = require(cfg, "compliance", "tau_occ")
        self.area_min = require(cfg, "compliance", "area_min_px")
        self.pose = cfg["pose"] if cfg.get("pose", {}).get("enabled") else None
        self.gate = cfg.get("compliance", {}).get("keypoint_gate") if self.pose else None
        self.hold_s = cfg.get("compliance", {}).get("have_hold_s") or {}
        self.last_have = {}     # (track_id, ppe, side) -> t lần cuối thấy Có
        pc = cfg.get("part_cls") or {}
        self.part = pc if pc.get("enabled") and self.pose else None   # bộ phân loại bộ phận (parts.py), cần pose
        self.p_hist = {}        # (track_id, ppe, bên) -> [(t, p)] trong vote_window_s giây gần nhất
        self.last_ps = []       # p (đã gộp) của lần part_vote gần nhất
        # Bước C: {ppe: {face_conf}}; vắng -> không phủ quyết theo hướng nhìn (như bản 4).
        self.veto_frontal = ((self.part or {}).get("veto_frontal") or {}) if self.part else {}
        # Bước D: {kp_conf, min_sep, face_strong, hold_s}; vắng -> không nhận quay lưng (như bản 4).
        self.back_cfg = (cfg.get("compliance") or {}).get("back_view") if self.pose else None
        self.back_last = {}     # track_id -> t lần cuối quay lưng
        # Bước F3: găng ghép dự phòng theo vùng tay khi cổ tay không hợp lệ -> có hộp gán thì Có (không bao giờ suy Thiếu)
        self.gloves_fallback = bool(self.pose and (cfg.get("association") or {}).get("gloves_region_fallback"))
        # Bước F1 tầm gần (2026-11-25): găng gán theo cổ tay thang cẳng tay khi cổ tay < pose.wrist_conf -> chỉ dẫn tới Có
        self.gloves_fallback = self.gloves_fallback or bool(self.pose and (cfg.get("association") or {}).get("wrist_anchor"))
        self._back = {}         # track_id -> quay lưng ở khung đang xét (tính một lần mỗi khung)
        # Bước M1 (kế hoạch 2026-11-16_post_holdout_fixes mục 2): {t_veto}; mọi chân có ảnh cắt đều 1 - p >= t_veto ->
        # bỏ hộp ủng của detector (dép, giày thường). Vắng -> như bản cuối.
        self.veto_boots = ((self.part or {}).get("veto_boots") or None) if self.part else None
        # F2 (2026-11-25_close_range_fixes): nhớ PPE theo (người, PPE, bên). {hold_conf, hold_iou}; vắng -> như cũ.
        self.mem_cfg = (cfg.get("compliance") or {}).get("ppe_memory")
        self.mem = {}           # (track_id, ppe, bên) -> (t lần cuối có bằng chứng hộp, hộp)
        self.weak = []          # hộp PPE điểm thấp của khung hiện tại (Detector.weak), người gọi gán trước mỗi khung

    def _mem_on(self, name):
        """F2 có áp dụng cho món này không: `ppe_memory.ppe` (danh sách) vắng = mọi món."""
        return bool(self.mem_cfg) and name in (self.mem_cfg.get("ppe") or self.ppe)

    def _hold(self, name, key, blocked):
        """F2: (kiểu giữ "weak"/"time", hộp) nếu (người, PPE, bên) vừa có bằng chứng hộp trong have_hold_s giây và không
        bị bằng chứng âm chặn; None nếu không giữ. "weak": hộp điểm thấp cùng lớp trùng vị trí nhớ (IoU >= hold_iou), làm
        mới thời điểm nhớ; "time": không có hộp, giữ tới hết have_hold_s (không làm mới)."""
        if not self._mem_on(name) or self.now is None or blocked or key not in self.mem:
            return None
        t0, box = self.mem[key]
        if self.now - t0 > self.hold_s.get(name, 0):
            return None
        cls = self.ppe[name]["cls"]
        w = [d for d in self.weak if d.cls == cls and _iou(d.xyxy, box) >= self.mem_cfg["hold_iou"]]
        if w:
            best = max(w, key=lambda d: d.conf)
            self.mem[key] = (self.now, np.asarray(best.xyxy, dtype=float))
            return "weak", self.mem[key][1]
        return "time", box

    def _remember(self, key, assoc, track_id, name, side):
        """F2: ghi hộp gán (điểm cao nhất) của (người, PPE, bên) đang Có nhờ hộp detector."""
        if not self._mem_on(name) or self.now is None:
            return
        ds = assoc.owned.get(track_id, {}).get((name, side)) or []
        if ds:
            self.mem[key] = (self.now, np.asarray(max(ds, key=lambda d: d.conf).xyxy, dtype=float))

    def back_view(self, track):
        """Bước D: quay lưng ở khung này, hoặc đã quay lưng trong back_view.hold_s giây gần nhất (cùng track)."""
        if not self.back_cfg:
            return False
        tid = track.track_id
        if tid not in self._back:
            now = back_view_now(getattr(track, "extra", {}).get("kps"), track.xyxy, self.back_cfg)
            if now and self.now is not None:
                self.back_last[tid] = self.now
            held = (self.now is not None and tid in self.back_last
                    and self.now - self.back_last[tid] <= self.back_cfg["hold_s"])
            self._back[tid] = now or held
        return self._back[tid]

    def part_ps(self, name, track, side):
        """p có PPE của bộ phân loại cho (người, PPE, bên), gộp theo thời gian (vote_window_s). Ủng: mọi chân.
        Mỗi khung gọi một lần cho mỗi (người, PPE, bên), vì mỗi lần gọi thêm p vào lịch sử."""
        got = getattr(track, "extra", {}).get("parts", {})
        ps = []
        win = self.part.get("vote_window_s") or 0
        for (n, s), p in got.items():
            if n != name or (name != "boots" and s != side):
                continue
            if self.now is not None and win > 0:
                # Gộp phiếu theo thời gian: trung bình p của bộ phận này trong vote_window_s giây gần nhất.
                h = self.p_hist.setdefault((track.track_id, n, s), [])
                h.append((self.now, p))
                h[:] = [(t, q) for t, q in h if self.now - t <= win]
                p = sum(q for _, q in h) / len(h)
            ps.append(p)
        return ps

    def part_vote(self, name, track, side):
        """Ý kiến của bộ phân loại bộ phận: "pos" (chắc có PPE), "neg" (chắc không có), "unsure", hoặc None (không có
        ảnh cắt). Ủng không chia bên: một chân chắc không có ủng là "neg"; không chân nào "neg" mà có chân chắc có là "pos"."""
        thr = (self.part or {}).get("thresholds", {}) or {}
        if name not in thr:
            return None
        ps = self.part_ps(name, track, side)
        self.last_ps = ps       # p đã gộp theo thời gian của phiếu này (bước C2 so với t_veto, không gộp lại lần hai)
        if not ps:
            return None
        t_pos, t_neg = thr[name]["t_pos"], thr[name]["t_neg"]
        if t_neg is not None and any(1 - p >= t_neg for p in ps):
            return "neg"
        if t_pos is not None and any(p >= t_pos for p in ps):
            return "pos"
        return "unsure"

    def keypoint_visible(self, name, track, frame_box):
        """Cổng quan sát theo pose (khi bật `keypoint_gate`): trả về False nếu bộ phận cần cho PPE này không nhìn thấy rõ.
        goggles: cần hai mắt (mặt hướng về camera); helmet: cần ít nhất một điểm đầu và đầu không chạm mép trên khung;
        boots: cần mắt cá và mắt cá không sát mép dưới khung. Không có pose cho người này: không chặn (giữ luật vùng)."""
        g = self.gate.get(name) if self.gate else None
        kps = getattr(track, "extra", {}).get("kps")
        if not g or not kps:
            return True
        c = g["kp_conf"]
        if name == "goggles":
            # Quay lưng: pose có thể đoán "mắt" ở sau gáy, nhưng vai COCO bị ngược (vai trái ở bên trái ảnh).
            # Nhìn về camera thì vai trái (5) ở bên phải ảnh so với vai phải (6).
            back = kps[5][2] >= c and kps[6][2] >= c and kps[5][0] < kps[6][0]
            return kps[1][2] >= c and kps[2][2] >= c and not back
        if name == "helmet":
            if not any(kps[i][2] >= c for i in range(5)):
                return False
            return track.xyxy[1] > frame_box[1] + g["edge_px"]
        if name == "boots":
            ok = [kps[i] for i in (15, 16) if kps[i][2] >= c]
            return bool(ok) and max(q[1] for q in ok) < frame_box[3] - g["edge_px"]
        return True

    def side_state(self, name, track, side, assoc, frame_box, others):
        p = self.ppe[name]
        if self.pose and p["sides"] and p["region"] == "hands":
            # Có pose: không thấy cổ tay đạt ngưỡng thì tay đó không quan sát được (G = 0), không suy ra Thiếu.
            q = valid_wrist(track, side, self.pose)
            if q is None and name in ((self.part or {}).get("observe_from_crop") or []):
                # Bộ phân loại đã cắt được ảnh tay này (cổ tay đạt part_cls.kp_conf): tay coi là nhìn thấy theo mức
                # của bước cắt ảnh, kết luận Thiếu vẫn chỉ khi bộ phân loại chắc là tay trần.
                w = getattr(track, "extra", {}).get("wrists", {}).get(side)
                if w is not None and w[2] >= self.part["kp_conf"] and (name, side) in track.extra.get("parts", {}):
                    q = w
            if q is None:
                key = (track.track_id, name, side)
                if (self.gloves_fallback and track.confident
                        and assoc.owned.get(track.track_id, {}).get((name, side))):
                    if self.now is not None:
                        self.last_have[key] = self.now
                    self._remember(key, assoc, track.track_id, name, side)
                    return HAVE, dict(v=0.0, o=0.0, area=0, observable=False, has=True, contested=False, vote=None,
                                      c2=None, fallback=True)
                hold = self._hold(name, key, not track.confident) if not assoc.owned.get(track.track_id, {}).get((name, side)) else None
                if hold:                     # F2: cổ tay vừa tụt dưới ngưỡng, găng vừa thấy -> giữ Có
                    if hold[0] == "weak":    # giữ theo thời gian không làm mới mốc: báo chậm tối đa have_hold_s
                        self.last_have[key] = self.now
                    return HAVE, dict(v=0.0, o=0.0, area=0, observable=False, has=False, contested=False, vote=None,
                                      c2=None, held=hold[0], held_box=hold[1])
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
        if observable and not self.keypoint_visible(name, track, frame_box):
            observable = False
        back = name in ("helmet", "goggles") and self.back_view(track)      # bước D
        if back and name == "goggles":
            observable = False          # quay lưng: không thấy mắt -> kính Chưa xác định
        has = bool(assoc.owned.get(track.track_id, {}).get((name, side)))
        if name == "boots" and not has:
            ankles = getattr(track, "extra", {}).get("ankles")
            if ankles and ankles["conf"] >= 0.5:
                dist_to_bottom = track.xyxy[3] - ankles["max_y"]
                person_h = track.xyxy[3] - track.xyxy[1]
                if dist_to_bottom < 0.065 * person_h:
                    observable = False
        contested = (name, side) in assoc.contested.get(track.track_id, set())
        key = (track.track_id, name, side)
        recently_have = self.now is not None and key in self.last_have and self.now - self.last_have[key] <= self.hold_s.get(name, 0)
        covered = bool(self.part) and name in (self.part.get("thresholds") or {})   # PPE có bước kiểm tra thứ hai
        min_h = ((self.part or {}).get("min_person_px") or {}).get(name)
        if covered and min_h and track.xyxy[3] - track.xyxy[1] < min_h:
            covered = False     # người nhỏ hơn mức này: bộ phân loại không đáng tin, dùng luật cũ
        vote = self.part_vote(name, track, side) if covered else None
        vmax = ((self.part or {}).get("veto_max_conf") or {}).get(name)
        sure_box = vmax is not None and any(d.conf >= vmax for d in
                                            assoc.owned.get(track.track_id, {}).get((name, side)) or [])
        if covered and vote == "neg" and name in (self.part.get("veto") or []) and not sure_box:
            # Bộ phân loại chắc không có PPE (vd kính thường) thì phủ quyết hộp PPE của detector. F3 (2026-11-25):
            # hộp detector có conf >= part_cls.veto_max_conf thì không phủ quyết (detector rất chắc, vd kính vàng ôm mặt).
            has = False
        conflict = False
        c2 = None               # bước C, C2 đã làm gì với hộp detector (chỉ để vẽ, không đổi trạng thái): veto / conflict
        if self.veto_boots and name == "boots" and not covered:
            # Bước M1: tính p mọi khung (giữ lịch sử gộp), chỉ dùng khi detector có hộp ủng gán cho người này.
            bps = self.part_ps("boots", track, side)
            if has and bps and all(1 - p >= self.veto_boots["t_veto"] for p in bps):
                has = False
                c2 = "veto"
        vf = self.veto_frontal.get(name)
        if (covered and vote == "neg" and vf and not back and has
                and frontal_strict(getattr(track, "extra", {}).get("kps"), vf["face_conf"], self.part["kp_conf"])):
            # Bước C: nhìn thẳng chắc, detector có hộp mà bộ phân loại không thấy mũ (vd đầu trọc).
            # Không có t_veto (C): phủ quyết. Có t_veto (C2): rất chắc (1 - p >= t_veto) -> phủ quyết (Thiếu);
            # phân vân (t_neg <= 1 - p < t_veto) -> mâu thuẫn -> Chưa xác định (không Có).
            t_veto = vf.get("t_veto")
            if t_veto is None or any(1 - p >= t_veto for p in self.last_ps):
                has = False
                c2 = "veto"
            else:
                conflict = True
                c2 = "conflict"
        no_missing = back and name == "helmet" and not has   # bước D: không tin phiếu neg từ phía sau
        if not covered or (vote is None and self.part.get("fallback_old_rule", True)):
            # Luật cũ: có hộp PPE gán hợp lệ là Có; vùng nhìn rõ mà không có hộp là Thiếu.
            have = track.confident and has
            missing = observable and not contested and not recently_have and not no_missing
        else:
            # Phương án 2, bản 2: detector thấy là Có; bộ phân loại chắc có cũng là Có. Thiếu chỉ khi bộ phân loại
            # thấy rõ không có PPE và detector không thấy. Còn lại Chưa xác định.
            have = track.confident and (has or vote == "pos")
            missing = (vote == "neg" and not has and observable and not contested and not recently_have
                       and not no_missing)
        if conflict:
            have = missing = False          # bước C2: detector và bộ phân loại mâu thuẫn -> Chưa xác định
        held = None
        if not have and not has:
            # F2: vừa có bằng chứng hộp -> giữ Có; bằng chứng âm (phiếu neg, phủ quyết, mâu thuẫn) chặn việc giữ
            held = self._hold(name, key, not track.confident or vote == "neg" or c2 is not None or conflict)
            if held:
                have, missing = True, False
        if have:
            state = HAVE
            if self.now is not None and not (held and held[0] == "time"):
                self.last_have[key] = self.now     # F2: giữ theo thời gian không làm mới mốc (trễ tối đa have_hold_s)
            if has:
                self._remember(key, assoc, track.track_id, name, side)
        elif missing:
            state = MISSING
        else:
            state = UNKNOWN
        extra = dict(held=held[0], held_box=held[1]) if held else {}
        return state, dict(v=round(v, 3), o=round(o, 3), area=round(visible), observable=observable,
                           has=has, contested=contested, vote=vote, c2=c2, **extra)

    now = None

    def __call__(self, tracks, assoc, frame_shape, names=None, t=None):
        """{track_id: {ppe: {"state", "sides": {side: (state, chi tiết)}}}} cho các PPE trong `names`.
        t (giây): bật luật giữ trạng thái Có trong `have_hold_s` (vừa thấy Có thì không đổi ngay sang Thiếu khi PPE mất vài khung)."""
        self.now = t
        self._back = {}
        h, w = frame_shape[:2]
        frame_box = np.array([0, 0, w, h], dtype=float)
        out = {}
        for t in tracks:
            others = [o.xyxy for o in tracks if o.track_id != t.track_id]
            res = {}
            for name in (self.ppe if names is None else names):   # danh sách rỗng = không kiểm món nào (tắt hết)
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
