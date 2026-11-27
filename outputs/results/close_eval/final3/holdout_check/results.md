# Kết quả theo khung (2026-11-27T23:31:07)

**Nhãn:** nhãn máy hai lượt, chưa người kiểm định; KIỂM TRA SAU KHI SỬA, KHÔNG CÒN MÙ (số chính thức: final/holdout 16/11)

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Cấu hình: `final2` = `outputs/results/close_eval/stepV/pipeline_base.yaml`, `final3` = `configs/pipeline.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | final2 | 1704 | 2394 | 100 | 853 | 26 | 39 | 655 | 714 | 18 | 40 |
| tổng | helmet | final3 | 1704 | 2394 | 100 | 853 | 26 | 39 | 655 | 714 | 18 | 40 |
| tổng | vest | final2 | 743 | 1565 | 778 | 809 | 351 | 2 | 457 | 29 | 1219 | 40 |
| tổng | vest | final3 | 1061 | 1565 | 778 | 809 | 119 | 2 | 371 | 29 | 1219 | 40 |
| tổng | gloves | final2 | 109 | 220 | 225 | 369 | 0 | 3 | 111 | 141 | 246 | 40 |
| tổng | gloves | final3 | 109 | 220 | 225 | 369 | 0 | 3 | 111 | 141 | 246 | 40 |
| tổng | goggles | final2 | 423 | 590 | 597 | 781 | 115 | 0 | 52 | 176 | 228 | 40 |
| tổng | goggles | final3 | 423 | 590 | 597 | 781 | 115 | 0 | 52 | 176 | 228 | 40 |
| tổng | boots | final2 | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 9 | 40 |
| tổng | boots | final3 | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 9 | 40 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| holdout/h1 | helmet | final2 | 353 | 398 | 0 | 0 | 0 | 0 | 40 | 0 | 0 | 5 |
| holdout/h1 | helmet | final3 | 353 | 398 | 0 | 0 | 0 | 0 | 40 | 0 | 0 | 5 |
| holdout/h1 | vest | final2 | 317 | 398 | 0 | 0 | 0 | 0 | 76 | 0 | 0 | 5 |
| holdout/h1 | vest | final3 | 350 | 398 | 0 | 0 | 0 | 0 | 43 | 0 | 0 | 5 |
| holdout/h1 | gloves | final2 | 0 | 0 | 46 | 180 | 0 | 3 | 0 | 131 | 88 | 5 |
| holdout/h1 | gloves | final3 | 0 | 0 | 46 | 180 | 0 | 3 | 0 | 131 | 88 | 5 |
| holdout/h1 | goggles | final2 | 0 | 0 | 245 | 250 | 0 | 0 | 0 | 0 | 147 | 5 |
| holdout/h1 | goggles | final3 | 0 | 0 | 245 | 250 | 0 | 0 | 0 | 0 | 147 | 5 |
| holdout/h1 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| holdout/h1 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| holdout/h2 | helmet | final2 | 0 | 0 | 0 | 241 | 0 | 3 | 0 | 238 | 0 | 2 |
| holdout/h2 | helmet | final3 | 0 | 0 | 0 | 241 | 0 | 3 | 0 | 238 | 0 | 2 |
| holdout/h2 | vest | final2 | 241 | 257 | 0 | 0 | 7 | 0 | 9 | 0 | 23 | 2 |
| holdout/h2 | vest | final3 | 241 | 257 | 0 | 0 | 7 | 0 | 9 | 0 | 23 | 2 |
| holdout/h2 | gloves | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 2 |
| holdout/h2 | gloves | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 2 |
| holdout/h2 | goggles | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| holdout/h2 | goggles | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| holdout/h2 | boots | final2 | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 0 | 2 |
| holdout/h2 | boots | final3 | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 0 | 2 |
| holdout/h3 | helmet | final2 | 12 | 459 | 0 | 0 | 0 | 0 | 447 | 0 | 0 | 0 |
| holdout/h3 | helmet | final3 | 12 | 459 | 0 | 0 | 0 | 0 | 447 | 0 | 0 | 0 |
| holdout/h3 | vest | final2 | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | vest | final3 | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 |
| holdout/h3 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 |
| holdout/h4 | helmet | final2 | 512 | 558 | 0 | 0 | 7 | 0 | 39 | 0 | 7 | 0 |
| holdout/h4 | helmet | final3 | 512 | 558 | 0 | 0 | 7 | 0 | 39 | 0 | 7 | 0 |
| holdout/h4 | vest | final2 | 62 | 404 | 0 | 0 | 232 | 0 | 110 | 0 | 168 | 0 |
| holdout/h4 | vest | final3 | 347 | 404 | 0 | 0 | 0 | 0 | 57 | 0 | 168 | 0 |
| holdout/h4 | gloves | final2 | 109 | 220 | 0 | 0 | 0 | 0 | 111 | 0 | 0 | 0 |
| holdout/h4 | gloves | final3 | 109 | 220 | 0 | 0 | 0 | 0 | 111 | 0 | 0 | 0 |
| holdout/h4 | goggles | final2 | 0 | 0 | 2 | 157 | 0 | 0 | 0 | 155 | 0 | 0 |
| holdout/h4 | goggles | final3 | 0 | 0 | 2 | 157 | 0 | 0 | 0 | 155 | 0 | 0 |
| holdout/h4 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h4 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h5 | helmet | final2 | 438 | 439 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | helmet | final3 | 438 | 439 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | vest | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 438 | 24 |
| holdout/h5 | vest | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 438 | 24 |
| holdout/h5 | gloves | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | gloves | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | goggles | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | goggles | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h7 | helmet | final2 | 109 | 250 | 0 | 0 | 19 | 0 | 119 | 0 | 11 | 9 |
| holdout/h7 | helmet | final3 | 109 | 250 | 0 | 0 | 19 | 0 | 119 | 0 | 11 | 9 |
| holdout/h7 | vest | final2 | 123 | 506 | 0 | 0 | 112 | 0 | 262 | 0 | 0 | 9 |
| holdout/h7 | vest | final3 | 123 | 506 | 0 | 0 | 112 | 0 | 262 | 0 | 0 | 9 |
| holdout/h7 | gloves | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 141 | 9 |
| holdout/h7 | gloves | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 141 | 9 |
| holdout/h7 | goggles | final2 | 0 | 0 | 58 | 82 | 0 | 0 | 0 | 21 | 56 | 9 |
| holdout/h7 | goggles | final3 | 0 | 0 | 58 | 82 | 0 | 0 | 0 | 21 | 56 | 9 |
| holdout/h7 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| holdout/h7 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| holdout/h8 | helmet | final2 | 280 | 290 | 15 | 22 | 0 | 2 | 10 | 5 | 0 | 0 |
| holdout/h8 | helmet | final3 | 280 | 290 | 15 | 22 | 0 | 2 | 10 | 5 | 0 | 0 |
| holdout/h8 | vest | final2 | 0 | 0 | 319 | 350 | 0 | 2 | 0 | 29 | 0 | 0 |
| holdout/h8 | vest | final3 | 0 | 0 | 319 | 350 | 0 | 2 | 0 | 29 | 0 | 0 |
| holdout/h8 | gloves | final2 | 0 | 0 | 179 | 189 | 0 | 0 | 0 | 10 | 3 | 0 |
| holdout/h8 | gloves | final3 | 0 | 0 | 179 | 189 | 0 | 0 | 0 | 10 | 3 | 0 |
| holdout/h8 | goggles | final2 | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 25 | 0 |
| holdout/h8 | goggles | final3 | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 25 | 0 |
| holdout/h8 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h8 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | helmet | final2 | 0 | 0 | 85 | 590 | 0 | 34 | 0 | 471 | 0 | 0 |
| holdout/h9 | helmet | final3 | 0 | 0 | 85 | 590 | 0 | 34 | 0 | 471 | 0 | 0 |
| holdout/h9 | vest | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | vest | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | gloves | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | gloves | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | goggles | final2 | 423 | 590 | 0 | 0 | 115 | 0 | 52 | 0 | 0 | 0 |
| holdout/h9 | goggles | final3 | 423 | 590 | 0 | 0 | 115 | 0 | 52 | 0 | 0 | 0 |
| holdout/h9 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | boots | final3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- holdout/h1, final2: 4 sự kiện: #1 người 1 0.0-13.267s goggles (session_ended_unverified); #2 người 2 0.433-13.267s goggles,helmet,vest (session_ended_unverified); #3 người 3 4.133-13.267s gloves,helmet,vest (session_ended_unverified); #4 người 5 10.967-13.267s goggles,helmet,vest (session_ended_unverified)
- holdout/h1, final3: 4 sự kiện: #1 người 1 0.0-13.267s goggles (session_ended_unverified); #2 người 2 0.433-13.267s goggles,helmet,vest (session_ended_unverified); #3 người 3 4.133-13.267s gloves,helmet,vest (session_ended_unverified); #4 người 5 10.967-13.267s goggles,helmet,vest (session_ended_unverified)
- holdout/h2, final2: 2 sự kiện: #1 người 1 0.067-9.4s  (session_ended_unverified); #2 người 2 5.133-9.4s boots,goggles,helmet,vest (session_ended_unverified)
- holdout/h2, final3: 2 sự kiện: #1 người 1 0.067-9.4s  (session_ended_unverified); #2 người 2 5.133-9.4s boots,goggles,helmet,vest (session_ended_unverified)
- holdout/h3, final2: 1 sự kiện: #1 người 1 0.0-15.3s vest (session_ended_unverified)
- holdout/h3, final3: 1 sự kiện: #1 người 1 0.0-15.3s vest (session_ended_unverified)
- holdout/h4, final2: 2 sự kiện: #1 người 1 0.0-8.08s  (session_ended_unverified); #2 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h4, final3: 1 sự kiện: #1 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h5, final2: 1 sự kiện: #1 người 1 0.45-7.758s vest (session_ended_unverified)
- holdout/h5, final3: 1 sự kiện: #1 người 1 0.45-7.758s vest (session_ended_unverified)
- holdout/h7, final2: 1 sự kiện: #1 người 1 0.0-9.142s  (session_ended_unverified)
- holdout/h7, final3: 1 sự kiện: #1 người 1 0.0-9.142s  (session_ended_unverified)
- holdout/h8, final2: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h8, final3: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h9, final2: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)
- holdout/h9, final3: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)

## So sánh với cấu hình mốc

### final2_vs_final3
- holdout/h1: sự kiện giống nhau (4 / 4); dòng frames.csv 577 / 577, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 577; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - vest (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 33}
- holdout/h2: sự kiện giống nhau (2 / 2); dòng frames.csv 311 / 311, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 311; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h3: sự kiện giống nhau (1 / 1); dòng frames.csv 460 / 460, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 460; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h4: sự kiện KHÁC: [{"index": 1, "field": "track_id", "a": 1, "b": 2}, {"index": 1, "field": "missing_items", "a": [], "b": ["vest"]}, {"index": 1, "field": "missing_history", "a": [[0.28, ["vest"]], [6.46, []], [8.08, []]], "b": [[0.28, ["vest"]], [0.52, ["vest"]], [0.92, ["vest"]], [1.56, ["vest"]], [3.32, ["vest"]], [3.38, ["vest"]], [3.46, ["vest"]], [3.6, ["vest"]], [3.66, ["vest"]], [3.72, ["vest"]], [3.74, ["vest"]], [3.84, ["vest"]], [4.72, ["vest"]], [4.74, ["vest"]], [4.76, ["vest"]], [4.86, ["vest"]], [4.88, ["vest"]], [5.74, ["vest"]], [5.8, ["vest"]], [8.08, ["vest"]]]}, {"index": 2, "field": "(thiếu sự kiện)", "a": {"track_id": 2, "start_time": 0.0, "confirmed_at": 0.28, "end_time": 8.08, "close_reason": "session_ended_unverified", "event_state": "closed", "missing_items": ["vest"], "missing_history": [[0.28, ["vest"]], [0.52, ["vest"]], [0.92, ["vest"]], [1.56, ["vest"]], [3.32, ["vest"]], [3.38, ["vest"]], [3.46, ["vest"]], [3.6, ["vest"]], [3.66, ["vest"]], [3.72, ["vest"]], [3.74, ["vest"]], [3.84, ["vest"]], [4.72, ["vest"]], [4.74, ["vest"]], [4.76, ["vest"]], [4.86, ["vest"]], [4.88, ["vest"]], [5.74, ["vest"]], [5.8, ["vest"]], [8.08, ["vest"]]], "index": 2}, "b": null}] (2 / 1); dòng frames.csv 808 / 808, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 808; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - vest (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 58, 'co|thieu->chua_xac_dinh': 5, 'co|thieu->co': 227}
- holdout/h5: sự kiện giống nhau (1 / 1); dòng frames.csv 438 / 438, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 438; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h7: sự kiện giống nhau (1 / 1); dòng frames.csv 500 / 500, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 500; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h8: sự kiện giống nhau (1 / 1); dòng frames.csv 350 / 350, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 350; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h9: sự kiện giống nhau (1 / 1); dòng frames.csv 593 / 593, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 593; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
