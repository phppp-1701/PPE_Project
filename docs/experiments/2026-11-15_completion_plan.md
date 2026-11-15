# Kế hoạch hoàn thiện dự án và báo cáo tối 15/11/2026

Người viết: Claude (agent). Mọi mục "đề xuất" dưới đây **chưa được duyệt**, chưa có code, chưa chạy. Số liệu trích ở đây
đều đã chạy thật (nguồn ghi kèm). Kế hoạch chi tiết từng bước vẫn ở `2026-11-06_ppe6_plan.md`.

## 0. Báo cáo tối 15/11 (đọc phần này trước)

**Đã làm hôm nay**

| Việc | Kết quả | Nguồn |
|---|---|---|
| Tắt B lần 1 (phương án 2) | 13 video: `frames.csv` trùng từng byte bản 4, sự kiện giống | plan mục B, `stepB/off13` |
| Bảo vệ nhãn holdout | `c80404f` thay bằng `0e65786` (bỏ 3 file spec chi tiết), sao lưu + SHA-256 khớp manifest; đã push | plan mục B2 |
| Push | `exp/ppe6` = `0e65786` trên GitHub; `main` không đổi (`cd3fa14`) | `git log` |
| B2 (vùng thân bản chặt) | Code + 24 test, 165 test qua; hiệu chuẩn val chạy một lần: V1-V4 đạt theo tiêu chí, **nhưng** V3 không phân biệt được và `edge_px` = 283 px không dùng được cho video | plan "Kết quả B2 trên val", `outputs/results/pipeline_calib_val/torso_strict.json` |

**Chưa làm, cố ý:** không bật B2, không chạy video, không đụng holdout, không commit B/B2, không bắt đầu C, D (cần bạn
duyệt tiêu chí trước, theo luật đã đặt).

