"""Bước kiểm tra thứ hai cho găng, ủng, kính: phân loại ảnh cắt bộ phận theo keypoint (YOLO11n-cls, phương án 2).

Ảnh cắt vuông lấy theo pose (17 điểm COCO, tọa độ khung):
- tay: tâm = cổ tay + k * (cổ tay - khuỷu), cạnh = s * độ dài cẳng tay;
- chân: tâm = mắt cá + k * (mắt cá - gối), cạnh = s * độ dài cẳng chân;
- mắt: tâm = trung điểm hai mắt, cạnh = s * khoảng cách hai mắt.
k, s ở configs/pipeline.yaml mục `part_cls.geometry`, chọn trên val bằng scripts/05e_select_part_cls.py.
Kết quả: xác suất có PPE p (chuẩn hóa trong các lớp của bộ phận), ghi vào track.extra["parts"][(ppe, side)].
"""

import math

import numpy as np

# Lớp có PPE và các lớp không có PPE của từng bộ phận (tên lớp của bộ phân loại, do 03y tạo)
PART_CLASSES = {
    "gloves": ("glove", ("bare_hand",)),
    "boots": ("safety_boot", ("not_safety_foot",)),
    "goggles": ("goggles", ("ordinary_glasses", "no_eyewear")),
    "vest": ("vest", ("no_vest",)),
}
HAND = ((9, 7), (10, 8))       # (cổ tay, khuỷu)
FOOT = ((15, 13), (16, 14))    # (mắt cá, gối)
EYES = (1, 2)
NOSE = 0
SHOULDERS, HIPS = (5, 6), (11, 12)


def _ok(kps, i, c):
    return kps[i][2] >= c


def extend_box(kps, i, j, g):
    """Ảnh cắt quanh điểm i, kéo dài theo hướng j -> i: tâm = P_i + k (P_i - P_j), cạnh = s |P_i - P_j|."""
    (x, y), (u, v) = kps[i][:2], kps[j][:2]
    return (x + g["k"] * (x - u), y + g["k"] * (y - v), g["s"] * math.hypot(x - u, y - v))


def eye_box(kps, g):
    (lx, ly), (rx, ry) = kps[EYES[0]][:2], kps[EYES[1]][:2]
    return ((lx + rx) / 2, (ly + ry) / 2, g["s"] * math.hypot(lx - rx, ly - ry))


def eye_profile_box(kps, i, g):
    """Mặt nghiêng (chỉ thấy mắt i và mũi): tâm ở mắt, khoảng cách hai mắt ước lượng bằng 2 |mắt - mũi|."""
    (x, y), (nx, ny) = kps[i][:2], kps[NOSE][:2]
    return (x, y, g["s"] * 2 * math.hypot(x - nx, y - ny))


def torso_box(kps, g, c):
    """Vùng thân theo vai (bắt buộc) và hông. Không thấy hông: chiều dài thân = h * độ rộng vai.
    Cạnh = s * max(độ rộng vai, chiều dài thân). Ảnh cắt bị cắt theo mép khung (người sát camera chỉ còn phần ngực)."""
    (ax, ay), (bx, by) = kps[SHOULDERS[0]][:2], kps[SHOULDERS[1]][:2]
    sw = math.hypot(ax - bx, ay - by)
    mx, my = (ax + bx) / 2, (ay + by) / 2
    if all(kps[i][2] >= c for i in HIPS):
        hx, hy = (kps[HIPS[0]][0] + kps[HIPS[1]][0]) / 2, (kps[HIPS[0]][1] + kps[HIPS[1]][1]) / 2
        H = math.hypot(hx - mx, hy - my)
        cx, cy = (mx + hx) / 2, (my + hy) / 2
    else:
        H = g["h"] * sw
        cx, cy = mx, my + H / 2
    return (cx, cy, g["s"] * max(sw, H))


def part_boxes(kps, geom, kp_conf):
    """[(ppe, side, (cx, cy, cạnh))] từ keypoint. side: "left"/"right" (tay, theo x trong ảnh như pose.py: cổ tay có
    x nhỏ hơn cổ tay kia là "left"), "15"/"16" (chân), None (mắt). Bộ phận thiếu điểm đạt kp_conf thì bỏ qua."""
    out = []
    for (w, e), (w2, _) in zip(HAND, HAND[::-1]):
        if _ok(kps, w, kp_conf) and _ok(kps, e, kp_conf):
            side = "left" if kps[w][0] <= kps[w2][0] else "right"
            out.append(("gloves", side, extend_box(kps, w, e, geom["hand"])))
    for a, k in FOOT:
        if _ok(kps, a, kp_conf) and _ok(kps, k, kp_conf):
            out.append(("boots", str(a), extend_box(kps, a, k, geom["foot"])))
    if all(_ok(kps, i, kp_conf) for i in EYES):
        out.append(("goggles", None, eye_box(kps, geom["eye"])))
    elif _ok(kps, NOSE, kp_conf) and any(_ok(kps, i, kp_conf) for i in EYES):
        i = EYES[0] if _ok(kps, EYES[0], kp_conf) else EYES[1]
        out.append(("goggles", None, eye_profile_box(kps, i, geom["eye"])))
    if "torso" in geom and all(_ok(kps, i, kp_conf) for i in SHOULDERS):
        out.append(("vest", None, torso_box(kps, geom["torso"], kp_conf)))
    return out


