# data/raw/goggles_sg — Safety Goggles, Roboflow Universe

CHỈ ĐỌC, không sửa file trong thư mục này. Dùng cho B1 (bộ phân loại kính bản 6, kế hoạch
`docs/experiments/2026-11-25_close_range_fixes.md`), chỉ vào **train** của bộ phân loại ảnh cắt mắt.

| Mục | Giá trị |
|---|---|
| Nguồn gốc | https://universe.roboflow.com/database-sjrvw/safety-goggles |
| Bản xuất | fork sang workspace `hongs-workspace-jyvld` (`safety-goggles-kgtuh`, v1), xuất YOLOv8 ngày 25/11/2026, "No image augmentation techniques were applied" |
| Tải | người dùng tải 25/11/2026; zip `Safety Goggles.v1-5.yolov8.zip`, 10,201,478 byte, sha256 `c931330f9ec40131a14cb15c2484dbe4b40c9b9be07edd12be44ab8134bf4e91` |
| Giấy phép | **CC BY 4.0** (theo `data.yaml`) |
| Ghi nguồn | "Safety Goggles, Roboflow Universe, CC BY 4.0" |
| Lớp | eyes_with_goggles, eyes_without_goggles, head, head_with_helmet |
| Số ảnh | 1.288 (train 901, valid 258, test 128) |
| Dùng | lớp `eyes_with_goggles` (405 hộp, 380 ảnh): ảnh đa dạng, người đang đeo, nhiều người không đội mũ, chủ yếu kính trong |
