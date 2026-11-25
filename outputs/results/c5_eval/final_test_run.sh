# Tập test, chạy MỘT LẦN (người dùng cho phép 26/11/2026), commit đóng băng 28ad782. Detector c6_ft.
set -e
export YOLO_AUTOINSTALL=False
PY=.venv/Scripts/python
W=outputs/train/yolo11s_ppe6_c6_ft/weights/best.pt
O=outputs/results/c5_eval
$PY scripts/04d_capture_val.py --weights $W --data data/ppe6/c5/eval/test/data.yaml --split test --out $O/final_c6_ft_test
$PY scripts/04m_crop_pass.py --split test --capture $O/final_c6_ft_test --weights $W --out $O/final_c6_ft_crop_test
$PY scripts/04j_c5_eval.py --split test --run c6_ft=$O/final_c6_ft_test --run c6_ft_zoom=$O/final_c6_ft_crop_test --name final_test_c6_ft
$PY scripts/04o_eval_by_source.py --split test --run c6_ft=$O/final_c6_ft_test --run c6_ft_zoom=$O/final_c6_ft_crop_test --name final_test_by_source
echo ALL_DONE
