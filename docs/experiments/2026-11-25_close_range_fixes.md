# Sửa điểm yếu tầm gần (F1, F2, F3) — 25/11/2026

Người dùng giao 24-25/11/2026 sau khi test app: người gần camera, PPE nhìn rõ mà hệ thống báo Thiếu hoặc hộp PPE nhấp
nháy. Kế hoạch này ghi **trước khi sửa**; tiêu chí khóa ở đây, không đổi sau khi thấy kết quả. Người dùng đồng ý thứ tự
F1 → F2 → F3 ngày 25/11/2026.

## Chẩn đoán (05h, video18-27 `kiem_thu_gan` đợt 2, cấu hình c6_ft + zoom N=1)

`scripts/05h_close_range_probe.py`, kết quả `outputs/results/close_probe/summary.md`. Không có nhãn, chỉ để tìm điểm yếu.

- Giả thuyết "hộp ByteTrack (lọc Kalman) nhỏ hơn người thật" **không đúng**: cao hộp track / hộp detector p10 0,98-1,00
  ở cả 10 video. Bỏ đề xuất S1.
- Nguyên nhân 1 — **người bị khung cắt**: vùng cơ thể theo tỉ lệ cố định của hộp người giả định hộp chứa cả người. Chỉ thấy
  cẳng chân thì ủng chiếm nửa dưới hộp, tâm ủng ra ngoài vùng chân (y0 = 0,795) → detector thấy ủng nhưng bị loại
  "outside". Ủng video26: 688 khung bộ phận bị loại "outside" (báo Thiếu 45% khung), video25: 190. Găng video20: 652,
  video19: 293, video24: 135 (găng thành Chưa xác định vì cổ tay dưới `pose.wrist_conf` 0,8 thì không có ứng viên).
- Nguyên nhân 2 — **điểm dao động quanh ngưỡng**: găng video18 514 lần đổi trạng thái/phút, 250 lần mất Có ngắn hơn 1 s;
  video19 120/phút, 91 lần. Phần lớn khung mất: có hộp nhưng dưới ngưỡng conf.
- Nguyên nhân 3 — **bộ phân loại phủ quyết nhầm**: kính bảo hộ vàng ôm mặt video21 bị bác bỏ 100% khung ("kính thường").

## F1 — neo PPE theo khung xương cho người bị cắt

Thêm ứng viên (hợp với vùng cũ, như bước F1 kính theo mắt 16/11/2026), không bỏ luật cũ:

- **Ủng theo mắt cá** (`association.ankle_anchor: {kp_conf, k_ankle}`): mắt cá (COCO 15/16) và gối cùng bên đạt
  `kp_conf`; s = khoảng cách gối - mắt cá (ống chân); ứng viên khi khoảng cách tâm ủng - mắt cá ≤ `k_ankle` × s.
  Khoảng cách quy về thang `max_distance` như kính.
