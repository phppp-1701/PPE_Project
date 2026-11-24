# 2026-11-21 — So sánh kết quả hệ thống hiện tại với các nghiên cứu tiền đề

Mục đích: đặt kết quả của detector đang dùng (c6_ft + zoom mọi khung) cạnh số của các bài trong mục "Tổng quan tình hình
nghiên cứu liên quan" của báo cáo (`D:\KhoaLuan\BaoCao\report_DinhHuy_HoangPhuong_04_11.docx`, Bảng 1.1), nói rõ chỗ hơn,
chỗ kém và nguyên nhân. Tài liệu này dùng để viết phần thảo luận ở Chương 4.

**Đọc trước khi dùng số:**

- Số của bài báo là số **của bài báo**, không phải kết quả của đề tài (CLAUDE.md). Mọi bảng dưới đây ghi rõ cột nào là của ai.
- Các bài dùng dữ liệu, cách chia tập, định nghĩa lớp, cỡ ảnh khác nhau, nên **không so trực tiếp được** (bài tổng quan
  `02` tr.16-17 cũng nói vậy). Chỉ so có ý nghĩa khi cùng nguồn ảnh và cùng định nghĩa lớp; các trường hợp này được tách riêng
  ở mục 2.
- Số của đề tài: tập **val** (chưa chạy test; test chỉ chạy một lần cho bản chốt). Nhãn val là nhãn máy, có kiểm định mẫu của
  người. Chưa có số trên Pictor-PPE và video đánh giá cuối.
- Số bài báo lấy từ báo cáo mục 1.4. Các số dùng để so theo lớp đã đối chiếu lại PDF ở `D:\KhoaLuan\Documents\file .pdf`:
  SH17 (file `04`, Bảng IV tr.10), CHV/YOLOv8 (file `14`, bảng theo lớp), CHVG/YOLOX (file `15`, Bảng 4 tr.13 và Bảng 6
  tr.20), YOLOv11 ủng (file `16`, tr.5), Rahman (file `05`, tr.3520). Số các bài còn lại lấy nguyên từ báo cáo, chưa đối chiếu lại.

## 1. Kết quả của đề tài (c6_ft + zoom, val)

Nguồn: `outputs/results/c5_eval/c8lab_c6_vs_crop.json` (04j, KTC 95% bootstrap theo cảnh), `by_source_c6_ft.json` (04o),
`outputs/results/c5_eval/zoom_bench/` (07, video). Mô hình YOLO11s, 9,4 triệu tham số, imgsz 960, 6 lớp.

| Lớp | Tập chấm (số hộp) | mAP50 không zoom | mAP50 có zoom | KTC 95% (có zoom) |
|---|---|---|---|---|
| Người | ppe4 (3.029) | 0,894 | 0,894 | [0,849; 0,925] |
| Mũ bảo hộ | ppe4 (897) | 0,899 | 0,899 | [0,855; 0,934] |
| Áo phản quang | ppe4 (620) | 0,780 | 0,780 | [0,625; 0,896] |
| Găng bảo hộ | ppe4 (864) | 0,674 | 0,708 | [0,609; 0,794] |
| Kính bảo hộ | lớp mới + CHVG (155) | 0,807 | 0,862 | [0,800; 0,915] |
| Ủng / giày bảo hộ | lớp mới (76) | 0,677 | 0,691 | [0,572; 0,818] |

Trung bình 6 lớp (mỗi lớp trên tập con của nó): 0,806. Hệ thống đầy đủ (phát hiện + zoom + ByteTrack + gán theo vùng + trạng
thái + sự kiện) chạy **20,2 khung/giây**, p95 91 ms trên RTX 3050 Laptop 4 GB (video3-6; video đông người nhất 12,6).

**Theo nguồn ảnh** (`scripts/04o_eval_by_source.py`, cùng luật ignore và tập con như 04j, không bootstrap):

