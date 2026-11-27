# Kết quả theo khung (2026-11-28T04:15:27)

**Nhãn:** nhãn máy hai lượt, chưa người kiểm định; KIỂM TRA SAU KHI SỬA, KHÔNG CÒN MÙ (số chính thức: final/holdout 16/11)

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Cấu hình: `final3` = `outputs/results/close_eval/final5/pipeline_final3_5d7acec.yaml`, `final5` = `configs/pipeline.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | final3 | 1755 | 2394 | 100 | 853 | 21 | 56 | 609 | 697 | 7 | 40 |
| tổng | helmet | final5 | 1773 | 2394 | 100 | 853 | 21 | 57 | 591 | 696 | 7 | 40 |
| tổng | vest | final3 | 1061 | 1565 | 778 | 809 | 119 | 2 | 371 | 29 | 1219 | 40 |
| tổng | vest | final5 | 1061 | 1565 | 778 | 809 | 119 | 2 | 371 | 29 | 1219 | 40 |
| tổng | gloves | final3 | 109 | 220 | 225 | 369 | 0 | 3 | 111 | 141 | 246 | 40 |
| tổng | gloves | final5 | 126 | 220 | 268 | 369 | 0 | 1 | 94 | 100 | 254 | 40 |
| tổng | goggles | final3 | 423 | 590 | 597 | 781 | 115 | 0 | 52 | 176 | 228 | 40 |
| tổng | goggles | final5 | 432 | 590 | 597 | 781 | 121 | 0 | 37 | 176 | 228 | 40 |
| tổng | boots | final3 | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 9 | 40 |
| tổng | boots | final5 | 0 | 0 | 75 | 141 | 0 | 3 | 0 | 61 | 10 | 40 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| holdout/h1 | helmet | final3 | 378 | 398 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 5 |
| holdout/h1 | helmet | final5 | 380 | 398 | 0 | 0 | 0 | 0 | 13 | 0 | 0 | 5 |
| holdout/h1 | vest | final3 | 350 | 398 | 0 | 0 | 0 | 0 | 43 | 0 | 0 | 5 |
| holdout/h1 | vest | final5 | 350 | 398 | 0 | 0 | 0 | 0 | 43 | 0 | 0 | 5 |
| holdout/h1 | gloves | final3 | 0 | 0 | 46 | 180 | 0 | 3 | 0 | 131 | 88 | 5 |
| holdout/h1 | gloves | final5 | 0 | 0 | 89 | 180 | 0 | 1 | 0 | 90 | 91 | 5 |
| holdout/h1 | goggles | final3 | 0 | 0 | 245 | 250 | 0 | 0 | 0 | 0 | 147 | 5 |
| holdout/h1 | goggles | final5 | 0 | 0 | 245 | 250 | 0 | 0 | 0 | 0 | 147 | 5 |
| holdout/h1 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| holdout/h1 | boots | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| holdout/h2 | helmet | final3 | 0 | 0 | 0 | 241 | 0 | 3 | 0 | 238 | 0 | 2 |
| holdout/h2 | helmet | final5 | 0 | 0 | 0 | 241 | 0 | 3 | 0 | 238 | 0 | 2 |
| holdout/h2 | vest | final3 | 241 | 257 | 0 | 0 | 7 | 0 | 9 | 0 | 23 | 2 |
| holdout/h2 | vest | final5 | 241 | 257 | 0 | 0 | 7 | 0 | 9 | 0 | 23 | 2 |
| holdout/h2 | gloves | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 2 |
| holdout/h2 | gloves | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 19 | 2 |
| holdout/h2 | goggles | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| holdout/h2 | goggles | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| holdout/h2 | boots | final3 | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 0 | 2 |
| holdout/h2 | boots | final5 | 0 | 0 | 75 | 141 | 0 | 3 | 0 | 61 | 0 | 2 |
| holdout/h3 | helmet | final3 | 12 | 459 | 0 | 0 | 0 | 0 | 447 | 0 | 0 | 0 |
| holdout/h3 | helmet | final5 | 12 | 459 | 0 | 0 | 0 | 0 | 447 | 0 | 0 | 0 |
| holdout/h3 | vest | final3 | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | vest | final5 | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 |
| holdout/h3 | boots | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| holdout/h4 | helmet | final3 | 512 | 558 | 0 | 0 | 7 | 0 | 39 | 0 | 7 | 0 |
| holdout/h4 | helmet | final5 | 511 | 558 | 0 | 0 | 7 | 0 | 40 | 0 | 7 | 0 |
| holdout/h4 | vest | final3 | 347 | 404 | 0 | 0 | 0 | 0 | 57 | 0 | 168 | 0 |
| holdout/h4 | vest | final5 | 347 | 404 | 0 | 0 | 0 | 0 | 57 | 0 | 168 | 0 |
| holdout/h4 | gloves | final3 | 109 | 220 | 0 | 0 | 0 | 0 | 111 | 0 | 0 | 0 |
| holdout/h4 | gloves | final5 | 126 | 220 | 0 | 0 | 0 | 0 | 94 | 0 | 0 | 0 |
| holdout/h4 | goggles | final3 | 0 | 0 | 2 | 157 | 0 | 0 | 0 | 155 | 0 | 0 |
| holdout/h4 | goggles | final5 | 0 | 0 | 2 | 157 | 0 | 0 | 0 | 155 | 0 | 0 |
| holdout/h4 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h4 | boots | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h5 | helmet | final3 | 438 | 439 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | helmet | final5 | 438 | 439 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | vest | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 438 | 24 |
| holdout/h5 | vest | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 438 | 24 |
| holdout/h5 | gloves | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | gloves | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | goggles | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | goggles | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | boots | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h7 | helmet | final3 | 125 | 250 | 0 | 0 | 14 | 0 | 108 | 0 | 0 | 9 |
| holdout/h7 | helmet | final5 | 142 | 250 | 0 | 0 | 14 | 0 | 91 | 0 | 0 | 9 |
| holdout/h7 | vest | final3 | 123 | 506 | 0 | 0 | 112 | 0 | 262 | 0 | 0 | 9 |
| holdout/h7 | vest | final5 | 123 | 506 | 0 | 0 | 112 | 0 | 262 | 0 | 0 | 9 |
| holdout/h7 | gloves | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 141 | 9 |
| holdout/h7 | gloves | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 141 | 9 |
| holdout/h7 | goggles | final3 | 0 | 0 | 58 | 82 | 0 | 0 | 0 | 21 | 56 | 9 |
| holdout/h7 | goggles | final5 | 0 | 0 | 58 | 82 | 0 | 0 | 0 | 21 | 56 | 9 |
| holdout/h7 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| holdout/h7 | boots | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| holdout/h8 | helmet | final3 | 290 | 290 | 15 | 22 | 0 | 2 | 0 | 5 | 0 | 0 |
| holdout/h8 | helmet | final5 | 290 | 290 | 15 | 22 | 0 | 2 | 0 | 5 | 0 | 0 |
| holdout/h8 | vest | final3 | 0 | 0 | 319 | 350 | 0 | 2 | 0 | 29 | 0 | 0 |
| holdout/h8 | vest | final5 | 0 | 0 | 319 | 350 | 0 | 2 | 0 | 29 | 0 | 0 |
| holdout/h8 | gloves | final3 | 0 | 0 | 179 | 189 | 0 | 0 | 0 | 10 | 3 | 0 |
| holdout/h8 | gloves | final5 | 0 | 0 | 179 | 189 | 0 | 0 | 0 | 10 | 3 | 0 |
| holdout/h8 | goggles | final3 | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 25 | 0 |
| holdout/h8 | goggles | final5 | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 25 | 0 |
| holdout/h8 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h8 | boots | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | helmet | final3 | 0 | 0 | 85 | 590 | 0 | 51 | 0 | 454 | 0 | 0 |
| holdout/h9 | helmet | final5 | 0 | 0 | 85 | 590 | 0 | 52 | 0 | 453 | 0 | 0 |
| holdout/h9 | vest | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | vest | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | gloves | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | gloves | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | goggles | final3 | 423 | 590 | 0 | 0 | 115 | 0 | 52 | 0 | 0 | 0 |
| holdout/h9 | goggles | final5 | 432 | 590 | 0 | 0 | 121 | 0 | 37 | 0 | 0 | 0 |
| holdout/h9 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | boots | final5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- holdout/h1, final3: 4 sự kiện: #1 người 1 0.0-13.267s goggles (session_ended_unverified); #2 người 2 0.433-13.267s goggles,helmet,vest (session_ended_unverified); #3 người 3 4.133-13.267s gloves,helmet,vest (session_ended_unverified); #4 người 5 10.967-13.267s goggles,vest (session_ended_unverified)
- holdout/h1, final5: 4 sự kiện: #1 người 1 0.0-13.267s gloves,goggles (session_ended_unverified); #2 người 2 0.433-13.267s goggles,helmet,vest (session_ended_unverified); #3 người 3 4.133-13.267s gloves,helmet,vest (session_ended_unverified); #4 người 5 10.967-13.267s goggles,vest (session_ended_unverified)
- holdout/h2, final3: 2 sự kiện: #1 người 1 0.067-9.4s  (session_ended_unverified); #2 người 2 5.133-9.4s boots,goggles,vest (session_ended_unverified)
- holdout/h2, final5: 2 sự kiện: #1 người 1 0.067-9.4s boots (session_ended_unverified); #2 người 2 5.133-9.4s boots,goggles,helmet,vest (session_ended_unverified)
- holdout/h3, final3: 1 sự kiện: #1 người 1 0.0-15.3s vest (session_ended_unverified)
- holdout/h3, final5: 1 sự kiện: #1 người 1 0.0-15.3s vest (session_ended_unverified)
- holdout/h4, final3: 1 sự kiện: #1 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h4, final5: 1 sự kiện: #1 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h5, final3: 1 sự kiện: #1 người 1 0.45-7.758s vest (session_ended_unverified)
- holdout/h5, final5: 1 sự kiện: #1 người 1 0.45-7.758s vest (session_ended_unverified)
- holdout/h7, final3: 1 sự kiện: #1 người 1 0.0-9.142s  (session_ended_unverified)
- holdout/h7, final5: 1 sự kiện: #1 người 1 0.0-9.142s  (session_ended_unverified)
- holdout/h8, final3: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h8, final5: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h9, final3: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)
- holdout/h9, final5: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)

## So sánh với cấu hình mốc

### final3_vs_final5
- holdout/h1: sự kiện KHÁC: [{"index": 1, "field": "missing_items", "a": ["goggles"], "b": ["gloves", "goggles"]}, {"index": 1, "field": "missing_history", "a": [[0.467, ["goggles"]], [1.967, ["gloves", "goggles"]], [4.967, ["gloves", "goggles"]], [5.0, ["gloves", "goggles"]], [10.033, ["goggles"]], [13.267, ["goggles"]]], "b": [[0.467, ["goggles"]], [3.233, ["gloves", "goggles"]], [4.967, ["gloves", "goggles"]], [5.0, ["gloves", "goggles"]], [10.033, ["goggles"]], [10.233, ["gloves", "goggles"]], [13.267, ["gloves", "goggles"]]]}] (4 / 4); dòng frames.csv 577 / 577, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 577; Có mới trên người không có nhãn {'helmet': 1, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 3, 'co|co->chua_xac_dinh': 1}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->thieu': 3, 'thieu|chua_xac_dinh->co': 1, 'thieu|chua_xac_dinh->thieu': 45, 'thieu|co->chua_xac_dinh': 3, 'thieu|thieu->chua_xac_dinh': 2}
- holdout/h2: sự kiện KHÁC: [{"index": 1, "field": "missing_items", "a": [], "b": ["boots"]}, {"index": 1, "field": "missing_history", "a": [[0.533, ["boots", "vest"]], [2.467, ["boots"]], [5.733, []], [9.1, []], [9.133, []], [9.367, []], [9.4, []]], "b": [[0.533, ["vest"]], [1.1, ["vest"]], [1.167, ["vest"]], [2.467, []], [2.9, ["boots"]], [9.1, ["boots"]], [9.133, ["boots"]], [9.4, ["boots"]]]}, {"index": 2, "field": "missing_items", "a": ["boots", "goggles", "vest"], "b": ["boots", "goggles", "helmet", "vest"]}, {"index": 2, "field": "missing_history", "a": [[5.8, ["boots", "goggles", "vest"]], [6.167, ["boots", "goggles", "vest"]], [9.4, ["boots", "goggles", "vest"]]], "b": [[5.8, ["boots", "goggles", "vest"]], [6.033, ["boots", "goggles", "helmet", "vest"]], [6.167, ["boots", "goggles", "helmet", "vest"]], [9.4, ["boots", "goggles", "helmet", "vest"]]]}] (2 / 2); dòng frames.csv 311 / 311, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 311; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->thieu': 10, 'chua_xac_dinh|thieu->chua_xac_dinh': 5}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 2, 'chua_xac_dinh|co->chua_xac_dinh': 54, 'thieu|thieu->chua_xac_dinh': 43, 'thieu|thieu->co': 3}
- holdout/h3: sự kiện giống nhau (1 / 1); dòng frames.csv 460 / 460, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 460; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 13, 'chua_xac_dinh|co->chua_xac_dinh': 13, 'chua_xac_dinh|co->thieu': 1}
- holdout/h4: sự kiện giống nhau (1 / 1); dòng frames.csv 808 / 808, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 808; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|co->chua_xac_dinh': 1}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 15, 'co|chua_xac_dinh->co': 17}
- holdout/h5: sự kiện giống nhau (1 / 1); dòng frames.csv 438 / 438, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 438; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h7: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.234, ["vest"]], [0.317, ["gloves", "vest"]], [2.753, ["gloves", "goggles", "vest"]], [3.27, ["gloves", "goggles"]], [4.221, ["goggles"]], [4.938, []], [6.823, []], [7.124, []], [8.258, []], [8.325, []], [8.358, []], [9.142, []]], "b": [[0.234, ["vest"]], [0.317, ["gloves", "vest"]], [2.753, ["gloves", "goggles", "vest"]], [3.27, ["gloves", "goggles"]], [4.154, ["gloves", "goggles"]], [4.171, ["gloves", "goggles"]], [4.238, ["goggles"]], [5.439, ["goggles"]], [5.455, ["goggles"]], [5.472, ["goggles"]], [5.489, ["goggles"]], [5.556, []], [5.672, []], [5.706, []], [6.823, []], [7.14, []], [8.258, []], [8.325, []], [8.358, []], [9.142, []]]}] (1 / 1); dòng frames.csv 500 / 500, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 500; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 17, 'co|chua_xac_dinh->thieu': 1, 'co|thieu->chua_xac_dinh': 1}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|co->chua_xac_dinh': 2}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|co->chua_xac_dinh': 70}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|co->chua_xac_dinh': 1}
- holdout/h8: sự kiện giống nhau (1 / 1); dòng frames.csv 350 / 350, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 350; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h9: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.56, ["goggles", "helmet", "vest"]], [7.48, ["helmet", "vest"]], [20.64, ["vest"]], [23.72, ["vest"]]], "b": [[0.56, ["goggles", "helmet", "vest"]], [7.68, ["helmet", "vest"]], [20.64, ["vest"]], [23.72, ["vest"]]]}] (1 / 1); dòng frames.csv 593 / 593, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 593; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'thieu|chua_xac_dinh->co': 4, 'thieu|co->chua_xac_dinh': 3}
  - goggles (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 9, 'co|chua_xac_dinh->thieu': 6}
