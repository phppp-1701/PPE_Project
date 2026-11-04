# 2026-11-04 — Chạy thử chuỗi xử lý trên 2 video (bước 3a–3b)

Mục đích: kiểm tra code chạy đúng trên video thật, xem lỗi bằng mắt. Không phải đánh giá chính thức (chưa có nhãn video, chưa chọn tham số video).

## Lệnh và dữ liệu

```
python scripts/05_run_video.py data/videos/video1.mp4
python scripts/05_run_video.py data/videos/video2.mp4
```

Video (nguồn trong `data/videos/video_sources.csv`): video1 — stock công trường, 1280×720, 30 FPS, 64,7 s, nhiều cảnh cắt ghép (spec loại khỏi bộ đánh giá); video2 — camera giám sát cố định trong xưởng/kho, 1920×1080, 6 FPS, 17 s. Detector r2 (`imgsz` 960), conf/NMS/vùng cơ thể chọn trên val ngày 04/11; ByteTrack mặc định Ultralytics (chưa chỉnh). Chạy tới bước `associate` (bước 3c còn tham số null).

## Kết quả

| | video1 | video2 |
|---|---|---|
| FPS toàn luồng (gồm đọc, vẽ, ghi video) | 17,3 | 7,5 (video ngắn, khung khởi động chiếm phần lớn) |
| Detector p50 / p95 (ms) | 28 / 86 | 50 / 77 |
| Số quỹ đạo (ID) | 24 | 18 (khoảng 8 người) |

Quan sát và kiểm tra thêm:

- **Số ID nhảy cóc**: BYTETracker của Ultralytics cấp số cho cả quỹ đạo thử chỉ sống 1 khung (video1 hiện tới "ID66" nhưng chỉ có 24 quỹ đạo). Đã đổi sang số hiển thị liên tục (`src/ppe/tracker.py`).
- **Đổi ID thật** (video2: 13 ID sinh ra giữa video): video 6 FPS (người di chuyển xa giữa hai khung) và hộp người lúc có lúc không. Cần chỉnh ByteTrack trên video chỉnh tham số.
- **Mất khung người** (video2): số người đạt conf 0,39 mỗi khung dao động 2–8 (thực tế khoảng 7–8); ở conf ≥ 0,1 trung bình 7,1 (NMS 0,5) / 8,7 (NMS 0,7). Nguyên nhân chính ở detector (người nhỏ, nhìn từ trên cao, bị che), không phải NMS.
- **Áo phản quang không được nhận ở video2**: conf áo cao nhất 0,10–0,25 (ngưỡng 0,40), cả ở `imgsz` 1280. Kiểm tra dữ liệu train (`outputs/results/data_vest_helmet_check/`): hộp vest theo màu chủ đạo — CHV vàng-xanh 626 / cam 389 / đỏ 64; Construction-PPE 331 / 286 / 348; SH17 95 / 144 / 25 → dữ liệu có nhiều áo cam, đỏ; màu không phải nguyên nhân. Người ở video2 chỉ cao 70–90 px ở đầu vào 960; cắt vùng có người và phóng to (người cao khoảng 240–260 px) thì cùng mô hình nhận áo với conf 0,52–0,73 → nguyên nhân là **cỡ người quá nhỏ**.
- **Thử dò PPE trên ảnh cắt từng người** (cắt hộp người nới 15%/10%, `imgsz` 320, chỉ khám phá): video2 hai khung — áo đạt ngưỡng ở 5/10 người (cả khung: 0/10); thời gian 28–83 ms cho 4–6 ảnh cắt (lần đầu có khởi động). video1 người to: kết quả gần như cả khung.
- **Mũ lưỡi trai / mũ vải bị nhận là mũ bảo hộ** (video1, cả khung và ảnh cắt, conf 0,64–0,78). Nhãn helmet trong train là mũ bảo hộ thật (xem mẫu `helmet_*.jpg`), nên đây là lỗi phân biệt của mô hình, không phải lỗi nhãn.
- **Áo cam mặc ngoài quần yếm xanh** (video1, khung cuối) không được nhận cả khi cắt ảnh → lỗi ngoại hình, không phải cỡ.

## Thêm chế độ dò PPE trên ảnh cắt (nhóm chọn hướng B, 04/11/2026)

`python scripts/05a_calibrate_val.py --crop` (val, chỉ chấm PPE nằm trong người detector tìm được với conf person ≥ 0,39; ảnh cắt = hộp người nới 10% mỗi phía). F1 trung bình mũ/áo/găng ở conf tốt nhất:

| Chế độ | Tất cả | Người < 120 px (ở 960) | 120–240 px | ≥ 240 px | ms/người |
|---|---|---|---|---|---|
| full (cả khung) | **0,789** | 0,486 | **0,651** | **0,838** | – |
| crop256 | 0,717 | **0,578** | 0,608 | 0,755 | 10,8 |
| crop320 | 0,738 | 0,564 | 0,644 | 0,776 | 10,6 |
| crop480 | 0,753 | 0,555 | 0,628 | 0,799 | 13,2 |

Ảnh cắt chỉ giúp người nhỏ (nhóm < 120 px: áo 0,471 → 0,571, găng 0,242 → 0,455 với crop256), kém hơn ở người lớn. → Chọn `ppe_source: auto`: người < 120 px dùng crop256 (conf mũ 0,50 / áo 0,57 / găng 0,42, chọn trên nhóm này, ít mẫu: 82/47/34 hộp nhãn), người lớn hơn dùng cả khung. Ghi trong `configs/pipeline.yaml` và spec 5.1 (bổ sung).

Chạy lại video2 với `auto`: áo được nhận ở nhiều người xa (trước: không áo nào đạt ngưỡng); một số áo chưa gán được người (`Ao?`, vùng thân chọn trên ảnh chụp ngang không khớp góc nhìn từ trên cao); người gần camera (≥ 120 px, dùng cả khung) vẫn chưa được nhận áo. video1 chạy bình thường (detector p50 19,8 ms).

## Nhận xét

- Hệ thống chạy đúng cấu trúc: phát hiện → theo dõi → gán PPE cho đúng người và đúng tay trên video1.
- Với camera xa (người dưới khoảng 100 px), detector không thấy PPE; nếu không xử lý, bước 3c sẽ kết luận Thiếu sai hàng loạt. Thiết kế đã có `area_min_px` (vùng quá nhỏ → Chưa xác định); cần chọn trên video chỉnh tham số.
- Lỗi mũ lưỡi trai và áo kiểu lạ cần thêm dữ liệu hoặc ghi là hạn chế.
