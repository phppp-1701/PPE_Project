# src/ppe — Code chính

Mỗi file ứng với một bước xử lý:

| File | Việc |
|---|---|
| `__init__.py` | Kiểu dữ liệu dùng chung (`Det`, `Track`, ba trạng thái), đọc `configs/pipeline.yaml`, báo lỗi khi tham số còn null |
| `detector.py` | Chạy YOLO11s, trả về hộp người và PPE; `ppe_source` = `full` (PPE dò cả khung), `crop` (PPE dò trên ảnh cắt từng người) hoặc `auto` (ảnh cắt cho người nhỏ, cả khung cho người lớn) |
| `tracker.py` | Chạy ByteTrack cho hộp người |
| `pose.py` | Tìm cổ tay bằng YOLO11n-pose trên ảnh cắt từng người (bật/tắt ở `configs/pipeline.yaml` mục `pose`) |
| `parts.py` | Bước kiểm tra thứ hai cho găng, ủng, kính: cắt ảnh tay, chân, mắt theo keypoint, phân loại bằng YOLO11n-cls (bật ở mục `part_cls`) |
| `association.py` | Gán mũ, áo, găng cho đúng người theo vùng cơ thể |
| `compliance.py` | Kết luận Có / Thiếu / Chưa xác định |
| `temporal.py` | Cửa sổ thời gian xác nhận vi phạm, khắc phục |
| `events.py` | Mở, cập nhật, đóng sự kiện cảnh báo |
| `pipeline.py` | Nối các bước trên thành một luồng |

Người dùng không cần chạy trực tiếp các file này; các script trong `scripts/` gọi chúng.
