# 2026-11-05 — Chỉnh tham số trên video2 (bước 3c)

Mục đích: chọn tham số theo dõi, trạng thái trên video chỉnh tham số. Không phải đánh giá chính thức; video2 không dùng để đánh giá cuối.

## Dữ liệu và lệnh

- video2: camera cố định góc cao, 1920×1080, 6 FPS, 17 s, 102 khung.
- Nhãn: `data/videos/video2_cvat.zip`, 10 người, 833 hộp. Nguồn nhãn ghi ở `data/videos/video2_notes.txt`: hộp người do người và máy vẽ, người sửa; **trạng thái PPE do Claude gán theo yêu cầu người dùng**, xem cách 6 khung, chưa người duyệt độc lập.
- Lệnh: `python scripts/05d_calibrate_video.py video2 --tracker`, `--state`, `--rerun`. Kết quả: `outputs/results/pipeline_calib_video/video2/`.

## ByteTrack

216 bộ tham số, ghép IoU ≥ 0,5.

| Cấu hình | IDF1 | MOTA | IDSW | Số ID | FN | FP |
|---|---|---|---|---|---|---|
| Mặc định Ultralytics | 0,572 | 0,477 | 10 | 18 | 354 | 72 |
| Đã chọn (`new_track_thresh` 0,39, `fuse_score` false) | 0,636 | 0,454 | 4 | 11 | 352 | 99 |

IDF1 tốt nhất là 0,637 nhưng phải đổi thêm `match_thresh`, IDSW 5, nên giữ bộ đổi ít hơn. MOTA giảm nhẹ vì FP tăng. Khoảng 42% hộp nhãn không ghép được với người nào (FN 352/833), lỗi chủ yếu ở bước phát hiện người hoặc hộp lệch, không phải ByteTrack.

## Trạng thái áo: lỗi ở detector

Với config trước khi đổi, trong 480 lượt người có áo ghép được: áo gán đúng 97, không dò được áo trong hộp người 365, dò được nhưng bị loại khi gán 18.

Thử trên 204 mẫu cách 4 khung, tỉ lệ người có hộp áo đạt conf 0,40 (hộp nhãn):

| Cỡ người | Cả khung 960 | Ảnh cắt 256 | Ảnh cắt 320 | Ảnh cắt 480 |
|---|---|---|---|---|
| < 150 px (n = 124) | 0,00 | 0,32 | 0,30 | 0,26 |
| 150–250 px (n = 75) | 0,00 | 0,33 | 0,37 | 0,39 |

Lưới `max_person_px` × `crop.imgsz` (conf giữ nguyên):

| `max_person_px` | `crop.imgsz` | Áo đúng | Báo Thiếu áo sai | Mũ đúng (Thiếu) | Báo Có mũ sai | ms/khung |
|---|---|---|---|---|---|---|
| 120 | 256 | 97 | 302 | 337 | 61 | 90 (gồm khởi động) |
| 120 | 480 | 104 | 295 | 362 | 36 | 76 |
| **180** | **320** | **163** | **236** | 338 | 60 | 60 |
| 180 | 480 | 150 | 249 | 362 | 36 | 80 |

Chọn 180 + 320, ưu tiên áo. `crop.imgsz` 480 giảm báo Có mũ sai (60 → 36) nhưng kém hơn về áo. Giá trị 240 và 2000 cho kết quả bằng 180. Conf ảnh cắt chọn cho crop256, chưa chọn lại cho crop320; không hạ trên video2 vì video này không có ai thiếu áo, không đo được nhận nhầm.

## Ngưỡng trạng thái: chưa đủ cơ sở để chọn

900 dòng thử, ở `max_person_px` 180, `crop.imgsz` 320. 481 lượt ghép được:

- `ambiguity_margin` (0,02–0,2) và `tau_in` (0,5–0,9): không đổi kết quả áo. Không có người ở mép khung đủ để đo.
- `tau_occ`: 1,0 → 0,4 giảm báo Thiếu áo sai 236 → 205, Coverage 0,832 → 0,736.
- `area_min_px`: áo 1.600 giảm báo Thiếu sai 205 → 134 nhưng áo đúng 148 → 81, Coverage 0,447. Không tách được đúng và sai, vì người lớn cũng bị sót áo.
- Mũ: mọi trường hợp nhãn gần như Thiếu; 60 lượt báo Có sai (mũ lưỡi trai, mũ vải).
- Găng: nhãn Chưa xác định 353 nhưng hệ thống báo Thiếu 294 trong số đó. Hình học hộp người không biết tay khuất sau bàn hay thùng.

Vì vậy `ambiguity_margin`, `tau_in`, `tau_occ`, `area_min_px` vẫn để null.

## Thử cửa sổ thời gian (chỉ khám phá, chưa chọn)

Theo người, áo ở `tau_occ` 0,4: có người được nhận gần hết (63 Có, 0 Thiếu), có người không bao giờ được nhận (0 Có, 78 Thiếu). Số người bị báo thiếu áo sai trên 8 người có lượt ghép:

| `T_on` | `theta_on` 0,6 | 0,8 | 1,0 |
|---|---|---|---|
| 1 s | 7 | 6 | 6 |
| 3 s | 5 | 5 | 3 |
| 5 s | 3 | 3 | 2 |

