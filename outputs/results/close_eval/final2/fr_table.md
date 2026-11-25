# Bảng yêu cầu chức năng FR-01…10 (bản cuối 2, 26/11/2026)

Bản cuối 2: detector c6_ft + zoom, bản cuối 16/11 + M1 + đợt sửa tầm gần (F1 ủng, F2 nhớ PPE, A1 găng, A2 hiển thị, A3 WebSocket; kính bản 3), commit đóng băng `28ad782`. Bản 16/11: `final/fr_table.md`. Trạng thái theo `docs/spec.md` RQ4:
**Đạt**, **Đạt một phần**, **Không đạt**, **Chưa kiểm thử**, kèm bằng chứng đã chạy thật. Video dùng làm bằng chứng là
video phát triển (3-6, 9-17), không phải đánh giá khách quan; holdout đã chạy chính thức một lần 16/11 (bản cuối cũ); lần chạy 26/11 là kiểm tra sau khi sửa, không còn mù.

| Mã | Yêu cầu (spec) | Trạng thái | Bằng chứng | Giới hạn |
|---|---|---|---|---|
| FR-01 | Đọc khung hình từ camera hoặc video, kèm nguồn và phiên | **Đạt** (camera thêm 16/11, sau đóng băng) | Video: `scripts/05_run_video.py` đọc file, gắn `source_id`, `session_id` vào mọi sự kiện (`annotated_main/*/events.jsonl`); 13 video chạy đủ khung (`benchmark/`: số khung khớp). Camera: `backend/live.py` (`/api/live/start`), chạy thật 16/11 trên webcam laptop: 1280×720, phiên `cam0_20261116_195139` ghi vào `monitoring_sessions`, sự kiện mang `source_id` `cam0` và `session_id`; `tests/test_live.py` | Một webcam mỗi lần. Webcam trả khoảng 30 FPS nhưng xử lý chỉ **11,5–16 FPS** (2–3 người trong khung, có vẽ và mã hóa JPEG), thấp hơn benchmark video; chưa đo tách từng bước trên camera |
| FR-02 | Phát hiện các lớp PPE: hộp, nhãn, độ tin cậy | **Đạt** | c6_ft 6 lớp + zoom (găng, kính, ủng). **Tập test chạy một lần 26/11** (`c5_eval/final_test_c6_ft.json`, nhãn máy đã sửa C5, chưa người kiểm định toàn bộ), mAP50 có zoom: người 0,923, mũ 0,855, áo 0,821, găng 0,718 [0,637; 0,782], kính 0,756 [0,682; 0,825], ủng 0,596 [0,450; 0,743]. Pictor-PPE (`final2/pictor/`): người 0,851, mũ 0,681, áo 0,477 | Găng, kính, ủng chưa đạt 0,8; spec ghi 4 lớp, đề tài đổi 6 lớp |
| FR-03 | Liên kết PPE với từng người, xử lý nhiều người | **Đạt** | `tests/test_association_compliance.py` (tranh chấp không gán, PPE xa bị loại, găng từng tay, cúi người), `test_pose_regions.py`, `test_torso_strict.py`; V3b trên val (`pipeline_calib_val/assoc_pose.json`); F1 kính theo mắt | Áo người sát camera bị cắt ở ngực thường không gán (B1, B2, F2 không đạt); găng khi không thấy cổ tay thành Chưa xác định |
| FR-04 | Có / Thiếu / Chưa xác định cho từng PPE bắt buộc; găng từng tay | **Đạt** | `frames.csv` mỗi người mỗi khung 5 PPE; `tests/test_association_compliance.py` (Thiếu chỉ khi nhìn rõ, đầu ngoài khung -> Chưa xác định, găng từng tay), `test_compliance_cd.py` (C2, D); hiển thị nhất quán `06c`: 0 vi phạm (`annotated_main/display_audit.json`) | Độ đúng đo so với nhãn máy (chưa người kiểm định). **Holdout** (`holdout_summary.md`): mũ 0,542 (bản 4: 0,630; D làm mất 226 khung Thiếu đúng), áo 0,698, găng 0,497, kính 0,743 (bản 4: 0,528), ủng 0,248 |
| FR-05 | Gán, duy trì mã theo dõi qua khung | **Đạt** | ByteTrack (`src/ppe/tracker.py`); chọn tham số 11/11 bằng `05d --tracker` trên 5 video chỉnh tham số (nhãn người): IDF1 TB 0,919, MOTA TB 0,890, tổng IDSW 5; 05h video18-27: 1 mã/người ở 7 video một người | Đo trên video chỉnh tham số (không khách quan), với detector C4 lúc chọn |
| FR-06 | Tổng hợp theo thời gian; không cảnh báo từ một khung | **Đạt** | `tests/test_temporal_events.py`: `test_single_missing_frame_does_not_alert`, `test_min_valid_frac_blocks_sparse_missing`, `test_unknown_is_not_recovery` | |
| FR-07 | Một sự kiện mỗi đợt vi phạm; cập nhật `missing_items`, không trùng | **Đạt** | `test_continuous_missing_helmet_gives_one_event`, `test_second_missing_ppe_updates_same_event`, `test_recovered_closes_event`; API (`fr_api_check.json`): 36 thay đổi của 7 sự kiện -> 7 bản ghi | Event F1 chỉ đo ở ablation A-E (video 4-6); holdout không có nhãn sự kiện |
| FR-08 | Lưu sự kiện kèm thời gian, nguồn, mã theo dõi, ảnh hoặc clip minh chứng | **Đạt** | `events.jsonl`: thời gian, `source_id`, `session_id`, `track_id`, `evidence_refs`; ảnh `outputs/evidence/<phiên>/`; API: chi tiết 200 có lịch sử, ảnh minh chứng 200 (JPEG 279 KB) | Ảnh, không có clip |
| FR-09 | Dashboard: cảnh báo, lọc lịch sử, xem minh chứng, thống kê | **Đạt (API, WebSocket); giao diện chưa kiểm bằng mắt** | `dashboard/index.html`; API 200 (`final/fr_api_check.json`); **WebSocket `/ws`** (25/11): đẩy "changed" khi dữ liệu đổi và trạng thái camera mỗi giây, `tests/test_live.py::test_ws_pushes_changes_and_live_status`, chạy thử uvicorn thật | Mất kết nối thì quay về hỏi định kỳ |
| FR-10 | Cấu hình PPE bắt buộc cho từng nguồn | **Đạt** cho camera trực tiếp (16/11); video vẫn theo cấu hình | API chính sách theo nguồn có phiên bản; camera đọc chính sách mới nhất khi mở và áp dụng ngay khi đổi (`Pipeline.set_required`). Chạy thật 16/11: PUT `cam0` [vest, helmet] khi đang chạy -> `applied_live: true`, sự kiện đang mở đóng với `policy_changed`, sự kiện mới chỉ còn mũ, áo (`policy_version` 2); `tests/test_live.py` | `05_run_video` (video) vẫn dùng `required_ppe` trong `configs/pipeline.yaml`; dashboard chưa kiểm bằng trình duyệt |

