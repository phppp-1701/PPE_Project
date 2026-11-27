# Sửa "Chưa xác định" sai của áo — 27/11/2026

Viết trước khi chạy. Người dùng giao (27/11/2026): tối ưu "Chưa xác định" (CXĐ); đồng ý hướng đề xuất: sửa áo theo
ngoại lệ, mũ ghi vào Hạn chế.

## Chẩn đoán (đã chạy, `outputs/results/close_eval/diag_unknown/`, `scripts/06d_diagnose_unknown.py`)

Chỉ video chỉnh tham số 3-6 (nhãn người) và `kiem_thu_gan` 9-17 (nhãn máy, chỉ đo). Không chạy holdout.

- Holdout (đọc số đếm có sẵn `final2/holdout_check`, không dò lý do): CXĐ của găng, kính, ủng đúng với nhãn 0,92 / 0,90 /
  0,99; của mũ 0,26, áo 0,33.
- **Áo** (nhãn Có → CXĐ): 258 khung có hộp áo trong hộp người nhưng bị loại `outside` (tâm áo ngoài vùng thân cố định);
  188 trong đó người chạm mép dưới khung (đứng gần, bị cắt). Lỗi ở luật gán.
- **Mũ** (nhãn Có → CXĐ): quay lưng (D) 28 + 333 (video17, bộ phân loại vùng đầu phiếu `neg` sai), cổng khung xương 140
  (video4, người xa); detector không có hộp mũ. Bỏ luật sẽ thành báo thiếu oan; gốc ở detector → **Hạn chế**, không sửa.

## Thay đổi thử (V)

Bật `association.torso_strict` với đúng tham số F2 đã chọn trên val ngày 16/11/2026
(`outputs/results/pipeline_calib_val/assoc_pose.json`, `tham_so.F2`): `kp_conf 0.5, kx 1.259, ky0 -0.297, kh 0.123,
slope_max_deg 48.3, s_min 1.116, edge_frac 0.112`. Không chọn lại tham số.

**Đã biết trước (val 16/11):** F2 không đạt tiêu chí V3b (gán nhầm áo người phía sau bị bỏ sót 18 → 19 ở cắt 55%,
20 → 21 ở cắt 65%). Nếu bật là **ngoại lệ người dùng duyệt** (27/11/2026), ghi rõ trong báo cáo.

## Tiêu chí (khóa trước khi chạy)

Hồi quy video3-6 (nhãn người, `06b evaluate`, mốc = `configs/pipeline.yaml` hiện tại, `28ad782` + chẩn đoán):

1. Áo: "Có đúng" tăng.
2. Áo: "báo Có sai" không tăng; "báo Thiếu oan" không tăng.
3. Mũ, găng, kính, ủng: mọi số không đổi (V chỉ chạm áo).
4. Sự kiện: số sự kiện mỗi video không đổi, hoặc chỉ bớt mục áo của sự kiện ứng với khung nhãn Có áo.

Đạt cả 4 → bật V trong `configs/pipeline.yaml`, chạy lại holdout (ghi "kiểm tra sau sửa, không mù"; số chính thức vẫn
16/11) và `kiem_thu_gan` 9-17 (chỉ báo cáo). Không đạt → không bật, ghi Hạn chế.

## Kết quả V (27/11/2026): không đổi gì

`outputs/results/close_eval/stepV/dev36/`: mọi số, mọi PPE, mọi sự kiện video3-6 giống hệt bản hiện tại → không bật.
Thăm dò (scratchpad, video3-5, chỉ đọc): hộp áo bị loại `outside` đều do **lệch ngang** (u trung vị 0,29 video4; 0,73
video5; 0,76 video3; vùng thân x 0,309-0,665), chiều dọc đúng. Xem ảnh: hộp người bị **tay dang ra** kéo rộng (bắt tay,
ngồi xổm vươn tay), vùng thân theo tỉ lệ nằm giữa hộp nên lệch khỏi thân thật. B2 cố ý không nới ngang nên không có tác dụng.

## V2 — vùng thân đặt theo hai vai (ghi trước khi code và chạy)

