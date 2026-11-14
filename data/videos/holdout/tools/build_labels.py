"""Dựng nhãn tham chiếu (CVAT for video 1.1) cho video holdout từ track 05f và spec thuộc tính của Claude.

Spec JSON: {video: {"persons": [{"name": "P0",
                                  "boxes": [{"tids": [0, 1], "range": [a, b]}, ...],   # hợp các track trong khoảng
                                  "extend": {"top": 0.08, "right": 0.25, "to_top": true}, "window": 12,  # tùy chọn
                                  "attrs": {"helmet": [[0, "co"], [120, "chua_xac_dinh"]], ...}}]}}
Mỗi khung có hộp ghi một box (keyframe mỗi khung, không nội suy), thuộc tính theo mốc gần nhất phía trước. Hộp
`outside` sau khung cuối. Không có dự đoán của hệ thống nào trong quá trình này.

Cách chạy (từ thư mục gốc, .venv):
    python data/videos/holdout/tools/build_labels.py <spec.json> <thư mục ra> [--check <thư mục ảnh kiểm>]
Ghi <thư mục ra>/<video>/annotations.xml; --check vẽ hộp và thuộc tính mỗi 1 s để kiểm bằng mắt.
"""

import argparse
import json
import re
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
ORDER = ["helmet", "vest", "glove_left", "glove_right", "goggles", "boots"]
SHORT = {"co": "C", "thieu": "T", "chua_xac_dinh": "?"}


def prefill(v):
    x = (ROOT / f"outputs/results/video/holdout/{v}/prefill/annotations.xml").read_text(encoding="utf-8")
    T = {}
    for tid, body in re.findall(r'<track id="(\d+)"[^>]*>(.*?)</track>', x, re.S):
        T[int(tid)] = {int(f): None if o == "1" else [float(a), float(b), float(c), float(d)] for f, o, a, b, c, d in re.findall(
            r'frame="(\d+)" keyframe="1" outside="(\d)" occluded="0" xtl="([\d.]+)" ytl="([\d.]+)" xbr="([\d.]+)" ybr="([\d.]+)"', body)}
    n = int(re.search(r"<size>(\d+)</size>", x).group(1))
    w = int(re.search(r"<width>(\d+)</width>", x).group(1))
    h = int(re.search(r"<height>(\d+)</height>", x).group(1))
    return T, n, w, h


def at(kf, f):
    """Hộp của track tại khung f (nội suy giữa khung khóa như CVAT); None nếu track không có mặt."""
    ks = sorted(kf)
    prev = [k for k in ks if k <= f]
    if not prev or kf[prev[-1]] is None:
        return None
    a = kf[prev[-1]]
    nxt = [k for k in ks if k > f]
    if prev[-1] == f or not nxt or kf[nxt[0]] is None:
        return a
    b, r = kf[nxt[0]], (f - prev[-1]) / (nxt[0] - prev[-1])
    return [a[i] + (b[i] - a[i]) * r for i in range(4)]


def val(seg, f):
    return [v for s, v in seg if s <= f][-1]


