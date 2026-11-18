# Nhật ký phiên bản — PPE Monitor (Windows Desktop)

Mọi thay đổi đáng chú ý của ứng dụng desktop trên nhánh `feat/desktop` được ghi tại đây.

## [Unreleased]

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

