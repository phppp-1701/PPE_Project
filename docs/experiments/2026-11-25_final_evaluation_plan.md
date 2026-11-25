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
