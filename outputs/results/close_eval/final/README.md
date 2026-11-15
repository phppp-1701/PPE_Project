# close_eval/final: đóng băng bản cuối và đánh giá cuối

Bản cuối (người dùng duyệt 16/11/2026): **bản 4 + D + C2 + F1** (`configs/pipeline.yaml` ở commit nguồn ghi trong
`manifest.json`). Quyết định, tiêu chí, kết quả từng bước: `docs/experiments/2026-11-06_ppe6_plan.md` (mục C, D, C2, F,
hiển thị nhất quán) và `docs/experiments/2026-11-15_completion_plan.md`.

## Quy tắc

- Sau commit nguồn, code và cấu hình ngoài `outputs/results/close_eval/` không đổi; `06b evaluate --manifest` kiểm lại
  trước khi chạy và dừng nếu lệch (code, cấu hình, trọng số, video, nhãn).
- Đánh giá trên holdout (`data/videos/holdout/`, 8 video niêm phong) **chỉ chạy một lần, khi người dùng cho phép**.
  Không chỉnh tham số, logic sau khi xem kết quả. Nhãn holdout là nhãn máy qua hai lượt, chưa người kiểm định.
- Mốc so sánh: bản 4 (`pipeline_v4_0b756b8.yaml` = `git show 0b756b8:configs/pipeline.yaml`).

## File

| File / thư mục | Nội dung |
|---|---|
| `pipeline_v4_0b756b8.yaml` | Cấu hình bản 4 (mốc) |
| `manifest.json` | Commit nguồn, sha256 cấu hình, trọng số, script, video và nhãn holdout (so khớp `data/videos/holdout/manifest.json`), môi trường |
| `benchmark/` | Hiệu năng bản 4 và bản cuối trên video 3-6 (`07_benchmark_pipeline.py`), lần 1: máy đang chạy Minecraft, **số tuyệt đối không dùng**, chỉ giữ để đối chiếu |
| `benchmark_clean/`, `benchmark_clean_run.log` | Đo lại cùng lệnh sau khi tắt game (GPU nghỉ P8 trước khi đo): **số dùng cho báo cáo** |
| `fr_table.md` | Bảng FR-01…10 (Đạt / Không đạt / Chưa kiểm thử) kèm bằng chứng |
| `holdout/`, `holdout_run.log` | Đánh giá cuối, **đã chạy một lần** 16/11/2026 theo cho phép của người dùng. Trên Git chỉ có `results.md`, `results.json` (số đếm); `transitions.csv` (nhãn từng khung) và `frames.csv` của từng video chỉ giữ ở máy |
| `holdout_summary.md` | Tóm tắt holdout: mũ giảm (0,630 → 0,542, D chặn báo thiếu ở h2), kính tăng (0,528 → 0,743), áo, găng, ủng không đổi |
| `pictor/pictor_eval.py`, `pictor/pictor_eval.md`, `pictor/pictor_eval.json` | Kiểm thử ngoài detector trên Pictor-PPE (RQ1), C4 và r2; chép tập sang thư mục tạm để không ghi `.cache` vào `data/ppe4/`. Chạy: `python outputs/results/close_eval/final/pictor/pictor_eval.py --work <thư mục tạm>` |

## Tái lập

```
# 1. Manifest (cây làm việc sạch, ở commit nguồn)
python scripts/06b_evaluate_close_videos.py manifest --config configs/pipeline.yaml \
    --baseline-commit 0b756b8 --baseline-config outputs/results/close_eval/final/pipeline_v4_0b756b8.yaml \
    --videos holdout/h1 holdout/h2 holdout/h3 holdout/h4 holdout/h5 holdout/h7 holdout/h8 holdout/h9 \
    --labels "data/videos/holdout/labels/{b}_machine_cvat.zip" --out outputs/results/close_eval/final/manifest.json

# 2. Hiệu năng (không chạy việc GPU khác cùng lúc)
python scripts/07_benchmark_pipeline.py --config v4=outputs/results/close_eval/final/pipeline_v4_0b756b8.yaml \
    --config final=configs/pipeline.yaml --videos video3 video4 video5 video6 --repeats 3 \
    --out outputs/results/close_eval/final/benchmark

# 3. Đánh giá cuối (CHỈ khi người dùng cho phép; kiểm manifest trước khi chạy)
python scripts/06b_evaluate_close_videos.py evaluate --manifest outputs/results/close_eval/final/manifest.json \
    --videos holdout/h1 holdout/h2 holdout/h3 holdout/h4 holdout/h5 holdout/h7 holdout/h8 holdout/h9 \
    --labels "data/videos/holdout/labels/{b}_machine_cvat.zip" --label-note "..." \
    --config v4=outputs/results/close_eval/final/pipeline_v4_0b756b8.yaml --config final=configs/pipeline.yaml \
    --out outputs/results/close_eval/final/holdout
```

h6 bị loại khi gán nhãn (vi phạm tiêu chí 3), trước mọi dự đoán (`data/videos/holdout/sources.csv`).
