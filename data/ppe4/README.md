# data/ppe4 — Bộ dữ liệu bốn lớp

Do `scripts/01-03` tạo ra, không sửa tay. Lớp: 0 người, 1 mũ bảo hộ, 2 áo phản quang, 3 găng tay bảo hộ.
Cấu trúc sau khi tạo: `images/{train,val,test}`, `labels/{train,val,test}` (định dạng YOLO) và `stats.csv` (nguồn, mã nhóm, tập của từng ảnh).

`converted/` — kết quả trung gian của `01_convert_labels.py`, đầu vào của bước 02-03:

- `converted/<bộ>/labels/*.txt`: nhãn YOLO 4 lớp, mỗi ảnh gốc một file (file rỗng = ảnh không còn hộp nào sau khi lọc).
- `converted/<bộ>/index.csv`: mỗi ảnh một dòng — đường dẫn ảnh gốc trong `data/raw/`, file nhãn mới, tập gốc, số hộp từng lớp, `gloves_labeled` (0 = bộ chưa có nhãn găng tay).
- `converted/<bộ>/cvat/`: gói nạp vào CVAT do `01a_cvat_export.py` tạo — mỗi phần một `<bộ>_partXX_images.zip` (tạo task) và một `<bộ>_partXX_yolo1.1.zip` (Upload annotations, định dạng YOLO 1.1), cùng `parts.csv` ghi ảnh nào thuộc phần nào.
- `converted/<bộ>/cvat/<bộ>_partXX_prelabel_gloves.csv`: hộp găng YOLOE vẽ trước (`01c_prelabel_gloves.py`); `_prelabel_uploaded.csv`: id các hộp đó trên CVAT sau khi tải lên, dùng để biết hộp nào do máy vẽ khi nhập nhãn về.
- `converted/summary.json`: thống kê số ảnh, số hộp từng lớp, hộp bị bỏ theo lớp gốc.

Ảnh chưa được chép ở bước này (SH17 đã 13 GB); bước 03 chép ảnh khi chia tập.
