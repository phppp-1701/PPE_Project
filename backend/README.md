# backend — API và cơ sở dữ liệu

FastAPI nhận cảnh báo từ chuỗi xử lý, lưu vào SQLite (`outputs/ppe.db`) và cung cấp dữ liệu cho dashboard. Làm ở bước 4 của kế hoạch.

| File | Dùng để |
|---|---|
| `app.py` | Các API: sự kiện (`/api/events`), ảnh minh chứng, thống kê, nguồn và chính sách PPE theo nguồn (có phiên bản), phản hồi của giám sát viên, camera trực tiếp (`/api/live/*`), kiểm tra sẵn sàng và gọi cửa sổ desktop (`/api/health`, `/api/desktop/focus`); phục vụ dashboard ở `/dashboard` |
| `db.py` | Tạo bảng SQLite, tạo sẵn các nguồn mặc định, phục hồi sự kiện/phiên bị ngắt đột ngột (`recover_crashed_sessions` → `app_crash_recovered`); đọc đường dẫn qua `desktop/paths.py` (mặc định giữ `outputs/ppe.db` cho bản web) |
| `live.py` | Camera trực tiếp: đọc webcam, chạy chuỗi xử lý (`src/ppe`, cấu hình `configs/pipeline.yaml`), vẽ khung bằng hàm vẽ của `scripts/05_run_video.py`, phát ảnh MJPEG, ghi sự kiện và phiên vào SQLite. Tham số ở `configs/live.yaml` |
| `import_events.py` | Nạp `events.jsonl` của các video đã chạy vào database |

## Chạy demo camera trực tiếp

```
.venv\Scripts\activate
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --timeout-graceful-shutdown 3
```

Mở `http://127.0.0.1:8000` → ô "Camera trực tiếp" → **Bắt đầu** (nạp mô hình mất vài giây). Bật tắt PPE ở thẻ "Quy định PPE
bắt buộc" (nguồn `cam0`) rồi **Lưu**: áp dụng ngay cho camera đang chạy. Bấm **Dừng** trước khi tắt server; nếu quên,
`--timeout-graceful-shutdown 3` để Ctrl+C không bị treo vì trình duyệt còn giữ luồng ảnh.

| API camera | Việc |
|---|---|
| `POST /api/live/start` | Mở phiên mới với chính sách mới nhất của nguồn `cam0` (đang chạy thì 409) |
| `POST /api/live/stop` | Dừng: sự kiện đang mở đóng với lý do `session_ended_unverified`, tắt webcam |
| `GET /api/live/status` | Trạng thái (`idle`, `starting`, `running`, `stopping`, `error`), FPS xử lý, FPS camera, số người, PPE đang kiểm, phiên bản chính sách |
| `GET /api/live/stream` | Khung đã vẽ dạng MJPEG (dùng trong `<img src>`) |
| `GET /api/live/snapshot` | Một ảnh JPEG mới nhất |

Khi đổi chính sách lúc đang chạy (`PUT /api/sources/cam0/policy`): sự kiện đang mở đóng với lý do `policy_changed`,
cửa sổ thời gian đếm lại từ đầu theo danh sách mới, sự kiện mới mang `policy_version` mới.

Giới hạn: một webcam (một nguồn trực tiếp) mỗi lần; video webcam không được lưu, chỉ ảnh minh chứng của sự kiện
(`outputs/evidence/<phiên>/`). Kết quả trên webcam chỉ để trình diễn, không dùng làm số đánh giá và không dùng để train.
