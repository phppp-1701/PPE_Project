# Báo cáo giai đoạn 5: đánh giá bản 4 đóng băng trên 9 video quay gần (kiem_thu_gan)

Ngày chạy: 14/11/2026. Tập `kiem_thu_gan` chỉ dùng để báo cáo. Không chỉnh ngưỡng, trọng số, logic hay nhãn theo kết
quả này.

## 1. Cấu hình và phiên bản đã dùng

| Mục | Giá trị |
|---|---|
| Lệnh | mục 5 của `outputs/results/close_eval/README.md` (`06b evaluate --manifest ...`), log `../kiem_thu_gan_run.log` |
| Kiểm manifest trước khi chạy | đạt: code trùng `source_commit` `0b756b8`, không có thay đổi chưa commit, sha256 của cấu hình, 5 trọng số, 9 video, 9 file nhãn trùng `manifest.json` (HEAD lúc chạy `05adc55`, commit chỉ chứa manifest) |
| Bản 4 (`v4`) | `configs/pipeline.yaml` ở `0b756b8`: detector C4 (`yolo11s_ppe6_c4`), imgsz 960, ByteTrack, `yolo11n-pose.pt`; bộ phân loại: găng bản 2, kính bản 3, **mũ bản 4** (vùng đầu k 0,2, s 1,3; t_pos 0,91, t_neg 0,50) |
| Bản cũ (`baseline`) | `pipeline_baseline_0645f53.yaml` = `configs/pipeline.yaml` của `0645f53` (mũ theo luật cũ, mọi thứ khác như bản 4) |
| Môi trường | Python 3.12.12, torch 2.11.0+cu128, ultralytics 8.4.189, RTX 3050 Laptop 4 GB, driver 576.28 |
| Chạy | 9 video × 2 cấu hình, đúng thứ tự video9 → video17, mỗi video bản cũ trước rồi bản 4; mọi lượt chạy tới bước `full`, không lỗi; số khung xử lý bằng số khung của video |

Thứ tự trong lệnh (video, cấu hình) là cố định trong `06b`; mỗi lượt là một tiến trình riêng nên thứ tự không ảnh hưởng
kết quả (kết quả đã kiểm lặp lại giống từng byte trên video 3-6).

## 2. Nhãn tham chiếu và cách chấm

- **Nhãn tham chiếu, không phải ground truth đã xác minh.** `data/videos/video9..17_machine_cvat.zip` là nhãn máy
  (Claude) qua hai lượt, trạng thái `machine_consensus`, **chưa có người kiểm định**. Chỗ hai lượt khác nhau đã để
  `chua_xac_dinh`.
- **Nguy cơ thiên lệch:** người gán (Claude) đã xem kết quả hệ thống trên các video này trước khi gán, nên nhãn có thể
  nghiêng về phía hệ thống (đánh giá có thể lạc quan hơn thực tế), nhất là ở các khung khó.
- Chấm theo khung-người: hộp nhãn ở mỗi khung (nội suy giữa khung khóa) ghép với người dự đoán có IoU lớn nhất, đạt
  0,5 (`calibration.video.match_iou`). Ghép không ràng buộc một-một (cách đã dùng từ trước, giữ để so được). Hộp
  không ghép được nằm ở cột "Không ghép", không bị bỏ.
- Găng: `thieu` nếu một tay `thieu`, `co` nếu hai tay `co`, còn lại `chua_xac_dinh`.
- **Không tính Event F1** cho 9 video vì chưa có nhãn sự kiện. Chỉ liệt kê sự kiện hệ thống tạo ra.
- Số trong bảng là số khung-người, không phải độ chính xác tuyệt đối so với thực tế.

## 3. Kết quả

Ký hiệu: "Có đúng a/b" = a khung máy Có trên b khung nhãn Có (b gồm cả khung không ghép); tương tự "Thiếu đúng".
Báo thiếu oan = nhãn Có, máy Thiếu. Báo Có sai = nhãn Thiếu, máy Có. CXĐ = Chưa xác định.

### 3.1. Tổng 9 video (bản 4)

| PPE | Có đúng | Thiếu đúng | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|
| Mũ | 1858/2117 | 624/704 | 53 | 49 | 193 | 31 | 0 | 182 | 24 |
| Áo | 1317/1939 | 1064/1064 | 422 | 0 | 176 | 0 | 0 | 0 | 24 |
| Găng | 224/377 | 526/1070 | 0 | 0 | 143 | 544 | 31 | 1556 | 24 |
| Kính | 795/957 | 770/771 | 114 | 0 | 48 | 1 | 74 | 1275 | 24 |
| Ủng | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 1 | 3003 | 24 |

