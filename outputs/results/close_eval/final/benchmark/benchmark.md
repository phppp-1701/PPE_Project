# Benchmark (2026-11-15T16:48:06)

Phạm vi: Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm giải mã khung; GPU từ nvidia-smi lấy mẫu.

Video video3, video4, video5, video6; 3 lượt lặp; bỏ 30 khung đầu mỗi video khỏi thống kê; nvidia-smi mỗi 500 ms. Môi trường: NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.11.0+cu128, ultralytics 8.4.189.

Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.

| Chỉ số | v4 | final | Chênh (sau − đầu) |
|---|---|---|---|
| Latency TB (ms) | 64.5 ± 1.4 | 64.0 ± 0.7 | -0.4 (-0.7%) |
| P95 latency, video cao nhất (ms) | 94.4 ± 2.0 | 92.2 ± 2.9 | -2.1 (-2.2%) |
| FPS xử lý | 15.52 ± 0.34 | 15.62 ± 0.18 | +0.10 (+0.7%) |
| FPS gồm giải mã | 14.26 ± 0.30 | 14.34 ± 0.22 | +0.09 (+0.6%) |
| GPU util TB (%) | 71.3 ± 1.1 | 71.5 ± 0.1 | +0.2 (+0.3%) |
| VRAM GPU tăng so với nền, đỉnh (MiB) | 274 ± 1 | 272 ± 1 | -1 (-0.5%) |
| PyTorch reserved đỉnh (MiB) | 184 ± 0 | 184 ± 0 | +0 (+0.0%) |
| PyTorch allocated đỉnh (MiB) | 151 ± 0 | 151 ± 0 | +0 (+0.0%) |

Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):

| Bước | v4 | final |
|---|---|---|
| association | 0.07 | 0.07 |
| compliance | 0.74 | 0.73 |
| detector | 34.77 | 34.85 |
| parts | 15.56 | 15.26 |
| pose | 12.46 | 12.26 |
| temporal_events | 0.32 | 0.31 |
| tracker | 0.49 | 0.48 |

Kiểm tra: video3: cùng số khung True ([1950]), số sự kiện {'v4': [7], 'final': [7]}; video4: cùng số khung True ([349]), số sự kiện {'v4': [3], 'final': [3]}; video5: cùng số khung True ([219]), số sự kiện {'v4': [2], 'final': [2]}; video6: cùng số khung True ([206]), số sự kiện {'v4': [2], 'final': [2]}
