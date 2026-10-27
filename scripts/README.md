# scripts — Các lệnh chạy theo thứ tự

| File | Việc | Bước kế hoạch |
|---|---|---|
| `00_check_env.py` | Kiểm tra PyTorch nhận GPU, chạy thử YOLO11s trên ảnh mẫu | 0 |
| `01_convert_labels.py` | Đổi nhãn từng bộ về bốn lớp theo `configs/label_map.yaml`, ghi vào `data/ppe4/converted/` (chưa chép ảnh) | 1 |
| `01a_cvat_export.py` | Đóng gói nhãn 4 lớp của một bộ (vd. CHV) thành các phần định dạng CVAT YOLO 1.1 kèm zip ảnh, để gán bổ sung găng tay | 1 |
| `02_check_data.py` | Tìm nhãn lỗi, ảnh trùng | 1 |
| `03_split_data.py` | Chia train/val/test theo nhóm ảnh | 1 |
| `04_train.py` | Huấn luyện YOLO11s | 2 |
| `05_run_video.py` | Chạy một video qua toàn bộ hệ thống | 3 |
| `06_evaluate.py` | Tính độ đo, so sánh cấu hình A-E | 5 |

Các file sẽ được viết dần khi làm tới bước tương ứng.
