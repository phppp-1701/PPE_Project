# backend — API và cơ sở dữ liệu

FastAPI nhận cảnh báo từ chuỗi xử lý, lưu vào SQLite và cung cấp dữ liệu cho ứng dụng Desktop / Dashboard.

| File | Dùng để |
|---|---|
| `app.py` | Các API: sự kiện (`/api/events`), phiên (`/api/sessions`), ảnh minh chứng, thống kê (`/api/stats`), nguồn và chính sách PPE theo nguồn, phản hồi giám sát viên, điều khiển camera & tệp video (`/api/live/*`), danh sách webcam (`/api/cameras`), cài đặt người dùng (`/api/settings`), thông tin hệ thống/mô hình (`/api/system`), xuất dữ liệu (`/api/export/events.csv`, `/api/export/events.zip`), kiểm tra sẵn sàng và gọi cửa sổ desktop (`/api/health`, `/api/desktop/focus`) |
| `db.py` | Tạo bảng SQLite, tạo sẵn các nguồn mặc định, phục hồi sự kiện/phiên bị ngắt đột ngột (`recover_crashed_sessions` → `app_crash_recovered`); đọc đường dẫn qua `desktop/paths.py` |
| `live.py` | Điều khiển luồng trực tiếp từ **Webcam** (2 luồng, luôn lấy khung mới nhất) hoặc **Tệp Video** (đọc tuần tự từng khung, thời gian `t = frame_idx / fps`, hỗ trợ `realtime` / `fast`, `pause` / `resume`), trích xuất trạng thái chi tiết từng người trong khung (`persons_detail`), vẽ khung bằng hàm vẽ của `scripts/05_run_video.py`, phát ảnh MJPEG |
| `video_file.py` | Kiểm tra và mở tệp video (`.mp4`, `.avi`, `.mov`, `.mkv`), đọc thông số FPS / tổng số khung / thời lượng và chuẩn hóa `source_id` theo tên tệp |
| `import_events.py` | Nạp `events.jsonl` của các video đã chạy vào database |

## Chạy ứng dụng Desktop hoặc Web Server

- **Chạy ứng dụng Desktop toàn màn hình**: chạy `run_app.bat` hoặc `.venv\Scripts\python.exe desktop/main.py`.
- **Chạy riêng Backend Web Server**: chạy `run_web.bat` hoặc:
  ```
  .venv\Scripts\activate
  python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --timeout-graceful-shutdown 3
  ```

## Các API chính

| API | Việc |
|---|---|
| `POST /api/live/start` | Mở phiên mới từ webcam (`{source: "camera", source_id: "webcam{n}"}`) hoặc camera IP Fofu (`{source: "camera", source_id: "cam0"}` qua bridge MJPEG) hoặc tệp video (`{source: "file", path, mode: "realtime" \| "fast"}`). Chạy được **nhiều camera đồng thời** — mỗi nguồn một phiên độc lập; vượt `max_parallel` (configs/live.yaml) sẽ bị từ chối 409 |
| `POST /api/live/pause`, `POST /api/live/resume` | Tạm dừng / tiếp tục khi đang phát tệp video (`?source_id=...` khi có nhiều phiên tệp) |
| `POST /api/live/stop` | Dừng phiên: `?source_id=...` dừng một nguồn, không truyền = dừng tất cả. Đóng sự kiện đang mở với lý do `session_ended_unverified`, giải phóng camera/tệp |
| `GET /api/live/status` | Trạng thái một nguồn (`?source_id=...`), hoặc nguồn mặc định/đang chạy nếu không truyền: FPS, tiến độ video (`frame`, `total_frames`, `position_s`, `duration_s`), danh sách trạng thái từng người trong khung (`persons_detail`) |
| `GET /api/live/statuses` | Trạng thái của **tất cả** nguồn đang theo dõi trong một request (dashboard đa camera poll mỗi giây) |
| `GET /api/live/stream` | Luồng MJPEG của một nguồn: `?source_id=...` (gắn trực tiếp vào `<img src>` của từng tile) |
| `GET /api/cameras` | Danh mục camera chọn được theo dõi: `catalog` (cam0 Fofu + webcam{n} + urlcam{n} đã thêm, cờ `in_use`, tên theo database), webcam quét được, `discovered` (camera LAN tự quảng cáo), `max_parallel`, các nguồn đang chạy |
| `POST /api/cameras/url` | Thêm camera ngoài bằng URL stream (`{name, url}` — iPhone app DroidCam/iVCam, laptop khác, camera IP) → lưu vào bảng sources với `rtsp_url` |
| `GET /api/cameras/discovered` | Camera trong mạng LAN tự quảng cáo qua UDP trong 12 giây gần nhất (laptop_cam_server) |
| `PUT /api/sources/{source_id}/name` | Đặt tên khu vực cho camera (`{name}`) — tên hiện trong tile, feed sự kiện và bảng thống kê theo nguồn |
| `GET /api/settings`, `PUT /api/settings` | Đọc / ghi cài đặt người dùng (`%LOCALAPPDATA%\PPEMonitor\settings.yaml`) |
| `GET /api/system` | Thông tin phiên bản, GPU/CPU, dung lượng ổ đĩa, mã SHA-256 trọng số và ngưỡng nhận diện (chỉ đọc) |
| `GET /api/export/events.csv`, `GET /api/export/events.zip` | Xuất sự kiện theo bộ lọc ra CSV (UTF-8 có BOM cho Excel) hoặc gói ZIP kèm ảnh minh chứng |
