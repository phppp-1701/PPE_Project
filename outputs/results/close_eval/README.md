# close_eval: đánh giá đóng băng mũ bản 4 (ngoại lệ) và 9 video kiem_thu_gan

Quyết định và tiêu chí: `docs/experiments/2026-11-06_ppe6_plan.md`, mục "Ngoại lệ bản 4 cho mũ". Bản 4 **không đạt**
tiêu chí "bỏ sót không tăng" trên video 3-6. Người dùng chọn bật bản 4, ghi trước khi chạy 9 video `kiem_thu_gan`.

## File

| File / thư mục | Nội dung |
|---|---|
| `pipeline_baseline_0645f53.yaml` | Cấu hình bản cũ (mũ theo luật cũ), lấy nguyên từ `git show 0645f53:configs/pipeline.yaml` |
| `dev_check/` | Giai đoạn 2: hai cấu hình trên video 3-6 (video phát triển); `results.md`, `results.json`, `transitions.csv`, `<cấu hình>/<video>/frames.csv, events.jsonl, summary.json` |
| `benchmark/` | Giai đoạn 3: `benchmark.md`, `benchmark.json` (video 3-6) |
| `manifest.json` | Giai đoạn 4: commit nguồn, sha256 cấu hình, trọng số, video, nhãn, môi trường |
| `kiem_thu_gan/` | Giai đoạn 5 (chỉ chạy khi người dùng cho phép): hai cấu hình trên 9 video `kiem_thu_gan` |

## Tái lập (từ thư mục gốc, đã kích hoạt `.venv`)

```
# 0. Lấy đúng code: commit nguồn ghi trong manifest.json (source_commit)
git checkout <source_commit>

# 1. Cấu hình bản cũ
git show 0645f53:configs/pipeline.yaml > outputs/results/close_eval/pipeline_baseline_0645f53.yaml

# 2. Kiểm tra kỹ thuật trên video 3-6
python scripts/06b_evaluate_close_videos.py evaluate --videos video3 video4 video5 video6 \
    --labels "data/videos/{v}_cvat.zip" --label-note "..." \
    --config baseline=outputs/results/close_eval/pipeline_baseline_0645f53.yaml --config v4=configs/pipeline.yaml \
    --out outputs/results/close_eval/dev_check

# 3. Hiệu năng (không chạy việc GPU khác cùng lúc)
python scripts/07_benchmark_pipeline.py \
    --config baseline=outputs/results/close_eval/pipeline_baseline_0645f53.yaml --config v4=configs/pipeline.yaml \
    --videos video3 video4 video5 video6 --repeats 3 --out outputs/results/close_eval/benchmark

# 4. Manifest (cây làm việc phải sạch)
python scripts/06b_evaluate_close_videos.py manifest --config configs/pipeline.yaml \
    --baseline-commit 0645f53 --baseline-config outputs/results/close_eval/pipeline_baseline_0645f53.yaml \
    --videos video9 video10 video11 video12 video13 video14 video15 video16 video17 \
    --labels "data/videos/{v}_machine_cvat.zip" --out outputs/results/close_eval/manifest.json

# 5. 9 video kiem_thu_gan, kiểm manifest trước khi chạy
python scripts/06b_evaluate_close_videos.py evaluate --manifest outputs/results/close_eval/manifest.json \
    --videos video9 video10 video11 video12 video13 video14 video15 video16 video17 \
    --labels "data/videos/{v}_machine_cvat.zip" --label-note "..." \
    --config baseline=outputs/results/close_eval/pipeline_baseline_0645f53.yaml --config v4=configs/pipeline.yaml \
    --out outputs/results/close_eval/kiem_thu_gan
```

Trọng số (`outputs/train/...`, video `data/videos/*.mp4`) không nằm trên Git; sha256 trong `manifest.json` để kiểm
đúng file. sha256 của file text (`.yaml`, `.py`, ... ; `hash_mode: lf_normalized`) tính sau khi đổi CRLF
thành LF, vì `core.autocrlf` làm file lấy từ Git có CRLF hay LF tùy máy; file khác (`raw`) tính nguyên byte.
`manifest.json` nằm ở commit sau commit nguồn và không ghi mã commit chứa chính nó. Kết quả lặp lại được: chạy lại cho `frames.csv` giống từng byte (đã kiểm trên video 3-6).

## Lưu ý khi đọc số

- Nhãn 9 video `kiem_thu_gan` (`video9..17_machine_cvat.zip`) là **nhãn máy qua hai lượt (machine_consensus), chưa
  được người kiểm định**. Số so với nhãn này không phải độ chính xác tuyệt đối so với thực tế.
- Nhãn video 3-6 là nhãn video chỉnh tham số (một phần do Claude sửa ngày 13/11/2026, chưa người duyệt); video 3-6
  là video phát triển, không phải tập đánh giá.
- Số là số khung-người. Hộp nhãn không ghép được người dự đoán nằm ở cột "Không ghép", không bị bỏ.
- Hiệu năng: phạm vi đo ghi trong `benchmark.md`; GPU và VRAM của cả card lấy từ `nvidia-smi` theo mẫu, không phải đo
  liên tục.
