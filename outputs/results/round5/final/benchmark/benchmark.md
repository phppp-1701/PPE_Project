# Benchmark (2026-11-28T13:15:13)

Phạm vi: Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm giải mã khung; GPU từ nvidia-smi lấy mẫu.

Video video3, video4, video5, video6; 3 lượt lặp; bỏ 30 khung đầu mỗi video khỏi thống kê; nvidia-smi mỗi 500 ms. Môi trường: NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.11.0+cu128, ultralytics 8.4.189.

Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.

| Chỉ số | cuoi4 | r5 | Chênh (sau − đầu) |
|---|---|---|---|
| Latency TB (ms) | 39.9 ± 0.4 | 40.4 ± 1.3 | +0.5 (+1.2%) |
| P95 latency, video cao nhất (ms) | 92.8 ± 0.6 | 94.5 ± 5.1 | +1.6 (+1.7%) |
| FPS xử lý | 25.05 ± 0.27 | 24.78 ± 0.79 | -0.27 (-1.1%) |
| FPS gồm giải mã | 22.71 ± 0.26 | 22.47 ± 0.68 | -0.24 (-1.0%) |
| GPU util TB (%) | 45.6 ± 1.5 | 45.3 ± 0.6 | -0.4 (-0.8%) |
| VRAM GPU tăng so với nền, đỉnh (MiB) | 360 ± 72 | 425 ± 181 | +65 (+18.1%) |
| PyTorch reserved đỉnh (MiB) | 200 ± 0 | 200 ± 0 | +0 (+0.0%) |
| PyTorch allocated đỉnh (MiB) | 176 ± 0 | 176 ± 0 | +0 (+0.0%) |

Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):

| Bước | cuoi4 | r5 |
|---|---|---|
| association | 0.09 | 0.10 |
| compliance | 0.67 | 0.68 |
| detector | 25.19 | 25.48 |
| parts | 13.45 | 13.66 |
| pose | 8.72 | 8.78 |
| temporal_events | 0.29 | 0.29 |
| tracker | 0.42 | 0.42 |

Kiểm tra: video3: cùng số khung True ([1950]), số sự kiện {'cuoi4': [7], 'r5': [7]}; video4: cùng số khung True ([349]), số sự kiện {'cuoi4': [3], 'r5': [3]}; video5: cùng số khung True ([219]), số sự kiện {'cuoi4': [2], 'r5': [2]}; video6: cùng số khung True ([206]), số sự kiện {'cuoi4': [2], 'r5': [2]}
