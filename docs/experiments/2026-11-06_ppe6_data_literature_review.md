# 2026-11-06 — Tổng quan tài liệu về xử lý dữ liệu cho bộ PPE 6 lớp

Mục đích: tìm cách xử lý dữ liệu có bằng chứng, rồi chọn cách phù hợp với thử nghiệm `exp/ppe6`. Tài liệu này là Bước 0, chưa đổi nhãn hay dữ liệu nào. Toàn bộ là tóm tắt bằng lời của Claude; số trang là **số trang của file PDF**, không phải số trang tạp chí.

## Phạm vi đọc

- 96 file PDF trong `D:\KhoaLuan`: 49 bài gốc ở `Documents/file .pdf`, 20 bản đánh dấu ở `Documents/highlight_tong_quan`, 20 bản sao ở `Research/_backup`, 7 quy định khóa luận ở `Rules/pdf`. Trong repo không có PDF.
- 47/49 bài gốc trích được chữ. Bài 30 (41 trang, chương sách về CNN) và 44 (34 trang, mạch tuần tự) là bản scan; đã xem trang đầu, không liên quan đến dữ liệu PPE nên không đọc tiếp.
- Bảng khó trích đã xem trực tiếp trên trang: bài 04 tr.10, bài 12 tr.6, bài 15 tr.14, bài 16 tr.5.
- Cách đọc: trích văn bản theo trang, lọc từ khóa về dữ liệu, gán nhãn, chia tập, hạn chế, rồi đọc các trang liên quan. **Không đọc từng chữ toàn văn.** "Không nêu" nghĩa là không tìm thấy theo cách đọc này. Bài 09, 10, 13, 19, 20, 43 chỉ quét nhanh.
- Bài không dùng cho dữ liệu: 01, 21, 22, 24, 29, 33, 35, 37-41, 44, 46-49 (bản tin, theo dõi, kiến trúc, độ đo).
- Ngoài PDF, đã kiểm tra repo SH17 trên GitHub và bản ghi CHVG trên figshare. Chưa tải dữ liệu nào.

Ký hiệu bằng chứng: **Đã đo** = bài có số liệu cho chính điều đó. **Chỉ nêu** = bài nói hoặc làm nhưng không so sánh. **Nhận định** = suy luận của Claude.

## 1. Bảng so sánh các bài

### 1a. Bài PPE có kính hoặc giày, ủng