`association.torso_shift {kp_conf, kx}`: khi `shoulder_geometry` (hai vai >= kp_conf, vai trong hộp người, hông thấp hơn
vai nếu thấy) hợp lệ, thêm vùng R: ngang [mx - kx·sw, mx + kx·sw] (mx trung điểm vai, sw bề rộng vai), dọc giữ như vùng
thân cũ, cắt theo hộp người; tâm áo trong vùng cũ hoặc R đều là ứng viên (khoảng cách chuẩn hóa nhỏ hơn được lấy). Tham số:
`kp_conf 0.5`, `kx 1.259` (= `kx` của B2/F2 chọn trên val 15-16/11/2026). Không chọn tham số mới.

Tiêu chí V2 (khóa): như tiêu chí 1-4 ở trên trên video3-6 (nhãn người), thêm (5) "Có mới trên người không có nhãn" của áo
không tăng (chặn gán áo cho người không có trong nhãn). Chưa đo V3b trên val (chưa có chế độ 05a cho V2; ghi rõ là giới hạn).
Đạt → bật, chạy lại holdout ("kiểm tra sau sửa, không mù") và 9-17 (chỉ báo cáo).

## Kết quả V2 (27/11/2026), `outputs/results/close_eval/stepV/dev36_V2/`

| Áo, video3-6 | base | V2 |
|---|---|---|
| Có đúng / 2.630 | 2.430 | **2.506** |
| Thiếu đúng / 1.043 | 1.002 | 1.001 |
| Báo thiếu oan | 48 | 47 |
| Báo Có sai | 3 | **4** |
| Có → CXĐ | 114 | **39** |

Theo video: video4 Có→CXĐ 34 → 5, video5 66 → 20, video3 +1 Có đúng, video6 không đổi. Mũ, găng, kính, ủng giống hệt.
Sự kiện: số sự kiện giống ở cả 4 video; video3 #5 chỉ lệch mốc bỏ mục áo trong `missing_history` 39,840 → 39,806 s.
Có mới trên người không có nhãn: 0.

Áp tiêu chí: (1) đạt; (2) **không đạt**: báo Có sai 3 → 4 (một khung, video3 f1152, nhãn người 5 không áo nhận Có;
cùng khung người 6 có áo từ Thiếu oan thành Có đúng; đây cũng là khung đã làm B1 không đạt 15/11); báo thiếu oan đạt;
(3) đạt; (4) đạt; (5) đạt. → Theo tiêu chí đã khóa: **không đạt**, chờ người dùng quyết định (ngoại lệ hay không).

Người dùng (27/11/2026): không bật V2, "phân tích và tìm phương án khác để cải thiện".

## V3 — V2 thêm cổng cỡ áo (ghi trước khi code và chạy)

Phân tích (scratchpad, chỉ đọc, video3-5 chỉnh tham số): f1152 video3 hộp người 5 gộp hai người (người trước không áo,
người sau có áo không được phát hiện riêng); hai "vai" thuộc hai người nên sw phình: rộng áo / sw 0,90, sw / rộng hộp
người 0,67. 79 áo V2 ghép đúng (video4, 5): rộng áo / sw 1,46-2,90 (p5-p95), sw / rộng hộp 0,24-0,41.

V3: như V2, chỉ dùng vùng theo vai khi rộng hộp áo >= `s_min` x sw, `s_min` 1,116 = cổng cỡ áo G5 của B2 chọn trên val
15/11/2026 (`pipeline_calib_val/torso_strict.json`). Không chọn ngưỡng mới. Tiêu chí: như V2 (1-5), video3-6.

## Kết quả V3 (27/11/2026)

**Video3-6** (`stepV/dev36_V3`, tiêu chí khóa): áo Có đúng 2.430 → 2.505, Có→CXĐ 114 → 39, báo Có sai 3 → 3, báo thiếu
oan 48 → 48; mũ, găng, kính, ủng, sự kiện giống hệt; Có mới trên người không nhãn 0. **Đạt cả 5** → bật trong
`configs/pipeline.yaml` (27/11/2026).

**Holdout — kiểm tra sau sửa, KHÔNG còn mù** (`close_eval/final3/holdout_check`, nhãn máy hai lượt chưa người kiểm định;
số chính thức vẫn 16/11): chỉ áo đổi.

