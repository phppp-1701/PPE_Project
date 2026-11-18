# Train C5 trên Kaggle (C5-s@960 và C5-s@1280)

Kế hoạch: `docs/experiments/2026-11-16_c5_detector_plan.md`, tiêu chí chọn bản đã khóa (mục "Tiêu chí chọn bản C5").
Hai lần train dùng **cùng dữ liệu, cùng tham số C4**, chỉ khác `imgsz`. Mỗi lần một notebook, một phiên GPU T4.

## 1. Tải gói lên Kaggle (một lần, dùng cho cả hai notebook)

1. kaggle.com → Datasets → New Dataset → tải `data/ppe6/variants/kaggle/c5_pack.zip` (khoảng 348 MB), đặt tên ví dụ
   `khoa-luan-ppe6-c5`.
2. New Dataset thứ hai → tải `data/ppe6/variants/kaggle/c5_extra_pack.zip` (khoảng 225 MB), tên ví dụ `khoa-luan-ppe6-c5-extra`.
3. Notebook mới → Add Input: dataset chính `phpp1701/khoa-luan-dataset`, `khoa-luan-ppe6-c5`, `khoa-luan-ppe6-c5-extra`.
   Bật GPU T4, bật Internet. **Không** Add Input gói C2, C4 cũ (ô đầu tự tìm `manifest.tsv`, `oversample.txt`, phải duy nhất).

## 2. Ô notebook

Cách chạy cả hai bản trong một phiên GPU T4 x2 (mỗi bản một GPU) ghi trong kế hoạch, mục "Trạng thái 17/11/2026".

Notebook 1 dùng `IMGSZ = 960`, notebook 2 dùng `IMGSZ = 1280`. Phần còn lại giống hệt.

```
IMGSZ = 960   # notebook 2: 1280
import glob, os
import json
# Dataset chính cũng có manifest.tsv cũ: chỉ nhận thư mục có ready.json ghi variant c5 (lỗi lần chạy 17/11 sáng)
PACK = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/ready.json", recursive=True) if json.load(open(p)).get("variant") == "c5"][0]
assert sum(1 for l in open(f"{PACK}/manifest.tsv") if l.startswith("train\t")) == 7169
EXTRA = os.path.dirname(sorted(glob.glob("/kaggle/input/**/c5_extra/oversample.txt", recursive=True))[0])
print("PACK =", PACK, "| EXTRA =", EXTRA)
!pip install -q ultralytics==8.4.189
!git clone -b exp/ppe6 https://github.com/phppp-1701/PPE_Project.git
%cd PPE_Project
# chỉ đổi imgsz (và cỡ ảnh thu nhỏ trước, đặt bằng imgsz như ghi chú trong configs/train.yaml)
!sed -i "s/^copy_max_side: 960/copy_max_side: {IMGSZ}/; s/^  imgsz: 960/  imgsz: {IMGSZ}/" configs/train.yaml
!grep -n "copy_max_side\|  imgsz" configs/train.yaml
!python -c "import ultralytics, torch; print(ultralytics.__version__, torch.cuda.get_device_name(0))"
!python -u scripts/04_train.py --ppe6 {PACK} --extra {EXTRA} --run-name yolo11s_ppe6_c5_s{IMGSZ} --out /kaggle/working/runs --data-copy /tmp/ppe_data
!python scripts/04f_check_run.py --run /kaggle/working/runs/yolo11s_ppe6_c5_s{IMGSZ}
!du -sh /kaggle/working/runs
```

Bấm **Save Version → Save & Run All (Commit)**. Hai notebook chạy được song song nếu tài khoản còn đủ hạn mức GPU (mỗi
lần tới 11 giờ, `time: 11` trong `configs/train.yaml`).

## 3. Kiểm tra log

- `grep` in ra `copy_max_side: <IMGSZ>` và `imgsz: <IMGSZ>`.
- `Bộ 6 lớp: {'train': 7169, 'val_monitor': 1070}` và dòng `Bộ phụ: ...` (khoảng 3.463 ảnh, 1.413 bản thêm).
- `Xong: /kaggle/working/runs/yolo11s_ppe6_c5_s<IMGSZ>`, `04f` báo đạt, `names` đủ 6 lớp.
- Bản 1280: thời gian mỗi epoch dài hơn khoảng 1,6 lần; `time: 11` có thể dừng trước 100 epoch (Ultralytics tự co lịch
  học theo giờ). Ghi lại số epoch và giờ thật.

## 4. Tải về và chấm trên máy

Tải thư mục `runs` của mỗi phiên, giải nén vào `outputs/train/yolo11s_ppe6_c5_s960/`, `..._s1280/`, rồi:

```
python scripts/04f_check_run.py --run outputs/train/yolo11s_ppe6_c5_s960 --save
python scripts/04d_capture_val.py --weights outputs/train/yolo11s_ppe6_c5_s960/weights/best.pt --data data/ppe6/c5/eval/val/data.yaml --out outputs/results/c5_eval/c5_s960_val
python scripts/04d_capture_val.py --weights outputs/train/yolo11s_ppe6_c5_s1280/weights/best.pt --data data/ppe6/c5/eval/val/data.yaml --out outputs/results/c5_eval/c5_s1280_val --imgsz 1280
python scripts/04j_c5_eval.py --split val --run c5_s960=outputs/results/c5_eval/c5_s960_val --run c5_s1280=outputs/results/c5_eval/c5_s1280_val --name c5_960_vs_1280
python scripts/04j_c5_eval.py --split val --run c4=outputs/results/c5_eval/c4_val --run c5_s960=outputs/results/c5_eval/c5_s960_val --name c4_vs_c5_s960
```

Rồi áp tiêu chí đã khóa (`configs/ppe6.yaml` mục `c5_decision`); bản 1280 còn phải đo `07_benchmark_pipeline.py`.
Test chỉ chạy một lần cho bản được chọn.

## Sự cố 17/11/2026 (lần chạy đầu)

Cell chọn `manifest.tsv` đầu tiên trong mọi Input; dataset chính `khoa-luan-dataset` có một `manifest.tsv` cũ đứng trước theo thứ tự chữ cái, nên ghép nhầm gói (`train 6852, val_monitor 1073` thay vì 7169 / 1070). Bộ phụ C5 tham chiếu ảnh chỉ có trong gói C5 (`chv__ppe_0140`) nên `add_extra` báo `FileNotFoundError` sau khoảng 1 giờ chép ảnh, trước epoch đầu. Không có kết quả train. Sửa: chọn gói theo `ready.json` (`variant: c5`) và kiểm 7169 ảnh train trước khi chạy.
