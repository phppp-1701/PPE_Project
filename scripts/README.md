# scripts — Các lệnh chạy theo thứ tự

| File | Việc | Bước kế hoạch |
|---|---|---|
| `00_check_env.py` | Kiểm tra PyTorch nhận GPU, chạy thử YOLO11s trên ảnh mẫu | 0 |
| `01_convert_labels.py` | Đổi nhãn từng bộ về bốn lớp theo `configs/label_map.yaml`, ghi vào `data/ppe4/converted/` (chưa chép ảnh) | 1 |
| `01a_cvat_export.py` | Đóng gói nhãn 4 lớp của một bộ (vd. CHV) thành các phần định dạng CVAT YOLO 1.1 kèm zip ảnh, để gán bổ sung găng tay | 1 |
| `01b_cvat_upload.py` | Tự tạo task trên app.cvat.ai cho các phần đã đóng gói (tải ảnh, nạp nhãn YOLO 1.1); bỏ qua task đã có. `--check-first` đưa ảnh cần người xem lên đầu task. Cần biến môi trường `CVAT_ACCESS_TOKEN` do người dùng tự gán | 1 |
| `01c_prelabel_gloves.py` | Gán trước găng tay bằng YOLOE (tham số trong `configs/prelabel.yaml`), lưu CSV; `--upload` thêm hộp (nguồn `auto`) vào task CVAT để người duyệt | 1 |
| `01d_cvat_apply_review.py` | Áp kết quả duyệt tự động (`chv_review_boxes.csv`, `chv_review_images.csv`) lên CVAT: xóa hộp găng sai còn nguyên, gắn tag `check` cho ảnh cần người xem | 1 |
| `01e_cvat_reorder_task.py` | Tạo lại một task CVAT để ảnh có tag `check` lên đầu, giữ nguyên mọi hộp/tag và nguồn, có sao lưu và đối chiếu | 1 |
| `02_check_data.py` | Tìm nhãn lỗi, ảnh trùng | 1 |
| `03_split_data.py` | Chia train/val/test theo nhóm ảnh | 1 |
| `04_train.py` | Huấn luyện YOLO11s | 2 |
| `05_run_video.py` | Chạy một video qua toàn bộ hệ thống | 3 |
| `06_evaluate.py` | Tính độ đo, so sánh cấu hình A-E | 5 |

Các file sẽ được viết dần khi làm tới bước tương ứng.