| Bài | Dữ liệu | Định nghĩa nhãn kính, ủng | Quy trình gán | Chia tập, rò rỉ | Mất cân bằng, vật nhỏ, ca mơ hồ | Tiền xử lý, gộp bộ | Chỉ số, ngoài miền | Điểm yếu |
|---|---|---|---|---|---|---|---|---|
| **04 SH17** | 8.099 ảnh Pexels, 75.994 hộp, 17 lớp (tr.1, 5). Khoảng 11.000 ảnh sau lọc trùng, 26% rỗng bị bỏ (tr.5) | `glasses` có thẻ on/off/safety/vision; `shoes` có on/off/safety/other, trong đó safety gồm cả **giày thể thao dày** (tr.7). Thẻ phát hành ở **bản mở rộng** (tr.6) | 4 người: 3 gán, trưởng nhóm sửa, một học viên kiểm cuối (tr.5). Đồng thuận: không nêu | 80/20, tập kiểm thử lấy ngẫu nhiên (tr.9). Có lọc trùng, không nêu cách | Nêu mất cân bằng (tr.8), không xử lý; để cho hướng sau (tr.14) | Giữ độ phân giải gốc (tr.6) | YOLOv9-e: `glasses` mAP50 76,4, `shoes` 70,8, gộp mọi loại (tr.10). Pictor 58,8% (tr.11) | Chia ngẫu nhiên; không có ablation; không có số cho kính, giày bảo hộ riêng |
| **12 head-mounted** | 12.682 ảnh gộp Pictor, Roboflow, ảnh tự thu; 12 loại PPE (tr.2) | **Kính bảo hộ (2.633 ảnh) và kính râm (828 ảnh) là hai lớp riêng** (tr.6). Tiêu chí phân biệt: không nêu | Cắt vùng đầu bằng pose rồi mới gán, để gán nhanh hơn (tr.2). Số người gán: không nêu | Ngẫu nhiên 70/15/15 (tr.5). Chống trùng: không nêu | Nhận xét số ảnh tương quan với kết quả (tr.6-7), không kiểm định | Lật, nhiễu Gauss xác suất 20% (tr.5) | YOLOv5 kính bảo hộ P 0,980, R 0,923; kính râm P 1,000, R 0,711 (tr.6) | Kết quả trên ảnh cắt đầu, camera ở điểm kiểm tra, không so được với khung toàn cảnh. Bài cũng nói PPE ngày càng giống đồ dân dụng (tr.7) |
| **15 CHVG** | 1.699 ảnh, 11.604 hộp, kính chiếm 4,58% (tr.5). Mở rộng từ CHV thêm 369 ảnh và lớp kính, đầu trần (tr.5). Công khai trên figshare (tr.5) | Lớp "safety glass". Tiêu chí tách kính thường: không nêu | Gán tay bằng labelImg (tr.5). Số người: không nêu | 3 tập; có thử 3 tổ hợp dữ liệu (tr.5, 13). Chống trùng: không nêu | Kính có tỉ lệ bỏ sót cao nhất 13,85% (tr.14). Kính trong suốt, nhỏ, mờ dễ sót (tr.20) | Ảnh 640×640 (tr.5) | AP kính 74,12-85,00 qua các tổ hợp và cỡ mô hình (tr.14) | Thử 3 tổ hợp là điểm tốt, nhưng dao động AP kính khoảng 11 điểm cho thấy tập đánh giá không ổn định (Nhận định) |
| **03 GBSG** | 4.000 ảnh, video gần và camera giám sát, 1 khung mỗi 5 s (tr.12-13) | Lớp kính bảo hộ. Bài ghi rõ **kính cận bị nhận nhầm khi nhìn nghiêng** (tr.19) | LabelImg (tr.13). Số người: không nêu | 8:1:1 **sau khi** tăng cường (tr.13) | Vật nhỏ xử lý bằng kiến trúc (tr.8) | Cắt, lật, chỉnh sáng ngoại tuyến (tr.13); mosaic (tr.6) | Ngoài miền: không nêu | Tăng cường trước khi chia: có thể rò rỉ (Nhận định, theo bài 28) |
| **16 YOLOv11** | 15 lớp có ủng và không ủng (tr.3) | `Safety boots`, `No safety boots`. Tiêu chí: không nêu | Không nêu | Ngẫu nhiên 70/20/10 (tr.3) | Tăng cường ưu tiên lớp ít mẫu (tr.3), không so sánh | Lật, xoay, sáng, tỉ lệ (tr.3) | Ủng: P 0,738, R 0,488, mAP50 0,611; không ủng 0,903 (tr.5) | **Số tự mâu thuẫn:** 717 ảnh (tr.1) và 4.196 ảnh (tr.5); mAP50 0,810 trong chữ (tr.1, 5) và 0,713 trong bảng (tr.5). Không nên dùng làm mốc |
| **05 Generic PPE** | 20.001 ảnh: điện thoại, CCTV, Roboflow; có giày và không giày (tr.8) | Tiêu chí giày: không nêu | Grounding DINO vẽ, người sửa; mô hình sơ bộ gán tiếp (tr.8, 10) | 70/20/10 (tr.8). Tách theo video: không nêu | Không cân bằng, "để dữ liệu tự nói" (tr.17) | Gộp 3 nguồn, bỏ ảnh kém, sửa nhãn (tr.10) | Có so theo nguồn (tr.14, 17) | Khung CCTV có thể ở cả train và test (Nhận định) |
| **08 non-PPE** | 3.392 ảnh; 5 lớp "thiếu PPE", có không giày (tr.6, 8) | Gán chỗ thiếu PPE, không gán PPE | LabelImg (tr.8). Số người: không nêu | Ngẫu nhiên 60/20/20 (tr.6) | Tăng cường 102 ảnh thành 816 ảnh, chỉ cho lớp hiếm (tr.7); AP theo cỡ (tr.6) | Thứ tự tăng cường và chia tập không rõ (tr.8) | **Thử 4 bộ ngoài: AP50 giảm 4-7 điểm** (tr.13). Không giày AP50 83,48 (tr.1) | Bộ ngoài chỉ đo được lớp mũ (tr.13) |
| **17 Raspberry Pi** | 1.471 ảnh, 7.310 sau tăng cường; có giày (tr.1) | Không nêu | Roboflow (tr.4). Số người: không nêu | 96/2/2 **sau khi** tăng cường (tr.1, 4) | Găng kém nhất do nhỏ, bị che (tr.7) | Xoay ±15° ngoại tuyến (tr.4) | Không | Rò rỉ gần như chắc chắn, tập kiểm thử rất nhỏ (Nhận định) |

