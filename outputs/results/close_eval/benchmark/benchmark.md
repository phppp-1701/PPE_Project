# Benchmark (2026-11-14T18:25:13)

Phạm vi: Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm giải mã khung; GPU từ nvidia-smi lấy mẫu.

Video video3, video4, video5, video6; 3 lượt lặp; bỏ 30 khung đầu mỗi video khỏi thống kê; nvidia-smi mỗi 500 ms. Môi trường: NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.11.0+cu128, ultralytics 8.4.189.

Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.

| Chỉ số | baseline | v4 | Chênh (sau − đầu) |
|---|---|---|---|
| Latency TB (ms) | 38.3 ± 0.8 | 43.4 ± 1.5 | +5.1 (+13.3%) |
| P95 latency, video cao nhất (ms) | 60.7 ± 4.5 | 71.2 ± 8.0 | +10.5 (+17.3%) |
| FPS xử lý | 26.13 ± 0.55 | 23.07 ± 0.84 | -3.05 (-11.7%) |
| FPS gồm giải mã | 22.97 ± 0.39 | 20.51 ± 0.67 | -2.45 (-10.7%) |
| GPU util TB (%) | 41.3 ± 5.4 | 42.7 ± 6.0 | +1.4 (+3.5%) |
| VRAM GPU tăng so với nền, đỉnh (MiB) | 281 ± 10 | 362 ± 143 | +81 (+29.0%) |
| PyTorch reserved đỉnh (MiB) | 180 ± 0 | 184 ± 0 | +4 (+2.2%) |
| PyTorch allocated đỉnh (MiB) | 146 ± 0 | 151 ± 0 | +6 (+4.0%) |

Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):

| Bước | baseline | v4 |
|---|---|---|
| association | 0.06 | 0.06 |
| compliance | 0.65 | 0.67 |
| detector | 18.50 | 19.23 |
| parts | 8.70 | 12.87 |
| pose | 9.59 | 9.79 |
| temporal_events | 0.30 | 0.29 |
| tracker | 0.43 | 0.43 |

Kiểm tra: video3: cùng số khung True ([1950]), số sự kiện {'baseline': [7], 'v4': [7]}; video4: cùng số khung True ([349]), số sự kiện {'baseline': [3], 'v4': [3]}; video5: cùng số khung True ([219]), số sự kiện {'baseline': [2], 'v4': [2]}; video6: cùng số khung True ([206]), số sự kiện {'baseline': [2], 'v4': [2]}
