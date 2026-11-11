# Hiệu chỉnh ByteTrack & Pipeline 6 lớp trên mô hình C4 (`yolo11s_ppe6_c4`)

**Ngày:** 2026-11-11
**Nhánh:** `exp/ppe6`
**Trọng số phát hiện:** `outputs/train/yolo11s_ppe6_c4/weights/best.pt` (`sha256: 98e3950d125401f3eca14ea9b15b57501d105153a0768fc1e6256d909783b8a3`, `imgsz: 960`)

---

## 1. Bổ sung bộ video chuẩn một cảnh liên tục (`data/videos/`)

Hai video cũ từ YouTube (`video1.mp4`, `video2.mp4`) có hạn chế: `video1.mp4` cắt cảnh nhiều lần và có chữ quảng cáo che ảnh; `video2.mp4` chỉ đạt 6 FPS (tua nhanh). Để hiệu chỉnh ByteTrack và đánh giá luồng thời gian thực khách quan, 6 video một cảnh liên tục (0 lần cắt cảnh, camera cố định hoặc lia mượt, tốc độ thực 25–60 FPS) từ các bộ mẫu công khai đã được tải về `data/videos/` và ghi vào `data/videos/video_sources.csv`:

| Mã | Tệp | Độ phân giải | FPS | Thời lượng (số khung) | Vai trò | Đặc điểm cảnh quay & PPE |
|---|---|---|---:|---:|---|---|
| `video3` | `data/videos/video3.mp4` | 1920×1080 | 29.97 | 65.1s (1.950) | `chinh_tham_so` | Intel IoT DevKit (`Safety_Full_Hat_and_Vest.mp4`): 7 người đi qua hành lang theo 4 đợt, đủ tổ hợp **Có** và **Thiếu** mũ, áo, găng, kính, ủng. |
| `video4` | `data/videos/video4.mp4` | 1280×720 | 30.00 | 11.6s (349) | `chinh_tham_so` | Công trường (`ppe-3-1.mp4`): 3 công nhân (2 người đủ mũ/áo/găng/ủng; 1 người đội mũ nhưng **thiếu áo phản quang**). |
| `video5` | `data/videos/video5.mp4` | 1920×1080 | 30.00 | 7.3s (219) | `chinh_tham_so` | Công trường (`demo3.mp4`): 2 người đi bộ bắt tay nhau, đều đội mũ, mặc áo, **đeo kính bảo hộ (`goggles`)**, đi ủng, **thiếu găng tay**. |
| `video6` | `data/videos/video6.mp4` | 1280×720 | 25.00 | 8.2s (206) | `chinh_tham_so` | Công trường ngoài trời (`ppe-2-1.mp4`): 2 người bị cắt ngang chân ở mép dưới ảnh; người trái có mũ/áo nhưng thiếu găng; người phải có mũ/găng nhưng thiếu áo. |
| `video7` | `data/videos/video7.mp4` | 1920×1080 | 29.97 | 15.0s (450) | `chay_thu` | Supervisely (`supervisely_construction_1.mp4`): góc camera cao toàn cảnh ~10 công nhân đổ bê tông, có che khuất. |
| `video8` | `data/videos/video8.mp4` | 1920×1080 | 59.94 | 75.9s (4.548) | `chay_thu` | Intel (`worker-zone-detection.mp4`): camera kho xưởng 60 FPS kiểm tra tốc độ thực thi dài hạn. |

> **Lưu ý về `video7.mp4` (`supervisely_construction_1.json`):** Kiểm tra trực quan khung hình 0 cho thấy tệp nhãn gốc của Supervisely chỉ gắn nhãn 4/9 công nhân có mặt trong cảnh (bỏ trống 5 công nhân thật), nếu dùng làm nhãn chuẩn chỉnh tham số sẽ phạt oan mô hình phát hiện đúng 5 người còn lại thành dương tính giả (`FP`). Do đó `video7.mp4` được xếp vai trò `chay_thu`.

Nhãn chuẩn định dạng CVAT for video 1.1 (`video3_cvat.zip` .. `video6_cvat.zip`) được tạo độc lập với mô hình C4 (sử dụng `yolo11s.pt` gốc trên COCO kết hợp ghép vết IoU và đối chiếu thuộc tính 6 lớp PPE thực tế từng nhân vật), kèm ghi chú chi tiết trong `data/videos/video{3,4,5,6}_notes.txt`.

---

## 2. Hiệu chỉnh ngưỡng phát hiện và vùng cơ thể 6 lớp trên tập `val` (`05a_calibrate_val.py`)

Chạy `scripts/05a_calibrate_val.py` trên tập `val` (1.602 ảnh: 1.586 ảnh gốc + 16 ảnh `val_new` cho lớp kính/ủng):

### 2.1. Ngưỡng `conf` và `nms_iou` (`outputs/results/pipeline_calib_val/conf.json`)
- **`nms_iou` chọn:** `0.50` (macro-F1 trên 6 lớp đạt **0.7658**).
- **Ngưỡng tự tin theo từng lớp (`detector.conf`):**

