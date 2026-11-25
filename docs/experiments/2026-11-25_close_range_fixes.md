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
- Sửa trước khi chạy (25/11/2026): val là ảnh rời, không có chuỗi khung nên không chọn được `hold_conf`, `hold_iou` trên
  val. Đặt theo mức đã có, không chỉnh: `hold_conf` = `tracker.track_low_thresh` 0,10 (ý tưởng ghép hộp điểm thấp với đối
  tượng đang theo dõi của ByteTrack; cũng là mức thấp nhất detector trả về), `hold_iou` = `calibration.match_iou` 0,5.
  `hold_s` dùng lại `compliance.have_hold_s` (mũ 1,0; áo 1,0; găng 1,5; kính 2,0; ủng 1,5 — đều ≤ 2 s). Hộp điểm thấp
  khớp vị trí nhớ thì làm mới thời điểm nhớ (là bằng chứng); không có thì giữ Có tối đa `hold_s`. Không giữ khi bộ phân
  loại chắc không có PPE (phiếu neg), khi phủ quyết C2/M1 hay mâu thuẫn C2 (bằng chứng âm thắng).
- **Tiêu chí F2**: trên video3-6 (05h): tổng số lần đổi trạng thái mỗi phút (mọi PPE) giảm ≥ 80% so với hiện tại; V1, V2 như
  F1 không xấu đi; Event F1 A→E (06) không giảm; thời gian giữ tối đa `hold_s` ≤ 2 s (tháo PPE thật thì báo chậm tối đa
  2 s, bảo đảm bằng thiết kế, có unit test).

## F3 — phủ quyết kính chỉ khi detector không chắc

- Bộ phân loại chỉ bác bỏ hộp kính khi điểm detector của hộp < `veto_max_conf` (chọn trên val).
- **Tiêu chí F3**: trên val (kính val_new + CHVG): số kính thật bị bác bỏ giảm; trên video3-6 và video11 (kính cận, lý do
  bật phủ quyết 13/11/2026): kính báo Có sai không tăng.
- Cách chọn (ghi 25/11/2026, trước khi chạy; `05e --goggles-veto-conf`): ảnh val tập `goggles_all` (C5 eval, val_new + CHVG
  val), chạy detector như pipeline (có zoom), người = hộp người detector đạt conf, pose + bộ phân loại như pipeline, ghép
  bằng Associator. Hộp kính gán cho người mà phiếu bộ phân loại là neg = hộp bị phủ quyết; đúng nếu IoU ≥ 0,5 với hộp kính
  nhãn, sai nếu không. `veto_max_conf` = conf lớn nhất của hộp **sai** bị phủ quyết, làm tròn lên 0,01 → trên val không bỏ
  ca phủ quyết đúng nào, chỉ thả kính thật có conf cao hơn mọi hộp sai.

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

### F1 lần 2 cho ủng (người dùng chọn 25/11/2026; ghi trước khi chạy)

- Chỉ ủng; găng bỏ khỏi F1 (chuyển sang F2). Neo mắt cá như lần 1 (cùng `k_ankle` tự chọn), thêm **cổng người bị cắt**:
  chỉ dùng neo khi mép trên hộp người ≤ `edge_px` (người bị khung cắt phía trên, chỉ thấy phần dưới — đúng ca lỗi video25,
  video26). `edge_px` = `compliance.keypoint_gate.helmet.edge_px` (4 px, mức đã dùng để nhận "đầu chạm mép trên"), không
  thêm tham số mới. Người không chạm mép trên: gán như hiện tại.
- Tiêu chí giữ nguyên (a)-(d) và hồi quy video3-6 (V1, V2). Không đạt thì không bật, ghi Giới hạn.

**Kết quả lần 2 (25/11/2026): không đạt.** `assoc_close_edge.json`. Ảnh đủ: ghép đúng 64 → 65 / 72, sai người 0 → 0, V3b
7 → 7 (cổng làm người không bị cắt gần như giữ nguyên). Các mức cắt như lần 1: 60%: đúng 40 → 72, sai người 0 → 1, V3b
4 → 5; 45%: 18 → 70, V3b 3 → 4; 30%: 9 → 40, V3b 1 → 1. (c), (d) không đạt.
Xem từng ca (`scratchpad`, không lưu): các ca xấu đi đều từ **một ảnh** (`construction_ppe__image1256`): ba người đứng sát,
chân đan nhau, hộp ủng nhãn là chiếc ủng bị che một phần nằm giữa người giữa và người phải; pose của người giữa đặt mắt cá
gần chiếc ủng đó. Không thử lần 3 trên val này (sẽ thành chỉnh theo một ảnh). Chờ người dùng quyết định.

