# tests — Kiểm thử tự động

Các bài kiểm tra cho code trong `src/ppe`, ví dụ: thiếu mũ liên tục thì chỉ được tạo đúng một cảnh báo. Chạy bằng `pytest` (từ thư mục gốc: `python -m pytest tests -q`).

- `conftest.py`: thêm `src/` vào đường dẫn; cấu hình thử `test_cfg`, `temporal_params`. Các giá trị này chỉ để kiểm tra logic, không phải tham số của hệ thống.
- `test_association_compliance.py`: gán PPE theo vùng, tranh chấp, ba trạng thái, găng xét từng tay.
- `test_temporal_events.py`: xác nhận thiếu/khắc phục theo thời gian, một sự kiện cho một người, chờ quan sát, đóng khi hết phiên.