| Lớp | SH17 | CHV | Construction-PPE | CHVG (ảnh riêng, không có trong train) |
|---|---|---|---|---|
| Người | 0,879 (2.132) | 0,939 (532) | 0,922 (365) | — |
| Mũ | 0,722 (139) | 0,951 (494) | 0,893 (264) | — |
| Áo | **0,255** (104) | 0,921 (275) | 0,846 (241) | — |
| Găng, không zoom → có zoom | 0,651 → **0,715** (420) | 0,600 → 0,606 (228) | 0,779 → 0,781 (216) | — |
| Kính, không zoom → có zoom | 0,640 → 0,704 (24) | — | — | 0,854 → **0,915** (127) |
| Ủng, không zoom → có zoom | 0,620 → 0,667 (51) | — | 0,798 → 0,759 (25) | — |

(số trong ngoặc là số hộp nhãn; ô < 10 hộp bỏ trống)

## 2. So sánh trên cùng nguồn ảnh

Đây là phần so sánh có ý nghĩa nhất, vì cùng loại ảnh. Vẫn khác: tập ảnh chấm, cách chia, định nghĩa lớp, cỡ mô hình.

### 2a. SH17 — Ahmad và Rahimi (2024) [6]

Bài: YOLOv9-e (58,1 triệu tham số, gấp khoảng 6 lần YOLO11s), 17 lớp, tập kiểm thử 1.620 ảnh **chia ngẫu nhiên** 80/20.
Đề tài: 1.225 ảnh SH17 trong val, chia theo nhóm ảnh gần trùng (dHash), chỉ **233** ảnh trùng với tập kiểm thử của bài
(đếm bằng `data/raw/sh17/val_files.txt`).

| Lớp | Bài [6] (mAP50, %) | Đề tài, ảnh SH17 (có zoom) | Hơn / kém |
|---|---|---|---|
| person | 92,1 | 87,9 | kém 4,2 điểm |
| helmet | 77,0 | 72,2 | kém 4,8 điểm |
| safety-vest | **57,7** | **25,5** | **kém 32,2 điểm** |
| gloves | 66,5 | **71,5** (không zoom 65,1) | **hơn 5,0 điểm** nhờ zoom |
| glasses (mọi loại kính) → kính bảo hộ | 76,4 | 70,4 (24 hộp) | không so được (định nghĩa khác, quá ít hộp) |
| shoes (mọi loại giày) → ủng / giày bảo hộ | 70,8 | 66,7 (51 hộp) | không so được (định nghĩa khác) |

**Lưu ý sửa báo cáo:** báo cáo mục 1.4 ghi "áo phản quang chỉ đạt 29,3%". Đối chiếu Bảng IV (tr.10) bằng cách trích thô từng
hàng và số hộp: hàng có 29,3 là **`foot`** (bàn chân); `safety-vest` có 97 hộp (khớp đúng 97 hộp áo trong
`data/raw/sh17/val_files.txt`, xem `data/raw/sh17/README.md`) và mAP50 **57,7**; `helmet` 154 hộp (khớp 154), mAP50 **77,0**.
Bản trích theo bố cục trang làm lệch hàng, nên dễ đọc nhầm. Cần sửa câu này trong báo cáo.

### 2b. CHV — Barlybayev và cộng sự (2024) [5]

Bài: YOLOv8 n đến x, 6 lớp (người, áo, 4 màu mũ), CHV 1.330 ảnh.

| Lớp | Bài [5] | Đề tài, ảnh CHV | Hơn / kém |
|---|---|---|---|
| Áo phản quang | YOLOv8n 0,841; YOLOv8x 0,888 | **0,921** | hơn 0,03-0,08 |
| Mũ | 4 lớp theo màu, cao nhất mũ trắng 0,967 (YOLOv8x) | 0,951 (một lớp mũ, gộp màu) | không so trực tiếp (bài tách màu) |

### 2c. CHVG — Ferdous và Ahsan (2022) [4]

