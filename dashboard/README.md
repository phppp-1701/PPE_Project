# dashboard — Giao diện Ứng dụng Giám sát PPE (Industrial VMS UI)

Giao diện ứng dụng toàn màn hình (`100vw x 100vh`) viết bằng HTML/CSS/JS thuần (ES Modules, không cần bước build), chạy chung cho cả cửa sổ ứng dụng Desktop (`pywebview`) và trình duyệt Web tại `/dashboard/index.html`.

## Cấu trúc thư mục

| Đường dẫn | Vai trò |
|---|---|
| `index.html` | Khung vỏ ứng dụng (App Shell): Thanh điều hướng chức năng bên trái (6 mục), thanh tiêu đề, 6 màn hình chức năng, thanh trạng thái cố định dưới đáy và các hộp thoại chi tiết/trợ giúp |
| `css/app.css` | Hệ thống thiết kế phẳng công nghiệp (Industrial Carbon & Steel Blue), đồng nhất 1 chủ đề, không dùng emoji, số liệu thẳng cột (`tabular-nums`) |
| `js/api.js` | Lớp giao tiếp API tập trung, hằng số nghiệp vụ 5 trang bị PPE (`M, A, G, K, U`), nội dung trợ giúp ngữ cảnh và cầu nối `window.pywebview.api` |
| `js/monitor.js` | Logic màn hình **Giám sát trực tiếp**: chuyển đổi Webcam / Tệp Video, điều khiển phát / tạm dừng / dừng, bảng **Đối tượng trong khung hình** (`persons_detail`), luồng cảnh báo tức thời và ngăn chỉnh nhanh PPE |
| `js/events.js` | Logic màn hình **Nhật ký vi phạm**: lọc đa chiều, phân trang 50 dòng, xem ảnh minh chứng theo mốc thời gian (Timeline), đánh giá cảnh báo đúng/sai và **Xuất CSV / ZIP** |
| `js/settings.js` | Điều hướng 6 menu chức năng, phím tắt toàn cục (`Space`, `Esc`, `Ctrl+E`, `F1`, `F11`), màn hình **Quy định PPE** (kèm mẫu nhanh `presets`), **Thống kê**, **Cài đặt hệ thống** và **Trợ giúp** |

## 6 Menu chức năng chính

1. **Giám sát trực tiếp**: Trung tâm phát hiện thời gian thực cho Admin (khung hình 16:9 + bảng kiểm tra trạng thái từng người đang trong khung hình + luồng sự kiện mới nhất).
2. **Nhật ký vi phạm**: Tra cứu lịch sử sự kiện, lọc theo phiên/nguồn/trạng thái/PPE/ngày, duyệt ảnh minh chứng, gửi phản hồi và xuất báo cáo CSV / ZIP.
3. **Quy định PPE**: Thiết lập trang bị bắt buộc theo từng nguồn phát và chọn mẫu nhanh (*Công trường*, *Hàn / mài*, *Kho bãi*).
4. **Thống kê**: 5 thẻ chỉ số KPI, biểu đồ tần suất vi phạm theo 5 trang bị và phân bố theo nguồn.
5. **Cài đặt**: Chọn webcam mặc định, độ phân giải, thiết bị suy luận (`auto` / `cuda` / `cpu`), chu kỳ lưu trữ, âm báo và xem thông số mô hình (chỉ đọc).
6. **Trợ giúp & Giới thiệu (`F1`)**: Hướng dẫn vận hành, phím tắt, câu hỏi thường gặp (FAQ) và giới hạn hệ thống.