| Áo, 8 video | final2 | final3 (V3) |
|---|---|---|
| Có đúng / 1.565 | 743 | **1.061** |
| Thiếu đúng / 809 | 778 | 778 |
| Báo thiếu oan | 351 | **119** |
| Báo Có sai | 2 | 2 |
| Có → CXĐ | 457 | 371 |
| Độ đúng (Có đúng + Thiếu đúng) / (nhãn Có + Thiếu) | 0,641 | **0,775** |
| Coverage trên khung nhãn Có/Thiếu | 0,789 | **0,826** |
| Đúng khi đã kết luận | 0,812 | **0,938** |

Sự kiện: 7/8 video giống; h4 bớt một sự kiện thiếu áo của người 1 (nhãn Có áo cả video; báo thiếu oan h4 232 → 0).
Có mới trên người không nhãn 0.

**kiem_thu_gan 9-17** (chỉ đo, `close_eval/final3/kiem_thu_gan`): áo Có đúng 1.237 → 1.311, báo thiếu oan 466 → 420,
Có sai 0 → 0, CXĐ 213 → 185; video15 bớt một sự kiện thiếu áo báo oan (báo thiếu oan 48 → 2); video15 có 4 khung Có áo
mới trên người không có nhãn (chưa xem). Các PPE khác giống hệt.

Chưa đo lại tốc độ (V3 chỉ thêm phép so hình học cho áo, không thêm mô hình). Mũ: ghi Hạn chế (gốc ở detector).

# Đợt 2 (người dùng giao 27/11/2026: nâng RQ2 mũ, găng; giải quyết RQ3; chọn làm cả 0-6 kể cả M2)

## Bước 0 (xong): sửa phép chấm E trong `06_evaluate_ablation.py`

E trước đây chỉ so món PPE (không xét người, thời gian) trong khi A-D xét người - PPE - khoảng thời gian. Sửa: E dùng
cùng `evaluate_alerts` với A-D (người của sự kiện lấy từ hộp người lúc sự kiện được tạo). `final3/ablation.json` (cấu
hình có V3): E 11 cảnh báo, TP 10, sai 1, trùng 0, FN 2, P 0,909, R 0,833, **Event F1 0,870** (chấm cũ 0,957). Video4:
một cảnh báo gán nhầm người, hai vi phạm bị sót.

## M1 — mũ vào lượt zoom (ghi trước khi chạy)

Thêm lớp 1 (mũ) vào `detector.zoom.classes` (và `crop_pass.classes` khi chấm val). Không thêm lượt mô hình (crop đã dò
mọi lớp rồi lọc). Tham số zoom khác giữ nguyên.

Tiêu chí (khóa):
1. Val (04m `--classes 1 3 4 5` so với `3 4 5`, chấm 04j): mũ mAP50 trên ppe4 val không giảm quá 0,005; mũ trên val_new
   không giảm quá 0,02 (ít hộp); các lớp khác giữ nguyên.
2. Video3-6 (06b, nhãn người): mũ báo Có sai không tăng, báo thiếu oan không tăng; mũ Có đúng + Thiếu đúng không giảm;
   các PPE khác không đổi; số sự kiện không tăng.
Đạt cả hai → bật. Test không chạy lại (đã dùng một lần; zoom có mũ chưa có số test, ghi rõ).

## G1 — găng: một tay Có, tay kia không có bằng chứng tay trần → Có (ghi trước khi code và chạy)

Chẩn đoán (`diag_unknown`, video3-6 nhãn người): găng nhãn Có → CXĐ chủ yếu là một tay đã có hộp găng gán đúng (`gan_minh`)
còn tay kia CXĐ (bộ phân loại phân vân 54, ngoài khung 22, tranh chấp 10). Luật gộp hai tay hiện tại: có tay Thiếu → Thiếu;
mọi tay Có → Có; còn lại CXĐ. Nhãn Thiếu → CXĐ chủ yếu không thấy cổ tay (176) hoặc bị che: đúng là không quan sát được,
không sửa.

