# Nhật ký phiên bản — PPE Monitor (Windows Desktop)

Mọi thay đổi đáng chú ý của ứng dụng desktop trên nhánh `feat/desktop` được ghi tại đây.

## [Unreleased]

### M2, M3, M4 & M5 — Giao diện Desktop App toàn màn hình, Trung tâm Phát hiện Admin, Nguồn tệp Video & Xuất dữ liệu (2026-11-18)
- **Tái cấu trúc giao diện thành Ứng dụng Desktop toàn màn hình (`dashboard/`)**:
  - Tách `dashboard/index.html` thành kiến trúc module `css/app.css`, `js/api.js`, `js/monitor.js`, `js/events.js`, `js/settings.js`.
  - Áp dụng thiết kế phẳng công nghiệp **Industrial VMS (Carbon & Steel Blue)** toàn màn hình (`100vw x 100vh`), loại bỏ hoàn toàn emoji và màu cầu vồng rời rạc, dùng bộ SVG icon đơn sắc và số liệu thẳng cột (`tabular-nums`).
  - Tổ chức thanh điều hướng chức năng bên trái gồm 6 mục: *Giám sát trực tiếp*, *Nhật ký vi phạm*, *Quy định PPE*, *Thống kê*, *Cài đặt*, *Trợ giúp & Giới thiệu (`F1`)*, kèm Thanh trạng thái cố định ở đáy cửa sổ.
- **Nâng cấp Trung tâm Phát hiện (Detection View) cho Admin**:
  - Thêm hàm `summarize_persons_in_frame` trong `backend/live.py` trả về `persons_detail` trong `/api/live/status`.
  - Hiển thị bảng **Đối tượng trong khung hình** thời gian thực bên phải video với thẻ từng `Người #ID`, ma trận 5 ô trạng thái (`M`, `A`, `G`, `K`, `U`: `Đạt` / `Thiếu` / `Khuất` / `Tắt`) và luồng **Sự kiện vi phạm gần nhất** kèm âm báo tùy chọn.
  - Thêm ngăn chỉnh nhanh **Quy định PPE** và các nút chọn Mẫu nhanh (*Công trường*, *Hàn / mài*, *Kho bãi*) ngay trên thanh công cụ giám sát.
- **Bổ sung nguồn phát Tệp Video tuần tự (`backend/video_file.py`, `backend/live.py`)**:
  - Hỗ trợ chọn và phát tệp `.mp4`, `.avi`, `.mov` theo chế độ *Thời gian thực* (`realtime`) hoặc *Nhanh nhất* (`fast`), đọc tuần tự từng khung hình với `t = frame_idx / fps`, hỗ trợ Tạm dừng / Tiếp tục và thanh tiến độ.
- **Bổ sung các API quản trị và Xuất báo cáo (`backend/app.py`, `desktop/main.py`)**:
  - Thêm `/api/cameras`, `/api/sessions`, `/api/settings`, `/api/settings/cleanup`, `/api/system`, `/api/export/events.csv` (UTF-8 có BOM cho Excel) và `/api/export/events.zip` (CSV kèm ảnh minh chứng).
  - Thêm cầu nối `export_from_url` và `toggle_fullscreen` (`F11`) trong `DesktopBridge` (`desktop/main.py`).

### M0 & M1 — Khung vỏ ứng dụng desktop, đường dẫn dữ liệu và đóng gói thử (2026-11-18)
- Đồng bộ nhánh `feat/desktop` với `origin/exp/ppe6` (CI `pytest`, cấu hình detector `c6_ft`).
- Tạo môi trường `.venv` Python 3.12 (CUDA 12.8) và khóa phiên bản `pywebview==6.2.1`, `pyinstaller==6.22.3`, `filelock==4.2.4` trong `requirements.txt` và `requirements-lock.txt`.
- Thêm `configs/desktop.yaml`: khai báo cổng tự chọn (`0`), đường dẫn dữ liệu, webcam mặc định, thiết bị xử lý (`auto`/`cuda`/`cpu`), chu kỳ giữ dữ liệu và các mẫu PPE nhanh.
- Thêm `desktop/paths.py`: phân tách tài nguyên chỉ đọc (mã nguồn / PyInstaller `onedir`) và thư mục dữ liệu người dùng `%LOCALAPPDATA%\PPEMonitor\`, giữ nguyên đường dẫn `outputs/` khi chạy bản web và `pytest`.
- Thêm `desktop/main.py`, `desktop/assets/splash.html`, `desktop/assets/icon.ico`:
  - Mở cửa sổ `pywebview` (Edge WebView2) kèm màn hình chờ kiểm tra quyền ghi, GPU/CPU, trọng số và máy chủ nội bộ.
  - Chạy `uvicorn` ở luồng nền trên `127.0.0.1` với cổng tự chọn; tự động đóng các phiên/sự kiện treo từ lần tắt đột ngột trước (`app_crash_recovered`).
  - Khóa một phiên bản chạy duy nhất (`app.lock` + gọi cửa sổ đang mở lên trước khi mở lần hai).
  - Xác nhận khi đóng cửa sổ lúc đang giám sát, dừng `LiveCamera` sạch (`session_ended_unverified`), ghi log xoay vòng 7 file và tạo gói chẩn đoán lỗi `.zip`.
- Thêm `desktop/ppe_monitor.spec` (chế độ `onedir`, hỗ trợ đóng gói thử vỏ rỗng `PPE_EMPTY_BUILD=1` và bản đầy đủ) cùng bộ kiểm thử tự động `tests/test_desktop.py`.
