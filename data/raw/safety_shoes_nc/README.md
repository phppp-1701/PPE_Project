# data/raw/safety_shoes_nc — Safety Shoes Detection (Nedrick Chandra), Roboflow Universe

CHỈ ĐỌC, không sửa file trong thư mục này. Dùng cho C6 (kế hoạch `docs/experiments/2026-11-16_c5_detector_plan.md`,
mục C6), chỉ vào train.

| Mục | Giá trị |
|---|---|
| Nguồn gốc | https://universe.roboflow.com/nedrick-chandra-gpg1l/safety-shoes-detection-5qgkg/dataset/2 (bản v2 của tác giả) |
| Bản xuất | fork sang workspace `aremojidetech` (`safety-shoes-detection-5qgkg-tlulf`, v1) rồi xuất YOLOv8 ngày 17/11/2026, "No image augmentation techniques were applied" khi xuất |
| Tải | người dùng tải 17/11/2026; zip `Safety Shoes Detection.v1-safety-shoes-detection--nedrick-chandra---ban-v2.yolov8.zip`, 253.925.751 byte, sha256 `d54c5d63f472f402de9bb6438b9b29ddd6ef585e931a6d201660d67e7ec016ca` |
| Giấy phép | **CC BY 4.0** (theo `data.yaml`, `README.dataset.txt`) |
| Ghi nguồn | "Safety Shoes Detection, Nedrick Chandra, Roboflow Universe, CC BY 4.0" |

## Nội dung

1.693 ảnh: train 1.375, valid 176, test 142. Năm lớp: `0 Safety-shoes`, `1 d`, `2 not_safety_shoe`, `3 person`,
`4 safety_shoe`. Hộp: `safety_shoe` 3.763 (train 3.135), `Safety-shoes` 85, `not_safety_shoe` 35, `person` 297, `d` 1.

## Kiểm tra (Claude, 17/11/2026, 24 ảnh ngẫu nhiên)

- Miền đúng: công trường, nhà xưởng, công nhân đi ủng / giày bảo hộ; mỗi chiếc một hộp, phần lớn sát.
- **Nhiều ảnh đã bị tăng cường sẵn từ nguồn**: xoay 90°, nhiễu hạt muối tiêu, ảnh trắng đen; một số ảnh có watermark
  dreamstime. Ảnh xoay 90° nên bỏ hoặc dùng có cân nhắc (camera thật không xoay).
- `person` chỉ gán ở một phần ảnh; mũ, áo, găng không có nhãn. Hai lớp `Safety-shoes`, `safety_shoe` cùng nghĩa (gộp);
  `d` bỏ. Không đưa nguyên ảnh vào train (người, mũ, áo thành nền): cắt vùng chân như `safety_shoe_vf`.
