# configs — Cấu hình

- `label_map.yaml`: ánh xạ mã lớp gốc của từng bộ dữ liệu sang bốn lớp, kèm vị trí ảnh/nhãn trong `data/raw/`. Dùng bởi `scripts/01_convert_labels.py`.
- `prelabel.yaml`: mô hình YOLOE, `imgsz`, `conf` dùng để gán trước găng tay cho CHV (chọn trên `chv_part01`), và project CVAT nhận hộp. Dùng bởi `scripts/01c_prelabel_gloves.py`.
- `ppe4.yaml`: khai báo bốn lớp và đường dẫn dữ liệu cho YOLO.
- `train.yaml`: cấu hình huấn luyện (kích thước ảnh, epoch, batch, seed...).
- `pipeline.yaml`: các ngưỡng của chuỗi xử lý. Chưa có giá trị: chọn trên tập xác thực ở bước thực nghiệm rồi mới điền.

Muốn đổi con số thì sửa ở đây, không sửa trong code.