- **Găng theo cổ tay, thang cẳng tay** (`association.wrist_anchor: {kp_conf, k_wrist}`): cổ tay và khuỷu cùng bên đạt
  `kp_conf` (thấp hơn `pose.wrist_conf`); s = khoảng cách khuỷu - cổ tay; ứng viên khi khoảng cách tâm găng - cổ tay ≤
  `k_wrist` × s. Găng gán theo đường này chỉ dẫn tới **Có** cho tay đó, không bao giờ dẫn tới Thiếu (tay vẫn "không quan
  sát được" nếu cổ tay < `pose.wrist_conf`), như F3 cũ.
- `kp_conf` = `part_cls.kp_conf` (0,5). `k_ankle`, `k_wrist` = phân vị cao (`calibration.region_coverage`, như k_eye) của
  tỉ lệ khoảng cách / s trên val (ủng: val 6 lớp có nhãn ủng; găng: ppe4 val), ảnh đủ. Chọn tự động trong 05a, không chỉnh tay.

**Tiêu chí F1** (chấm `05a --assoc-close`, chỉ val; như tiêu chí bước F 16/11/2026, thêm kiểu cắt "chỉ thấy phần dưới"):

- Cảnh: ảnh đủ; ủng cắt **mép trên** giữ phần dưới 60 / 45 / 30% chiều cao người chủ; găng cắt **mép dưới** 55 / 65 / 75%
  (như bước F). Pose chạy lại trên ảnh cắt. Hộp người, PPE là nhãn thật.
- Đạt khi, riêng từng món (ủng, găng): (a) ảnh đủ: số ghép đúng không giảm; (b) ghép đúng tăng ở ít nhất một mức cắt;
  (c) ghép sai người không tăng ở mọi mức; (d) V3b (nới hộp người gần nhất bao PPE) gán nhầm không tăng ở mọi mức.
- Hồi quy video chỉnh tham số video3-6 (nhãn người, `06b evaluate`, so với cấu hình hiện tại): với ủng và găng,
  (V1) khung nhãn Thiếu mà dự đoán Có không tăng; (V2) khung nhãn Có mà dự đoán Thiếu không tăng.
- Món nào không đạt thì không bật món đó (ghi vào Giới hạn). Người dùng quyết định cuối cùng.

## F2 — nhớ PPE theo bộ phận và hiển thị ổn định

- Mỗi (người, PPE, bên) đã có hộp gán Có: các khung sau, hộp cùng lớp có điểm ≥ `hold_conf` (thấp hơn ngưỡng) mà tâm vẫn ở
  gần vị trí cũ (IoU với hộp nhớ ≥ `hold_iou`) thì giữ Có; không có thì giữ tối đa `hold_s` giây. Tham số trong
  `configs/pipeline.yaml`; `hold_conf`, `hold_iou` chọn trên val (ảnh) theo độ chính xác hộp điểm thấp gần hộp đúng.
- App và `05_run_video` vẽ hộp đã giữ (nét đứt, ghi "giữ") thay vì để hộp tắt.
- **Tiêu chí F2**: trên video3-6 (05h): tổng số lần đổi trạng thái mỗi phút (mọi PPE) giảm ≥ 80% so với hiện tại; V1, V2 như
  F1 không xấu đi; Event F1 A→E (06) không giảm; thời gian giữ tối đa `hold_s` ≤ 2 s (tháo PPE thật thì báo chậm tối đa
  2 s, bảo đảm bằng thiết kế, có unit test).

## F3 — phủ quyết kính chỉ khi detector không chắc

- Bộ phân loại chỉ bác bỏ hộp kính khi điểm detector của hộp < `veto_max_conf` (chọn trên val).
- **Tiêu chí F3**: trên val (kính val_new + CHVG): số kính thật bị bác bỏ giảm; trên video3-6 và video11 (kính cận, lý do
  bật phủ quyết 13/11/2026): kính báo Có sai không tăng.

## Quy tắc

- Chọn tham số chỉ trên val và video chỉnh tham số. video18-27 chỉ để xem lại sau khi sửa (đã dùng để chẩn đoán, không còn
  khách quan); holdout chỉ dùng cho đánh giá cuối.
- Mỗi bước: test, commit, push, báo người dùng.

## Kết quả

### F1 lần 1 (25/11/2026): không đạt, chưa bật

`05a --assoc-close` → `outputs/results/pipeline_calib_val/assoc_close.json`. Tham số tự chọn: `k_ankle` 0,634 (72 ủng có gối,
mắt cá), `k_wrist` 2,393 (672 găng có khuỷu, cổ tay). Mẫu: ủng 32 ảnh val_new, cắt 39 ca mỗi mức; găng 379 ảnh ppe4 val.

| Món | Mức | Ghép đúng (hiện tại → F1) / n | Sai người | V3b gán nhầm |
|---|---|---|---|---|
| Ủng | ảnh đủ | 64 → 72 / 72 | 0 → 0 | 7 → 8 |
| Ủng | giữ dưới 60% | 40 → 72 / 73 | 0 → 1 | 4 → 5 |
| Ủng | giữ dưới 45% | 18 → 70 / 73 | 0 → 0 | 3 → 4 |
| Ủng | giữ dưới 30% | 9 → 40 / 72 | 0 → 0 | 1 → 1 |
| Găng | ảnh đủ | 567 → 646 / 706 | 3 → 10 | 15 → 71 |
| Găng | cắt 55% | 115 → 195 / 250 | 1 → 7 | 4 → 15 |
| Găng | cắt 65% | 262 → 424 / 485 | 2 → 11 | 9 → 45 |
| Găng | cắt 75% | 382 → 503 / 561 | 2 → 8 | 11 → 47 |

- Ủng: (a), (b) đạt; (c) sai người +1 (mức 60%), (d) V3b +1 ở ba mức → **không đạt** theo tiêu chí "không tăng".
  Ghép đúng tăng mạnh ở người chỉ thấy chân (45%: 18 → 70 / 73).
- Găng: (c), (d) không đạt rõ (V3b 15 → 71 ở ảnh đủ). `k_wrist` 2,393 lớn: cẳng tay chĩa về camera bị ngắn lại trong ảnh
  (thang s nhỏ) nên tỉ lệ khoảng cách / s phình ra, vùng neo quá rộng và lấn sang người đứng gần.
- Theo quy tắc của kế hoạch: không bật món nào; chưa chạy hồi quy video3-6. Chờ người dùng quyết định.
