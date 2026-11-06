"""Hàm dùng chung cho thử nghiệm 6 lớp: quyết định hiệu lực, trạng thái ảnh, kiểm tra rò rỉ và nhãn, AP, đọc kết quả CVAT."""

import xml.etree.ElementTree as ET
from collections import Counter

import numpy as np

SAFE, ORDINARY, UNCLEAR, IGNORE = "safety", "ordinary", "unclear", "ignore"
SOFT_NOTES = ("not_safety", "too_small")   # giày SH17 chưa phân loại: không gán nhãn, nhưng vẫn giữ ảnh ở train
NUM_CLASSES = 6
NEW_CLASS = {"goggles": 4, "boots": 5}


def effective(agent, human):
    """Quyết định hiệu lực của một hộp. Người duyệt luôn thắng agent. Trả về (nhãn, ghi chú, nguồn)."""
    if human is not None:
        return human["after"], "", "human"
    return agent["label"], agent["note"], agent["decided_by"]


def blocks_train(label, note, target):
    """Ảnh có hộp này không được ở train: kính không rõ luôn chặn; ủng không rõ chặn trừ giày mặc định, giày quá nhỏ."""
    if label != UNCLEAR:
        return False
    return target == "goggles" or note not in SOFT_NOTES


def eval_status(decisions):
    """Trạng thái một ảnh đánh giá theo các hộp kính, ủng của nó: (label, source) mỗi hộp.

    ready: mọi hộp đã có người chốt và không còn `unclear`.
    pending: còn hộp chưa có người chốt. rejected: người chốt `unclear`, ảnh loại khỏi đánh giá lớp mới.
    """
    if any(src != "human" for _, src in decisions):
        return "pending"
    return "rejected" if any(lab == UNCLEAR for lab, _ in decisions) else "ready"


def diverse_pick(emb, keys, k, seed):
    """Chọn k phần tử đa dạng: bắt đầu ngẫu nhiên có seed, mỗi bước lấy phần tử xa tập đã chọn nhất."""
    if len(keys) <= k:
        return list(keys)
    order = np.argsort(np.array(keys, dtype=str), kind="stable")
    e = emb[order]
    start = int(np.random.default_rng(seed).integers(0, len(e)))
    chosen = [start]
    best = e @ e[start]
    for _ in range(k - 1):
        best[chosen] = np.inf
        n = int(np.argmin(best))
        chosen.append(n)
        best = np.maximum(best, e @ e[n])
    return [keys[order[i]] for i in chosen]


def check_label_rows(rows, allowed=NUM_CLASSES):
    """rows: các dòng 'cls cx cy w h'. Trả về danh sách lỗi."""
    bad = []
    for line in rows:
        t = line.split()
        if len(t) != 5:
            bad.append(f"sai số cột: {line}")
            continue
        c = t[0]
        if not c.isdigit() or int(c) >= allowed:
            bad.append(f"mã lớp sai: {line}")
        x, y, w, h = map(float, t[1:])
        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
            bad.append(f"tọa độ sai: {line}")
        if x - w / 2 < -1e-4 or x + w / 2 > 1 + 1e-4 or y - h / 2 < -1e-4 or y + h / 2 > 1 + 1e-4:
            bad.append(f"hộp ra ngoài ảnh: {line}")
    return bad


def check_leaks(sets, scene, ppe4_split):
    """sets: {tên: tập file}. Kiểm tra ảnh trùng, cảnh trùng giữa các tập, train không chứa ảnh val/test của ppe4."""
    bad = []
    names = sorted(sets)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            both = sets[a] & sets[b]
            if both:
                bad.append(f"ảnh trùng {a}, {b}: {len(both)}")
            same = {scene[f] for f in sets[a]} & {scene[f] for f in sets[b]}
            if same:
                bad.append(f"cảnh trùng {a}, {b}: {len(same)}")
    wrong = [f for f in sets.get("train", ()) if ppe4_split[f] != "train"]
    if wrong:
        bad.append(f"train chứa ảnh val/test của ppe4: {len(wrong)}")
    return bad


