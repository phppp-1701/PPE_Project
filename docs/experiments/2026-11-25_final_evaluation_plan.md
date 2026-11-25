# Kế hoạch đánh giá cuối sau đợt sửa tầm gần — 25/11/2026

Viết trước khi chạy. Bản cuối mới = cấu hình sau `2026-11-25_close_range_fixes.md` (F1, F2, A1, A2, A3; B1 nếu đạt).

## Đóng băng

1. Sau khi chốt B1 (đạt → bật kính bản 6; không đạt → giữ bản 3): commit nguồn, ghi `outputs/results/close_eval/final2/`
   (`06b manifest`: sha256 code, cấu hình, trọng số, video, nhãn). Sau đó không sửa code, cấu hình cho tới khi chạy xong.
2. Mốc so sánh: bản cuối 16/11/2026 (`outputs/results/close_eval/final/`, detector C4) và cấu hình c6_ft + zoom trước đợt sửa
   (`outputs/results/c5_eval/zoom_bench/pipeline_zoom_n1.yaml`).

## Chạy (theo thứ tự)

| # | Việc | Lệnh / ghi chú | Tính chất số |
|---|---|---|---|
| 1 | Tốc độ (07) | `--config before=…pipeline_zoom_n1.yaml --config final2=configs/pipeline.yaml`, video3-6, 3 lượt | chính thức (đo 25/11 cho cấu hình chưa có B1; bộ phân loại kính bản 6 cùng kiến trúc nên không đổi tốc độ) |
| 2 | **Tập test, chạy đúng một lần** | detector c6_ft cả ảnh (04d) và có zoom (04m), chấm 04j `--split test`; người dùng cho phép trước | chính thức (detector) |
| 3 | Pictor-PPE | `final/pictor/pictor_eval.py` với c6_ft | chính thức (kiểm thử ngoài) |
| 4 | Ablation A→E | `06_evaluate_ablation.py --config configs/pipeline.yaml --out final2/ablation.json` (video4-6) | video chỉnh tham số: không khách quan, ghi rõ |
| 5 | Holdout | `06b evaluate` 8 video, so với bản cuối 16/11 | **"kiểm tra sau khi sửa, không còn mù"**; số chính thức vẫn là lần 16/11 |
| 6 | Hồi quy video3-6 | `06b evaluate` final2 so với trước đợt sửa | video chỉnh tham số |
| 7 | Xem lại video18-27 | `05h --ids 18-27` | đã dùng để chẩn đoán, chỉ xem lại |
| 8 | Bảng FR | cập nhật `fr_table.md` (FR-09 WebSocket) | |

## Báo cáo

Ghi mọi ngoại lệ người dùng duyệt (F1, F2, A1) cùng tiêu chí không đạt; số holdout chính thức (16/11) và số kiểm tra sau
sửa tách riêng; nhãn holdout, val là nhãn máy (có hoặc chưa có kiểm định người) như đã ghi ở từng mục.

## Kết quả (26/11/2026), cấu hình đóng băng `28ad782`

**1. Tập test (chạy một lần, người dùng cho phép)** — `outputs/results/c5_eval/final_test_c6_ft.json`, nhãn máy đã sửa C5:

| Lớp (tập con) | c6_ft cả ảnh | c6_ft + zoom (hệ thống) [KTC 95%] |
|---|---|---|
| Người (ppe4) | 0,923 | 0,923 [0,906; 0,939] |
| Mũ (ppe4) | 0,855 | 0,855 [0,771; 0,918] |
| Áo (ppe4) | 0,821 | 0,821 [0,755; 0,887] |
| Găng (ppe4, 864 hộp) | 0,684 | 0,718 [0,637; 0,782] |
| Kính (goggles_all, 166 hộp) | 0,734 | 0,756 [0,682; 0,825] |
| Ủng (ảnh lớp mới, 92 hộp) | 0,537 | 0,596 [0,450; 0,743] |

Theo nguồn (`final_test_by_source.json`, có zoom): áo SH17 0,517; mũ SH17 0,540; ủng SH17 0,549, Construction-PPE 0,817;
kính CHVG 0,847, SH17 0,649; găng SH17 0,700, CHV 0,612, Construction-PPE 0,855.

**2. Pictor-PPE** (`close_eval/final2/pictor/`): c6_ft người 0,851, mũ 0,681, áo 0,477 [0,258; 0,686] (42 hộp); C4 0,851 /
0,685 / 0,419.

**3. Ablation A→E** (`final2/ablation.json`, video4-6 chỉnh tham số): E 7 cảnh báo, 0 sai, 0 trùng, Event F1 0,9565, trễ
1,41 s; A 4.881 cảnh báo, F1 0,0045. Giống cấu hình trước đợt sửa.

**4. Holdout — kiểm tra sau khi sửa, KHÔNG còn mù** (`final2/holdout_check/`; số chính thức vẫn là `final/holdout` 16/11).
Độ đúng khung-người = (Có đúng + Thiếu đúng) / (nhãn Có + Thiếu), nhãn máy hai lượt chưa người kiểm định:

| PPE | Chính thức 16/11 (C4) | c6_ft + zoom trước đợt sửa | Bản cuối 2 |
|---|---|---|---|
| Mũ | 0,542 | 0,556 | 0,556 |
| Áo | 0,698 | 0,641 | 0,641 |
| Găng | 0,497 | 0,436 | **0,567** (Có đúng 0 → 109 / 220; báo Có sai 0 → 3) |
| Kính | 0,743 | 0,652 | **0,744** (Có đúng 297 → 423) |
| Ủng | 0,248 | 0,858 | 0,858 |

Đợt sửa tầm gần tăng găng, kính, không đổi mũ, áo, ủng trên holdout; áo giảm so với 16/11 do đổi detector (C4 → c6_ft), có
từ trước đợt sửa.

**5. Hồi quy video3-6** (`final2/dev36/`, so với trước đợt sửa): Có đúng găng 686 → 754, kính 357 → 367, ủng 318 → 651; báo
Có sai và Thiếu oan mọi PPE không đổi; sự kiện giống nhau.

**6. Xem lại video18-27** (`final2/close_probe/`, đã dùng để chẩn đoán): ủng video26 Có 0,08 → 0,84, Thiếu 0,45 → 0; găng
video18/19/20/24 Có 0,25/0,39/0,18/0,79 → 0,64/0,72/0,53/1,00; còn: kính vàng video21, giày video27, mũ cứu hỏa video23.

**7. Tốc độ:** 17,99 FPS xử lý (25/11, cùng lượt với trước đợt sửa 18,06). **8. FR:** `final2/fr_table.md`.
