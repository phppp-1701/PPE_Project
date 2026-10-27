# data/raw/construction_ppe — Construction-PPE (data card)

Construction-PPE (Ultralytics, 2025) — bổ sung, chủ yếu găng tay; kiểm tra nhãn bằng mắt trước khi dùng. CHỈ ĐỌC, không sửa file trong thư mục này.

## Nguồn và giấy phép

| Mục | Giá trị |
|---|---|
| Link tải | https://github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip (lấy từ `construction-ppe.yaml` của Ultralytics) |
| Tài liệu | https://docs.ultralytics.com/datasets/detect/construction-ppe/ |
| Người tải | Claude, ngày 26/10/2026, tải trực tiếp bằng `curl` (không qua `yolo train`) |
| File zip | `construction-ppe.zip`, 178.415.813 byte (khớp kích thước chuẩn), 2.852 mục, kiểm tra zip không lỗi |
| SHA-256 | `bef8dcb599aa4e9d9f5e602cb6fa7143d3c84d7f6a0ff40463d7f2a4c2632ccc` |
| Giấy phép | AGPL-3.0 (file `LICENSE` đi kèm) |

## Cấu trúc

```
construction_ppe/
├── LICENSE
├── data.yaml        tên 11 lớp, đường dẫn train/val/test
├── images/
│   ├── train/   1.132 ảnh
│   ├── val/       143 ảnh
│   └── test/      141 ảnh
└── labels/
    ├── train/   1.142 nhãn YOLO txt (10 file thừa, xem dưới)
    ├── val/       143
    └── test/      141
```

## Kết quả kiểm tra (26/10/2026, chỉ đọc)

- 1.416 ảnh (1.259 .jpg, 157 .jpeg); cạnh dài 612-1.024 px, trung vị 640.
- Định dạng YOLO txt `class cx cy w h`; tên lớp lấy từ `data.yaml`.
- 0 ảnh thiếu nhãn, 0 file nhãn rỗng, 0 dòng sai định dạng.
- **10 nhãn thiếu ảnh** trong `labels/train`: `image940(1).txt`, `image941(1)`, `image944(1)`, `image945(1)`-`image950(1)`, `image95(1)`. Cả 10 giống hệt từng byte với file không có `(1)` tương ứng → bản sao thừa, bỏ qua khi chuyển đổi.
- Không có ảnh trùng tên hoặc trùng nội dung (md5) giữa train/val/test.
- Chia tập có sẵn: train 1.132 / val 143 / test 141 — khớp `data.yaml` và spec.

### Lớp và phân bố (số đối tượng; trong ngoặc: số ảnh chứa lớp)

| Mã gốc | Tên | train | val | test | Tổng |
|---|---|---|---|---|---|
| 0 | helmet | 1.341 (830) | 201 (107) | 192 (110) | 1.734 |
| 1 | gloves | 1.146 (562) | 136 (68) | 163 (75) | 1.445 |
| 2 | vest | 1.269 (828) | 171 (109) | 178 (111) | 1.618 |
| 3 | boots | 1.235 (530) | 151 (64) | 211 (75) | 1.597 |
| 4 | goggles | 419 (385) | 47 (44) | 52 (51) | 518 |
| 5 | none | 651 (347) | 81 (43) | 65 (35) | 797 |
| 6 | Person | 1.770 (1.067) | 239 (139) | 236 (133) | 2.245 |
| 7 | no_helmet | 400 (232) | 45 (27) | 40 (24) | 485 |
| 8 | no_goggle | 337 (216) | 41 (25) | 33 (24) | 411 |
| 9 | no_gloves | 442 (190) | 56 (23) | 58 (23) | 556 |
| 10 | no_boots | 88 (28) | 4 (2) | 23 (6) | 115 |

Tổng 11.521 đối tượng (train 9.098, val 1.172, test 1.251). Số liệu `train` chỉ tính 1.132 nhãn có ảnh, không tính 10 file nhãn thừa.

## Ánh xạ sang 4 lớp (docs/spec.md mục 2.1)

| Mã gốc | Tên gốc | → Lớp ppe4 |
|---|---|---|
| 6 | Person | 0 person |
| 0 | helmet | 1 helmet |
| 2 | vest | 2 vest |
| 1 | gloves | 3 gloves |
| 3, 4, 5, 7, 8, 9, 10 | boots, goggles, none, no_helmet, no_goggle, no_gloves, no_boots | bỏ |
