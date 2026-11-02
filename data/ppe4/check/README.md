# data/ppe4/check — Báo cáo kiểm tra dữ liệu

Do `scripts/02_check_data.py` tạo ra, không sửa tay (trừ `fixes.csv` khi có). Tham số trong `configs/data_check.yaml`.

- `technical_issues.csv`: phần 1 (`--technical`). Mỗi lỗi kỹ thuật một dòng: bộ, ảnh, lỗi (ảnh không đọc được, thiếu file nhãn, sai số cột, mã lớp ngoài 0-3, hộp kích thước 0 hoặc ra ngoài ảnh, dòng trùng, số hộp trong `index.csv` không khớp file nhãn).
- `stats.json`: thống kê theo bộ, chỉ tính ảnh không bị loại: số ảnh theo tập gốc, số hộp và số ảnh có từng lớp, phân bố cỡ hộp (nhỏ < 32², vừa < 96², lớn, theo pixel), cỡ ảnh, số ảnh không có hộp nào.

Phần 2 (`--duplicates`):

- `hashes.csv`: dấu vân tay dHash 64 bit của từng ảnh (sau khi cắt viền tối), làm cache cho lần chạy sau.
- `duplicate_pairs.csv`: mọi cặp ảnh có khoảng cách Hamming ≤ `scan_hamming`.
- `dup_samples_dXX.jpg`: vài cặp mẫu ở mỗi khoảng cách, dùng để chọn ngưỡng.
- `cross_review.csv`, `cross_review_XX.jpg`: cặp khác bộ ở vùng chưa chắc chắn, đánh số để người xem.
- `duplicate_confirmed.csv`: **người ghi** — các cặp trong `cross_review` đã xác nhận là cùng một ảnh.
- `groups.csv`: `group_id` của từng ảnh (ảnh trùng hoặc cùng cảnh chung một nhóm), cỡ nhóm, các bộ có trong nhóm. Bước 03 chia tập theo cột này.

Phần 3 (`--content`, `--missing-person`):

- `content_flags.csv`: hộp đáng ngờ theo quy tắc (`configs/data_check.yaml` mục `content`): `tiny` (quá nhỏ ở cỡ huấn luyện), `dup_box` (hai hộp cùng lớp chồng gần khít), `*_outside_person` (PPE không nằm trong hộp người nào), `gloves_too_big`, `ppe_no_person_in_image`. Chỉ là danh sách để xem, không tự sửa.
- `person_preds.csv`: mọi hộp người mà `yolo11s.pt` (COCO) dự đoán trên ảnh SH17, CHV, Construction-PPE (cache, chạy lại bằng `--rerun`).
- `missing_person.csv`: người máy thấy (conf ≥ `list_conf`) mà chưa có hộp `person` trong nhãn.
- `fixes.csv`: **danh sách sửa nhãn đã duyệt** — mỗi dòng: bộ, ảnh, `action` (`add` / `delete`), lớp, hộp YOLO, lý do, `train_only` (1 = ảnh có hộp máy thêm, chỉ đưa vào tập train), người/ngày quyết định. Nhãn trong `converted/` không bị sửa; bước sau áp dụng file này.
