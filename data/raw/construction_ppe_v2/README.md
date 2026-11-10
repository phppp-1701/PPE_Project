# data/raw/construction_ppe_v2 — Ultralytics Construction-PPE, bản mới (data card)

Bản phát hành mới của Construction-PPE (Ultralytics), khác hẳn bản cũ ở `data/raw/construction_ppe/`. CHỈ ĐỌC, không sửa file trong thư mục này.

## Nguồn và giấy phép

| Mục | Giá trị |
|---|---|
| Link tải | https://github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip (cùng link với bản cũ; Ultralytics đã thay nội dung) |
| Tải | Claude tải ngày 10/11/2026 theo yêu cầu người dùng; zip 647.666.037 byte, sha256 `e5817aa9c73f33e525d76ca6bc6af4e4eac9dcea9bcfef1cfd1a71c09fbc1232` |
| Giấy phép | **CC BY 4.0** (`LICENSE.txt`). Bản cũ là AGPL-3.0. Ghi nguồn: "Ultralytics Construction-PPE Dataset, Ultralytics team, November 2026, CC BY 4.0" |
| Mô tả gốc | `README_ultralytics.md` (đổi tên từ README.md của bộ) |
| **Ảnh sinh** | README gốc: "combines human-collected and **generated** images", nhãn do người và máy, đã duyệt lại. `manifest.jsonl` không ghi ảnh nào là ảnh sinh |

## Cấu trúc

```
construction_ppe_v2/
├── images/train   800 ảnh      labels/train   YOLO txt
├── images/val     200 ảnh      labels/val
├── data.yaml      12 lớp: 0 helmet, 1 gloves, 2 vest, 3 boots, 4 goggles, 5 Person,
│                  6 no_helmet, 7 no_goggle, 8 no_gloves, 9 no_boots, 10 forklift, 11 no_vest
├── manifest.jsonl tên file, phần chia, sha256, số hộp
└── LICENSE.txt, README_ultralytics.md
```

## Kiểm tra (10/11/2026)

- 1.000 ảnh, 1.000 file nhãn. Không ảnh nào trùng dHash chính xác với bản cũ (1.403 ảnh).
- Số ảnh chứa / số hộp: boots 731 / 2.484, goggles 539 / 751, Person 991 / 2.443, helmet 759 / 1.576, vest 801 / 1.816, gloves 682 / 1.929.
- Xem 24 hộp boots ngẫu nhiên: phần lớn là bốt da, ủng công trình nhìn rõ (gần định nghĩa bản 3); vài hộp người ở xa rất nhỏ.

## Chưa làm

Chưa dùng ở đâu. Trước khi đưa vào train: kiểm tra trùng cảnh gần đúng với `val_new`, `test_new`; chấm lại ủng, kính theo định nghĩa bản 3, bản 2; quyết định có dùng ảnh sinh không. Không dùng cho val, test (có ảnh sinh).
