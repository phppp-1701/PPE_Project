# Nâng detector cho găng, kính, ủng (C5): phân tích lỗi C4 và kế hoạch (16/11/2026)

Nhánh `exp/ppe6`. Tài liệu ghi theo thứ tự đã làm: lý do, bước A (đã chạy), kế hoạch các bước sau (chưa làm). Mọi số
dưới đây là số đo thật trên máy, ghi kèm lệnh và file kết quả. Phần đánh dấu **(Claude quan sát)** là nhận xét của agent
khi xem bảng ảnh, không phải số đo, không phải nhãn người.

## 0. Vì sao có bước này (chuỗi kết quả trước)

| Mốc | Kết quả dẫn tới quyết định | Tài liệu |
|---|---|---|
| r1 → r2 (03/11) | Đổi `imgsz` 640 → 960 vì găng bỏ sót chủ yếu là hộp nhỏ: găng mAP50 val +0,058, phần tăng nằm ở hộp 8–16 px, hộp ≥ 32 px gần như không đổi | `2026-11-03_yolo11s_r2.md` |
| r2 suy luận ở 1280 (04/11) | Không train lại, chỉ chạy ở 1280: găng 0,576 → 0,588, trung bình giảm 0,790 → 0,783 → giữ 960 | như trên, mục cuối |
| C2, C3, C4 (06–11/11) | Thêm lớp kính, ủng; C4 chọn làm bản 6 lớp chính. Test: găng 0,638, kính 0,736 (38 hộp, KTC 0,60–0,86), ủng 0,477 (102 hộp, KTC 0,33–0,65) | `2026-11-06_ppe6_plan.md`, `2026-11-12_c4_official_test_and_ablation.md` |
| Holdout (16/11) | Độ đúng hệ thống so với nhãn máy: găng 0,497, kính 0,743, ủng 0,248 | `outputs/results/close_eval/final/holdout_summary.md` |
| Demo camera (16/11) | Người dùng thấy kính cận thỉnh thoảng bị nghi là kính bảo hộ, tay trần thỉnh thoảng bị nhận là găng. Chẩn đoán 30 s (scratchpad, không phải tập đánh giá): kính báo Có sai 0/433 khung (42 khung detector nghi, bộ phân loại bác bỏ cả 42), găng báo Có sai 3/433 khung một tay, cảnh báo vẫn tạo đúng | mục "camera trực tiếp" của phiên 16/11 |

**Người dùng quyết định 16/11/2026:** nâng mAP50 detector của các lớp đang dưới 0,8 (găng, kính, ủng). Thứ tự: (A) phân
tích lỗi, (B) sửa chất lượng nhãn do Claude làm (người dùng không gán tay), (C) thêm dữ liệu tốt có ghi nguồn đầy đủ,
(D) train ở `imgsz` 1280, (E) YOLO11m nếu chạy tốt trên camera laptop, (F) mở rộng val, test cho kính, ủng do Claude
gán. Mục tiêu 0,8 là mong muốn của người dùng; tài liệu này ghi trung thực mức đạt được.

## 1. Bước A: phân tích lỗi C4 trên val (đã chạy 16/11/2026)

Lệnh: `python scripts/04h_error_analysis.py` (tham số `configs/ppe6.yaml` mục `error_analysis`; đọc `capture.npz` của
04d đã có, không chạy lại mô hình). Kết quả: `outputs/results/error_analysis/c4_val_gloves/`, `c4_valnew/`
(`summary.json`, `fn.csv`, `fp.csv`, bảng ảnh `sheet_*.jpg`). AP50 tính lại khớp 04e (kính 0,7263, ủng 0,5264).

Quy ước: ghép tham lam theo conf, cùng lớp, IoU ≥ 0,5. "Bỏ sót" tính trên mọi dự đoán của capture (conf ≥ 0,001), nên
recall ở đây là recall tối đa. "Báo thừa" chỉ tính dự đoán conf ≥ 0,25. Cỡ hộp = cạnh ngắn ở không gian ảnh vào 960.
Kiểu lỗi: `lech_hop` (có dự đoán cùng lớp IoU 0,1–0,5), `nham_lop`, `khong_thay`; báo thừa thêm `vat_am` (trùng hộp
tay trần / giày / kính thường / `no_gloves`... của nhãn gốc SH17, Construction-PPE), `trung_lap`, `khong_ro`.

### 1a. Găng (ppe4 val, 864 hộp)

| | Số |
|---|---|
| AP50 (val gốc) | 0,6154 |
| Recall tối đa | 0,836 (< 16 px 0,669; 16–32 px 0,850; 32–64 px 0,826; ≥ 64 px 0,887) |
| Recall theo nguồn | CHV 0,855; Construction-PPE 0,824; SH17 0,831 |
| Bỏ sót 142 hộp | lệch hộp 80, không thấy 61, nhầm lớp 1 |
| **Báo thừa conf ≥ 0,25: 312** | **không rõ 156**, lệch hộp 74, trùng tay trần SH17 57, trùng lặp 24, nhầm lớp 1 |

Nhận xét:
- Recall tối đa đã 0,84 mà AP chỉ 0,62: **vấn đề chính của găng là báo thừa có conf cao**, không phải bỏ sót.
- **(Claude quan sát)** `sheet_gloves_thua_khong_ro.jpg` (40 báo thừa conf cao nhất): khoảng 12–18/40 là găng thật
  không có nhãn (găng trắng, xanh lá, đen, đỏ, găng y tế); còn lại là lỗi thật (lá cây, quần jean, tay trần, miếng đệm
  gối). `sheet_gloves_thua_vat_am.jpg`: khoảng 8–10/40 hộp "hands" của SH17 thật ra là tay đeo găng (SH17 chỉ gán
  `hands`, không gán `gloves`). → **nhãn găng bị thiếu ở val** (và nhiều khả năng ở train): mAP găng bị đo thấp hơn
  thực, và mô hình bị dạy rằng găng là nền.
- **(Claude quan sát)** `sheet_gloves_bo_sot_lon.jpg`: phần lớn bỏ sót lớn là lệch hộp do quy ước khoanh không thống
  nhất: có hộp gồm cả cổ găng dài, có hộp khoanh hai tay chung; vài nhãn đặt trên găng không đeo hoặc tay trần.
- Hộp < 16 px: 118/864 (14%), recall 0,669: phần `imgsz` 1280 có thể giúp (như r1 → r2).
- SH17 có 15.770 hộp `hands` (train 11.020, val 2.390, test 2.440), chỉ 80 hộp trùng hộp `gloves`: nguồn ứng viên lớn để
  tìm găng thiếu nhãn.

### 1b. Ủng (`val_new`, 83 hộp, 69 ảnh)

| | Số |
|---|---|
| AP50 | 0,5264 |
| Recall tối đa | 0,711 (< 32 px 0,833; 32–64 px 0,778; **≥ 64 px 0,628**) |
| Recall theo nguồn | **Construction-PPE 0,500 (36 hộp)**; SH17 0,872 (47 hộp) |
| Bỏ sót 24 | **lệch hộp 16**, không thấy 7, nhầm lớp 1 |
| Báo thừa 18 | **lệch hộp 11**, giày thường 5, không rõ 2 |

Nhận xét:
- Hộp lớn bị sót nhiều hơn hộp nhỏ: không phải vấn đề cỡ ảnh.
- **(Claude quan sát)** `sheet_boots_bo_sot_lon.jpg`: nhãn Construction-PPE có hộp **khoanh cả đôi chân** (quy ước của
  project: mỗi chiếc một hộp) và hộp **lệch hẳn ra nền** cạnh chiếc ủng; vài nhãn SH17 là giày thể thao. Đếm hình dạng
  hộp ủng Construction-PPE bản cũ (rộng > 1,3 × cao, nhiều khả năng là cả đôi): train 207/1.044, val 55/291, test
  44/262 (khoảng 20%).
- → lỗi chính của ủng là **nhãn không nhất quán giữa hai nguồn**, AP50 ở IoU 0,5 phạt thẳng lỗi này.

### 1c. Kính (`val_new`, 29 hộp)

AP50 0,7263, recall tối đa 0,862, bỏ sót 4 (lệch hộp 2, không thấy 2), báo thừa 8 (2 mỗi loại). **Tập quá nhỏ để
phân tích theo nhóm**; KTC của test (38 hộp) rộng 0,26. Muốn biết kính đạt 0,8 hay không phải có tập đánh giá lớn hơn
(bước F).

### 1d. Đối chiếu mũ, áo (ppe4 val)

Mũ AP50 0,892, recall 0,942. Áo 0,778, recall 0,860; áo < 16 px recall 0,053 (57 hộp), SH17 áo recall 0,442.

### 1e. Tốc độ detector trên laptop (lần đo bẩn, phải đo lại)

Lệnh: `python scripts/04i_detector_speed.py` (`configs/ppe6.yaml` mục `speed_check`, video4, 200 khung, batch 1).
Kết quả `outputs/results/error_analysis/detector_speed.json`. **Máy đang chạy Minecraft và SKLauncher, GPU bận 38% khi
nhàn rỗi**, nên số tuyệt đối chậm hơn lần benchmark sạch (detector C4 khoảng 17 ms). Chỉ dùng tỉ lệ:

