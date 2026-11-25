# data/raw/goggles_ppes — PPEs, Roboflow Universe

CHỈ ĐỌC, không sửa file trong thư mục này. Dùng cho B1 (bộ phân loại kính bản 6, kế hoạch
`docs/experiments/2026-11-25_close_range_fixes.md`), chỉ vào **train** của bộ phân loại ảnh cắt mắt.

| Mục | Giá trị |
|---|---|
| Nguồn gốc | https://universe.roboflow.com/datatraining-w81fe/ppes-kaxsi-hsnvi |
| Bản xuất | fork sang workspace `hongs-workspace-jyvld` (`ppes-kaxsi-hsnvi-pfnsh`, v1), xuất YOLOv8 ngày 25/11/2026, "No image augmentation techniques were applied" |
| Tải | người dùng tải 25/11/2026; zip `PPEs.v1-3.yolov8.zip`, 1,436,901,530 byte, sha256 `5654b39ffea9b5aed32adc253f4895b3ec60811a9428151e907f58ed166cc28d` |
| Giấy phép | **CC BY 4.0** (theo `data.yaml`) |
| Ghi nguồn | "PPEs, Roboflow Universe, CC BY 4.0" |
| Lớp | goggles, no_goggles, no_shoes, shoes |
| Số ảnh | 5.429 (train 4.429, valid 1.000) |
| Dùng | lớp `goggles` (3.346 hộp, 3.043 ảnh): camera phòng thí nghiệm, vài người lặp lại, không đội mũ, nhiều ảnh gần trùng |
