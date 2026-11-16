# data/raw/hard_hat_cc0 — Hard Hat Detection (CC0) (thẻ dữ liệu của project)

`README.md` trong thư mục này là thẻ gốc của Hugging Face (tải kèm), không phải của project. CHỈ ĐỌC, không sửa file.

## Nguồn và giấy phép

| Mục | Giá trị |
|---|---|
| Trang | https://huggingface.co/datasets/Voxel51/hard-hat-detection |
| Revision tải | `d11e7d6b69ba1a22422db3230c0415d39a699d7c` (cố định, tái lập được) |
| Gốc | Kaggle `andrewmvd/hard-hat-detection`; trích dẫn "Hard Hat Dataset", Make ML (https://makeml.app/datasets/hard-hat-workers) |
| Giấy phép | `cc0-1.0` (thẻ license trên Hugging Face) |
| Người tải | Claude, 16/11/2026, theo yêu cầu người dùng (kế hoạch `docs/experiments/2026-11-16_post_holdout_fixes.md` mục 3) |
| Cách tải | HTTPS (urllib), 8 luồng; bỏ `.gitattributes`, `dataset_preview.gif` |
| Kiểm tra | 5.004 file, 0 lỗi; `sha256.txt` ghi sha256 từng file (sha256 của chính `sha256.txt`: `1a21197a8a8f5d65ab3a17c7ecb39f53c9c0e0912178cb3c3006cc984104a4e3`); `samples.json`: `da9777e7dfede3906cd51a81b6520bc284e05335c39d5e2e82f7223f3be624e3` |

## Cấu trúc và nhãn

- `data/hard_hat_workers<n>.png`: 5.000 ảnh, khoảng 416 × 416 px.
- `samples.json` (định dạng FiftyOne): mỗi ảnh có `ground_truth.detections`, `label` ∈ {helmet, head, person},
  `bounding_box` = [x, y, w, h] chuẩn hóa, gốc trên trái. Số hộp: helmet 18.966, head 5.785, person 751.
- Không có nhãn màu mũ hay hướng nhìn.

## Cách dùng trong project

Chỉ dùng cho **train** bộ phân loại vùng đầu bản 5 (`03y`, `parts.version: 5`): helmet → `helmet`; head không chứa hộp mũ
(IoA ≤ 0,3) → `no_helmet`. Ảnh trùng ảnh đánh giá (pHash 64 bit, Hamming ≤ `parts.v5.dedup_hamming`; ppe4 val/test,
Pictor, ppe6 test_new) bị bỏ. Không dùng cho detector, val, test hay đánh giá.
