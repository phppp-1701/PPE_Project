# data/ppe6 — Thử nghiệm 6 lớp (nhánh `exp/ppe6`)

Lớp: 0-3 như `ppe4`, 4 kính bảo hộ, 5 ủng bảo hộ. Kế hoạch: `docs/experiments/2026-11-06_ppe6_plan.md`.

`review/` do `scripts/03c_ppe6_review_sheets.py` tạo:

- `boxes.csv`: danh sách hộp kính, giày gốc cần duyệt.
- `sheets/`: bảng ảnh, hộp viền đỏ, số ở góc là `box_id`.
- `sheets/*.txt`: mã hộp của từng bảng, dùng cho `--apply`.
- `decisions.csv`: kết quả duyệt (`safety`, `ordinary`, `unclear`), ghi rõ người hay Claude duyệt. Quy tắc ở `docs/annotation_rules.md`.

- `review/decisions_v2.csv`: quyết định theo định nghĩa kính 2, có giá trị trước và sau.

`scene/`: `features.npz`, `scene_ids.csv`, `near_threshold.csv` và ảnh mẫu kiểm tra cụm (`03e`, `03f`).

`eval/`: `scene_roles.csv` (cảnh đánh giá), `chvg_split.csv`, `tradeoff.csv` (`03h`).

`dataset/`: bộ 6 lớp (`03i`). `images/`, `labels/` chỉ có trên máy; `manifest.json`, `excluded.csv`, `eval_status.csv`, `ignore.csv` có trên git. `val_new.txt`, `test_new.txt` chỉ gồm ảnh đã có người chốt. `ignore.csv`: vùng bỏ qua khi đánh giá lớp mới (hộp người chốt `unclear`, `ignore`), luật ở `configs/ppe6.yaml` mục `eval_ignore`.

`dataset_c1/`, `dataset_c2/`: train C1, C2 (`03m`); `dataset/` là C0, không sửa. `dataset_c2/mask_map.csv`: ảnh gốc, ảnh che, vùng che. `variants/`: bảng mất dữ liệu, so sánh, gói Kaggle.

`review/cvat_pack_blind/`: gói duyệt mù (`03p`), dùng gói này để duyệt. `_private/` giữ nhóm gốc, giá trị agent: người duyệt không mở. `review/second_review.csv`, `agreement.json`: người thứ hai, chỉ để kiểm tra chất lượng.

`review/fast_<task>_state.json`, `fast_<task>_log.csv`: phiên và nhật ký của công cụ duyệt nhanh (`03q`). `review/export_<task>_<thời gian>.zip`: file xuất CVAT giữ lại (`03r`).

`review/machine_pass_a.csv`, `machine_pass_b.csv`, `machine_merged.csv`: nhãn máy hai lượt và kết quả gộp (`03t`), không phải nhãn người. `review/cvat_pack_audit/`: gói kiểm định (`audit`, `audit_img2`; `audit_img` bản đầu lỗi, không dùng), `_private/` không mở khi duyệt. `review/audit_review.csv`, `audit_report.json`: người kiểm định.

`review/cvat_pack/`: gói duyệt (`03k`), hướng dẫn ở `docs/ppe6_review_guide.md`. `review/human_review.csv`: kết quả người duyệt (`03l`), chỉ xuất hiện khi có người nhập.

`external/chvg/`: CHVG tải từ figshare (`03g`), không đưa lên git. Chưa dùng cho train.

`parts/`: ảnh cắt tay, chân, mắt cho bộ phân loại kiểm tra thứ hai (`03y`), dạng thư mục YOLO-cls `train/`, `val/`; chỉ có trên máy, `summary.json` ghi số lượng.
`parts_v5/`: bộ phân loại bản 5 (`03y`, `parts.version: 5`, kế hoạch 2026-11-16_post_holdout_fixes mục 3b): `parts/` bản 4 chép nguyên (train, val) + ảnh đầu mũ / không mũ từ kho chọn theo tầng (kiểu cắt × tối × nhỏ) để mỗi tầng có mũ ≈ không mũ; `added_meta.csv` (ảnh thêm), `summary.json` (bảng tầng, kiểm tỉ lệ); gói `variants/kaggle/parts_v5_pack.zip`; chỉ có trên máy.

`parts_v5_pool/`: kho ảnh đầu nguồn mới của bản 5 (CHV train, `hard_hat_cc0`, SHWD; cắt như train, có bản làm tối cho người quay lưng), `meta.csv` (nguồn, kiểu cắt, nhìn từ sau, cỡ, độ sáng), `pool_info.json`; chỉ có trên máy.

`parts_v5_check/`: tập kiểm riêng bản 5: 15% ảnh CC0 và SHWD không vào train, cắt kiểu val, `meta.csv`; nhãn gốc của bộ công khai; chỉ để báo cáo tỉ lệ nhầm theo tầng, không là tiêu chí; chỉ có trên máy.

`c5/`: C5, sửa nhãn và mở rộng val/test (`03z`, kế hoạch 2026-11-16_c5_detector_plan), nhãn máy: `owl_eval.json`, `c4_*_pred.json`, `sh17_hands.csv` (đề xuất); `review_items_*.csv`, `review/` (bảng ảnh, `.txt` ô → item, `.dec` quyết định của Claude), `machine_pass_claude.csv`; `dataset_c5/` (train C2 + sửa), `c5_extra/` (bộ phụ), `changes_*.csv` (mọi thay đổi); `eval/{val,test}/`, `eval/ignore.csv`, `eval/files.json` (val/test đã sửa); `audit/audit.html` (kiểm định của người), `audit/_private/` (đáp án máy, người kiểm định không mở). Ảnh, nhãn chỉ có trên máy. Gói Kaggle `variants/kaggle/c5_pack.zip`, `c5_extra_pack.zip`.

`c6/`: C6 (`03za`): `scan.json`, `eval_hashes.json` (pHash), `ext/` (ảnh ủng ngoài đã lọc, nhãn), `rotcheck/` (bảng Claude xem, `.dec` ô bị loại), `c6_extra/` (bộ phụ C6). Chỉ có trên máy; gói `variants/kaggle/c6_extra_pack.zip`.

`c7/`: C7 (`03zb`): `c6ft_train_boots_pred.json`, `changes_c7.csv`, `c7_extra/` (bộ phụ C7). Chỉ có trên máy; gói `variants/kaggle/c7_extra_pack.zip`.

`c8/`: C8 găng (`03zc`, `03za --section c8_ext`): `c6ft_train_gloves_pred.json`, `test_gloves_pred.json`, `scan.json`, `eval_hashes.json`, `ext/` (ảnh găng ngoài đã lọc), `c8_extra/` (bộ phụ C8, không đạt `c8_decision`). Chỉ có trên máy; gói `variants/kaggle/c8_extra_pack.zip`.

`c9/`: C9 (`03zd`): `zoom/` (3.000 ảnh cắt người `zoom__<ảnh>__<người>.jpg` ở độ phân giải gốc của train C5, nhãn đã đổi theo vùng cắt, `summary.json` có vùng cắt của từng ảnh), `c9_extra/` (= `c6/c6_extra` + `zoom/`, trọng số c6_ft). Chỉ có trên máy; gói `variants/kaggle/c9_extra_pack.zip`.
