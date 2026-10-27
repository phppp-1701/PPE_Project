# data/raw/sh17 — SH17 (data card)

SH17 (Ahmad & Rahimi, 2024) — **nguồn chính**. CHỈ ĐỌC, không sửa file trong thư mục này.

## Nguồn và giấy phép

| Mục | Giá trị |
|---|---|
| Link tải | https://www.kaggle.com/datasets/mugheesahmad/sh17-dataset-for-ppe-detection |
| Người tải | Nhóm tải `archive.zip` (13,4 GB) từ Kaggle ngày 21/10/2026, giải nén ở `Downloads\archive`; Claude chép nguyên vẹn vào đây ngày 26/10/2026 (robocopy: 32.398 file, 13,26 GB, 0 lỗi) |
| Giấy phép | CC BY-NC-SA 4.0 — chỉ dùng cho giáo dục và nghiên cứu, **không phân phối lại** |
| Nguồn ảnh | Pexels (link gốc từng ảnh trong `meta-data/*.json`) |

## Cấu trúc

```
sh17/
├── images/         8.099 ảnh (8.077 .jpeg, 4 .jpg, 18 .png)
├── labels/         8.099 nhãn YOLO txt
├── voc_labels/     8.099 nhãn Pascal VOC xml (cùng hộp với labels/, có tên lớp)
├── meta-data/      8.099 json (link Pexels, tác giả, kích thước ảnh gốc trên Pexels)
├── train_files.txt 6.479 tên ảnh
└── val_files.txt   1.620 tên ảnh
```

## Kết quả kiểm tra (26/10/2026, chỉ đọc)

- 8.099 ảnh, 8.099 nhãn; 0 ảnh thiếu nhãn, 0 nhãn thiếu ảnh, 0 file nhãn rỗng, 0 dòng sai định dạng (đủ 5 cột, tọa độ trong [0,1], w/h > 0).
- Định dạng: YOLO txt `class cx cy w h` (chuẩn hóa) và VOC xml song song.
- Bộ không kèm yaml/classes.txt. **Tên lớp lấy bằng cách ghép từng hộp YOLO với hộp VOC** (VOC có tên lớp): 75.993/75.994 hộp khớp, mỗi mã ứng đúng một tên. Hộp còn lại (`pexels-photo-258626.txt` dòng 111, person, sát mép dưới) lệch nhẹ so với VOC; số person ở hai định dạng bằng nhau.
- Kích thước ảnh trong VOC khớp kích thước ảnh thật ở cả 8.099 ảnh; không ảnh nào có cờ xoay EXIF. `meta-data` ghi kích thước bản gốc trên Pexels, có ảnh khác ảnh thật (3/203 ảnh lấy mẫu), không dùng để quy đổi nhãn.
- Ảnh rất lớn (theo `meta-data`): cạnh dài nhỏ nhất 1.920, trung vị 5.940, lớn nhất 14.640 px; 8.010 ảnh có cạnh dài ≥ 3.000 px.
- Chia tập có sẵn: `train_files.txt` 6.479, `val_files.txt` 1.620; không trùng nhau, hợp lại đủ 8.099. Không có tập test.

### Lớp và phân bố

| Mã gốc | Tên | Số đối tượng | Số ảnh chứa | train (đối tượng) | val (đối tượng) |
|---|---|---|---|---|---|
| 0 | person | 13.802 | 7.617 | 11.068 | 2.734 |
| 1 | ear | 7.730 | 4.884 | | |
| 2 | ear-mufs | 318 | 223 | | |
| 3 | face | 8.950 | 5.646 | | |
| 4 | face-guard | 134 | 127 | | |
| 5 | face-mask-medical | 670 | 395 | | |
| 6 | foot | 759 | 347 | | |
| 7 | tools | 4.647 | 2.257 | | |
| 8 | glasses | 1.945 | 1.588 | | |
| 9 | gloves | 2.790 | 1.321 | 2.261 | 529 |
| 10 | helmet | 927 | 466 | 773 | 154 |
| 11 | hands | 15.850 | 6.455 | | |
| 12 | head | 11.985 | 6.495 | | |
| 13 | medical-suit | 157 | 114 | | |
| 14 | shoes | 4.560 | 1.570 | | |
| 15 | safety-suit | 240 | 141 | | |
| 16 | safety-vest | 530 | 213 | 433 | 97 |

Tổng 75.994 đối tượng. Cột train/val chỉ tính cho các lớp được giữ.

## Ánh xạ sang 4 lớp (docs/spec.md mục 2.1)

| Mã gốc | Tên gốc | → Lớp ppe4 | Ghi chú |
|---|---|---|---|
| 0 | person | 0 person | |
| 10 | helmet | 1 helmet | chỉ giữ khi đúng là mũ bảo hộ |
| 16 | safety-vest | 2 vest | |
| 9 | gloves | 3 gloves | chỉ giữ khi đúng là găng bảo hộ |
| 1-8, 11-15 | còn lại (gồm `shoes`, `safety-suit`, `medical-suit`) | bỏ | |
