# Benchmark (2026-11-28T01:41:06)

Phạm vi: Pipeline stage full (detector, tracker, pose, parts, association, compliance, temporal, events, ảnh minh chứng); không vẽ, không ghi video, không frames.csv, không backend; latency không gồm giải mã khung; GPU từ nvidia-smi lấy mẫu.

Video video3, video4, video5, video6; 3 lượt lặp; bỏ 30 khung đầu mỗi video khỏi thống kê; nvidia-smi mỗi 500 ms. Môi trường: NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.11.0+cu128, ultralytics 8.4.189.

Giá trị: trung bình ± độ lệch chuẩn giữa các lượt lặp.

| Chỉ số | final2 | final4 | Chênh (sau − đầu) |
|---|---|---|---|
| Latency TB (ms) | 55.1 ± 1.0 | 56.7 ± 1.1 | +1.5 (+2.8%) |
| P95 latency, video cao nhất (ms) | 102.8 ± 7.2 | 107.3 ± 8.8 | +4.6 (+4.5%) |
| FPS xử lý | 18.14 ± 0.33 | 17.64 ± 0.35 | -0.49 (-2.7%) |
| FPS gồm giải mã | 16.78 ± 0.26 | 16.38 ± 0.31 | -0.40 (-2.4%) |
| GPU util TB (%) | 45.2 ± 1.8 | 44.3 ± 1.3 | -0.8 (-1.8%) |
| VRAM GPU tăng so với nền, đỉnh (MiB) | 571 ± 147 | 399 ± 108 | -172 (-30.2%) |
| PyTorch reserved đỉnh (MiB) | 198 ± 0 | 200 ± 0 | +2 (+1.0%) |
| PyTorch allocated đỉnh (MiB) | 170 ± 0 | 176 ± 0 | +6 (+3.8%) |

Thời gian trung bình từng bước (ms, gộp mọi lượt và video, có trọng số số khung):

| Bước | final2 | final4 |
|---|---|---|
| association | 0.08 | 0.10 |
| compliance | 0.68 | 0.68 |
| detector | 33.03 | 33.15 |
| parts | 11.93 | 13.34 |
| pose | 8.67 | 8.67 |
| temporal_events | 0.29 | 0.29 |
| tracker | 0.42 | 0.42 |

Kiểm tra: video3: cùng số khung True ([1950]), số sự kiện {'final2': [7], 'final4': [7]}; video4: cùng số khung True ([349]), số sự kiện {'final2': [3], 'final4': [3]}; video5: cùng số khung True ([219]), số sự kiện {'final2': [2], 'final4': [2]}; video6: cùng số khung True ([206]), số sự kiện {'final2': [2], 'final4': [2]}