Bài: YOLOX s đến x, 8 lớp, ảnh 640×640, 3 cách chia. AP kính (safety glass) **74,12-85,00** qua mọi cỡ mô hình và cách chia
(Bảng 4); YOLOv5x trên CHVG 77,8 (Bảng 6). Bài ghi kính có tỉ lệ bỏ sót cao nhất 13,85%.

| Lớp | Bài [4] | Đề tài, ảnh riêng CHVG | Hơn / kém |
|---|---|---|---|
| Kính bảo hộ | 74,12-85,00 (YOLOX), 77,8 (YOLOv5x) | 0,854 không zoom; **0,915** có zoom | hơn bản tốt nhất của bài 6,5 điểm (có zoom) |
| Áo | 88,14-93,55 | (ảnh CHV) 0,921 | tương đương |

Điểm mạnh của phép so này: ảnh riêng của CHVG **không có trong train** của đề tài (CLAUDE.md), nên đây gần với kiểm thử ngoài
nguồn; trong bài [4], ảnh kiểm thử cùng bộ với ảnh train.

### 2d. Ủng bảo hộ — Razan và cộng sự (2026) [9]

Bài: YOLOv11n, Roboflow, lớp `Safety boots` P 0,738, R 0,488, mAP50 0,611 (tr.5). Đề tài: 0,691 có zoom. Số của bài tự mâu
thuẫn (số ảnh 717 và 4.196, mAP50 0,810 và 0,713; xem `2026-11-06_ppe6_data_literature_review.md`), nên **không dùng làm
mốc**; chỉ ghi để thấy ủng là lớp khó ở cả hai nơi.

## 3. So với các bài khác (khác dữ liệu, chỉ đối chiếu định tính)

| Bài | Số của bài | Vì sao không so trực tiếp |
|---|---|---|
| Rahman [7] | mAP50 95,2% (gộp nguồn); găng thấp nhất vì ít mẫu (tr.3520) | 20.001 ảnh, tăng cường lên 50.096 rồi chia 70/20/10; không tách theo video |
| Faradila [10] | mAP50 90%, 5-8 FPS (Raspberry Pi) | chia 96/2/2 **sau khi** tăng cường, tập kiểm thử khoảng 146 ảnh, gần như chắc rò rỉ |
| Naufaldihanif [17] | mAP50 0,939 (YOLOv11n) | 5 lớp, chỉ mũ và áo, không có găng, kính, ủng |
| Lê Võ Thanh Xuân [19] | mAP 0,92-0,96 (YOLOv8 cỡ lớn) | găng và kính là hai lớp khó nhất; mô hình lớn |
| Wang [14] | AP vật nhỏ 61,22 so với vật lớn 91,51; "không găng" 85,36, "không giày" 83,48 | lớp vi phạm, không phải lớp trang bị |
| Al-Azani [13] | 92,36% cùng camera → 66,70% camera mới; cả luồng 8,6 FPS (tuần tự), 28,65 FPS (đa luồng) trên RTX A6000 | chỉ mũ và áo; GPU mạnh hơn nhiều |
| Horesh [16] | triển khai thật: găng không còn ý nghĩa thống kê (p = 0,337) | bộ phân loại vùng tay, môi trường y tế |
| Thoan [18] | mAP 0,705 (YOLOv8, 10 lớp) | 960 ảnh, gộp lớp dùng và không dùng |

## 4. Chỗ đề tài tốt hơn, và vì sao

1. **Kính bảo hộ trên CHVG: 0,915 so với 74-85 của bài gốc [4].**
   - Zoom: cắt vùng người từ ảnh gốc độ phân giải cao rồi dò lại (kính +0,060 trên CHVG). Kính nhỏ, trong suốt; bài [4] chạy
     ở 640×640 nên kính mất chi tiết, đúng như bài tự nhận ("khi nhỏ và mờ thì bị sót", tr.20).
   - Đề tài chạy ở 960 thay vì 640, và YOLO11 mới hơn YOLOX (2021).
   - Gộp thêm kính từ CHV, SH17, Construction-PPE; kính thường giữ làm mẫu âm.
   - Thận trọng: chỉ 127 hộp, nhãn đo là nhãn máy (lớp kính đạt kiểm định của người lần 1, mẫu "máy nói có" chỉ 13 ô).
