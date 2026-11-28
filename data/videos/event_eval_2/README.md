# event_eval_2: tập video độc lập thứ hai có nhãn sự kiện (round5, RQ3)

Người dùng duyệt 28/11/2026 (round5, `docs/experiments/2026-11-28_round5_plan.md`). Tập `event_eval` đã chạy hai lần nên
không còn độc lập; tập này là tập độc lập duy nhất để kết luận RQ3 cho phiên bản cải tiến của round5.

## Quy tắc (ghi trước khi tải)

- Niêm phong (manifest sha256 video + nhãn, commit) **trước khi chạy bất kỳ cấu hình round5 nào** trên tập này.
- Chạy đúng một lần cho mỗi cấu hình đem so (mốc cuối 4 và bản round5 cuối), sau khi niêm phong. Không chỉnh tham số sau
  khi xem kết quả. Không dùng để train.
- Nhãn: như `event_eval` (hộp người COCO + Claude hai lượt + người dùng kiểm định mẫu); quy tắc chấm như `06e` (chặt và theo
  kiểm định), không đổi.

## Tiêu chí chọn video (ghi trước khi tải, 28/11/2026)

1. Pexels, cảnh thật, một cảnh liền, 8-40 s, 1-4 người lao động đủ lớn để đánh giá ít nhất hai loại PPE.
2. Không cùng buổi quay với mọi video đã dùng hoặc đã xem (video1-27, holdout, event_eval e1-e9 và mọi ứng viên đã xem
   khi chọn event_eval): loại các loạt mã ở `data/videos/event_eval/README.md` và thêm 1081xxxx, 1135xxxx, 1209xxxx,
   1356xxxx, 1392xxxx, 1431xxxx, 1491xxxx, 1639xxxx, 3977xxx, 428xxxx-429xxxx, 744xxxx, 748xxxx, 781xxxx, 1064xxxx,
   493xxxx, 1778xxxx, 1191xxxx, 620xxxx, 2065xxxx, 1222xxxx, 1342xxxx, 8986xxx-8987xxx. Mỗi loạt mã mới tối đa 1 video.
3. **Đa dạng tình huống sự kiện**: có video có người đủ PPE (đo báo sai), có người thiếu, người vào/ra khung, quay lưng, gần
   và xa, trong nhà và ngoài trời; không chọn riêng theo mũ hay ủng.
4. Chọn theo nội dung khung hình gốc (Claude xem 3 khung), không theo dự đoán của hệ thống.
5. 8-12 video; không đủ thì dùng số đạt và báo đúng số lượng (video và sự kiện).

## Kết quả chọn và gán nhãn (28/11/2026)

~50 ứng viên Pexels (12 trang tìm, nhiều mã mới không tải được bản xem thử), xem khung gốc, chọn **11 video** (f1-f11,
`sources.csv`): xưởng hàn, cắt plasma, sửa đường ray, dỡ hàng, công nhân đường phố (bị xe che, đội mũ để dưới đất), thi công
vỉa hè, xưởng mộc (3), thợ đầu sát camera, thợ ống nước. Loại: cột điện (người quá nhỏ), gầm xe, ảnh chụp từ trên cao, tay
không thấy người. f8, f10 chỉ có bản 960 px.
Chỉ gán người chính (người nền nhỏ, người ở mép khung, track trên vật thể không gán; cảnh báo trên họ tính "ngoài nhãn").
Hai lượt do cùng Claude gán (A cả khung, B ảnh cắt), trạng thái gán theo từng người cho cả video (không theo từng khoảng
thời gian), nên đồng thuận mũ/áo 1,0 không nói lên độ khó; găng κ 0,70, kính 0,90. **17 sự kiện chuẩn** trên 11 video.
Niêm phong `manifest.json` trước mọi dự đoán. Chờ người dùng kiểm định (`labels/audit.html`).