| Mô hình × imgsz | ms/khung TB (đo bẩn) | So với s@960 |
|---|---|---|
| C4 (s) @ 960 | 36,7 | 1,00 |
| C4 (s) @ 1280 | 60,3 | 1,64 |
| YOLO11s COCO @ 960 / 1280 | 39,2 / 62,5 | 1,07 / 1,70 |
| YOLO11m COCO @ 960 | 82,5 | 2,25 |
| YOLO11m COCO @ 1280 | 137,8 | 3,75 |

`yolo11m.pt` (trọng số COCO của Ultralytics) được tải về thư mục gốc project để đo; chỉ dùng đo tốc độ.

**Đo lại khi máy rảnh (17/11/2026 khoảng 02:15, không còn `javaw`, GPU nhàn rỗi 23%)**, cùng lệnh; số bẩn giữ ở
`detector_speed_dirty_minecraft.json`, số sạch ở `detector_speed.json`:

| Mô hình × imgsz | ms/khung TB | p95 | Ước lượng cả pipeline* | Tiêu chí ≥ 20 FPS |
|---|---|---|---|---|
| C4 (s) @ 960 | 17,01 | 17,47 | khoảng 38 ms (đo thật 07: 26,55 FPS) | đạt |
| C4 (s) @ 1280 | 26,15 | 26,93 | khoảng 47 ms, khoảng 21 FPS | sát mốc, phải đo bằng 07 |
| YOLO11s COCO @ 960 / 1280 | 18,63 / 33,15 | 22,20 / 41,32 | | |
| YOLO11m COCO @ 960 | 45,05 | 50,61 | khoảng 66 ms, khoảng 15 FPS | không đạt |
| YOLO11m COCO @ 1280 | 71,99 | 74,83 | khoảng 93 ms, khoảng 11 FPS | không đạt |

*Ước lượng = detector + khoảng 21 ms phần còn lại của pipeline (37,7 ms/khung của bản cuối trừ 17 ms detector). Chỉ để
loại cấu hình; cấu hình được chọn phải đo lại bằng `07_benchmark_pipeline.py`. → **Loại YOLO11m** theo tiêu chí tốc độ
người dùng chốt 17/11; còn s@960 và s@1280.

### 1f. Kết luận bước A

1. **Găng:** lỗi lớn nhất là nhãn thiếu (găng không được gán, nhất là SH17 gán `hands` cho tay đeo găng) và quy ước
   khoanh hộp không thống nhất; sau đó là tay trần bị nhận là găng; hộp < 16 px là phần nhỏ (14%).
2. **Ủng:** lỗi lớn nhất là nhãn Construction-PPE (hộp cả đôi, hộp lệch); cỡ ảnh không phải nguyên nhân chính.
3. **Kính:** chưa đủ mẫu để kết luận; cần tập đánh giá lớn hơn.
4. **Cỡ ảnh 1280** chỉ nhắm vào phần hộp nhỏ (găng < 16 px, kính nhỏ ở xa); không sửa được lỗi nhãn. Không thể đảm
   bảo trước là 1280 giúp: phải đo trên val (bước D).
5. Vì nhãn val cũng sai, **sửa nhãn val sẽ làm thay đổi số đo của cả C4**: mọi so sánh C5 với C4 phải chấm lại C4 trên
   val đã sửa (cùng bộ nhãn), không so với số cũ.

## 2. Kế hoạch các bước sau (chưa làm, chờ người dùng duyệt các điểm ở mục 3)

### B. Sửa nhãn (Claude làm, ghi là nhãn máy)

- **Găng thiếu nhãn:** ứng viên = hộp `hands` của SH17 không trùng `gloves` (mọi split) + báo thừa conf cao của C4
  (**chỉ dùng cho train**, không dùng làm ứng viên cho val/test để không thiên vị C4). Hai lượt máy độc lập:
  (1) bộ phân loại tay (găng / tay trần) của project, (2) Claude xem bảng ảnh cắt. Hai lượt cùng nói "găng" thì thêm hộp;
  khác nhau thì thành vùng `ignore` (val/test) hoặc bỏ ảnh khỏi train; như quy trình máy gán đã có (`machine_consensus`).
- **Quy ước hộp găng:** một hộp cho mỗi bàn tay đeo găng, gồm cổ găng nhìn thấy; hộp hai tay chung thì tách hoặc
  `ignore`.
- **Ủng:** hộp rộng (cả đôi) và hộp lệch của Construction-PPE: Claude xem bảng ảnh; tách thành hai hộp theo mắt cá (pose)
  khi rõ, không rõ thì `ignore`; train có thể dùng hộp dự đoán C4 làm gợi ý nắn hộp, val/test thì không.
- **Kính:** Claude xem lại toàn bộ hộp kính val/test (nhỏ, làm được hết) theo `docs/annotation_rules.md`.
- Ghi mọi thay đổi vào bảng (ảnh, hộp cũ, hộp mới, lý do, lượt máy) để truy lại; không sửa `data/raw/`, `data/ppe4/`.

### C. Thêm dữ liệu

Tìm bộ công khai có găng, ủng, kính bảo hộ đang đeo và mẫu âm (tay trần, giày thường, kính cận); ghi nguồn, giấy phép,
số ảnh, cách đổi nhãn, sha256 trong `data/raw/<nguồn>/README.md`; lọc trùng cảnh với mọi tập đánh giá (03e); chỉ vào
train. Danh sách ứng viên sẽ trình người dùng trước khi tải.

### D, E. Cỡ ảnh, cỡ mô hình

- Đo lại tốc độ khi tắt game. Chốt với người dùng **FPS tối thiểu trên camera** trước khi chọn s/m, 960/1280.
- Thời gian Kaggle: C4 (s, 960) 6,69 giờ cho 68 epoch. Ước tính theo tỉ lệ tốc độ: s@1280 khoảng 11–12 giờ (sát giới
  hạn 12 giờ một phiên), m@960 khoảng 15 giờ, m@1280 hơn 25 giờ (nhiều phiên, gần hết hạn mức GPU tuần). Phương án rẻ hơn:
  **tinh chỉnh tiếp từ trọng số C4** ở 1280 trên dữ liệu đã sửa, ít epoch hơn.
- Để biết 1280 có giúp không, phải có so sánh cùng dữ liệu: C5-960 và C5-1280 (2 lần train), chọn trên val đã sửa.

### F. Mở rộng val, test cho kính, ủng

Claude gán nhãn ảnh mới (không trùng cảnh với train) theo `docs/annotation_rules.md`, hai lượt máy, hộp hai lượt khác
nhau không vào val/test (luật CLAUDE.md).

## 2B. Bước B, F: đang làm (từ 16/11/2026, người dùng "ok thực hiện đi")

Người dùng cho làm tiếp khi chưa trả lời ba câu ở mục 3. Cách xử lý: mọi nhãn mới ghi trạng thái nhãn máy
(`machine_consensus` / `machine_labeled`), chưa có người kiểm định; gói kiểm định mẫu được chuẩn bị để người dùng làm khi
muốn. FPS tối thiểu hỏi lại ở bước D, E. Tốc độ đo lại khi máy không chạy Minecraft (23:30 ngày 16/11 vẫn còn `javaw`).

Script: `scripts/03z_c5_relabel.py`, tham số `configs/ppe6.yaml` mục `c5_relabel`, kết quả `data/ppe6/c5/`.

### Hai lần chạy thử (scratchpad, chỉ để chọn cách làm)

1. **240 hộp `hands` SH17 ngẫu nhiên (train)**, chấm bằng bộ phân loại tay (`yolo11n_cls_parts_v4`) và OWLv2 trên ảnh cắt.
   **(Claude quan sát)** gần như toàn bộ là tay trần (SH17 có nhiều ảnh văn phòng, đời thường); chỉ khoảng 2–4/240 là
   găng không có nhãn. Bộ phân loại tay xếp các găng này lên đầu (p ≥ 0,8). OWLv2 trên ảnh cắt **không phân biệt** găng /
   tay trần (tay trần cũng được 0,5 với câu "a glove"). → Không dùng OWLv2 để chấm ảnh cắt; bộ phân loại tay chỉ dùng để
   chọn hộp cần xem (p ≥ 0,25), Claude xem toàn bộ hộp được chọn.
2. **OWLv2 cả ảnh, 60 ảnh ppe4 val**, câu hỏi "a glove", "a work glove", "a gloved hand": tìm lại 92% hộp găng có sẵn ở
   điểm 0,2 (69% ở 0,3); 15 đề xuất không trùng nhãn, **(Claude quan sát)** 2 là găng xanh thật không có nhãn, còn lại tay
   trần. → OWLv2 cả ảnh dùng để **đề xuất** găng, ủng, kính thiếu nhãn trên ảnh đánh giá; Claude quyết định.

Thời gian OWLv2: khoảng 1,3 giây/ảnh khi GPU chỉ chạy nó, 3,3 giây khi chạy cùng việc khác.

### Cách làm (chốt trước khi xem ảnh)

