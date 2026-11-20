# tests — Kiểm thử tự động

Các bài kiểm tra cho code trong `src/ppe`, ví dụ: thiếu mũ liên tục thì chỉ được tạo đúng một cảnh báo. Chạy bằng `pytest` (từ thư mục gốc: `python -m pytest tests -q`).

- `conftest.py`: thêm `src/` vào đường dẫn; cấu hình thử `test_cfg`, `temporal_params`. Các giá trị này chỉ để kiểm tra logic, không phải tham số của hệ thống.
- `test_association_compliance.py`: gán PPE theo vùng, tranh chấp, ba trạng thái, găng xét từng tay.
- `test_temporal_events.py`: xác nhận thiếu/khắc phục theo thời gian, một sự kiện cho một người, chờ quan sát, đóng khi hết phiên.
- `test_draw_evidence.py`: bước A, vẽ vùng ảnh cắt nét đứt "(PL)" khi PPE Có do bộ phân loại mà không có hộp detector; vẽ không đổi kết quả.
- `test_torso_pose.py`: bước B lần 1 (đã tắt), vùng thân theo khung xương cho áo; bật lại bằng tham số `association.torso_pose_b1`; cấu hình hiện tại tắt B1.
- `test_torso_strict.py`: bước B2 (`association.torso_strict`, tham số thử, chưa hiệu chuẩn): cổng G1-G5, vùng R không rộng hơn vùng cũ theo ngang, pose bất thường và thiếu kích thước khung thì như bản 4, chỉ áo, B1 và B2 không bật cùng lúc, cảnh ngẫu nhiên không chạm mép dưới giống bản 4; hàm chia val theo nhóm `unit_folds` của 05a (V4).
- `test_compliance_cd.py`: bước C, C2 (phủ quyết mũ khi nhìn thẳng, hai mức) và D (nhận quay lưng, giữ theo thời gian); cấu hình hiện tại D, C2 bật.
- `test_boots_veto.py`: bước M1, bộ phân loại chân bác bỏ hộp ủng của detector khi mọi chân có ảnh cắt đều rất chắc không phải ủng; vắng khóa như bản cuối; PPE khác không đổi.
- `test_live.py`: camera trực tiếp với webcam giả, pipeline giả, database tạm (không cần GPU): đổi PPE bắt buộc khi đang chạy đóng sự kiện với lý do `policy_changed` và đếm lại; bắt đầu, dừng, lỗi webcam, lỗi nạp mô hình; luồng MJPEG kết thúc khi dừng; API `/api/live/*`, chính sách áp dụng ngay, ảnh minh chứng không ghi trùng, phiên được ghi.
- `test_pose_regions.py`: bước F (giá trị thử): F1 kính theo mắt, F2 áo theo vai với `edge_frac`, F3 găng dự phòng theo vùng tay (có hộp mới Có, không bao giờ suy Thiếu); vắng khóa như bản chính.

**Chạy tự động trên GitHub:** `.github/workflows/tests.yml` chạy toàn bộ `pytest` (Windows, PyTorch CPU) cho mỗi push và pull request vào `main`, `exp/ppe6`, `feat/desktop`. Test không được cần trọng số, dữ liệu, video (không có trong git); test mới cần dữ liệu thì tự tạo dữ liệu giả trong test.

`test_train_extra.py`: ghép bộ phụ của `scripts/04_train.py` (ảnh cùng tên thay ảnh gốc, tên lặp trong `oversample.txt` tạo nhiều bản), dữ liệu giả trong thư mục tạm.
`test_crop_pass.py`: C9 (`scripts/04m_crop_pass.py`): cách tính tp trùng `match_predictions` của Ultralytics trên dữ liệu ngẫu nhiên, NMS, gộp hộp crop chỉ cho lớp trong `classes`, cắt vùng người và đổi toạ độ; `detector.zoom` của `src/ppe/detector.py` với mô hình giả (đổi toạ độ, nhân `conf_scale`, lọc conf, NMS với PPE cả khung).

`test_c9_decide.py`: C9 (`scripts/04n_c9_decide.py`): đủ ba điều kiện thì đạt; găng tăng dưới 0,03 thì không đạt; tụt đúng 0,02 vẫn đạt, quá 0,02 thì không đạt; mỗi lớp lấy đúng tập con (ủng tập ppe4 không tính).
