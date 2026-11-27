#!/bin/bash
# Tiếp run_all.sh sau khi máy restart (28/11/2026): event_eval và holdout đã xong; chạy lại kiem_thu_gan (bị ngắt), ablation, tốc độ.
set -e
cd /d/KhoaLuan/PPE_PROJECT
export YOLO_AUTOINSTALL=False PYTHONIOENCODING=utf-8
PY=.venv/Scripts/python.exe; F=outputs/results/close_eval/final4; B=$F/pipeline_final2_28ad782.yaml
$PY scripts/07_benchmark_pipeline.py --config final2=$B --config final4=configs/pipeline.yaml --out $F/benchmark > $F/benchmark.log 2>&1
$PY scripts/06b_evaluate_close_videos.py evaluate --videos video9 video10 video11 video12 video13 video14 video15 video16 video17 --labels "data/videos/{v}_machine_cvat.zip" --label-note "kiem_thu_gan nhãn máy; chỉ đo" --config final2=$B --config final4=configs/pipeline.yaml --out $F/kiem_thu_gan > $F/kiem_thu_gan.log 2>&1
$PY scripts/06_evaluate_ablation.py --config configs/pipeline.yaml --out $F/ablation.json > $F/ablation.log 2>&1
$PY scripts/06f_holdout_events.py --run $F/holdout_check/final4 --out $F/holdout_events.json > $F/holdout_events.log 2>&1
echo XONG > $F/done.txt