- **Nguồn đề xuất, chỉ để chọn chỗ cần xem:** OWLv2 cả ảnh (ảnh đánh giá), detector C4 (train và ảnh đánh giá), bộ phân
  loại tay trên mọi hộp `hands` SH17 không trùng găng (15.767 hộp; p ≥ 0,25: train 524, val 148, test 145).
- **Ảnh đánh giá dùng cả đề xuất của C4** (khác kế hoạch ban đầu). Lý do: găng C4 đã thấy mà không có nhãn là găng thật; bỏ
  chúng ra thì val vẫn thiếu nhãn đúng ở chỗ C4 báo, làm điểm C4 thấp sai. Để giảm thiên vị, đề xuất gộp từ ba nguồn, hộp
  chọn theo thứ tự hộp `hands` do người vẽ của SH17 > OWLv2 > C4, và bảng ảnh không ghi nguồn hay điểm.
  **Hộp ủng, kính có sẵn của ảnh đánh giá chỉ được nắn theo gợi ý OWLv2**, không theo C4.
- **Claude xem từng ô** trên bảng ảnh (ảnh cắt có ngữ cảnh, hộp đích đỏ, gợi ý đánh số), mù với nguồn và điểm, ghi mã quyết
  định; `collect` kiểm đủ ô và ghi `machine_pass_claude.csv`.
- **Hai lượt cho val, test:** lượt Claude và bộ phân loại bộ phận (tay, chân, mắt; p ≥ 0,5 là có PPE). Giống nhau thì
  `machine_consensus`, dùng làm nhãn; khác nhau, hoặc Claude ghi "không rõ", thì thành vùng `ignore` (không tính đúng, không
  tính sai), đúng luật CLAUDE.md. Train dùng quyết định của Claude, ô "không rõ" bị che xám như `dataset_c2`.

### Kết quả phần train (17/11/2026, nhãn máy, chưa người kiểm định)

Lệnh: `03z hands`, `03z c4pred`, `03z candidates --part train`, `03z sheets --task ...`, Claude ghi
`data/ppe6/c5/review/<task>_<số>.dec`, `03z collect`, `03z build-train`, `03b --dataset data/ppe6/c5/dataset_c5 --out
data/ppe6/c5/c5_extra`, `03z build-extra`.

| Việc | Ô Claude xem | Kết quả |
|---|---|---|
| Găng thiếu nhãn, train (đề xuất C4 conf ≥ 0,25 + hộp `hands` SH17 p ≥ 0,25, không trùng găng có sẵn) | 1.039 ô, 22 bảng | **85 găng thêm** (C2 72, Construction-PPE mới 13); **262 không rõ → che xám** (C2 224, mới 38); 692 không phải găng |
| Hộp ủng train Construction-PPE (không khớp C4 IoU ≥ 0,5, hoặc rộng > 1,3 × cao) | 670 ô, 14 bảng | giữ 630; thay theo gợi ý 5; bỏ (không phải ủng: tay áo, tay cầm giấy) 2; không rõ → bỏ hộp, che 33 |

**Sửa lại nhận định bước A về ủng:** 616/670 hộp "rộng" là **một chiếc ủng nhìn nghiêng** (chiếc ủng nằm ngang rộng hơn
cao), không phải hộp cả đôi; nhãn ủng train của Construction-PPE bản mới phần lớn đúng (**(Claude quan sát)** khác C4 chủ
yếu do mép hộp lệch nhẹ). Hộp sai thật chỉ khoảng 40/670 (6%). Hộp ủng của val (Construction-PPE bản cũ) kiểm riêng ở
phần đánh giá.

**(Claude quan sát) về găng:** ô "không rõ" nhiều (25%) vì tay tối, nhòe, ảnh trắng đen, cỡ nhỏ; che xám thay vì đoán
để mô hình không học nhãn sai cả hai chiều. Bộ phân loại tay cho nhiều ô nghi găng là tay trần da tối.

Bộ train C5: `data/ppe6/c5/dataset_c5/` (train C2 + sửa; ảnh có vùng che mới thu về cạnh dài 2.048 px, JPEG 92),
`changes_train.csv` (mỗi thay đổi: ảnh, item, quyết định, hộp cũ, hộp mới); gói Kaggle
`data/ppe6/variants/kaggle/c5_pack.zip` (339 MB, cùng định dạng gói C2: manifest, nhãn, ảnh che, ready.json ghi
"nhãn máy, chưa người kiểm định"). Bộ phụ `data/ppe6/c5/c5_extra/` (03b chạy lại trên train đã sửa: 2.500 ảnh cắt,
1.425 ảnh găng lặp; + 963 ảnh Construction-PPE mới với nhãn đã sửa), gói `c5_extra_pack.zip` (226 MB),
`changes_extra.csv`.

### Thêm dữ liệu (bước C): ứng viên tìm được, chưa tải

| Bộ | Lớp có ích | Giấy phép | Ghi chú |
|---|---|---|---|
| CPPE-5 (Dagli, Shaikh 2021; arXiv 2112.09569) | gloves, goggles (y tế) | nhãn Apache 2.0; ảnh Flickr, theo điều khoản Flickr | khoảng 1.000 ảnh, miền y tế; kính bảo hộ y tế đúng định nghĩa kính bảo hộ |
| Open Images V7 (Google) | Glove, Goggles, Boot | nhãn CC BY 4.0, ảnh ghi CC BY 2.0 | miền chung (găng thể thao, kính trượt tuyết, bốt thời trang): phải lọc theo ngữ cảnh lao động |
| Roboflow "PPE Dataset for Workplace Safety" (SiaBar) | gloves, glasses an toàn | CC BY 4.0 (theo kết quả tìm kiếm) | trang chặn truy cập tự động (403); cần người dùng mở bằng tài khoản Roboflow để xem lớp, nguồn ảnh |

### Kết quả phần val, test (17/11/2026, nhãn máy, chờ người kiểm định)

Lệnh: `03z owl` (OWLv2 cả 3.232 ảnh đánh giá), `03z c4pred --eval`, `03z candidates --part eval`, `03z sheets`, Claude
ghi `.dec`, `03z collect`, `03z build-eval` → `data/ppe6/c5/eval/{val,test}/` (ảnh, nhãn 6 lớp, `data.yaml`),
`eval/ignore.csv`, `eval/files.json`, `changes_eval.csv` (mỗi dòng: item, quyết định Claude, p bộ phân loại, hành động,
trạng thái, hộp).

Ảnh đánh giá kính, ủng (`files.json` mục `new_class_files`): val 923 ảnh (val_new 69 + SH17, Construction-PPE cảnh sạch
của ppe4 val), test 981. Trước: val_new 69, test_new 117.

| Việc | Ô Claude xem | Claude quyết định |
|---|---|---|
| Găng thiếu nhãn, val + test (OWLv2 + C4 + hands SH17) | 2.038 ô, 34 bảng | găng 382, không phải 701, không rõ 955 |
| Giày SH17 (ủng bảo hộ hay giày thường), val + test | 964 ô, 21 bảng | ủng / giày bảo hộ 21, giày thường 502, không rõ 441 |
| Kính SH17 (kính bảo hộ đang đeo?), val + test | 321 ô, 7 bảng | kính bảo hộ 1, kính thường 228, không đeo 36, không rõ 56 |
| Hộp ủng có sẵn Construction-PPE (val, test, val_new, test_new) | 147 ô | giữ 82, nắn theo OWLv2 14, không phải ủng 27, không rõ 24 |
| Hộp kính có sẵn Construction-PPE | 20 ô | giữ 5, nắn 2, không phải 7, không rõ 6 |
| Ủng thiếu nhãn (OWLv2, Construction-PPE) | 177 ô | ủng 26, không 26, không rõ 125 |
| Kính thiếu nhãn (OWLv2, Construction-PPE) | 162 ô | kính 6, không 112, không rõ 44 |

Gộp hai lượt (Claude và bộ phân loại bộ phận v4, p ≥ 0,5 là có): găng thêm val 153, test 138; ủng thêm val 19
(SH17 4 + Construction-PPE 15), test 18; kính thêm 6; hộp ủng nắn 14, kính 2. **Vùng ignore** (hai lượt khác nhau hoặc
không rõ): găng val 625, test 589; ủng val 373, test 399; kính val 61, test 91.

**(Claude quan sát):**
- Hộp ủng Construction-PPE bản cũ trong val, test **sai nhiều hơn train**: 27/147 (18%) không phải ủng (giày thể thao,
  ống quần, chân trần, cả đôi chân ở xa), 24 không rõ. Đây là một phần lý do recall ủng của Construction-PPE thấp (bước A).
- Giày SH17 gần như toàn giày thường, ảnh đời thường: thêm được rất ít ủng (21 Claude chọn, 14 sau gộp). Kính SH17 gần như
  toàn kính cận, kính râm: **mở rộng tập đánh giá kính từ SH17 không được** (chỉ 1 kính bảo hộ). Kính cần nguồn khác
  (CHVG đã có 342 ảnh nháp chưa duyệt; bộ công khai ở bước C).
- Găng: tỉ lệ "không rõ" cao (47%) vì ứng viên OWLv2, C4 gồm nhiều tay nhỏ, nhòe, tối; ô không rõ thành ignore, không tính.

