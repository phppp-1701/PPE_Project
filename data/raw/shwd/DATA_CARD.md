# data/raw/shwd — Safety Helmet Wearing Dataset (SHWD) (thẻ dữ liệu của project)

CHỈ ĐỌC, không sửa file trong thư mục này.

## Nguồn và giấy phép

| Mục | Giá trị |
|---|---|
| Trang | https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset |
| File tải | `VOC2028.zip` (Google Drive của repo), người dùng tải 16/11/2026; 1.117.970.537 byte |
| SHA-256 zip | `2f6c5c347b778271bc8b27c2d61b731fc5fb8cdb4f45fce583dd2f82e6a46401` |
| Giải nén | Claude, 16/11/2026: kiểm zip không lỗi, không có đường dẫn ra ngoài; chỉ lấy `.xml`, `.jpg`, `.txt` (15.156 file) |
| Giấy phép | Repo ghi **MIT License** (file LICENSE, "Copyright (c) 2019 njvisionpower"). README: ảnh có mũ lấy từ Google / Baidu và gán tay bằng LabelImg; một phần ảnh không mũ lấy từ SCUT-HEAD (https://github.com/HCIILAB/SCUT-HEAD-Dataset-Release), bộ này có điều khoản riêng. Bản quyền ảnh gốc không được repo nói rõ: chỉ dùng cho nghiên cứu (khóa luận), không phát hành lại ảnh |

## Cấu trúc và nhãn

`VOC2028/JPEGImages` 7.581 ảnh, `VOC2028/Annotations` 7.581 file Pascal VOC, `VOC2028/ImageSets/Main` (train, val,
trainval, test của tác giả; project không dùng cách chia này). Lớp: `hat` 9.044 (có mũ), `person` 111.514 (đầu không mũ;
nhiều đầu rất nhỏ: 67.996 hộp rộng dưới 24 px bị bỏ khi cắt), `dog` 3 (bỏ).

## Cách dùng trong project

Chỉ dùng cho **train** bộ phân loại vùng đầu bản 5 (`03y`, `parts.version: 5`): `hat` → `helmet`, `person` không chứa
hộp mũ → `no_helmet`. Ảnh trùng ảnh đánh giá (pHash) bị bỏ. Không dùng cho detector, val, test hay đánh giá.
