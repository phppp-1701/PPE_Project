# Kết quả theo khung (2026-11-25T13:51:20)

**Nhãn:** nhãn người (video chỉnh tham số)

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Cấu hình: `base` = `outputs/results/close_eval/stepF2/pipeline_base.yaml`, `F2` = `outputs/results/close_eval/stepF2/pipeline_F2.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | base | 2914 | 3165 | 444 | 508 | 13 | 23 | 202 | 34 | 0 | 43 |
| tổng | helmet | F2 | 2970 | 3165 | 444 | 508 | 13 | 34 | 146 | 23 | 0 | 43 |
| tổng | vest | base | 2430 | 2630 | 1002 | 1043 | 48 | 3 | 114 | 33 | 0 | 43 |
| tổng | vest | F2 | 2524 | 2630 | 1002 | 1043 | 48 | 33 | 20 | 3 | 0 | 43 |
| tổng | gloves | base | 686 | 904 | 1676 | 2072 | 0 | 1 | 218 | 369 | 130 | 43 |
| tổng | gloves | F2 | 753 | 904 | 1676 | 2072 | 0 | 1 | 151 | 369 | 130 | 43 |
| tổng | goggles | base | 357 | 438 | 2474 | 2886 | 0 | 0 | 81 | 369 | 0 | 43 |
| tổng | goggles | F2 | 367 | 438 | 2474 | 2886 | 0 | 0 | 71 | 369 | 0 | 43 |
| tổng | boots | base | 318 | 832 | 551 | 925 | 61 | 0 | 443 | 355 | 21 | 43 |
| tổng | boots | F2 | 651 | 832 | 551 | 925 | 61 | 0 | 110 | 355 | 21 | 43 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video3 | helmet | base | 1202 | 1268 | 444 | 508 | 13 | 23 | 17 | 34 | 0 | 43 |
| video3 | helmet | F2 | 1212 | 1268 | 444 | 508 | 13 | 34 | 7 | 23 | 0 | 43 |
| video3 | vest | base | 1188 | 1288 | 447 | 488 | 48 | 3 | 14 | 33 | 0 | 43 |
| video3 | vest | F2 | 1202 | 1288 | 447 | 488 | 48 | 33 | 0 | 3 | 0 | 43 |
| video3 | gloves | base | 0 | 0 | 1087 | 1428 | 0 | 0 | 0 | 315 | 129 | 43 |
| video3 | gloves | F2 | 0 | 0 | 1087 | 1428 | 0 | 0 | 0 | 315 | 129 | 43 |
| video3 | goggles | base | 0 | 0 | 1639 | 1776 | 0 | 0 | 0 | 94 | 0 | 43 |
| video3 | goggles | F2 | 0 | 0 | 1639 | 1776 | 0 | 0 | 0 | 94 | 0 | 43 |
| video3 | boots | base | 4 | 134 | 401 | 487 | 61 | 0 | 59 | 67 | 21 | 43 |
| video3 | boots | F2 | 60 | 134 | 401 | 487 | 61 | 0 | 3 | 67 | 21 | 43 |
| video4 | helmet | base | 882 | 1047 | 0 | 0 | 0 | 0 | 165 | 0 | 0 | 0 |
| video4 | helmet | F2 | 928 | 1047 | 0 | 0 | 0 | 0 | 119 | 0 | 0 | 0 |
| video4 | vest | base | 664 | 698 | 349 | 349 | 0 | 0 | 34 | 0 | 0 | 0 |
| video4 | vest | F2 | 698 | 698 | 349 | 349 | 0 | 0 | 0 | 0 | 0 | 0 |
| video4 | gloves | base | 481 | 698 | 0 | 0 | 0 | 0 | 217 | 0 | 1 | 0 |
| video4 | gloves | F2 | 547 | 698 | 0 | 0 | 0 | 0 | 151 | 0 | 1 | 0 |
| video4 | goggles | base | 0 | 0 | 423 | 698 | 0 | 0 | 0 | 275 | 0 | 0 |
| video4 | goggles | F2 | 0 | 0 | 423 | 698 | 0 | 0 | 0 | 275 | 0 | 0 |
| video4 | boots | base | 314 | 698 | 0 | 0 | 0 | 0 | 384 | 0 | 0 | 0 |
| video4 | boots | F2 | 591 | 698 | 0 | 0 | 0 | 0 | 107 | 0 | 0 | 0 |
| video5 | helmet | base | 418 | 438 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| video5 | helmet | F2 | 418 | 438 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| video5 | vest | base | 372 | 438 | 0 | 0 | 0 | 0 | 66 | 0 | 0 | 0 |
| video5 | vest | F2 | 418 | 438 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 |
| video5 | gloves | base | 0 | 0 | 383 | 438 | 0 | 1 | 0 | 54 | 0 | 0 |
| video5 | gloves | F2 | 0 | 0 | 383 | 438 | 0 | 1 | 0 | 54 | 0 | 0 |
| video5 | goggles | base | 357 | 438 | 0 | 0 | 0 | 0 | 81 | 0 | 0 | 0 |
| video5 | goggles | F2 | 367 | 438 | 0 | 0 | 0 | 0 | 71 | 0 | 0 | 0 |
| video5 | boots | base | 0 | 0 | 150 | 438 | 0 | 0 | 0 | 288 | 0 | 0 |
| video5 | boots | F2 | 0 | 0 | 150 | 438 | 0 | 0 | 0 | 288 | 0 | 0 |
| video6 | helmet | base | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | helmet | F2 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | vest | base | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | vest | F2 | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | gloves | base | 205 | 206 | 206 | 206 | 0 | 0 | 1 | 0 | 0 | 0 |
| video6 | gloves | F2 | 206 | 206 | 206 | 206 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | goggles | base | 0 | 0 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | goggles | F2 | 0 | 0 | 412 | 412 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | boots | base | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video6 | boots | F2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- video3, base: 7 sự kiện: #1 người 1 2.936-65.065s gloves,goggles (session_ended_unverified); #2 người 2 17.518-65.065s boots,gloves,goggles,helmet,vest (session_ended_unverified); #3 người 3 19.052-65.065s boots,gloves,goggles (session_ended_unverified); #4 người 4 35.469-65.065s boots,gloves,goggles (session_ended_unverified); #5 người 5 37.471-65.065s boots,gloves,goggles,helmet (session_ended_unverified); #6 người 6 38.839-65.065s boots,gloves,goggles,vest (session_ended_unverified); #7 người 7 54.688-65.065s boots,gloves,goggles (session_ended_unverified)
- video3, F2: 7 sự kiện: #1 người 1 2.936-65.065s gloves,goggles (session_ended_unverified); #2 người 2 17.518-65.065s boots,gloves,goggles,helmet,vest (session_ended_unverified); #3 người 3 19.052-65.065s boots,gloves,goggles (session_ended_unverified); #4 người 4 35.469-65.065s boots,gloves,goggles (session_ended_unverified); #5 người 5 37.471-65.065s boots,gloves,goggles,helmet (session_ended_unverified); #6 người 6 38.839-65.065s boots,gloves,goggles,vest (session_ended_unverified); #7 người 7 54.688-65.065s boots,gloves,goggles (session_ended_unverified)
- video4, base: 3 sự kiện: #1 người 1 0.0-11.633s goggles (session_ended_unverified); #2 người 2 0.0-11.633s vest (session_ended_unverified); #3 người 3 6.133-11.633s goggles (session_ended_unverified)
- video4, F2: 3 sự kiện: #1 người 1 0.0-11.633s goggles (session_ended_unverified); #2 người 2 0.0-11.633s vest (session_ended_unverified); #3 người 3 6.133-11.633s goggles (session_ended_unverified)
- video5, base: 2 sự kiện: #1 người 1 0.0-7.3s boots,gloves (session_ended_unverified); #2 người 2 0.0-7.3s boots,gloves (session_ended_unverified)
- video5, F2: 2 sự kiện: #1 người 1 0.0-7.3s boots,gloves (session_ended_unverified); #2 người 2 0.0-7.3s boots,gloves (session_ended_unverified)
- video6, base: 2 sự kiện: #1 người 1 0.0-8.24s goggles,vest (session_ended_unverified); #2 người 2 0.0-8.24s gloves,goggles (session_ended_unverified)
- video6, F2: 2 sự kiện: #1 người 1 0.0-8.24s goggles,vest (session_ended_unverified); #2 người 2 0.0-8.24s gloves,goggles (session_ended_unverified)

## So sánh với cấu hình mốc

### base_vs_F2
- video3: sự kiện KHÁC: [{"index": 1, "field": "missing_history", "a": [[3.403, ["goggles"]], [8.342, ["gloves", "goggles"]], [11.311, ["gloves", "goggles"]], [65.065, ["gloves", "goggles"]]], "b": [[3.403, ["goggles"]], [8.308, ["gloves", "goggles"]], [11.311, ["gloves", "goggles"]], [65.065, ["gloves", "goggles"]]]}, {"index": 3, "field": "missing_history", "a": [[19.586, ["boots"]], [19.753, ["boots", "goggles"]], [20.32, ["boots", "gloves", "goggles"]], [25.192, ["boots", "gloves", "goggles"]], [65.065, ["boots", "gloves", "goggles"]]], "b": [[19.586, ["boots"]], [19.753, ["boots", "goggles"]], [20.32, ["boots", "gloves", "goggles"]], [25.259, ["boots", "gloves", "goggles"]], [65.065, ["boots", "gloves", "goggles"]]]}, {"index": 5, "field": "missing_history", "a": [[37.938, ["vest"]], [38.205, ["boots", "vest"]], [38.238, ["boots", "goggles", "vest"]], [39.84, ["boots", "goggles"]], [40.307, ["boots", "gloves", "goggles"]], [41.174, ["boots", "gloves", "goggles", "helmet"]], [46.28, ["boots", "gloves", "goggles", "helmet"]], [65.065, ["boots", "gloves", "goggles", "helmet"]]], "b": [[37.938, ["vest"]], [38.205, ["boots", "vest"]], [38.238, ["boots", "goggles", "vest"]], [39.84, ["boots", "goggles"]], [40.307, ["boots", "gloves", "goggles"]], [42.042, ["boots", "gloves", "goggles", "helmet"]], [46.28, ["boots", "gloves", "goggles", "helmet"]], [65.065, ["boots", "gloves", "goggles", "helmet"]]]}, {"index": 6, "field": "missing_history", "a": [[39.306, ["goggles"]], [40.641, ["boots", "goggles", "vest"]], [43.944, ["boots", "gloves", "goggles", "vest"]], [46.58, ["boots", "gloves", "goggles", "vest"]], [65.065, ["boots", "gloves", "goggles", "vest"]]], "b": [[39.306, ["goggles"]], [40.641, ["boots", "goggles"]], [41.942, ["boots", "goggles", "vest"]], [43.944, ["boots", "gloves", "goggles", "vest"]], [46.58, ["boots", "gloves", "goggles", "vest"]], [65.065, ["boots", "gloves", "goggles", "vest"]]]}] (7 / 7); dòng frames.csv 1746 / 1746, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 1746; Có mới trên người không có nhãn {'helmet': 4, 'vest': 3, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 10, 'thieu|chua_xac_dinh->co': 11}
  - vest (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 14, 'thieu|chua_xac_dinh->co': 30}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 1}
  - boots (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 56}
- video4: sự kiện giống nhau (3 / 3); dòng frames.csv 1047 / 1047, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 1047; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 46}
  - vest (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 34}
  - gloves (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 96, 'co|chua_xac_dinh->co': 66}
  - boots (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 277}
- video5: sự kiện giống nhau (2 / 2); dòng frames.csv 438 / 438, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 438; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - vest (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 46}
  - goggles (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 10}
- video6: sự kiện giống nhau (2 / 2); dòng frames.csv 412 / 412, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 412; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - gloves (nhãn|mốc->bản kia): {'co|chua_xac_dinh->co': 1}