G1 (`compliance.gloves_any_have: true`): gộp hai tay — có tay Thiếu → Thiếu (như cũ); ngược lại có ít nhất một tay Có → Có;
còn lại CXĐ. Rủi ro: người chỉ đeo một găng, tay trần không nhìn rõ → báo Có sai.

Tiêu chí (khóa), video3-6 nhãn người (06b, mốc = cấu hình hiện tại):
1. Găng Có đúng tăng.
2. Găng báo Có sai tăng không quá 1% số khung nhãn Thiếu găng (2.072 → tối đa +20 khung); báo thiếu oan không tăng.
3. Các PPE khác không đổi; số sự kiện không tăng.

### Kết quả M1 (28/11/2026)

Val (`c5_eval/m1_crop_helmet_val`): mũ ppe4 0,8985 → 0,8983 (−0,0002), val_new 0,708 → 0,723 (+0,015); lớp khác giữ nguyên.
Video3-6 (`close_eval/stepM1z/dev36`): mũ Có đúng 2.914 → 2.916, báo thiếu oan 13 → 11, báo Có sai 23 → 23; PPE khác,
sự kiện giống hệt. **Đạt** → bật `detector.zoom.classes: [1, 3, 4, 5]`. Không thêm lượt mô hình. G1 chạy trên nền đã có M1.

### Kết quả G1 (28/11/2026): không đạt, không bật

Video3-6 (`close_eval/stepG1/dev36`, nền có M1): găng Có đúng 754 → 866, Có→CXĐ 150 → 38, nhưng **báo Có sai 1 → 58**
(video3 +30, video5 +27; mức cho phép +20) và 7 khung Có găng mới trên người không có nhãn. Nguyên nhân: người tay trần có
một tay bị detector nhận nhầm là găng, tay kia không quan sát được → G1 kết luận Có. Theo tiêu chí khóa: không đạt, không bật.
Code giữ (khóa vắng = như cũ). Ghi Hạn chế: găng cần thấy cả hai tay.

## M2' — bộ phân loại vùng đầu bản 5 cho mũ, giữ luật D (ghi trước khi chạy, 28/11/2026)

M2 (train lại bộ phân loại đầu với ảnh nhìn từ sau) đã làm 16/11 (`2026-11-16_post_holdout_fixes.md`, bản 5): mũ nhìn từ
sau cho là có mũ 87,4% → 94,0% (sáng), 67,6% → 91,9% (tối) trên tập kiểm riêng; **không đạt V-B1** (mũ nhìn từ sau bị cho
là không mũ 4,6% > 2%) nên không bật. V-B1 bảo vệ việc *báo Thiếu từ phía sau*; luật D vẫn chặn việc đó. Nên M2': đổi
`part_cls.weights_by_ppe.helmet` sang bản 5, **giữ D**; bản 5 chỉ giúp thêm "Có" khi nhìn từ sau, và ở phía trước (C2).

Ngưỡng: chọn lại trên val cho bản 5 bằng `05e --weights <v5> --out val_select_v5.json` (cùng luật chọn như v4: t_pos,
t_neg theo `precision_target`); C2 (`veto_frontal.helmet`) chọn lại bằng `05e --helmet-veto2` với bản 5 nếu khác v4.
Không chọn trên video.

Tiêu chí (khóa): (1) val: V-B2, V-B3 bản 5 đạt (đã đo 16/11: đạt); (2) video3-6 (06b, nhãn người, nền hiện tại M1+V3):
mũ báo Có sai không tăng, báo thiếu oan không tăng, mũ Có đúng không giảm; PPE khác không đổi; số sự kiện không tăng.

### Kết quả M2' (28/11/2026): đạt, bật

Val: ngưỡng bản 5 `val_select_v5.json` (mũ t_pos 0,94, t_neg 0,50; đầu s 1,0); C2 chọn lại với bản 5
(`helmet_veto2_val_v5.json`) ra cùng t_veto 0,7, face_conf 0,7 (V-C1 0,74%, V-C3 0,37%). Video3-6 (`stepM2/dev36`): mũ Có
đúng 2.916 → 2.921, Có→CXĐ 202 → 197, báo Có sai 23 → 23, báo thiếu oan 11 → 11; PPE khác, sự kiện giống hệt. **Đạt** →
bật (`weights_by_ppe.helmet` bản 5, `geometry.head.s` 1,0, `thresholds.helmet.t_pos` 0,94). Luật D giữ nguyên.

