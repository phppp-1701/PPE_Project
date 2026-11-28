"""Trang kiểm định cho người dùng: mỗi sự kiện chuẩn (và mỗi người không có sự kiện) một thẻ, 3 ảnh trong khoảng thời
gian, hộp người, món thiếu; người dùng bấm Đúng / Sai / Không chắc rồi tải file JSON. Không có dự đoán của hệ thống.

    python data/videos/event_eval/tools/audit_page.py   # -> labels/audit.html
"""

import base64
import json
import os
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[4]
EV = ROOT / "data" / "videos" / os.environ.get("EV_SET", "event_eval")   # EV_SET=event_eval_2
L = EV / "labels"
VN = {"helmet": "mũ bảo hộ", "vest": "áo phản quang", "gloves": "găng tay", "goggles": "kính bảo hộ", "boots": "ủng/giày bảo hộ"}


def shot(v, tr, tracks, t):
    fps = tr["fps"]
    f = int(round(t * fps))
    cap = cv2.VideoCapture(str(EV / f"{v}.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, f)
    ok, im = cap.read()
    cap.release()
    if not ok:
        return ""
    best = None
    for tid in tracks:
        fb = tr["tracks"].get(tid, {})
        near = [int(k) for k in fb if abs(int(k) - f) <= fps]
        if near:
            k = min(near, key=lambda x: abs(x - f))
            best = fb[str(k)]
    if best:
        x1, y1, x2, y2 = map(int, best)
        cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 255), max(3, im.shape[1] // 300))
    s = 480 / im.shape[1]
    im = cv2.resize(im, None, fx=s, fy=s)
    return base64.b64encode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 80])[1]).decode()


def main():
    gt = json.loads((L / "events_gt.json").read_text(encoding="utf-8"))["events"]
    A = json.loads((L / "work" / "spec_A.json").read_text(encoding="utf-8"))["videos"]
    items = []
    for v, persons in A.items():
        tr = json.loads((L / "work" / f"{v}_tracks.json").read_text(encoding="utf-8"))
        evs = gt.get(v, [])
        for name, pa in persons.items():
            mine = [e for e in evs if e["person"] == name]
            fr = sorted(int(f) for t in pa["tracks"] for f in tr["tracks"].get(t, {}))
            t0, t1 = fr[0] / tr["fps"], fr[-1] / tr["fps"]
            if mine:
                for e in mine:
                    ts = [e["start"] + 0.5, (e["start"] + e["end"]) / 2, e["end"] - 0.5]
                    claim = f"Người trong khung vàng THIẾU: {', '.join(VN[m] for m in e['missing'])} — từ {e['start']:.1f} s đến {e['end']:.1f} s"
                    items.append(dict(id=f"{v}_{name}_{e['start']}", video=v, claim=claim, imgs=[shot(v, tr, pa["tracks"], t) for t in ts]))
            else:
                ts = [t0 + 0.5, (t0 + t1) / 2, t1 - 0.5]
                items.append(dict(id=f"{v}_{name}_none", video=v, claim=f"Người trong khung vàng KHÔNG thấy rõ thiếu món nào ({t0:.1f}-{t1:.1f} s) — không có sự kiện",
                                  imgs=[shot(v, tr, pa["tracks"], t) for t in ts]))
    cards = "".join(f"""<div class="card" data-id="{it['id']}"><h3>{k + 1}. {it['video']}.mp4</h3><p>{it['claim']}</p>
<div class="imgs">{''.join(f'<img src="data:image/jpeg;base64,{b}">' for b in it['imgs'] if b)}</div>
<div class="bar"><label><input type="radio" name="{it['id']}" value="dung"> Đúng</label>
<label><input type="radio" name="{it['id']}" value="sai"> Sai</label>
<label><input type="radio" name="{it['id']}" value="khong_chac"> Không chắc</label>
<input type="text" placeholder="ghi chú nếu Sai (vd thực ra có đeo kính)" style="flex:1"></div></div>""" for k, it in enumerate(items))
    html = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kiểm định nhãn sự kiện</title><style>
:root{{--bg:#f6f6f4;--fg:#1d1d1b;--line:#d9d9d4;--acc:#1f6feb}} body{{margin:0;padding:12px 16px;font:14px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--fg)}}
.card{{background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px;margin:10px 0}} h3{{margin:0 0 4px;font-size:15px}}
.imgs{{display:flex;gap:6px;flex-wrap:wrap}} .imgs img{{width:min(32%,480px);height:auto;border:1px solid var(--line)}}
.bar{{display:flex;gap:12px;align-items:center;margin-top:6px;flex-wrap:wrap}} input[type=text]{{padding:4px 6px;border:1px solid var(--line);border-radius:6px}}
button{{font:inherit;padding:6px 12px;border-radius:6px;border:1px solid var(--acc);background:var(--acc);color:#fff}}</style></head><body>
<h1 style="font-size:18px">Kiểm định nhãn sự kiện (event_eval, nhãn máy hai lượt)</h1>
<p>Mỗi thẻ là một kết luận của nhãn máy. Xem 3 ảnh (đầu, giữa, cuối khoảng thời gian), người cần xét nằm trong <b>khung vàng</b>.
Bấm <b>Đúng</b> nếu kết luận đúng với mắt bạn; <b>Sai</b> nếu sai (ghi lý do); <b>Không chắc</b> nếu ảnh không đủ rõ. Quy tắc: mũ lưỡi trai,
mũ len, mặt nạ hàn không phải mũ bảo hộ; kính thường không phải kính bảo hộ. Chưa có dự đoán nào của hệ thống trên các video này.</p>
<p><input type="text" id="who" placeholder="tên người kiểm định"> </p>{cards}
<button id="save">Tải file kết quả (audit_result.json)</button>
<script>
document.getElementById('save').onclick=()=>{{const who=document.getElementById('who').value; if(!who){{alert('Nhập tên người kiểm định');return;}}
const out={{auditor:who,saved_at:new Date().toISOString(),items:[...document.querySelectorAll('.card')].map(c=>({{id:c.dataset.id,
verdict:(c.querySelector('input[type=radio]:checked')||{{}}).value||null,note:c.querySelector('input[type=text]').value}}))}};
if(out.items.some(i=>!i.verdict)&&!confirm('Còn thẻ chưa chọn. Vẫn lưu?'))return;
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,1)],{{type:'application/json'}}));a.download='audit_result.json';a.click();}};
</script></body></html>"""
    (L / "audit.html").write_text(html, encoding="utf-8")
    print(len(items), "thẻ ->", L / "audit.html")


if __name__ == "__main__":
    main()