| Lớp | `conf` chọn | Precision | Recall | F1 | Quy tắc chọn |
|---|---:|---:|---:|---:|---|
| `person` (0) | `0.40` | 0.903 | 0.844 | **0.873** | Cực đại F1 trên tập `val` |
| `helmet` (1) | `0.34` | 0.922 | 0.844 | **0.881** | Cực đại F1 trên tập `val` |
| `vest` (2) | `0.28` | 0.848 | 0.747 | **0.794** | Cực đại F1 trên tập `val` |
| `gloves` (3) | `0.44` | 0.728 | 0.573 | **0.641** | Cực đại F1 trên tập `val` |
| `goggles` (4) | `0.15` | 0.808 | 0.724 | **0.764** | Cực đại F1 trên tập `val_new` (ngưỡng 0.15 giữ Precision > 0.80 và F1 cao nhất) |
| `boots` (5) | `0.15` | 0.688 | 0.530 | **0.599** | Cực đại F1 trên tập `val_new` (bắt tốt ủng ở cự ly trung bình trên video) |

### 2.2. Vùng cơ thể chuẩn hóa và khoảng cách tối đa (`outputs/results/pipeline_calib_val/regions.json`)
- Phân vị 5%–95% tâm khung PPE thật trong hệ tọa độ khung người (mở rộng biên an toàn $\pm 0.02$):
  - `head`: `x0 = 0.153, x1 = 0.829, y0 = 0.023, y1 = 0.295` (dùng chung cho cả `helmet` và `goggles` để bao phủ cả góc nhìn nghiêng khi người quay đầu).
  - `torso`: `x0 = 0.309, x1 = 0.665, y0 = 0.241, y1 = 0.732`.
  - `hands`: `x0 = 0.041, x1 = 0.961, y0 = 0.093, y1 = 0.943`.
  - `feet`: `x0 = 0.115, x1 = 0.813, y0 = 0.795, y1 = 1.020` (`y1 = 1.020 > 1.0` kết hợp `tau_in.boots = 0.95` giúp tự động trả về `chua_xac_dinh` khi khung người chạm mép dưới ảnh `y2 ≈ H`, tránh báo sai *Thiếu ủng* khi chân bị cắt khỏi khung hình).
- Khoảng cách chuẩn hóa tối đa (`association.max_distance`, phân vị 95%):
  - `helmet`: `0.299`, `vest`: `0.227`, `gloves`: `0.399`, `goggles`: `0.298`, `boots`: `0.339`.

---

## 3. Hiệu chỉnh ByteTrack trên 5 video chỉnh tham số (`05d_calibrate_video.py --tracker`)

Quét lưới 216 cấu hình ByteTrack trên toàn bộ 5 video `chinh_tham_so` (`video2`..`video6`, tổng cộng **2.826 khung hình**):

- **Tham số ByteTrack tối ưu (`configs/pipeline.yaml` -> `tracker`):**
  - `track_high_thresh`: `0.25`
  - `track_low_thresh`: `0.10`
  - `new_track_thresh`: `0.50`
  - `track_buffer`: `30`
  - `match_thresh`: `0.80`
  - `fuse_score`: `false`

- **Kết quả chi tiết theo từng video (`outputs/results/pipeline_calib_video/video{2..6}/tracker_grid.csv`):**

| Video | Số khung | Số người thật (`GT`) | Số ID mô hình tạo | IDF1 | MOTA | IDSW (Đổi ID) | Mostly Tracked (`MT`) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `video2` (6 FPS) | 102 | 10 | 10 | 0.6869 | 0.5668 | 5 | 7 / 10 |
| `video3` (30 FPS) | 1.950 | 7 | 7 | **0.9857** | **0.9718** | **0** | 7 / 7 |
| `video4` (30 FPS) | 349 | 3 | 3 | **0.9746** | **0.9498** | **0** | 3 / 3 |
| `video5` (30 FPS) | 219 | 2 | 2 | **0.9776** | **0.9863** | **0** | 2 / 2 |
| `video6` (25 FPS) | 206 | 2 | 2 | **0.9684** | **0.9752** | **0** | 2 / 2 |
| **Trung bình / Tổng** | **2.826** | **24** | **24** | **0.9186** | **0.8900** | **5** (0 trên video 25–30 FPS) | **21 / 24** |

> Trên cả 4 video tốc độ thực 25–30 FPS (`video3`..`video6`), ByteTrack đạt **0 lần đổi ID (`IDSW = 0`)**, số lượng ID tạo ra khớp tuyệt đối 100% với số người thật trong cảnh, và `IDF1` đạt từ **0.968 đến 0.986**.

---

## 4. Hiệu chỉnh Pose & Trạng thái tuân thủ 6 lớp (`05d_calibrate_video.py --state`)

