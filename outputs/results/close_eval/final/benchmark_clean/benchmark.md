# Benchmark (2026-11-15T18:21:01)

Phạm vi: Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm giải mã khung; GPU từ nvidia-smi lấy mẫu.

Video video3, video4, video5, video6; 3 lượt lặp; bỏ 30 khung đầu mỗi video khỏi thống kê; nvidia-smi mỗi 500 ms. Môi trường: NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.11.0+cu128, ultralytics 8.4.189.

Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.

| Chỉ số | v4 | final | Chênh (sau − đầu) |
|---|---|---|---|
| Latency TB (ms) | 38.9 ± 1.8 | 37.8 ± 2.7 | -1.1 (-2.9%) |
| P95 latency, video cao nhất (ms) | 70.9 ± 9.2 | 57.1 ± 4.7 | -13.7 (-19.4%) |
| FPS xử lý | 25.75 ± 1.18 | 26.55 ± 1.80 | +0.80 (+3.1%) |
| FPS gồm giải mã | 22.92 ± 1.01 | 23.62 ± 1.53 | +0.71 (+3.1%) |
| GPU util TB (%) | 36.7 ± 1.5 | 36.8 ± 1.4 | +0.1 (+0.2%) |
| VRAM GPU tăng so với nền, đỉnh (MiB) | 361 ± 94 | 309 ± 64 | -52 (-14.5%) |
| PyTorch reserved đỉnh (MiB) | 184 ± 0 | 184 ± 0 | +0 (+0.0%) |
| PyTorch allocated đỉnh (MiB) | 151 ± 0 | 151 ± 0 | +0 (+0.0%) |

Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):

| Bước | v4 | final |
|---|---|---|
| association | 0.06 | 0.06 |
| compliance | 0.64 | 0.62 |
| detector | 17.35 | 17.02 |
| parts | 11.31 | 10.88 |
| pose | 8.80 | 8.50 |
| temporal_events | 0.28 | 0.27 |
| tracker | 0.40 | 0.39 |

Kiểm tra: video3: cùng số khung True ([1950]), số sự kiện {'v4': [7], 'final': [7]}; video4: cùng số khung True ([349]), số sự kiện {'v4': [3], 'final': [3]}; video5: cùng số khung True ([219]), số sự kiện {'v4': [2], 'final': [2]}; video6: cùng số khung True ([206]), số sự kiện {'v4': [2], 'final': [2]}
