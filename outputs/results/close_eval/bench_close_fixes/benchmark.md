# Benchmark (2026-11-25T19:39:38)

Phạm vi: Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm giải mã khung; GPU từ nvidia-smi lấy mẫu.

Video video3, video4, video5, video6; 3 lượt lặp; bỏ 30 khung đầu mỗi video khỏi thống kê; nvidia-smi mỗi 500 ms. Môi trường: NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.11.0+cu128, ultralytics 8.4.189.

Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.

| Chỉ số | before | current | Chênh (sau − đầu) |
|---|---|---|---|
| Latency TB (ms) | 55.4 ± 1.9 | 55.6 ± 1.3 | +0.2 (+0.4%) |
| P95 latency, video cao nhất (ms) | 100.9 ± 0.7 | 113.6 ± 15.6 | +12.8 (+12.7%) |
| FPS xử lý | 18.06 ± 0.61 | 17.99 ± 0.43 | -0.07 (-0.4%) |
| FPS gồm giải mã | 16.74 ± 0.55 | 16.61 ± 0.46 | -0.14 (-0.8%) |
| GPU util TB (%) | 43.1 ± 0.9 | 44.0 ± 1.7 | +0.9 (+2.1%) |
| VRAM GPU tăng so với nền, đỉnh (MiB) | 435 ± 58 | 393 ± 51 | -43 (-9.8%) |
| PyTorch reserved đỉnh (MiB) | 198 ± 0 | 198 ± 0 | +0 (+0.0%) |
| PyTorch allocated đỉnh (MiB) | 170 ± 0 | 170 ± 0 | +0 (+0.0%) |

Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):

| Bước | before | current |
|---|---|---|
| association | 0.06 | 0.08 |
| compliance | 0.68 | 0.69 |
| detector | 32.91 | 33.09 |
| parts | 12.14 | 12.14 |
| pose | 8.84 | 8.83 |
| temporal_events | 0.29 | 0.29 |
| tracker | 0.44 | 0.44 |

Kiểm tra: video3: cùng số khung True ([1950]), số sự kiện {'before': [7], 'current': [7]}; video4: cùng số khung True ([349]), số sự kiện {'before': [3], 'current': [3]}; video5: cùng số khung True ([219]), số sự kiện {'before': [2], 'current': [2]}; video6: cùng số khung True ([206]), số sự kiện {'before': [2], 'current': [2]}
