# Chạy thử bộ 6 lớp trên Kaggle

Mục đích: xác nhận `--ppe6` chạy được trên Kaggle, lưu và tải được `best.pt`. Không phải train thật; số từ lần chạy này không dùng. Chỉ chạy khi r3 không còn dùng GPU Kaggle.

Ước tính thời gian dưới 30 phút, phần lớn để cài đặt và mở dataset; chưa đo trên Kaggle.

## 1. Tải gói lên Kaggle

1. Vào kaggle.com → Datasets → New Dataset.
2. Tải file `data/ppe6/variants/kaggle/c2_final_pack.zip` (239 MB), đặt tên tùy ý, ví dụ `khoa-luan-ppe6-c2-final`. Kaggle tự giải nén. Chỉ Add Input **một** gói final_pack mỗi notebook, vì ô đầu tự tìm `manifest.tsv`.
3. Mở notebook mới, Add Input: dataset chính `phpp1701/khoa-luan-dataset` và dataset vừa tạo. Bật GPU T4, bật Internet.
4. Trong cột Input, xem đường dẫn thật của hai dataset. Lần r3, đường dẫn có dạng `/kaggle/input/datasets/phpp1701/<tên>`.

## 2. Ô notebook

Thay `PACK` nếu đường dẫn thật khác:

```
# Tự tìm thư mục gói có manifest.tsv (gói final_pack), không phải gõ đường dẫn
import glob, os
PACK = os.path.dirname(sorted(glob.glob("/kaggle/input/**/manifest.tsv", recursive=True))[0])
print("PACK =", PACK)
!pip install -q ultralytics==8.4.189
!git clone -b exp/ppe6 https://github.com/phppp-1701/PPE_Project.git
%cd PPE_Project
!python -c "import ultralytics, torch; print(ultralytics.__version__, torch.cuda.get_device_name(0))"
!python -u scripts/04_train.py --ppe6 {PACK} --smoke 64 --run-name yolo11s_ppe6_c2 --out /kaggle/working/runs --data-copy /tmp/ppe_data
!python scripts/04f_check_run.py --run /kaggle/working/runs/yolo11s_ppe6_c2_smoke
!du -sh /kaggle/working/runs
```

Bấm **Save Version → Save & Run All (Commit)**.

## 3. Kết quả đúng

Trong log phải có:

- `Bộ 6 lớp: {'train': 64, 'val_monitor': 64}`.
- `Xong: /kaggle/working/runs/yolo11s_ppe6_c2_smoke`.
- `Đạt, đã ghi .../smoke_check.json`, với `best_mb` khoảng 19 (r2 là 19,2 MB) và `names` đủ 6 lớp.

Lỗi thường gặp:

- `Tìm thấy 0 manifest.tsv`: sai đường dẫn `PACK`, xem lại cột Input.
- `Tìm thấy 2 data.yaml`: thêm `--data <đường dẫn data.yaml của dataset chính>` vào lệnh train.

## 4. Tải về và kiểm tra trên máy

Vào phiên bản vừa chạy → Output → tải thư mục `runs`, giải nén vào `outputs/train/kaggle_smoke/`, rồi chạy:

```
python scripts/04f_check_run.py --run outputs/train/kaggle_smoke --save
```

So `sha256`, `best_mb` với log Kaggle: phải giống nhau. Lệnh ghi `data/ppe6/variants/kaggle_smoke.json`, checklist sẽ đánh dấu đã chạy thử.
