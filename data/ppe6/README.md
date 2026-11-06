# data/ppe6 — Thử nghiệm 6 lớp (nhánh `exp/ppe6`)

Lớp: 0-3 như `ppe4`, 4 kính bảo hộ, 5 ủng bảo hộ. Kế hoạch: `docs/experiments/2026-11-06_ppe6_plan.md`.

`review/` do `scripts/03c_ppe6_review_sheets.py` tạo:

- `boxes.csv`: danh sách hộp kính, giày gốc cần duyệt.
- `sheets/`: bảng ảnh, hộp viền đỏ, số ở góc là `box_id`.
- `sheets/*.txt`: mã hộp của từng bảng, dùng cho `--apply`.
- `decisions.csv`: kết quả duyệt (`safety`, `ordinary`, `unclear`), ghi rõ người hay Claude duyệt. Quy tắc ở `docs/annotation_rules.md`.
