# Hướng dẫn duyệt nhãn thử nghiệm 6 lớp

**Từ 07/11/2026 quy trình là máy gán nhãn, người kiểm định.** Bạn không duyệt toàn bộ `task_a`, `task_b`, `task_c`, `task_d` nữa mà làm mục "Kiểm định gói audit" ngay dưới đây. Định nghĩa nhãn và ca khó ở các mục sau vẫn áp dụng.

## Kiểm định gói audit

Gói ở `data/ppe6/review/cvat_pack_audit/`, không cần CVAT, không cần token. **Không mở `_private`.** Công cụ không hiện nhãn máy; tự nhìn ảnh rồi chọn, không rõ thì chọn `3`.

```
python scripts/03q_ppe6_fast_review.py --task audit --reviewer "Tên bạn"
```

Mở http://127.0.0.1:8765, dùng phím như mục "Công cụ duyệt nhanh". Phím `C` và `M` không dùng ở gói này. Xong, tắt bằng Ctrl + C rồi:

```
python scripts/03q_ppe6_fast_review.py --task audit_img2 --reviewer "Tên bạn"
```

Mỗi ảnh chỉ hỏi một lớp, ghi ở đầu khung phải (kính hoặc ủng, giày). Khung trắng là hộp đã có. Thấy đồ bảo hộ **của lớp được hỏi**, nhìn rõ, mà chưa có khung trắng thì bấm `M` rồi `V`; không có thì bấm `V`; ảnh hỏng (người đủ lớn mà ảnh quá mờ, tối, lỗi) thì bấm `R`. Đồ thường, người ở xa, không chắc: `V`.

Gói `audit_img` bản đầu (07/11/2026) thiếu khung có sẵn và không ghi lớp được hỏi, nên câu hỏi với người khác câu hỏi hai lượt máy đã thấy. Phiên đã chấm giữ nguyên trên đĩa, không nhập, không dùng để kết luận; `audit-import` chỉ đọc `audit_img2`. Cuối cùng:

```
python scripts/03t_ppe6_machine_label.py audit-import --reviewer "Tên bạn"
python scripts/03t_ppe6_machine_label.py audit-report
```

Kết quả ghi `audit_review.csv`, trạng thái `human_audited`, không ghi `human_review.csv`.

**Gói `rest` (kiểm định không đạt, 07/11/2026):** mọi hộp val, test người chưa xem trong `audit` (335 hộp, 242 ảnh). Chấm giống gói `audit`:

```
python scripts/03q_ppe6_fast_review.py --task rest --reviewer "Tên bạn"
python scripts/03t_ppe6_machine_label.py rest-import --reviewer "Tên bạn"
python scripts/03t_ppe6_machine_label.py eval-count
```

Kết quả ghi `rest_review.csv`, trạng thái `human_reviewed`.

Dành cho người duyệt. Dùng gói mù ở `data/ppe6/review/cvat_pack_blind/` (không có trên git). **Không mở thư mục `_private`** và không mở gói cũ `cvat_pack/`, vì ở đó có ý kiến của Claude.

Gói mù không hiện nhãn của agent, nguồn ảnh hay nhóm. Tự nhìn ảnh rồi quyết định. Ảnh không đủ rõ thì chọn `unclear`, đừng đoán.

| Task | Việc | Thứ tự |
|---|---|---|
| `trial` | Thử gói, khoảng 10 hộp | 1 |
| `task_a` | Ủng ở tập đánh giá | 2, làm cùng bảng cảnh |
| `task_c` | Mẫu giày và kính | 3 |
| `task_d` | Mẫu ảnh đo ủng thiếu nhãn | 4 |
| `task_b` | Kính ở tập đánh giá | 5 |
| `second` | Dành cho người thứ hai, không bắt buộc | bất kỳ lúc nào |

## Công cụ duyệt nhanh

Dùng cho `task_a`, `task_b`, `task_c`, `task_d`, thay cho bấm trong CVAT. Công cụ chỉ giảm thao tác: mọi lựa chọn do bạn bấm cho từng hộp, không có gợi ý hay chọn hàng loạt. Quy tắc nhãn ở các mục dưới vẫn giữ nguyên.

```
python scripts/03q_ppe6_fast_review.py --task task_a --reviewer "Tên bạn"
```

Mở http://127.0.0.1:8765 bằng Chrome. Tự lưu sau mỗi phím; đóng rồi chạy lại lệnh là tiếp tục đúng chỗ.

