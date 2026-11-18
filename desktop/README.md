# desktop — Ứng dụng desktop Windows PPE Monitor

Thư mục vỏ ứng dụng desktop Windows 10/11 (64-bit) cho hệ thống giám sát trang bị bảo hộ lao động 6 lớp (`docs/desktop_app_plan.md`). Ứng dụng dùng `pywebview` (Microsoft Edge WebView2) nhúng giao diện `dashboard/` và chạy `backend.app` (`uvicorn`) ở luồng nền trên `127.0.0.1:<cổng tự chọn>`, tái sử dụng nguyên vẹn chuỗi nhận diện `src/ppe/`.

## Cấu trúc thư mục

| File / Thư mục | Vai trò |
|---|---|
| `main.py` | Điểm vào ứng dụng: khóa 1 phiên bản chạy (`app.lock`), tạo màn hình chờ, kiểm tra môi trường, mở `uvicorn` nền ở cổng tự chọn, cầu nối hộp thoại file Windows (`js_api`), đóng sạch khi thoát |
| `paths.py` | Quy đổi đường dẫn khi chạy từ mã nguồn hoặc từ bộ cài PyInstaller (`sys._MEIPASS` / `onedir`); chuyển dữ liệu người dùng sang `%LOCALAPPDATA%\PPEMonitor\` mà không ảnh hưởng bản web / `pytest` |
| `ppe_monitor.spec` | Cấu hình đóng gói PyInstaller chế độ thư mục (`onedir`) |
| `assets/` | Biểu tượng đa kích thước `icon.ico`, `logo.png` và màn hình chờ `splash.html` |
| `CHANGELOG.md` | Nhật ký thay đổi theo từng mốc và phiên bản |

## Chạy từ mã nguồn (Windows)

```powershell
.\.venv\Scripts\activate
python -m desktop.main
```

Các tùy chọn kiểm thử nhanh:
- `python -m desktop.main --check-only`: kiểm tra đường dẫn, khóa phiên bản chạy, phục hồi phiên treo và mở thử máy chủ nội bộ (không mở cửa sổ GUI).
- `python -m desktop.main --auto-close-ms 1500`: mở cửa sổ `pywebview` thật, nạp màn hình chờ và dashboard rồi tự đóng sạch sau 1,5 giây.

## Đóng gói bằng PyInstaller

1. **Đóng gói thử vỏ ứng dụng rỗng (M1 — kiểm tra nhanh không kèm PyTorch / trọng số):**
   ```powershell
   $env:PPE_EMPTY_BUILD = "1"
   .\.venv\Scripts\pyinstaller.exe --noconfirm --clean desktop\ppe_monitor.spec
   Remove-Item Env:\PPE_EMPTY_BUILD
   .\dist\PPEMonitor\PPEMonitor.exe
   ```

2. **Đóng gói bản đầy đủ kèm mô hình và trọng số (M6):**
   Giải nén gói trọng số `.pt` vào thư mục gốc repo (khớp `configs/pipeline.yaml`), sau đó chạy:
   ```powershell
   .\.venv\Scripts\pyinstaller.exe --noconfirm --clean desktop\ppe_monitor.spec
   .\dist\PPEMonitor\PPEMonitor.exe
   ```

## Lưu trữ dữ liệu người dùng

Khi chạy chế độ desktop, toàn bộ dữ liệu người dùng được tách khỏi thư mục cài đặt và lưu tại `%LOCALAPPDATA%\PPEMonitor\`:
- `ppe.db`: cơ sở dữ liệu SQLite
- `evidence/`: ảnh minh chứng theo từng phiên
- `settings.yaml`: cài đặt riêng của người dùng (ghi đè hợp lệ lên `configs/desktop.yaml`)
- `logs/ppe_monitor.log`: nhật ký xoay vòng (giữ tối đa 7 file)
- `exports/`: thư mục mặc định khi xuất CSV / ZIP và gói chẩn đoán lỗi

