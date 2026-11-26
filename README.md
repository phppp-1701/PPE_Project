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

Demo camera trực tiếp (webcam laptop, dashboard, bật tắt PPE bắt buộc): xem `backend/README.md`.

## Trạng thái

- [x] Bước 0: cài môi trường (Python, PyTorch GPU, Ultralytics)
- [x] Bước 1: chuẩn bị dữ liệu ảnh (26/10 - 08/11)
- [x] Bước 2: huấn luyện YOLO11s (02/11 - 12/11) — chọn r2 (`imgsz` 960), xem `docs/experiments/2026-11-03_yolo11s_r2.md`
- [x] Bước 3: chuỗi xử lý video — detector c6_ft + zoom, ByteTrack, pose, bộ phân loại bộ phận, gán PPE, ba trạng thái,
  cửa sổ thời gian, sự kiện (`configs/pipeline.yaml`)
- [x] Bước 4: API (FastAPI, SQLite, WebSocket `/ws`) và dashboard; camera trực tiếp
- [x] Bước 5: video kiểm thử và thực nghiệm — đợt sửa tầm gần (`docs/experiments/2026-11-25_close_range_fixes.md`)
- [x] Bước 6 (phần kỹ thuật): đóng băng cấu hình `28ad782`, đánh giá cuối 26/11 (test chạy một lần, Pictor, ablation,
  holdout kiểm tra sau sửa, FR) — `docs/experiments/2026-11-25_final_evaluation_plan.md`, `outputs/results/close_eval/final2/`
- [ ] Bước 6: viết báo cáo (người dùng); gộp `exp/ppe6` vào `main` khi người dùng đồng ý
