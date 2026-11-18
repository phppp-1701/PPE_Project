# data/raw/safety_shoe_vf — Safety_shoe / no_safety_shoe (Vertical Farming), Roboflow Universe

CHỈ ĐỌC, không sửa file trong thư mục này. Dùng cho C6 (kế hoạch `docs/experiments/2026-11-16_c5_detector_plan.md`,
mục C6), chỉ vào train.

| Mục | Giá trị |
|---|---|
| Nguồn gốc | https://universe.roboflow.com/vertical-farming-tvyjl/safety_shoe-eimup-mn0qq (người dùng fork về workspace riêng rồi xuất) |
| Bản | v1, xuất định dạng YOLOv8 ngày 17/11/2026, không tăng cường ảnh (theo `README.dataset.txt`) |
| Tải | người dùng tải 17/11/2026; zip `Safety_shoe.v1-safety_shoe---no_safety_shoe--vertical-farming-.yolov8.zip`, 364.410.734 byte, sha256 `c1da6511c84fe9bcb9c2bda95679b452f4af204027728b2614406bd0dfdaa2b5` |
| Giấy phép | **Public Domain** (theo trang và `data.yaml`) |
| Ghi nguồn | "Safety_shoe / no_safety_shoe, Vertical Farming, Roboflow Universe" |

## Nội dung

1.310 ảnh: train 1.003, valid 211, test 96. Hai lớp: `0 no_safety-shoe`, `1 safety-shoe`. Hộp: safety-shoe 2.469
(train 1.829), no_safety-shoe 712. Mỗi chiếc giày một hộp; phần lớn ảnh có 2 hộp.

## Kiểm tra (Claude, 17/11/2026, 24 ảnh ngẫu nhiên)

- Mỗi chiếc giày một hộp, khá sát; `safety-shoe` gồm ủng cao su, giày bảo hộ da; `no_safety-shoe` gồm dép, giày thường.
- **Nhiều ảnh gần trùng nhau** (cùng cảnh, cùng người, khung hình liền nhau; giàn giáo, sân thượng); một số ảnh có nhiễu
  hạt. Cần lọc trùng (pHash) trong bộ và với mọi tập đánh giá trước khi dùng.
- **Chỉ có nhãn giày**: người, mũ, áo, găng trong ảnh không có nhãn. Đưa nguyên ảnh vào train sẽ dạy mô hình rằng người,
  mũ, áo là nền. Cách dùng phải xử lý điểm này (xem kế hoạch).