def person_boxes(p, T, w, h):
    """Hộp người mỗi khung: hợp các track của quy tắc; `window` k: hợp thêm hộp trong ±k khung (cùng quy tắc) để hộp
    không bị hụt khi track 05f chỉ phủ một phần người; `extend`: nới mép theo tỉ lệ cạnh, `to_top`/`to_bottom`: kéo tới
    mép khung (người rất gần, đầu hoặc thân chạm mép)."""
    raw, rng = {}, {}
    for ri, rule in enumerate(p["boxes"]):
        a, b = rule["range"]
        for f in range(a, b + 1):
            bs = [at(T[t], f) for t in rule["tids"] if t in T]
            bs = [q for q in bs if q]
            if bs:
                raw[f] = [min(x[0] for x in bs), min(x[1] for x in bs), max(x[2] for x in bs), max(x[3] for x in bs)]
                rng[f] = ri
    k = p.get("window", 0)
    e = p.get("extend") or {}
    out = {}
    for f, q in raw.items():
        qs = [raw[g] for g in range(f - k, f + k + 1) if g in raw and rng[g] == rng[f]]
        q = [min(x[0] for x in qs), min(x[1] for x in qs), max(x[2] for x in qs), max(x[3] for x in qs)]
        bw, bh = q[2] - q[0], q[3] - q[1]
        q = [q[0] - e.get("left", 0) * bw, q[1] - e.get("top", 0) * bh, q[2] + e.get("right", 0) * bw, q[3] + e.get("bottom", 0) * bh]
        if e.get("to_top"):
            q[1] = 0.0
        if e.get("to_bottom"):
            q[3] = float(h)
        out[f] = [max(0.0, q[0]), max(0.0, q[1]), min(float(w), q[2]), min(float(h), q[3])]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--check")
    a = ap.parse_args()
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    for v, sv in spec.items():
        T, n, w, h = prefill(v)
        xml = ['<?xml version="1.0" encoding="utf-8"?>\n<annotations>\n  <version>1.1</version>\n',
               f'  <meta><task><name>{v}</name><size>{n}</size><mode>interpolation</mode><start_frame>0</start_frame>'
               f'<stop_frame>{n - 1}</stop_frame><original_size><width>{w}</width><height>{h}</height></original_size>'
               '<labels><label><name>person</name></label></labels></task></meta>\n']
        allb = []
        for i, p in enumerate(sv["persons"]):
            B = person_boxes(p, T, w, h)
            allb.append((p, B))
            xml.append(f'  <track id="{i}" label="person" source="manual">\n')
            fs = sorted(B)
            for f in fs:
                q = B[f]
                at_ = "".join(f'<attribute name="{k}">{val(p["attrs"][k], f)}</attribute>' for k in ORDER)
                xml.append(f'    <box frame="{f}" keyframe="1" outside="0" occluded="0" xtl="{q[0]:.2f}" ytl="{q[1]:.2f}" '
                           f'xbr="{q[2]:.2f}" ybr="{q[3]:.2f}" z_order="0">{at_}</box>\n')
                if f + 1 not in B and f + 1 < n:
                    xml.append(f'    <box frame="{f + 1}" keyframe="1" outside="1" occluded="0" xtl="{q[0]:.2f}" ytl="{q[1]:.2f}" '
                               f'xbr="{q[2]:.2f}" ybr="{q[3]:.2f}" z_order="0">{at_}</box>\n')
            xml.append("  </track>\n")
        xml.append("</annotations>\n")
        d = Path(a.out) / v
        d.mkdir(parents=True, exist_ok=True)
        (d / "annotations.xml").write_text("".join(xml), encoding="utf-8")
        print(v, n, "khung,", len(sv["persons"]), "người,", sum(len(B) for _, B in allb), "hộp")
        if a.check:
            cap = cv2.VideoCapture(str(ROOT / f"data/videos/holdout/{v}.mp4"))
            fps = cap.get(5)
            tiles = []
            for f in range(0, n, max(1, round(fps))):
                cap.set(1, f)
                ok, im = cap.read()
                if not ok:
                    continue
                for p, B in allb:
                    if f in B:
                        q = [int(x) for x in B[f]]
                        cv2.rectangle(im, (q[0], q[1]), (q[2], q[3]), (0, 0, 255), 4)
                        txt = p["name"] + " " + " ".join(k[:2].upper() + SHORT[val(p["attrs"][k], f)] for k in ORDER)
                        cv2.putText(im, txt, (q[0] + 5, max(30, q[1] + 35)), 0, 1.2, (0, 0, 255), 3)
                hh, ww = im.shape[:2]
                im = cv2.resize(im, (int(360 * ww / hh), 360))
                cv2.putText(im, f"f{f}", (5, 30), 0, 1.0, (0, 255, 255), 2)
                tiles.append(im)
            per = 4 if tiles[0].shape[1] > 400 else 8
            rows = []
            for k in range(0, len(tiles), per):
                r = tiles[k:k + per]
                r += [np.zeros_like(tiles[0])] * (per - len(r))
                rows.append(np.hstack(r))
            Path(a.check).mkdir(parents=True, exist_ok=True)
            for j in range(0, len(rows), 4):
                cv2.imwrite(str(Path(a.check) / f"check_{v}_{j // 4}.jpg"), np.vstack(rows[j:j + 4]), [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    main()
