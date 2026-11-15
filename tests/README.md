# tests — Kiểm thử tự động

Các bài kiểm tra cho code trong `src/ppe`, ví dụ: thiếu mũ liên tục thì chỉ được tạo đúng một cảnh báo. Chạy bằng `pytest` (từ thư mục gốc: `python -m pytest tests -q`).

- `conftest.py`: thêm `src/` vào đường dẫn; cấu hình thử `test_cfg`, `temporal_params`. Các giá trị này chỉ để kiểm tra logic, không phải tham số của hệ thống.
- `test_association_compliance.py`: gán PPE theo vùng, tranh chấp, ba trạng thái, găng xét từng tay.
- `test_temporal_events.py`: xác nhận thiếu/khắc phục theo thời gian, một sự kiện cho một người, chờ quan sát, đóng khi hết phiên.
- `test_draw_evidence.py`: bước A, vẽ vùng ảnh cắt nét đứt "(PL)" khi PPE Có do bộ phân loại mà không có hộp detector; vẽ không đổi kết quả.
- `test_torso_pose.py`: bước B lần 1 (đã tắt), vùng thân theo khung xương cho áo; bật lại bằng tham số `association.torso_pose_b1`; cấu hình hiện tại tắt B1.
- `test_torso_strict.py`: bước B2 (`association.torso_strict`, tham số thử, chưa hiệu chuẩn): cổng G1-G5, vùng R không rộng hơn vùng cũ theo ngang, pose bất thường và thiếu kích thước khung thì như bản 4, chỉ áo, B1 và B2 không bật cùng lúc, cảnh ngẫu nhiên không chạm mép dưới giống bản 4; hàm chia val theo nhóm `unit_folds` của 05a (V4).
