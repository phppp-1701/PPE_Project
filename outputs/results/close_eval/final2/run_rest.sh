# Đánh giá cuối phần còn lại (kế hoạch 2026-11-25_final_evaluation_plan.md), cấu hình đóng băng 28ad782.
export YOLO_AUTOINSTALL=False
PY=.venv/Scripts/python
F=outputs/results/close_eval/final2
$PY scripts/06_evaluate_ablation.py --config configs/pipeline.yaml --out $F/ablation.json > $F/ablation.log 2>&1
$PY scripts/06b_evaluate_close_videos.py evaluate --videos holdout/h1 holdout/h2 holdout/h3 holdout/h4 holdout/h5 holdout/h7 holdout/h8 holdout/h9 \
  --labels "data/videos/holdout/labels/{b}_machine_cvat.zip" --label-note "nhãn máy hai lượt, chưa người kiểm định; KIỂM TRA SAU KHI SỬA, KHÔNG CÒN MÙ (số chính thức: final/holdout 16/11)" \
  --config v4=outputs/results/close_eval/final/pipeline_v4_0b756b8.yaml --config before=outputs/results/c5_eval/zoom_bench/pipeline_zoom_n1.yaml --config final2=configs/pipeline.yaml \
  --out $F/holdout_check > $F/holdout_check.log 2>&1
$PY scripts/06b_evaluate_close_videos.py evaluate --videos video3 video4 video5 video6 --labels "data/videos/{v}_cvat.zip" --label-note "nhãn người (video chỉnh tham số)" \
  --config before=outputs/results/c5_eval/zoom_bench/pipeline_zoom_n1.yaml --config final2=configs/pipeline.yaml --out $F/dev36 > $F/dev36.log 2>&1
$PY scripts/05h_close_range_probe.py --ids 18-27 --no-video --out $F/close_probe > $F/close_probe.log 2>&1
echo ALL_DONE > $F/done.txt
