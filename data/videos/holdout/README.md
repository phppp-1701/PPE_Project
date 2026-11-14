# holdout: tập video quay gần độc lập (niêm phong)

Người dùng giao 14/11/2026, sau khi 9 video `kiem_thu_gan` (video9-17) đã được xem lỗi bằng mắt và dùng để định hướng
sửa A-D, nên không còn là tập đánh giá khách quan. Tập này thay thế cho đánh giá cuối của các bản sau bản 4.

## Quy tắc

- Chỉ dùng để đo một lần cho bản cuối cùng. Không dùng để chọn ngưỡng, sửa logic, huấn luyện.
- Không chạy hệ thống (bất kỳ phiên bản nào) trên các video này, không xem dự đoán, cho tới khi người dùng cho phép
  đánh giá cuối.
- Nhãn tham chiếu gán trước khi có bất kỳ dự đoán nào của hệ thống (khác với 9 video cũ, nơi người gán đã xem kết quả
  hệ thống trước).
- Niêm phong: `manifest.json` ghi sha256 của video và nhãn; đánh giá cuối phải kiểm manifest trước khi chạy.
- Video không lên Git (dung lượng); thông tin nguồn, giấy phép, sha256 nằm trong `sources.csv` và `manifest.json`.

## Tiêu chí chọn video (ghi trước khi tải, 14/11/2026)

1. Nguồn Pexels (Pexels License: dùng miễn phí, không bắt buộc ghi công, cho phép chỉnh sửa; không bán lại nguyên
   bản). Cảnh quay thật, không phải hoạt họa.
2. **Không cùng buổi quay** với video 3-6 và video9-17: loại các clip cùng tác giả và cùng loạt mã liên tiếp với
   video đã dùng (8486xxx-8488xxx, 8963xxx-8965xxx, 6473xxx-6474xxx, 8987xxx, 9431xxx, 19832xxx, 5423xxx, 5434xxx), và
   các ứng viên cũ đã xem trong lần chọn trước (4206528, 4206544, 5752057, 6474172, 8460395, 8965526).
3. Quay gần: người gần nhất cao từ khoảng một nửa khung trở lên (có thể bị cắt ở ngực hoặc hông), 1-3 người.
4. Ít nhất hai loại PPE trong 6 lớp nhìn đánh giá được (có hoặc không có), ví dụ mũ, áo phản quang, kính bảo hộ, găng.
5. Một cảnh liền, không cắt ghép, dài từ khoảng 4 giây.
6. Chọn để đa dạng tình huống (nhìn thẳng, nghiêng, quay lưng; có và không có PPE; trong nhà và ngoài trời) theo nội
   dung khung hình gốc, **không theo dự đoán của hệ thống**. Không cố chọn trường hợp hệ thống đã biết là sai.
7. 6-9 video. Không đủ video đạt tiêu chí thì dừng và báo cáo, không thay bằng nguồn khác.

## Cách gán nhãn (như 9 video cũ, trước khi có dự đoán)

- Hộp người: `05f_cvat_prefill_xml.py` (yolo11s.pt gốc COCO, không phải mô hình đề tài, không dự đoán PPE).
- Thuộc tính PPE: Claude gán hai lượt độc lập về cách nhìn (lượt A cả khung mỗi 0,5 s; lượt B ảnh cắt sát người mỗi
  0,33 s, lệch thời điểm); chỗ hai lượt khác nhau là `chua_xac_dinh`. Trạng thái `machine_consensus`, chưa người kiểm
  định. Báo cáo tỉ lệ đồng thuận hai lượt như chỉ số chất lượng nhãn.
- Quy tắc nhãn: `docs/video_labeling.md` (6 thuộc tính).

## Kết quả chọn và gán nhãn (14/11/2026)

- 20 ứng viên (5 trang tìm kiếm Pexels), xem khung gốc, chọn 9 (h1-h9). Khi gán nhãn, **h6 (40773981) bị loại**: 5-6
  người qua lại, vi phạm tiêu chí 3; phát hiện khi xem ảnh tờ, trước mọi dự đoán. Không thay video khác. **Tập dùng: 8
  video** h1, h2, h3, h4, h5, h7, h8, h9 (3.855 hộp người-khung, 9 người). Lý do từng ứng viên: `candidates.csv`.
- Chỉ gán người chính (người nền rất nhỏ ở h1, h2 không gán, không chấm). Hộp người từ track 05f, ghép tay theo
  khoảng khung, nới mép ở h3 (hộp COCO cắt mất mũ), lấy hợp ±k khung ở h7, h9 (track 05f chỉ phủ một phần người), kéo
  tới mép khung ở h9 (đầu sát camera); kiểm bằng ảnh.
- Thuộc tính: lượt A (`labels/spec_A.json`), lượt B (`labels/spec_B_attrs.json`), đồng thuận
  (`labels/spec_consensus.json`). Cùng một người gán (Claude) hai lượt với cách nhìn khác nhau; không độc lập hoàn toàn.
- Độ đồng thuận hai lượt (`labels/agreement.json`, mọi khung có hộp): mũ 0,967 (kappa 0,936), áo 0,999 (0,998), găng
  trái 0,858 (0,612), găng phải 0,895 (0,696), kính 0,961 (0,927), ủng 0,998 (0,968).
- Số khung theo trạng thái nhãn đồng thuận (`labels/label_counts.json`): mũ Có 2.394 / Thiếu 853; áo Có 1.565 / Thiếu
  809; găng Có 220 / Thiếu 369; kính Có 590 / Thiếu 781; ủng Thiếu 141, không có Có. Ủng và găng ít mẫu: kết quả hai
  món này trên tập này yếu. Kính Có chỉ có ở một video (h9).
- Hai trường hợp định nghĩa: h5 áo liền thân tối có dải phản quang ở vai, h9 thân chỉ thấy vai: áo để
  `chua_xac_dinh` (phân vân, theo quy tắc chọn `chua_xac_dinh`).
- Trạng thái: **machine_consensus, chưa người kiểm định**. Khác với 9 video cũ: nhãn gán **trước** khi có bất kỳ dự
  đoán nào của hệ thống trên các video này.

## File

| File | Nội dung |
|---|---|
| `sources.csv` | mã, URL, tác giả, giấy phép, ngày tải, độ phân giải, FPS, số khung, sha256, lý do chọn |
| `candidates.csv` | mọi ứng viên đã xem và lý do chọn hoặc loại |
| `h<n>.mp4` | video (không lên Git) |
| `labels/h<n>_machine_cvat.zip` | nhãn tham chiếu (CVAT for video 1.1) |
| `manifest.json` | niêm phong: sha256 video, nhãn, ngày niêm phong |