### 1b. Bài PPE khác và bài phương pháp

| Bài | Điều rút ra cho dữ liệu | Trang | Loại |
|---|---|---|---|
| **07 CCTV** | Bỏ găng và giày bảo hộ khỏi nhãn vì **ở khoảng cách camera không nhận ra được** | tr.4 | Chỉ nêu, là quyết định của nhóm gán |
| 07 | 9 người gán theo hướng dẫn viết sẵn, có kiểm tra | tr.5 | Chỉ nêu |
| 07 | Test theo video. Test I cùng góc khác giờ, Test II khác góc và môi trường. Đây là cách chia tốt nhất trong các bài PPE | tr.7, 11 | Đã đo (có 2 tập) |
| 07 | Giữ tỉ lệ giữa lớp nhiều và lớp ít tối đa 3 lần. Val lại là 10% cuối mỗi video, sát train | tr.7 | Chỉ nêu |
| **26 Pictor** | Hai người gán độc lập để giảm thiên lệch | tr.8 | Chỉ nêu |
| 26 | Phê phán chia ngẫu nhiên khung cùng thiết bị, địa điểm, thời điểm: ảnh test quá giống train | tr.15-16 | Lập luận phương pháp |
| **25 Pose** | Mắt định vị kính, mắt cá định vị giày; **chỉ đề xuất, chỉ thử mũ và áo** | tr.5, 15 | Chỉ nêu |
| 25 | Thêm mẫu âm giúp giảm báo nhầm; lỗi do ảnh thấp và vật giống nhau | tr.10, 12 | Chỉ nêu |
| **23 CHV** | Chọn 1.330 ảnh từ khoảng 10.000, người thứ hai kiểm | tr.6 | Chỉ nêu |
| 23 | Thử trên Pictor và GDUT, gán lại nhãn test cho khớp | tr.18 | Đã đo |
| 23, 18 | Áo thun bị nhận là áo phản quang | 23 tr.19; 18 tr.3 | Chỉ nêu |
| **18 CHVG sửa** | Duyệt mẫu thấy ảnh thiếu nhãn; đặt quy tắc vẽ hộp; máy gán rồi người kiểm | tr.5-6 | Chỉ nêu |
| **06** | Ánh xạ 9 lớp về 5 lớp; chia ngẫu nhiên | tr.3 | Chỉ nêu |
| **11 Bệnh viện** | Duy nhất có Kappa, nhưng đo **giữa AI và nhãn**, không giữa người gán. Bối cảnh ảnh hưởng rõ | tr.4, 7 | Đã đo |
| **13** | Ảnh quá sáng hoặc tối làm biên mờ, khó vẽ hộp | tr.4 | Chỉ nêu |
| **02 Tổng quan** | Dữ liệu khác nhau nên không so trực tiếp được số các bài; hay gộp bộ công khai | tr.16-17 | Lập luận |
| 02 | Có thể tổng hợp ảnh bằng dựng hình | tr.9, 23 | Chỉ nêu |
| **34 VOC** | Xóa ảnh trùng và gần trùng | tr.5 | Chỉ nêu |
| 34 | Yêu cầu nhãn nhất quán, chính xác, **đầy đủ**; người tổ chức kiểm từng nhãn | tr.7 | Chỉ nêu |
| 34 | Vật khó nhận được gắn `difficult` và **bỏ khỏi đánh giá** | tr.7 | Lập luận phương pháp |
| **45 COCO** | Nhiều người cùng gán một ảnh để tăng độ phủ; hợp nhiều người tốt hơn một chuyên gia | tr.5 | Đã đo |
| 45 | Vùng đông, không tách được thì gán chung | tr.6 | Chỉ nêu |
| **28 Rò rỉ** | Trùng lặp (L1.4), mẫu không độc lập giữa train và test (L3.2): cùng một cá thể ở hai tập là rò rỉ | tr.2, 5 | Tổng hợp nhiều nghiên cứu |
| **27 Rò rỉ** | Gắn thẻ hợp lệ khi thu dữ liệu, tách phần học và phần dự đoán | tr.5 | Lập luận |
| **32 Tăng cường** | Tăng cường phải giữ đúng nhãn; có thể dùng như lấy mẫu thêm | tr.5, 7 | Tổng hợp |
| **36 YOLOv4** | Mosaic ghép 4 ảnh | tr.6 | Bài đề xuất |
| **31 Transfer** | Lợi ích chuyển giao giảm khi hai miền càng khác | tr.2 | Đã đo, trên ImageNet |
| **42** | Từ chối dự đoán để đổi độ phủ lấy độ tin cậy | tr.1 | Đã đo, trên phân loại |

