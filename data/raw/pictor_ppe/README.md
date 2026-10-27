# data/raw/pictor_ppe — Pictor-PPE (data card)

Pictor-PPE / Pictor-v3 (Nath và cộng sự, 2020) — **CHỈ dùng để kiểm thử ngoài**, không dùng để huấn luyện hay chọn ngưỡng. CHỈ ĐỌC, không sửa file trong thư mục này.

## Nguồn và giấy phép

| Mục | Giá trị |
|---|---|
| Link tải | https://drive.google.com/drive/folders/1akhyTNVrkqMMcIFUQCEbW5ehfmG0CdYH?usp=sharing |
| GitHub | https://github.com/ciber-lab/pictor-ppe |
| Người tải | Nhóm tải thư mục Drive thành `pictor-ppe-20261026T140852Z-1-001.zip` ngày 26/10/2026; Claude giải nén vào đây cùng ngày |
| File zip | 1.846.749.109 byte, 799 mục, kiểm tra zip không lỗi |
| SHA-256 | `dd45563b2312864fb7743d78360591ff1eeea622e4baf010326993ea05c09a00` |
| Giấy phép | Trang gốc không ghi giấy phép, chỉ yêu cầu trích dẫn bài báo: Nath, Behzadan, Paal, *Deep learning for site safety: Real-time detection of personal protective equipment*, Automation in Construction, 2020 |

Khi giải nén: chỉ lấy `Images/` và `Labels/`, bỏ thư mục gốc `pictor-ppe/`. **Không giải nén `Models/`** (6 file trọng số `.h5` của tác giả, không phải dữ liệu); file zip gốc vẫn có nếu cần.

## Cấu trúc

```
pictor_ppe/
├── Images/   784 ảnh .jpg (774 ảnh + 10 bản sao "(1)")
└── Labels/   9 file: pictor_ppe_crowdsourced_approach-{01,02,03}_{train,valid,test}.txt
```

## Định dạng nhãn

Không phải YOLO txt. Mỗi file là một danh sách, mỗi dòng một ảnh:

```
<tên ảnh>\t<x1>,<y1>,<x2>,<y2>,<lớp>\t<x1>,<y1>,<x2>,<y2>,<lớp>...
```

Tọa độ là pixel tuyệt đối (góc trên trái, góc dưới phải). Ba "approach" dùng chung ảnh và chung cách chia tập, khác nhau ở lớp:

- **approach-01**: worker, hat, vest là ba đối tượng riêng (dùng cho đề tài).
- **approach-02**: chỉ hộp worker, lớp là trạng thái của worker.
- **approach-03**: chỉ hộp worker, mọi hộp đều lớp 0.

README của tác giả không ghi mã số lớp (mục định dạng nhãn còn "@TODO"). **Mã lớp của approach-01 được suy ra từ chính file nhãn:**

| Mã | Tên | Căn cứ |
|---|---|---|
| 2 | worker | 2.497/2.497 hộp trùng khít với hộp worker của approach-03 |
| 0 | hat | 1.635/1.646 hộp có tâm nằm trong hộp worker; vị trí dọc trung vị r_y = 0,077 (đỉnh người) |
| 1 | vest | 41/42 hộp có tâm nằm trong hộp worker; r_y trung vị = 0,361 (thân người) |

approach-02 có 4 mã: 0 (873), 1 (1.583), 2 (1), 3 (40) hộp. Số hộp khớp với thứ tự W, WH, WV, WHV mà README mô tả (WH + WHV = 1.623 so với 1.646 hat; WV + WHV = 41 so với 42 vest), nhưng thứ tự này **chưa có tài liệu xác nhận**; đề tài không dùng approach-02.

## Kết quả kiểm tra (26/10/2026, chỉ đọc)

- 784 ảnh; 774 ảnh có nhãn, khớp "774 crowd-sourced images" trong README. Phần web-mined (698 ảnh) không có trong thư mục công khai này.
- 10 ảnh không có trong file nhãn nào: `image_from_china(4224) (1).jpg`, `(4232) (1)`, `(4234) (1)`, `(4235) (1)`, `(4238) (1)`, `(4239) (1)`, `(424) (1)`, `(4241) (1)`, `(4250) (1)`, `(4252) (1)` — cả 10 giống hệt từng byte với ảnh không có `(1)` → bản sao, bỏ qua.
- 0 dòng sai định dạng, 0 ảnh trong nhãn mà thiếu file ảnh, 0 ảnh có danh sách hộp rỗng.
- Ảnh cạnh dài 640-1.617 px, trung vị 1.216.
- Chia tập có sẵn (giống nhau ở cả 3 approach): train 502 / valid 120 / test 152 ảnh; không trùng nhau. Đề tài dùng toàn bộ 774 ảnh để kiểm thử ngoài (sau khi loại ảnh trùng với dữ liệu huấn luyện, spec mục 2.3).

### Phân bố lớp approach-01 (số hộp)

| Mã | Tên | train | valid | test | Tổng |
|---|---|---|---|---|---|
| 2 | worker | 1.646 | 417 | 434 | 2.497 |
| 0 | hat | 1.085 | 276 | 285 | 1.646 |
| 1 | vest | 21 | 14 | 7 | 42 |

## Ánh xạ sang 4 lớp (docs/spec.md mục 2.1)

| Mã gốc (approach-01) | Tên gốc | → Lớp ppe4 |
|---|---|---|
| 2 | worker | 0 person |
| 0 | hat | 1 helmet |
| 1 | vest | 2 vest |
| — | (không có) | 3 gloves — không đánh giá găng trên Pictor-PPE |