## Yêu cầu phi chức năng liên quan

| Mã | Trạng thái | Bằng chứng |
|---|---|---|
| NFR-01 (đo FPS, thời gian bước, độ trễ cảnh báo) | **Đã đo** | `close_eval/bench_close_fixes/benchmark.md` (25/11, cùng lượt): trước đợt sửa 18,06 ± 0,61 FPS xử lý, sau 17,99 ± 0,43, latency TB 55,6 ms (RTX 3050 Laptop, video3-6). Lần đo 20/11 cùng cấu hình: 20,2 FPS (máy khác trạng thái). Bản 16/11 (C4, không zoom): 26,55 FPS (`final/benchmark_clean/`). Độ trễ cảnh báo (ablation E): 1,41 s |
| NFR-02 (đổi PPE bắt buộc, tham số không sửa module) | Đạt | Tham số trong `configs/pipeline.yaml`; khóa C2, D, F1 bật / tắt không sửa code (test "vắng khóa như bản chính") |
| NFR-05 (tách module, kiểm thử riêng) | Đạt | `src/ppe/` (detector, tracker, pose, parts, association, compliance, temporal, events), `backend/`, `dashboard/`; 224 test |

## Việc còn thiếu để hoàn thiện RQ1-RQ4

1. ~~Đánh giá cuối trên holdout~~: đã chạy một lần 16/11 (`holdout_summary.md`).
2. ~~Đo lại hiệu năng~~: đã đo lại 16/11 (`benchmark_clean/`).
3. ~~Pictor-PPE~~: đã làm 16/11 (`pictor/pictor_eval.md`).
4. Kiểm giao diện dashboard bằng trình duyệt; camera trực tiếp (FR-01) nếu cần.
