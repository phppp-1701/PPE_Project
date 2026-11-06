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

- 4 lớp, thứ tự cố định: 0 person, 1 helmet, 2 vest, 3 gloves. Không có ủng. Đây là bản chính ở `main`; bản 6 lớp đang thử ở nhánh `exp/ppe6` (xem mục dưới).
- YOLO11s (Ultralytics) + ByteTrack (`BYTETracker` của Ultralytics, chỉ track hộp người; không dùng `model.track()`) + gán PPE theo vùng cơ thể. YOLO11n-pose chỉ thêm khi kết quả trên tập xác thực cho thấy cần và người dùng đồng ý.
- Huấn luyện YOLO11s trên Kaggle (ultralytics==8.4.189, cùng phiên bản với máy); laptop chỉ dùng để suy luận, chạy hệ thống và đo hiệu năng.
- Dữ liệu: SH17 (chính), CHV và Construction-PPE (bổ sung), Pictor-PPE chỉ kiểm thử ngoài. Video kiểm thử lấy từ Internet.
- Stack: Python, FastAPI, SQLite, WebSocket, HTML/CSS/JS thuần. Chạy trên laptop i5-11500H, RTX 3050 4 GB, RAM 32 GB.

## Thử nghiệm 6 lớp (nhánh `exp/ppe6`)

- Nhóm quyết định 06/11/2026: thử thêm 4 goggles, 5 boots, thứ tự 0-3 giữ nguyên. Kế hoạch ở `docs/experiments/2026-11-06_ppe6_plan.md`.
- Bản nào tốt hơn thì lấy. Tiêu chí bằng số phải chốt và ghi vào kế hoạch trước khi train, không chọn sau khi đã thấy kết quả. Người dùng quyết định cuối cùng.
- `goggles` chỉ gồm kính bảo hộ đang đeo, `boots` chỉ gồm ủng hoặc giày bảo hộ nhìn rõ; quy tắc ở `docs/annotation_rules.md`. Kính, giày thường không gán nhãn, dùng làm mẫu âm.
- Dùng lại cách chia train/val/test của `ppe4`. Không sửa `data/ppe4/`, `data/raw/`. Dữ liệu thử nghiệm ở `data/ppe6/`.
- Ủng là lớp mới chính, mốc 0,5 của ủng là điều kiện chọn bản. Kính là thử nghiệm, báo riêng nội bộ và CHVG; không đạt thì pipeline ghi "Chưa xác định" cho kính, không chặn ủng.
- Ảnh riêng của CHVG chưa đưa vào train, chỉ dùng đo lớp kính. Ảnh CHV thuộc `ppe4` train được ghép nhãn kính từ CHVG (bản C1, C2). Bốn lớp cũ quyết định trên val sạch theo cảnh, so với r2. Agent không được đánh dấu hộp nào là người đã duyệt; `val_new`, `test_new` chỉ gồm ảnh đã có người chốt.
- r3 và bản 4 lớp ưu tiên trước: không để thử nghiệm làm chậm bước 3-5 hay chiếm GPU Kaggle của r3.

## Cấm

- Không bịa số liệu (mAP, FPS, Event F1, kết quả test) khi chưa chạy thật; không lấy số của bài báo làm kết quả của đề tài.
- Không dùng Pictor-PPE hay video đánh giá cuối để chọn ngưỡng; không dùng video để huấn luyện.
- Không sửa file trong `data/raw/`.