## Cấu hình cuối 3 (đóng băng 28/11/2026)

Bản cuối 2 (`28ad782`) + V3 (áo theo vai) + M1 (mũ vào zoom) + M2' (bộ phân loại đầu bản 5). G1 không bật. Sau mốc này
chạy một lần: event_eval (RQ3), holdout và kiem_thu_gan 9-17 (kiểm tra sau sửa, không mù), ablation video4-6 (chấm E
đã sửa), tốc độ (07). Không sửa code, cấu hình trong lúc chạy.

## Kết quả đánh giá cuối 3 (28/11/2026, cấu hình `5d7acec`, chạy một lần; máy restart giữa chừng: event_eval và holdout đã
xong trước, phần còn lại chạy tiếp bằng `final4/run_rest.sh`, chưa xem kết quả nào trước khi chạy xong)

**RQ3 — tập độc lập event_eval** (`outputs/results/event_eval/final4/event_eval.json`; 7 video, 10 sự kiện chuẩn, nhãn máy
hai lượt, người dùng kiểm định 11 Đúng / 0 Sai / 1 Không chắc):

| | Cảnh báo | TP | Sai | Trùng | Ngoài nhãn | FN | P | R | **Event F1** | Trễ TB |
|---|---|---|---|---|---|---|---|---|---|---|
| E, chặt | 21 | 8 | 5 | 0 | 8 | 2 | 0,615 | 0,80 | **0,696** | 0,64 s |
| E, theo kiểm định | 21 | 9 | 4 | 0 | 8 | 1 | 0,692 | 0,90 | **0,783** | 0,60 s |
| Theo khung, chặt | 6.508 | 9 | 663 | 4.445 | 1.391 | 1 | 0,002 | 0,90 | 0,004 | |

KTC 95% (bootstrap theo video): E F1 chặt [0,400; 0,952], hiệu E − theo khung [0,397; 0,948] (không chứa 0); theo kiểm
định E F1 [0,609; 1,000]. Recall E thấp hơn theo khung 10 điểm (một sự kiện trên 10). Lỗi tập trung ở e3 (0 TP chặt: hai
người nhìn từ sau, sự kiện chuẩn chỉ có kính/găng) và e7 (2 cảnh báo cho người tiền cảnh mờ mà nhãn để không sự kiện).
"Ngoài nhãn" = cảnh báo trên người không ghép được hộp nhãn (không tính sai, báo riêng).

**RQ3 số phụ — holdout** (`final4/holdout_events.json`, không mù, nhãn máy chưa kiểm định, 7 sự kiện suy từ nhãn khung):
E F1 0,667 (P 0,625, R 0,714) [0,286; 0,933]; theo khung 0,005; hiệu [0,281; 0,929].

**Ablation video4-6** (chấm E đã sửa): E F1 0,870 (P 0,909, R 0,833), A 0,0045 — như `final3`.

**RQ2 — holdout, kiểm tra sau sửa, không mù** (`final4/holdout_check`): mũ Có đúng 1.704 → 1.755, Có→CXĐ 655 → 609,
báo thiếu oan 26 → 21, **báo Có sai 39 → 56**, Thiếu→CXĐ 714 → 697; áo như V3 (0,775); găng, kính, ủng không đổi.
Mũ: độ đúng 0,556 → 0,571, Coverage 0,576 → 0,595, đúng khi đã kết luận 0,965 → 0,960.
kiem_thu_gan 9-17 (chỉ đo): mũ Có đúng 1.756 → 1.823, Có→CXĐ 346 → 279, Thiếu đúng 689 → 681, Có sai 1 → 2; áo như V3.

**RQ4 — tốc độ** (`final4/benchmark`, sau restart, video3-6, 3 lượt): 17,64 ± 0,35 FPS xử lý, **16,38 ± 0,31 FPS gồm giải
mã**, trễ TB 56,7 ms, P95 107,3 ms (bản cuối 2 cùng lượt: 18,14 / 16,78). Bộ phân loại 11,9 → 13,3 ms (mũ thêm vào zoom).