**C4 chấm lại trên val đã sửa** (`04d` + `04j_c5_eval.py`, `outputs/results/c5_eval/c4_val.json`, KTC 95% bootstrap theo
cảnh, nhãn máy chưa kiểm định):

| Lớp | Val gốc (bước A) | Val đã sửa, ảnh ppe4 val (1.586) | Val đã sửa, ảnh đánh giá lớp mới (923) |
|---|---|---|---|
| người | | 0,892 | 0,851 |
| mũ | 0,892 | 0,893 | 0,713 |
| áo | 0,778 | 0,778 | 0,417 |
| găng | 0,615 (864 hộp) | **0,623** [0,532; 0,716] (1.010 hộp) | 0,481 (420) |
| kính | 0,726 (val_new, 29 hộp) | | 0,681 [0,482; 0,871] (28 hộp) |
| ủng | 0,526 (val_new, 83 hộp) | | **0,458** [0,332; 0,618] (123 hộp) |

Nhận xét: sửa nhãn val không làm điểm C4 nhảy lên (găng +0,007); mức 0,6 của găng là thật chứ không chỉ do nhãn thiếu. Ủng
trên tập rộng hơn thấp hơn val_new. Từ đây mọi so sánh C5 với C4 dùng val đã sửa này (cùng nhãn, cùng ignore).

### Kiểm định của người lần 1 (17/11/2026): găng KHÔNG ĐẠT, ủng "có" không đạt

`03z audit --per 50` (263 ô, mẫu phân tầng các item `machine_consensus` của val, test; trang ẩn quyết định máy), người
kiểm định Hoàng Phương, `03z audit-report` → `data/ppe6/c5/audit/report.json`. Bất đồng người – máy (KTC Wilson 95%):

| Tầng | n | Bất đồng | Tiêu chí < 10% |
|---|---|---|---|
| Găng, máy nói có (hộp thêm) | 43 | **25 (58%)** [43%; 72%] | **không đạt** |
| Găng, máy nói không | 50 | 3 (6%) | đạt |
| Ủng, máy nói có (hộp giữ / nắn / thêm) | 44 | **7 (16%)** [8%; 29%] | **không đạt** |
| Ủng, máy nói không | 47 | 2 (4%) | đạt |
| Kính, máy nói có | 13 | 0 | đạt (n nhỏ) |
| Kính, máy nói không | 49 | 1 (2%) | đạt |

Người dùng nhận xét: "găng lại sai khá nhiều, một số cái đúng thì box lại không bao hết găng mà chỉ một phần nhỏ".

**Lỗi hệ thống (Claude xem lại 25 ô găng, 7 ô ủng bị người bác):**
1. **Găng – hình học hộp.** Khi xem bảng ảnh, Claude chấm "gần hộp có găng không", không chấm "hộp có bao sát đúng một
   chiếc găng không" như `docs/annotation_rules.md` mục 2. Hộp OWLv2 (nguồn của phần lớn ô thêm) thường bao vật đang cầm
   (khăn, túi, dụng cụ, mũ), chỉ một phần găng, hoặc hai găng một hộp; hộp `hands` SH17 có lúc chỉ bao một phần bàn tay.
   Một số ô là sai thật (tay trần, khăn).
2. **Ủng – hộp ở đầu gối.** Ảnh Construction-PPE bản cũ có hộp "boots" đặt ở đầu gối / ống quần (vd image1162: 3 ô); Claude
   đã giữ (`k`). Thêm một giày thể thao bị giữ.
Ngoài ra vài ô người và Claude khác nhau ở ca biên (giày da đen, kính đeo trên trán); theo luật, quyết định của người
được giữ, không chọn lại mẫu.

Hệ quả theo quy trình 07/11: **không dùng hộp găng thêm và hộp ủng giữ / thêm của val, test hiện tại để kết luận.** Số C4
trên val đã sửa ở mục trên (găng 0,623, ủng 0,458) vì vậy **chưa dùng được**.

### Sửa sau kiểm định lần 1 (17/11/2026, người dùng đồng ý)

1. **Găng val, test:** mọi hộp găng máy thêm thành vùng ignore (`gloves_eval_add ... >audit1_fail`). Val, test găng = nhãn
   gốc của người + ignore; không còn hộp găng nhãn máy.
2. **Ủng val, test:** `03z recheck` tạo một ô cho mỗi hộp ủng cuối cùng (giữ / nắn / thêm, 135 hộp); Claude xem lại với
   tiêu chí chặt "hộp bao sát đúng một chiếc ủng / giày bảo hộ" (bảng `boots_eval_recheck_*`): giữ 57, không phải 32 (hộp ở
   đầu gối, giày thể thao, ủng thời trang, hộp hai chiếc), không rõ 46. Không giữ thì thành ignore.
3. **Găng train:** 85 hộp găng Claude đã thêm được xem lại cùng tiêu chí (`gloves_train_recheck_*`): giữ 49, không phải 14,
   không rõ 22; không giữ thì che xám (không thành nhãn). Train C5 dựng lại (`build-train`, 03b, `build-extra`): găng thêm
   còn 41 (C2) + 8 (Construction-PPE mới); gói `c5_pack.zip` 348 MB, `c5_extra_pack.zip` 225 MB.
4. Val, test dựng lại (`build-eval`). Ignore: găng val 778, test 727; ủng val 420, test 430; kính val 61, test 91.
5. **Kiểm định lần 2, chỉ ủng:** `03z audit --only boots --tag 2 --per 50` → `data/ppe6/c5/audit2/audit.html`.

### Kiểm định lần 2, chỉ ủng (17/11/2026)

`03z audit --only boots --tag 2 --per 50` (100 ô), người kiểm định Hoàng Phương, `03z audit-report --tag 2`:

| Tầng | Lần đầu | Sau khi người xem lại 12 ô bất đồng |
|---|---|---|
| Ủng, máy nói có (sau lượt xem lại chặt) | **0/50** [0%; 7,1%], đạt | 0/50 |
| Ủng, máy nói không (giày SH17 Claude chấm giày thường) | 12/49 (24%), không đạt | **0/49** |

12 ô bất đồng đều là giày thể thao / giày thường (Claude xem lại). Người kiểm định được cho xem riêng 12 ô này
(`audit2/recheck12.html`: ảnh phóng to + ngữ cảnh rộng, không hiện ý máy) **sau khi biết chúng bất đồng**, và xác nhận
cả 12 là giày thường (`audit2/recheck12_result.json`). Báo cáo phải ghi cả hai số: lần đầu 12/49, sau xem lại 0/49;
người xem lại biết ô nào đang bất đồng nên kết quả sau xem lại không độc lập hoàn toàn. Không chọn mẫu lại.

**C4 chấm lại trên val đã sửa sau hai lần kiểm định** (`outputs/results/c5_eval/c4_val.json`, KTC 95% theo cảnh):

| Lớp | Val gốc (bước A) | Val đã sửa, ảnh ppe4 val | Val đã sửa, ảnh đánh giá lớp mới (923) |
|---|---|---|---|
| găng | 0,615 (864 hộp) | **0,662** [0,566; 0,754] (864 hộp + 778 vùng ignore) | 0,509 (343) |
| kính | 0,726 (29) | | 0,681 [0,482; 0,871] (28) |
| ủng | 0,526 (83) | | **0,632** [0,490; 0,776] (76) |

Cùng một mô hình C4: số tăng là do **nhãn val đúng hơn**, không phải mô hình tốt hơn (găng: vùng có găng thật nhưng không
có nhãn không còn bị tính là báo sai; ủng: bỏ hộp ở đầu gối, giày thường). Đây là mốc C4 để so với C5.

### Quyết định của người dùng (17/11/2026)

1. **Có kiểm định mẫu của người** cho nhãn máy C5. Gói kiểm định: trang web chạy trên máy, ảnh cắt + câu hỏi, người
   bấm Đúng / Sai / Không rõ, ẩn quyết định của máy; khoảng 300 ô, ưu tiên val, test; tiêu chí như quy trình 07/11
   (bất đồng < 10% theo lớp, không có lỗi hệ thống thì tầng được dùng).
2. **Tốc độ demo camera:** người dùng: "miễn sao không delay so với mắt người là ok". Claude đổi thành tiêu chí đo được,
   ghi trước khi đo lại tốc độ và trước khi train C5: **xử lý ≥ 20 khung/giây (≤ 50 ms/khung) và độ trễ p95 ≤ 100 ms**
   trên laptop với camera (cùng cách đo NFR-01 của 07). Cấu hình (s/m, 960/1280) nào không đạt thì không chọn cho demo.

### Kính: thêm 342 ảnh CHVG vào đánh giá (17/11/2026, người dùng chọn phương án a)

