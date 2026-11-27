#!/bin/bash
# Cấu hình cuối 3 (5d7acec): chạy một lần sau đóng băng 28/11/2026.
set -e
cd /d/KhoaLuan/PPE_PROJECT
export YOLO_AUTOINSTALL=False PYTHONIOENCODING=utf-8
PY=.venv/Scripts/python.exe; F=outputs/results/close_eval/final4; B=$F/pipeline_final2_28ad782.yaml
$PY scripts/06e_event_eval.py --config configs/pipeline.yaml --out outputs/results/event_eval/final4 > $F/event_eval.log 2>&1
$PY scripts/06b_evaluate_close_videos.py evaluate --videos holdout/h1 holdout/h2 holdout/h3 holdout/h4 holdout/h5 holdout/h7 holdout/h8 holdout/h9 --labels "data/videos/holdout/labels/{b}_machine_cvat.zip" --label-note "nhãn máy hai lượt, chưa người kiểm định; KIỂM TRA SAU KHI SỬA, KHÔNG CÒN MÙ (số chính thức: final/holdout 16/11)" --config final2=$B --config final4=configs/pipeline.yaml --out $F/holdout_check > $F/holdout_check.log 2>&1
$PY scripts/06b_evaluate_close_videos.py evaluate --videos video9 video10 video11 video12 video13 video14 video15 video16 video17 --labels "data/videos/{v}_machine_cvat.zip" --label-note "kiem_thu_gan nhãn máy; chỉ đo" --config final2=$B --config final4=configs/pipeline.yaml --out $F/kiem_thu_gan > $F/kiem_thu_gan.log 2>&1
$PY scripts/06_evaluate_ablation.py --config configs/pipeline.yaml --out $F/ablation.json > $F/ablation.log 2>&1
$PY scripts/07_benchmark_pipeline.py --config final2=$B --config final4=configs/pipeline.yaml --out $F/benchmark > $F/benchmark.log 2>&1
echo XONG > $F/done.txt