**Ngoại lệ (người dùng quyết định 25/11/2026):** chấp nhận đánh đổi của lần 2 cho ủng (val không đạt (c), (d) do một ảnh).
Điều kiện còn lại giữ nguyên: hồi quy video3-6 (V1, V2 cho ủng, găng). V1 hoặc V2 xấu đi thì không bật.

**Hồi quy video3-6** (`06b evaluate`, `outputs/results/close_eval/stepF1close/`): mọi khung, mọi PPE, mọi sự kiện **giống
hệt** cấu hình trước (không ai trong video3-6 bị cắt ở mép trên) → V1, V2 đạt. **Bật** `association.ankle_anchor` trong
`configs/pipeline.yaml` (25/11/2026, ngoại lệ người dùng).

### F2 (25/11/2026): không đạt, chưa bật

Chạy `outputs/results/close_eval/stepF2/run_all.sh`: cấu hình hiện tại (đã có F1 ủng) `pipeline_base.yaml` so với
`pipeline_F2.yaml` (thêm `compliance.ppe_memory: {hold_conf: 0.10, hold_iou: 0.5}`), video3-6.

- **Nhấp nháy** (05h, `flicker_base/`, `flicker_F2/`): đổi trạng thái mỗi phút (mọi PPE, có trọng số theo thời lượng)
  42,9 → 31,6, **giảm 26,5% < 80%** → không đạt. Theo loại: Có↔Chưa xác định 276 → 139 lần (−50%, đúng hiện tượng "hộp
  hiện rồi tắt"); Thiếu↔Chưa xác định 241 → 235 (F2 không nhắm tới: bộ phận lúc thấy lúc không khi người không có PPE);
  Thiếu→Có 16 → 16; Có→Thiếu 0 → 2. Mất Có ngắn < 1 s: 120 → 58; hộp màu tắt: 150 → 80.
- **Hồi quy video3-6** (`dev36/`, nhãn người), khung Có đúng / Báo Có sai (V1) / Báo thiếu oan (V2):
  mũ 2.914 → 2.970 / 23 → **34** / 13 → 13; áo 2.430 → 2.524 / 3 → **33** / 48 → 48; găng 686 → 753 / 1 → 1 / 0 → 0;
  kính 357 → 367 / 0 → 0 / 0 → 0; ủng 318 → **651** / 0 → 0 / 61 → 61. Với ủng, găng (phạm vi V1, V2 ghi ở F1) đạt; nhưng
  mũ, áo báo Có sai tăng (giữ Có sau khi hộp thuộc người khác đi ngang, hoặc hộp điểm thấp của người khác trùng vị trí nhớ
  — giả thuyết, chưa kiểm từng ca).
- **Event F1 A→E** (`ablation_base.json`, `ablation_F2.json`): giống hệt (E 0,9565, 7 cảnh báo, 0 sai, trễ 1,405 s): giữ chỉ
  trong `have_hold_s`, khoảng mà bản cũ đã không cho báo Thiếu.
- Theo quy tắc: không bật. Chờ người dùng quyết định.

**Ngoại lệ F2 (người dùng quyết định 25/11/2026):** bật F2 **chỉ cho găng, kính, ủng** (`ppe_memory.ppe`), dù không đạt mốc
nhấp nháy −80%. Ba món này trên video3-6 không tăng báo Có sai hay Thiếu oan; bộ nhớ mỗi (người, món, bên) độc lập nên số đo
ở trên của ba món giữ nguyên khi tắt mũ, áo. Mũ, áo giữ như cũ (vì báo Có sai tăng).

### F3 (25/11/2026): không đạt, không bật

`05e --goggles-veto-conf` → `outputs/results/parts_cls/goggles_veto_conf_val.json`. 1.094 ảnh val goggles_all; 142 hộp kính
gán cho người (116 khớp nhãn). Bộ phân loại phủ quyết 23 hộp: **11 kính thật** (conf 0,21-0,80) và 12 hộp sai (conf
0,15-0,7995). Quy tắc cho `veto_max_conf` = 0,80 (hộp sai cao nhất 0,7995) → không thả được kính thật nào → tiêu chí "kính
thật bị bác bỏ giảm" không đạt. Conf của detector không tách được hai nhóm. Code (`part_cls.veto_max_conf`) giữ, không bật.
Ghi nhận: trên val này phủ quyết kính bỏ đúng 12 và bỏ nhầm 11 (nhãn máy có kiểm định mẫu); lý do bật phủ quyết (13/11/2026)
là kính cận trên video11. Đưa vào Giới hạn: kính bảo hộ màu (vàng, ôm mặt) có thể bị nhận là kính thường.

## Xem lại video18-27 sau F1 (ủng) + F2 (găng, kính, ủng) — 25/11/2026

`05h --ids 18-27 --out outputs/results/close_probe/after_F1F2` (cấu hình đang dùng), so với lần chẩn đoán đầu
(`close_probe/summary.json`). Video đã dùng để chẩn đoán nên đây chỉ là xem lại, không phải đánh giá khách quan.
Tỉ lệ khung Có / Thiếu, đổi trạng thái mỗi phút:

- Ủng video26 (ủng cao su, chỉ thấy cẳng chân): Có 0,08 → **0,84**, Thiếu 0,45 → **0,00**, 95 → 54 lần/phút.
- Ủng video25 (đổ bê tông, nhiều người chỉ thấy nửa dưới): Có 0,46 → 0,75, Thiếu 0,04 → 0,01, 149 → 97 lần/phút.
- Găng video18: Có 0,25 → 0,64, 514 → 115 lần/phút (mất Có ngắn 250 → 54); video19: 0,39 → 0,60, 120 → 36 (91 → 27);
  video20: 0,18 → 0,42, 109 → 76; video24: 0,79 → 0,80.
- Kính video20: Có 0,28 → 0,37. Kính video18 đổi trạng thái tăng 270 → 346 lần/phút (người ở xa, kính lúc thấy lúc không;
  giữ Có tạo thêm đổi Có↔Chưa xác định).
- Chưa sửa: kính vàng video21 vẫn bị phủ quyết (F3 không đạt); giày bảo hộ video27 (người quỳ) vẫn Thiếu 0,49 và nhảy
  ~500 lần/phút; mũ cứu hỏa video23 bị phủ quyết (ca biên).

## Đợt 2 (người dùng yêu cầu 25/11/2026: "sửa cho được, không ghi giới hạn"; làm song song)

Mục Giới hạn của báo cáo vẫn giữ những điểm thật sự chưa sửa được (trung thực học thuật), nhưng cố thu hẹp tối đa.

### B1 — bộ phân loại kính bản 6 (kính bảo hộ màu, người không đội mũ)

- Chẩn đoán (xem bằng mắt 120 ảnh cắt mỗi lớp của `data/ppe6/parts/train`): lớp `goggles` gần như toàn kính trong, người đội
  mũ, cảnh công trường (khoảng 3/120 kính vàng); lớp `ordinary_glasses` là chân dung, văn phòng, có kính râm tròng tối. Bộ
  phân loại dễ học lối tắt "tròng có màu / không mũ → kính thường" (giả thuyết, khớp video21).
- Dữ liệu thêm: bộ Roboflow Universe công khai (CC BY 4.0 hoặc Public Domain) có người **đang đeo** kính bảo hộ, có kính màu;
  người dùng tải như các bộ trước. Ảnh cắt mắt tạo như 03y (pose, `match_anchor`), **chỉ vào train**; nhãn máy, người kiểm
  định mẫu theo quy trình đã có.
- **Tiêu chí B1** (khóa trước khi train): (1) val `goggles_all` (như F3, `05e --goggles-veto-conf` với trọng số mới): kính thật
  bị phủ quyết giảm ≥ 50% (11 → ≤ 5) và hộp sai bị phủ quyết giảm không quá 2 (12 → ≥ 10); (2) val ảnh cắt mắt (05e chọn
  ngưỡng như bản 3): độ chính xác phiếu neg ≥ `precision_target.neg` 0,97; (3) hồi quy video3-6 và video11: kính báo Có sai
  không tăng.

### A1 — găng của người bị khung cắt, lần 2 (ghi trước khi chạy)

- `association.wrist_anchor` thêm hai khóa: `scale: arm_max` — thang s = max(cẳng tay khuỷu-cổ tay, bắp tay vai-khuỷu) thay
  cho chỉ cẳng tay (lần 1 hỏng vì cẳng tay chĩa về camera bị ngắn → `k_wrist` 2,39, vùng neo lấn sang người bên cạnh);
  `edge_px` — chỉ neo khi hộp người chạm **một mép bất kỳ** của khung trong `edge_px` (= `keypoint_gate.helmet.edge_px`, 4 px).
  Cần cổ tay, khuỷu ≥ `kp_conf`; bắp tay dùng khi vai ≥ `kp_conf`. `k_wrist` tự chọn như lần 1 (phân vị cao, ảnh đủ ppe4 val).
- Tiêu chí như F1: (a)-(d) trên val (`05a --assoc-close-gloves2`, cắt mép dưới 55/65/75%), rồi hồi quy video3-6 (V1, V2).

### A2 — làm mượt hiển thị trạng thái (ghi trước khi chạy)

- Phần nhấp nháy F2 không xử lý (Thiếu↔Chưa xác định 235 lần trên video3-6) là bộ phận lúc thấy lúc không. Sửa ở **lớp hiển
  thị** (`src/ppe/display.py`, khóa `display.hold_s`): ô trạng thái từng PPE trên người hiện trạng thái chắc chắn gần nhất (Có
  hoặc Thiếu) thêm tối đa `hold_s` giây khi khung hiện tại là Chưa xác định; Có↔Thiếu đổi ngay. **Không** đổi trạng thái
  từng khung, cửa sổ thời gian, sự kiện, chỉ số (unit test kiểm).
- `hold_s` chọn trên video3-6 (video chỉnh tham số) bằng 05h: giá trị nhỏ nhất trong [0,5; 1,0; 1,5; 2,0] làm số lần đổi
  trạng thái **hiển thị** mỗi phút (mọi PPE, cấu hình hiện tại) giảm ≥ 80% so với trạng thái từng khung; không giá trị nào đạt
  thì báo, không tự nới lưới.

**A1 lần 2 (25/11/2026): không đạt.** `assoc_close_gloves2.json`, `k_wrist` 1,745 (thang max(cẳng tay, bắp tay)). Ảnh đủ:
đúng 567 → 605 / 706, sai người 3 → 9, V3b 15 → 33; cắt 55%: 115 → 197, sai 1 → 5, V3b 4 → 15; 65%: 262 → 424, sai 2 → 7,
V3b 9 → 37; 75%: 382 → 504, sai 2 → 7, V3b 11 → 46. Thang mới giảm V3b so với lần 1 (71 → 33) nhưng (c), (d) vẫn không đạt.

### A1 lần 3 (ghi trước khi chạy)

Như lần 2, thêm hai điều kiện chặn gán sang người khác (khóa `wrist_anchor.exclusive: true`): (i) cổ tay neo phải là cổ tay
**gần tâm găng nhất** trong mọi cổ tay (≥ `kp_conf`) của mọi người ở khung; (ii) tâm găng nằm trong hộp người nới
`calibration.inside_margin` (10%). `k_wrist` giữ cách chọn như lần 2. Tiêu chí như cũ. Không đạt thì dừng A1 (không thử lần 4).

**A1 lần 3 (25/11/2026): không đạt (d).** `assoc_close_gloves3.json`. Ảnh đủ: đúng 567 → 602 / 706, sai người 3 → **3**, V3b
15 → 32; 55%: 115 → 198, sai 1 → 1, V3b 4 → 14; 65%: 262 → 422, sai 2 → 2, V3b 9 → 37; 75%: 382 → 501, sai 2 → 2, V3b
11 → 47. (a), (b), (c) đạt; (d) không. V3b giả lập chủ găng **không được phát hiện** (bỏ chủ, nới hộp người gần nhất bao
găng): khi đó cổ tay gần nhất còn lại là của người bên cạnh. Hậu quả nếu bật: tay người bên cạnh có thể bị báo Có găng khi
chủ găng bị detector bỏ sót (không bao giờ dẫn tới Thiếu). Dừng A1 theo kế hoạch; chờ người dùng quyết định.

**A2 (25/11/2026): đạt, bật.** `05i` trên `close_eval/stepA2/states_current` (05h, cấu hình hiện tại F1 + F2, video3-6):
đổi trạng thái từng khung (mỗi PPE của mỗi người) 28,49 lần/phút; hiển thị với hold_s 0,5 / 1,0 / 1,5 / 2,0: 8,11 / 5,89 /
5,31 / 5,31 (giảm 71,5 / 79,3 / 81,4 / 81,4%) → chọn **1,5 s**. `display.hold_s: 1.5` trong `configs/pipeline.yaml`.

### A3 — dashboard qua WebSocket (25/11/2026): xong

Người dùng đồng ý cài `websockets==15.0.1` (khóa trong `requirements.txt`, `requirements-lock.txt`). `backend/app.py`: `/ws`
đẩy "changed" khi dữ liệu đổi và trạng thái camera mỗi giây; `dashboard/index.html` nhận qua WebSocket, mất kết nối thì hỏi
định kỳ như cũ. Kiểm: `tests/test_live.py::test_ws_pushes_changes_and_live_status`; chạy uvicorn thật, client `websockets`
nhận "changed" và "live". Giao diện trình duyệt chưa kiểm bằng mắt.

**A1 ngoại lệ (người dùng quyết định 25/11/2026) và hồi quy video3-6** (`close_eval/stepA1/dev36`): găng Có đúng 753 → 754,
báo Có sai 1 → 1, Thiếu oan 0 → 0; mũ, áo, kính, ủng, sự kiện không đổi; video4 có 31 khung nhãn Chưa xác định thành Có.
V1, V2 đạt → **bật** `association.wrist_anchor` (lần 3) trong `configs/pipeline.yaml`.

### B1 — dữ liệu và cách train (ghi 25/11/2026, trước khi tạo dữ liệu)

Người dùng tải 5 bộ Roboflow (CC BY 4.0, xuất YOLOv8, không tăng cường). Xem bằng mắt mẫu hộp kính mỗi bộ:
- `goggles_sg` (Safety Goggles, lớp `eyes_with_goggles`, 405 hộp): ảnh đa dạng, nhiều người không đội mũ, chủ yếu kính trong → dùng.
- `goggles_ppes` (PPEs, lớp `goggles`, 3.346 hộp): camera phòng thí nghiệm, vài người lặp lại, không mũ → dùng sau khi bỏ ảnh
  gần trùng (pHash, `dedup_hamming` như bản 5) và giới hạn `max_ppes` hộp.
- `goggles_safety` (Safety, lớp `Safety Glasses`, 29 hộp) và `goggles_workplace` (PPE Dataset for Workplace, lớp `Glass`, 8
  hộp): có kính màu nhưng nhãn lẫn kính thường → **người dùng kiểm từng hộp** (tờ ảnh), chỉ giữ hộp người đánh dấu là kính BH.
- Safety Glasses (ảnh sản phẩm, không người đeo): bỏ.
- Chỉ thêm lớp `goggles` vào **train**; val giữ nguyên bản 4 (so sánh được với bản 3). Ảnh gần trùng ảnh đánh giá (val, test,
  pHash) bị bỏ. Ảnh cắt như bản 5: theo hộp (xê dịch) và theo keypoint (`match_anchor` mắt), tăng cường như `parts.aug`.
- Train bản 6 (YOLO11n-cls, như bản 4, `04g`), thêm tăng cường đổi sắc độ `hsv_h` 0,1 (mặc định 0,015) để mô hình không dựa
  vào màu tròng. Chỉ dùng cho kính (`weights_by_ppe.goggles`); găng, mũ, ủng giữ trọng số cũ. Tiêu chí B1 như đã khóa ở trên.