| Phím | Việc |
|---|---|
| `1` `2` `3` `4` | `decision`: bảo hộ, thường, không rõ, bỏ qua |
| `7` `8` `9` | `person_ok`: đủ lớn, quá nhỏ, không chắc |
| `V` / `R` | Ảnh: đã xem xong / loại ảnh |
| `←` hoặc `Z` / `→` | Quay lại / đi tiếp, không đổi giá trị |
| `S` / `N` | Xem sau / nhảy tới ô thiếu kế tiếp |
| `Del` | Xóa lựa chọn của hộp đang xem |
| `C` / `M` | Hộp này / ảnh này cần mở CVAT; bấm lại để bỏ đánh dấu |

Đủ ô của một hộp thì tự sang hộp sau. `task_b`, `task_d` có thêm bước xem cả ảnh, phải bấm `V` hoặc `R`.

Cần mở CVAT khi hộp lệch, ảnh thiếu hộp, hoặc ca khó: bấm `C` hoặc `M`, link nằm cuối trang. Trong CVAT chỉ sửa vị trí hoặc vẽ hộp mới rồi Save, **không đặt `decision`, `person_ok` ở đó**. Quay lại công cụ, chọn phím, rồi bấm `C` hoặc `M` lần nữa để bỏ đánh dấu.

`task_d`: không thấy ủng rõ thì `V`. Nhìn rõ ủng bảo hộ thì `M`, vẽ `boots_new` trong CVAT, quay lại bỏ đánh dấu rồi bấm `V`. Ảnh chỉ tính là thiếu nhãn khi có hộp `boots_new`.

Cuối buổi, trong PowerShell đã đặt token:

```
$s = Read-Host "Token CVAT" -AsSecureString
$env:CVAT_LOCAL_TOKEN = [Net.NetworkCredential]::new('', $s).Password
python scripts/03r_ppe6_fast_finish.py --task task_a --reviewer "Tên bạn"
```

Lệnh dừng nếu còn ô thiếu hoặc mục cần mở CVAT; thêm `--partial` nếu cố ý nhập dở. Nó cũng dừng, không ghi đè, nếu giá trị trên CVAT khác công cụ.

## Tạo task

1. Trên CVAT, tạo task mới, đặt đúng tên thư mục (`trial`, `task_a`...). Mục Labels chọn tab Raw, dán nội dung `labels.json` của task đó.
2. Tải `images.zip` làm dữ liệu. Giữ thứ tự theo tên ảnh.
3. Actions → Upload annotations, định dạng **CVAT for images 1.1**, chọn `annotations.xml`.
4. Duyệt xong: Actions → Export task dataset, định dạng **CVAT for images 1.1**, bỏ tích Save images.

## Thử `trial` trước

1. Mở job, kiểm tra thấy khoảng 10 hộp đúng vị trí, `decision` và `person_ok` đang là `chua_chon`.
2. Đặt `decision`, `person_ok` cho mọi hộp, thêm một tag `image_checked`, vẽ một hộp `boots_new`.
3. Xuất file rồi chạy:

```
python scripts/03l_ppe6_import_review.py --task trial --file <file_xuất.zip> --reviewer "Tên bạn"
```

Kết quả đúng: in từng hộp với giá trị trước, sau và tên bạn. Ghi vào `trial_review.csv`, không tính là đã duyệt. Có thể thử để sót một ô: lệnh phải dừng, không ghi gì, và liệt kê ô đó. Nếu lỗi khác, gửi nội dung lỗi và file xuất; đừng duyệt tiếp.

## Duyệt từng hộp

Xem cả ảnh, không chỉ trong hộp. Mỗi hộp đặt `decision`:

| Giá trị | Khi nào |
|---|---|
| `safety` | Đúng đồ bảo hộ theo định nghĩa dưới |
| `ordinary` | Đồ thường, hoặc không đang đeo, đang mang |
| `unclear` | Không phân biệt được; ảnh sẽ bị loại khỏi đánh giá lớp mới |
| `ignore` | Có đồ nhưng quá nhỏ, quá mờ; không tính đúng, không tính sai |
| `chua_chon` | Mặc định. Không bao giờ được coi là đồng ý; lệnh nhập sẽ dừng nếu còn ô này |

Hộp lệch thì kéo lại cho đúng. Đừng xóa hộp; hộp sai thì chọn `ordinary` hoặc `unclear`.

**Kính bảo hộ:** đang đeo trên mắt và có dấu hiệu của chính chiếc kính: tròng ôm mặt, tấm chắn bên, gọng kiểu kính an toàn, tròng vàng hoặc đỏ, kính kín kiểu goggle. Không xét người đó có đội mũ hay không.

**Ủng, giày bảo hộ:** nhìn rõ là ủng cao su, ủng công trình, giày cổ cao đế dày kiểu công trình. Giày thể thao, kể cả loại dày, giày da, dép là `ordinary`.

**Ca khó:**