Ủng: nhãn luôn là `chua_xac_dinh` (chân ngoài khung ở cả 9 video), nên không đo được ủng trên tập này.

### 3.2. So với bản cũ

- **Tổng 9 video của bản 4 giống hệt bản cũ ở mọi PPE và mọi cột** (bảng tổng của bản cũ trong `results.md`).
- Khác nhau chỉ ở:
  - video16, mũ: 2 khung nhãn CXĐ, bản cũ CXĐ → bản 4 Có (không tính được đúng hay sai vì nhãn CXĐ);
  - video15, mũ: 1 dòng ở người không có nhãn, bản cũ không Có → bản 4 Có (không kiểm được đúng sai).
- Dòng `frames.csv` (khung, người, hộp) hai bản trùng hoàn toàn ở cả 9 video. Sự kiện (người, mở, đóng, mục thiếu,
  lịch sử mục thiếu) giống nhau ở cả 9 video.
- Bản cũ trên tập này khớp với số đã ghi trong kế hoạch ngày 14/11 (cùng tử số; mẫu số ở đây gồm thêm khung không
  ghép).

### 3.3. Từng video (bản 4; bản cũ giống hệt trừ 3 khung nêu ở 3.2)

| Video | PPE | Có đúng | Thiếu đúng | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|
| video9 | mũ | 315/315 | 0/0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video9 | áo | 52/315 | 0/0 | 232 | 0 | 31 | 0 | 0 | 0 | 0 |
| video9 | găng | 0/0 | 81/160 | 0 | 0 | 0 | 79 | 0 | 155 | 0 |
| video9 | kính | 207/225 | 85/85 | 11 | 0 | 7 | 0 | 5 | 5 | 0 |
| video10 | mũ | 361/361 | 0/0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video10 | áo | 179/361 | 0/0 | 182 | 0 | 0 | 0 | 0 | 0 | 0 |
| video10 | găng | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 0 | 361 | 0 |
| video10 | kính | 361/361 | 0/0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | mũ | 191/191 | 66/78 | 0 | 11 | 0 | 1 | 0 | 2 | 0 |
| video11 | áo | 0/0 | 271/271 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | găng | 0/0 | 264/271 | 0 | 0 | 0 | 7 | 0 | 0 | 0 |
| video11 | kính | 0/0 | 270/271 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| video12 | mũ | 167/167 | 0/0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | áo | 0/0 | 167/167 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | găng | 167/167 | 0/0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | kính | 0/0 | 167/167 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video13 | mũ | 0/0 | 179/247 | 0 | 38 | 0 | 30 | 0 | 0 | 0 |
| video13 | áo | 0/0 | 247/247 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video13 | găng | 0/88 | 0/0 | 0 | 0 | 88 | 0 | 0 | 159 | 0 |
| video13 | kính | 3/132 | 110/110 | 94 | 0 | 35 | 0 | 5 | 5 | 0 |
| video14 | mũ | 0/0 | 379/379 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video14 | áo | 0/0 | 379/379 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video14 | găng | 0/0 | 69/113 | 0 | 0 | 0 | 44 | 0 | 266 | 0 |
| video14 | kính | 224/239 | 138/138 | 9 | 0 | 6 | 0 | 2 | 2 | 0 |
| video15 | mũ | 142/162 | 0/0 | 0 | 0 | 7 | 0 | 0 | 122 | 24 |
| video15 | áo | 154/284 | 0/0 | 8 | 0 | 98 | 0 | 0 | 0 | 24 |
| video15 | găng | 57/122 | 0/0 | 0 | 0 | 55 | 0 | 30 | 162 | 24 |
| video15 | kính | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 46 | 284 | 24 |
| video16 | mũ | 422/441 | 0/0 | 0 | 0 | 19 | 0 | 0 | 58 | 0 |
| video16 | áo | 452/499 | 0/0 | 0 | 0 | 47 | 0 | 0 | 0 | 0 |
| video16 | găng | 0/0 | 5/46 | 0 | 0 | 0 | 41 | 1 | 453 | 0 |
| video16 | kính | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 16 | 499 | 0 |
| video17 | mũ | 260/480 | 0/0 | 53 | 0 | 167 | 0 | 0 | 0 | 0 |
| video17 | áo | 480/480 | 0/0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video17 | găng | 0/0 | 107/480 | 0 | 0 | 0 | 373 | 0 | 0 | 0 |
| video17 | kính | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 0 | 480 | 0 |

