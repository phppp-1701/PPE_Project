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

`dataset/`: bộ 6 lớp (`03i`). `images/`, `labels/` chỉ có trên máy; `manifest.json`, `excluded.csv`, `eval_status.csv` có trên git. `val_new.txt`, `test_new.txt` chỉ gồm ảnh đã có người chốt.

`review/cvat_pack/`: gói duyệt (`03k`), hướng dẫn ở `docs/ppe6_review_guide.md`. `review/human_review.csv`: kết quả người duyệt (`03l`), chỉ xuất hiện khi có người nhập.

`external/chvg/`: CHVG tải từ figshare (`03g`), không đưa lên git. Chưa dùng cho train.