CHVG `chvg_glass_val`, `chvg_glass_test` (171 + 171 ảnh, cảnh tách theo 03h) đã có **hộp kính người chốt 07/11/2026**
(122 + 122); ảnh còn `pending` vì chưa xem cả ảnh tìm kính sót. Làm: `03z owl --chvg` (OWLv2, 0,46 giây/ảnh),
`03z candidates --part chvg` (219 đề xuất không trùng hộp có sẵn), Claude xem 8 bảng `goggles_chvg_add_*` theo tiêu chí
chặt (kính bảo hộ **đang đeo trên mắt**, hộp bao sát): kính 8, không 145 (kính đẩy lên mũ, kính cận, vành mũ, mặt),
không rõ 66. Gộp với bộ phân loại mắt: thêm val 5, test 3; ignore val 72, test 67. `build-eval` thêm ảnh CHVG vào
`eval/{val,test}` (mục `chvg_files` của `files.json`); `04j` thêm tập con `chvg` và `goggles_all` (= ảnh lớp mới + CHVG),
chỉ lớp kính; cảnh CHVG lấy từ `eval_status.csv`. Kiểm định: `03z audit --task goggles_chvg_add --tag 3 --per 40`
(48 ô) → `data/ppe6/c5/audit3/audit.html`.

C4 trên val đã sửa (chạy lại 04d với 1.773 ảnh; các lớp cũ lệch ≤ 0,002 so với lần trước do gom batch khác):

| Kính | Hộp | C4 mAP50 [KTC 95%] |
|---|---|---|
| tập lớp mới (SH17, Construction-PPE) | 28 | 0,682 [0,482; 0,871] |
| CHVG | 127 | **0,817** [0,754; 0,884] |
| gộp (`goggles_all`) | 155 | **0,762** [0,680; 0,832] |

Kính trong tiêu chí chọn bản dùng `goggles_all` (155 hộp) thay cho 28 hộp.

**Kiểm định kính CHVG (audit3, 48 ô, Hoàng Phương):** bất đồng 3/42 (7,1%) [2,5%; 19,0%], máy nói có 0/7, máy nói không
3/35 (8,6%), **đạt** mốc < 10%; 6 ô người chọn Không rõ. Ba ô bất đồng: hai ô kính bảo hộ **đẩy lên mũ** (Claude: không,
theo định nghĩa "đang đeo trên mắt"; người: có), một ô mờ. Cùng kiểu với ô a014 của lần kiểm định 1 (kính trên trán).
Định nghĩa của project giữ "kính đang đeo trên mắt" (`docs/annotation_rules.md`, quy tắc 6 lớp) cho tới khi người dùng
quyết định khác; đã hỏi người dùng 17/11.

**Người dùng chốt 17/11/2026: giữ định nghĩa "kính đang đeo trên mắt".** Người kiểm định xem lại 4 ô kính bất đồng của
lần 1 và lần 3 (`audit3/recheck_goggles.html`, có ghi định nghĩa, không hiện ý máy; người xem biết đây là ô bất đồng) và
đồng ý với quyết định của Claude cho cả 4 ("ok đồng ý theo bạn", `audit3/recheck_goggles_result.json`). Báo cáo ghi:
kính CHVG lần đầu 3/42 (7,1%), sau xem lại 0/42.

### Phân tích dữ liệu trước khi train C5 (17/11/2026)

`python scripts/04k_c5_data_stats.py` → `outputs/results/c5_eval/data_stats.json`.

**Train C4 và C5** (ảnh chính + bộ phụ; số hộp, không tính bản lặp): cùng 10.632 ảnh. Găng 7.759 → 7.816 (+57), kính
1.258 → 1.259, ủng 2.570 → 2.528 (−42); C5 có thêm khoảng 270 ảnh có vùng che xám (găng / ủng không rõ). **Sửa nhãn train
thay đổi dưới 1% số hộp**: bước B chủ yếu sửa cách đo (val, test), không làm dữ liệu train khác nhiều.

Nguồn hộp train C5: găng SH17 1.958, Construction-PPE mới 1.868, ảnh thu nhỏ 2.458, CHV 695, Construction-PPE cũ 426,
ảnh cắt người 411; **kính 58% (735/1.259) từ Construction-PPE mới** (bộ có ảnh sinh), SH17 230, CHV 115; **ủng 62%
(1.579/2.528) từ Construction-PPE mới**, CHV 344, thu nhỏ 272, SH17 198.

Cỡ hộp (cạnh ngắn sau khi đưa ảnh về imgsz), tỉ lệ < 16 / 16–32 / 32–64 / ≥ 64 px:

| Lớp | @960 | @1280 |
|---|---|---|
| găng | 9,8 / 14,4 / 32,0 / 43,8 % | 5,5 / 11,3 / 23,3 / 59,8 % |
| kính | 2,7 / 24,9 / 51,3 / 21,1 % | 1,0 / 9,5 / 50,7 / 38,9 % |
| ủng | 2,1 / 17,1 / 41,0 / 39,8 % | 0,2 / 9,5 / 29,6 / 60,8 % |

Hộp dưới 32 px ở 960: găng 24%, kính 28%, ủng 19%; ở 1280 còn 17%, 11%, 10%.

**Val, test đã sửa** (hộp / vùng ignore): val găng 864 / 757, kính 29 + CHVG 127 / 61 + 72, ủng 79 / 420; test găng
864 / 681, kính 41 + CHVG 125 / 91 + 67, ủng 92 / 430.

Nhận xét (Claude):
1. Dữ liệu train C5 gần như C4 → C5-s@960 dự kiến xấp xỉ C4; khác biệt chính của lần train này là `imgsz` 1280.
2. Kính, ủng phụ thuộc một nguồn (Construction-PPE mới, có ảnh sinh); thêm nguồn khác (bước C) là đòn bẩy chưa dùng.
3. Vùng ignore nhiều (ủng 420 so với 79 hộp): val ủng chỉ đo trên hộp chắc chắn; số đo ủng không phạt dự đoán ở chỗ
   không rõ.

### Tiêu chí chọn bản C5 (khóa 17/11/2026, người dùng đồng ý, trước khi train C5)

Hai lần train trên cùng dữ liệu C5 (`c5_pack.zip` + `c5_extra_pack.zip`), cùng tham số C4 trừ `imgsz`: **C5-s@960**,
**C5-s@1280**. Chấm bằng `04d` + `04j_c5_eval.py` trên val đã sửa (`data/ppe6/c5/eval/val`), so ghép cặp theo cảnh.
Tham số ở `configs/ppe6.yaml` mục `c5_decision`.

1. **960 hay 1280:** chọn 1280 chỉ khi trung bình mAP50 của găng (tập ppe4), kính, ủng (tập lớp mới) của 1280 cao hơn 960
   **≥ 0,02** và pipeline đầy đủ với detector 1280 đạt **≥ 20 khung/giây, p95 ≤ 100 ms** (`07_benchmark_pipeline.py`);
   không thì chọn 960.
2. **C5 thay C4** khi, với bản chọn ở bước 1: găng và ủng **không thấp hơn C4** (điểm), và người, mũ, áo (tập ppe4) **không
   tụt quá 0,02** so với C4. Kính báo riêng (28 hộp, hoặc tập CHVG nếu kịp kiểm định), không chặn.
3. Test đã sửa chỉ chạy một lần cho bản được chọn. Người dùng quyết định cuối cùng.

### Trạng thái 17/11/2026

Người dùng chạy C5-s@960 và C5-s@1280 song song trên Kaggle (GPU T4 x2, một cell: mỗi bản một GPU qua
`CUDA_VISIBLE_DEVICES`, clone riêng, chỉ đổi `imgsz`, `copy_max_side`), sẽ báo kết quả. **Mục tiêu người dùng giữ: detector
đạt mAP50 ≥ 0,8 cho các PPE.** Lần train này trả lời: 1280 có giúp không, C5 có thay C4 không; nhiều khả năng chưa đủ 0,8
vì dữ liệu train gần như C4 → bước C (thêm dữ liệu) là hướng tiếp theo nếu chưa đạt.

### Kết quả C5 (17/11/2026)

Kaggle, một phiên GPU T4 x2, hai bản song song (log `outputs/train/yolo11s_ppe6_c5_s*/kaggle_train.log`). Lần chạy đầu hỏng
do chọn nhầm gói (`docs/c5_kaggle_run.md`, mục Sự cố). Lần hai: bản 960 dừng sớm ở epoch 72 (best 52, patience 20); bản
1280 chạy hết 53 epoch (Ultralytics co lịch theo `time: 11`), cả hai ghi `Xong`; phiên bị cắt ở 12 giờ khi cell còn
đang chờ in log, sau khi train xong. `04f` đạt cả hai; sha256 best.pt: s960 `aeea881a…bbebe`, s1280 `2dcfb624…53fa4`.
Chấm: `04d` (1280 với `--imgsz 1280`), `04j` → `outputs/results/c5_eval/c5_960_vs_1280.json`, `c4_vs_c5_s960.json`,
`c4_vs_c5_s1280.json`. Val đã sửa, nhãn máy có kiểm định mẫu của người.

| Lớp (tập) | C4 | C5-s960 | C5-s1280 |
|---|---|---|---|
| người (ppe4) | 0,892 | 0,893 | 0,880 |
| mũ (ppe4) | 0,892 | 0,899 | 0,913 |
| áo (ppe4) | 0,778 | 0,783 | 0,781 |
| găng (ppe4) | 0,662 | 0,667 | 0,674 |
| kính (goggles_all, 155) | 0,762 | **0,809** [0,734; 0,872] | 0,702 |
| ủng (lớp mới, 76) | 0,632 | 0,625 [0,480; 0,772] | 0,543 |