**Trạng thái Git khi tắt máy:** nhánh `exp/ppe6`, HEAD = remote = `0e65786`. Chưa commit (giữ nguyên trên đĩa):
`configs/pipeline.yaml`, `docs/experiments/2026-11-06_ppe6_plan.md`, `scripts/05a_calibrate_val.py`,
`scripts/README.md`, `src/ppe/association.py`, `src/ppe/pipeline.py`, `tests/README.md`, mới: `tests/test_torso_pose.py`,
`tests/test_torso_strict.py`, file này. Bản sao phòng hờ: `D:\KhoaLuan\backup\wip_20261115\` (patch + file mới + sha256).

**Real-time:** `docs/spec.md` không đặt mức FPS (NFR-01 chỉ yêu cầu đo và nêu phạm vi). Đo thật (07 benchmark, video
3-6, RTX 3050, `close_eval/benchmark/benchmark.md`): bản 4: 23,07 ± 0,84 FPS xử lý, 20,51 ± 0,67 FPS gồm giải mã
video; cấu hình trước bản 4 (không bộ phân loại mũ): 26,13 và 22,97 FPS. Chưa
theo kịp video 25-30 FPS từng khung; giám sát trực tiếp được nếu bỏ bớt khung (cảnh báo cần nhiều giây mới xác nhận).
Không được ghi "đạt 25-30 FPS".

## 1. Dự án cần kết quả gì để hoàn thiện (theo `docs/spec.md`)

| Câu hỏi | Cần có | Hiện có | Còn thiếu |
|---|---|---|---|
| RQ1 phát hiện | P, R, F1, AP, mAP từng lớp trên test nội bộ và Pictor-PPE; thời gian suy luận | Có (C4, `2026-11-12_c4_official_test_and_ablation.md`) | Cập nhật vào báo cáo 6 lớp |
| RQ2 gán PPE, trạng thái | Ma trận 3x3, P/R/F1 từng trạng thái, macro-F1 trên video kiểm thử | Chỉ trên video phát triển (nhãn máy) | **Đánh giá cuối một lần trên holdout** |
| RQ3 theo dõi, cảnh báo | Event P/R/F1 khi có nhãn sự kiện; A-E | Ablation A-E có; holdout không có nhãn sự kiện | Ghi rõ "không có Event F1" cho holdout, hoặc gán nhãn sự kiện (quyết định) |
| RQ4 hệ thống | Bảng FR-01…10 Đạt/Không đạt/Chưa kiểm thử kèm bằng chứng; FPS, p50/p95, CPU/GPU/RAM | FPS, p50/p95 có (07); backend, dashboard có | **Bảng FR-01…10 có bằng chứng** |

Hoàn thiện = mỗi ô trên có số đo thật hoặc ghi "chưa kiểm thử" có lý do; báo cáo nêu đúng giới hạn. Không cần mọi
lỗi đều hết, cần lỗi còn lại được đo và nói rõ.

## 2. Vấn đề tồn đọng

| # | Vấn đề | Ví dụ | Nguyên nhân (chẩn đoán đã chạy) | Hướng |
|---|---|---|---|---|
| P1 | Người bị cắt ở ngực có áo nhưng báo Thiếu | video9, video10 | Tâm áo ngoài vùng thân cố định | B2: chờ quyết định (mục 3.1) |
| P2 | Đầu trọc báo **Có mũ** (nghiêm trọng) | video13 f108, f240 | Detector có hộp mũ (0,60; 0,58); bộ phân loại mũ chắc không có mũ (p 0,12; 0,04) nhưng mũ không trong `veto` | C (mục 3.2) |
| P3 | Quay lưng mà báo Thiếu kính | video16 f455 | Vai ngược nhưng độ tin cậy 0,49 / 0,45 < 0,5 nên không nhận là quay lưng; pose còn đoán mặt sau gáy (mũi 0,89) | D (mục 3.3) |
| P4 | Mũ tối nhìn từ sau báo Thiếu | video17 f345 | Detector không thấy; bộ phân loại mũ p 0,002; vai ngược rõ (0,99) | D giảm thành Chưa xác định; sửa tận gốc cần E |
| P5 | Kính trong (ảnh trắng đen) báo Thiếu | video13 f194 | Detector không thấy; bộ phân loại kính p 0,20 | E (dữ liệu) |
| P6 | Tốc độ dưới 25 FPS | | Bộ phân loại mũ bản 4 tốn khoảng 12% | Mục 3.6 |
| P7 | `05d`, `06_evaluate_ablation` không truyền `frame_shape` | | B2 tắt trong hai script đó nếu bật | Sửa nếu giữ B2 |
| P8 | Nhãn video là nhãn máy, chưa người kiểm định | holdout, kiem_thu_gan | Quy trình đã chọn | Kiểm định mẫu (mục 3.5) |
| P9 | Báo cáo, spec còn ghi 4 lớp | | Đổi hướng 09/11 | Người dùng sửa (mục 3.7) |
| P10 | Holdout ít ủng (không có khung Có), ít găng | `labels/label_counts.json` | Video có sẵn trên mạng | Báo là giới hạn |

## 3. Kế hoạch (đề xuất, chờ duyệt từng mục)

### 3.1 B2: chọn một (16/11)
- (a) **Dừng B2** (đề xuất của agent nếu thiếu thời gian): giữ bản 4 cho áo; P1 thành giới hạn có số đo.
- (b) Thiết kế lại rồi chạy lại val: `edge` theo tỉ lệ chiều cao khung (hoặc chỉ chọn từ ảnh độ phân giải gần video);
  V3 tạo tình huống chồng hộp (vd đặt hộp người khác phủ tâm áo). Ghi tiêu chí trước. Lưu ý: kết quả lần 1 đã được xem.
- (c) Chạy video với tham số hiện tại: agent không khuyên (G4 gần như không lọc).
- Dù chọn gì: commit code B1, B2 ở trạng thái tắt (cấu hình không có `torso_pose`, `torso_strict`) để giữ lịch sử.

### 3.2 C: phủ quyết mũ khi nhìn thẳng (P2)
- **Quy tắc đề xuất:** thêm phủ quyết cho mũ chỉ khi **nhìn thẳng chắc chắn**: mũi và hai mắt >= `kp_conf`, hai vai
  >= `kp_conf` và **không** ngược (vai trái COCO ở bên phải ảnh). Khi đó phiếu `neg` của bộ phân loại mũ bỏ hộp mũ của
  detector -> Thiếu (nếu vùng quan sát được). Không nhìn thẳng chắc: như bản 4 (hộp detector thắng).
- **Chọn, kiểm trên val ảnh** (ppe4 val, nhãn mũ và người thật, pose như pipeline; không dùng video):
  - V-C1 người đội mũ (nhãn), nhìn thẳng theo quy tắc, có hộp mũ: tỉ lệ bị phủ quyết nhầm (mũ thật bị bỏ). Đề xuất
    ngưỡng chấp nhận <= 2%.
  - V-C2 người không đội mũ (nhãn) nhìn thẳng mà detector có hộp mũ (Có sai): tỉ lệ phủ quyết được. Báo số, không đặt
    mốc (val có thể ít ca).
  - `t_neg` mũ giữ 0,50 (bản 4), không chọn lại.
- **Hồi quy 13 video** (không chọn tham số): mũ Có sai không tăng; mũ báo Thiếu sai không tăng quá 0 khung (mốc đề xuất,
  chờ duyệt); áo, găng, kính, ủng giống từng khung; liệt kê khác biệt sự kiện.
- **Test:** nhìn thẳng + neg + có hộp -> Thiếu; không nhìn thẳng -> như bản 4; vai ngược -> như bản 4; thiếu điểm mặt
  -> như bản 4; chỉ mũ thay đổi.
- **Rủi ro:** bộ phân loại mũ bản 4 từng sai mạnh với mũ tối (video17); nếu sai cả khi nhìn thẳng thì C gây Thiếu sai.
  V-C1 đo đúng rủi ro này.

### 3.3 D: nhận ra quay lưng chắc hơn (P3, P4)
- **Quy tắc đề xuất:** "quay lưng" khi hai vai ngược với độ tin cậy >= `kp_back` (thấp hơn 0,5), hoặc track đã quay
  lưng trong `back_hold_s` giây gần nhất (giữ theo thời gian, chống nhảy khung). Khi quay lưng: kính Chưa xác định (như
  hiện tại nhưng bắt được nhiều ca hơn); mũ: không có hộp detector thì **Chưa xác định** thay vì Thiếu (không tin phiếu
  `neg` từ phía sau); có hộp thì Có như cũ.
- **Cần quyết định:** val ảnh không có nhãn hướng người, nên `kp_back`, `back_hold_s` chưa chọn được trên val. Cách:
  (i) người gán nhãn hướng (trước / sau / nghiêng) cho khoảng 200 người ở val (không dùng video); hoặc (ii) dùng
  `kp_back` = 0,3 như quy ước, báo là "chưa chọn trên val". Agent không tự đặt.
- **Đánh đổi biết trước:** người quay lưng thật sự không đội mũ sẽ thành Chưa xác định (mất cảnh báo từ phía sau).
- **Hồi quy 13 video:** kính và mũ báo Thiếu sai giảm hoặc giữ; mũ Có sai không tăng; số khung Thiếu đúng bị chuyển
  thành Chưa xác định: báo số; áo, găng, ủng giống từng khung.

### 3.4 E: dữ liệu và train lại (hoãn)
- Chỉ làm nếu còn thời gian sau khi chốt bản cuối (hạn 30/11). Cần: mũ tối nhìn từ sau, đầu trọc (mẫu âm), kính trong;
  train trên Kaggle (ultralytics 8.4.189), không dùng video. Nếu không làm: P4, P5 ghi là giới hạn có số đo.

### 3.5 Đóng băng bản cuối và đánh giá cuối (sau B2/C/D)
1. Đóng băng như bản 4: commit nguồn -> `manifest.json` (sha256 cấu hình, trọng số, script, video) -> commit manifest.
2. Kiểm định mẫu nhãn holdout bởi người (đề xuất: 10% khung mỗi video, chọn ngẫu nhiên có seed, trước khi chạy hệ
   thống). Nếu không làm: mọi số holdout ghi "nhãn máy qua hai lượt, chưa người kiểm định".
3. Chạy **một lần** bản cuối trên holdout bằng `06b` (khi người dùng cho phép): ma trận 3x3, P/R/F1 từng trạng thái,
   macro-F1 từng PPE; báo cả bản 4 đóng băng để so. Không chỉnh gì sau khi xem.
4. `07` benchmark bản cuối: FPS xử lý, toàn luồng, p50/p95 từng bước, GPU/RAM.
5. Bảng FR-01…10 kèm bằng chứng (lệnh, file kết quả, ảnh chụp dashboard).

### 3.6 Tốc độ (P6)
- Phương án (mỗi phương án đổi kết quả nhận diện thì phải đo lại cả độ chính xác, là quyết định của người dùng):
  suy luận FP16 nếu chưa bật; bộ phân loại chạy cách khung (vd 2 khung một lần) vì đã gộp phiếu theo `vote_window_s`;
  bỏ bộ phân loại mũ bản 4 nếu C/D không cần nó; bỏ bớt khung đầu vào khi giám sát trực tiếp.
- Báo cáo ghi số đo thật, phạm vi đo (video 3-6, RTX 3050, imgsz 960), không tuyên bố 25-30 FPS.

### 3.7 Báo cáo và tài liệu
- Sửa báo cáo và `docs/spec.md` sang 6 lớp (người dùng); ghi: C2 không đạt tiêu chí, đổi bản chính là quyết định
  của người dùng sau khi thấy kết quả; mũ bản 4 là ngoại lệ (bỏ sót video3 58 -> 60); B1 không đạt và đã tắt; nhãn
  video là nhãn máy; video kiem_thu_gan đã thành video phát triển sau 14/11.
- Gộp `exp/ppe6` vào `main` khi người dùng đồng ý.
- Rà mục "Việc còn lại" cũ của `2026-11-06_ppe6_plan.md` (mức 80 hộp ủng, gói `audit`, `03i`, ngưỡng người đủ lớn,
  `04d`/`04e`, Kaggle): đánh dấu đã xong hoặc bỏ.

## 4. Lịch đề xuất (hạn theo README: bước 3-4 trước 19/11, bước 5 đến 24/11, bước 6 đến 30/11)

| Ngày | Việc |
|---|---|
| 16/11 | Quyết định B2; commit B/B2 tắt; duyệt tiêu chí C |
| 16-17/11 | C: val, code, test, hồi quy; báo |
| 17-18/11 | D: quyết định nhãn hướng; val, code, test, hồi quy; báo |
| 19/11 | Đóng băng bản cuối; bảng FR-01…10 |
| 20-21/11 | Kiểm định mẫu nhãn holdout (nếu làm); đánh giá cuối một lần; benchmark |
| 22-24/11 | Viết kết quả RQ1-RQ4; E nếu còn thời gian |
| 24-30/11 | Sửa báo cáo 6 lớp, giới hạn, gộp nhánh |

## 5. Quyết định cần từ bạn (sáng 16/11)

1. B2: (a) dừng / (b) thiết kế lại / (c) chạy video.
2. Cho commit code B1, B2 ở trạng thái tắt.
3. Duyệt quy tắc và tiêu chí C (mục 3.2), đặc biệt mốc V-C1 <= 2% và "mũ Thiếu sai không tăng".
4. D: cách chọn `kp_back`, `back_hold_s` (gán nhãn hướng trên val hay để quy ước có ghi chú).
5. Có kiểm định mẫu nhãn holdout bởi người trước đánh giá cuối không.
6. Có làm E không, hay ghi P4, P5 là giới hạn.
