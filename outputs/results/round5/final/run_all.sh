#!/bin/bash
# Round5: so cuối 4 (cuoi4) và r5 (cuối 4 + P3). Chạy một lần.
set -e
cd /d/KhoaLuan/PPE_PROJECT
export YOLO_AUTOINSTALL=False PYTHONIOENCODING=utf-8
PY=.venv/Scripts/python.exe; F=outputs/results/round5/final; A=$F/pipeline_cuoi4.yaml; B=$F/pipeline_r5.yaml
$PY scripts/07_benchmark_pipeline.py --config cuoi4=$A --config r5=$B --out $F/benchmark > $F/benchmark.log 2>&1
$PY scripts/06b_evaluate_close_videos.py evaluate --videos video3 video4 video5 video6 --labels "data/videos/{v}_cvat.zip" --label-note "video3-6 nhãn người (chỉnh tham số)" --config cuoi4=$A --config r5=$B --out $F/dev36 > $F/dev36.log 2>&1
$PY scripts/06_evaluate_ablation.py --config $B --out $F/ablation_r5.json > $F/ablation.log 2>&1
EV_SET=event_eval_2 $PY scripts/06e_event_eval.py --config $A --out outputs/results/event_eval_2/cuoi4 > $F/ev2_cuoi4.log 2>&1
EV_SET=event_eval_2 $PY scripts/06e_event_eval.py --config $B --out outputs/results/event_eval_2/r5 > $F/ev2_r5.log 2>&1
$PY scripts/06b_evaluate_close_videos.py evaluate --videos holdout/h1 holdout/h2 holdout/h3 holdout/h4 holdout/h5 holdout/h7 holdout/h8 holdout/h9 --labels "data/videos/holdout/labels/{b}_machine_cvat.zip" --label-note "nhãn máy hai lượt, chưa người kiểm định; KHÔNG ĐỘC LẬP (đã xem nhiều lần)" --config cuoi4=$A --config r5=$B --out $F/holdout_check > $F/holdout_check.log 2>&1
$PY scripts/06f_holdout_events.py --run $F/holdout_check/r5 --out $F/holdout_events_r5.json > $F/holdout_events.log 2>&1
$PY scripts/06e_event_eval.py --config $B --out outputs/results/event_eval/r5 > $F/ev1_r5.log 2>&1
echo XONG > $F/done.txt
