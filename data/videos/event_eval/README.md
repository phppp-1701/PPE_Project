# event_eval: tập video độc lập có nhãn sự kiện (RQ3, H3)

Người dùng giao 27/11/2026: kiểm H3 trên video độc lập có nhãn sự kiện do người gán. Không có bộ công khai nào có nhãn
sự kiện vi phạm PPE theo người (đã tìm 27/11/2026), nên tự tạo.

## Quy tắc (ghi trước khi tải)

- Chỉ dùng để đo **một lần** cho cấu hình cuối. Không dùng để chọn ngưỡng, sửa logic, huấn luyện.
- **Không chạy hệ thống** (bất kỳ phiên bản nào) trên các video này, không xem dự đoán, cho tới khi nhãn sự kiện của
  người dùng xong và được niêm phong (`manifest.json`: sha256 video và nhãn).
- Nhãn sự kiện do **người dùng** gán bằng `tools/event_label.html` (Claude không gán, không sửa nhãn). Trạng thái nhãn:
  `human_labeled`.
- Video không lên Git; nguồn, giấy phép, sha256 trong `sources.csv`.

## Tiêu chí chọn video (ghi trước khi tải, 27/11/2026)

1. Nguồn Pexels (Pexels License). Cảnh quay thật, một cảnh liền, không cắt ghép, dài khoảng 8-40 giây.
2. **Không cùng buổi quay** với mọi video đã dùng (video1-27, holdout h1-h9, cam0): loại các loạt mã 8486xxx-8488xxx,
   8963xxx-8965xxx, 6473xxx-6474xxx, 8987xxx, 9431xxx, 19832xxx, 5423xxx, 5434xxx, 3224xxxx, 5100xxx, 846xxxx-847xxxx,
   4077xxxx, 14185xxx, 27917xxx, 30172xxx, 40481xxx, 8818xxx, 6046xxx, 5846xxx, 9373xxx, 7100xxx, 9894xxx, 34289xxx,
   37654xxx, 5972xxx. Mỗi loạt mã mới chọn tối đa 1 video.
3. Có người lao động đủ lớn để người nhìn đánh giá được ít nhất hai loại PPE (mũ, áo phản quang, găng, kính, ủng).
4. Có **ít nhất một trường hợp thiếu PPE** nhìn rõ (để có sự kiện), và ưu tiên video có cả người đủ PPE (để đo cảnh
   báo sai). Đa dạng: trong nhà, ngoài trời, 1-4 người, gần và trung bình.
5. Chọn theo nội dung khung hình gốc (Claude xem 3 khung mỗi video), **không theo dự đoán của hệ thống**.
6. 8-12 video. Không đủ thì dừng và báo cáo.

## Nhãn sự kiện

Mỗi sự kiện: một người, một món PPE bắt buộc, khoảng thời gian [bắt đầu, kết thúc] người đó thiếu món đó liên tục và
nhìn thấy được. Người được đánh dấu bằng một cú bấm vào người ở khung bắt đầu (tọa độ dùng để ghép với người của hệ
thống). PPE bắt buộc của từng video do người dùng chọn khi gán (theo bối cảnh, ví dụ mũ + áo ở công trường).
Quy tắc chi tiết ở đầu trang `tools/event_label.html`.

## Đổi cách gán nhãn (người dùng quyết định 28/11/2026)

Người dùng không gán tay (tốn thời gian), chọn: **nhãn máy hai lượt + người kiểm định mẫu sự kiện** (như holdout), và
thêm số phụ từ nhãn khung có sẵn của holdout. `tools/event_label.html` giữ lại nhưng không dùng.

- Hộp người: `tools/machine_label.py tracks` (yolo11s.pt gốc COCO + ByteTrack của Ultralytics, không phải mô hình đề tài).
- Thuộc tính PPE theo thời gian: Claude gán hai lượt khác cách nhìn (A: cả khung mỗi 0,5 s; B: ảnh cắt từng người mỗi
  1/3 s, lệch 1/6 s). Hai lượt khác nhau → `chua_xac_dinh`. Trạng thái `machine_consensus`.
- Sự kiện chuẩn suy từ nhãn đồng thuận theo spec 7.4 (PPE bắt buộc: cả 5 món như cấu hình mặc định): bắt đầu khi lần
  đầu có món Thiếu; kết thúc khi mọi món là Có, hoặc người rời khung quá 2 s, hoặc hết video (chưa xác minh).
- Người dùng kiểm định mẫu: bấm Đúng/Sai trên từng sự kiện chuẩn (ảnh minh họa). Báo cáo: "nhãn máy hai lượt, có kiểm
  định mẫu của người".

**Loại trước mọi dự đoán (28/11/2026):** e2 (khoảng 6 người nhỏ ở xa trên giàn) và e4 (khoảng 15 người đổ bê tông) vượt
"1-4 người" của tiêu chí 4, như h6 của holdout. **Còn 7 video** (e1, e3, e5, e6, e7, e8, e9), dưới mức 8 của tiêu chí 6:
không còn ứng viên đạt trong hai đợt tìm (khoảng 120 kết quả Pexels), báo người dùng, dùng 7 video và ghi là sai lệch.

## Kiểm định của người dùng (28/11/2026, `labels/audit_result.json`)

Người kiểm định: người dùng (Hoàng Phương), 12 thẻ (10 sự kiện chuẩn, 2 người không có sự kiện): **11 Đúng, 0 Sai, 1 Không
chắc** (e5 P1: thấy áo, mũ; khớp "không sự kiện"). Ghi chú thêm món thiếu nhãn máy bỏ sót: e1 P1, P2 (găng, giày, kính),
e3 P2 (găng), e5 P2 (găng), e9 P1 (găng, kính; ảnh cho thấy găng hàn vàng — giữ nguyên ghi chú người dùng, nêu trong báo cáo).
Trạng thái nhãn: `machine_consensus`, `human_audited` toàn bộ 12 thẻ (kiểm định kết luận, không gán lại).

**Quy tắc chấm (chốt trước khi chạy hệ thống trên e1-e9):** ghép như spec 7.4 (cùng video, IoU người >= 0,5 ở thời điểm
cảnh báo, thời điểm nằm trong khoảng sự kiện, ít nhất một PPE trùng). Báo hai mức: **chặt** (PPE trùng với `missing` của
nhãn máy) và **theo kiểm định** (PPE trùng với `missing` hợp các món người dùng ghi thêm). Cảnh báo trên người không có
trong nhãn (người nền COCO bỏ do track < 1 s hoặc < 10% chiều cao) báo riêng, không tính sai.
