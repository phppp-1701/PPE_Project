# Benchmark (2026-11-28T03:22:09)

Phạm vi: Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm giải mã khung; GPU từ nvidia-smi lấy mẫu.

Video video4, video5, video6; 3 lượt lặp; bỏ 30 khung đầu mỗi video khỏi thống kê; nvidia-smi mỗi 500 ms. Môi trường: NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.11.0+cu128, ultralytics 8.4.189.

Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.

| Chỉ số | base | S3 | Chênh (sau − đầu) |
|---|---|---|---|
| Latency TB (ms) | 82.3 ± 0.1 | 55.5 ± 0.3 | -26.8 (-32.6%) |
| P95 latency, video cao nhất (ms) | 98.9 ± 0.6 | 93.8 ± 1.5 | -5.1 (-5.1%) |
| FPS xử lý | 12.15 ± 0.02 | 18.02 ± 0.10 | +5.87 (+48.4%) |
| FPS gồm giải mã | 11.46 ± 0.03 | 16.56 ± 0.11 | +5.09 (+44.5%) |
| GPU util TB (%) | 43.9 ± 0.1 | 44.7 ± 1.2 | +0.8 (+1.8%) |
| VRAM GPU tăng so với nền, đỉnh (MiB) | 309 ± 9 | 320 ± 20 | +11 (+3.4%) |
| PyTorch reserved đỉnh (MiB) | 200 ± 0 | 200 ± 0 | +0 (+0.0%) |
| PyTorch allocated đỉnh (MiB) | 176 ± 0 | 176 ± 0 | +0 (+0.0%) |

Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):

| Bước | base | S3 |
|---|---|---|
| association | 0.22 | 0.22 |
| compliance | 1.42 | 1.38 |
| detector | 45.73 | 32.15 |
| parts | 20.67 | 21.27 |
| pose | 13.23 | 13.55 |
| temporal_events | 0.43 | 0.43 |
| tracker | 0.58 | 0.58 |

Kiểm tra: video4: cùng số khung True ([349]), số sự kiện {'base': [3], 'S3': [3]}; video5: cùng số khung True ([219]), số sự kiện {'base': [2], 'S3': [2]}; video6: cùng số khung True ([206]), số sự kiện {'base': [2], 'S3': [2]}
