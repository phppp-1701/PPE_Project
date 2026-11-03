# scripts — Các lệnh chạy theo thứ tự

| File | Việc | Bước kế hoạch |
|---|---|---|
| `00_check_env.py` | Kiểm tra PyTorch nhận GPU, chạy thử YOLO11s trên ảnh mẫu | 0 |
| `01_convert_labels.py` | Đổi nhãn từng bộ về bốn lớp theo `configs/label_map.yaml`, ghi vào `data/ppe4/converted/` (chưa chép ảnh) | 1 |
| `01a_cvat_export.py` | Đóng gói nhãn 4 lớp của một bộ (vd. CHV) thành các phần định dạng CVAT YOLO 1.1 kèm zip ảnh, để gán bổ sung găng tay | 1 |
| `01b_cvat_upload.py` | Tự tạo task trên app.cvat.ai cho các phần đã đóng gói (tải ảnh, nạp nhãn YOLO 1.1); bỏ qua task đã có. `--check-first` đưa ảnh cần người xem lên đầu task. Cần biến môi trường `CVAT_ACCESS_TOKEN` do người dùng tự gán | 1 |
| `01c_prelabel_gloves.py` | Gán trước găng tay bằng YOLOE (tham số trong `configs/prelabel.yaml`), lưu CSV; `--upload` thêm hộp (nguồn `auto`) vào task CVAT để người duyệt | 1 |
| `01d_cvat_apply_review.py` | Áp kết quả duyệt tự động (`chv_review_boxes.csv`, `chv_review_images.csv`) lên CVAT: xóa hộp găng sai còn nguyên, gắn tag `check` cho ảnh cần người xem | 1 |
| `01e_cvat_reorder_task.py` | Tạo lại một task CVAT để ảnh có tag `check` lên đầu, giữ nguyên mọi hộp/tag và nguồn, có sao lưu và đối chiếu; `--first` chọn thứ tự các ảnh `check` | 1 |
| `01f_import_cvat.py` | Nhập nhãn đã gán trên CVAT (`<bộ>_partXX_done_cvat.zip`) về `data/ppe4/converted/<bộ>/labels`, thêm cột `review` (human/machine) và `reject` vào `index.csv`, liệt kê hộp person/helmet/vest bị thêm/xóa so với nhãn gốc; nhãn cũ sao lưu ở `labels_before_cvat/` | 1 |
| `02_check_data.py` | Kiểm tra dữ liệu, ghi báo cáo vào `data/ppe4/check/`. `--technical`: lỗi kỹ thuật (ảnh hỏng, nhãn sai định dạng, hộp ra ngoài ảnh) và thống kê; `--duplicates`: dấu vân tay dHash, cặp ảnh trùng/gần trùng, `group_id` (`groups.csv`); `--content`: liệt kê hộp đáng ngờ theo quy tắc; `--missing-person`: chạy `yolo11s.pt` tìm người chưa có hộp | 1 |
| `03_split_data.py` | Chia train/val/test 70/15/15 theo `group_id` (tham số trong `configs/split.yaml`): bỏ ảnh reject, áp `fixes.csv`, nhóm có ảnh máy duyệt hoặc hộp máy thêm buộc vào train, các nhóm còn lại cân bằng theo số ảnh từng bộ và số hộp từng lớp. Ghi `data/ppe4/dataset/`, `data/ppe4/pictor_test/`, `data/ppe4/stats.csv`. `--dry-run` chỉ in bảng chia | 1 |
| `04_train.py` | Huấn luyện YOLO11s trên Kaggle theo `configs/train.yaml` (tự tìm `data.yaml` trong `/kaggle/input`), `--resume` chạy tiếp từ `last.pt`; xong thì đánh giá `best.pt` trên val, ghi `run_info.json` (GPU, phiên bản, thời gian, P/R/mAP từng lớp) | 2 |
| `04b_analyze_val.py` | Phân tích lỗi một lần huấn luyện trên val (laptop): tính lại mAP, tỉ lệ tìm được theo lớp × bộ × cỡ hộp, danh sách dự đoán thừa, ô cắt mẫu bỏ sót / dự đoán thừa; tham số ở `configs/train.yaml` mục `analyze`, ghi `outputs/results/<run>_val/` | 2 |
| `05_run_video.py` | Chạy một video qua toàn bộ hệ thống | 3 |
| `06_evaluate.py` | Tính độ đo, so sánh cấu hình A-E | 5 |

Các file sẽ được viết dần khi làm tới bước tương ứng.