### 1c. Nhận xét chung

- **Không bài nào định nghĩa rõ cách phân biệt kính, giày bảo hộ với đồ thường.** Bài 04 cho nhãn thẻ nhưng tiêu chí giày lại rộng; bài 12 tách hai lớp nhưng không nêu tiêu chí.
- **Không bài PPE nào báo mức đồng thuận giữa người gán.**
- **Không bài PPE nào có ablation cho cân bằng lớp, mẫu âm, hay vùng ignore.** Các cách này được làm hoặc khuyên, chưa được chứng minh trong miền PPE.
- **Chia ngẫu nhiên là cách phổ biến nhưng yếu** (04, 06, 08, 12, 16, 25, 26). Không nên học theo. Bài 03 và 17 còn tăng cường trước khi chia.
- Số mAP của các bài không so được với nhau, đúng như bài 02 nêu.

## 2. Đối chiếu với dữ liệu của mình

Số đo ngày 06/11/2026 trên `data/ppe6/review/`:

| Điều kiểm tra | Kết quả |
|---|---|
| Cảnh mũ cam | 380 ảnh nằm trong **270 `group_id` khác nhau**, ở cả ba tập (253/74/53 ảnh) |
| Cảnh ủng đỏ | 411 ảnh, **294 `group_id`**, ở cả ba tập (273/74/64 ảnh) |
| `safety` không thuộc cảnh đã gắn thẻ | Kính: train 297, val 57, test 53. Ủng: train 352, val 86, test 144 |
| Hộp ở val và test | Kính 765, ủng 1.893 |

Hệ quả:

- Nhóm dHash ở `ppe4` (Hamming ≤ 8) **không gom được cảnh**. Đây đúng là lỗi L3.2 của bài 28, và cách chia hiện tại không tránh được nó ở lớp mới.
- Val sạch của kính chỉ còn 57 hộp, quá ít để kết luận chắc.
- Các cảnh chưa gắn thẻ vẫn còn: trên bảng ảnh SH17 thấy nhiều buổi chụp cùng người, cùng đôi ủng. `data/raw/sh17/meta-data/*.json` có `photographer_id` và mã ảnh, có thể dùng để gom buổi chụp (Nhận định, chưa thử).
- Bản SH17 đang có không chứa thẻ `safety`. Repo GitHub chỉ có danh sách URL và script, cũng không có file thẻ. Kết quả tìm kiếm cho biết bản ghi Zenodo đang hạn chế, chưa xác minh trực tiếp.

## 3. Bảng quyết định

Chi phí: Thấp là dưới nửa ngày, Vừa là 1-2 ngày, Cao là nhiều ngày công người.