1. **Cải tiến xử lý hai bàn tay chắp sát nhau (`src/ppe/association.py`):**
   - Chỉ loại bỏ phát hiện do tranh chấp (`contested`) khi hai ứng viên nằm trong khoảng `ambiguity_margin` thuộc về **hai người khác nhau** (`other_people`).
   - Phân phối găng tay luân phiên: khi người đã nhận 1 găng ở cổ tay thứ nhất, phát hiện găng tiếp theo có cổ tay còn lại trong danh sách ứng viên sẽ được gán cho cổ tay còn lại thay vì dồn cả 2 hộp vào cùng 1 bên.
   - Khi hai cổ tay của **cùng một người** chắp sát nhau khiến YOLO gộp thành 1 hộp găng tay rộng phủ cả hai cổ tay (`box_span > wrist_distance`), cả hai tay đều được công nhận là `HAVE` (đạt 481 khung `HAVE` găng tay trên `video4`, tăng từ 27 khung ban đầu).
2. **Cải tiến điều kiện công nhận có PPE (`src/ppe/compliance.py`):**
   - Đổi `if observable and has: state = HAVE` thành `if track.confident and has: state = HAVE`.
   - Khi mô hình đã phát hiện rõ ràng PPE thuộc về người đó (`has = True`), người đó được tính là `HAVE` ngay cả khi vùng cơ thể chạm mép ảnh dưới (như công nhân đứng ở sát đáy ảnh 720p trong `video4`), tăng số khung `boots = co` từ 3 khung lên **402 khung**.
   - Ngược lại, điều kiện `observable` vẫn kiểm soát chặt chẽ trạng thái `MISSING` (`thieu`), đảm bảo khi chân bị cắt khỏi khung hình và không thấy ủng thì luôn trả về `chua_xac_dinh` (đạt 374/412 khung `chua_xac_dinh` trên `video6`, tránh hoàn toàn báo động giả).
3. **Cửa sổ thời gian không đối xứng (`temporal: T_on=5.0s, T_off=2.0s, n_on=n_off=15`):**
   - `T_on = 5.0s, n_on = 15`: Tránh báo động giả khi PPE chỉ bị che khuất tạm thời 1–2 giây trong quá trình làm việc.
   - `T_off = 2.0s, n_off = 15`: Xác nhận khắc phục nhanh chóng chỉ sau ~1.4 giây khi công nhân bước vào tầm nhìn rõ (giúp cả 2 công nhân trong `video5` tự động xóa vi phạm kính `goggles` sau 5.9s và 6.47s).
4. **Độ chính xác trạng thái tuân thủ theo khung trên các video 25–30 FPS:**
   - `video3`: `helmet` macro-F1 = **0.940**, `vest` macro-F1 = **0.968**, `boots` macro-F1 = **0.935**.
   - `video4`: `helmet` F1_co = **0.996**, `vest` macro-F1 = **0.973** (`F1_co = 0.994`, `F1_thieu = 0.952`), `gloves` F1_co = **0.965**, `boots` F1_co = **0.986**.
   - `video5`: `helmet` F1_co = **1.000**, `vest` F1_co = **0.995**, `goggles` F1_co = **0.953**, `boots` F1_co = **0.941**, `gloves` F1_thieu = **0.918**.
   - `video6`: `helmet` F1_co = **0.998**, `vest` macro-F1 = **0.998** (`F1_co = 0.995`, `F1_thieu = 1.000`), `gloves` macro-F1 = **0.989** (`F1_co = 0.978`, `F1_thieu = 1.000`), và `boots` = 91% `chua_xac_dinh` (0 báo động giả khi chân ở ngoài khung hình).

---

## 5. Kết quả chạy toàn luồng thời gian thực (`05_run_video.py`)

Chạy toàn bộ 6 bước (YOLO11s C4 `imgsz=960` + YOLO11n-pose + ByteTrack + Gán vùng/Elip + Đánh giá 3 trạng thái + Làm mượt cửa sổ trượt & ghi video đầu ra) trên GPU:

| Video | Độ phân giải | Số khung | Thời gian chạy (s) | FPS toàn luồng | Độ trễ `detector` p50 (ms) | Độ trễ `pose` p50 (ms) | Độ trễ `tracker` p50 (ms) | Số sự kiện vi phạm (`events.jsonl`) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `video4` | 1280×720 | 349 | 23.69 | **14.73 FPS** | 20.63 | 19.63 | 0.83 | 3 |
| `video5` | 1920×1080 | 219 | 23.80 | **9.20 FPS** | 29.35 | 25.87 | 0.96 | 2 |
| `video6` | 1280×720 | 206 | 16.20 | **12.72 FPS** | 24.74 | 22.86 | 0.91 | 2 |
| `video7` | 1920×1080 | 450 | 44.15 | **10.19 FPS** | 43.71 | 17.54 | 1.07 | 48 |

- Các sự kiện vi phạm được ghi vào `outputs/results/video/video{4..6}/events.jsonl` kèm các ảnh bằng chứng trích xuất trong `outputs/evidence/`.
- 110/110 bài kiểm thử đơn vị trong thư mục `tests/` đạt tuyệt đối 100%.

