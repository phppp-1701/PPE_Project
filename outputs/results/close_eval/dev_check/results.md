# Kết quả theo khung (2026-11-14T18:30:58)

**Nhãn:** Nhãn video chỉnh tham số video3-6 (data/videos/video<3-6>_notes.txt; một phần do Claude sửa 13/11/2026, chưa người duyệt). Video phát triển, không phải tập đánh giá.

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Cấu hình: `baseline` = `outputs/results/close_eval/pipeline_baseline_0645f53.yaml`, `v4` = `configs/pipeline.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | baseline | 2904 | 3165 | 443 | 508 | 31 | 22 | 191 | 36 | 0 | 46 |
| tổng | helmet | v4 | 2915 | 3165 | 441 | 508 | 21 | 22 | 190 | 38 | 0 | 46 |
| tổng | vest | baseline | 2394 | 2630 | 984 | 1043 | 50 | 3 | 146 | 50 | 0 | 46 |
| tổng | vest | v4 | 2394 | 2630 | 984 | 1043 | 50 | 3 | 146 | 50 | 0 | 46 |
| tổng | gloves | baseline | 693 | 904 | 1680 | 2072 | 0 | 0 | 211 | 363 | 155 | 46 |
| tổng | gloves | v4 | 693 | 904 | 1680 | 2072 | 0 | 0 | 211 | 363 | 155 | 46 |
| tổng | goggles | baseline | 334 | 438 | 2512 | 2886 | 0 | 0 | 104 | 328 | 0 | 46 |
| tổng | goggles | v4 | 334 | 438 | 2512 | 2886 | 0 | 0 | 104 | 328 | 0 | 46 |
| tổng | boots | baseline | 402 | 832 | 562 | 925 | 134 | 1 | 285 | 340 | 9 | 46 |
| tổng | boots | v4 | 402 | 832 | 562 | 925 | 134 | 1 | 285 | 340 | 9 | 46 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video3 | helmet | baseline | 1187 | 1268 | 443 | 508 | 31 | 22 | 11 | 36 | 0 | 46 |
| video3 | helmet | v4 | 1197 | 1268 | 441 | 508 | 21 | 22 | 11 | 38 | 0 | 46 |
| video3 | vest | baseline | 1194 | 1288 | 471 | 488 | 49 | 1 | 5 | 10 | 0 | 46 |
| video3 | vest | v4 | 1194 | 1288 | 471 | 488 | 49 | 1 | 5 | 10 | 0 | 46 |
| video3 | gloves | baseline | 0 | 0 | 1073 | 1428 | 0 | 0 | 0 | 326 | 155 | 46 |
| video3 | gloves | v4 | 0 | 0 | 1073 | 1428 | 0 | 0 | 0 | 326 | 155 | 46 |
| video3 | goggles | baseline | 0 | 0 | 1632 | 1776 | 0 | 0 | 0 | 98 | 0 | 46 |
| video3 | goggles | v4 | 0 | 0 | 1632 | 1776 | 0 | 0 | 0 | 98 | 0 | 46 |
| video3 | boots | baseline | 0 | 134 | 410 | 487 | 114 | 1 | 9 | 54 | 9 | 46 |
| video3 | boots | v4 | 0 | 134 | 410 | 487 | 114 | 1 | 9 | 54 | 9 | 46 |
| video4 | helmet | baseline | 869 | 1047 | 0 | 0 | 0 | 0 | 178 | 0 | 0 | 0 |
| video4 | helmet | v4 | 870 | 1047 | 0 | 0 | 0 | 0 | 177 | 0 | 0 | 0 |
| video4 | vest | baseline | 604 | 698 | 307 | 349 | 1 | 2 | 93 | 40 | 0 | 0 |
| video4 | vest | v4 | 604 | 698 | 307 | 349 | 1 | 2 | 93 | 40 | 0 | 0 |
| video4 | gloves | baseline | 496 | 698 | 0 | 0 | 0 | 0 | 202 | 0 | 0 | 0 |
| video4 | gloves | v4 | 496 | 698 | 0 | 0 | 0 | 0 | 202 | 0 | 0 | 0 |
| video4 | goggles | baseline | 0 | 0 | 468 | 698 | 0 | 0 | 0 | 230 | 0 | 0 |
| video4 | goggles | v4 | 0 | 0 | 468 | 698 | 0 | 0 | 0 | 230 | 0 | 0 |
| video4 | boots | baseline | 402 | 698 | 0 | 0 | 20 | 0 | 276 | 0 | 0 | 0 |
| video4 | boots | v4 | 402 | 698 | 0 | 0 | 20 | 0 | 276 | 0 | 0 | 0 |
| video5 | helmet | baseline | 436 | 438 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| video5 | helmet | v4 | 436 | 438 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| video5 | vest | baseline | 390 | 438 | 0 | 0 | 0 | 0 | 48 | 0 | 0 | 0 |
| video5 | vest | v4 | 390 | 438 | 0 | 0 | 0 | 0 | 48 | 0 | 0 | 0 |
| video5 | gloves | baseline | 0 | 0 | 401 | 438 | 0 | 0 | 0 | 37 | 0 | 0 |
| video5 | gloves | v4 | 0 | 0 | 401 | 438 | 0 | 0 | 0 | 37 | 0 | 0 |
| video5 | goggles | baseline | 334 | 438 | 0 | 0 | 0 | 0 | 104 | 0 | 0 | 0 |
| video5 | goggles | v4 | 334 | 438 | 0 | 0 | 0 | 0 | 104 | 0 | 0 | 0 |
| video5 | boots | baseline | 0 | 0 | 152 | 438 | 0 | 0 | 0 | 286 | 0 | 0 |
| video5 | boots | v4 | 0 | 0 | 152 | 438 | 0 | 0 | 0 | 286 | 0 | 0 |
| video6 | helmet | baseline | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | helmet | v4 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | vest | baseline | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | vest | v4 | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | gloves | baseline | 197 | 206 | 206 | 206 | 0 | 0 | 9 | 0 | 0 | 0 |
| video6 | gloves | v4 | 197 | 206 | 206 | 206 | 0 | 0 | 9 | 0 | 0 | 0 |
| video6 | goggles | baseline | 0 | 0 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | goggles | v4 | 0 | 0 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- video3, baseline: 7 sự kiện: #1 người 1 2.97-65.065s boots,gloves,goggles (session_ended_unverified); #2 người 2 17.518-65.065s boots,gloves,goggles,helmet,vest (session_ended_unverified); #3 người 3 19.052-65.065s boots,gloves,goggles (session_ended_unverified); #4 người 4 35.402-65.065s boots,gloves,goggles (session_ended_unverified); #5 người 5 37.571-65.065s boots,gloves,goggles,helmet (session_ended_unverified); #6 người 6 38.906-65.065s boots,gloves,goggles,vest (session_ended_unverified); #7 người 7 54.721-65.065s boots,gloves,goggles (session_ended_unverified)
- video3, v4: 7 sự kiện: #1 người 1 2.97-65.065s boots,gloves,goggles (session_ended_unverified); #2 người 2 17.518-65.065s boots,gloves,goggles,helmet,vest (session_ended_unverified); #3 người 3 19.052-65.065s boots,gloves,goggles (session_ended_unverified); #4 người 4 35.402-65.065s boots,gloves,goggles (session_ended_unverified); #5 người 5 37.571-65.065s boots,gloves,goggles,helmet (session_ended_unverified); #6 người 6 38.906-65.065s boots,gloves,goggles,vest (session_ended_unverified); #7 người 7 54.721-65.065s boots,gloves,goggles (session_ended_unverified)
- video4, baseline: 3 sự kiện: #1 người 1 0.0-11.633s goggles (session_ended_unverified); #2 người 2 0.0-11.633s vest (session_ended_unverified); #3 người 3 6.133-11.633s goggles (session_ended_unverified)
- video4, v4: 3 sự kiện: #1 người 1 0.0-11.633s goggles (session_ended_unverified); #2 người 2 0.0-11.633s vest (session_ended_unverified); #3 người 3 6.133-11.633s goggles (session_ended_unverified)
- video5, baseline: 2 sự kiện: #1 người 1 0.0-7.3s boots,gloves (session_ended_unverified); #2 người 2 0.0-7.3s boots,gloves (session_ended_unverified)
- video5, v4: 2 sự kiện: #1 người 1 0.0-7.3s boots,gloves (session_ended_unverified); #2 người 2 0.0-7.3s boots,gloves (session_ended_unverified)
- video6, baseline: 2 sự kiện: #1 người 1 0.0-8.24s gloves,goggles (session_ended_unverified); #2 người 2 0.0-8.24s goggles,vest (session_ended_unverified)
- video6, v4: 2 sự kiện: #1 người 1 0.0-8.24s gloves,goggles (session_ended_unverified); #2 người 2 0.0-8.24s goggles,vest (session_ended_unverified)

## So sánh với cấu hình mốc

### baseline_vs_v4
- video3: sự kiện KHÁC: [{"index": 5, "field": "missing_history", "a": [[38.038, ["vest"]], [38.171, ["boots", "goggles", "vest"]], [39.84, ["boots", "goggles"]], [41.108, ["boots", "goggles", "helmet"]], [42.943, ["boots", "gloves", "goggles", "helmet"]], [46.28, ["boots", "gloves", "goggles", "helmet"]], [65.065, ["boots", "gloves", "goggles", "helmet"]]], "b": [[38.038, ["vest"]], [38.171, ["boots", "goggles", "vest"]], [39.84, ["boots", "goggles"]], [41.174, ["boots", "goggles", "helmet"]], [42.943, ["boots", "gloves", "goggles", "helmet"]], [46.28, ["boots", "gloves", "goggles", "helmet"]], [65.065, ["boots", "gloves", "goggles", "helmet"]]]}, {"index": 7, "field": "missing_history", "a": [[55.188, ["boots", "vest"]], [55.255, ["boots", "helmet", "vest"]], [55.589, ["boots", "goggles", "helmet", "vest"]], [55.622, ["boots", "gloves", "goggles", "helmet", "vest"]], [56.423, ["boots", "gloves", "goggles", "vest"]], [56.723, ["boots", "gloves", "goggles"]], [62.796, ["boots", "gloves", "goggles"]], [65.065, ["boots", "gloves", "goggles"]]], "b": [[55.188, ["boots", "vest"]], [55.589, ["boots", "goggles", "vest"]], [55.622, ["boots", "gloves", "goggles", "vest"]], [56.723, ["boots", "gloves", "goggles"]], [62.796, ["boots", "gloves", "goggles"]], [65.065, ["boots", "gloves", "goggles"]]]}] (7 / 7); dòng frames.csv 1741 / 1741, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 1741; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 2, 'co|thieu->chua_xac_dinh': 2, 'co|thieu->co': 8, 'thieu|thieu->chua_xac_dinh': 2}
- video4: sự kiện giống nhau (3 / 3); dòng frames.csv 1047 / 1047, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 1047; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 1}
- video5: sự kiện giống nhau (2 / 2); dòng frames.csv 438 / 438, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 438; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video6: sự kiện giống nhau (2 / 2); dòng frames.csv 412 / 412, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 412; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