2. **Găng trên ảnh SH17: 0,715 so với 66,5 của YOLOv9-e [6], với mô hình nhỏ hơn khoảng 6 lần.**
   - Không zoom thì 0,651, thấp hơn bài 1,4 điểm; toàn bộ phần hơn đến từ zoom (+0,064 trên SH17). Ảnh SH17 rất lớn
     (cạnh dài trung vị ảnh val 5.816 px), thu về 960 làm găng chỉ còn vài chục pixel; zoom lấy lại chi tiết từ ảnh gốc.
   - Zoom không giúp ảnh CHV (+0,006) vì ảnh CHV vốn nhỏ: không có thêm chi tiết để lấy. Điều này cho thấy phần tăng là do độ
     phân giải, không phải do may.
   - Thận trọng: định nghĩa găng của đề tài chỉ giữ găng bảo hộ (SH17 gộp mọi loại), và chỉ 233/1.225 ảnh trùng tập kiểm thử
     của bài.
3. **Áo phản quang trên CHV: 0,921 so với 0,841-0,888 [5].** Nhiều dữ liệu áo từ nhiều nguồn (train 4.534 hộp áo), imgsz 960.
4. **Mức hệ thống, không bài nào có:**
   - Theo dõi từng người (ByteTrack), gán PPE theo vùng cơ thể, ba trạng thái Có / Thiếu / Chưa xác định, gom vi phạm thành sự
     kiện. Các bài [4]-[21] đều đánh giá từng ảnh độc lập (báo cáo mục 1.4, "khoảng trống nghiên cứu").
   - Tốc độ đo **cả luồng** (20,2 khung/giây trên GPU laptop 4 GB), không chỉ tốc độ mô hình. Al-Azani [13] cho thấy hai số này
     khác xa nhau (338 FPS mô hình, 8,6 FPS cả luồng).
   - Trạng thái "Chưa xác định" thay cho đoán bừa: trên video chỉnh tham số, găng báo "Có" sai 1 lần, kính 0 lần; ủng báo
     "Thiếu" sai 61 lần trên 832 khung-người có ủng.
5. **Đánh giá chặt hơn:**
   - Chia theo nhóm ảnh gần trùng, lớp mới đánh giá trên cảnh không có ở train. Nhiều bài chia ngẫu nhiên (SH17 [6], Razan [9],
     Wang [14], Isailovic [15], Naufaldihanif [17]), Faradila [10] tăng cường trước khi chia, nên số của các bài dễ cao hơn thực tế.
   - KTC 95% bootstrap theo cảnh, vùng ignore cho ca mơ hồ, tiêu chí chọn bản khóa trước khi train, có kiểm định của người
     trên nhãn máy. Không bài PPE nào trong danh sách báo cáo đồng thuận người gán hoặc khoảng tin cậy
     (`2026-11-06_ppe6_data_literature_review.md`, mục 1c).

## 5. Chỗ đề tài kém hơn, và vì sao

1. **Áo phản quang trên ảnh SH17: 0,255 so với 57,7 của [6] (kém 32 điểm).** Đây là chỗ kém nhất.
   - Phân tích lỗi c6_ft (`2026-11-16_c5_detector_plan.md`, mục C7): recall áo trên SH17 chỉ 0,452, trong khi CHV 0,964,
     Construction-PPE 0,896. Áo SH17 hay nhỏ, ở xa, trong ảnh nhà xưởng đông người; hộp < 16 px có recall 0,088.
   - Áo SH17 trong train ít: 345 hộp trên tổng 4.534 (CHV 982, Construction-PPE cũ và mới 772 + 1.723). Mô hình học "áo" chủ yếu từ
     ảnh công trường, nên kém trên ảnh nhà xưởng. Bài [6] chỉ train trên SH17 nên khớp miền hơn.
   - Ảnh SH17 lớn bị thu về 960; zoom không áp cho áo (chỉ găng, kính, ủng), vì áo nhìn chung là vật to.
   - Trong ba lớp vật lớn (người, mũ, áo), áo là lớp duy nhất chưa qua 0,8 (0,780 trên cả tập ppe4); phần kéo xuống chủ yếu là SH17.
