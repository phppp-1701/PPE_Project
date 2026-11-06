# data/ppe4 — Bộ dữ liệu bốn lớp

Do `scripts/01-03` tạo ra, không sửa tay. Lớp: 0 người, 1 mũ bảo hộ, 2 áo phản quang, 3 găng tay bảo hộ.
Kết quả của `03_split_data.py`:

- `dataset/`: bộ dùng để huấn luyện (SH17 + CHV + Construction-PPE). `images/{train,val,test}`, `labels/{train,val,test}` (nhãn YOLO đã áp `check/fixes.csv`), `data.yaml` (không ghi `path`, Ultralytics lấy thư mục chứa file làm gốc), `split_summary.json` (cấu hình và bảng số lượng theo tập × bộ × lớp). Tên file có tiền tố bộ, vd `sh17__abc.jpg`. Ảnh chép nguyên bản gốc.
- `pictor_test/`: Pictor-PPE, chỉ kiểm thử ngoài (`images/test`, `labels/test`, `data.yaml`), không có nhãn găng tay.
- `stats.csv`: mỗi ảnh một dòng: bộ, ảnh gốc, tên file mới, `group_id`, tập (`train`/`val`/`test`; Pictor là `external_test`), lý do buộc vào train (`machine_review` / `fixes_train_only`), số hộp add/delete đã áp, số hộp từng lớp.

`r3_extra/` — bộ phụ cho lần huấn luyện r3, do `03b_make_extra_train.py` tạo từ ảnh train: `images/train`, `labels/train` (ảnh cắt `crop__*`, ảnh thu nhỏ `shrink__*`), `oversample.txt`, `summary.json`.

`converted/` — kết quả trung gian của `01_convert_labels.py`, đầu vào của bước 02-03:

- `converted/<bộ>/labels/*.txt`: nhãn YOLO 4 lớp, mỗi ảnh gốc một file (file rỗng = ảnh không còn hộp nào sau khi lọc).
- `converted/<bộ>/index.csv`: mỗi ảnh một dòng — đường dẫn ảnh gốc trong `data/raw/`, file nhãn mới, tập gốc, số hộp từng lớp, `gloves_labeled` (0 = bộ chưa có nhãn găng tay).
- `converted/<bộ>/cvat/`: gói nạp vào CVAT do `01a_cvat_export.py` tạo — mỗi phần một `<bộ>_partXX_images.zip` (tạo task) và một `<bộ>_partXX_yolo1.1.zip` (Upload annotations, định dạng YOLO 1.1), cùng `parts.csv` ghi ảnh nào thuộc phần nào.
- `converted/<bộ>/cvat/<bộ>_partXX_prelabel_gloves.csv`: hộp găng YOLOE vẽ trước (`01c_prelabel_gloves.py`); `_prelabel_uploaded.csv`: id các hộp đó trên CVAT sau khi tải lên, dùng để biết hộp nào do máy vẽ khi nhập nhãn về.
- `converted/chv/cvat/chv_review_boxes.csv`: kết quả duyệt từng hộp găng máy vẽ (glove / not_glove / uncertain, kèm id trên CVAT); `chv_review_images.csv`: từng ảnh là `check` (cần người xem) hay `machine_reviewed` (chỉ máy duyệt, chỉ dùng cho train), kèm lý do.
- Sau khi gán xong trên CVAT, `01f_import_cvat.py` ghi đè `converted/<bộ>/labels` và `index.csv` bằng nhãn có găng tay. `index.csv` thêm cột `review` (`human` = có người xem, dùng được cho val/test; `machine` = chỉ máy duyệt, chỉ cho train) và `reject` (1 = loại, theo `cvat/<bộ>_reject.csv` hoặc tag `reject` trên CVAT). Nhãn cũ chưa có găng ở `labels_before_cvat/`. Hộp person/helmet/vest bị thêm/xóa so với nhãn gốc ghi ở `cvat/<bộ>_cvat_changes.csv`, thống kê ở `cvat/<bộ>_cvat_import.json`. Chạy lại `01_convert_labels.py` thì phải chạy lại `01f`.
- `converted/<bộ>/cvat/<bộ>_reject.csv`: ảnh loại sau khi gán (`unclear` = không phân biệt được găng hay tay trần; `missing_gloves` = găng rõ nhưng thiếu hộp).
- `converted/summary.json`: thống kê số ảnh, số hộp từng lớp, hộp bị bỏ theo lớp gốc.

`check/` — báo cáo của `02_check_data.py` (xem `check/README.md`).

Bước 01-02 chưa chép ảnh; bước 03 chép ảnh khi chia tập (SH17 khoảng 13 GB).