Ủng ở mọi video: nhãn CXĐ toàn bộ (video15 có 1 khung máy Thiếu trên nhãn CXĐ). Bảng đầy đủ cả hai cấu hình:
`results.md`, `results.json`.

### 3.4. Sự kiện hệ thống tạo ra (bản 4, giống bản cũ; không có nhãn sự kiện để chấm)

| Video | Sự kiện (người, thời gian, mục thiếu cuối) |
|---|---|
| video9 | người 1, 0-10,5 s: găng, áo |
| video10 | người 1, 0-12,0 s: xác nhận thiếu áo lúc 0,47 s; từ 7,43 s danh sách mục thiếu rỗng (áo không còn bị xác nhận thiếu); đóng khi hết video (`session_ended_unverified`) |
| video11 | người 1, 0-10,8 s: găng, kính, áo |
| video12 | người 1, 0-6,7 s: kính, áo |
| video13 | người 1, 0-8,2 s: kính, mũ, áo |
| video14 | người 1, 0-15,2 s: găng, mũ, áo |
| video15 | người 3, 0-4,9 s: găng |
| video16 | không có sự kiện |
| video17 | người 1, 1,2-16,0 s: găng |

## 4. Trường hợp sai và đáng chú ý

1. **Mũ, video17 (lý do làm bản 4): bản 4 không cải thiện.** 260/480 khung Có đúng, 53 báo thiếu oan, 167 CXĐ, giống
   bản cũ. Phân tích chỉ đọc (`helmet_diag.py`, `helmet_diag_video17.json`, `.jpg`; chạy lại đúng cấu hình đóng băng,
   ghi thêm chi tiết mũ mỗi khung):
   - cả 480 khung đều cắt được vùng đầu; ảnh cắt đặt đúng chỗ (đầu nhìn từ sau, mũ tối màu có quai sau gáy nằm giữa
     ảnh, xem `helmet_diag_video17.jpg`);
   - bộ phân loại bản 4 cho xác suất có mũ rất thấp: trung vị 0,018 (thấp nhất 0,0003, cao nhất 0,94); phiếu `neg`
     ở 442/480 khung, `unsure` 38, không khung nào `pos`;
   - 222 khung vẫn Có vì detector thấy hộp mũ (mũ không bị phủ quyết); 53 khung Thiếu do detector không thấy hộp và
     phiếu `neg`; 167 khung CXĐ (phiếu `neg`, không hộp, nhưng không đủ điều kiện kết luận Thiếu).
   - Kết luận: lỗi nằm ở bộ phân loại (đoán "không mũ" khá chắc trên mũ tối màu nhìn từ sau), không phải ở hình học cắt
     ảnh. Nguyên nhân sâu hơn (vd dữ liệu train ít mũ nhìn từ sau có quai) chưa kiểm chứng.
2. **Áo bị cắt ở ngực (video9, video10): 414 khung báo thiếu oan** (232 + 182), lỗi đã biết; áo không dùng bộ phân
   loại.
3. **Kính, video13 (ảnh trắng đen, kính trong): 94 khung báo thiếu oan**, chỉ 3/132 khung Có đúng; lỗi đã biết.
4. **Mũ báo Có sai: 49 khung** (video13 38, video11 11), nhãn Thiếu mà máy Có. Có ở cả bản cũ, không do bản 4.
5. **Găng: nhiều CXĐ** (544 khung nhãn Thiếu thành CXĐ, 143 khung nhãn Có thành CXĐ), nhất là video17 (373/480);
   găng ít khi báo sai (0 báo thiếu oan, 0 báo Có sai) nhưng thường không kết luận.
6. **video15: 24 hộp nhãn không ghép được người** (người ở mép, chồng nhau); giữ ở cột "Không ghép".
7. **video16 (người quay lưng): không có sự kiện**, kính, găng gần như toàn CXĐ theo nhãn; mũ 422/441 Có đúng.

## 5. Hiệu năng

- Đo có kiểm soát (giai đoạn 3, `../benchmark/benchmark.md`, video 3-6, 3 lượt, không ghi video, latency không gồm giải
  mã): bản 4 **23,07 ± 0,84 FPS xử lý**, **20,51 ± 0,67 FPS gồm giải mã**, latency TB 43,4 ms (bản cũ 26,13 FPS,
  22,97 FPS, 38,3 ms).
