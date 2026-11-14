# scripts — Các lệnh chạy theo thứ tự

| File | Việc | Bước kế hoạch |
|---|---|---|
| `00_check_env.py` | Kiểm tra PyTorch nhận GPU, chạy thử YOLO11s trên ảnh mẫu | 0 |
| `01_convert_labels.py` | Đổi nhãn từng bộ về bốn lớp theo `configs/label_map.yaml`, ghi vào `data/ppe4/converted/` (chưa chép ảnh) | 1 |
| `01a_cvat_export.py` | Đóng gói nhãn 4 lớp của một bộ (vd. CHV) thành các phần định dạng CVAT YOLO 1.1 kèm zip ảnh, để gán bổ sung găng tay | 1 |
| `01b_cvat_upload.py` | Tự tạo task trên app.cvat.ai cho các phần đã đóng gói (tải ảnh, nạp nhãn YOLO 1.1); bỏ qua task đã có. `--check-first` đưa ảnh cần người xem lên đầu task. Cần biến môi trường `CVAT_ACCESS_TOKEN` do người dùng tự gán | 1 |
| `01c_prelabel_gloves.py` | Gán trước găng tay bằng YOLOE (tham số trong `configs/prelabel.yaml`), lưu CSV; `--upload` thêm hộp (nguồn `auto`) vào task CVAT để người duyệt | 1 |
| `01d_cvat_apply_review.py` | Áp kết quả duyệt tự động (`chv_review_boxes.csv`, `chv_review_images.csv`) lên CVAT: xóa hộp găng sai còn nguyên, gắn tag `check` cho ảnh cần người xem | 1 |
| `01e_cvat_reorder_task.py` | Tạo lại một task CVAT để ảnh có tag `check` lên đầu, giữ nguyên mọi hộp/tag và nguồn, có sao lưu và đối chiếu; `--first` chọn thứ tự các ảnh `check` | 1 |
| `01f_import_cvat.py` | Nhập nhãn đã gán trên CVAT (`<bộ>_partXX_done_cvat.zip`) về `data/ppe4/converted/<bộ>/labels`, thêm cột `review` (human/machine) và `reject` vào `index.csv`, liệt kê hộp person/helmet/vest bị thêm/xóa so với nhãn gốc; nhãn cũ sao lưu ở `labels_before_cvat/` | 1 |
| `02_check_data.py` | Kiểm tra dữ liệu, ghi báo cáo vào `data/ppe4/check/`. `--technical`: lỗi kỹ thuật (ảnh hỏng, nhãn sai định dạng, hộp ra ngoài ảnh) và thống kê; `--duplicates`: dấu vân tay dHash, cặp ảnh trùng/gần trùng, `group_id` (`groups.csv`); `--content`: liệt kê hộp đáng ngờ theo quy tắc; `--missing-person`: chạy `yolo11s.pt` tìm người chưa có hộp | 1 |
| `03_split_data.py` | Chia train/val/test 70/15/15 theo `group_id` (tham số trong `configs/split.yaml`): bỏ ảnh reject, áp `fixes.csv`, nhóm có ảnh máy duyệt hoặc hộp máy thêm buộc vào train, các nhóm còn lại cân bằng theo số ảnh từng bộ và số hộp từng lớp. Ghi `data/ppe4/dataset/`, `data/ppe4/pictor_test/`, `data/ppe4/stats.csv`. `--dry-run` chỉ in bảng chia | 1 |
| `03b_make_extra_train.py` | Tạo bộ phụ cho r3 từ ảnh train (không đụng val, test): ảnh cắt từng người nhỏ, người lớn thu nhỏ mô phỏng người ở xa, danh sách ảnh có găng lấy thêm. Tham số ở `configs/train.yaml` mục `extra`, ghi `data/ppe4/r3_extra/`. `--dry-run` chỉ đếm | 2 |
| `03c_ppe6_review_sheets.py` | Thử nghiệm 6 lớp: lập danh sách hộp kính, giày gốc, vẽ bảng ảnh để duyệt, ghi `data/ppe6/review/`. `--apply` ghi quyết định theo bảng, `--mark-small` đánh dấu hộp quá nhỏ, `--summary` chỉ đếm. Tham số ở `configs/ppe6.yaml` | thử nghiệm |
| `03d_ppe6_decisions_v2.py` | Áp định nghĩa kính 2, ghi `data/ppe6/review/decisions_v2.csv`, không sửa `decisions.csv` | thử nghiệm |
| `03e_ppe6_scene_features.py` | Tính pHash, đặc trưng YOLO, biểu đồ màu của mọi ảnh, ghi `data/ppe6/scene/features.npz` | thử nghiệm |
| `03f_ppe6_scene_ids.py` | Gom cảnh theo ngưỡng ở `configs/ppe6.yaml`; `--sweep` thử lưới ngưỡng | thử nghiệm |
| `03g_ppe6_chvg_check.py` | Kiểm MD5, giải nén, thống kê CHVG vào `data/ppe6/external/chvg/` | thử nghiệm |
| `03h_ppe6_select_eval.py` | Chọn cảnh cho `val_new`, `test_new`, tách CHVG theo cảnh. `--sweep` in bảng đánh đổi các mức mục tiêu ủng | thử nghiệm |
| `03i_ppe6_build_dataset.py` | Sinh bộ 6 lớp vào `data/ppe6/dataset/` (ảnh là liên kết cứng), manifest, kiểm tra rò rỉ ảnh, cảnh, mã lớp, tọa độ. `--check` chỉ kiểm tra | thử nghiệm |
| `03j_ppe6_noise.py` | Đo nhiễu giày SH17, tác động ngưỡng cỡ hộp, chọn mẫu P2, ghi `outputs/results/ppe6_noise/` | thử nghiệm |
| `03k_ppe6_cvat_pack.py` | Tạo gói duyệt CVAT P0a, P0b, P1, P2 và bảng cảnh, không tải lên CVAT | thử nghiệm |
| `03l_ppe6_import_review.py` | Nhập kết quả người duyệt, giữ dấu vết; `--report` tỉ lệ bất đồng, đề xuất ngưỡng người đủ lớn | thử nghiệm |
| `03m_ppe6_train_variants.py` | Tạo train C1 (thêm CHV ghép nhãn kính), C2 (che vùng không rõ), bảng mất dữ liệu, bảng so sánh, gói Kaggle, kiểm tra rò rỉ | thử nghiệm |
| `03n_ppe6_readiness.py` | Chấm quy tắc sau duyệt (`gates`), tính ngưỡng người đủ lớn (`scope`), dựng `val_monitor` từ nhãn đã duyệt và gói cuối (`monitor`), checklist sẵn sàng train (`checklist`) | thử nghiệm |
| `03p_ppe6_blind_pack.py` | Tạo gói duyệt mù `cvat_pack_blind/`: ẩn nhãn agent, nguồn, nhóm, trộn ngẫu nhiên, gói `trial`, gói người thứ hai; `--check` quét lộ nhãn | thử nghiệm |
| `03q_ppe6_fast_review.py` | Giao diện duyệt nhanh cục bộ ở `127.0.0.1`: ảnh đầy đủ và ảnh phóng to, phím số, tự lưu. Mọi nhãn do người bấm từng hộp, không có đề xuất hay chọn hàng loạt | thử nghiệm |
| `03r_ppe6_fast_finish.py` | Lệnh cuối buổi: đồng bộ CVAT, đối chiếu từng ô, xuất, nhập bằng `03l`, `--report`, `03i`, in điều kiện dừng. Token đọc từ `CVAT_LOCAL_TOKEN` | thử nghiệm |
| `03s_ppe6_fast_e2e.py` | Kiểm thử công cụ duyệt nhanh trên CVAT thật bằng task bản sao `fast_agent_test`, reviewer `AGENT_TEST`, rồi xóa task đó | thử nghiệm |
| `03t_ppe6_machine_label.py` | Quy trình máy gán: `sheets` vẽ bảng ảnh cho từng lượt, `collect` khóa kết quả lượt, `merge` gộp, `compare` so với nhãn cũ sau khi khóa, `audit` tạo gói kiểm định, `audit-img2` gói ảnh làm lại có hộp đã có và lớp được hỏi, `rest` gói hộp val, test còn lại khi kiểm định không đạt, `rest-import`, `eval-count`, `audit-import`, `audit-report` | thử nghiệm |
| `03u_ppe6_consistency.py` | Tỷ lệ tự nhất quán của nhãn người: khung lặp trong các tập đánh giá và hộp được chấm hai lần, ghi `outputs/results/ppe6_consistency.json` | thử nghiệm |
| `03w_ppe6_owl_scan.py` | Soát nhãn train bằng OWLv2 (nhận diện theo chữ, không train): tìm khung ủng, kính bị sót hoặc sai, chỉ để chọn chỗ xem lại | thử nghiệm |
| `03x_ppe6_c4_extra.py` | Bộ phụ C4: bộ phụ C3 + ảnh Construction-PPE bản mới (bỏ ảnh trùng cảnh đánh giá, đổi về 6 lớp, che ủng nhỏ), gói Kaggle | thử nghiệm |
| `03y_ppe6_part_crops.py` | Bộ dữ liệu phân loại ảnh cắt tay, chân, mắt (7 lớp: găng/tay trần, ủng/giày thường-chân trần, kính bảo hộ/kính thường/không kính) cho bước kiểm tra thứ hai | thử nghiệm |
| `04g_train_parts_cls.py` | Train bộ phân loại ảnh cắt (YOLO11n-cls) trên Kaggle | thử nghiệm |
| `04_train.py` | Huấn luyện YOLO11s trên Kaggle theo `configs/train.yaml` (tự tìm `data.yaml` trong `/kaggle/input`), `--resume` chạy tiếp từ `last.pt`; `--extra` ghép bộ phụ của `03b` vào train; `--ppe6` dựng bộ 6 lớp từ gói của `03m`, `--smoke` kiểm tra đường chạy 1 epoch; xong thì đánh giá `best.pt` trên val, ghi `run_info.json` (GPU, phiên bản, thời gian, P/R/mAP từng lớp) | 2 |
| `04b_analyze_val.py` | Phân tích lỗi một lần huấn luyện trên val (laptop): tính lại mAP, tỉ lệ tìm được theo lớp × bộ × cỡ hộp, danh sách dự đoán thừa, ô cắt mẫu bỏ sót / dự đoán thừa, tốc độ trên laptop (`speed.json`, batch 1; `--speed-only` chỉ đo tốc độ; `--imgsz` chạy ở cỡ ảnh khác lúc train, ghi vào `<run>_val_infer<cỡ>/`); tham số ở `configs/train.yaml` mục `analyze`, ghi `outputs/results/<run>_val/` | 2 |
| `04d_capture_val.py` | Chạy `model.val`, lưu dự đoán, nhãn, `tp` của Ultralytics từng ảnh; chỉ dùng val | thử nghiệm |
| `04e_ppe6_eval.py` | Bộ đánh giá duy nhất: `old` so 4 lớp cũ trên val gốc, val sạch, bootstrap ghép cặp theo cảnh; `new` đo kính, ủng có xử lý `ignore` | thử nghiệm |
| `04f_check_run.py` | Kiểm tra đầu ra train: `best.pt` lưu được, tải được, đúng 6 lớp, kích thước hợp lý | thử nghiệm |
| `05a_calibrate_val.py` | Chọn trên val ảnh tham số của chuỗi xử lý: `--regions` vùng cơ thể và `max_distance` từ vị trí tâm PPE (nhãn thật) trong hộp người; `--conf` conf từng lớp (F1 lớn nhất) và NMS IoU từ dự đoán của detector; `--crop` so sánh PPE dò cả khung với dò trên ảnh cắt từng người ở các cỡ ảnh cắt. `--pose` tính tỉ lệ tâm găng nhãn thật nằm trong elip cổ tay, so với vùng tay. Ghi đề xuất vào `outputs/results/pipeline_calib_val/`, người chép giá trị đã duyệt vào `configs/pipeline.yaml` | 3 |
| `05_run_video.py` | Chạy một video qua chuỗi xử lý tới bước xa nhất đã đủ tham số (`--stage` chọn bước): ghi video đã vẽ, `frames.csv` (trạng thái từng người mỗi khung), `events.jsonl`, `summary.json` (FPS, thời gian từng bước) vào `outputs/results/video/<tên video>/` | 3 |
| `05b_cvat_video_task.py` | Tạo task CVAT cho một video (`data/videos/<video_id>.mp4`) với bộ nhãn trong `docs/video_labeling.md`, không kèm dự đoán của hệ thống; task cùng tên đã có thì dừng. `--dry-run` chỉ in kế hoạch. Token đọc từ `CVAT_ACCESS_TOKEN` hoặc `~/.cvat_token` | 3 |
| `05c_cvat_prefill_people.py` | Vẽ sẵn hộp người cho task video trên CVAT bằng `yolo11s.pt` gốc, nối tiếp các track người gán đã vẽ, không điền PPE; tham số ở `configs/prelabel.yaml` mục `video_people`. Mặc định chỉ tạo bản xem trước và `review.csv` (khung cần xem) trong `outputs/results/video/<video>/prefill/`; `--upload` sao lưu rồi ghi lên CVAT. Chỉ dùng cho video chỉnh tham số | 3 |
| `05d_calibrate_video.py` | Chọn tham số trên video `chinh_tham_so` so với nhãn CVAT: `--tracker` thử ByteTrack (MOTA, IDF1, IDSW), `--state` thử `ambiguity_margin`, `tau_in`, `tau_occ`, `area_min_px` (ma trận 3×3, macro-F1, Coverage); `--rerun` chạy lại detector. Lưới ở `configs/pipeline.yaml` mục `calibration.video`; ghi đề xuất vào `outputs/results/pipeline_calib_video/<video>/`, người chép giá trị đã duyệt vào config | 3 |
| `05e_select_part_cls.py` | Chọn hình học ảnh cắt (theo keypoint) và ngưỡng `t_pos`, `t_neg` của bộ phân loại bộ phận trên val (ảnh cắt kiểu pipeline); ghi `outputs/results/parts_cls/val_select.json`, in khối gợi ý, người chép vào `configs/pipeline.yaml` mục `part_cls` | thử nghiệm |
| `05f_cvat_prefill_xml.py` | Vẽ sẵn track người (yolo11s.pt gốc, không dự đoán PPE) cho video, ghi `outputs/results/video/<video>/prefill/annotations.xml` (CVAT for video 1.1) để tải lên CVAT cục bộ bằng giao diện; kèm `review.csv`, `preview.mp4`. Dùng cho video `kiem_thu_gan` (người dùng duyệt 14/11/2026) | thử nghiệm |
| `06_evaluate.py` | Tính độ đo, so sánh cấu hình A-E | 5 |

Các file sẽ được viết dần khi làm tới bước tương ứng.
