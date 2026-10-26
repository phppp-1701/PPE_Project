# CLAUDE.md — Luật làm việc với project PPE

## Đọc trước

1. `docs/spec.md`: đặc tả hệ thống, lấy từ Chương 1-3 của báo cáo `D:\KhoaLuan\BaoCao\report_DinhHuy_HoangPhuong_24_10.docx`. Đây là nguồn đúng duy nhất cho thiết kế.
2. README của thư mục sắp làm việc.

## Cách làm việc

- Người dùng là sinh viên, cần hiểu việc đang làm. Trước mỗi bước lớn, giải thích bằng lời dễ hiểu: làm gì, vì sao, tạo ra file nào. Chỉ làm khi người dùng đồng ý.
- Chỉ làm bước được giao trong kế hoạch (`README.md`, mục Trạng thái). Không tạo thư mục mới ngoài cấu trúc hiện có; nếu cần thì hỏi trước.
- Mỗi thư mục mới hoặc script mới phải có giải thích ngắn trong README tương ứng.
- Tên thư mục, file, biến, hàm đều dùng tiếng Anh; nội dung tài liệu và chú thích trong code viết tiếng Việt.
- Ngưỡng và tham số nằm trong `configs/`, không viết cứng trong code. Chưa chọn trên tập xác thực thì để trống, không tự đặt giá trị.
- Không cài package mới khi chưa hỏi; khi cài phải khóa phiên bản.
- Không commit, push, xóa file của người dùng khi chưa được yêu cầu.
- Hết mỗi bước: báo file đã tạo hoặc sửa, lệnh đã chạy thật, kết quả thật, việc còn lại.

## Quyết định đã chốt

- 4 lớp, thứ tự cố định: 0 person, 1 helmet, 2 vest, 3 gloves. Không có ủng.
- YOLO11s (Ultralytics) + ByteTrack (`BYTETracker` của Ultralytics, chỉ track hộp người; không dùng `model.track()`) + gán PPE theo vùng cơ thể. YOLO11n-pose chỉ thêm khi kết quả trên tập xác thực cho thấy cần và người dùng đồng ý.
- Huấn luyện YOLO11s trên Kaggle (ultralytics==8.4.189, cùng phiên bản với máy); laptop chỉ dùng để suy luận, chạy hệ thống và đo hiệu năng.
- Dữ liệu: SH17 (chính), CHV và Construction-PPE (bổ sung), Pictor-PPE chỉ kiểm thử ngoài. Video kiểm thử lấy từ Internet.
- Stack: Python, FastAPI, SQLite, WebSocket, HTML/CSS/JS thuần. Chạy trên laptop i5-11500H, RTX 3050 4 GB, RAM 32 GB.

## Cấm

- Không bịa số liệu (mAP, FPS, Event F1, kết quả test) khi chưa chạy thật; không lấy số của bài báo làm kết quả của đề tài.
- Không dùng Pictor-PPE hay video đánh giá cuối để chọn ngưỡng; không dùng video để huấn luyện.
- Không sửa file trong `data/raw/`.
