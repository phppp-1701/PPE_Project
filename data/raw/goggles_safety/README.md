# data/raw/goggles_safety — Safety, Roboflow Universe

CHỈ ĐỌC, không sửa file trong thư mục này. Dùng cho B1 (bộ phân loại kính bản 6, kế hoạch
`docs/experiments/2026-11-25_close_range_fixes.md`), chỉ vào **train** của bộ phân loại ảnh cắt mắt.

| Mục | Giá trị |
|---|---|
| Nguồn gốc | https://universe.roboflow.com/new-workspace-wvyfr/safety-yp34e |
| Bản xuất | fork sang workspace `hongs-workspace-jyvld` (`safety-yp34e-yavi4`, v1), xuất YOLOv8 ngày 25/11/2026, "No image augmentation techniques were applied" |
| Tải | người dùng tải 25/11/2026; zip `Safety.v1-2.yolov8.zip`, 4,169,738 byte, sha256 `19b53d7ef19ed816b5a76a189b6154ec5070ce45dea573b9c8eebdb6efc2ba05` |
| Giấy phép | **CC BY 4.0** (theo `data.yaml`) |
| Ghi nguồn | "Safety, Roboflow Universe, CC BY 4.0" |
| Lớp | Hand Protection, Head Protection, Reflective Clothing, Respiratory Protection, Safety Glasses, Safety Shoes |
| Số ảnh | 31 (train 21, valid 6, test 4) |
| Dùng | lớp `Safety Glasses` (29 hộp): có kính màu, nhưng lẫn kính thường -> người dùng kiểm từng hộp |