| # | Vấn đề | Cách làm | Nguồn và trang | Mức bằng chứng | Kết luận | Lý do | Tác động dữ liệu | Chi phí |
|---|---|---|---|---|---|---|---|---|
| 1 | Cảnh lặp ở cả ba tập | Gom theo cảnh, không chỉ dHash; dùng thẻ cảnh và `photographer_id`. Đánh giá lớp mới chỉ trên ảnh không cùng cảnh với train | 28 tr.5; 26 tr.15-16; 07 tr.7 | Lập luận mạnh, nhiều nguồn | **Áp dụng** | Cùng một người ở train và val là rò rỉ | Val kính còn tối đa 57 hộp, ủng 86 | Vừa |
| 2 | Giữ so sánh 4 lớp với r2, r3 | **Không chuyển ảnh giữa các tập.** Giữ val `ppe4` cho lớp 0-3; thêm danh sách `val_new` cho lớp 4-5. Bản này thay đề xuất trước đây là đưa cảnh vào train | 28 tr.5; Nhận định | Nhận định có căn cứ | **Áp dụng** | Chuyển ảnh val sang train sẽ làm hỏng phép so lớp 0-3 | Không đổi val, test của `ppe4` | Thấp |
| 3 | Cảnh áp đảo train | Giới hạn số ảnh mỗi cảnh trong phần train hiện có | 07 tr.7 | Chỉ nêu | **Áp dụng**, ngưỡng để ablation | Tránh mô hình học một người | Ước tính kính train khoảng 330, ủng khoảng 400-450 hộp, tùy ngưỡng | Thấp |
| 4 | Hộp `unclear` ở val, test | Coi như `difficult`: không tính đúng, không tính báo nhầm | 34 tr.7 | Lập luận phương pháp | **Áp dụng** | Ultralytics không có sẵn, cần đánh giá riêng cho lớp 4-5 | Không mất ảnh | Vừa |
| 5 | Hộp `unclear` ở train | Giữ quy tắc loại 355 ảnh; so với che xám vùng đó | 34 tr.7; che vùng: không nêu | Nhận định | **Thử nghiệm** | Giữ ảnh có đồ chưa gán dạy sai; loại ảnh mất dữ liệu | 355 ảnh | Thấp |
| 6 | 3.186 hộp giày SH17 `not_safety` lẫn giày tối có thể là bảo hộ | Tách lại thành giày thường và giày mơ hồ, làm val, test trước (965 hộp) | 34 tr.7; 04 tr.7 | Lập luận | **Áp dụng** | Vi phạm yêu cầu nhãn đầy đủ nếu giữ lẫn | Có thể thêm `safety`, thêm ảnh bị che | Vừa |
| 7 | Nguồn đúng cho kính, giày SH17 | Tìm **bản mở rộng có thẻ**: Kaggle, Zenodo, hỏi tác giả | 04 tr.6-7 | Bài nói đã phát hành | **Áp dụng** (chỉ tìm) | Nhãn của 4 người tốt hơn nhãn Claude duyệt nhanh | Có thể thay 1.945 + 4.560 quyết định | Thấp |
| 8 | Kính ít dữ liệu | Thêm **CHVG** (CC BY 4.0, 104 MB) sau khi lọc trùng với val, test, Pictor; duyệt theo định nghĩa của mình | 15 tr.5 | Đã đo trên bộ đó, nhãn chưa kiểm | **Cần duyệt** (đổi nguồn dữ liệu) | Đánh được lớp kính ở ảnh công trường, có phần trùng CHV | Khoảng 530 hộp kính trước khi duyệt | Vừa |
| 9 | Luật "kính tối ôm mặt + mũ = bảo hộ" | Xét theo vật, không theo mũ; kính tối không phân biệt được thì `unclear` | 12 tr.6-7; 03 tr.19 | Chỉ nêu + Nhận định | **Cần duyệt** (đổi định nghĩa) | Mũ là ngữ cảnh, dễ thành đường tắt | Xem mục 5 | Thấp |
| 10 | Kính cận, kính râm | Giữ ảnh, không gán nhãn, làm mẫu âm | 25 tr.10, 12; 03 tr.19; 23 tr.19 | Chỉ nêu | **Áp dụng** | Đã có sẵn, không tốn thêm | 1.363 hộp kính `ordinary` | Thấp |
| 11 | Kính thường là lớp riêng | Thêm lớp phụ, không đưa vào hệ thống | 12 tr.6 | Chỉ nêu | **Thử nghiệm** | Lớp riêng có thể học ranh giới tốt hơn, chưa ai so | Đổi số lớp | Vừa |
| 12 | Duyệt val, test | Người duyệt, ưu tiên hai người độc lập, tính Kappa trên mẫu chung | 26 tr.8; 04 tr.5; 34 tr.7; 45 tr.5 | Chỉ nêu, COCO đã đo | **Áp dụng** | Không bài PPE nào đo đồng thuận, đây là điểm cộng | 340 hộp `safety`, cộng hộp xếp khác | Cao |
| 13 | Cân bằng lớp | Chờ kết quả lấy mẫu thêm găng của r3, rồi mới quyết định | 07 tr.7; 16 tr.3; 08 tr.7; 32 tr.5 | Chỉ nêu, 05 tr.17 không làm | **Thử nghiệm** | Không bài PPE nào có ablation; r3 cho số của chính mình | Chưa có | Thấp |
| 14 | Tăng cường trước khi chia | Không làm | 28 tr.5; 03 tr.13; 17 tr.4 | Lập luận | **Không áp dụng** | Bản sao vào test | Không | Không |
| 15 | Tăng cường khi train | Giữ mặc định đã dùng. Ảnh cắt và thu nhỏ của `03b` chỉ tạo từ train | 32 tr.7; 36 tr.6 | Tổng hợp | **Áp dụng** | Thu nhỏ quá có thể làm mất dấu hiệu kính: cần xem lại | Chưa có | Thấp |
| 16 | Máy gán trước | Dùng mô hình 6 lớp để tìm kính, ủng còn sót, người xác nhận | 05 tr.8, 10; 18 tr.5-6 | Chỉ nêu | **Thử nghiệm**, sau lần train đầu | Dùng cho train; val, test vẫn do người | Có thể thêm hộp | Vừa |
| 17 | Phạm vi camera | Kính, ủng chỉ kết luận khi người đủ lớn; không thì Chưa xác định; báo kết quả theo cỡ | 07 tr.4; 15 tr.20; 42 tr.1 | Chỉ nêu | **Cần duyệt** (đổi phạm vi) | Bài 07 đã bỏ giày vì lý do này; ước tính kính khoảng 15 px ở video2 | Không đổi dữ liệu train | Thấp |
| 18 | Định vị bằng pose | Vùng mắt cho kính, mắt cá cho giày | 25 tr.5; 12 tr.2, 8 | Chỉ nêu, chưa bài nào thử cho kính và giày toàn thân | **Thử nghiệm**, sau train | Có thể giảm nhầm, nhưng pose hiện chỉ dùng cho tay | Không | Vừa |
| 19 | Ngoài miền | Video quay gần, khác camera, chia theo video. Pictor không dùng được cho lớp mới | 07 tr.7, 11; 08 tr.13; 04 tr.11 | Đã đo | **Áp dụng** | Bài 08 giảm 4-7 điểm dù chỉ lớp mũ | Cần video mới có kính, ủng | Cao |
| 20 | Báo cáo | mAP từng lớp, AP theo cỡ, ma trận nhầm kính thường, khoảng tin cậy khi ít mẫu | 08 tr.6; 03 tr.19 | Chỉ nêu + Nhận định | **Áp dụng** | Val kính quá nhỏ cho một con số đơn | Không | Thấp |
| 21 | Ngưỡng `too_small` 24 px | Đo lại trên mẫu; giữ như `difficult` ở val, test | 34 tr.7 | Lập luận | **Áp dụng** | Đang đặt theo cảm quan | Đổi một phần 1.036 hộp | Thấp |
| 22 | CHV thiếu nhãn kính, ủng | Giữ không dùng ở train | 34 tr.7; 18 tr.5 | Lập luận | **Áp dụng** | Nếu CHVG được duyệt thì xét lại phần trùng | Giữ nguyên kế hoạch | Không |
| 23 | Ảnh tổng hợp | Không làm lúc này | 02 tr.9, 23 | Chỉ nêu | **Không áp dụng** | Ngoài khả năng và thời gian | Không | Cao |
| 24 | SMOTE | Không làm | 05 tr.17 | Bài chỉ gợi ý | **Không áp dụng** | Không phù hợp với hộp phát hiện (Nhận định) | Không | Không |