def ap_from_tp(tp, conf, n_gt, weight=None):
    """AP nội suy 101 điểm, chép compute_ap của Ultralytics 8.4.189. Trả về (AP@0.5, AP@0.5:0.95).

    Điểm phụ (recall cuối, precision 0) làm precision rơi về 0 ngay tại recall lớn nhất.

    tp: bool [n, n_iou]. weight: số lần mỗi dự đoán xuất hiện (bootstrap).
    """
    if n_gt <= 0:
        return 0.0, 0.0
    w = np.ones(len(conf)) if weight is None else weight
    order = np.argsort(-conf, kind="stable")
    tp, w = tp[order], w[order]
    x = np.linspace(0, 1, 101)
    aps = []
    for k in range(tp.shape[1]):
        tpc = np.cumsum(tp[:, k] * w)
        fpc = np.cumsum((1 - tp[:, k]) * w)
        recall = tpc / n_gt
        precision = tpc / np.maximum(tpc + fpc, 1e-16)
        r = np.concatenate(([0.0], recall, [recall[-1] if len(recall) else 1.0], [1.0]))
        p = np.flip(np.maximum.accumulate(np.flip(np.concatenate(([1.0], precision, [0.0], [0.0])))))
        aps.append(float(np.trapezoid(np.interp(x, r, p), x)))
    return aps[0], float(np.mean(aps))


UNREVIEWED = "chua_duyet"
DECISIONS = (SAFE, ORDINARY, UNCLEAR, IGNORE)
BOX_MOVED = 0.01     # hộp lệch quá tỉ lệ này của cạnh ảnh thì coi là người đã sửa hộp
NOT_A_PERSON = {"", "agent", "claude", "auto", "machine"}


def parse_cvat(xml_text):
    """Đọc CVAT for images 1.1. Trả về (hộp, tag). Hộp: dict(image, label, attrs, xtl, ytl, xbr, ybr, width, height)."""
    boxes, tags = [], []
    for im in ET.fromstring(xml_text).iter("image"):
        name, w, h = im.get("name"), float(im.get("width")), float(im.get("height"))
        for t in im.findall("tag"):
            tags.append((name, t.get("label")))
        for b in im.findall("box"):
            attrs = {a.get("name"): (a.text or "").strip() for a in b.findall("attribute")}
            boxes.append(dict(image=name, label=b.get("label"), attrs=attrs, xtl=float(b.get("xtl")), ytl=float(b.get("ytl")), xbr=float(b.get("xbr")),
                              ybr=float(b.get("ybr")), width=w, height=h))
    return boxes, tags


def merge_review(boxes, tags, index, reviewer, pack, now):
    """Đổi kết quả CVAT thành dòng human_review, human_added. index: {box_id: dòng index.csv}; `images` trong index theo tên ảnh.

    Hộp còn `chua_duyet` bị bỏ qua: không bao giờ tính là người đã duyệt. Trả về (dòng duyệt, hộp thêm, số hộp chưa duyệt).
    """
    if reviewer.strip().lower() in NOT_A_PERSON:
        raise ValueError("Cần tên người duyệt thật.")
    rows, added, skipped = [], [], 0
    by_name = {r["image_name"]: r["file"] for r in index.values()} | index.get("__images__", {})
    for b in boxes:
        w, h = b["width"], b["height"]
        norm = dict(cx=(b["xtl"] + b["xbr"]) / 2 / w, cy=(b["ytl"] + b["ybr"]) / 2 / h, w=(b["xbr"] - b["xtl"]) / w, h=(b["ybr"] - b["ytl"]) / h)
        if b["label"] in ("boots_new", "goggles_new"):
            added.append(dict(file=by_name[b["image"]], target=b["label"].replace("_new", ""), **{k: round(v, 6) for k, v in norm.items()}, reviewer=reviewer, pack=pack))
            continue
        bid = b["attrs"].get("box_id", "")
        decision = b["attrs"].get("decision", UNREVIEWED)
        if bid not in index:
            raise ValueError(f"box_id không có trong gói: {bid}")
        if decision == UNREVIEWED:
            skipped += 1
            continue
        if decision not in DECISIONS:
            raise ValueError(f"Quyết định lạ: {decision}")
        old = index[bid]
        moved = max(abs(norm[k] - float(old[k])) for k in ("cx", "cy", "w", "h")) > BOX_MOVED
        rows.append(dict(box_id=bid, target=old["target"], source=old["source"], before=old["agent_label"], after=decision, person_ok=b["attrs"].get("person_ok", ""),
                         reviewer=reviewer, reviewed_at=now, pack=pack, **{f"new_{k}": round(v, 6) if moved else "" for k, v in norm.items()}))
    for name, label in tags:
        if label in ("image_checked", "reject_image"):
            rows.append(dict(box_id="image:" + by_name[name], target="image", source="", before="", after="checked" if label == "image_checked" else "reject", person_ok="",
                             reviewer=reviewer, reviewed_at=now, pack=pack, new_cx="", new_cy="", new_w="", new_h=""))
    return rows, added, skipped