**Áp tiêu chí đã khóa:**
1. Trung bình găng, kính, ủng: s960 0,701, s1280 0,640 → 1280 thấp hơn 0,061 (không đạt +0,02) → **chọn 960**. Không
   cần đo tốc độ 1280. 1280 tụt rõ ở kính CHVG (−0,112 [−0,173; −0,060] so với 960) và ủng (−0,082); có thể do 1280 chỉ
   được 53 epoch trong 11 giờ (960: 72 epoch, best 52), chưa kiểm chứng.
2. C5-s960 so với C4: găng +0,006 (không thấp hơn: đạt); **ủng −0,006** [−0,076; +0,077] (thấp hơn C4 về điểm: **không
   đạt** điều kiện "không thấp hơn"); người +0,001, mũ +0,007, áo +0,005 (không tụt quá 0,02: đạt); kính +0,048.
   → Theo tiêu chí đã khóa, **C5 không thay C4**. Mức tụt của ủng nằm trong nhiễu (KTC chứa 0). Người dùng quyết định cuối.
3. Mục tiêu 0,8: chỉ kính đạt (0,809 với C5-s960). Găng 0,667, ủng 0,625 còn xa; hai lớp này cần dữ liệu mới (bước C).

**Người dùng quyết định 17/11/2026: chọn C5-s960 (phương án b, ngoại lệ).** C5 không đạt tiêu chí đã khóa vì ủng tụt
0,006 so với C4 (KTC chứa 0); người dùng chọn C5-s960 sau khi xem kết quả, lý do kính tăng 0,048 lên 0,809, các lớp
khác không tụt có ý nghĩa. Báo cáo phải ghi đúng như vậy. Người dùng yêu cầu tiếp: tìm cách tối ưu để tăng găng, ủng.
`configs/pipeline.yaml` `detector.weights` đổi sang C5-s960; ngưỡng pipeline chọn với C4, cần chạy lại hồi quy video.

## C6: tăng găng, ủng (người dùng chọn 17/11/2026: làm cả hai nhóm)

Phân tích lỗi C5-s960 trên val đã sửa (`04h --run c5s960_val_gloves`, `c5s960_val_boots`):
- Găng: AP 0,667, recall tối đa 0,824; bỏ sót 150 (lệch hộp 81, không thấy 69: găng đen / tối, bị che); báo thừa conf
  ≥ 0,25: 160 (không rõ 77, lệch hộp 43, vật âm 25, trùng lặp 14). Lỗi chia đều, không có một nguyên nhân lớn.
- Ủng: AP 0,625, recall tối đa 0,816 nhưng chỉ 11 báo thừa conf ≥ 0,25 → **ủng đúng có conf thấp** (mô hình chưa tự tin).
  Lệch nguồn: 51/76 hộp ủng val là SH17, train chỉ 198 hộp ủng SH17 (62% ủng train từ Construction-PPE mới).

Kế hoạch C6:
1. **Không cần dữ liệu ngoài:** tìm ủng chưa gán trong hộp `shoes` / `foot` của SH17 train (đề xuất: C5-s960 + bộ phân
   loại chân; Claude xem; người kiểm định mẫu); lặp ảnh có ủng khi train (như găng); tinh chỉnh tiếp từ C5-s960 ở 960.
2. **Bước C, dữ liệu ngoài (chỉ train):** ứng viên Roboflow (người dùng tải, YOLOv8): Safety_shoe / no_safety_shoe
   (Vertical Farming, 1.310 ảnh, CC0, có giày thường làm mẫu âm), Safety Shoes Detection (Nedrick Chandra, 1.693 ảnh,
   CC BY 4.0), Gloves and bare hands (Tejan Mehndiratta, 868 ảnh, giấy phép phải kiểm); CPPE-5 (găng y tế). Mỗi bộ: ghi
   nguồn, giấy phép, sha256 ở `data/raw/<bộ>/README.md`, đổi nhãn theo quy tắc project, lọc trùng ảnh đánh giá, kiểm mẫu.
Tiêu chí chọn bản C6 khóa trước khi train.

### Bước C: dữ liệu ngoài đã tải (17/11/2026, người dùng tải từ Roboflow)

| Thư mục `data/raw/` | Bộ | Giấy phép | Ảnh | Nhận xét (Claude, 24 ảnh mẫu) |
|---|---|---|---|---|
| `safety_shoe_vf/` | Safety_shoe / no_safety_shoe (Vertical Farming) | Public Domain | 1.310 | ủng / giày bảo hộ 2.469 hộp, giày thường 712; nhãn tốt; nhiều ảnh gần trùng; chỉ có nhãn giày |
| `safety_shoes_nc/` | Safety Shoes Detection (Nedrick Chandra, v2) | CC BY 4.0 | 1.693 | safety_shoe 3.763 hộp, miền công trường; nhiều ảnh đã xoay 90°, nhiễu sẵn; chỉ có nhãn giày |
| `gloves_bare_tm/` | Gloves and bare hands detection (Tejan Mehndiratta) | CC BY 4.0 | 868 | tên lớp sai nội dung, hộp găng lớp 0 lệch, ảnh cận trong nhà → ít giá trị, chưa dùng |

Mỗi thư mục có `README.md` (nguồn, bản, sha256 zip, giấy phép, ghi nguồn, kiểm tra). Hai bộ giày chỉ có nhãn giày: dùng
bằng cách **cắt vùng chân** (không để người, mũ, áo không có nhãn thành nền), lọc ảnh gần trùng (pHash) trong bộ và với
ảnh đánh giá, gộp lớp ủng; giày thường là mẫu âm (vùng không nhãn). Xem giày SH17 train (nhóm 1): dừng sau 5/28 bảng
(210 ô: 8 ủng, ≈ 4%), không đáng công. 8 hộp này **không** đưa vào C6 (để dùng lại gói `c5_pack.zip` đã có trên Kaggle,
không phải tải lại 348 MB); ghi lại để biết.

CPPE-5 **không tải** (người dùng đồng ý tải nếu ổn; Claude kiểm 17/11): thẻ dữ liệu Hugging Face ghi giấy phép
"unknown", GitHub chỉ có giấy phép Apache cho code, ảnh từ Flickr / Google Images; không có lớp người. `gloves_bare_tm`
chưa dùng. Găng C6 chỉ dựa vào dữ liệu hiện có.

### C6: dựng dữ liệu (`scripts/03za_c6_external_boots.py`, mục `c6_ext`)

Hai bộ ủng chỉ có nhãn giày, nên không cắt vùng chân như dự định ban đầu (ủng thành rất to so với ảnh thật, lệch cỡ với
val); thay vào đó dùng **nguyên ảnh** và: ủng của bộ → lớp 5; người, mũ, áo → **nhãn máy C5-s960** conf ≥ 0,5, conf
0,25–0,5 che xám; găng, kính dự đoán conf ≥ 0,1 → che xám (không gán nhãn máy cho hai lớp yếu); giày thường → không
nhãn (mẫu âm). Bỏ ảnh xoay sẵn (C5 thấy người hoặc ủng rõ hơn hẳn khi xoay 90°; spec 2.4 cấm xoay góc lớn), ảnh gần trùng
(pHash ≤ 6), và **cả nhóm cảnh** có ảnh gần ảnh đánh giá (pHash ≤ 10).

**Rò rỉ cảnh phát hiện 17/11:** bộ Vertical Farming chứa khung hình cắt từ cùng các video với Construction-PPE cũ
(`Video1`–`Video4`, `image_*`, …; 304 ảnh trùng ảnh đánh giá ở pHash ≤ 6, cùng cảnh sân thượng, cổng). Lọc theo ảnh
không đủ (các khung khác của cùng video vẫn là cùng cảnh) → bỏ cả 14 nhóm tên gốc chạm ảnh đánh giá (đều thuộc
Vertical Farming). Safety Shoes (Nedrick Chandra) không nhóm nào chạm (khoảng cách nhỏ nhất 12–16, mức ngẫu nhiên).

Bộ phụ C6 = bộ phụ C5 + ảnh ủng ngoài; ảnh lặp = găng của C5 (1.413) + mọi ảnh train có ủng (1.052) + ảnh ủng ngoài;
kèm trọng số C5-s960 để tinh chỉnh. Gói `data/ppe6/variants/kaggle/c6_extra_pack.zip`; gói chính vẫn `c5_pack.zip`.

**Số liệu (18/11/2026):** 3.003 ảnh của hai bộ → bỏ nhóm cảnh trùng đánh giá 646, gần trùng 497, xoay (tự động) 239,
không có ủng 166 → 1.455 ảnh; Claude xem toàn bộ 1.455 ảnh (25 bảng `data/ppe6/c6/rotcheck/rot_*`, `.dec` ghi ô bị loại)
và **loại thêm 549 ảnh** (ảnh xoay / lộn ngược mà bộ lọc tự động bỏ sót, ảnh ghép, poster; phần lớn là ảnh stock đã tăng
cường của Safety Shoes) → **906 ảnh** vào train: 2.416 hộp ủng (nc 1.873, vf 543), nhãn máy người 1.305, mũ 487, áo 164.
Ảnh lặp 3.197 (găng C5 1.413 + ảnh có ủng 1.052 + ảnh ủng ngoài 906 − trùng). Gói `c6_extra_pack.zip` 507 MB.
Hướng dẫn Kaggle: `docs/c6_kaggle_run.md`.

