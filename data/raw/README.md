# data/raw — Dữ liệu gốc (CHỈ ĐỌC, KHÔNG SỬA)

Mỗi bộ dữ liệu giải nén vào thư mục con của nó. Không sửa file ở đây; mọi bước chuyển đổi ghi kết quả sang `data/ppe4/`.

`construction_ppe_v2/`: Construction-PPE bản mới của Ultralytics (10/11/2026, CC BY 4.0, có ảnh sinh), tải để bổ sung ủng, kính cho bản 6 lớp; xem README trong thư mục.

`hard_hat_cc0/`: Hard Hat Detection (Hugging Face Voxel51, gốc Kaggle andrewmvd / MakeML, CC0, 5.000 ảnh 416 px; helmet, head, person), tải 16/11/2026 chỉ để thêm ảnh đầu cho bộ phân loại mũ bản 5 (train); thẻ dữ liệu ở `DATA_CARD.md`.

`shwd/`: Safety Helmet Wearing Dataset (GitHub njvisionpower, MIT; một phần ảnh từ SCUT-HEAD), 7.581 ảnh VOC (hat, person), người dùng tải 16/11/2026, chỉ để thêm ảnh đầu cho bộ phân loại mũ bản 5 (train); thẻ dữ liệu ở `DATA_CARD.md`.

`safety_shoe_vf/`: Safety_shoe / no_safety_shoe (Roboflow Universe, Vertical Farming, Public Domain, 1.310 ảnh; safety-shoe, no_safety-shoe), người dùng tải 17/11/2026 để thêm ủng cho C6 (chỉ train); xem README trong thư mục.

`safety_shoes_nc/`: Safety Shoes Detection (Roboflow Universe, Nedrick Chandra, CC BY 4.0, 1.693 ảnh; chủ yếu safety_shoe), người dùng tải 17/11/2026 để thêm ủng cho C6 (chỉ train); xem README trong thư mục.

`gloves_bare_tm/`: Gloves and bare hands detection (Roboflow Universe, Tejan Mehndiratta, CC BY 4.0, 868 ảnh; tên lớp không khớp nội dung), người dùng tải 17/11/2026, chưa quyết định dùng; xem README trong thư mục.

`safety_gloves_ru/`: Safety Gloves (Roboflow Universe Projects, CC BY 4.0, 3.373 ảnh CCTV nhà xưởng; Gloves, NO-Gloves), người dùng tải 19/11/2026 để thêm găng cho C8 (chỉ train); xem README trong thư mục.
