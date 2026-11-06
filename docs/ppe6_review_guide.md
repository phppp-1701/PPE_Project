# Hướng dẫn duyệt nhãn thử nghiệm 6 lớp

Dành cho người duyệt. Gói ở `data/ppe6/review/cvat_pack/` (không có trên git). Làm theo thứ tự P0a, P0b, P1, P2.

## Thử gói nhỏ trước

Gói `TRIAL` có 10 hộp lấy từ P0a, làm mất khoảng 2 phút (ước tính). Kết quả ghi riêng `trial_review.csv`, không tính là đã duyệt bộ dữ liệu.

1. Tạo task theo mục dưới với thư mục `cvat_pack/TRIAL`.
2. Mở job, kiểm tra thấy 10 hộp nhãn `boots_review` đúng vị trí trên ảnh, thuộc tính `decision` đang là `chua_duyet`.
3. Đặt `decision` cho vài hộp, để nguyên vài hộp, thêm một tag `image_checked`, vẽ một hộp `boots_new`.
4. Xuất file rồi chạy:

```
python scripts/03l_ppe6_import_review.py --group TRIAL --file <file_xuất.zip> --reviewer "Tên bạn"
```

Kết quả đúng: in đúng những hộp đã đặt, giá trị trước và sau, tên bạn; hộp để nguyên nằm ở số "hộp chưa duyệt". Nếu lỗi, gửi lại nội dung lỗi; đừng làm tiếp P0a.

## Tạo task

1. Trên CVAT, tạo task mới. Mục Labels chọn tab Raw, dán nội dung `labels.json` của nhóm.
2. Tải `images.zip` làm dữ liệu.
3. Actions → Upload annotations, định dạng **CVAT for images 1.1**, chọn `annotations.xml`.
4. Duyệt xong: Actions → Export task dataset, định dạng **CVAT for images 1.1**, bỏ tích Save images.

## Duyệt từng hộp

Xem cả ảnh, không chỉ trong hộp. Mỗi hộp đặt `decision`:

| Giá trị | Khi nào |
|---|---|
| `safety` | Đúng đồ bảo hộ theo định nghĩa dưới |
| `ordinary` | Đồ thường, hoặc không đang đeo, đang mang |
| `unclear` | Không phân biệt được; ảnh sẽ bị loại khỏi đánh giá lớp mới |
| `ignore` | Có đồ nhưng quá nhỏ, quá mờ; không tính đúng, không tính sai |
| `chua_duyet` | Mặc định. Hộp còn giá trị này coi như chưa ai xem |

`agent_label` là ý kiến của Claude, chỉ để tham khảo. Hộp lệch thì kéo lại cho đúng.

**Kính bảo hộ:** đang đeo trên mắt và có dấu hiệu của chính chiếc kính: tròng ôm mặt, tấm chắn bên, gọng kiểu kính an toàn, tròng vàng hoặc đỏ, kính kín kiểu goggle. Không xét người đó có đội mũ hay không.

**Ủng, giày bảo hộ:** nhìn rõ là ủng cao su, ủng công trình, giày cổ cao đế dày kiểu công trình. Giày thể thao, kể cả loại dày, giày da, dép là `ordinary`.

**Ca khó:**

- Kính tối không phân biệt được với kính râm: `unclear`.
- Gọng thường, tròng trong, không có tấm chắn: `unclear` nếu không chắc là kính cận.
- Kính đẩy lên đầu, treo áo, cầm tay: `ordinary`.
- Giày tối màu, không thấy cổ và đế: `unclear`.
- Hộp ở chân trần, ống quần, hoặc lệch hẳn khỏi vật: kéo lại nếu thấy vật, không thì `unclear`.

**`person_ok`**, dùng để chốt ngưỡng người đủ lớn. Chỉ xét theo mắt nhìn, không theo điểm mô hình:

| Giá trị | Khi nào |
|---|---|
| `du_lon` | Người đủ lớn để bạn phân biệt được đồ bảo hộ với đồ thường |
| `qua_nho` | Người quá nhỏ hoặc góc quá cao để phân biệt |
| `khong_ro` | Không chắc |

## Thêm hộp và gắn thẻ ảnh

- Thấy kính, ủng bảo hộ chưa có hộp: vẽ hộp nhãn `goggles_new` hoặc `boots_new`.
- Xem xong một ảnh: thêm tag `image_checked`. **Bắt buộc với mọi ảnh CHVG trong P0b**, kể cả ảnh không có hộp; thiếu tag thì ảnh chưa được dùng. Ảnh CHVG có thể sót kính, hãy xem kỹ.
- Ảnh không dùng được: tag `reject_image`.

## Mẫu CHV đo ủng thiếu nhãn (`P2_chv`)

99 ảnh không có hộp. Với mỗi ảnh: chỉ vẽ `boots_new` khi nhìn rõ là ủng hoặc giày bảo hộ; người ở xa không nhìn rõ thì không vẽ. Xem xong thêm tag `image_checked`. Kết quả chỉ để đo, không đổi nhãn train.

## Duyệt cảnh (làm cùng P0a)

Mở `scene_review/scene_NN.jpg`. Mỗi hàng là một cảnh: bên trái vạch đỏ là ảnh đánh giá, bên phải là 3 ảnh train gần nhất.
Điền `scene_review/scene_review.csv`, cột `same_as_train` = `yes` nếu cùng buổi chụp, cùng người hoặc cùng chỗ. Cảnh `yes` bị loại khỏi đánh giá.
`repeat_scene_check.jpg`: mỗi hàng là một cụm lớn, thứ tự `s00000` đến `s00007`. Claude coi `s00001`, `s00005`, `s00007` là cảnh lặp thật, còn lại là cụm nối nhầm. Nếu sai, báo để sửa `repeat_scenes` trong `configs/ppe6.yaml`.

## Nhập kết quả

Chạy từ gốc project, thay tên và đường dẫn:

```
python scripts/03l_ppe6_import_review.py --group P0a --file <file_xuất.zip> --reviewer "Tên bạn"
python scripts/03l_ppe6_import_review.py --scenes <scene_review.csv> --reviewer "Tên bạn"
python scripts/03l_ppe6_import_review.py --report
python scripts/03i_ppe6_build_dataset.py
```

Sau khi nhập hết, theo thứ tự:

```
python scripts/03n_ppe6_readiness.py gates
python scripts/03n_ppe6_readiness.py scope --write
python scripts/03n_ppe6_readiness.py monitor --variant c2
python scripts/03n_ppe6_readiness.py monitor --variant c1
python scripts/03n_ppe6_readiness.py checklist
```

`gates` chỉ ra quy tắc nào kích hoạt. Nếu mọi mục `pass`, đặt `final.data_locked: true` trong `configs/ppe6.yaml`.

`--report` in tỉ lệ khác nhau giữa bạn và Claude theo lớp, nguồn, và đề xuất ngưỡng người đủ lớn. `03i` đưa ảnh đã chốt vào `val_new.txt`, `test_new.txt`.