### Tiêu chí chọn C6 (khóa 18/11/2026 trước khi train, `configs/ppe6.yaml` mục `c6_decision`)

Hai bản cùng dữ liệu, imgsz 960, song song trên Kaggle T4 x2: **c6_scratch** (từ `yolo11s.pt`, tham số như C5, so được
với C5 về dữ liệu) và **c6_ft** (tinh chỉnh từ C5-s960: 40 epoch, lr0 0,002, warmup 1; Claude đặt). Giữa hai bản: trung
bình mAP50 găng, kính, ủng cao hơn. **C6 thay C5-s960** khi ủng tăng ≥ 0,03 và găng, kính, người, mũ, áo không tụt quá
0,02 (val đã sửa, cùng tập con như C5). Người dùng quyết định cuối.

### Kết quả C6 (18/11/2026)

Kaggle T4 x2, một phiên, hai bản song song (log `outputs/train/yolo11s_ppe6_c6_*/kaggle_train.log`): cả hai ghép đúng
`train 7169, val_monitor 1070`, bộ phụ 4.369 ảnh, 3.197 bản lặp, 14.735 ảnh train. **c6_scratch**: 52 epoch, 6,94 giờ,
dừng sớm (best epoch 32 theo val_monitor). **c6_ft**: 21 epoch, 3,05 giờ, dừng sớm, **best epoch 1** (theo mAP50-95 trên
val_monitor; val_monitor vẫn là nhãn cũ). `04f` đạt cả hai; sha256 best.pt: c6_scratch `575678ca…c6be4`, c6_ft
`881afaa7…8ec8`. Chấm: `04d` + `04j` → `outputs/results/c5_eval/c5_vs_c6_scratch.json`, `c5_vs_c6_ft.json`.

| Lớp (tập) | C5-s960 | c6_scratch | c6_ft | c6_ft − C5 [KTC 95%] |
|---|---|---|---|---|
| người (ppe4) | 0,893 | 0,885 | 0,894 | +0,001 |
| mũ (ppe4) | 0,899 | 0,903 | 0,899 | −0,000 |
| áo (ppe4) | 0,783 | 0,779 | 0,780 | −0,004 |
| găng (ppe4) | 0,667 | 0,655 | 0,657 | −0,010 [−0,023; −0,001] |
| kính (goggles_all, 155) | 0,809 | 0,706 | 0,807 | −0,002 [−0,045; +0,035] |
| ủng (lớp mới, 76) | 0,625 | 0,636 | **0,677** | **+0,051** [−0,018; +0,116] |

**Áp tiêu chí đã khóa (`c6_decision`):**
1. Giữa hai bản C6: trung bình găng, kính, ủng: c6_ft 0,714, c6_scratch 0,666 → **chọn c6_ft**. c6_scratch tụt kính rõ
   (CHVG −0,101 [−0,154; −0,052]).
2. c6_ft so với C5-s960: ủng +0,051 ≥ 0,03 (**đạt**); găng −0,010, kính −0,002, người +0,001, mũ −0,000, áo −0,004, đều
   không tụt quá 0,02 (**đạt**). → **C6 (c6_ft) đạt tiêu chí thay C5-s960.** Người dùng quyết định cuối.
3. Lưu ý khi viết báo cáo: KTC của mức tăng ủng còn chứa 0 (76 hộp); c6_ft tốt nhất ở epoch 1, tức gần như C5 tinh chỉnh
   một epoch với dữ liệu ủng mới; găng giảm nhẹ nhưng KTC không chứa 0. Mục tiêu 0,8: kính 0,807 đạt; găng 0,657, ủng 0,677
   chưa đạt.

**Người dùng đồng ý 18/11/2026 chuyển sang c6_ft** ("cũng được, nhưng tôi vẫn muốn kết quả phải trên 0.8 hết").
`configs/pipeline.yaml` `detector.weights` = `outputs/train/yolo11s_ppe6_c6_ft/weights/best.pt` (sha256
`881afaa7f858d2cf7d95d15335609851574d3a7fd59f900ec5b41b1ad3818ec8`). **Test đã sửa và hồi quy video hoãn tới khi chốt bản
cuối** (người dùng muốn tiếp tục nâng áo, găng, ủng lên 0,8; test chỉ chạy một lần cho bản được chọn cuối cùng).

## C7: nâng áo, găng, ủng lên 0,8 (người dùng yêu cầu 18/11/2026)

### Phân tích lỗi c6_ft trên val đã sửa (`04h --run c6ft_val_ppe4`, `c6ft_val_boots`)

| Lớp | AP50 | Recall tối đa | Chỗ hỏng chính |
|---|---|---|---|
| Áo (ppe4, 620) | 0,780 | 0,852 | **SH17 recall 0,452** (104 hộp; CHV 0,964, Construction-PPE 0,896); hộp < 16 px recall 0,088 (57 hộp); báo thừa 103 (không rõ 50, lệch 30, nhầm lớp 15) |
| Găng (ppe4, 864) | 0,657 | 0,810 | bỏ sót 164 (không thấy 85, lệch hộp 77), < 16 px recall 0,585; báo thừa 146 (không rõ 71, lệch 36, vật âm 26) — chia đều, không có một nguyên nhân lớn |
| Ủng (lớp mới, 76) | 0,677 | **0,934** | ủng gần như tìm đủ; AP bị kéo bởi **báo thừa conf cao** (33: giày thường SH17 14, không rõ 15), có cái conf 0,81 |

**(Claude quan sát)** bảng ảnh: áo bỏ sót tập trung ở một số ảnh SH17 đông người, áo nhỏ ở xa; vài nhãn "vest" của
Construction-PPE cũ là áo giáp quân sự (không phải áo phản quang). Ủng báo thừa: giày thể thao, bốt cổ ngắn có gót, và vài
giày da lao động màu nâu (ca biên theo định nghĩa "ủng / giày bảo hộ nhìn rõ").

### Tốc độ FP16 (`04i`, `speed_check` bản 18/11, `outputs/results/error_analysis/detector_speed_fp16.json`)

| Detector @960 | FP32 ms/khung | FP16 ms/khung (p95) |
|---|---|---|
| s (c6_ft) | 17,02 | 12,49 (15,98) |
| m (COCO, cùng kiến trúc) | 35,34 | **21,73** (22,48) |

Lần đo 17/11 (máy rảnh) m@960 FP32 là 45,05 ms; lần này 35,34 ms (khác nhau, chưa rõ lý do; FP16 đo cùng lượt). Ước lượng
pipeline với m FP16: khoảng 38 − 17 + 22 ≈ 43 ms/khung ≈ 23 FPS → **YOLO11m FP16 có thể đạt mốc ≥ 20 FPS**; phải đo bằng 07
khi có trọng số thật. FP16 phải kiểm trên val (AP gần như không đổi so với FP32) trước khi dùng.

### C7: dữ liệu (người dùng chọn phương án a, 18/11/2026; `scripts/03zb_c7_prep.py`, mục `c7`)

1. **Ủng báo thừa trên train:** c6_ft dự đoán ủng trên 8.132 ảnh train (gốc C5 + ảnh nguyên bộ phụ C6); 589 dự đoán conf ≥ 0,3
   không trùng nhãn ủng. Claude xem 15 bảng (`bootsfp_train_add_*`): **ủng thật thiếu nhãn 63** (thêm nhãn), **giày thường /
   vật khác 216** (giày thể thao, giày da, dép, giày cao gót, ống quần, tay, vật dụng), không rõ 310 (che xám). 270 ảnh sửa.
   **(Claude quan sát)** nhiều ô "không rõ" là giày / bốt da lao động cổ thấp: ca biên của định nghĩa "ủng / giày bảo hộ nhìn
   rõ", che để không học sai chiều nào.
2. **Mẫu âm khó:** 178 ảnh có giày thường bị nhận nhầm, lặp thêm 2 lần.
3. **Áo SH17:** 152 ảnh SH17 train có áo, lặp thêm 1 lần.
4. Ảnh sửa nằm trong bộ phụ **cùng tên** ảnh gốc; `04_train.py add_extra` sửa để ảnh bộ phụ thay ảnh gốc và tên lặp trong
   `oversample.txt` tạo nhiều bản (`rep__`, `rep1__`…), test `tests/test_train_extra.py`. Gói chính `c5_pack.zip` không đổi.
   Gói `data/ppe6/variants/kaggle/c7_extra_pack.zip` (676 MB, oversample 3.705).
5. Găng: không có dữ liệu mới (người dùng chưa trả lời câu hỏi tìm thêm bộ găng).

**Tiêu chí C7 (khóa 18/11/2026 trước khi train, `c7_decision`):** C7-m (YOLO11m COCO, 960, DDP 2 GPU, batch 16) thay c6_ft khi
trung bình mAP50 găng, kính, ủng tăng ≥ 0,02, không lớp nào tụt quá 0,02, FP16 lệch FP32 ≤ 0,005 mỗi lớp trên val (mới được
chạy FP16), và pipeline (07) ≥ 20 khung/giây, p95 ≤ 100 ms. Hướng dẫn: `docs/c7_kaggle_run.md`.

