# Benchmark (2026-11-28T03:55:50)

Phạm vi: Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm giải mã khung; GPU từ nvidia-smi lấy mẫu.

Video video3, video4, video5, video6; 3 lượt lặp; bỏ 30 khung đầu mỗi video khỏi thống kê; nvidia-smi mỗi 500 ms. Môi trường: NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.11.0+cu128, ultralytics 8.4.189.

Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.

| Chỉ số | final3 | final5 | Chênh (sau − đầu) |
|---|---|---|---|
| Latency TB (ms) | 50.4 ± 0.1 | 36.5 ± 0.1 | -13.9 (-27.5%) |
| P95 latency, video cao nhất (ms) | 91.0 ± 3.0 | 83.2 ± 0.9 | -7.8 (-8.6%) |
| FPS xử lý | 19.86 ± 0.04 | 27.40 ± 0.08 | +7.54 (+38.0%) |
| FPS gồm giải mã | 18.38 ± 0.04 | 24.78 ± 0.08 | +6.40 (+34.8%) |
| GPU util TB (%) | 43.4 ± 0.2 | 43.9 ± 0.4 | +0.4 (+1.0%) |
| VRAM GPU tăng so với nền, đỉnh (MiB) | 297 ± 1 | 297 ± 0 | +0 (+0.1%) |
| PyTorch reserved đỉnh (MiB) | 200 ± 0 | 200 ± 0 | +0 (+0.0%) |
| PyTorch allocated đỉnh (MiB) | 176 ± 0 | 176 ± 0 | +0 (+0.0%) |

Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):

| Bước | final3 | final5 |
|---|---|---|
| association | 0.09 | 0.08 |
| compliance | 0.63 | 0.61 |
| detector | 29.73 | 23.23 |
| parts | 11.53 | 12.02 |
| pose | 7.69 | 7.86 |
| temporal_events | 0.27 | 0.27 |
| tracker | 0.38 | 0.39 |

Kiểm tra: video3: cùng số khung True ([1950]), số sự kiện {'final3': [7], 'final5': [7]}; video4: cùng số khung True ([349]), số sự kiện {'final3': [3], 'final5': [3]}; video5: cùng số khung True ([219]), số sự kiện {'final3': [2], 'final5': [2]}; video6: cùng số khung True ([206]), số sự kiện {'final3': [2], 'final5': [2]}
