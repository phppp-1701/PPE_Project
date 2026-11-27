# Benchmark (2026-11-28T02:32:13)

Phạm vi: Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm giải mã khung; GPU từ nvidia-smi lấy mẫu.

Video video4, video5, video6; 3 lượt lặp; bỏ 30 khung đầu mỗi video khỏi thống kê; nvidia-smi mỗi 500 ms. Môi trường: NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.11.0+cu128, ultralytics 8.4.189.

Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.

| Chỉ số | base | Sa | Sb | Sc | Chênh (sau − đầu) |
|---|---|---|---|---|---|
| Latency TB (ms) | 82.5 ± 0.4 | 72.0 ± 0.2 | 68.4 ± 0.6 | 58.4 ± 0.4 | -24.2 (-29.3%) |
| P95 latency, video cao nhất (ms) | 100.4 ± 1.6 | 96.2 ± 0.3 | 97.1 ± 1.3 | 98.1 ± 0.9 | -2.4 (-2.3%) |
| FPS xử lý | 12.12 ± 0.05 | 13.89 ± 0.04 | 14.61 ± 0.13 | 17.14 ± 0.11 | +5.02 (+41.4%) |
| FPS gồm giải mã | 11.44 ± 0.05 | 13.04 ± 0.07 | 13.66 ± 0.12 | 15.86 ± 0.13 | +4.41 (+38.6%) |
| GPU util TB (%) | 41.4 ± 0.4 | 44.4 ± 0.6 | 39.9 ± 0.3 | 42.1 ± 1.5 | +0.6 (+1.5%) |
| VRAM GPU tăng so với nền, đỉnh (MiB) | 301 ± 4 | 304 ± 3 | 297 ± 0 | 303 ± 2 | +2 (+0.6%) |
| PyTorch reserved đỉnh (MiB) | 200 ± 0 | 200 ± 0 | 200 ± 0 | 200 ± 0 | +0 (+0.0%) |
| PyTorch allocated đỉnh (MiB) | 176 ± 0 | 176 ± 0 | 176 ± 0 | 176 ± 0 | +0 (+0.0%) |

Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):

| Bước | base | Sa | Sb | Sc |
|---|---|---|---|---|
| association | 0.22 | 0.22 | 0.22 | 0.21 |
| compliance | 1.40 | 1.36 | 1.39 | 1.36 |
| detector | 45.62 | 45.47 | 31.51 | 31.68 |
| parts | 20.94 | 21.06 | 20.91 | 21.21 |
| pose | 13.27 | 13.31 | 13.35 | 13.40 |
| temporal_events | 0.43 | 0.43 | 0.42 | 0.44 |
| tracker | 0.58 | 0.57 | 0.57 | 0.57 |

Kiểm tra: video4: cùng số khung True ([349]), số sự kiện {'base': [3], 'Sa': [3], 'Sb': [3], 'Sc': [3]}; video5: cùng số khung True ([219]), số sự kiện {'base': [2], 'Sa': [2], 'Sb': [2], 'Sc': [2]}; video6: cùng số khung True ([206]), số sự kiện {'base': [2], 'Sa': [2], 'Sb': [2], 'Sc': [2]}
