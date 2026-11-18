# configs — Cấu hình

- `label_map.yaml`: ánh xạ mã lớp gốc của từng bộ dữ liệu sang bốn lớp, kèm vị trí ảnh/nhãn trong `data/raw/`. Dùng bởi `scripts/01_convert_labels.py`.
- `data_check.yaml`: tham số kiểm tra dữ liệu (sai số làm tròn tọa độ, mốc cỡ hộp theo COCO, ngưỡng gần trùng — để trống cho tới khi xem các cặp mẫu). Dùng bởi `scripts/02_check_data.py`.
- `split.yaml`: tỉ lệ train/val/test (70/15/15 theo spec), `seed`, bộ tham gia chia, bộ kiểm thử ngoài (Pictor-PPE), đường dẫn vào/ra. Dùng bởi `scripts/03_split_data.py`.
- `ppe4.yaml`: khai báo bốn lớp và đường dẫn dữ liệu cho YOLO.
- `train.yaml`: cấu hình huấn luyện YOLO11s (trọng số khởi tạo, `imgsz`, `epochs`, `batch`, `seed`, `cache`, tăng cường). Lần 1 giữ mặc định Ultralytics; từ r2 `patience` 20 (dừng sớm), `imgsz` 960, `copy_max_side` (thu nhỏ trước ảnh lớn trên Kaggle thay cho cache RAM). Dùng bởi `scripts/04_train.py`. Mục `analyze`: tham số phân tích lỗi trên val của `scripts/04b_analyze_val.py` (chỉ để chẩn đoán).
- `ppe6.yaml`: thử nghiệm 6 lớp (nhánh `exp/ppe6`): lớp, duyệt hộp, định nghĩa kính 2, gom cảnh, chọn tập đánh giá, cảnh lặp, kiểm tra CHVG, gói CVAT, ngưỡng người đủ lớn (còn để trống). Dùng bởi `scripts/03c`-`03l`, `04c`.
- Mục `fast_review` của `ppe6.yaml`: cổng, địa chỉ CVAT cục bộ, tên biến token, mã task cho công cụ duyệt nhanh; không chứa giá trị nhãn.
- Mục `labeling` của `ppe6.yaml`: quy trình máy gán, người kiểm định: seed từng lượt, bảng ảnh, mẫu kiểm định, mức bất đồng. Không chứa nhãn.
- `pipeline.yaml`: chuỗi xử lý video (`src/ppe`, `scripts/05*`): trọng số và `imgsz` của detector, danh sách PPE (thêm loại mới chỉ cần thêm mục), tham số ByteTrack (mặc định Ultralytics, chưa chỉnh), vùng cơ thể, khả năng quan sát, cửa sổ thời gian, mục `calibration` cho `05a`. `null` = chưa chọn; ghi ngày và cách chọn cạnh mỗi giá trị.
- `live.yaml`: chế độ camera trực tiếp (`backend/live.py`): nguồn `cam0`, chỉ số webcam, độ phân giải xin webcam, cỡ và chất lượng ảnh gửi lên trình duyệt. Tham số vận hành theo phần cứng, không phải ngưỡng nhận diện (nhận diện vẫn theo `pipeline.yaml`).
- `desktop.yaml`: tham số vận hành của ứng dụng desktop Windows (`desktop/`, nhánh `feat/desktop`): cổng tự chọn (`0`), đường dẫn dữ liệu người dùng, webcam mặc định, thiết bị suy luận (`auto`/`cuda`/`cpu`), chu kỳ giữ dữ liệu, âm cảnh báo và các mẫu PPE nhanh. Không chứa ngưỡng nhận diện.

- `ppe6.yaml` mục `error_analysis`, `speed_check`, `c5_relabel`: phân tích lỗi C4, đo tốc độ detector, sửa nhãn C5 (kế hoạch `docs/experiments/2026-11-16_c5_detector_plan.md`). Ngưỡng đề xuất của `c5_relabel` do Claude đặt từ chạy thử trên mẫu, chỉ để chọn chỗ cần xem, không chọn theo điểm mô hình.

Muốn đổi con số thì sửa ở đây, không sửa trong code.
