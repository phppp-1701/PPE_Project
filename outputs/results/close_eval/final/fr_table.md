# Bảng yêu cầu chức năng FR-01…10 (bản cuối, 16/11/2026)

Bản cuối: bản 4 + D + C2 + F1, commit nguồn `0a47b91` (`manifest.json`). Trạng thái theo `docs/spec.md` RQ4:
**Đạt**, **Đạt một phần**, **Không đạt**, **Chưa kiểm thử**, kèm bằng chứng đã chạy thật. Video dùng làm bằng chứng là
video phát triển (3-6, 9-17), không phải đánh giá khách quan; đánh giá cuối trên holdout chưa chạy (chờ người dùng).

| Mã | Yêu cầu (spec) | Trạng thái | Bằng chứng | Giới hạn |
|---|---|---|---|---|
| FR-01 | Đọc khung hình từ camera hoặc video, kèm nguồn và phiên | **Đạt một phần** | Video: `scripts/05_run_video.py` đọc file, gắn `source_id`, `session_id` vào mọi sự kiện (`annotated_main/*/events.jsonl`); 13 video chạy đủ khung (`benchmark/`: số khung khớp) | **Camera trực tiếp chưa có đường đọc**: `05_run_video` chỉ mở file; webcam `cam0` (13/11) được ghi thành file rồi xử lý như video |
| FR-02 | Phát hiện các lớp PPE: hộp, nhãn, độ tin cậy | **Đạt** | C4 6 lớp. Test nội bộ (1.583 ảnh): mAP50 person 0,921, helmet 0,860, vest 0,819, gloves 0,638, TB 4 lớp 0,809; `test_new` (117 ảnh): kính 0,736 [0,600; 0,860], ủng 0,477 [0,335; 0,648] (`docs/experiments/2026-11-12_c4_official_test_and_ablation.md`) | Spec ghi 4 lớp, đề tài đổi 6 lớp (09/11). Ủng dưới mốc 0,5 (khoảng tin cậy chứa 0,5). **Pictor-PPE** (`pictor/pictor_eval.md`, 774 ảnh, kiểm thử ngoài): person 0,851, helmet 0,685 (recall 0,47), vest 0,419 (42 hộp, KTC [0,198; 0,646]); mũ giảm rõ khi đổi miền ảnh |
| FR-03 | Liên kết PPE với từng người, xử lý nhiều người | **Đạt** | `tests/test_association_compliance.py` (tranh chấp không gán, PPE xa bị loại, găng từng tay, cúi người), `test_pose_regions.py`, `test_torso_strict.py`; V3b trên val (`pipeline_calib_val/assoc_pose.json`); F1 kính theo mắt | Áo người sát camera bị cắt ở ngực thường không gán (B1, B2, F2 không đạt); găng khi không thấy cổ tay thành Chưa xác định |
| FR-04 | Có / Thiếu / Chưa xác định cho từng PPE bắt buộc; găng từng tay | **Đạt** | `frames.csv` mỗi người mỗi khung 5 PPE; `tests/test_association_compliance.py` (Thiếu chỉ khi nhìn rõ, đầu ngoài khung -> Chưa xác định, găng từng tay), `test_compliance_cd.py` (C2, D); hiển thị nhất quán `06c`: 0 vi phạm (`annotated_main/display_audit.json`) | Độ đúng đo so với nhãn máy (chưa người kiểm định). **Holdout** (`holdout_summary.md`): mũ 0,542 (bản 4: 0,630; D làm mất 226 khung Thiếu đúng), áo 0,698, găng 0,497, kính 0,743 (bản 4: 0,528), ủng 0,248 |
| FR-05 | Gán, duy trì mã theo dõi qua khung | **Đạt (định tính)** | ByteTrack (`src/ppe/tracker.py`), `track_id` trong `frames.csv`, sự kiện theo track | **MOTA, IDF1, IDSW chưa đo** (không có nhãn theo dõi) |
| FR-06 | Tổng hợp theo thời gian; không cảnh báo từ một khung | **Đạt** | `tests/test_temporal_events.py`: `test_single_missing_frame_does_not_alert`, `test_min_valid_frac_blocks_sparse_missing`, `test_unknown_is_not_recovery` | |
| FR-07 | Một sự kiện mỗi đợt vi phạm; cập nhật `missing_items`, không trùng | **Đạt** | `test_continuous_missing_helmet_gives_one_event`, `test_second_missing_ppe_updates_same_event`, `test_recovered_closes_event`; API (`fr_api_check.json`): 36 thay đổi của 7 sự kiện -> 7 bản ghi | Event F1 chỉ đo ở ablation A-E (video 4-6); holdout không có nhãn sự kiện |
| FR-08 | Lưu sự kiện kèm thời gian, nguồn, mã theo dõi, ảnh hoặc clip minh chứng | **Đạt** | `events.jsonl`: thời gian, `source_id`, `session_id`, `track_id`, `evidence_refs`; ảnh `outputs/evidence/<phiên>/`; API: chi tiết 200 có lịch sử, ảnh minh chứng 200 (JPEG 279 KB) | Ảnh, không có clip |
| FR-09 | Dashboard: cảnh báo, lọc lịch sử, xem minh chứng, thống kê | **Đạt (API); giao diện chưa kiểm lại** | `dashboard/index.html` gọi `/api/stats`, `/api/events`, chi tiết, phản hồi, chính sách; API trả 200 (`fr_api_check.json`: danh sách 7, lọc theo nguồn, thống kê theo PPE, phản hồi); `/` chuyển tới dashboard | Cập nhật bằng hỏi định kỳ 3 s, **không có WebSocket** (stack trong CLAUDE.md ghi WebSocket). Giao diện chưa kiểm bằng trình duyệt trong đợt này |
| FR-10 | Cấu hình PPE bắt buộc cho từng nguồn | **Đạt một phần** | API chính sách theo nguồn có phiên bản (PUT -> version 2, GET đọc lại đúng); `Pipeline(required_ppe=...)` | **Chuỗi xử lý chưa đọc chính sách từ backend**: `05_run_video` dùng `required_ppe` trong `configs/pipeline.yaml` |

