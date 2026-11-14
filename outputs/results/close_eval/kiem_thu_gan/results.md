# Kết quả theo khung (2026-11-14T18:42:00)

**Nhãn:** Nhãn tham chiếu: nhãn máy (Claude) qua hai lượt, machine_consensus, CHƯA có người kiểm định; không phải ground truth đã xác minh. Người gán đã xem kết quả hệ thống trên các video này trước khi gán, nên có nguy cơ thiên lệch về phía hệ thống. Chỗ hai lượt khác nhau là chua_xac_dinh. Tập kiem_thu_gan: chỉ báo, không chỉnh theo.

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Manifest: `outputs/results/close_eval/manifest.json`, commit nguồn `0b756b849e`, HEAD `05adc554cc`.

Cấu hình: `baseline` = `outputs/results/close_eval/pipeline_baseline_0645f53.yaml`, `v4` = `configs/pipeline.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | baseline | 1858 | 2117 | 624 | 704 | 53 | 49 | 193 | 31 | 0 | 24 |
| tổng | helmet | v4 | 1858 | 2117 | 624 | 704 | 53 | 49 | 193 | 31 | 0 | 24 |
| tổng | vest | baseline | 1317 | 1939 | 1064 | 1064 | 422 | 0 | 176 | 0 | 0 | 24 |
| tổng | vest | v4 | 1317 | 1939 | 1064 | 1064 | 422 | 0 | 176 | 0 | 0 | 24 |
| tổng | gloves | baseline | 224 | 377 | 526 | 1070 | 0 | 0 | 143 | 544 | 31 | 24 |
| tổng | gloves | v4 | 224 | 377 | 526 | 1070 | 0 | 0 | 143 | 544 | 31 | 24 |
| tổng | goggles | baseline | 795 | 957 | 770 | 771 | 114 | 0 | 48 | 1 | 74 | 24 |
| tổng | goggles | v4 | 795 | 957 | 770 | 771 | 114 | 0 | 48 | 1 | 74 | 24 |
| tổng | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 24 |
| tổng | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 24 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video9 | helmet | baseline | 315 | 315 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video9 | helmet | v4 | 315 | 315 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video9 | vest | baseline | 52 | 315 | 0 | 0 | 232 | 0 | 31 | 0 | 0 | 0 |
| video9 | vest | v4 | 52 | 315 | 0 | 0 | 232 | 0 | 31 | 0 | 0 | 0 |
| video9 | gloves | baseline | 0 | 0 | 81 | 160 | 0 | 0 | 0 | 79 | 0 | 0 |
| video9 | gloves | v4 | 0 | 0 | 81 | 160 | 0 | 0 | 0 | 79 | 0 | 0 |
| video9 | goggles | baseline | 207 | 225 | 85 | 85 | 11 | 0 | 7 | 0 | 5 | 0 |
| video9 | goggles | v4 | 207 | 225 | 85 | 85 | 11 | 0 | 7 | 0 | 5 | 0 |
| video9 | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video9 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video10 | helmet | baseline | 361 | 361 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video10 | helmet | v4 | 361 | 361 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video10 | vest | baseline | 179 | 361 | 0 | 0 | 182 | 0 | 0 | 0 | 0 | 0 |
| video10 | vest | v4 | 179 | 361 | 0 | 0 | 182 | 0 | 0 | 0 | 0 | 0 |
| video10 | gloves | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video10 | gloves | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video10 | goggles | baseline | 361 | 361 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video10 | goggles | v4 | 361 | 361 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video10 | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video10 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | helmet | baseline | 191 | 191 | 66 | 78 | 0 | 11 | 0 | 1 | 0 | 0 |
| video11 | helmet | v4 | 191 | 191 | 66 | 78 | 0 | 11 | 0 | 1 | 0 | 0 |
| video11 | vest | baseline | 0 | 0 | 271 | 271 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | vest | v4 | 0 | 0 | 271 | 271 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | gloves | baseline | 0 | 0 | 264 | 271 | 0 | 0 | 0 | 7 | 0 | 0 |
| video11 | gloves | v4 | 0 | 0 | 264 | 271 | 0 | 0 | 0 | 7 | 0 | 0 |
| video11 | goggles | baseline | 0 | 0 | 270 | 271 | 0 | 0 | 0 | 1 | 0 | 0 |
| video11 | goggles | v4 | 0 | 0 | 270 | 271 | 0 | 0 | 0 | 1 | 0 | 0 |
| video11 | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | helmet | baseline | 167 | 167 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | helmet | v4 | 167 | 167 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | vest | baseline | 0 | 0 | 167 | 167 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | vest | v4 | 0 | 0 | 167 | 167 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | gloves | baseline | 167 | 167 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | gloves | v4 | 167 | 167 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | goggles | baseline | 0 | 0 | 167 | 167 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | goggles | v4 | 0 | 0 | 167 | 167 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video12 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video13 | helmet | baseline | 0 | 0 | 179 | 247 | 0 | 38 | 0 | 30 | 0 | 0 |
| video13 | helmet | v4 | 0 | 0 | 179 | 247 | 0 | 38 | 0 | 30 | 0 | 0 |
| video13 | vest | baseline | 0 | 0 | 247 | 247 | 0 | 0 | 0 | 0 | 0 | 0 |
| video13 | vest | v4 | 0 | 0 | 247 | 247 | 0 | 0 | 0 | 0 | 0 | 0 |
| video13 | gloves | baseline | 0 | 88 | 0 | 0 | 0 | 0 | 88 | 0 | 0 | 0 |
| video13 | gloves | v4 | 0 | 88 | 0 | 0 | 0 | 0 | 88 | 0 | 0 | 0 |
| video13 | goggles | baseline | 3 | 132 | 110 | 110 | 94 | 0 | 35 | 0 | 5 | 0 |
| video13 | goggles | v4 | 3 | 132 | 110 | 110 | 94 | 0 | 35 | 0 | 5 | 0 |
| video13 | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video13 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video14 | helmet | baseline | 0 | 0 | 379 | 379 | 0 | 0 | 0 | 0 | 0 | 0 |
| video14 | helmet | v4 | 0 | 0 | 379 | 379 | 0 | 0 | 0 | 0 | 0 | 0 |
| video14 | vest | baseline | 0 | 0 | 379 | 379 | 0 | 0 | 0 | 0 | 0 | 0 |
| video14 | vest | v4 | 0 | 0 | 379 | 379 | 0 | 0 | 0 | 0 | 0 | 0 |
| video14 | gloves | baseline | 0 | 0 | 69 | 113 | 0 | 0 | 0 | 44 | 0 | 0 |
| video14 | gloves | v4 | 0 | 0 | 69 | 113 | 0 | 0 | 0 | 44 | 0 | 0 |
| video14 | goggles | baseline | 224 | 239 | 138 | 138 | 9 | 0 | 6 | 0 | 2 | 0 |
| video14 | goggles | v4 | 224 | 239 | 138 | 138 | 9 | 0 | 6 | 0 | 2 | 0 |
| video14 | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video14 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video15 | helmet | baseline | 142 | 162 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 24 |
| video15 | helmet | v4 | 142 | 162 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 24 |
| video15 | vest | baseline | 154 | 284 | 0 | 0 | 8 | 0 | 98 | 0 | 0 | 24 |
| video15 | vest | v4 | 154 | 284 | 0 | 0 | 8 | 0 | 98 | 0 | 0 | 24 |
| video15 | gloves | baseline | 57 | 122 | 0 | 0 | 0 | 0 | 55 | 0 | 30 | 24 |
| video15 | gloves | v4 | 57 | 122 | 0 | 0 | 0 | 0 | 55 | 0 | 30 | 24 |
| video15 | goggles | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 46 | 24 |
| video15 | goggles | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 46 | 24 |
| video15 | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 24 |
| video15 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 24 |
| video16 | helmet | baseline | 422 | 441 | 0 | 0 | 0 | 0 | 19 | 0 | 0 | 0 |
| video16 | helmet | v4 | 422 | 441 | 0 | 0 | 0 | 0 | 19 | 0 | 0 | 0 |
| video16 | vest | baseline | 452 | 499 | 0 | 0 | 0 | 0 | 47 | 0 | 0 | 0 |
| video16 | vest | v4 | 452 | 499 | 0 | 0 | 0 | 0 | 47 | 0 | 0 | 0 |
| video16 | gloves | baseline | 0 | 0 | 5 | 46 | 0 | 0 | 0 | 41 | 1 | 0 |
| video16 | gloves | v4 | 0 | 0 | 5 | 46 | 0 | 0 | 0 | 41 | 1 | 0 |
| video16 | goggles | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| video16 | goggles | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| video16 | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video16 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video17 | helmet | baseline | 260 | 480 | 0 | 0 | 53 | 0 | 167 | 0 | 0 | 0 |
| video17 | helmet | v4 | 260 | 480 | 0 | 0 | 53 | 0 | 167 | 0 | 0 | 0 |
| video17 | vest | baseline | 480 | 480 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video17 | vest | v4 | 480 | 480 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video17 | gloves | baseline | 0 | 0 | 107 | 480 | 0 | 0 | 0 | 373 | 0 | 0 |
| video17 | gloves | v4 | 0 | 0 | 107 | 480 | 0 | 0 | 0 | 373 | 0 | 0 |
| video17 | goggles | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video17 | goggles | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video17 | boots | baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video17 | boots | v4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- video9, baseline: 1 sự kiện: #1 người 1 0.0-10.5s gloves,vest (session_ended_unverified)
- video9, v4: 1 sự kiện: #1 người 1 0.0-10.5s gloves,vest (session_ended_unverified)
- video10, baseline: 1 sự kiện: #1 người 1 0.0-12.033s  (session_ended_unverified)
- video10, v4: 1 sự kiện: #1 người 1 0.0-12.033s  (session_ended_unverified)
- video11, baseline: 1 sự kiện: #1 người 1 0.0-10.84s gloves,goggles,vest (session_ended_unverified)
- video11, v4: 1 sự kiện: #1 người 1 0.0-10.84s gloves,goggles,vest (session_ended_unverified)
- video12, baseline: 1 sự kiện: #1 người 1 0.0-6.68s goggles,vest (session_ended_unverified)
- video12, v4: 1 sự kiện: #1 người 1 0.0-6.68s goggles,vest (session_ended_unverified)
- video13, baseline: 1 sự kiện: #1 người 1 0.0-8.233s goggles,helmet,vest (session_ended_unverified)
- video13, v4: 1 sự kiện: #1 người 1 0.0-8.233s goggles,helmet,vest (session_ended_unverified)
- video14, baseline: 1 sự kiện: #1 người 1 0.0-15.16s gloves,helmet,vest (session_ended_unverified)
- video14, v4: 1 sự kiện: #1 người 1 0.0-15.16s gloves,helmet,vest (session_ended_unverified)
- video15, baseline: 1 sự kiện: #1 người 3 0.0-4.88s gloves (session_ended_unverified)
- video15, v4: 1 sự kiện: #1 người 3 0.0-4.88s gloves (session_ended_unverified)
- video16, baseline: 0 sự kiện: 
- video16, v4: 0 sự kiện: 
- video17, baseline: 1 sự kiện: #1 người 1 1.201-16.016s gloves (session_ended_unverified)
- video17, v4: 1 sự kiện: #1 người 1 1.201-16.016s gloves (session_ended_unverified)

## So sánh với cấu hình mốc

### baseline_vs_v4
- video9: sự kiện giống nhau (1 / 1); dòng frames.csv 315 / 315, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 315; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video10: sự kiện giống nhau (1 / 1); dòng frames.csv 361 / 361, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 361; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video11: sự kiện giống nhau (1 / 1); dòng frames.csv 271 / 271, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 271; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video12: sự kiện giống nhau (1 / 1); dòng frames.csv 167 / 167, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 167; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video13: sự kiện giống nhau (1 / 1); dòng frames.csv 247 / 247, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 247; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video14: sự kiện giống nhau (1 / 1); dòng frames.csv 379 / 379, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 379; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video15: sự kiện giống nhau (1 / 1); dòng frames.csv 299 / 299, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 299; Có mới trên người không có nhãn {'helmet': 1, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
- video16: sự kiện giống nhau (0 / 0); dòng frames.csv 499 / 499, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 499; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - helmet (nhãn|mốc->bản kia): {'chua_xac_dinh|chua_xac_dinh->co': 2}
- video17: sự kiện giống nhau (1 / 1); dòng frames.csv 480 / 480, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 480; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