def disagreement(rows):
    """Tỉ lệ người khác agent theo (lớp, nguồn). Trả về {(lớp, nguồn): (số khác, tổng)}."""
    total, diff = Counter(), Counter()
    for r in rows:
        if r["box_id"].startswith("image:"):
            continue
        k = (r["target"], r["source"])
        total[k] += 1
        diff[k] += r["before"] != r["after"]
    return {k: (diff[k], total[k]) for k in sorted(total)}


def scope_threshold(rows, min_rate):
    """rows: (chiều cao người px, người đủ lớn hay không). Chiều cao nhỏ nhất mà mọi người cao từ đó trở lên đạt tỉ lệ min_rate."""
    rows = sorted(rows)
    best = None
    ok = sum(r[1] for r in rows)
    n = len(rows)
    for height, good in rows:
        if n and ok / n >= min_rate:
            best = height
            break
        ok -= good
        n -= 1
    return best


def parse_yolo(text):
    """Dòng nhãn YOLO thành (lớp, cx, cy, w, h)."""
    out = []
    for line in text.splitlines():
        t = line.split()
        if t:
            out.append((int(t[0]), *map(float, t[1:5])))
    return out


def box_iou_xyxy(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / max((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i, 1e-12)


def merge_glass_status(corr, ham, helmet_iou, cfg):
    """Ảnh CHV và CHVG ghép được không. helmet_iou None: ảnh không có mũ để so, chỉ dựa vào độ giống ảnh."""
    if corr < cfg["min_corr"] or ham > cfg["max_hamming"]:
        return "image_mismatch"
    if helmet_iou is None:
        return "no_helmet_check"
    return "ok" if helmet_iou >= cfg["min_helmet_iou"] else "box_mismatch"


def cover_fraction(box, regions):
    """Phần diện tích `box` bị các vùng che phủ, đo trên lưới để không đếm trùng chỗ hai vùng chồng nhau."""
    x1, y1, x2, y2 = box
    if x2 <= x1 or y2 <= y1:
        return 0.0
    xs = np.linspace(x1, x2, 32)
    ys = np.linspace(y1, y2, 32)
    hit = np.zeros((32, 32), dtype=bool)
    for a, b, c, d in regions:
        hit |= ((ys[:, None] >= b) & (ys[:, None] <= d)) & ((xs[None, :] >= a) & (xs[None, :] <= c))
    return float(hit.mean())


def mask_decision(regions, labelled, max_cover):
    """Che được khi không hộp đã gán nào bị che quá max_cover. labelled: (lớp, x1, y1, x2, y2). Trả về (được, mức che lớn nhất)."""
    worst = max((cover_fraction(b[1:], regions) for b in labelled), default=0.0)
    return worst <= max_cover, worst


def ignore_filter(tp, boxes, classes, ignore, iou_min=0.5):
    """Bỏ dự đoán sai trùng vùng `ignore` (không tính đúng, không tính sai). ignore: (lớp, x1, y1, x2, y2). Trả về mặt nạ giữ lại."""
    keep = np.ones(len(boxes), dtype=bool)
    for i, b in enumerate(boxes):
        if tp[i].any():
            continue
        if any(c == classes[i] and box_iou_xyxy(b, g) >= iou_min for c, *g in ignore):
            keep[i] = False
    return keep