def cut(frame, box, min_px):
    """Ảnh cắt vuông quanh (cx, cy, cạnh), cắt theo mép khung. None nếu cạnh nhỏ hơn min_px sau khi cắt."""
    h, w = frame.shape[:2]
    cx, cy, side = box
    a, b = int(max(cx - side / 2, 0)), int(max(cy - side / 2, 0))
    c, d = int(min(cx + side / 2, w)), int(min(cy + side / 2, h))
    if min(c - a, d - b) < min_px:
        return None
    return frame[b:d, a:c]


def ppe_prob(probs, names, ppe):
    """Xác suất có PPE trong các lớp của bộ phận (chuẩn hóa lại cho tổng bằng 1)."""
    pos, negs = PART_CLASSES[ppe]
    idx = {v: k for k, v in names.items()}
    p = float(probs[idx[pos]])
    n = sum(float(probs[idx[q]]) for q in negs)
    return p / max(p + n, 1e-9)


class PartClassifier:
    def __init__(self, cfg, root):
        from ultralytics import YOLO

        self.c = cfg["part_cls"]
        self.device = cfg["detector"]["device"]
        self.model = YOLO(root / self.c["weights"])
        self.names = self.model.names

    def classify(self, crops):
        if not crops:
            return []
        rs = self.model.predict(crops, imgsz=self.c["imgsz"], device=self.device, verbose=False)
        return [r.probs.data.cpu().numpy() for r in rs]

    def __call__(self, frame, tracks):
        """Ghi track.extra["parts"] = {(ppe, side): p có PPE} cho người có keypoint."""
        items = []
        for t in tracks:
            t.extra["parts"] = {}
            kps = t.extra.get("kps")
            if not kps:
                continue
            for ppe, side, box in part_boxes(kps, self.c["geometry"], self.c["kp_conf"]):
                crop = cut(frame, box, self.c["min_px"])
                if crop is not None:
                    items.append((t, ppe, side, crop))
        for (t, ppe, side, _), pr in zip(items, self.classify([x[3] for x in items])):
            t.extra["parts"][(ppe, side)] = ppe_prob(pr, self.names, ppe)


def anchors(kps, ppe, c):
    """[(điểm gốc (x, y), hàm hình học -> hộp)] của một người cho PPE này: cổ tay có khuỷu, mắt cá có gối, trung điểm mắt."""
    out = []
    if ppe == "gloves":
        for w, e in HAND:
            if kps[w][2] >= c and kps[e][2] >= c:
                out.append((kps[w][:2], lambda g, w=w, e=e: extend_box(kps, w, e, g)))
    elif ppe == "boots":
        for a, k in FOOT:
            if kps[a][2] >= c and kps[k][2] >= c:
                out.append((kps[a][:2], lambda g, a=a, k=k: extend_box(kps, a, k, g)))
    elif ppe == "goggles" and all(kps[i][2] >= c for i in EYES):
        mid = ((kps[1][0] + kps[2][0]) / 2, (kps[1][1] + kps[2][1]) / 2)
        out.append((mid, lambda g: eye_box(kps, g)))
    elif ppe == "goggles" and kps[NOSE][2] >= c:
        for i in EYES:
            if kps[i][2] >= c:
                out.append((kps[i][:2], lambda g, i=i: eye_profile_box(kps, i, g)))
    elif ppe == "vest" and all(kps[i][2] >= c for i in SHOULDERS):
        g0 = torso_box(kps, {"h": 1.5, "s": 1.0}, c)   # chỉ để lấy tâm khi ghép với hộp nhãn
        out.append((g0[:2], lambda g: torso_box(kps, g, c)))
    return out


def match_anchor(people_kps, ppe, bx, kp_conf):
    """Hàm hình học của điểm gốc gần tâm hộp nhãn bx nhất (mọi người trong ảnh), cách tâm không quá cạnh dài hộp; None nếu không có."""
    c = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
    lim = max(bx[2] - bx[0], bx[3] - bx[1])
    best = None
    for kps in people_kps:
        for pt, mk in anchors(kps, ppe, kp_conf):
            d = math.hypot(pt[0] - c[0], pt[1] - c[1])
            if d <= lim and (best is None or d < best[0]):
                best = (d, mk)
    return best and best[1]


def people_keypoints(im, person_model, pose, device):
    """Keypoint từng người trong ảnh tĩnh: tìm người bằng mô hình pose trên cả ảnh, rồi chạy PoseEstimator của pipeline
    trên ảnh cắt từng người (như khi chạy video)."""
    from types import SimpleNamespace

    r = person_model.predict(im, imgsz=640, conf=0.25, device=device, verbose=False)[0]
    tracks = [SimpleNamespace(xyxy=b, extra={}) for b in r.boxes.xyxy.cpu().numpy()]
    pose(im, tracks)
    return [t.extra["kps"] for t in tracks if t.extra.get("kps")]
