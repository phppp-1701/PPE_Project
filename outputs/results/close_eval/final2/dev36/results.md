# Kết quả theo khung (2026-11-26T02:25:12)

**Nhãn:** nhãn người (video chỉnh tham số)

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Cấu hình: `before` = `outputs/results/c5_eval/zoom_bench/pipeline_zoom_n1.yaml`, `final2` = `configs/pipeline.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | before | 2914 | 3165 | 444 | 508 | 13 | 23 | 202 | 34 | 0 | 43 |
| tổng | helmet | final2 | 2914 | 3165 | 444 | 508 | 13 | 23 | 202 | 34 | 0 | 43 |
| tổng | vest | before | 2430 | 2630 | 1002 | 1043 | 48 | 3 | 114 | 33 | 0 | 43 |
| tổng | vest | final2 | 2430 | 2630 | 1002 | 1043 | 48 | 3 | 114 | 33 | 0 | 43 |
| tổng | gloves | before | 686 | 904 | 1676 | 2072 | 0 | 1 | 218 | 369 | 130 | 43 |
| tổng | gloves | final2 | 754 | 904 | 1676 | 2072 | 0 | 1 | 150 | 369 | 129 | 43 |
| tổng | goggles | before | 357 | 438 | 2474 | 2886 | 0 | 0 | 81 | 369 | 0 | 43 |
| tổng | goggles | final2 | 367 | 438 | 2474 | 2886 | 0 | 0 | 71 | 369 | 0 | 43 |
| tổng | boots | before | 318 | 832 | 551 | 925 | 61 | 0 | 443 | 355 | 21 | 43 |
| tổng | boots | final2 | 651 | 832 | 551 | 925 | 61 | 0 | 110 | 355 | 21 | 43 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video3 | helmet | before | 1202 | 1268 | 444 | 508 | 13 | 23 | 17 | 34 | 0 | 43 |
| video3 | helmet | final2 | 1202 | 1268 | 444 | 508 | 13 | 23 | 17 | 34 | 0 | 43 |
| video3 | vest | before | 1188 | 1288 | 447 | 488 | 48 | 3 | 14 | 33 | 0 | 43 |
| video3 | vest | final2 | 1188 | 1288 | 447 | 488 | 48 | 3 | 14 | 33 | 0 | 43 |
| video3 | gloves | before | 0 | 0 | 1087 | 1428 | 0 | 0 | 0 | 315 | 129 | 43 |
| video3 | gloves | final2 | 0 | 0 | 1087 | 1428 | 0 | 0 | 0 | 315 | 129 | 43 |
| video3 | goggles | before | 0 | 0 | 1639 | 1776 | 0 | 0 | 0 | 94 | 0 | 43 |
| video3 | goggles | final2 | 0 | 0 | 1639 | 1776 | 0 | 0 | 0 | 94 | 0 | 43 |
| video3 | boots | before | 4 | 134 | 401 | 487 | 61 | 0 | 59 | 67 | 21 | 43 |
| video3 | boots | final2 | 60 | 134 | 401 | 487 | 61 | 0 | 3 | 67 | 21 | 43 |
| video4 | helmet | before | 882 | 1047 | 0 | 0 | 0 | 0 | 165 | 0 | 0 | 0 |
| video4 | helmet | final2 | 882 | 1047 | 0 | 0 | 0 | 0 | 165 | 0 | 0 | 0 |
| video4 | vest | before | 664 | 698 | 349 | 349 | 0 | 0 | 34 | 0 | 0 | 0 |
| video4 | vest | final2 | 664 | 698 | 349 | 349 | 0 | 0 | 34 | 0 | 0 | 0 |
| video4 | gloves | before | 481 | 698 | 0 | 0 | 0 | 0 | 217 | 0 | 1 | 0 |
| video4 | gloves | final2 | 548 | 698 | 0 | 0 | 0 | 0 | 150 | 0 | 0 | 0 |
| video4 | goggles | before | 0 | 0 | 423 | 698 | 0 | 0 | 0 | 275 | 0 | 0 |
| video4 | goggles | final2 | 0 | 0 | 423 | 698 | 0 | 0 | 0 | 275 | 0 | 0 |
| video4 | boots | before | 314 | 698 | 0 | 0 | 0 | 0 | 384 | 0 | 0 | 0 |
| video4 | boots | final2 | 591 | 698 | 0 | 0 | 0 | 0 | 107 | 0 | 0 | 0 |
| video5 | helmet | before | 418 | 438 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| video5 | helmet | final2 | 418 | 438 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| video5 | vest | before | 372 | 438 | 0 | 0 | 0 | 0 | 66 | 0 | 0 | 0 |
| video5 | vest | final2 | 372 | 438 | 0 | 0 | 0 | 0 | 66 | 0 | 0 | 0 |
| video5 | gloves | before | 0 | 0 | 383 | 438 | 0 | 1 | 0 | 54 | 0 | 0 |
| video5 | gloves | final2 | 0 | 0 | 383 | 438 | 0 | 1 | 0 | 54 | 0 | 0 |
| video5 | goggles | before | 357 | 438 | 0 | 0 | 0 | 0 | 81 | 0 | 0 | 0 |
| video5 | goggles | final2 | 367 | 438 | 0 | 0 | 0 | 0 | 71 | 0 | 0 | 0 |
| video5 | boots | before | 0 | 0 | 150 | 438 | 0 | 0 | 0 | 288 | 0 | 0 |
| video5 | boots | final2 | 0 | 0 | 150 | 438 | 0 | 0 | 0 | 288 | 0 | 0 |
| video6 | helmet | before | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | helmet | final2 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | vest | before | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | vest | final2 | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | gloves | before | 205 | 206 | 206 | 206 | 0 | 0 | 1 | 0 | 0 | 0 |
| video6 | gloves | final2 | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | goggles | before | 0 | 0 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | goggles | final2 | 0 | 0 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | boots | before | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | boots | final2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- video3, before: 7 sự kiện: #1 người 1 2.936-65.065s gloves,goggles (session_ended_unverified); #2 người 2 17.518-65.065s boots,gloves,goggles,helmet,vest (session_ended_unverified); #3 người 3 19.052-65.065s boots,gloves,goggles (session_ended_unverified); #4 người 4 35.469-65.065s boots,gloves,goggles (session_ended_unverified); #5 người 5 37.471-65.065s boots,gloves,goggles,helmet (session_ended_unverified); #6 người 6 38.839-65.065s boots,gloves,goggles,vest (session_ended_unverified); #7 người 7 54.688-65.065s boots,gloves,goggles (session_ended_unverified)
- video3, final2: 7 sự kiện: #1 người 1 2.936-65.065s gloves,goggles (session_ended_unverified); #2 người 2 17.518-65.065s boots,gloves,goggles,helmet,vest (session_ended_unverified); #3 người 3 19.052-65.065s boots,gloves,goggles (session_ended_unverified); #4 người 4 35.469-65.065s boots,gloves,goggles (session_ended_unverified); #5 người 5 37.471-65.065s boots,gloves,goggles,helmet (session_ended_unverified); #6 người 6 38.839-65.065s boots,gloves,goggles,vest (session_ended_unverified); #7 người 7 54.688-65.065s boots,gloves,goggles (session_ended_unverified)
- video4, before: 3 sự kiện: #1 người 1 0.0-11.633s goggles (session_ended_unverified); #2 người 2 0.0-11.633s vest (session_ended_unverified); #3 người 3 6.133-11.633s goggles (session_ended_unverified)
- video4, final2: 3 sự kiện: #1 người 1 0.0-11.633s goggles (session_ended_unverified); #2 người 2 0.0-11.633s vest (session_ended_unverified); #3 người 3 6.133-11.633s goggles (session_ended_unverified)
- video5, before: 2 sự kiện: #1 người 1 0.0-7.3s boots,gloves (session_ended_unverified); #2 người 2 0.0-7.3s boots,gloves (session_ended_unverified)
- video5, final2: 2 sự kiện: #1 người 1 0.0-7.3s boots,gloves (session_ended_unverified); #2 người 2 0.0-7.3s boots,gloves (session_ended_unverified)
- video6, before: 2 sự kiện: #1 người 1 0.0-8.24s goggles,vest (session_ended_unverified); #2 người 2 0.0-8.24s gloves,goggles (session_ended_unverified)
- video6, final2: 2 sự kiện: #1 người 1 0.0-8.24s goggles,vest (session_ended_unverified); #2 người 2 0.0-8.24s gloves,goggles (session_ended_unverified)

## So sánh với cấu hình mốc

### before_vs_final2
- video3: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[3.403, ["goggles"]], [8.342, ["gloves", "goggles"]], [11.311, ["gloves", "goggles"]], [65.065, ["gloves", "goggles"]]], "b": [[3.403, ["goggles"]], [8.308, ["gloves", "goggles"]], [11.311, ["gloves", "goggles"]], [65.065, ["gloves", "goggles"]]]}] (7 / 7); dòng frames.csv 1746 / 1746, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 1746; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 1}
  - boots (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 56}
- video4: sự kiện giống nhau (3 / 3); dòng frames.csv 1047 / 1047, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 1047; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 127, 'chua_xac_dinh|thieu->co': 1, 'co|chua_xac_dinh->co': 67}
  - boots (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 277}
- video5: sự kiện giống nhau (2 / 2); dòng frames.csv 438 / 438, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 438; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - goggles (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 10}
- video6: sự kiện giống nhau (2 / 2); dòng frames.csv 412 / 412, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 412; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - gloves (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 1}
