# Kết quả theo khung (2026-11-28T00:22:03)

**Nhãn:** video3-6 nhãn người (chỉnh tham số)

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Cấu hình: `base` = `outputs/results/close_eval/stepM1z/pipeline_base.yaml`, `M1` = `outputs/results/close_eval/stepM1z/pipeline_M1.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | base | 2914 | 3165 | 444 | 508 | 13 | 23 | 202 | 34 | 0 | 43 |
| tổng | helmet | M1 | 2916 | 3165 | 444 | 508 | 11 | 23 | 202 | 34 | 0 | 43 |
| tổng | vest | base | 2505 | 2630 | 1002 | 1043 | 48 | 3 | 39 | 33 | 0 | 43 |
| tổng | vest | M1 | 2505 | 2630 | 1002 | 1043 | 48 | 3 | 39 | 33 | 0 | 43 |
| tổng | gloves | base | 754 | 904 | 1676 | 2072 | 0 | 1 | 150 | 369 | 129 | 43 |
| tổng | gloves | M1 | 754 | 904 | 1676 | 2072 | 0 | 1 | 150 | 369 | 129 | 43 |
| tổng | goggles | base | 367 | 438 | 2474 | 2886 | 0 | 0 | 71 | 369 | 0 | 43 |
| tổng | goggles | M1 | 367 | 438 | 2474 | 2886 | 0 | 0 | 71 | 369 | 0 | 43 |
| tổng | boots | base | 651 | 832 | 551 | 925 | 61 | 0 | 110 | 355 | 21 | 43 |
| tổng | boots | M1 | 651 | 832 | 551 | 925 | 61 | 0 | 110 | 355 | 21 | 43 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video3 | helmet | base | 1202 | 1268 | 444 | 508 | 13 | 23 | 17 | 34 | 0 | 43 |
| video3 | helmet | M1 | 1204 | 1268 | 444 | 508 | 11 | 23 | 17 | 34 | 0 | 43 |
| video3 | vest | base | 1188 | 1288 | 447 | 488 | 48 | 3 | 14 | 33 | 0 | 43 |
| video3 | vest | M1 | 1188 | 1288 | 447 | 488 | 48 | 3 | 14 | 33 | 0 | 43 |
| video3 | gloves | base | 0 | 0 | 1087 | 1428 | 0 | 0 | 0 | 315 | 129 | 43 |
| video3 | gloves | M1 | 0 | 0 | 1087 | 1428 | 0 | 0 | 0 | 315 | 129 | 43 |
| video3 | goggles | base | 0 | 0 | 1639 | 1776 | 0 | 0 | 0 | 94 | 0 | 43 |
| video3 | goggles | M1 | 0 | 0 | 1639 | 1776 | 0 | 0 | 0 | 94 | 0 | 43 |
| video3 | boots | base | 60 | 134 | 401 | 487 | 61 | 0 | 3 | 67 | 21 | 43 |
| video3 | boots | M1 | 60 | 134 | 401 | 487 | 61 | 0 | 3 | 67 | 21 | 43 |
| video4 | helmet | base | 882 | 1047 | 0 | 0 | 0 | 0 | 165 | 0 | 0 | 0 |
| video4 | helmet | M1 | 882 | 1047 | 0 | 0 | 0 | 0 | 165 | 0 | 0 | 0 |
| video4 | vest | base | 693 | 698 | 349 | 349 | 0 | 0 | 5 | 0 | 0 | 0 |
| video4 | vest | M1 | 693 | 698 | 349 | 349 | 0 | 0 | 5 | 0 | 0 | 0 |
| video4 | gloves | base | 548 | 698 | 0 | 0 | 0 | 0 | 150 | 0 | 0 | 0 |
| video4 | gloves | M1 | 548 | 698 | 0 | 0 | 0 | 0 | 150 | 0 | 0 | 0 |
| video4 | goggles | base | 0 | 0 | 423 | 698 | 0 | 0 | 0 | 275 | 0 | 0 |
| video4 | goggles | M1 | 0 | 0 | 423 | 698 | 0 | 0 | 0 | 275 | 0 | 0 |
| video4 | boots | base | 591 | 698 | 0 | 0 | 0 | 0 | 107 | 0 | 0 | 0 |
| video4 | boots | M1 | 591 | 698 | 0 | 0 | 0 | 0 | 107 | 0 | 0 | 0 |
| video5 | helmet | base | 418 | 438 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| video5 | helmet | M1 | 418 | 438 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| video5 | vest | base | 418 | 438 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| video5 | vest | M1 | 418 | 438 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| video5 | gloves | base | 0 | 0 | 383 | 438 | 0 | 1 | 0 | 54 | 0 | 0 |
| video5 | gloves | M1 | 0 | 0 | 383 | 438 | 0 | 1 | 0 | 54 | 0 | 0 |
| video5 | goggles | base | 367 | 438 | 0 | 0 | 0 | 0 | 71 | 0 | 0 | 0 |
| video5 | goggles | M1 | 367 | 438 | 0 | 0 | 0 | 0 | 71 | 0 | 0 | 0 |
| video5 | boots | base | 0 | 0 | 150 | 438 | 0 | 0 | 0 | 288 | 0 | 0 |
| video5 | boots | M1 | 0 | 0 | 150 | 438 | 0 | 0 | 0 | 288 | 0 | 0 |
| video6 | helmet | base | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | helmet | M1 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | vest | base | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | vest | M1 | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | gloves | base | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | gloves | M1 | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | goggles | base | 0 | 0 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | goggles | M1 | 0 | 0 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | boots | base | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | boots | M1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- video3, base: 7 sự kiện: #1 người 1 2.936-65.065s gloves,goggles (session_ended_unverified); #2 người 2 17.518-65.065s boots,gloves,goggles,helmet,vest (session_ended_unverified); #3 người 3 19.052-65.065s boots,gloves,goggles (session_ended_unverified); #4 người 4 35.469-65.065s boots,gloves,goggles (session_ended_unverified); #5 người 5 37.471-65.065s boots,gloves,goggles,helmet (session_ended_unverified); #6 người 6 38.839-65.065s boots,gloves,goggles,vest (session_ended_unverified); #7 người 7 54.688-65.065s boots,gloves,goggles (session_ended_unverified)
- video3, M1: 7 sự kiện: #1 người 1 2.936-65.065s gloves,goggles (session_ended_unverified); #2 người 2 17.518-65.065s boots,gloves,goggles,helmet,vest (session_ended_unverified); #3 người 3 19.052-65.065s boots,gloves,goggles (session_ended_unverified); #4 người 4 35.469-65.065s boots,gloves,goggles (session_ended_unverified); #5 người 5 37.471-65.065s boots,gloves,goggles,helmet (session_ended_unverified); #6 người 6 38.839-65.065s boots,gloves,goggles,vest (session_ended_unverified); #7 người 7 54.688-65.065s boots,gloves,goggles (session_ended_unverified)
- video4, base: 3 sự kiện: #1 người 1 0.0-11.633s goggles (session_ended_unverified); #2 người 2 0.0-11.633s vest (session_ended_unverified); #3 người 3 6.133-11.633s goggles (session_ended_unverified)
- video4, M1: 3 sự kiện: #1 người 1 0.0-11.633s goggles (session_ended_unverified); #2 người 2 0.0-11.633s vest (session_ended_unverified); #3 người 3 6.133-11.633s goggles (session_ended_unverified)
- video5, base: 2 sự kiện: #1 người 1 0.0-7.3s boots,gloves (session_ended_unverified); #2 người 2 0.0-7.3s boots,gloves (session_ended_unverified)
- video5, M1: 2 sự kiện: #1 người 1 0.0-7.3s boots,gloves (session_ended_unverified); #2 người 2 0.0-7.3s boots,gloves (session_ended_unverified)
- video6, base: 2 sự kiện: #1 người 1 0.0-8.24s goggles,vest (session_ended_unverified); #2 người 2 0.0-8.24s gloves,goggles (session_ended_unverified)
- video6, M1: 2 sự kiện: #1 người 1 0.0-8.24s goggles,vest (session_ended_unverified); #2 người 2 0.0-8.24s gloves,goggles (session_ended_unverified)

## So sánh với cấu hình mốc

### base_vs_M1
- video3: sự kiện giống nhau (7 / 7); dòng frames.csv 1746 / 1746, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 1746; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|thieu->co': 2}
- video4: sự kiện giống nhau (3 / 3); dòng frames.csv 1047 / 1047, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 1047; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video5: sự kiện giống nhau (2 / 2); dòng frames.csv 438 / 438, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 438; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video6: sự kiện giống nhau (2 / 2); dòng frames.csv 412 / 412, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 412; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
