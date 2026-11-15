# Kết quả theo khung (2026-11-15T18:47:55)

**Nhãn:** Holdout 8 video niêm phong (h6 loại trước mọi dự đoán). Nhãn máy qua hai lượt, chưa người kiểm định; không phải nhãn người đã duyệt. Chạy một lần duy nhất 16/11/2026 theo cho phép của người dùng; không chỉnh tham số sau khi xem kết quả.

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Manifest: `outputs/results/close_eval/final/manifest.json`, commit nguồn `0a47b91cb6`, HEAD `3a4c44a672`.

Cấu hình: `v4` = `outputs/results/close_eval/final/pipeline_v4_0b756b8.yaml`, `final` = `configs/pipeline.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | v4 | 1805 | 2394 | 241 | 853 | 274 | 145 | 307 | 467 | 51 | 26 |
| tổng | helmet | final | 1746 | 2394 | 15 | 853 | 12 | 113 | 628 | 725 | 3 | 26 |
| tổng | vest | v4 | 847 | 1565 | 809 | 809 | 356 | 0 | 349 | 0 | 1265 | 26 |
| tổng | vest | final | 847 | 1565 | 809 | 809 | 356 | 0 | 349 | 0 | 1265 | 26 |
| tổng | gloves | v4 | 0 | 220 | 293 | 369 | 0 | 0 | 220 | 76 | 317 | 26 |
| tổng | gloves | final | 0 | 220 | 293 | 369 | 0 | 0 | 220 | 76 | 317 | 26 |
| tổng | goggles | v4 | 127 | 590 | 597 | 781 | 115 | 0 | 348 | 178 | 260 | 26 |
| tổng | goggles | final | 421 | 590 | 597 | 781 | 92 | 0 | 77 | 178 | 228 | 26 |
| tổng | boots | v4 | 0 | 0 | 35 | 141 | 0 | 18 | 0 | 88 | 353 | 26 |
| tổng | boots | final | 0 | 0 | 35 | 141 | 0 | 18 | 0 | 88 | 353 | 26 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| holdout/h1 | helmet | v4 | 382 | 398 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 6 |
| holdout/h1 | helmet | final | 350 | 398 | 0 | 0 | 0 | 0 | 42 | 0 | 0 | 6 |
| holdout/h1 | vest | v4 | 318 | 398 | 0 | 0 | 0 | 0 | 74 | 0 | 0 | 6 |
| holdout/h1 | vest | final | 318 | 398 | 0 | 0 | 0 | 0 | 74 | 0 | 0 | 6 |
| holdout/h1 | gloves | v4 | 0 | 0 | 112 | 180 | 0 | 0 | 0 | 68 | 91 | 6 |
| holdout/h1 | gloves | final | 0 | 0 | 112 | 180 | 0 | 0 | 0 | 68 | 91 | 6 |
| holdout/h1 | goggles | v4 | 0 | 0 | 243 | 250 | 0 | 0 | 0 | 1 | 145 | 6 |
| holdout/h1 | goggles | final | 0 | 0 | 243 | 250 | 0 | 0 | 0 | 1 | 145 | 6 |
| holdout/h1 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| holdout/h1 | boots | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| holdout/h2 | helmet | v4 | 0 | 0 | 220 | 241 | 0 | 0 | 0 | 21 | 2 | 0 |
| holdout/h2 | helmet | final | 0 | 0 | 0 | 241 | 0 | 0 | 0 | 241 | 0 | 0 |
| holdout/h2 | vest | v4 | 234 | 257 | 0 | 0 | 6 | 0 | 17 | 0 | 25 | 0 |
| holdout/h2 | vest | final | 234 | 257 | 0 | 0 | 6 | 0 | 17 | 0 | 25 | 0 |
| holdout/h2 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| holdout/h2 | gloves | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| holdout/h2 | goggles | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h2 | goggles | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h2 | boots | v4 | 0 | 0 | 35 | 141 | 0 | 18 | 0 | 88 | 5 | 0 |
| holdout/h2 | boots | final | 0 | 0 | 35 | 141 | 0 | 18 | 0 | 88 | 5 | 0 |
| holdout/h3 | helmet | v4 | 0 | 459 | 0 | 0 | 262 | 0 | 197 | 0 | 0 | 0 |
| holdout/h3 | helmet | final | 0 | 459 | 0 | 0 | 0 | 0 | 459 | 0 | 0 | 0 |
| holdout/h3 | vest | v4 | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | vest | final | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 294 | 0 |
| holdout/h3 | boots | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 294 | 0 |
| holdout/h4 | helmet | v4 | 522 | 558 | 0 | 0 | 0 | 0 | 36 | 0 | 1 | 0 |
| holdout/h4 | helmet | final | 522 | 558 | 0 | 0 | 0 | 0 | 36 | 0 | 1 | 0 |
| holdout/h4 | vest | v4 | 78 | 404 | 0 | 0 | 264 | 0 | 62 | 0 | 205 | 0 |
| holdout/h4 | vest | final | 78 | 404 | 0 | 0 | 264 | 0 | 62 | 0 | 205 | 0 |
| holdout/h4 | gloves | v4 | 0 | 220 | 0 | 0 | 0 | 0 | 220 | 0 | 0 | 0 |
| holdout/h4 | gloves | final | 0 | 220 | 0 | 0 | 0 | 0 | 220 | 0 | 0 | 0 |
| holdout/h4 | goggles | v4 | 0 | 0 | 1 | 157 | 0 | 0 | 0 | 156 | 0 | 0 |
| holdout/h4 | goggles | final | 0 | 0 | 1 | 157 | 0 | 0 | 0 | 156 | 0 | 0 |
| holdout/h4 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h4 | boots | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h5 | helmet | v4 | 436 | 439 | 0 | 0 | 0 | 0 | 1 | 0 | 2 | 13 |
| holdout/h5 | helmet | final | 436 | 439 | 0 | 0 | 0 | 0 | 1 | 0 | 2 | 13 |
| holdout/h5 | vest | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 445 | 13 |
| holdout/h5 | vest | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 445 | 13 |
| holdout/h5 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| holdout/h5 | gloves | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| holdout/h5 | goggles | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| holdout/h5 | goggles | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| holdout/h5 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| holdout/h5 | boots | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| holdout/h7 | helmet | v4 | 175 | 250 | 0 | 0 | 12 | 0 | 63 | 0 | 46 | 7 |
| holdout/h7 | helmet | final | 148 | 250 | 0 | 0 | 12 | 0 | 90 | 0 | 0 | 7 |
| holdout/h7 | vest | v4 | 217 | 506 | 0 | 0 | 86 | 0 | 196 | 0 | 0 | 7 |
| holdout/h7 | vest | final | 217 | 506 | 0 | 0 | 86 | 0 | 196 | 0 | 0 | 7 |
| holdout/h7 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 216 | 7 |
| holdout/h7 | gloves | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 216 | 7 |
| holdout/h7 | goggles | v4 | 0 | 0 | 61 | 82 | 0 | 0 | 0 | 21 | 71 | 7 |
| holdout/h7 | goggles | final | 0 | 0 | 61 | 82 | 0 | 0 | 0 | 21 | 58 | 7 |
| holdout/h7 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 54 | 7 |
| holdout/h7 | boots | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 54 | 7 |
| holdout/h8 | helmet | v4 | 290 | 290 | 21 | 22 | 0 | 0 | 0 | 1 | 0 | 0 |
| holdout/h8 | helmet | final | 290 | 290 | 15 | 22 | 0 | 0 | 0 | 7 | 0 | 0 |
| holdout/h8 | vest | v4 | 0 | 0 | 350 | 350 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h8 | vest | final | 0 | 0 | 350 | 350 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h8 | gloves | v4 | 0 | 0 | 181 | 189 | 0 | 0 | 0 | 8 | 3 | 0 |
| holdout/h8 | gloves | final | 0 | 0 | 181 | 189 | 0 | 0 | 0 | 8 | 3 | 0 |
| holdout/h8 | goggles | v4 | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 44 | 0 |
| holdout/h8 | goggles | final | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 25 | 0 |
| holdout/h8 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h8 | boots | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | helmet | v4 | 0 | 0 | 0 | 590 | 0 | 145 | 0 | 445 | 0 | 0 |
| holdout/h9 | helmet | final | 0 | 0 | 0 | 590 | 0 | 113 | 0 | 477 | 0 | 0 |
| holdout/h9 | vest | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | vest | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | gloves | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | goggles | v4 | 127 | 590 | 0 | 0 | 115 | 0 | 348 | 0 | 0 | 0 |
| holdout/h9 | goggles | final | 421 | 590 | 0 | 0 | 92 | 0 | 77 | 0 | 0 | 0 |
| holdout/h9 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | boots | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- holdout/h1, v4: 3 sự kiện: #1 người 1 0.0-13.267s gloves,goggles (session_ended_unverified); #2 người 4 4.2-13.267s gloves,vest (session_ended_unverified); #3 người 7 10.933-13.267s goggles,helmet,vest (session_ended_unverified)
- holdout/h1, final: 3 sự kiện: #1 người 1 0.0-13.267s gloves,goggles (session_ended_unverified); #2 người 4 4.2-13.267s gloves,vest (session_ended_unverified); #3 người 7 10.933-13.267s goggles,helmet,vest (session_ended_unverified)
- holdout/h2, v4: 2 sự kiện: #1 người 1 0.0-9.4s helmet (session_ended_unverified); #2 người 2 5.033-9.4s boots,gloves,goggles,helmet,vest (session_ended_unverified)
- holdout/h2, final: 2 sự kiện: #1 người 1 0.0-9.4s  (session_ended_unverified); #2 người 2 5.033-9.4s boots,gloves,goggles,helmet,vest (session_ended_unverified)
- holdout/h3, v4: 1 sự kiện: #1 người 1 0.0-15.3s boots,helmet,vest (session_ended_unverified)
- holdout/h3, final: 1 sự kiện: #1 người 1 0.0-15.3s boots,vest (session_ended_unverified)
- holdout/h4, v4: 2 sự kiện: #1 người 1 0.0-8.08s  (session_ended_unverified); #2 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h4, final: 2 sự kiện: #1 người 1 0.0-8.08s  (session_ended_unverified); #2 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h5, v4: 1 sự kiện: #1 người 1 0.1-7.758s vest (session_ended_unverified)
- holdout/h5, final: 1 sự kiện: #1 người 1 0.1-7.758s vest (session_ended_unverified)
- holdout/h7, v4: 1 sự kiện: #1 người 1 0.0-9.142s boots,gloves,goggles (session_ended_unverified)
- holdout/h7, final: 1 sự kiện: #1 người 1 0.0-9.142s boots,gloves,goggles (session_ended_unverified)
- holdout/h8, v4: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h8, final: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h9, v4: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)
- holdout/h9, final: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)

## So sánh với cấu hình mốc

### v4_vs_final
- holdout/h1: sự kiện giống nhau (3 / 3); dòng frames.csv 583 / 583, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 583; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|co->chua_xac_dinh': 32}
- holdout/h2: sự kiện KHÁC: [{"index": 1, "field": "missing_items", "a": ["helmet"], "b": []}, {"index": 1, "field": "missing_history", "a": [[0.467, ["boots", "vest"]], [2.433, ["boots"]], [2.567, ["boots", "helmet"]], [2.967, ["helmet"]], [5.667, ["helmet"]], [5.7, ["helmet"]], [5.733, ["helmet"]], [5.833, ["helmet"]], [5.9, ["helmet"]], [5.967, ["helmet"]], [9.033, ["helmet"]], [9.1, ["helmet"]], [9.167, ["helmet"]], [9.233, ["helmet"]], [9.267, ["helmet"]], [9.333, ["helmet"]], [9.4, ["helmet"]]], "b": [[0.467, ["boots", "vest"]], [2.433, ["boots"]], [2.967, []], [5.667, []], [5.7, []], [5.733, []], [5.833, []], [5.9, []], [5.967, []], [9.033, []], [9.1, []], [9.167, []], [9.233, []], [9.267, []], [9.333, []], [9.4, []]]}] (2 / 2); dòng frames.csv 316 / 316, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 316; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|thieu->chua_xac_dinh': 2, 'thieu|thieu->chua_xac_dinh': 220}
- holdout/h3: sự kiện KHÁC: [{"index": 1, "field": "missing_items", "a": ["boots", "helmet", "vest"], "b": ["boots", "vest"]}, {"index": 1, "field": "missing_history", "a": [[0.467, ["boots", "helmet", "vest"]], [15.3, ["boots", "helmet", "vest"]]], "b": [[0.467, ["boots", "vest"]], [15.3, ["boots", "vest"]]]}] (1 / 1); dòng frames.csv 463 / 463, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 463; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|thieu->chua_xac_dinh': 262}
- holdout/h4: sự kiện giống nhau (2 / 2); dòng frames.csv 808 / 808, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 808; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h5: sự kiện giống nhau (1 / 1); dòng frames.csv 459 / 459, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 459; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- holdout/h7: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.234, ["gloves", "vest"]], [1.185, ["boots", "gloves", "vest"]], [2.686, ["boots", "gloves", "goggles", "vest"]], [3.136, ["boots", "gloves", "goggles"]], [5.372, ["boots", "gloves", "goggles"]], [5.389, ["boots", "gloves", "goggles"]], [5.455, ["boots", "gloves", "goggles"]], [5.472, ["boots", "gloves", "goggles"]], [6.256, ["boots", "gloves", "goggles"]], [6.29, ["boots", "gloves", "goggles"]], [6.406, ["boots", "gloves", "goggles"]], [6.423, ["boots", "gloves", "goggles"]], [6.456, ["boots", "gloves", "goggles"]], [6.473, ["boots", "gloves", "goggles"]], [6.49, ["boots", "gloves", "goggles"]], [6.507, ["boots", "gloves", "goggles"]], [6.924, ["boots", "gloves", "goggles"]], [6.94, ["boots", "gloves", "goggles"]], [7.024, ["boots", "gloves", "goggles"]], [7.04, ["boots", "gloves", "goggles"]], [7.057, ["boots", "gloves", "goggles"]], [7.174, ["boots", "gloves", "goggles"]], [7.191, ["boots", "gloves", "goggles"]], [7.207, ["boots", "gloves", "goggles"]], [7.224, ["boots", "gloves", "goggles"]], [7.241, ["boots", "gloves", "goggles"]], [7.291, ["boots", "gloves", "goggles"]], [7.407, ["boots", "gloves", "goggles"]], [8.292, ["boots", "gloves", "goggles"]], [9.142, ["boots", "gloves", "goggles"]]], "b": [[0.234, ["gloves", "vest"]], [1.185, ["boots", "gloves", "vest"]], [2.686, ["boots", "gloves", "goggles", "vest"]], [3.136, ["boots", "gloves", "goggles"]], [5.372, ["boots", "gloves", "goggles"]], [5.389, ["boots", "gloves", "goggles"]], [5.455, ["boots", "gloves", "goggles"]], [5.472, ["boots", "gloves", "goggles"]], [6.256, ["boots", "gloves", "goggles"]], [6.29, ["boots", "gloves", "goggles"]], [6.406, ["boots", "gloves", "goggles"]], [6.423, ["boots", "gloves", "goggles"]], [6.456, ["boots", "gloves", "goggles"]], [6.523, ["boots", "gloves", "goggles"]], [6.924, ["boots", "gloves", "goggles"]], [6.94, ["boots", "gloves", "goggles"]], [6.957, ["boots", "gloves", "goggles"]], [7.007, ["boots", "gloves", "goggles"]], [7.024, ["boots", "gloves", "goggles"]], [7.508, ["boots", "gloves", "goggles"]], [7.541, ["boots", "gloves", "goggles"]], [7.558, ["boots", "gloves", "goggles"]], [7.574, ["boots", "gloves", "goggles"]], [7.608, ["boots", "gloves", "goggles"]], [8.258, ["boots", "gloves", "goggles"]], [9.142, ["boots", "gloves", "goggles"]]]}] (1 / 1); dòng frames.csv 499 / 499, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 499; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|thieu->chua_xac_dinh': 46, 'co|co->chua_xac_dinh': 27}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|thieu->chua_xac_dinh': 13}
- holdout/h8: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.467, ["goggles", "helmet", "vest"]], [1.235, ["gloves", "goggles", "helmet", "vest"]], [2.102, ["gloves", "goggles", "vest"]], [11.678, ["gloves", "goggles", "vest"]]], "b": [[0.467, ["goggles", "helmet", "vest"]], [1.235, ["gloves", "goggles", "helmet", "vest"]], [1.869, ["gloves", "goggles", "vest"]], [11.678, ["gloves", "goggles", "vest"]]]}] (1 / 1); dòng frames.csv 350 / 350, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 350; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'thieu|thieu->chua_xac_dinh': 6}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|thieu->chua_xac_dinh': 19}
- holdout/h9: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.56, ["goggles", "vest"]], [7.52, ["vest"]], [23.72, ["vest"]]], "b": [[0.56, ["goggles", "vest"]], [7.04, ["vest"]], [23.72, ["vest"]]]}] (1 / 1); dòng frames.csv 593 / 593, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 593; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'thieu|co->chua_xac_dinh': 32}
  - goggles (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 294, 'co|thieu->chua_xac_dinh': 23}
