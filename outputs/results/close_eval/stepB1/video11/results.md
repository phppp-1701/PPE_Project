# Kết quả theo khung (2026-11-26T01:47:29)

**Nhãn:** nhãn máy (kiem_thu_gan, kính cận)

Ghép người: IoU ≥ 0.5. CXĐ = Chưa xác định. "Không ghép" = hộp nhãn không ghép được người dự đoán (giữ lại, không bỏ). Số là số khung-người, không phải độ chính xác tuyệt đối.

Cấu hình: `base` = `outputs/results/close_eval/stepB1/pipeline_base.yaml`, `B1` = `outputs/results/close_eval/stepB1/pipeline_B1.yaml`

## Tổng

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tổng | helmet | base | 184 | 191 | 66 | 78 | 0 | 1 | 7 | 11 | 0 | 0 |
| tổng | helmet | B1 | 184 | 191 | 66 | 78 | 0 | 1 | 7 | 11 | 0 | 0 |
| tổng | vest | base | 0 | 0 | 271 | 271 | 0 | 0 | 0 | 0 | 0 | 0 |
| tổng | vest | B1 | 0 | 0 | 271 | 271 | 0 | 0 | 0 | 0 | 0 | 0 |
| tổng | gloves | base | 0 | 0 | 271 | 271 | 0 | 0 | 0 | 0 | 0 | 0 |
| tổng | gloves | B1 | 0 | 0 | 271 | 271 | 0 | 0 | 0 | 0 | 0 | 0 |
| tổng | goggles | base | 0 | 0 | 270 | 271 | 0 | 0 | 0 | 1 | 0 | 0 |
| tổng | goggles | B1 | 0 | 0 | 155 | 271 | 0 | 115 | 0 | 1 | 0 | 0 |
| tổng | boots | base | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tổng | boots | B1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Từng video

| Video | PPE | Cấu hình | Có đúng | /nhãn Có | Thiếu đúng | /nhãn Thiếu | Báo thiếu oan | Báo Có sai | Có→CXĐ | Thiếu→CXĐ | Thiếu trên nhãn CXĐ | Không ghép |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| video11 | helmet | base | 184 | 191 | 66 | 78 | 0 | 1 | 7 | 11 | 0 | 0 |
| video11 | helmet | B1 | 184 | 191 | 66 | 78 | 0 | 1 | 7 | 11 | 0 | 0 |
| video11 | vest | base | 0 | 0 | 271 | 271 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | vest | B1 | 0 | 0 | 271 | 271 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | gloves | base | 0 | 0 | 271 | 271 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | gloves | B1 | 0 | 0 | 271 | 271 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | goggles | base | 0 | 0 | 270 | 271 | 0 | 0 | 0 | 1 | 0 | 0 |
| video11 | goggles | B1 | 0 | 0 | 155 | 271 | 0 | 115 | 0 | 1 | 0 | 0 |
| video11 | boots | base | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| video11 | boots | B1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Sự kiện

- video11, base: 1 sự kiện: #1 người 1 0.0-10.84s gloves,goggles,vest (session_ended_unverified)
- video11, B1: 1 sự kiện: #1 người 1 0.0-10.84s gloves,vest (session_ended_unverified)

## So sánh với cấu hình mốc

### base_vs_B1
- video11: sự kiện KHÁC: [{"index": 1, "field": "missing_items", "a": ["gloves", "goggles", "vest"], "b": ["gloves", "vest"]}, {"index": 1, "field": "missing_history", "a": [[0.56, ["gloves", "goggles", "helmet", "vest"]], [4.24, ["gloves", "goggles", "vest"]], [10.84, ["gloves", "goggles", "vest"]]], "b": [[0.56, ["gloves", "goggles", "helmet", "vest"]], [4.24, ["gloves", "goggles", "vest"]], [7.6, ["gloves", "vest"]], [10.84, ["gloves", "vest"]]]}] (1 / 1); dòng frames.csv 271 / 271, chỉ ở mốc 0, chỉ ở bản kia 0, cùng hộp 271; Có mới trên người không có nhãn {'helmet': 0, 'vest': 0, 'gloves': 0, 'goggles': 0, 'boots': 0}
  - goggles (nhãn|mốc->bản kia): {'thieu|thieu->co': 115}