### Kết quả C7-m (19/11/2026)

Kaggle T4 x2, DDP (`device 0,1`, batch 16), log `outputs/train/yolo11m_ppe6_c7/kaggle_train.log`: ghép đúng `train 7169,
val_monitor 1070`, bộ phụ 4.475 ảnh, 3.705 bản lặp, 15.243 ảnh train; **53 epoch, 8,35 giờ, dừng sớm, best epoch 33**.
`04f` đạt; sha256 best.pt `7a8eef5d1efdb94034565cdcf44371604d855840b906d9d517e943287a1ae1ea`. Chấm `04d` (FP32 và `--half`)
+ `04j` → `outputs/results/c5_eval/c6_vs_c7.json`, `c7_fp32_vs_fp16.json`.

| Lớp (tập) | c6_ft | C7-m | C7-m − c6_ft [KTC 95%] |
|---|---|---|---|
| người (ppe4) | 0,894 | 0,897 | +0,004 |
| mũ (ppe4) | 0,899 | 0,898 | −0,000 |
| áo (ppe4) | 0,780 | 0,779 | −0,001 |
| găng (ppe4) | 0,657 | 0,661 | +0,003 [−0,021; +0,028] |
| kính (goggles_all) | 0,807 | 0,774 | −0,033 [−0,104; +0,034] |
| ủng (lớp mới, 76) | 0,677 | 0,620 | −0,057 [−0,149; +0,036] |

FP16 so với FP32 của C7-m: mọi lớp lệch ≤ 0,005 (lớn nhất găng tập lớp mới −0,004) → đạt `half_check`.

**Áp tiêu chí đã khóa (`c7_decision`):** trung bình găng, kính, ủng: C7-m 0,685, c6_ft 0,714 → giảm 0,029 (cần tăng ≥ 0,02):
**không đạt**; ủng −0,057, kính −0,033 tụt quá 0,02: **không đạt**. → **C7-m không thay c6_ft**; hệ thống giữ c6_ft. Không đo
tốc độ 07 cho C7 (đã không đạt điều kiện độ chính xác).

Nhận xét (Claude): qua C4 → C7 (sửa nhãn, 1280, dữ liệu ủng ngoài, mẫu âm khó, mô hình m), **găng nằm yên quanh
0,66 (0,655–0,674), áo quanh 0,78**; mọi khác biệt giữa các bản nằm trong KTC. Mức trần này nhiều khả năng do dữ liệu
(găng nhỏ, bị che, nhập nhằng găng / tay; áo SH17 ở xa) và do tập val nhỏ với ủng (76 hộp), không phải do cỡ mô hình.

## C8: găng lên 0,8 (người dùng yêu cầu 19/11/2026) — chẩn đoán

Trên c6_ft, val đã sửa, ảnh ppe4 (864 hộp găng), tính lại AP găng theo ngưỡng IoU ghép (chẩn đoán, 19/11/2026):

| Nguồn | hộp | AP@0,5 | AP@0,3 | AP@0,1 |
|---|---|---|---|---|
| tất cả | 864 | 0,657 | 0,708 | 0,722 |
| SH17 | 420 | 0,627 | 0,667 | 0,685 |
| CHV | 228 | 0,590 | 0,646 | 0,658 |
| Construction-PPE | 216 | 0,774 | 0,844 | 0,859 |

→ Kể cả chỉ cần hộp chạm găng (IoU 0,1) AP vẫn 0,722: **khoanh lệch chỉ chiếm khoảng 0,06**; phần còn lại là **nhận sai**
(báo găng ở chỗ không có, bỏ sót găng).

**Chấm lại bằng bộ phân loại tay** (`04l_gloves_rescore.py`, `rescore_c6ft_cls_v2.json`, `_v4.json`): AP găng 0,657 → 0,668
(v2, w 0,25) / 0,669 (v4, w 0,25); không đáng kể.

**(Claude quan sát)** bảng báo thừa conf cao của c6_ft (`sheet_gloves_thua_khong_ro.jpg`): khoảng 5–8/40 là găng thật vẫn
chưa có nhãn ở val (găng da, găng trắng, găng hở ngón); còn lại là tay trần, dụng cụ, vật cầm tay, và một số hộp dự đoán
dẹt như một đường kẻ. Nhãn val găng còn thiếu là một giới hạn của phép đo.

### C8: kế hoạch và chỗ dừng (19/11/2026, người dùng chọn phương án a)

Ba việc, train một lần (tinh chỉnh từ c6_ft như C6), tiêu chí khóa trước khi train:
1. **Sửa nốt nhãn găng val, test** theo tiêu chí chặt (hộp bao sát đúng một chiếc găng), có kiểm định của người; ứng viên
   gộp từ dự đoán conf ≥ 0,4 của **mọi** bản C4, C5-s960, C6-ft, C7-m (để không nghiêng về một mô hình); test chỉ chạy
   predict lấy vị trí ứng viên, không tính điểm. Mọi bản được chấm lại trên cùng bộ nhãn mới.
2. **Dữ liệu găng ngoài** (người dùng tải từ Roboflow): Safety Gloves (Roboflow Universe Projects, safety-gloves-xbnf8,
   Gloves / NO-Gloves, CC BY 4.0 theo trang), hand glove (Eshwaran), gloves (Construction Images). Xử lý như C6 (lọc nhóm cảnh
   trùng ảnh đánh giá, ảnh xoay; găng → lớp 3, người / mũ / áo nhãn máy, kính / ủng che).
3. **Mẫu âm khó găng** trên train (găng báo thừa conf ≥ 0,4 của c6_ft, Claude xem: n → lặp 2 lần).

Script `scripts/03zc_c8_gloves.py` (`pred-train`, `pred-test`, `candidates` → `data/ppe6/c5/review_items_c8.csv`, nhiệm vụ
`gloves8_train_add`, `gloves8_eval_add`), mục `c8`. **Dừng 19/11 do hết hạn mức sử dụng tuần của Claude:** đã có danh sách
ứng viên; **chưa** xem bảng ảnh (`03z sheets --task gloves8_train_add` / `gloves8_eval_add`, ghi `.dec`, `collect`), chưa có
bước dựng dữ liệu, gói Kaggle, tiêu chí C8, kiểm định. Hệ thống vẫn dùng c6_ft.

### C8: nhãn găng val, test bản 2 (19–20/11/2026, nhãn máy, CHỜ kiểm định của người)

Claude xem 756 ô (`gloves8_*`, tiêu chí chặt "hộp bao sát đúng một chiếc găng"):

| | găng (g) | không phải (n) | không rõ (u) |
|---|---|---|---|
| train (găng báo thừa c6_ft) | 7 | 170 | 43 |
| val (dự đoán C4–C7 không trùng nhãn) | 17 | 189 | 62 |
| test (vị trí từ predict C4–C7, không tính điểm) | 12 | 188 | 68 |

Gộp với bộ phân loại tay (luật hai lượt): thêm nhãn găng val 12, test 10; vùng ignore mới val 179, test 178 (gồm ô
không rõ, ô Claude nói găng mà bộ phân loại không, ô Claude nói không mà bộ phân loại nói găng). Val, test dựng lại
(`build-eval`); bản trước sao lưu ở scratchpad. **Ignore mới phần lớn rơi đúng chỗ các mô hình báo thừa, nên làm AP găng
tăng mà mô hình không đổi**; báo cáo phải nói rõ.

Chấm lại mọi bản trên val nhãn găng bản 2 (`c8lab_*`, găng tập ppe4, 876 hộp):

| | C4 | C5-s960 | C6-ft | C7-m |
|---|---|---|---|---|
| găng (ppe4) | 0,673 | 0,688 | 0,677 | 0,681 |
| găng (ảnh lớp mới, 352) | 0,531 | 0,558 | 0,551 | 0,520 |

So với nhãn bản 1: C6-ft 0,657 → 0,677 (+0,020, toàn bộ do đổi nhãn đo). Các bản vẫn chênh nhau trong KTC. Còn cách 0,8
khoảng 0,12.

## 3. Điểm cần người dùng quyết định

1. **Kiểm định của người.** Theo CLAUDE.md: nhãn máy phải ghi "nhãn máy, có kiểm định mẫu của người", tầng không đạt kiểm
   định thì không dùng để kết luận. Người dùng không muốn gán tay. Đề xuất: người dùng chỉ **xem một mẫu nhỏ** (vd 100 ô
   ảnh, khoảng 15 phút, bấm đúng/sai) cho mỗi lớp. Nếu không làm: mọi số trên val/test mới phải ghi "nhãn máy, chưa người
   kiểm định", và không được viết là kết luận chắc chắn.
2. **FPS tối thiểu** chấp nhận cho demo camera (để chọn s/m, 960/1280).
3. **Thời gian:** hạn 30/11; B, C, F mỗi bước 1–3 ngày, mỗi lần train nửa ngày đến hơn một ngày Kaggle.
