# Kết quả theo khung (2026-11-15T20:57:05)

**Nhãn:** Nhãn video chỉnh tham số video3-6 (một phần do Claude sửa 13/11/2026, chưa người duyệt). Video phát triển, chỉ kiểm hồi quy bước M1.

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Cấu hình: `final` = `outputs/results/close_eval/stepM1/pipeline_final_e40e793.yaml`, `M1` = `outputs/results/close_eval/stepM1/pipeline_M1.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | final | 2915 | 3165 | 441 | 508 | 21 | 22 | 190 | 38 | 0 | 46 |
| tổng | helmet | M1 | 2915 | 3165 | 441 | 508 | 21 | 22 | 190 | 38 | 0 | 46 |
| tổng | vest | final | 2394 | 2630 | 984 | 1043 | 50 | 3 | 146 | 50 | 0 | 46 |
| tổng | vest | M1 | 2394 | 2630 | 984 | 1043 | 50 | 3 | 146 | 50 | 0 | 46 |
| tổng | gloves | final | 693 | 904 | 1680 | 2072 | 0 | 0 | 211 | 363 | 155 | 46 |
| tổng | gloves | M1 | 693 | 904 | 1680 | 2072 | 0 | 0 | 211 | 363 | 155 | 46 |
| tổng | goggles | final | 334 | 438 | 2512 | 2886 | 0 | 0 | 104 | 328 | 0 | 46 |
| tổng | goggles | M1 | 334 | 438 | 2512 | 2886 | 0 | 0 | 104 | 328 | 0 | 46 |
| tổng | boots | final | 402 | 832 | 562 | 925 | 134 | 1 | 285 | 340 | 9 | 46 |
| tổng | boots | M1 | 402 | 832 | 565 | 925 | 134 | 0 | 285 | 338 | 10 | 46 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video3 | helmet | final | 1197 | 1268 | 441 | 508 | 21 | 22 | 11 | 38 | 0 | 46 |
| video3 | helmet | M1 | 1197 | 1268 | 441 | 508 | 21 | 22 | 11 | 38 | 0 | 46 |
| video3 | vest | final | 1194 | 1288 | 471 | 488 | 49 | 1 | 5 | 10 | 0 | 46 |
| video3 | vest | M1 | 1194 | 1288 | 471 | 488 | 49 | 1 | 5 | 10 | 0 | 46 |
| video3 | gloves | final | 0 | 0 | 1073 | 1428 | 0 | 0 | 0 | 326 | 155 | 46 |
| video3 | gloves | M1 | 0 | 0 | 1073 | 1428 | 0 | 0 | 0 | 326 | 155 | 46 |
| video3 | goggles | final | 0 | 0 | 1632 | 1776 | 0 | 0 | 0 | 98 | 0 | 46 |
| video3 | goggles | M1 | 0 | 0 | 1632 | 1776 | 0 | 0 | 0 | 98 | 0 | 46 |
| video3 | boots | final | 0 | 134 | 410 | 487 | 114 | 1 | 9 | 54 | 9 | 46 |
| video3 | boots | M1 | 0 | 134 | 413 | 487 | 114 | 0 | 9 | 52 | 10 | 46 |
| video4 | helmet | final | 870 | 1047 | 0 | 0 | 0 | 0 | 177 | 0 | 0 | 0 |
| video4 | helmet | M1 | 870 | 1047 | 0 | 0 | 0 | 0 | 177 | 0 | 0 | 0 |
| video4 | vest | final | 604 | 698 | 307 | 349 | 1 | 2 | 93 | 40 | 0 | 0 |
| video4 | vest | M1 | 604 | 698 | 307 | 349 | 1 | 2 | 93 | 40 | 0 | 0 |
| video4 | gloves | final | 496 | 698 | 0 | 0 | 0 | 0 | 202 | 0 | 0 | 0 |
| video4 | gloves | M1 | 496 | 698 | 0 | 0 | 0 | 0 | 202 | 0 | 0 | 0 |
| video4 | goggles | final | 0 | 0 | 468 | 698 | 0 | 0 | 0 | 230 | 0 | 0 |
| video4 | goggles | M1 | 0 | 0 | 468 | 698 | 0 | 0 | 0 | 230 | 0 | 0 |
| video4 | boots | final | 402 | 698 | 0 | 0 | 20 | 0 | 276 | 0 | 0 | 0 |
| video4 | boots | M1 | 402 | 698 | 0 | 0 | 20 | 0 | 276 | 0 | 0 | 0 |
| video5 | helmet | final | 436 | 438 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| video5 | helmet | M1 | 436 | 438 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| video5 | vest | final | 390 | 438 | 0 | 0 | 0 | 0 | 48 | 0 | 0 | 0 |
| video5 | vest | M1 | 390 | 438 | 0 | 0 | 0 | 0 | 48 | 0 | 0 | 0 |
| video5 | gloves | final | 0 | 0 | 401 | 438 | 0 | 0 | 0 | 37 | 0 | 0 |
| video5 | gloves | M1 | 0 | 0 | 401 | 438 | 0 | 0 | 0 | 37 | 0 | 0 |
| video5 | goggles | final | 334 | 438 | 0 | 0 | 0 | 0 | 104 | 0 | 0 | 0 |
| video5 | goggles | M1 | 334 | 438 | 0 | 0 | 0 | 0 | 104 | 0 | 0 | 0 |
| video5 | boots | final | 0 | 0 | 152 | 438 | 0 | 0 | 0 | 286 | 0 | 0 |
| video5 | boots | M1 | 0 | 0 | 152 | 438 | 0 | 0 | 0 | 286 | 0 | 0 |
| video6 | helmet | final | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | helmet | M1 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | vest | final | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | vest | M1 | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | gloves | final | 197 | 206 | 206 | 206 | 0 | 0 | 9 | 0 | 0 | 0 |
| video6 | gloves | M1 | 197 | 206 | 206 | 206 | 0 | 0 | 9 | 0 | 0 | 0 |
| video6 | goggles | final | 0 | 0 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | goggles | M1 | 0 | 0 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | boots | final | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | boots | M1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- video3, final: 7 sự kiện: #1 người 1 2.97-65.065s boots,gloves,goggles (session_ended_unverified); #2 người 2 17.518-65.065s boots,gloves,goggles,helmet,vest (session_ended_unverified); #3 người 3 19.052-65.065s boots,gloves,goggles (session_ended_unverified); #4 người 4 35.402-65.065s boots,gloves,goggles (session_ended_unverified); #5 người 5 37.571-65.065s boots,gloves,goggles,helmet (session_ended_unverified); #6 người 6 38.906-65.065s boots,gloves,goggles,vest (session_ended_unverified); #7 người 7 54.721-65.065s boots,gloves,goggles (session_ended_unverified)
- video3, M1: 7 sự kiện: #1 người 1 2.97-65.065s boots,gloves,goggles (session_ended_unverified); #2 người 2 17.518-65.065s boots,gloves,goggles,helmet,vest (session_ended_unverified); #3 người 3 19.052-65.065s boots,gloves,goggles (session_ended_unverified); #4 người 4 35.402-65.065s boots,gloves,goggles (session_ended_unverified); #5 người 5 37.571-65.065s boots,gloves,goggles,helmet (session_ended_unverified); #6 người 6 38.906-65.065s boots,gloves,goggles,vest (session_ended_unverified); #7 người 7 54.721-65.065s boots,gloves,goggles (session_ended_unverified)
- video4, final: 3 sự kiện: #1 người 1 0.0-11.633s goggles (session_ended_unverified); #2 người 2 0.0-11.633s vest (session_ended_unverified); #3 người 3 6.133-11.633s goggles (session_ended_unverified)
- video4, M1: 3 sự kiện: #1 người 1 0.0-11.633s goggles (session_ended_unverified); #2 người 2 0.0-11.633s vest (session_ended_unverified); #3 người 3 6.133-11.633s goggles (session_ended_unverified)
- video5, final: 2 sự kiện: #1 người 1 0.0-7.3s boots,gloves (session_ended_unverified); #2 người 2 0.0-7.3s boots,gloves (session_ended_unverified)
- video5, M1: 2 sự kiện: #1 người 1 0.0-7.3s boots,gloves (session_ended_unverified); #2 người 2 0.0-7.3s boots,gloves (session_ended_unverified)
- video6, final: 2 sự kiện: #1 người 1 0.0-8.24s gloves,goggles (session_ended_unverified); #2 người 2 0.0-8.24s goggles,vest (session_ended_unverified)
- video6, M1: 2 sự kiện: #1 người 1 0.0-8.24s gloves,goggles (session_ended_unverified); #2 người 2 0.0-8.24s goggles,vest (session_ended_unverified)

## So sánh với cấu hình mốc

### final_vs_M1
- video3: sự kiện giống nhau (7 / 7); dòng frames.csv 1741 / 1741, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 1741; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - boots (nhãn|mốc->bản kia): {'chua_xac_dinh|co->chua_xac_dinh': 2, 'chua_xac_dinh|co->thieu': 1, 'thieu|chua_xac_dinh->thieu': 2, 'thieu|co->thieu': 1}
- video4: sự kiện giống nhau (3 / 3); dòng frames.csv 1047 / 1047, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 1047; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video5: sự kiện giống nhau (2 / 2); dòng frames.csv 438 / 438, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 438; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video6: sự kiện giống nhau (2 / 2); dòng frames.csv 412 / 412, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 412; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