## Phân tích điểm yếu sau đánh giá cuối 3 (28/11/2026, chỉ đọc kết quả đã có, không chỉnh gì)

- **Tốc độ theo video** (`final4/benchmark/benchmark.json`, FPS gồm giải mã, TB 3 lượt): video3 19,81; video4 10,45;
  video5 11,92; video6 12,87. Số 16,38 là gộp theo khung, video3 chiếm 1.950/2.724 khung. Cảnh gần, 2-3 người lớn trong
  khung (zoom + pose + bộ phân loại cho từng người) dưới 15 FPS. P95 81,8-117,2 ms.
- **Mũ vải / mũ lưỡi trai nhận là mũ bảo hộ** (e1: track 1 Có 91 khung, track 2 Có 68 khung, không khung Thiếu nào; nhãn
  và người kiểm định: thiếu mũ) → sự kiện e1 chỉ có áo, bỏ sót vi phạm mũ.
- **Mũ báo Có sai tăng ở h9** (34 → 51; h9 đầu sát camera, nhãn Thiếu 590 khung); phần tăng Có đúng ở h1 (+25), h7 (+16),
  h8 (+10).
- **Hộp người sai** (e9: track 2, 6 là bình khí/rèm hàn bị nhận là người, sinh sự kiện "ngoài nhãn").
- **Đổi mã theo dõi với người lớn sát camera, mờ** (e7: người tiền cảnh mờ thành track 2, 3, 4 → 3 sự kiện thiếu áo; nhãn
  để không sự kiện vì không nhìn rõ).
- **Cảnh báo cho người rất nhỏ ở xa** (e3: 5 sự kiện cho người cao 4-9% khung, ngoài nhãn) — không kiểm chứng được.
- **Thời điểm sự kiện so với nhãn bảo thủ** (e3 P1: hệ thống xác nhận thiếu găng lúc 0,23 s, nhãn đồng thuận chỉ bắt đầu
  từ 5,0 s → tính 1 sai + 1 sót ở mức chặt).
- **Món thiếu trong sự kiện chưa đủ** (e1 thiếu mũ, e3 thiếu kính không được báo; e5 người đủ mũ áo bị báo thiếu ủng, găng).
- Tập đánh giá sự kiện nhỏ (10 sự kiện, KTC F1 [0,40; 0,95]), nhãn máy có kiểm định.

# Đợt 3 (người dùng giao 28/11/2026: "sửa các lỗi kỹ thuật hiện có thể sửa được, ngay lập tức")

Sửa được ngay (không cần train): (1) tốc độ cảnh gần. Không sửa được trong thời gian còn lại (cần dữ liệu, train lại):
mũ vải nhận là mũ bảo hộ, mũ Có sai khi đầu sát camera, hộp người sai trên vật thể, găng cần hai tay → ghi Hạn chế.
(Cỡ người tối thiểu để cảnh báo: chưa có video chỉnh tham số có nhãn người nhỏ để chọn ngưỡng → không làm.)

## S — tốc độ cảnh gần (ghi trước khi code và chạy)

Biến thể: (a) `part_cls.every_n_frames: 2` (mới: khung bỏ qua dùng lại phiếu đã gộp trong `vote_window_s`, không thêm
phiếu mới); (b) `detector.zoom.every_n_frames: 2` (đã có; từ 25/11 có nhớ PPE F2 giữ hộp găng/kính/ủng giữa các khung);
(c) cả hai. Không đổi tham số khác.

Tiêu chí (khóa): (1) tốc độ (07, video4-6, 3 lượt): FPS gồm giải mã TB **≥ 15 ở cả video4, 5, 6**; (2) video3-6 (06b, nhãn
người, so với cấu hình cuối 3): mỗi PPE, Có đúng và Thiếu đúng giảm không quá 2% số khung nhãn tương ứng; báo Có sai và
báo thiếu oan (mỗi PPE) không tăng quá 1% số khung nhãn tương ứng; số sự kiện mỗi video không đổi. Chọn biến thể đạt cả hai
theo thứ tự ưu tiên a → b → c (ít thay đổi nhất trước). Không biến thể nào đạt → giữ nguyên, ghi Hạn chế.