2. **Người và mũ trên ảnh SH17: kém 4-5 điểm** (87,9 so với 92,1; 72,2 so với 77,0).
   - Mô hình nhỏ hơn khoảng 6 lần (9,4 so với 58,1 triệu tham số), chọn vì phải chạy thời gian thực trên laptop 4 GB.
   - Mũ: đề tài chỉ giữ mũ bảo hộ thật (`docs/spec.md` mục dữ liệu); mũ thường, mũ mơ hồ không là dương, nên lớp khó hơn.
     Chỉ 139 hộp mũ SH17 trong val nên số dao động lớn.
   - Chia theo nhóm ảnh (đề tài) khó hơn chia ngẫu nhiên (bài): ảnh cùng buổi chụp không nằm ở cả hai phía.
3. **Ủng thấp (0,691), dưới mốc 0,8.**
   - Định nghĩa chặt hơn mọi bài: chỉ ủng / giày bảo hộ nhìn rõ; giày thể thao, giày thường là mẫu âm
     (`docs/annotation_rules.md`). SH17 `shoes` gộp mọi loại giày, nên 70,8 của [6] là bài toán dễ hơn.
   - Ủng hầu như được tìm đủ (recall tối đa 0,934), nhưng **báo thừa có conf cao** trên giày thường SH17 và bốt cổ ngắn
     (33 báo thừa; ca biên theo định nghĩa). Đây là lỗi phân biệt, không phải lỗi thấy.
   - Ít dữ liệu: 2.528 hộp ủng train, chỉ 76 hộp val, KTC rộng [0,572; 0,818]. Nhãn ủng là nhãn máy: kiểm định lần 1 tầng
     "máy nói có" không đạt (7/44 bất đồng), lần 2 sau khi xem lại chặt thì đạt.
   - Trên video: ủng chỉ nhận đúng "Có" 38% khung-người (318/832), phần lớn còn lại là "Chưa xác định" vì chân nhỏ, bị che
     hoặc ra khỏi khung. Al-Azani [13] (camera giám sát) bỏ hẳn găng và giày khỏi nhãn vì ở khoảng cách camera không nhận ra được (file `07`, tr.4).
4. **Găng thấp (0,708 trên ppe4), dưới mốc 0,8.**
   - 34% hộp găng không có dự đoán nào (chẩn đoán C9); găng nhỏ, mỏng, găng y tế, nilon, găng len dễ lẫn với tay trần.
   - Nhãn găng val là vấn đề riêng: hai lần máy thêm hộp găng đều không đạt kiểm định của người (58% và 41% bất đồng),
     nên val không thêm hộp máy, chỉ thêm vùng ignore. Một số hộp val nằm chỗ không thấy găng. Trần đo được của găng bị
     giới hạn bởi chính nhãn.
   - Nhiều bài ghi găng là lớp khó hoặc kém nhất (Rahman [7], Faradila [10], Lê Võ Thanh Xuân [19]; Razan [9]: găng hay bị nhầm với
     nền; Horesh [16]: găng mất ý nghĩa thống kê khi triển khai thật).
     Mức của đề tài nằm trong khoảng chung: 0,606-0,781 tùy nguồn, so với 66,5 (SH17 [6]).
   - Đã thử C5-C9 (cỡ ảnh 1280, YOLO11m, thêm dữ liệu găng, ảnh cắt người): không bản nào tăng găng có ý nghĩa; chỉ zoom
     (lúc suy luận) tăng được +0,033.
