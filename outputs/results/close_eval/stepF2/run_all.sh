set -e
D=outputs/results/close_eval/stepF2
PY=.venv/Scripts/python
export YOLO_AUTOINSTALL=False
$PY scripts/05h_close_range_probe.py --ids 3-6 --no-video --config $D/pipeline_base.yaml --out $D/flicker_base
$PY scripts/05h_close_range_probe.py --ids 3-6 --no-video --config $D/pipeline_F2.yaml --out $D/flicker_F2
$PY scripts/06b_evaluate_close_videos.py evaluate --videos video3 video4 video5 video6 --labels "data/videos/{v}_cvat.zip" --label-note "nhãn người (video chỉnh tham số)" --config base=$D/pipeline_base.yaml --config F2=$D/pipeline_F2.yaml --out $D/dev36
$PY scripts/06_evaluate_ablation.py --config $D/pipeline_base.yaml --out $D/ablation_base.json
$PY scripts/06_evaluate_ablation.py --config $D/pipeline_F2.yaml --out $D/ablation_F2.json
echo ALL_DONE
