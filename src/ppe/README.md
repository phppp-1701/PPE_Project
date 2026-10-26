# src/ppe — Code chính

Mỗi file ứng với một bước xử lý:

| File | Việc |
|---|---|
| `detector.py` | Chạy YOLO11s, trả về hộp người và PPE |
| `tracker.py` | Chạy ByteTrack cho hộp người |
| `association.py` | Gán mũ, áo, găng cho đúng người theo vùng cơ thể |
| `compliance.py` | Kết luận Có / Thiếu / Chưa xác định |
| `temporal.py` | Cửa sổ thời gian xác nhận vi phạm, khắc phục |
| `events.py` | Mở, cập nhật, đóng sự kiện cảnh báo |
| `pipeline.py` | Nối các bước trên thành một luồng |

Người dùng không cần chạy trực tiếp các file này; các script trong `scripts/` gọi chúng.