- Quan sát trong lượt đánh giá này (một lượt mỗi video, có ghi `frames.csv`, `events.jsonl`, ảnh minh chứng; không
  phải benchmark có kiểm soát): tổng 2.841 khung, bản cũ 21,71 FPS, bản 4 18,33 FPS (FPS toàn luồng gồm đọc khung).
  Bước `parts` (p50) tăng ở mọi video, vd video9 7,8 → 18,8 ms; video17 6,7 → 11,9 ms.

| Video | Độ phân giải | Khung | FPS bản cũ | FPS bản 4 |
|---|---|---|---|---|
| video9 | 1920x1080 | 315 | 20,61 | 16,80 |
| video10 | 1920x1080 | 361 | 21,93 | 17,73 |
| video11 | 1080x1920 | 271 | 19,51 | 16,60 |
| video12 | 1920x1080 | 167 | 19,16 | 16,81 |
| video13 | 1920x1080 | 247 | 22,45 | 18,04 |
| video14 | 1920x1080 | 379 | 21,86 | 17,65 |
| video15 | 1920x1080 | 122 | 15,47 | 14,30 |
| video16 | 1920x1080 | 499 | 25,45 | 21,92 |
| video17 | 1920x1080 | 480 | 23,16 | 20,71 |

- Chưa có kết quả chứng minh hệ thống đáp ứng thời gian thực 25 hoặc 30 FPS; không kết luận điều đó.

## 6. Giới hạn

- Nhãn tham chiếu là nhãn máy hai lượt, chưa người kiểm định; người gán đã xem kết quả hệ thống trước (nguy cơ thiên
  lệch về phía hệ thống).
- Không có nhãn sự kiện: không có Event F1 trên tập này.
- Tập nhỏ: 9 video, 2.841 khung, phần lớn mỗi video một người; ủng không đo được (chân ngoài khung).
- Ghép người theo IoU lớn nhất, không một-một.
- Hiệu năng chỉ trên một laptop (RTX 3050 4 GB), lúc đo có container CVAT chạy nền; số FPS trong lượt đánh giá này
  không phải đo có kiểm soát.
- Tái lập: cần đúng trọng số và video (không có trên Git, kiểm bằng sha256 trong `manifest.json`); lặp lại giống từng
  byte mới kiểm trên máy này.
- Bản 4 là ngoại lệ: không đạt tiêu chí "bỏ sót không tăng" trên video 3-6 (người dùng chọn bật); găng bản 2 cũng là
  ngoại lệ.

## 7. Kết luận

**Bản 4 làm tốt:**
- Không gây hại đo được trên tập này: không thêm báo Có sai, không thêm báo thiếu oan, không đổi sự kiện, không mất
  người hay dòng nào so với bản cũ.
- Trên video 3-6 (video phát triển, không phải tập này) bản 4 bớt 10 khung báo thiếu oan mũ và bỏ một mục mũ báo nhầm
  trong sự kiện (giai đoạn 2).

**Bản 4 chưa làm tốt:**
- Không cải thiện video17, đúng tình huống bản 4 được làm ra để sửa: bộ phân loại đoán "không mũ" khá chắc trên mũ tối
  màu nhìn từ sau, dù ảnh cắt đúng chỗ.
- Trên 9 video, bản 4 gần như không đổi kết quả (3 khung khác, đều không kiểm được đúng sai) nhưng chậm hơn: FPS xử lý
  23,07 so với 26,13 (đo có kiểm soát, -11,7%).

**Chưa thể kết luận:**
- Bản 4 có tốt hơn bản cũ trên mũ nhìn từ sau nói chung hay không (chỉ có video17, và ở đó không tốt hơn).
- Độ chính xác thật so với thực tế (nhãn chưa người kiểm định, có nguy cơ thiên lệch).
- Chất lượng sự kiện trên 9 video (không có nhãn sự kiện).
- Ủng trên video gần (không có khung nhìn thấy chân).
- Khả năng đáp ứng thời gian thực 25 hoặc 30 FPS.

## 8. File

| File | Nội dung |
|---|---|
| `results.md`, `results.json` | bảng đầy đủ cả hai cấu hình, ma trận nhầm lẫn, sự kiện, so sánh |
| `transitions.csv` | 2 khung khác nhau giữa hai bản (video16) |
| `baseline/<video>/`, `v4/<video>/` | `frames.csv`, `events.jsonl`, `summary.json` của từng lượt |
| `helmet_diag.py`, `helmet_diag_video17.json`, `helmet_diag_video17.jpg` | phân tích chỉ đọc mũ video17 |
| `../kiem_thu_gan_run.log` | log toàn bộ lượt chạy |
