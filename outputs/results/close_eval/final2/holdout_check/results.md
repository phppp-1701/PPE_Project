# Kết quả theo khung (2026-11-26T02:18:41)

**Nhãn:** nhãn máy hai lượt, chưa người kiểm định; KIỂM TRA SAU KHI SỬA, KHÔNG CÒN MÙ (số chính thức: final/holdout 16/11)

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Cấu hình: `v4` = `outputs/results/close_eval/final/pipeline_v4_0b756b8.yaml`, `before` = `outputs/results/c5_eval/zoom_bench/pipeline_zoom_n1.yaml`, `final2` = `configs/pipeline.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | v4 | 1805 | 2394 | 241 | 853 | 274 | 145 | 307 | 467 | 51 | 26 |
| tổng | helmet | before | 1704 | 2394 | 100 | 853 | 26 | 39 | 655 | 714 | 18 | 40 |
| tổng | helmet | final2 | 1704 | 2394 | 100 | 853 | 26 | 39 | 655 | 714 | 18 | 40 |
| tổng | vest | v4 | 847 | 1565 | 809 | 809 | 356 | 0 | 349 | 0 | 1265 | 26 |
| tổng | vest | before | 743 | 1565 | 778 | 809 | 351 | 2 | 457 | 29 | 1219 | 40 |
| tổng | vest | final2 | 743 | 1565 | 778 | 809 | 351 | 2 | 457 | 29 | 1219 | 40 |
| tổng | gloves | v4 | 0 | 220 | 293 | 369 | 0 | 0 | 220 | 76 | 317 | 26 |
| tổng | gloves | before | 0 | 220 | 257 | 369 | 0 | 0 | 220 | 112 | 312 | 40 |
| tổng | gloves | final2 | 109 | 220 | 225 | 369 | 0 | 3 | 111 | 141 | 246 | 40 |
| tổng | goggles | v4 | 127 | 590 | 597 | 781 | 115 | 0 | 348 | 178 | 260 | 26 |
| tổng | goggles | before | 297 | 590 | 597 | 781 | 115 | 0 | 178 | 176 | 228 | 40 |
| tổng | goggles | final2 | 423 | 590 | 597 | 781 | 115 | 0 | 52 | 176 | 228 | 40 |
| tổng | boots | v4 | 0 | 0 | 35 | 141 | 0 | 18 | 0 | 88 | 353 | 26 |
| tổng | boots | before | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 22 | 40 |
| tổng | boots | final2 | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 9 | 40 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| holdout/h1 | helmet | v4 | 382 | 398 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 6 |
| holdout/h1 | helmet | before | 353 | 398 | 0 | 0 | 0 | 0 | 40 | 0 | 0 | 5 |
| holdout/h1 | helmet | final2 | 353 | 398 | 0 | 0 | 0 | 0 | 40 | 0 | 0 | 5 |
| holdout/h1 | vest | v4 | 318 | 398 | 0 | 0 | 0 | 0 | 74 | 0 | 0 | 6 |
| holdout/h1 | vest | before | 317 | 398 | 0 | 0 | 0 | 0 | 76 | 0 | 0 | 5 |
| holdout/h1 | vest | final2 | 317 | 398 | 0 | 0 | 0 | 0 | 76 | 0 | 0 | 5 |
| holdout/h1 | gloves | v4 | 0 | 0 | 112 | 180 | 0 | 0 | 0 | 68 | 91 | 6 |
| holdout/h1 | gloves | before | 0 | 0 | 78 | 180 | 0 | 0 | 0 | 102 | 104 | 5 |
| holdout/h1 | gloves | final2 | 0 | 0 | 46 | 180 | 0 | 3 | 0 | 131 | 88 | 5 |
| holdout/h1 | goggles | v4 | 0 | 0 | 243 | 250 | 0 | 0 | 0 | 1 | 145 | 6 |
| holdout/h1 | goggles | before | 0 | 0 | 245 | 250 | 0 | 0 | 0 | 0 | 147 | 5 |
| holdout/h1 | goggles | final2 | 0 | 0 | 245 | 250 | 0 | 0 | 0 | 0 | 147 | 5 |
| holdout/h1 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| holdout/h1 | boots | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| holdout/h1 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| holdout/h2 | helmet | v4 | 0 | 0 | 220 | 241 | 0 | 0 | 0 | 21 | 2 | 0 |
| holdout/h2 | helmet | before | 0 | 0 | 0 | 241 | 0 | 3 | 0 | 238 | 0 | 2 |
| holdout/h2 | helmet | final2 | 0 | 0 | 0 | 241 | 0 | 3 | 0 | 238 | 0 | 2 |
| holdout/h2 | vest | v4 | 234 | 257 | 0 | 0 | 6 | 0 | 17 | 0 | 25 | 0 |
| holdout/h2 | vest | before | 241 | 257 | 0 | 0 | 7 | 0 | 9 | 0 | 23 | 2 |
| holdout/h2 | vest | final2 | 241 | 257 | 0 | 0 | 7 | 0 | 9 | 0 | 23 | 2 |
| holdout/h2 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| holdout/h2 | gloves | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 2 |
| holdout/h2 | gloves | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 2 |
| holdout/h2 | goggles | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h2 | goggles | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| holdout/h2 | goggles | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| holdout/h2 | boots | v4 | 0 | 0 | 35 | 141 | 0 | 18 | 0 | 88 | 5 | 0 |
| holdout/h2 | boots | before | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 0 | 2 |
| holdout/h2 | boots | final2 | 0 | 0 | 121 | 141 | 0 | 0 | 0 | 18 | 0 | 2 |
| holdout/h3 | helmet | v4 | 0 | 459 | 0 | 0 | 262 | 0 | 197 | 0 | 0 | 0 |
| holdout/h3 | helmet | before | 12 | 459 | 0 | 0 | 0 | 0 | 447 | 0 | 0 | 0 |
| holdout/h3 | helmet | final2 | 12 | 459 | 0 | 0 | 0 | 0 | 447 | 0 | 0 | 0 |
| holdout/h3 | vest | v4 | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | vest | before | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | vest | final2 | 0 | 0 | 459 | 459 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | gloves | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | goggles | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h3 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 294 | 0 |
| holdout/h3 | boots | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 | 0 |
| holdout/h3 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 |
| holdout/h4 | helmet | v4 | 522 | 558 | 0 | 0 | 0 | 0 | 36 | 0 | 1 | 0 |
| holdout/h4 | helmet | before | 512 | 558 | 0 | 0 | 7 | 0 | 39 | 0 | 7 | 0 |
| holdout/h4 | helmet | final2 | 512 | 558 | 0 | 0 | 7 | 0 | 39 | 0 | 7 | 0 |
| holdout/h4 | vest | v4 | 78 | 404 | 0 | 0 | 264 | 0 | 62 | 0 | 205 | 0 |
| holdout/h4 | vest | before | 62 | 404 | 0 | 0 | 232 | 0 | 110 | 0 | 168 | 0 |
| holdout/h4 | vest | final2 | 62 | 404 | 0 | 0 | 232 | 0 | 110 | 0 | 168 | 0 |
| holdout/h4 | gloves | v4 | 0 | 220 | 0 | 0 | 0 | 0 | 220 | 0 | 0 | 0 |
| holdout/h4 | gloves | before | 0 | 220 | 0 | 0 | 0 | 0 | 220 | 0 | 0 | 0 |
| holdout/h4 | gloves | final2 | 109 | 220 | 0 | 0 | 0 | 0 | 111 | 0 | 0 | 0 |
| holdout/h4 | goggles | v4 | 0 | 0 | 1 | 157 | 0 | 0 | 0 | 156 | 0 | 0 |
| holdout/h4 | goggles | before | 0 | 0 | 2 | 157 | 0 | 0 | 0 | 155 | 0 | 0 |
| holdout/h4 | goggles | final2 | 0 | 0 | 2 | 157 | 0 | 0 | 0 | 155 | 0 | 0 |
| holdout/h4 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h4 | boots | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h4 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h5 | helmet | v4 | 436 | 439 | 0 | 0 | 0 | 0 | 1 | 0 | 2 | 13 |
| holdout/h5 | helmet | before | 438 | 439 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | helmet | final2 | 438 | 439 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | vest | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 445 | 13 |
| holdout/h5 | vest | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 438 | 24 |
| holdout/h5 | vest | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 438 | 24 |
| holdout/h5 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| holdout/h5 | gloves | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | gloves | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | goggles | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| holdout/h5 | goggles | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | goggles | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| holdout/h5 | boots | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h5 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| holdout/h7 | helmet | v4 | 175 | 250 | 0 | 0 | 12 | 0 | 63 | 0 | 46 | 7 |
| holdout/h7 | helmet | before | 109 | 250 | 0 | 0 | 19 | 0 | 119 | 0 | 11 | 9 |
| holdout/h7 | helmet | final2 | 109 | 250 | 0 | 0 | 19 | 0 | 119 | 0 | 11 | 9 |
| holdout/h7 | vest | v4 | 217 | 506 | 0 | 0 | 86 | 0 | 196 | 0 | 0 | 7 |
| holdout/h7 | vest | before | 123 | 506 | 0 | 0 | 112 | 0 | 262 | 0 | 0 | 9 |
| holdout/h7 | vest | final2 | 123 | 506 | 0 | 0 | 112 | 0 | 262 | 0 | 0 | 9 |
| holdout/h7 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 216 | 7 |
| holdout/h7 | gloves | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 191 | 9 |
| holdout/h7 | gloves | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 141 | 9 |
| holdout/h7 | goggles | v4 | 0 | 0 | 61 | 82 | 0 | 0 | 0 | 21 | 71 | 7 |
| holdout/h7 | goggles | before | 0 | 0 | 58 | 82 | 0 | 0 | 0 | 21 | 56 | 9 |
| holdout/h7 | goggles | final2 | 0 | 0 | 58 | 82 | 0 | 0 | 0 | 21 | 56 | 9 |
| holdout/h7 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 54 | 7 |
| holdout/h7 | boots | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 9 |
| holdout/h7 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| holdout/h8 | helmet | v4 | 290 | 290 | 21 | 22 | 0 | 0 | 0 | 1 | 0 | 0 |
| holdout/h8 | helmet | before | 280 | 290 | 15 | 22 | 0 | 2 | 10 | 5 | 0 | 0 |
| holdout/h8 | helmet | final2 | 280 | 290 | 15 | 22 | 0 | 2 | 10 | 5 | 0 | 0 |
| holdout/h8 | vest | v4 | 0 | 0 | 350 | 350 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h8 | vest | before | 0 | 0 | 319 | 350 | 0 | 2 | 0 | 29 | 0 | 0 |
| holdout/h8 | vest | final2 | 0 | 0 | 319 | 350 | 0 | 2 | 0 | 29 | 0 | 0 |
| holdout/h8 | gloves | v4 | 0 | 0 | 181 | 189 | 0 | 0 | 0 | 8 | 3 | 0 |
| holdout/h8 | gloves | before | 0 | 0 | 179 | 189 | 0 | 0 | 0 | 10 | 3 | 0 |
| holdout/h8 | gloves | final2 | 0 | 0 | 179 | 189 | 0 | 0 | 0 | 10 | 3 | 0 |
| holdout/h8 | goggles | v4 | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 44 | 0 |
| holdout/h8 | goggles | before | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 25 | 0 |
| holdout/h8 | goggles | final2 | 0 | 0 | 292 | 292 | 0 | 0 | 0 | 0 | 25 | 0 |
| holdout/h8 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h8 | boots | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h8 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | helmet | v4 | 0 | 0 | 0 | 590 | 0 | 145 | 0 | 445 | 0 | 0 |
| holdout/h9 | helmet | before | 0 | 0 | 85 | 590 | 0 | 34 | 0 | 471 | 0 | 0 |
| holdout/h9 | helmet | final2 | 0 | 0 | 85 | 590 | 0 | 34 | 0 | 471 | 0 | 0 |
| holdout/h9 | vest | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | vest | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | vest | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 590 | 0 |
| holdout/h9 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | gloves | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | gloves | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | goggles | v4 | 127 | 590 | 0 | 0 | 115 | 0 | 348 | 0 | 0 | 0 |
| holdout/h9 | goggles | before | 297 | 590 | 0 | 0 | 115 | 0 | 178 | 0 | 0 | 0 |
| holdout/h9 | goggles | final2 | 423 | 590 | 0 | 0 | 115 | 0 | 52 | 0 | 0 | 0 |
| holdout/h9 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | boots | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| holdout/h9 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- holdout/h1, v4: 3 sự kiện: #1 người 1 0.0-13.267s gloves,goggles (session_ended_unverified); #2 người 4 4.2-13.267s gloves,vest (session_ended_unverified); #3 người 7 10.933-13.267s goggles,helmet,vest (session_ended_unverified)
- holdout/h1, before: 4 sự kiện: #1 người 1 0.0-13.267s gloves,goggles (session_ended_unverified); #2 người 2 0.433-13.267s goggles,helmet,vest (session_ended_unverified); #3 người 3 4.133-13.267s gloves,helmet,vest (session_ended_unverified); #4 người 5 10.967-13.267s goggles,helmet,vest (session_ended_unverified)
- holdout/h1, final2: 4 sự kiện: #1 người 1 0.0-13.267s goggles (session_ended_unverified); #2 người 2 0.433-13.267s goggles,helmet,vest (session_ended_unverified); #3 người 3 4.133-13.267s gloves,helmet,vest (session_ended_unverified); #4 người 5 10.967-13.267s goggles,helmet,vest (session_ended_unverified)
- holdout/h2, v4: 2 sự kiện: #1 người 1 0.0-9.4s helmet (session_ended_unverified); #2 người 2 5.033-9.4s boots,gloves,goggles,helmet,vest (session_ended_unverified)
- holdout/h2, before: 2 sự kiện: #1 người 1 0.067-9.4s boots (session_ended_unverified); #2 người 2 5.133-9.4s boots,goggles,helmet,vest (session_ended_unverified)
- holdout/h2, final2: 2 sự kiện: #1 người 1 0.067-9.4s  (session_ended_unverified); #2 người 2 5.133-9.4s boots,goggles,helmet,vest (session_ended_unverified)
- holdout/h3, v4: 1 sự kiện: #1 người 1 0.0-15.3s boots,helmet,vest (session_ended_unverified)
- holdout/h3, before: 1 sự kiện: #1 người 1 0.0-15.3s vest (session_ended_unverified)
- holdout/h3, final2: 1 sự kiện: #1 người 1 0.0-15.3s vest (session_ended_unverified)
- holdout/h4, v4: 2 sự kiện: #1 người 1 0.0-8.08s  (session_ended_unverified); #2 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h4, before: 2 sự kiện: #1 người 1 0.0-8.08s  (session_ended_unverified); #2 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h4, final2: 2 sự kiện: #1 người 1 0.0-8.08s  (session_ended_unverified); #2 người 2 0.0-8.08s vest (session_ended_unverified)
- holdout/h5, v4: 1 sự kiện: #1 người 1 0.1-7.758s vest (session_ended_unverified)
- holdout/h5, before: 1 sự kiện: #1 người 1 0.45-7.758s vest (session_ended_unverified)
- holdout/h5, final2: 1 sự kiện: #1 người 1 0.45-7.758s vest (session_ended_unverified)
- holdout/h7, v4: 1 sự kiện: #1 người 1 0.0-9.142s boots,gloves,goggles (session_ended_unverified)
- holdout/h7, before: 1 sự kiện: #1 người 1 0.0-9.142s gloves,goggles (session_ended_unverified)
- holdout/h7, final2: 1 sự kiện: #1 người 1 0.0-9.142s  (session_ended_unverified)
- holdout/h8, v4: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h8, before: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h8, final2: 1 sự kiện: #1 người 1 0.0-11.678s gloves,goggles,vest (session_ended_unverified)
- holdout/h9, v4: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)
- holdout/h9, before: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)
- holdout/h9, final2: 1 sự kiện: #1 người 1 0.0-23.72s vest (session_ended_unverified)

## So sánh với cấu hình mốc

### v4_vs_before
- holdout/h1: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.467, ["goggles"]], [1.967, ["gloves", "goggles"]], [3.433, ["gloves", "goggles"]], [3.467, ["gloves", "goggles"]], [4.7, ["gloves", "goggles"]], [4.733, ["gloves", "goggles"]], [4.933, ["gloves", "goggles"]], [4.967, ["gloves", "goggles"]], [5.1, ["gloves", "goggles"]], [5.133, ["gloves", "goggles"]], [13.267, ["gloves", "goggles"]]], "b": [[0.467, ["goggles"]], [1.967, ["gloves", "goggles"]], [4.967, ["gloves", "goggles"]], [5.0, ["gloves", "goggles"]], [13.267, ["gloves", "goggles"]]]}, {"index": 2, "field": "track_id", "a": 4, "b": 2}, {"index": 2, "field": "start_time", "a": 4.2, "b": 0.433}, {"index": 2, "field": "confirmed_at", "a": 4.667, "b": 1.133}, {"index": 2, "field": "missing_items", "a": ["gloves", "vest"], "b": ["goggles", "helmet", "vest"]}, {"index": 2, "field": "missing_history", "a": [[4.667, ["vest"]], [6.033, ["gloves", "vest"]], [6.5, ["gloves", "vest"]], [13.267, ["gloves", "vest"]]], "b": [[1.133, ["goggles", "helmet", "vest"]], [1.3, ["goggles", "helmet", "vest"]], [1.467, ["goggles", "helmet", "vest"]], [1.5, ["goggles", "helmet", "vest"]], [13.267, ["goggles", "helmet", "vest"]]]}, {"index": 3, "field": "track_id", "a": 7, "b": 3}, {"index": 3, "field": "start_time", "a": 10.933, "b": 4.133}, {"index": 3, "field": "confirmed_at", "a": 11.4, "b": 4.6}, {"index": 3, "field": "missing_items", "a": ["goggles", "helmet", "vest"], "b": ["gloves", "helmet", "vest"]}, {"index": 3, "field": "missing_history", "a": [[11.4, ["goggles", "helmet", "vest"]], [11.933, ["goggles", "helmet", "vest"]], [13.267, ["goggles", "helmet", "vest"]]], "b": [[4.6, ["vest"]], [4.667, ["helmet", "vest"]], [6.3, ["gloves", "helmet", "vest"]], [6.5, ["gloves", "helmet", "vest"]], [13.267, ["gloves", "helmet", "vest"]]]}, {"index": 4, "field": "(thiếu sự kiện)", "a": null, "b": {"track_id": 5, "start_time": 10.967, "confirmed_at": 11.433, "end_time": 13.267, "close_reason": "session_ended_unverified", "event_state": "closed", "missing_items": ["goggles", "helmet", "vest"], "missing_history": [[11.433, ["vest"]], [11.533, ["goggles", "helmet", "vest"]], [11.933, ["goggles", "helmet", "vest"]], [13.267, ["goggles", "helmet", "vest"]]], "index": 4}}] (3 / 4); dòng frames.csv 583 / 577, chỉ ở mốc 169, chỉ ở bản kia 163, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 5, 'co|co->chua_xac_dinh': 35, 'co|khong_ghep->co': 1}
  - vest (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 35, 'co|co->chua_xac_dinh': 36, 'co|khong_ghep->chua_xac_dinh': 1}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->thieu': 20, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1, 'chua_xac_dinh|thieu->chua_xac_dinh': 7, 'thieu|chua_xac_dinh->thieu': 16, 'thieu|thieu->chua_xac_dinh': 50}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->thieu': 3, 'chua_xac_dinh|thieu->chua_xac_dinh': 1, 'thieu|chua_xac_dinh->thieu': 1, 'thieu|khong_ghep->thieu': 1}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1}
- holdout/h2: sự kiện KHÁC: [{"index": 1, "field": "start_time", "a": 0.0, "b": 0.067}, {"index": 1, "field": "confirmed_at", "a": 0.467, "b": 0.533}, {"index": 1, "field": "missing_items", "a": ["helmet"], "b": ["boots"]}, {"index": 1, "field": "missing_history", "a": [[0.467, ["boots", "vest"]], [2.433, ["boots"]], [2.567, ["boots", "helmet"]], [2.967, ["helmet"]], [5.667, ["helmet"]], [5.7, ["helmet"]], [5.733, ["helmet"]], [5.833, ["helmet"]], [5.9, ["helmet"]], [5.967, ["helmet"]], [9.033, ["helmet"]], [9.1, ["helmet"]], [9.167, ["helmet"]], [9.233, ["helmet"]], [9.267, ["helmet"]], [9.333, ["helmet"]], [9.4, ["helmet"]]], "b": [[0.533, ["boots", "vest"]], [2.467, ["boots"]], [9.1, ["boots"]], [9.133, ["boots"]], [9.2, ["boots"]], [9.4, ["boots"]]]}, {"index": 2, "field": "start_time", "a": 5.033, "b": 5.133}, {"index": 2, "field": "confirmed_at", "a": 5.5, "b": 5.8}, {"index": 2, "field": "missing_items", "a": ["boots", "gloves", "goggles", "helmet", "vest"], "b": ["boots", "goggles", "helmet", "vest"]}, {"index": 2, "field": "missing_history", "a": [[5.5, ["boots", "goggles", "helmet", "vest"]], [5.567, ["boots", "gloves", "goggles", "helmet", "vest"]], [6.167, ["boots", "gloves", "goggles", "helmet", "vest"]], [9.4, ["boots", "gloves", "goggles", "helmet", "vest"]]], "b": [[5.8, ["boots", "goggles", "helmet", "vest"]], [6.167, ["boots", "goggles", "helmet", "vest"]], [9.4, ["boots", "goggles", "helmet", "vest"]]]}] (2 / 2); dòng frames.csv 316 / 311, chỉ ở mốc 5, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 2, 'chua_xac_dinh|thieu->chua_xac_dinh': 2, 'thieu|thieu->chua_xac_dinh': 217, 'thieu|thieu->co': 3}
  - vest (nhãn|mốc->bản kia): {'chua_xac_dinh|thieu->khong_ghep': 2, 'co|chua_xac_dinh->co': 10, 'co|co->chua_xac_dinh': 2, 'co|co->thieu': 1}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 2, 'chua_xac_dinh|chua_xac_dinh->thieu': 14, 'chua_xac_dinh|thieu->chua_xac_dinh': 7}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 2}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 3, 'chua_xac_dinh|thieu->chua_xac_dinh': 5, 'thieu|chua_xac_dinh->thieu': 70, 'thieu|co->thieu': 18, 'thieu|thieu->khong_ghep': 2}
- holdout/h3: sự kiện KHÁC: [{"index": 1, "field": "missing_items", "a": ["boots", "helmet", "vest"], "b": ["vest"]}, {"index": 1, "field": "missing_history", "a": [[0.467, ["boots", "helmet", "vest"]], [15.3, ["boots", "helmet", "vest"]]], "b": [[0.467, ["vest"]], [15.3, ["vest"]]]}] (1 / 1); dòng frames.csv 463 / 460, chỉ ở mốc 3, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 4, 'co|thieu->chua_xac_dinh': 254, 'co|thieu->co': 8}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 58, 'chua_xac_dinh|chua_xac_dinh->thieu': 2, 'chua_xac_dinh|thieu->chua_xac_dinh': 157, 'chua_xac_dinh|thieu->co': 126}
- holdout/h4: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.28, ["vest"]], [6.64, ["vest"]], [6.66, ["vest"]], [8.0, []], [8.08, []]], "b": [[0.28, ["vest"]], [6.46, []], [8.08, []]]}, {"index": 2, "field": "missing_history", "a": [[0.28, ["vest"]], [1.6, ["vest"]], [2.88, ["vest"]], [2.9, ["vest"]], [3.12, ["vest"]], [3.14, ["vest"]], [3.16, ["vest"]], [3.18, ["vest"]], [3.36, ["vest"]], [3.38, ["vest"]], [3.42, ["vest"]], [3.48, ["vest"]], [3.6, ["vest"]], [3.62, ["vest"]], [3.78, ["vest"]], [3.8, ["vest"]], [4.5, ["vest"]], [8.08, ["vest"]]], "b": [[0.28, ["vest"]], [0.52, ["vest"]], [0.92, ["vest"]], [1.56, ["vest"]], [3.32, ["vest"]], [3.38, ["vest"]], [3.46, ["vest"]], [3.6, ["vest"]], [3.66, ["vest"]], [3.72, ["vest"]], [3.74, ["vest"]], [3.84, ["vest"]], [4.72, ["vest"]], [4.74, ["vest"]], [4.76, ["vest"]], [4.86, ["vest"]], [4.88, ["vest"]], [5.74, ["vest"]], [5.8, ["vest"]], [8.08, ["vest"]]]}] (2 / 2); dòng frames.csv 808 / 808, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->thieu': 2, 'chua_xac_dinh|co->thieu': 5, 'chua_xac_dinh|thieu->chua_xac_dinh': 1, 'co|chua_xac_dinh->co': 1, 'co|chua_xac_dinh->thieu': 1, 'co|co->chua_xac_dinh': 5, 'co|co->thieu': 6}
  - vest (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->thieu': 27, 'chua_xac_dinh|thieu->chua_xac_dinh': 64, 'co|chua_xac_dinh->co': 14, 'co|co->chua_xac_dinh': 37, 'co|thieu->chua_xac_dinh': 25, 'co|thieu->co': 7}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|co->chua_xac_dinh': 1, 'thieu|chua_xac_dinh->thieu': 2, 'thieu|thieu->chua_xac_dinh': 1}
- holdout/h5: sự kiện KHÁC: [{"index": 1, "field": "start_time", "a": 0.1, "b": 0.45}, {"index": 1, "field": "confirmed_at", "a": 0.434, "b": 0.684}, {"index": 1, "field": "missing_history", "a": [[0.434, ["vest"]], [7.758, ["vest"]]], "b": [[0.684, ["vest"]], [7.758, ["vest"]]]}] (1 / 1); dòng frames.csv 459 / 438, chỉ ở mốc 21, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 10, 'chua_xac_dinh|thieu->khong_ghep': 2, 'co|chua_xac_dinh->co': 1, 'co|khong_ghep->co': 1}
  - vest (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 4, 'chua_xac_dinh|khong_ghep->thieu': 1, 'chua_xac_dinh|thieu->khong_ghep': 8}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 12, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 12, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 12, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1}
- holdout/h7: sự kiện KHÁC: [{"index": 1, "field": "missing_items", "a": ["boots", "gloves", "goggles"], "b": ["gloves", "goggles"]}, {"index": 1, "field": "missing_history", "a": [[0.234, ["gloves", "vest"]], [1.185, ["boots", "gloves", "vest"]], [2.686, ["boots", "gloves", "goggles", "vest"]], [3.136, ["boots", "gloves", "goggles"]], [5.372, ["boots", "gloves", "goggles"]], [5.389, ["boots", "gloves", "goggles"]], [5.455, ["boots", "gloves", "goggles"]], [5.472, ["boots", "gloves", "goggles"]], [6.256, ["boots", "gloves", "goggles"]], [6.29, ["boots", "gloves", "goggles"]], [6.406, ["boots", "gloves", "goggles"]], [6.423, ["boots", "gloves", "goggles"]], [6.456, ["boots", "gloves", "goggles"]], [6.473, ["boots", "gloves", "goggles"]], [6.49, ["boots", "gloves", "goggles"]], [6.507, ["boots", "gloves", "goggles"]], [6.924, ["boots", "gloves", "goggles"]], [6.94, ["boots", "gloves", "goggles"]], [7.024, ["boots", "gloves", "goggles"]], [7.04, ["boots", "gloves", "goggles"]], [7.057, ["boots", "gloves", "goggles"]], [7.174, ["boots", "gloves", "goggles"]], [7.191, ["boots", "gloves", "goggles"]], [7.207, ["boots", "gloves", "goggles"]], [7.224, ["boots", "gloves", "goggles"]], [7.241, ["boots", "gloves", "goggles"]], [7.291, ["boots", "gloves", "goggles"]], [7.407, ["boots", "gloves", "goggles"]], [8.292, ["boots", "gloves", "goggles"]], [9.142, ["boots", "gloves", "goggles"]]], "b": [[0.234, ["vest"]], [0.317, ["gloves", "vest"]], [2.753, ["gloves", "goggles", "vest"]], [3.27, ["gloves", "goggles"]], [3.32, ["gloves", "goggles"]], [3.337, ["gloves", "goggles"]], [3.754, ["gloves", "goggles"]], [3.77, ["gloves", "goggles"]], [4.104, ["gloves", "goggles"]], [4.171, ["gloves", "goggles"]], [4.404, ["gloves", "goggles"]], [4.538, ["gloves", "goggles"]], [4.605, ["gloves", "goggles"]], [4.721, ["gloves", "goggles"]], [6.156, ["gloves", "goggles"]], [6.19, ["gloves", "goggles"]], [6.206, ["gloves", "goggles"]], [6.24, ["gloves", "goggles"]], [6.256, ["gloves", "goggles"]], [6.323, ["gloves", "goggles"]], [6.373, ["gloves", "goggles"]], [6.39, ["gloves", "goggles"]], [6.406, ["gloves", "goggles"]], [6.59, ["gloves", "goggles"]], [6.607, ["gloves", "goggles"]], [6.64, ["gloves", "goggles"]], [6.673, ["gloves", "goggles"]], [6.69, ["gloves", "goggles"]], [6.823, ["gloves", "goggles"]], [7.124, ["gloves", "goggles"]], [7.174, ["gloves", "goggles"]], [7.591, ["gloves", "goggles"]], [8.008, ["gloves", "goggles"]], [8.025, ["gloves", "goggles"]], [8.208, ["gloves", "goggles"]], [8.225, ["gloves", "goggles"]], [8.258, ["gloves", "goggles"]], [9.142, ["gloves", "goggles"]]]}] (1 / 1); dòng frames.csv 499 / 500, chỉ ở mốc 3, chỉ ở bản kia 4, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 2, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 7, 'chua_xac_dinh|chua_xac_dinh->khong_ghep': 2, 'chua_xac_dinh|chua_xac_dinh->thieu': 11, 'chua_xac_dinh|co->chua_xac_dinh': 3, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 4, 'chua_xac_dinh|thieu->chua_xac_dinh': 40, 'chua_xac_dinh|thieu->co': 5, 'chua_xac_dinh|thieu->khong_ghep': 1, 'co|chua_xac_dinh->co': 4, 'co|chua_xac_dinh->thieu': 7, 'co|co->chua_xac_dinh': 67, 'co|co->khong_ghep': 3}
  - vest (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 19, 'co|chua_xac_dinh->khong_ghep': 6, 'co|chua_xac_dinh->thieu': 4, 'co|co->chua_xac_dinh': 91, 'co|co->thieu': 22, 'co|khong_ghep->chua_xac_dinh': 4}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 3, 'chua_xac_dinh|chua_xac_dinh->khong_ghep': 6, 'chua_xac_dinh|chua_xac_dinh->thieu': 12, 'chua_xac_dinh|co->chua_xac_dinh': 2, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 4, 'chua_xac_dinh|thieu->chua_xac_dinh': 37}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 6, 'chua_xac_dinh|chua_xac_dinh->khong_ghep': 2, 'chua_xac_dinh|co->chua_xac_dinh': 1, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 4, 'chua_xac_dinh|thieu->chua_xac_dinh': 14, 'chua_xac_dinh|thieu->khong_ghep': 1, 'thieu|chua_xac_dinh->khong_ghep': 3, 'thieu|chua_xac_dinh->thieu': 1, 'thieu|thieu->chua_xac_dinh': 4}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 3, 'chua_xac_dinh|chua_xac_dinh->khong_ghep': 6, 'chua_xac_dinh|chua_xac_dinh->thieu': 6, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1, 'chua_xac_dinh|khong_ghep->co': 3, 'chua_xac_dinh|thieu->chua_xac_dinh': 10, 'chua_xac_dinh|thieu->co': 41}
- holdout/h8: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.467, ["goggles", "helmet", "vest"]], [1.235, ["gloves", "goggles", "helmet", "vest"]], [2.102, ["gloves", "goggles", "vest"]], [11.678, ["gloves", "goggles", "vest"]]], "b": [[0.467, ["goggles", "helmet", "vest"]], [1.368, ["gloves", "goggles", "helmet", "vest"]], [1.802, ["gloves", "goggles", "vest"]], [11.678, ["gloves", "goggles", "vest"]]]}] (1 / 1); dòng frames.csv 350 / 350, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|co->chua_xac_dinh': 10, 'thieu|thieu->chua_xac_dinh': 4, 'thieu|thieu->co': 2}
  - vest (nhãn|mốc->bản kia): {'thieu|thieu->chua_xac_dinh': 29, 'thieu|thieu->co': 2}
  - gloves (nhãn|mốc->bản kia): {'thieu|thieu->chua_xac_dinh': 2}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|thieu->chua_xac_dinh': 19}
- holdout/h9: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.56, ["goggles", "vest"]], [7.52, ["vest"]], [23.72, ["vest"]]], "b": [[0.56, ["goggles", "helmet", "vest"]], [7.56, ["helmet", "vest"]], [20.64, ["vest"]], [23.72, ["vest"]]]}] (1 / 1); dòng frames.csv 593 / 593, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'thieu|chua_xac_dinh->co': 30, 'thieu|chua_xac_dinh->thieu': 3, 'thieu|co->chua_xac_dinh': 59, 'thieu|co->thieu': 82}
  - goggles (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 159, 'co|chua_xac_dinh->thieu': 38, 'co|co->chua_xac_dinh': 12, 'co|thieu->chua_xac_dinh': 15, 'co|thieu->co': 23}
### v4_vs_final2
- holdout/h1: sự kiện KHÁC: [{"index": 1, "field": "missing_items", "a": ["gloves", "goggles"], "b": ["goggles"]}, {"index": 1, "field": "missing_history", "a": [[0.467, ["goggles"]], [1.967, ["gloves", "goggles"]], [3.433, ["gloves", "goggles"]], [3.467, ["gloves", "goggles"]], [4.7, ["gloves", "goggles"]], [4.733, ["gloves", "goggles"]], [4.933, ["gloves", "goggles"]], [4.967, ["gloves", "goggles"]], [5.1, ["gloves", "goggles"]], [5.133, ["gloves", "goggles"]], [13.267, ["gloves", "goggles"]]], "b": [[0.467, ["goggles"]], [1.967, ["gloves", "goggles"]], [4.967, ["gloves", "goggles"]], [5.0, ["gloves", "goggles"]], [10.033, ["goggles"]], [13.267, ["goggles"]]]}, {"index": 2, "field": "track_id", "a": 4, "b": 2}, {"index": 2, "field": "start_time", "a": 4.2, "b": 0.433}, {"index": 2, "field": "confirmed_at", "a": 4.667, "b": 1.133}, {"index": 2, "field": "missing_items", "a": ["gloves", "vest"], "b": ["goggles", "helmet", "vest"]}, {"index": 2, "field": "missing_history", "a": [[4.667, ["vest"]], [6.033, ["gloves", "vest"]], [6.5, ["gloves", "vest"]], [13.267, ["gloves", "vest"]]], "b": [[1.133, ["goggles", "helmet", "vest"]], [1.3, ["goggles", "helmet", "vest"]], [1.467, ["goggles", "helmet", "vest"]], [1.5, ["goggles", "helmet", "vest"]], [13.267, ["goggles", "helmet", "vest"]]]}, {"index": 3, "field": "track_id", "a": 7, "b": 3}, {"index": 3, "field": "start_time", "a": 10.933, "b": 4.133}, {"index": 3, "field": "confirmed_at", "a": 11.4, "b": 4.6}, {"index": 3, "field": "missing_items", "a": ["goggles", "helmet", "vest"], "b": ["gloves", "helmet", "vest"]}, {"index": 3, "field": "missing_history", "a": [[11.4, ["goggles", "helmet", "vest"]], [11.933, ["goggles", "helmet", "vest"]], [13.267, ["goggles", "helmet", "vest"]]], "b": [[4.6, ["vest"]], [4.667, ["helmet", "vest"]], [6.3, ["gloves", "helmet", "vest"]], [6.5, ["gloves", "helmet", "vest"]], [13.267, ["gloves", "helmet", "vest"]]]}, {"index": 4, "field": "(thiếu sự kiện)", "a": null, "b": {"track_id": 5, "start_time": 10.967, "confirmed_at": 11.433, "end_time": 13.267, "close_reason": "session_ended_unverified", "event_state": "closed", "missing_items": ["goggles", "helmet", "vest"], "missing_history": [[11.433, ["vest"]], [11.533, ["goggles", "helmet", "vest"]], [11.933, ["goggles", "helmet", "vest"]], [13.267, ["goggles", "helmet", "vest"]]], "index": 4}}] (3 / 4); dòng frames.csv 583 / 577, chỉ ở mốc 169, chỉ ở bản kia 163, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 5, 'co|co->chua_xac_dinh': 35, 'co|khong_ghep->co': 1}
  - vest (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 35, 'co|co->chua_xac_dinh': 36, 'co|khong_ghep->chua_xac_dinh': 1}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 21, 'chua_xac_dinh|chua_xac_dinh->thieu': 20, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1, 'chua_xac_dinh|thieu->chua_xac_dinh': 23, 'thieu|chua_xac_dinh->co': 1, 'thieu|chua_xac_dinh->thieu': 7, 'thieu|thieu->chua_xac_dinh': 71, 'thieu|thieu->co': 2}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->thieu': 3, 'chua_xac_dinh|thieu->chua_xac_dinh': 1, 'thieu|chua_xac_dinh->thieu': 1, 'thieu|khong_ghep->thieu': 1}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1}
- holdout/h2: sự kiện KHÁC: [{"index": 1, "field": "start_time", "a": 0.0, "b": 0.067}, {"index": 1, "field": "confirmed_at", "a": 0.467, "b": 0.533}, {"index": 1, "field": "missing_items", "a": ["helmet"], "b": []}, {"index": 1, "field": "missing_history", "a": [[0.467, ["boots", "vest"]], [2.433, ["boots"]], [2.567, ["boots", "helmet"]], [2.967, ["helmet"]], [5.667, ["helmet"]], [5.7, ["helmet"]], [5.733, ["helmet"]], [5.833, ["helmet"]], [5.9, ["helmet"]], [5.967, ["helmet"]], [9.033, ["helmet"]], [9.1, ["helmet"]], [9.167, ["helmet"]], [9.233, ["helmet"]], [9.267, ["helmet"]], [9.333, ["helmet"]], [9.4, ["helmet"]]], "b": [[0.533, ["boots", "vest"]], [2.467, ["boots"]], [5.733, []], [9.1, []], [9.133, []], [9.367, []], [9.4, []]]}, {"index": 2, "field": "start_time", "a": 5.033, "b": 5.133}, {"index": 2, "field": "confirmed_at", "a": 5.5, "b": 5.8}, {"index": 2, "field": "missing_items", "a": ["boots", "gloves", "goggles", "helmet", "vest"], "b": ["boots", "goggles", "helmet", "vest"]}, {"index": 2, "field": "missing_history", "a": [[5.5, ["boots", "goggles", "helmet", "vest"]], [5.567, ["boots", "gloves", "goggles", "helmet", "vest"]], [6.167, ["boots", "gloves", "goggles", "helmet", "vest"]], [9.4, ["boots", "gloves", "goggles", "helmet", "vest"]]], "b": [[5.8, ["boots", "goggles", "helmet", "vest"]], [6.167, ["boots", "goggles", "helmet", "vest"]], [9.4, ["boots", "goggles", "helmet", "vest"]]]}] (2 / 2); dòng frames.csv 316 / 311, chỉ ở mốc 5, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 2, 'chua_xac_dinh|thieu->chua_xac_dinh': 2, 'thieu|thieu->chua_xac_dinh': 217, 'thieu|thieu->co': 3}
  - vest (nhãn|mốc->bản kia): {'chua_xac_dinh|thieu->khong_ghep': 2, 'co|chua_xac_dinh->co': 10, 'co|co->chua_xac_dinh': 2, 'co|co->thieu': 1}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 2, 'chua_xac_dinh|chua_xac_dinh->thieu': 14, 'chua_xac_dinh|thieu->chua_xac_dinh': 7}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 2}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 59, 'chua_xac_dinh|thieu->chua_xac_dinh': 3, 'chua_xac_dinh|thieu->co': 2, 'thieu|chua_xac_dinh->thieu': 70, 'thieu|co->thieu': 18, 'thieu|thieu->khong_ghep': 2}
- holdout/h3: sự kiện KHÁC: [{"index": 1, "field": "missing_items", "a": ["boots", "helmet", "vest"], "b": ["vest"]}, {"index": 1, "field": "missing_history", "a": [[0.467, ["boots", "helmet", "vest"]], [15.3, ["boots", "helmet", "vest"]]], "b": [[0.467, ["vest"]], [15.3, ["vest"]]]}] (1 / 1); dòng frames.csv 463 / 460, chỉ ở mốc 3, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 4, 'co|thieu->chua_xac_dinh': 254, 'co|thieu->co': 8}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 150, 'chua_xac_dinh|thieu->chua_xac_dinh': 20, 'chua_xac_dinh|thieu->co': 265}
- holdout/h4: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.28, ["vest"]], [6.64, ["vest"]], [6.66, ["vest"]], [8.0, []], [8.08, []]], "b": [[0.28, ["vest"]], [6.46, []], [8.08, []]]}, {"index": 2, "field": "missing_history", "a": [[0.28, ["vest"]], [1.6, ["vest"]], [2.88, ["vest"]], [2.9, ["vest"]], [3.12, ["vest"]], [3.14, ["vest"]], [3.16, ["vest"]], [3.18, ["vest"]], [3.36, ["vest"]], [3.38, ["vest"]], [3.42, ["vest"]], [3.48, ["vest"]], [3.6, ["vest"]], [3.62, ["vest"]], [3.78, ["vest"]], [3.8, ["vest"]], [4.5, ["vest"]], [8.08, ["vest"]]], "b": [[0.28, ["vest"]], [0.52, ["vest"]], [0.92, ["vest"]], [1.56, ["vest"]], [3.32, ["vest"]], [3.38, ["vest"]], [3.46, ["vest"]], [3.6, ["vest"]], [3.66, ["vest"]], [3.72, ["vest"]], [3.74, ["vest"]], [3.84, ["vest"]], [4.72, ["vest"]], [4.74, ["vest"]], [4.76, ["vest"]], [4.86, ["vest"]], [4.88, ["vest"]], [5.74, ["vest"]], [5.8, ["vest"]], [8.08, ["vest"]]]}] (2 / 2); dòng frames.csv 808 / 808, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->thieu': 2, 'chua_xac_dinh|co->thieu': 5, 'chua_xac_dinh|thieu->chua_xac_dinh': 1, 'co|chua_xac_dinh->co': 1, 'co|chua_xac_dinh->thieu': 1, 'co|co->chua_xac_dinh': 5, 'co|co->thieu': 6}
  - vest (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->thieu': 27, 'chua_xac_dinh|thieu->chua_xac_dinh': 64, 'co|chua_xac_dinh->co': 14, 'co|co->chua_xac_dinh': 37, 'co|thieu->chua_xac_dinh': 25, 'co|thieu->co': 7}
  - gloves (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 109}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|co->chua_xac_dinh': 1, 'thieu|chua_xac_dinh->thieu': 2, 'thieu|thieu->chua_xac_dinh': 1}
- holdout/h5: sự kiện KHÁC: [{"index": 1, "field": "start_time", "a": 0.1, "b": 0.45}, {"index": 1, "field": "confirmed_at", "a": 0.434, "b": 0.684}, {"index": 1, "field": "missing_history", "a": [[0.434, ["vest"]], [7.758, ["vest"]]], "b": [[0.684, ["vest"]], [7.758, ["vest"]]]}] (1 / 1); dòng frames.csv 459 / 438, chỉ ở mốc 21, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 10, 'chua_xac_dinh|thieu->khong_ghep': 2, 'co|chua_xac_dinh->co': 1, 'co|khong_ghep->co': 1}
  - vest (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 4, 'chua_xac_dinh|khong_ghep->thieu': 1, 'chua_xac_dinh|thieu->khong_ghep': 8}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 12, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 12, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->khong_ghep': 12, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1}
- holdout/h7: sự kiện KHÁC: [{"index": 1, "field": "missing_items", "a": ["boots", "gloves", "goggles"], "b": []}, {"index": 1, "field": "missing_history", "a": [[0.234, ["gloves", "vest"]], [1.185, ["boots", "gloves", "vest"]], [2.686, ["boots", "gloves", "goggles", "vest"]], [3.136, ["boots", "gloves", "goggles"]], [5.372, ["boots", "gloves", "goggles"]], [5.389, ["boots", "gloves", "goggles"]], [5.455, ["boots", "gloves", "goggles"]], [5.472, ["boots", "gloves", "goggles"]], [6.256, ["boots", "gloves", "goggles"]], [6.29, ["boots", "gloves", "goggles"]], [6.406, ["boots", "gloves", "goggles"]], [6.423, ["boots", "gloves", "goggles"]], [6.456, ["boots", "gloves", "goggles"]], [6.473, ["boots", "gloves", "goggles"]], [6.49, ["boots", "gloves", "goggles"]], [6.507, ["boots", "gloves", "goggles"]], [6.924, ["boots", "gloves", "goggles"]], [6.94, ["boots", "gloves", "goggles"]], [7.024, ["boots", "gloves", "goggles"]], [7.04, ["boots", "gloves", "goggles"]], [7.057, ["boots", "gloves", "goggles"]], [7.174, ["boots", "gloves", "goggles"]], [7.191, ["boots", "gloves", "goggles"]], [7.207, ["boots", "gloves", "goggles"]], [7.224, ["boots", "gloves", "goggles"]], [7.241, ["boots", "gloves", "goggles"]], [7.291, ["boots", "gloves", "goggles"]], [7.407, ["boots", "gloves", "goggles"]], [8.292, ["boots", "gloves", "goggles"]], [9.142, ["boots", "gloves", "goggles"]]], "b": [[0.234, ["vest"]], [0.317, ["gloves", "vest"]], [2.753, ["gloves", "goggles", "vest"]], [3.27, ["gloves", "goggles"]], [4.221, ["goggles"]], [4.938, []], [6.823, []], [7.124, []], [8.258, []], [8.325, []], [8.358, []], [9.142, []]]}] (1 / 1); dòng frames.csv 499 / 500, chỉ ở mốc 3, chỉ ở bản kia 4, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 2, 'gloves': 3, 'goggles': 0, 'boots': 3}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 7, 'chua_xac_dinh|chua_xac_dinh->khong_ghep': 2, 'chua_xac_dinh|chua_xac_dinh->thieu': 11, 'chua_xac_dinh|co->chua_xac_dinh': 3, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 4, 'chua_xac_dinh|thieu->chua_xac_dinh': 40, 'chua_xac_dinh|thieu->co': 5, 'chua_xac_dinh|thieu->khong_ghep': 1, 'co|chua_xac_dinh->co': 4, 'co|chua_xac_dinh->thieu': 7, 'co|co->chua_xac_dinh': 67, 'co|co->khong_ghep': 3}
  - vest (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 19, 'co|chua_xac_dinh->khong_ghep': 6, 'co|chua_xac_dinh->thieu': 4, 'co|co->chua_xac_dinh': 91, 'co|co->thieu': 22, 'co|khong_ghep->chua_xac_dinh': 4}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 133, 'chua_xac_dinh|chua_xac_dinh->khong_ghep': 6, 'chua_xac_dinh|chua_xac_dinh->thieu': 1, 'chua_xac_dinh|co->chua_xac_dinh': 2, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 4, 'chua_xac_dinh|thieu->chua_xac_dinh': 76}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 132, 'chua_xac_dinh|chua_xac_dinh->khong_ghep': 2, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 4, 'chua_xac_dinh|thieu->chua_xac_dinh': 4, 'chua_xac_dinh|thieu->co': 10, 'chua_xac_dinh|thieu->khong_ghep': 1, 'thieu|chua_xac_dinh->khong_ghep': 3, 'thieu|chua_xac_dinh->thieu': 1, 'thieu|thieu->chua_xac_dinh': 4}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 253, 'chua_xac_dinh|chua_xac_dinh->khong_ghep': 6, 'chua_xac_dinh|khong_ghep->chua_xac_dinh': 1, 'chua_xac_dinh|khong_ghep->co': 3, 'chua_xac_dinh|thieu->co': 54}
- holdout/h8: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.467, ["goggles", "helmet", "vest"]], [1.235, ["gloves", "goggles", "helmet", "vest"]], [2.102, ["gloves", "goggles", "vest"]], [11.678, ["gloves", "goggles", "vest"]]], "b": [[0.467, ["goggles", "helmet", "vest"]], [1.368, ["gloves", "goggles", "helmet", "vest"]], [1.802, ["gloves", "goggles", "vest"]], [11.678, ["gloves", "goggles", "vest"]]]}] (1 / 1); dòng frames.csv 350 / 350, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|co->chua_xac_dinh': 10, 'thieu|thieu->chua_xac_dinh': 4, 'thieu|thieu->co': 2}
  - vest (nhãn|mốc->bản kia): {'thieu|thieu->chua_xac_dinh': 29, 'thieu|thieu->co': 2}
  - gloves (nhãn|mốc->bản kia): {'thieu|thieu->chua_xac_dinh': 2}
  - goggles (nhãn|mốc->bản kia): {'chua_xac_dinh|thieu->chua_xac_dinh': 19}
- holdout/h9: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[0.56, ["goggles", "vest"]], [7.52, ["vest"]], [23.72, ["vest"]]], "b": [[0.56, ["goggles", "helmet", "vest"]], [7.48, ["helmet", "vest"]], [20.64, ["vest"]], [23.72, ["vest"]]]}] (1 / 1); dòng frames.csv 593 / 593, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 0; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'thieu|chua_xac_dinh->co': 30, 'thieu|chua_xac_dinh->thieu': 3, 'thieu|co->chua_xac_dinh': 59, 'thieu|co->thieu': 82}
  - goggles (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 273, 'co|chua_xac_dinh->thieu': 38, 'co|thieu->chua_xac_dinh': 15, 'co|thieu->co': 23}
