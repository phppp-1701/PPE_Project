# Hệ thống giám sát và cảnh báo thiếu trang bị bảo hộ cá nhân trong xưởng lao động

Khóa luận của nhóm Định Huy, Hoàng Phương.

Hệ thống đọc video từ một camera, phát hiện người và trang bị bảo hộ (mũ bảo hộ, áo phản quang, găng tay bảo hộ) bằng YOLO11s, theo dõi từng người bằng ByteTrack, kết luận mỗi người Có / Thiếu / Chưa xác định từng loại trang bị, xác nhận vi phạm theo thời gian và ghi mỗi đợt vi phạm thành một cảnh báo hiển thị trên dashboard.

## Thư mục

| Thư mục | Dùng để |
|---|---|
| `docs/` | Đặc tả hệ thống (`spec.md`) và nhật ký thực nghiệm |
| `data/` | Dữ liệu ảnh gốc, bộ dữ liệu bốn lớp, video kiểm thử |
| `configs/` | Cấu hình và ngưỡng, sửa ở đây thay vì sửa code |
| `scripts/` | Các lệnh chạy, đánh số theo thứ tự làm |
| `src/ppe/` | Code chính, mỗi file một bước xử lý |
| `backend/` | API và cơ sở dữ liệu cảnh báo |
| `dashboard/` | Trang web xem cảnh báo |
| `outputs/` | Kết quả máy sinh ra |
| `tests/` | Kiểm thử tự động |

Mỗi thư mục có README riêng giải thích chi tiết.

## Quy trình

Bỏ dữ liệu vào `data/` → chỉnh số trong `configs/` → chạy lệnh trong `scripts/` → xem kết quả ở `outputs/` → ghi số liệu vào `docs/experiments/`.

## Trạng thái

- [x] Bước 0: cài môi trường (Python, PyTorch GPU, Ultralytics)
- [ ] Bước 1: chuẩn bị dữ liệu ảnh (26/10 - 08/11)
- [ ] Bước 2: huấn luyện YOLO11s (02/11 - 12/11)
- [ ] Bước 3: chuỗi xử lý video (09/11 - 19/11)
- [ ] Bước 4: API và dashboard (09/11 - 19/11)
- [ ] Bước 5: video kiểm thử và thực nghiệm (16/11 - 24/11)
- [ ] Bước 6: hoàn thiện (24/11 - 30/11)