## Yêu cầu phi chức năng liên quan

| Mã | Trạng thái | Bằng chứng |
|---|---|---|
| NFR-01 (đo FPS, thời gian bước, độ trễ cảnh báo) | **Đã đo (lần sạch)** | **Số dùng cho báo cáo: `benchmark_clean/benchmark.md`** (đo sau khi người dùng tắt game; GPU nghỉ P8 trước khi đo). Bản cuối: **26,55 ± 1,80 FPS xử lý, 23,62 ± 1,53 FPS gồm giải mã**, latency TB 37,8 ms; bản 4: 25,75 / 22,92 FPS, 38,9 ms. Hai bản ngang nhau (chênh trong độ lệch chuẩn, không phải cải thiện). Theo video (bản cuối, FPS xử lý): video3 29,8; video4 19,6; video5 21,1; video6 21,0, tức cảnh đông người chậm hơn, **không đạt 25 FPS ổn định trên mọi video**. Độ trễ cảnh báo chưa đo riêng (theo thiết kế ≥ thời gian xác nhận vi phạm). Lần đo bẩn `benchmark/` (15,62 FPS, máy chạy Minecraft) giữ lại để đối chiếu, không dùng |
| NFR-02 (đổi PPE bắt buộc, tham số không sửa module) | Đạt | Tham số trong `configs/pipeline.yaml`; khóa C2, D, F1 bật / tắt không sửa code (test "vắng khóa như bản chính") |
| NFR-05 (tách module, kiểm thử riêng) | Đạt | `src/ppe/` (detector, tracker, pose, parts, association, compliance, temporal, events), `backend/`, `dashboard/`; 196 test |

## Việc còn thiếu để hoàn thiện RQ1-RQ4

1. ~~Đánh giá cuối trên holdout~~: đã chạy một lần 16/11 (`holdout_summary.md`).
2. ~~Đo lại hiệu năng~~: đã đo lại 16/11 (`benchmark_clean/`).
3. ~~Pictor-PPE~~: đã làm 16/11 (`pictor/pictor_eval.md`).
4. Kiểm giao diện dashboard bằng trình duyệt; camera trực tiếp (FR-01) nếu cần.