## 4. Danh sách việc

**Làm ngay, không đổi quyết định đã chốt:** 1, 2, 3, 4, 6, 7, 10, 12, 15, 20, 21, 22.

**Cần ablation:**

- Mục 3: ngưỡng ảnh mỗi cảnh.
- Mục 5: loại ảnh hay che vùng.
- Mục 11: có lớp kính thường hay không.
- Mục 13: lấy mẫu thêm lớp mới.
- Mục 16 và 18: sau lần train đầu.
- Khi ablation, chọn trên `val_new`, không dùng test và Pictor.

**Không nên làm:**

- Chia ngẫu nhiên, hoặc coi `group_id` dHash là đã chống rò rỉ.
- Tăng cường trước khi chia.
- Lấy mAP của bài khác làm mốc, nhất là số của bài 16.
- Chuyển ảnh val, test sang train.
- Dùng val có cảnh lặp để chốt tiêu chí.
- Train thẳng `glasses`, `shoes` của SH17 như nhãn bảo hộ.

## 5. Điểm phải dừng để người dùng quyết định

Tài liệu cho thấy nên đổi các điểm sau, nên **dừng trước Bước 2**.

| Điểm | Hiện tại | Đề xuất | Bằng chứng | Tác động dữ liệu |
|---|---|---|---|---|
| Kính tối ôm mặt | Tính `safety` nếu đeo cùng mũ | Không dùng mũ làm tiêu chí. Không phân biệt được với kính râm thì `unclear` | 12 tr.6-7 tách kính râm và kính bảo hộ, PPE giống đồ dân dụng; 03 tr.19; phần mũ là Nhận định | Trên giấy kính 787 xuống khoảng 407 hộp. Nhưng cảnh mũ cam vốn bị giới hạn, nên thực tế mất khoảng 30 ảnh. Hộp kính tối ngoài cảnh này chưa đếm được, vì chỉ mẻ mẫu có ghi chú |
| Nguồn dữ liệu | Không có CHVG | Thêm CHVG sau khi lọc trùng và duyệt | 15 tr.5, 14 | Có thể thêm tới khoảng 530 hộp kính trước khi lọc và duyệt; con số thật sẽ thấp hơn |
| Phạm vi | Lớp mới đánh giá như lớp cũ | Chỉ kết luận khi người đủ lớn; góc cao để Chưa xác định | 07 tr.4; 15 tr.20 | Không đổi dữ liệu, đổi cách báo cáo và pipeline |
| Cách xử lý cảnh | Đề xuất cũ: đưa hai cảnh vào train | Không chuyển ảnh; dùng `val_new` | 28 tr.5 | Giữ nguyên `ppe4` |