5. **So với các bài báo số rất cao (90-98%: [7], [10], [17], [19]):** số tổng của đề tài thấp hơn rõ. Nguyên nhân chính không
   phải mô hình yếu hơn mà là bài toán khác: các bài đó ít lớp, vật to (mũ, áo), chia ngẫu nhiên hoặc tăng cường trước khi
   chia (rò rỉ), có bài số tự mâu thuẫn. Đề tài có 6 lớp với 3 lớp nhỏ (găng, kính, ủng), chia theo nhóm ảnh, và định nghĩa
   "bảo hộ" chặt.
6. **Chưa có số ngoài miền.** Các bài cho thấy số giảm mạnh khi đổi camera (Al-Azani [13]: −25,66 điểm; SH17 [6] trên
   Pictor 58,9%). Đề tài chưa chạy test, Pictor-PPE và video đánh giá cuối cho bản chốt, nên chưa nói được mức giảm.

## 6. Nguyên nhân gốc, tóm tắt

| Nguyên nhân | Ảnh hưởng | Bằng chứng trong đề tài |
|---|---|---|
| Vật nhỏ trong ảnh lớn bị thu về 960 | găng, kính, ủng, áo SH17 | zoom tăng găng SH17 +0,064, kính CHVG +0,060; không tăng trên CHV (ảnh nhỏ) |
| Lệch miền giữa nguồn (nhà xưởng SH17 và công trường CHV / Construction-PPE) | áo SH17 0,255 so với CHV 0,921 | recall áo SH17 0,452; áo SH17 chỉ 345/4.534 hộp train |
| Định nghĩa "bảo hộ" chặt hơn các bài | ủng, mũ, găng, kính | báo thừa ủng conf cao trên giày thường; mẫu âm kính thường |
| Nhãn máy, kiểm định của người không đạt ở găng | trần đo găng | kiểm định lần 1 và 4 không đạt; val chỉ thêm ignore |
| Ít dữ liệu lớp mới | kính (155 hộp val), ủng (76) | KTC rộng 0,24 điểm cho ủng |
| Mô hình nhỏ vì ràng buộc chạy thời gian thực trên laptop | người, mũ SH17 kém 4-5 điểm | YOLO11m (C7) không tăng: ủng −0,057, kính −0,033 |
| Đánh giá chặt (chia theo nhóm ảnh) | mọi lớp, số thấp hơn chia ngẫu nhiên | chỉ 233/1.225 ảnh SH17 val trùng tập test của bài |

## 7. Cách viết vào báo cáo (đề xuất)

- Không viết "tốt hơn nghiên cứu X" chung chung. Viết theo từng lớp, cùng nguồn ảnh, kèm điều kiện: ví dụ "Trên ảnh riêng
  của CHVG (không dùng để huấn luyện), lớp kính bảo hộ đạt mAP50 0,915 với lượt dò lại trên vùng người, so với 74,1-85,0 mà
  Ferdous và Ahsan [4] báo cáo trên tập kiểm thử chia từ cùng bộ dữ liệu".
- Nói thẳng chỗ kém: áo trên SH17 (0,255 so với 57,7), ủng và găng dưới 0,8, và nêu nguyên nhân ở mục 6.
- Ghi đủ: tập val, nhãn máy có kiểm định mẫu của người, KTC 95%, mô hình nhỏ hơn.
- Sửa số áo SH17 (29,3 → 57,7) ở mục 1.4 như mục 2a.
- Sau khi chạy test một lần cho bản chốt, thay số val bằng số test ở bảng chính, giữ val làm phụ lục.

## Lệnh đã chạy

```
python scripts/04o_eval_by_source.py --split val --run c6_ft=outputs/results/c5_eval/c8lab_c6_ft_val --run c6_ft_zoom=outputs/results/c5_eval/c8lab_c6_ft_crop_val --name by_source_c6_ft
```

Đối chiếu PDF: `pdftotext -raw` cho bảng SH17 (Bảng IV), CHV, CHVG (Bảng 4, 6), YOLOv11 ủng; đếm hộp SH17 bằng
`data/raw/sh17/val_files.txt` (chỉ đọc).