Cửa sổ dài hơn giảm báo sai nhưng không hết, vì người không bao giờ được nhận áo thì không cửa sổ nào cứu được. Video 17 s không đủ để chọn `T_on`; không có khắc phục nên không đo được `T_off`, `n_off`, `theta_off`. Tham số `temporal` vẫn để null.

## Kết luận

- Đã chọn và ghi vào `configs/pipeline.yaml`: `tracker.new_track_thresh`, `tracker.fuse_score`, `detector.crop.max_person_px`, `detector.crop.imgsz`.
- Video2 tuy cải thiện được theo dõi và áo, nhưng lỗi chính là detector trên góc nhìn cao: mô hình r2 không nhận được áo ở nhiều người. Chỉnh ngưỡng không sửa được lỗi này.
- Cần: video có người thiếu PPE và thấy rõ tay; dữ liệu train góc cao hoặc train trên ảnh cắt nếu muốn hệ thống dùng được ở camera kiểu này.
- Mọi tham số trên chỉ dựa trên một video 17 s, cần xem lại khi có thêm video chỉnh tham số.

## Bổ sung cùng ngày: thêm YOLO11n-pose và giá trị tạm

Nhóm đồng ý bật pose (tùy chọn có điều kiện, spec 5.2) và đặt giá trị tạm để chạy đủ luồng. Chưa kiểm tra pose trên val.

Găng trên video2, `tau_in` 0,7, `tau_occ` 0,4, `ambiguity_margin` 0,1, 481 lượt ghép:

| Cách xét tay | Coverage | macro-F1 | Nhãn Chưa xác định bị báo Thiếu | Thiếu đúng | Nhãn Có bị báo Thiếu |
|---|---|---|---|---|---|
| Vùng hình học | 0,802 | khoảng 0,28 | 280 | 91 | 15 |
| Pose ảnh cắt 320, `wrist_conf` 0,9 | 0,378 | 0,453 | 98 | 84 | 0 |

Đánh đổi: Coverage giảm vì hệ thống kết luận ít hơn. 18 lượt nhãn Có găng đều thành Chưa xác định, vì r2 không dò được găng ở các tay này. Thử trước đó: cả khung 960 tệ hơn nhiều (Thiếu đúng 17 ở `wrist_conf` 0,9), ảnh cắt 256 kém ảnh cắt 320 một chút.

Giá trị tạm trong `configs/pipeline.yaml`, ghi rõ TẠM: `ambiguity_margin` 0,1; `tau_in` 0,7; `tau_occ` 0,4; `area_min_px` 0; `T_on`, `T_off` 5 s và `theta_on`, `theta_off` 0,7 theo bài 24; `n_on`, `n_off` 5 chưa có căn cứ.

Chạy đủ luồng (`python scripts/05_run_video.py`, gồm ghi video):

| Video | FPS toàn luồng | Detector p50 / p95 (ms) | Pose p50 / p95 (ms) | Số sự kiện |
|---|---|---|---|---|
| video1 | 15,86 (17,3 trước khi có pose) | 28,8 / 39,5 | 22,7 / 33,4 | 11 |
| video2 | 5,65 (có khởi động, video ngắn) | 68,9 / 139,3 | 34,8 / 103,4 | 10 |

Trên video2, 6 trong 10 sự kiện có `vest` trong `missing_items`, là báo sai vì mọi người đều mặc áo. Sự kiện `helmet` khớp nhãn nhưng là do r2 không thấy mũ, không phải kiểm chứng được khả năng nhận mũ. Chưa tính Event F1: chưa có sự kiện chuẩn.

## Kiểm tra pose trên val (`python scripts/05a_calibrate_val.py --pose`)

448 người có găng trong nhãn, 706 găng nhãn thật (người nhỏ chỉ 34 găng), pose 22,1 ms/người khi chạy theo ảnh. Vùng tay cũ chứa 90,2% tâm găng. Tỉ lệ tâm găng nằm trong elip / tỉ lệ găng có cổ tay đạt ngưỡng:

| `wrist_conf` | `rho` 0,15 | `rho` 0,3 | Có cổ tay đạt ngưỡng |
|---|---|---|---|
| 0,5 | 76,6% | 89,2% | 96,3% |
| 0,7 | 74,5% | 86,0% | 93,5% |
| 0,9 | 55,0% | 63,3% | 73,5% |

`rho` 0,15 quá nhỏ, nên đổi sang 0,3; video2 giữ nguyên kết quả. Ở `wrist_conf` 0,9, 26,5% găng thành Chưa xác định và khoảng 10% găng có cổ tay đạt ngưỡng nhưng nằm ngoài elip, tức có thể bị báo Thiếu sai. `wrist_conf` thấp giữ được nhiều găng hơn nhưng trên video2 báo Thiếu sai tăng mạnh (0,7: 215). Giá trị 0,9 ưu tiên ít báo sai trên video2; cần chọn lại khi có video thấy rõ tay. Val chỉ có người đeo găng nên không đo được tay trần.

Chạy lại video2 đủ luồng: 9,06 FPS, 10 sự kiện (5,65 FPS lúc trước gồm khởi động mô hình).
