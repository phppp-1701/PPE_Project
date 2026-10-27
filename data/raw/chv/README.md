# data/raw/chv — CHV (data card)

CHV (Wang và cộng sự, 2021) — bổ sung mũ bảo hộ, áo phản quang. Chưa có nhãn găng tay: nhóm gán bổ sung bằng CVAT. CHỈ ĐỌC, không sửa file trong thư mục này.

## Nguồn và giấy phép

| Mục | Giá trị |
|---|---|
| Link tải | https://drive.google.com/file/d/1fdGn67W0B7ShpBDbbQpUF0ScPQa4DR0a/view?usp=sharing (`CHV_dataset.zip`) |
| GitHub tác giả | https://github.com/ZijianWang-ZW/PPE_detection |
| Người tải | Nhóm tải `CHV_dataset.zip` ngày 26/10/2026; Claude giải nén vào đây cùng ngày |
| File zip | 439.733.771 byte, 5.333 mục, kiểm tra zip không lỗi |
| SHA-256 | `e2a2ebef7b9a69fd2d7f5152eb808b14a3a0a76de015c802f3f187c437a8e577` |
| Giấy phép | Trang gốc không ghi giấy phép ("The dataset is open for free use"), chỉ yêu cầu trích dẫn bài báo: Wang và cộng sự, *Fast Personal Protective Equipment Detection for Real Construction Sites Using Deep Learning Approaches*, Sensors, 2021 |

Khi giải nén: bỏ thư mục gốc `CHV_dataset/` và bỏ `__MACOSX/` (file phụ của macOS, không phải dữ liệu). File `.DS_Store` nằm trong `CHV_dataset/` của zip nên được giữ nguyên.

## Cấu trúc

```
chv/
├── .DS_Store            file hệ thống macOS có sẵn trong zip, bỏ qua
├── images/              1.330 ảnh .jpg (ppe_0000.jpg ...)
├── annotations/         1.330 nhãn YOLO txt + README.md (tên lớp, định dạng)
└── data split/
    ├── train.txt        1.064 dòng
    ├── valid.txt          133 dòng
    └── test.txt           133 dòng
```

Các file chia tập ghi đường dẫn dạng `CHV_dataset/images/ppe_xxxx.jpg` (theo cấu trúc zip gốc); khi dùng chỉ lấy tên file.

## Kết quả kiểm tra (26/10/2026, chỉ đọc)

- 1.330 ảnh, 1.330 nhãn; 0 ảnh thiếu nhãn, 0 nhãn thiếu ảnh, 0 file nhãn rỗng, 0 dòng sai định dạng; không có ảnh trùng nội dung (md5).
- Định dạng YOLO txt `class cx cy w h`; tên lớp lấy từ `annotations/README.md`.
- Ảnh cạnh dài 160-6.750 px, trung vị 970.
- Chia tập có sẵn: train 1.064 / valid 133 / test 133; không trùng nhau, hợp lại đủ 1.330.
- Trang GitHub không nêu tên các bộ dữ liệu nguồn (chỉ ghi "from the Internet and open datasets"); spec ghi CHV lấy lại ảnh từ GDUT-HWD và SHWD → cần kiểm tra trùng lặp ở `02_check_data.py`.

### Lớp và phân bố (số đối tượng; trong ngoặc: số ảnh chứa lớp)

| Mã gốc | Tên | train | valid | test | Tổng |
|---|---|---|---|---|---|
| 0 | person | 3.050 (1.059) | 387 (133) | 450 (131) | 3.887 (1.323) |
| 1 | vest | 1.396 (559) | 171 (61) | 217 (76) | 1.784 (696) |
| 2 | blue helmet | 415 (221) | 49 (25) | 44 (29) | 508 (275) |
| 3 | red helmet | 438 (212) | 48 (29) | 50 (28) | 536 (269) |
| 4 | white helmet | 920 (425) | 99 (53) | 176 (58) | 1.195 (536) |
| 5 | yellow helmet | 989 (514) | 163 (70) | 147 (71) | 1.299 (655) |

Tổng 9.209 đối tượng. Không có lớp găng tay.

## Ánh xạ sang 4 lớp (docs/spec.md mục 2.1)

| Mã gốc | Tên gốc | → Lớp ppe4 | Ghi chú |
|---|---|---|---|
| 0 | person | 0 person | |
| 2, 3, 4, 5 | blue/red/white/yellow helmet | 1 helmet | giữ nguyên hộp |
| 1 | vest | 2 vest | |
| — | (không có) | 3 gloves | gán bổ sung bằng CVAT; ảnh gán không đủ rõ thì loại |
