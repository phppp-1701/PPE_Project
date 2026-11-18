# data/raw/gloves_bare_tm — Gloves and bare hands detection (Tejan Mehndiratta), Roboflow Universe

CHỈ ĐỌC, không sửa file trong thư mục này. Tải cho C6 (kế hoạch `docs/experiments/2026-11-16_c5_detector_plan.md`,
mục C6); **chưa quyết định dùng** (xem Kiểm tra).

| Mục | Giá trị |
|---|---|
| Nguồn gốc | https://universe.roboflow.com/tejan-mehndiratta-tcrvm/gloves-and-bare-hands-detection-xbrts |
| Bản xuất | fork sang workspace `hongs-workspace-jyvld` (`gloves-and-bare-hands-detection-xbrts-0fllv`, v1) rồi xuất YOLOv8 ngày 17/11/2026, không tăng cường khi xuất |
| Tải | người dùng tải 17/11/2026; zip `Gloves and bare hands detection.v1-gloves-and-bare-hands-detection--tejan-mehndiratt.yolov8.zip`, 231.858.717 byte, sha256 `23c31b6875b9105e594d47fed565dddbfbfebb14babf96cf4809a0dbc64e7aac` |
| Giấy phép | **CC BY 4.0** (theo `data.yaml`) |
| Ghi nguồn | "Gloves and bare hands detection, Tejan Mehndiratta, Roboflow Universe, CC BY 4.0" |

## Nội dung

868 ảnh: train 712, valid 139, test 17. Tên lớp trong `data.yaml` **không khớp nội dung**: `0 gloverotation`,
`1 paper`, `2 surgical-gloves`. Hộp: lớp 0: 223, lớp 1: 421 (chỉ train), lớp 2: 362.

## Kiểm tra (Claude, 17/11/2026, 24 ảnh ngẫu nhiên)

- Lớp 1 (`paper`) thật ra là **tay trần**; lớp 0 và 2 là **găng** (găng y tế trắng, xanh; găng len đen).
- **Hộp lớp 0 bị lệch hẳn khỏi chiếc găng** (dịch, xoay sai): không dùng được làm nhãn găng.
- Miền khác project: ảnh cận một bàn tay, trong nhà, chụp điện thoại, không phải công nhân ở công trường.
- Đánh giá: ít giá trị cho detector (miền khác, nhãn lệch). Có thể dùng ảnh tay trần (lớp 1) làm **mẫu âm** cho găng
  hoặc cho bộ phân loại tay; người dùng quyết định.
