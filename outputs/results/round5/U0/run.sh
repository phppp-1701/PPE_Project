#!/bin/bash
# U0: tách S3 thành zoom cách khung (Z) và phân loại cách khung (P); none = cuối 4 không S3. Chẩn đoán h2 (không chọn).
cd /d/KhoaLuan/PPE_PROJECT
export YOLO_AUTOINSTALL=False PYTHONIOENCODING=utf-8
PY=.venv/Scripts/python.exe; U=outputs/results/round5/U0
for n in none Z P S3; do
  $PY scripts/06d_diagnose_unknown.py --config $U/pipeline_$n.yaml --videos-machine holdout/h2 --labels-machine data/videos/holdout/labels/h2_machine_cvat.zip --out $U/diag_h2_$n > $U/diag_h2_$n.log 2>&1
done
$PY scripts/06b_evaluate_close_videos.py evaluate --videos video3 video4 video5 video6 --labels "data/videos/{v}_cvat.zip" --label-note "video3-6 nhãn người (chỉnh tham số)" --config S3=$U/pipeline_S3.yaml --config none=$U/pipeline_none.yaml --config Z=$U/pipeline_Z.yaml --config P=$U/pipeline_P.yaml --out $U/dev36 > $U/dev36.log 2>&1
echo XONG > $U/done.txt
