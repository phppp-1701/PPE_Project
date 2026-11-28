# Kết quả theo khung (2026-11-28T13:42:54)

**Nhãn:** nhãn máy hai lượt, chưa người kiểm định; KHÔNG ĐỘC LẬP (đã xem nhiều lần)

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Cấu hình: `cuoi4` = `outputs/results/round5/final/pipeline_cuoi4.yaml`, `r5` = `outputs/results/round5/final/pipeline_r5.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | cuoi4 | 1773 | 2394 | 100 | 853 | 21 | 57 | 591 | 696 | 7 | 40 |
| tổng | helmet | r5 | 1773 | 2394 | 100 | 853 | 21 | 57 | 591 | 696 | 7 | 40 |
| tổng | vest | cuoi4 | 1061 | 1565 | 778 | 809 | 119 | 2 | 371 | 29 | 1219 | 40 |
| tổng | vest | r5 | 1061 | 1565 | 778 | 809 | 119 | 2 | 371 | 29 | 1219 | 40 |
| tổng | gloves | cuoi4 | 126 | 220 | 268 | 369 | 0 | 1 | 94 | 100 | 254 | 40 |
| tổng | gloves | r5 | 126 | 220 | 268 | 369 | 0 | 1 | 94 | 100 | 254 | 40 |
| tổng | goggles | cuoi4 | 432 | 590 | 597 | 781 | 121 | 0 | 37 | 176 | 228 | 40 |
| tổng | goggles | r5 | 432 | 590 | 597 | 781 | 121 | 0 | 37 | 176 | 228 | 40 |
| tổng | boots | cuoi4 | 0 | 0 | 75 | 141 | 0 | 3 | 0 | 61 | 10 | 40 |
| tổng | boots | r5 | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 10 | 40 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| holdout/h1 | helmet | cuoi4 | 380 | 398 | 0 | 0 | 0 | 0 | 13 | 0 | 0 | 5 |
| holdout/h1 | helmet | r5 | 380 | 398 | 0 | 0 | 0 | 0 | 13 | 0 | 0 | 5 |
| holdout/h1 | vest | cuoi4 | 350 | 398 | 0 | 0 | 0 | 0 | 43 | 0 | 0 | 5 |
| holdout/h1 | vest | r5 | 350 | 398 | 0 | 0 | 0 | 0 | 43 | 0 | 0 | 5 |
| holdout/h1 | gloves | cuoi4 | 0 | 0 | 89 | 180 | 0 | 1 | 0 | 90 | 91 | 5 |
| holdout/h1 | gloves | r5 | 0 | 0 | 89 | 180 | 0 | 1 | 0 | 90 | 91 | 5 |
| holdout/h1 | goggles | cuoi4 | 0 | 0 | 245 | 250 | 0 | 0 | 0 | 0 | 147 | 5 |
| holdout/h1 | goggles | r5 | 0 | 0 | 245 | 250 | 0 | 0 | 0 | 0 | 147 | 5 |
| holdout/h1 | boots | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| holdout/h1 | boots | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| holdout/h2 | helmet | cuoi4 | 0 | 0 | 0 | 241 | 0 | 3 | 0 | 238 | 0 | 2 |
| holdout/h2 | helmet | r5 | 0 | 0 | 0 | 241 | 0 | 3 | 0 | 238 | 0 | 2 |
| holdout/h2 | vest | cuoi4 | 241 | 257 | 0 | 0 | 7 | 0 | 9 | 0 | 23 | 2 |
| holdout/h2 | vest | r5 | 241 | 257 | 0 | 0 | 7 | 0 | 9 | 0 | 23 | 2 |
| holdout/h2 | gloves | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 19 | 2 |
| holdout/h2 | gloves | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 19 | 2 |
| holdout/h2 | goggles | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| holdout/h2 | goggles | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| holdout/h2 | boots | cuoi4 | 0 | 0 | 75 | 141 | 0 | 3 | 0 | 61 | 0 | 2 |
| holdout/h2 | boots | r5 | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 0 | 2 |
| holdout/h3 | helmet | cuoi4 | 12 | 459 | 0 | 0 | 0 | 0 | 447 | 0 | 0 | 0 |
| holdout/h3 | helmet | r5 | 12 | 459 | 0 | 0 | 0 | 0 | 447 | 0 | 0 | 0 |
| holdout/h3 | vest | cuoi4 | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | vest | r5 | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | boots | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| holdout/h3 | boots | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| holdout/h4 | helmet | cuoi4 | 511 | 558 | 0 | 0 | 7 | 0 | 40 | 0 | 7 | 0 |
| holdout/h4 | helmet | r5 | 511 | 558 | 0 | 0 | 7 | 0 | 40 | 0 | 7 | 0 |
| holdout/h4 | vest | cuoi4 | 347 | 404 | 0 | 0 | 0 | 0 | 57 | 0 | 168 | 0 |
| holdout/h4 | vest | r5 | 347 | 404 | 0 | 0 | 0 | 0 | 57 | 0 | 168 | 0 |
| holdout/h4 | gloves | cuoi4 | 126 | 220 | 0 | 0 | 0 | 0 | 94 | 0 | 0 | 0 |
| holdout/h4 | gloves | r5 | 126 | 220 | 0 | 0 | 0 | 0 | 94 | 0 | 0 | 0 |
| holdout/h4 | goggles | cuoi4 | 0 | 0 | 2 | 157 | 0 | 0 | 0 | 155 | 0 | 0 |
| holdout/h4 | goggles | r5 | 0 | 0 | 2 | 157 | 0 | 0 | 0 | 155 | 0 | 0 |
| holdout/h4 | boots | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h4 | boots | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h5 | helmet | cuoi4 | 438 | 439 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | helmet | r5 | 438 | 439 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | vest | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 438 | 24 |
| holdout/h5 | vest | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 438 | 24 |
| holdout/h5 | gloves | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | gloves | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | goggles | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | goggles | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | boots | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | boots | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h7 | helmet | cuoi4 | 142 | 250 | 0 | 0 | 14 | 0 | 91 | 0 | 0 | 9 |
| holdout/h7 | helmet | r5 | 142 | 250 | 0 | 0 | 14 | 0 | 91 | 0 | 0 | 9 |
| holdout/h7 | vest | cuoi4 | 123 | 506 | 0 | 0 | 112 | 0 | 262 | 0 | 0 | 9 |
| holdout/h7 | vest | r5 | 123 | 506 | 0 | 0 | 112 | 0 | 262 | 0 | 0 | 9 |
| holdout/h7 | gloves | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 141 | 9 |
| holdout/h7 | gloves | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 141 | 9 |
| holdout/h7 | goggles | cuoi4 | 0 | 0 | 58 | 82 | 0 | 0 | 0 | 21 | 56 | 9 |
| holdout/h7 | goggles | r5 | 0 | 0 | 58 | 82 | 0 | 0 | 0 | 21 | 56 | 9 |
| holdout/h7 | boots | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| holdout/h7 | boots | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| holdout/h8 | helmet | cuoi4 | 290 | 290 | 15 | 22 | 0 | 2 | 0 | 5 | 0 | 0 |
| holdout/h8 | helmet | r5 | 290 | 290 | 15 | 22 | 0 | 2 | 0 | 5 | 0 | 0 |
| holdout/h8 | vest | cuoi4 | 0 | 0 | 319 | 350 | 0 | 2 | 0 | 29 | 0 | 0 |
| holdout/h8 | vest | r5 | 0 | 0 | 319 | 350 | 0 | 2 | 0 | 29 | 0 | 0 |
| holdout/h8 | gloves | cuoi4 | 0 | 0 | 179 | 189 | 0 | 0 | 0 | 10 | 3 | 0 |
| holdout/h8 | gloves | r5 | 0 | 0 | 179 | 189 | 0 | 0 | 0 | 10 | 3 | 0 |
| holdout/h8 | goggles | cuoi4 | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 25 | 0 |
| holdout/h8 | goggles | r5 | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 25 | 0 |
| holdout/h8 | boots | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h8 | boots | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | helmet | cuoi4 | 0 | 0 | 85 | 590 | 0 | 52 | 0 | 453 | 0 | 0 |
| holdout/h9 | helmet | r5 | 0 | 0 | 85 | 590 | 0 | 52 | 0 | 453 | 0 | 0 |
| holdout/h9 | vest | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | vest | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | gloves | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | gloves | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | goggles | cuoi4 | 432 | 590 | 0 | 0 | 121 | 0 | 37 | 0 | 0 | 0 |
| holdout/h9 | goggles | r5 | 432 | 590 | 0 | 0 | 121 | 0 | 37 | 0 | 0 | 0 |
| holdout/h9 | boots | cuoi4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | boots | r5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- holdout/h1, cuoi4: 4 sự kiện: #1 người 1 0.0-13.267s gloves,goggles (session_ended_unverified); #2 người 2 0.433-13.267s goggles,helmet,vest (session_ended_unverified); #3 người 3 4.133-13.267s gloves,helmet,vest (session_ended_unverified); #4 người 5 10.967-13.267s goggles,vest (session_ended_unverified)
- holdout/h1, r5: 4 sự kiện: #1 người 1 0.0-13.267s gloves,goggles (session_ended_unverified); #2 người 2 0.433-13.267s goggles,helmet,vest (session_ended_unverified); #3 người 3 4.133-13.267s gloves,helmet,vest (session_ended_unverified); #4 người 5 10.967-13.267s goggles,vest (session_ended_unverified)
- holdout/h2, cuoi4: 2 sự kiện: #1 người 1 0.067-9.4s boots (session_ended_unverified); #2 người 2 5.133-9.4s boots,goggles,helmet,vest (session_ended_unverified)
- holdout/h2, r5: 2 sự kiện: #1 người 1 0.067-9.4s boots (session_ended_unverified); #2 người 2 5.133-9.4s boots,goggles,helmet,vest (session_ended_unverified)
- holdout/h3, cuoi4: 1 sự kiện: #1 người 1 0.0-15.3s vest (session_ended_unverified)
- holdout/h3, r5: 1 sự kiện: #1 người 1 0.0-15.3s vest (session_ended_unverified)
- holdout/h4, cuoi4: 1 sự kiện: #1 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h4, r5: 1 sự kiện: #1 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h5, cuoi4: 1 sự kiện: #1 người 1 0.45-7.758s vest (session_ended_unverified)
- holdout/h5, r5: 1 sự kiện: #1 người 1 0.45-7.758s vest (session_ended_unverified)
- holdout/h7, cuoi4: 1 sự kiện: #1 người 1 0.0-9.142s  (session_ended_unverified)
- holdout/h7, r5: 1 sự kiện: #1 người 1 0.0-9.142s  (session_ended_unverified)
- holdout/h8, cuoi4: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h8, r5: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h9, cuoi4: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)
- holdout/h9, r5: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)

## So sánh với cấu hình mốc

### cuoi4_vs_r5
- holdout/h1: sự kiện giống nhau (4 / 4); dòng frames.csv 577 / 577, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 577; Có mới trên người không có nhãn {'helmet': 8, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h2: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.533, ["vest"]], [1.1, ["vest"]], [1.167, ["vest"]], [2.467, []], [2.9, ["boots"]], [9.1, ["boots"]], [9.133, ["boots"]], [9.4, ["boots"]]], "b": [[0.533, ["boots", "vest"]], [2.467, ["boots"]], [9.1, ["boots"]], [9.133, ["boots"]], [9.4, ["boots"]]]}, {"index": 2, "field": "missing_history", "a": [[5.8, ["boots", "goggles", "vest"]], [6.033, ["boots", "goggles", "helmet", "vest"]], [6.167, ["boots", "goggles", "helmet", "vest"]], [9.4, ["boots", "goggles", "helmet", "vest"]]], "b": [[5.8, ["boots", "goggles", "vest"]], [6.1, ["boots", "goggles", "helmet", "vest"]], [6.167, ["boots", "goggles", "helmet", "vest"]], [9.4, ["boots", "goggles", "helmet", "vest"]]]}] (2 / 2); dòng frames.csv 311 / 311, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 311; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - boots (nhãn|mốc->bản kia): {'thieu|chua_xac_dinh->thieu': 43, 'thieu|co->thieu': 3}
- holdout/h3: sự kiện giống nhau (1 / 1); dòng frames.csv 460 / 460, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 460; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 4}
- holdout/h4: sự kiện giống nhau (1 / 1); dòng frames.csv 808 / 808, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 808; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h5: sự kiện giống nhau (1 / 1); dòng frames.csv 438 / 438, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 438; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h7: sự kiện giống nhau (1 / 1); dòng frames.csv 500 / 500, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 500; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h8: sự kiện giống nhau (1 / 1); dòng frames.csv 350 / 350, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 350; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h9: sự kiện giống nhau (1 / 1); dòng frames.csv 593 / 593, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 593; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
