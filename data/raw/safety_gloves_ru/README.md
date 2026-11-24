# data/raw/safety_gloves_ru — Safety Gloves (Roboflow Universe Projects), Roboflow Universe

CHỈ ĐỌC, không sửa file trong thư mục này. Dùng cho C8 (kế hoạch `docs/experiments/2026-11-16_c5_detector_plan.md`, mục C8),
chỉ vào train.

| Mục | Giá trị |
|---|---|
| Nguồn gốc | https://universe.roboflow.com/roboflow-universe-projects/safety-gloves-xbnf8 |
| Bản xuất | fork sang workspace `hongs-workspace-jyvld` (`safety-gloves-xbnf8-bhgtr`, v1), xuất YOLOv8 ngày 19/11/2026, không tăng cường khi xuất |
| Tải | người dùng tải 19/11/2026; zip `Safety Gloves.v1-safety-gloves.yolov8.zip`, 481.398.679 byte, sha256 `88631e0602d5ae1ca65522eff64923fa5de038ce291f81a0f88f496196a98f21` |
| Giấy phép | **CC BY 4.0** (theo `data.yaml`) |
| Ghi nguồn | "Safety Gloves, Roboflow Universe Projects, Roboflow Universe, CC BY 4.0" |

## Nội dung

3.373 ảnh: train 2.362, valid 676, test 335. Hai lớp: `0 Gloves` (4.669 hộp), `1 NO-Gloves` (tay trần, 6.135 hộp).

## Kiểm tra (Claude, 19/11/2026, 24 ảnh ngẫu nhiên)

- Phần lớn là khung camera giám sát (CCTV) trong nhà xưởng, góc cao, người nhỏ; nhiều khung liên tiếp của cùng vài camera
  (gần trùng nhau). Vài ảnh không có người (phòng học, phòng tắm).
- Hộp găng và tay trần mỗi tay một hộp, nhiều hộp hơi rộng so với tay.
- Chỉ có nhãn tay: người, mũ, áo không có nhãn → dùng như C6 (người / mũ / áo nhãn máy, kính / ủng che).