- Kính tối không phân biệt được với kính râm: `unclear`.
- Gọng thường, tròng trong, không có tấm chắn: `unclear` nếu không chắc là kính cận.
- Kính đẩy lên đầu, treo áo, cầm tay: `ordinary`.
- Giày tối màu, không thấy cổ và đế: `unclear`.
- Hộp ở chân trần, ống quần, hoặc lệch hẳn khỏi vật: kéo lại nếu thấy vật, không thì `unclear`.

**`person_ok`** (`trial`, `task_a`, `task_b`), dùng để chốt ngưỡng người đủ lớn. Chỉ xét theo mắt nhìn:

| Giá trị | Khi nào |
|---|---|
| `du_lon` | Người đủ lớn để bạn phân biệt được đồ bảo hộ với đồ thường |
| `qua_nho` | Người quá nhỏ hoặc góc quá cao để phân biệt |
| `khong_ro` | Không chắc |

## Thêm hộp và gắn thẻ ảnh

- Thấy kính, ủng bảo hộ chưa có hộp: vẽ hộp nhãn `goggles_new` hoặc `boots_new`.
- Xem xong một ảnh: thêm tag `image_checked`. **Bắt buộc với mọi ảnh trong `task_b` và `task_d`**, kể cả ảnh không có hộp; thiếu tag thì ảnh đó chưa được tính.
- Ảnh không dùng được: tag `reject_image`.

`task_d` không có hộp. Chỉ vẽ `boots_new` khi nhìn rõ là ủng hoặc giày bảo hộ; người ở xa không nhìn rõ thì không vẽ. Kết quả chỉ để đo, không đổi nhãn train. Với mỗi tầng dưới 10%, chỉ ghi là không phát hiện vấn đề rõ: 0/33 vẫn có cận trên khoảng 10,4%.

## Duyệt cảnh (làm cùng `task_a`)

Mở `data/ppe6/review/cvat_pack/scene_review/scene_NN.jpg`. Thư mục này chỉ có ảnh và mã cảnh, không có nhãn hộp. Mỗi hàng là một cảnh: bên trái vạch đỏ là ảnh đánh giá, bên phải là 3 ảnh train gần nhất.
Điền `scene_review.csv`, cột `same_as_train` = `yes` nếu cùng buổi chụp, cùng người hoặc cùng chỗ, `no` nếu không. Cảnh `yes` bị loại khỏi đánh giá. Xem kỹ `s00294`.
`repeat_scene_check.jpg`: mỗi hàng là một cụm lớn, thứ tự `s00000` đến `s00007`. Claude coi `s00001`, `s00005`, `s00007` là cảnh lặp thật, còn lại là cụm nối nhầm. Nếu sai, báo để sửa `repeat_scenes` trong `configs/ppe6.yaml`.

## Nhập kết quả

Chạy từ gốc project. Lệnh dừng và không ghi gì nếu còn ô `chua_chon`; thêm `--partial` để nhập phần đã chọn và liệt kê phần còn thiếu.

```
python scripts/03l_ppe6_import_review.py --task task_a --file <file_xuất.zip> --reviewer "Tên bạn"
python scripts/03l_ppe6_import_review.py --scenes <scene_review.csv> --reviewer "Tên bạn"
python scripts/03i_ppe6_build_dataset.py
python scripts/03l_ppe6_import_review.py --report
```

`--report` in tỉ lệ khác nhau giữa bạn và Claude theo nhóm gốc, lớp, nguồn. Làm tương tự với `task_c`, `task_d`, `task_b`.

Sau khi nhập hết, theo thứ tự:

```
python scripts/03i_ppe6_build_dataset.py
python scripts/03n_ppe6_readiness.py gates
python scripts/03n_ppe6_readiness.py scope --write
python scripts/03n_ppe6_readiness.py monitor --variant c2
python scripts/03n_ppe6_readiness.py monitor --variant c1
python scripts/03n_ppe6_readiness.py checklist
```

`gates` chỉ ra quy tắc nào kích hoạt. Nếu mọi mục `pass`, đặt `final.data_locked: true` trong `configs/ppe6.yaml`.

## Người thứ hai

Tùy chọn, là kiểm tra chất lượng, không phải quyết định nhãn cuối. Người thứ hai duyệt độc lập task `second` theo cùng hướng dẫn, không xem kết quả của bạn. Bạn cũng phải duyệt `task_a`, `task_b` thì mới so được.

```
python scripts/03l_ppe6_import_review.py --task second --file <file_xuất.zip> --second-reviewer "Tên người thứ hai"
python scripts/03l_ppe6_import_review.py --agreement
```

Kết quả ghi riêng `second_review.csv`, `agreement.json`, không ghi đè bạn, không ảnh hưởng dataset, gates, checklist.
