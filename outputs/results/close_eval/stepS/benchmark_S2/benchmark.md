# Benchmark (2026-11-28T02:55:00)

Phạm vi: Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm giải mã khung; GPU từ nvidia-smi lấy mẫu.

Video video4, video5, video6; 3 lượt lặp; bỏ 30 khung đầu mỗi video khỏi thống kê; nvidia-smi mỗi 500 ms. Môi trường: NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.11.0+cu128, ultralytics 8.4.189.

Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.

| Chỉ số | base | S2 | Chênh (sau − đầu) |
|---|---|---|---|
| Latency TB (ms) | 82.5 ± 2.2 | 58.6 ± 1.7 | -23.9 (-29.0%) |
| P95 latency, video cao nhất (ms) | 100.9 ± 2.9 | 97.5 ± 4.0 | -3.4 (-3.4%) |
| FPS xử lý | 12.13 ± 0.32 | 17.08 ± 0.48 | +4.96 (+40.9%) |
| FPS gồm giải mã | 11.45 ± 0.29 | 15.77 ± 0.45 | +4.32 (+37.7%) |
| GPU util TB (%) | 42.7 ± 0.8 | 42.7 ± 1.8 | -0.0 (-0.0%) |
| VRAM GPU tăng so với nền, đỉnh (MiB) | 302 ± 4 | 324 ± 46 | +22 (+7.4%) |
| PyTorch reserved đỉnh (MiB) | 200 ± 0 | 200 ± 0 | +0 (+0.0%) |
| PyTorch allocated đỉnh (MiB) | 176 ± 0 | 176 ± 0 | +0 (+0.0%) |

Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):

| Bước | base | S2 |
|---|---|---|
| association | 0.22 | 0.22 |
| compliance | 1.43 | 1.41 |
| detector | 45.67 | 31.89 |
| parts | 20.81 | 20.99 |
| pose | 13.31 | 13.44 |
| temporal_events | 0.43 | 0.44 |
| tracker | 0.59 | 0.59 |

Kiểm tra: video4: cùng số khung True ([349]), số sự kiện {'base': [3], 'S2': [3]}; video5: cùng số khung True ([219]), số sự kiện {'base': [2], 'S2': [2]}; video6: cùng số khung True ([206]), số sự kiện {'base': [2], 'S2': [2]}