Định nghĩa giày giữ nguyên: bài 04 tính cả giày thể thao dày là bảo hộ, nhưng cách đó không kiểm tra được việc tuân thủ.

## 6. Lỗ hổng chưa trả lời được

| Câu hỏi | Tình trạng | Nên tìm |
|---|---|---|
| Có nhìn ra giày mũi thép không? | Không bài nào đo | Tiêu chuẩn giày bảo hộ (ISO 20345), nghiên cứu nhận dạng giày |
| Tiêu chí tách kính bảo hộ và kính thường | Không bài nào nêu | Bài 12 và nghiên cứu trước của cùng nhóm (tài liệu số 7 trong bài 12); tiêu chuẩn ANSI Z87.1 |
| Train với bộ thiếu nhãn từng phần | Không có trong PDF | Từ khóa: partial annotation, missing annotation, multi-dataset detection |
| Vùng ignore với YOLO | Không có; COCO, VOC chỉ nói ở đánh giá | Tài liệu Ultralytics, các bài về soft sampling |
| Lỗi nhãn trong tập đánh giá | Không có | Từ khóa: confident learning, label errors in test sets |
| Kích thước tối thiểu để nhận kính | Không có | Nghiên cứu vật nhỏ, ví dụ Tiny object detection |
| Video công khai có kính, ủng | Chưa thấy | Tìm tiếp, kể cả tự quay |
| Giấy phép khi gộp AGPL, CC BY-NC-SA, CC BY | Không có | Hỏi giáo viên hướng dẫn |

Các từ khóa và tên tiêu chuẩn ở bảng này là gợi ý từ trí nhớ của Claude, chưa kiểm chứng.
