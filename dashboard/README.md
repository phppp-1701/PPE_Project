# dashboard — Trang web xem cảnh báo

HTML/CSS/JS (`index.html`, không cần build), backend phục vụ ở `http://127.0.0.1:8000`. Làm ở bước 4 của kế hoạch.

- **Camera trực tiếp**: nút Bắt đầu/Dừng, hình webcam đã nhận diện (MJPEG từ `/api/live/stream`), FPS xử lý / FPS camera,
  số người, PPE đang kiểm, phiên bản chính sách. Trạng thái hỏi lại mỗi giây.
- **Quy định PPE bắt buộc**: chọn nguồn (mặc định nguồn webcam `cam0`), công tắc đọc chính sách hiện tại của nguồn;
  Lưu tạo phiên bản mới, áp dụng ngay nếu nguồn đang chạy camera.
- Thống kê vi phạm theo PPE, danh sách cảnh báo (tự làm mới 3 giây), chi tiết sự kiện với ảnh minh chứng theo mốc
  thời gian, phản hồi của giám sát viên. Danh sách xếp theo giờ hệ thống lúc tạo sự kiện (mới nhất trước); cột Thời điểm
  ghi giờ thật và giây trong phiên. Lọc theo phiên ("Phiên camera gần nhất" tự chọn khi bấm Bắt đầu, hoặc "Mọi phiên"),
  nguồn, trạng thái, PPE.

Cách chạy: xem `backend/README.md`.
