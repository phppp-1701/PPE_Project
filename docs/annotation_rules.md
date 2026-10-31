# Quy tắc gán nhãn găng tay cho CHV (CVAT)

Áp dụng cho mọi task `chv_partXX` trong project `CHV gloves`. Cả hai người đọc file này trước khi gán; gặp trường hợp mới thì thống nhất rồi bổ sung vào đây.

## Việc cần làm

Ảnh CHV đã có sẵn hộp `person`, `helmet`, `vest`. Chỉ **vẽ thêm hộp `gloves`**, hoặc gắn tag `reject` cho ảnh cần loại.

## 0. Hộp `gloves` máy vẽ sẵn và tag `check` (part02, part03)

Từ ngày 30/10/2026, `chv_part02` và `chv_part03` có sẵn hộp `gloves` do mô hình YOLOE vẽ (`scripts/01c_prelabel_gloves.py`). Bấm vào hộp, CVAT ghi nguồn là `auto`.

Sau đó máy duyệt lại toàn bộ (`scripts/01d_cvat_apply_review.py`): đã xóa các hộp chắc chắn không phải găng, và gắn tag **`check`** cho những ảnh máy không chắc (part02: 214 ảnh, part03: 326 ảnh). **Chỉ cần xem các ảnh có tag `check`**; ảnh không có tag là máy đã duyệt, không cần mở.

- Lọc ảnh trong CVAT: thanh trên cùng của job → biểu tượng phễu (Filter) → `Label` `==` `check` → chọn lọc theo frame có annotation. Hoặc bấm phím chuyển tới ảnh kế tiếp có annotation phù hợp bộ lọc.
- Xem xong một ảnh: sửa theo các quy tắc dưới, rồi **xóa tag `check`** của ảnh đó (bấm vào tag ở danh sách Objects bên phải → Delete). Hết tag `check` là xong task.
- Ảnh có tag `check` chỉ vì người ở xa, quá nhỏ: không cần vẽ găng (mục 3), xóa tag là xong.
- `chv_part03` được tạo lại ngày 31/10/2026 để **278 ảnh có tag `check` nằm ở đầu task (frame 0–277)**: chỉ cần duyệt từ frame 0 đến 277, phần sau là ảnh máy đã duyệt. Số ảnh `check` giảm từ 326 xuống 278 nhờ quy tắc rút từ kết quả người duyệt part02: hộp găng máy "không chắc" nhưng có độ tin cậy YOLOE ≥ 0,5 thì giữ (trên part02 đúng 84/94 hộp).
- `chv_part02` cũng được tạo lại ngày 31/10/2026 (`scripts/01e_cvat_reorder_task.py`, giữ nguyên mọi hộp/tag đã gán): **32 ảnh còn tag `check` nằm ở frame 0–31**.
- Ảnh không có tag `check` chỉ dùng cho tập train (máy duyệt), ảnh có tag đã được người xem mới được dùng cho val/test. Danh sách lưu ở `data/ppe4/converted/chv/cvat/chv_review_images.csv`.

Khi xem ảnh có tag `check`:

- Hộp đúng là găng và sát mép: **giữ nguyên**.
- Hộp đúng là găng nhưng lệch hoặc rộng: **kéo sửa** cho sát mép (quy tắc mục 2).
- Hộp vẽ vào tay trần, ống tay áo, dụng cụ, hoặc hai hộp cho cùng một chiếc găng: **xóa**.
- Găng máy bỏ sót (khoảng 1/4): **vẽ thêm** như thường.
- Người cao dưới khoảng 80 px mà máy vẫn vẽ găng: xóa (mục 3).
- Quy tắc `reject` không đổi: máy không gắn `reject`, người gán tự quyết định.

## 1. Cái gì là găng tay

| Trường hợp | Gán `gloves`? |
|---|---|
| Găng bảo hộ: vải, sợi len, da, cao su, găng phủ hạt, đeo trên tay | Có |
| Găng đang đeo nhưng chỉ thấy một phần (tay cầm dụng cụ, bị che) | Có, hộp bao phần thấy được |
| Găng không đeo (cầm trên tay, nhét túi, để dưới đất) | Có, vẫn vẽ nếu nhìn rõ là găng |
| Tay trần | Không vẽ gì |
| Ống tay áo dài che kín bàn tay | Không vẽ gì |
| Bàn tay bị che hoàn toàn (sau lưng, trong túi, sau vật khác) | Không vẽ gì |

Mô hình chỉ học nhận ra găng tay; găng có thuộc người nào hay đang đeo không là việc của bước gán PPE sau này. Vì vậy găng không đeo vẫn gán.

## 2. Cách vẽ hộp

- **Mỗi chiếc găng một hộp.** Hai tay đều đeo găng thì hai hộp, kể cả khi hai tay chồng lên nhau.
- Hộp **sát mép chiếc găng**, bao từ đầu ngón tay đến cổ găng; không bao cả cẳng tay hay ống tay áo.
- Găng bị che một phần: hộp **chỉ bao phần nhìn thấy**, không đoán phần bị che.
- Phóng to (lăn chuột) trước khi vẽ để mép hộp chính xác.

## 3. Khi nào gắn tag `reject` (loại cả ảnh)

Gắn `reject` khi **không thể quyết định** tay có găng hay không, sau khi đã phóng to:

- Người ở quá xa, bàn tay chỉ còn vài điểm ảnh, không phân biệt được găng với tay trần.
- Ảnh mờ, tối hoặc nhòe đúng chỗ bàn tay.
- Màu găng gần màu da hoặc nền, không chắc chắn.

Lý do: ảnh có găng mà không được gán sẽ dạy mô hình rằng găng tay là nền. Thà bỏ ảnh còn hơn để nhãn thiếu.

Không gắn `reject` chỉ vì ảnh không có găng; ảnh toàn tay trần là ảnh tốt, giữ lại.

Không gắn `reject` khi người **quá nhỏ hoặc quá xa đến mức không xác định được bàn tay ở đâu**: coi như tay không nhìn thấy và bỏ qua. Cụ thể: **hộp `person` cao dưới khoảng 80 px** (CVAT hiện kích thước khi bấm vào hộp, ví dụ `53.0x53.0px`) thì không xét găng của người đó, không vẽ, không `reject`. Ở cỡ này, khi đưa ảnh về 640 px để huấn luyện, bàn tay chỉ còn vài điểm ảnh. `reject` chỉ dùng khi bàn tay đủ lớn để thấy mà vẫn không phân biệt được găng hay tay trần.

Cách phân biệt tay có găng khi ảnh mờ: bàn tay có màu khác hẳn màu da (đen, xám, xanh, vàng, cam) thì là găng; thấy màu da và ngón tay thì là tay trần; chỉ là một đốm mờ lẫn với áo hoặc nền thì `reject`.

Nếu thấy mình `reject` quá nhiều (hơn khoảng 1/5 số ảnh của một phần), dừng lại và báo nhóm để xem lại quy tắc.

## 4. Hộp có sẵn (person, helmet, vest)

- **Thiếu hộp rõ ràng thì vẽ thêm luôn** (ví dụ người mặc áo phản quang có dải phản quang nhưng không có hộp `vest`). Vẽ theo cùng cách: sát mép phần nhìn thấy. Không cần ghi lại: khi ghép nhãn, script so bản xuất từ CVAT với nhãn gốc và tự liệt kê mọi hộp được thêm.
- Người ở hậu cảnh bị **mờ do lấy nét** nhưng vẫn nhận ra rõ là người (đủ lớn, thấy dáng người) thì vẽ đủ `person`, `helmet`, `vest` như người bình thường; mũ hoặc người bị mép ảnh cắt thì hộp chỉ bao phần nằm trong ảnh.
- **Mũ, áo, găng không đeo vẫn vẽ** (mũ cầm trên tay hoặc để dưới đất, áo vắt hoặc để trên đống đồ, găng cầm trên tay), miễn là nhìn rõ. YOLO chỉ học nhận ra vật; việc vật có đang được đeo hay không do bước gán PPE theo vùng cơ thể quyết định. Chốt ngày 27/10/2026.
- **Không sửa, không xóa hộp có sẵn**, kể cả khi thấy lệch. Hộp lệch ghi vào `data/ppe4/converted/chv/cvat/notes.txt`, mỗi dòng một ảnh, ví dụ:
  `ppe_0012.jpg  helmet lệch sang phải`
- **`vest` = áo gile bảo hộ màu huỳnh quang (cam, vàng chanh), có hoặc không có dải phản quang**, kể cả áo lưới. Chốt ngày 27/10/2026 sau khi xem mẫu: SH17 và Construction-PPE đều gán `vest` cho áo huỳnh quang không thấy dải phản quang, còn CHV thì bỏ sót; gặp áo loại này trong CHV mà chưa có hộp thì vẽ thêm. Áo khoác, áo dài tay hoặc áo thun huỳnh quang **có dải phản quang** (áo bảo hộ) cũng tính là `vest`, hộp chỉ bao phần thân áo (vai đến gấu áo), không bao ống tay hay quần. Áo khoác, áo thun, quần áo liền thân màu cam **thường, không có dải phản quang** thì **không** tính.
- **Trường hợp không chắc** có nên thêm hộp không thì không vẽ, ghi vào `notes.txt` để cả nhóm quyết định.
- Các ghi chú được xử lý ở bước kiểm tra dữ liệu (`scripts/02_check_data.py`).

## 5. Thao tác

| Phím | Tác dụng |
|---|---|
| Biểu tượng hình chữ nhật → Label `gloves` → Shape | Vẽ hộp đầu tiên |
| **N** | Vẽ tiếp hộp mới với nhãn vừa dùng |
| Biểu tượng thẻ treo → `reject` → Tag | Gắn tag loại ảnh |
| **F** / **D** | Ảnh sau / ảnh trước |
| **Ctrl + S** | Lưu (sau khoảng 10 ảnh) |
| **Delete** | Xóa hộp đang chọn (chỉ xóa hộp `gloves` mình vẽ) |

## 6. Chia việc

CHV có 1.330 ảnh, chia thành 3 task trong project `CHV gloves` (Organization `ppeKhoaLuan`):

| Task | Ảnh | Người gán |
|---|---|---|
| `chv_part01` | 100 ảnh, `ppe_0000`–`ppe_0099` | Phương (đã xong) |
| `chv_part02` | 615 ảnh, `ppe_0100`–`ppe_0714` | Huy |
| `chv_part03` | 615 ảnh, `ppe_0715`–`ppe_1329` | Phương |

Lý do chỉ có 3 task: gói miễn phí của CVAT chỉ cho mỗi Organization tạo **tối đa 3 task**. Ban đầu định chia 14 phần × 100 ảnh, nhưng không tạo được task thứ 4, nên ngày 27/10/2026 gộp 1.230 ảnh còn lại thành 2 task lớn. Không tạo thêm task trong Organization này.

- Mỗi ảnh chỉ một người gán. Task lớn: nhớ **Ctrl + S** thường xuyên, có thể gán nhiều buổi.
- Xong một task, export **hai bản** (Actions → Export task dataset, bỏ tích Save images):
  1. Định dạng **YOLO 1.1** → đặt tên `chv_partXX_done.zip`.
  2. Định dạng **CVAT for images 1.1** → đặt tên `chv_partXX_done_cvat.zip`. Bản này giữ tag `reject`; YOLO 1.1 chỉ lưu hộp nên có thể làm mất tag.
- Để cả hai file vào `data/ppe4/converted/chv/cvat/` trên máy của Phương. Thư mục `data/` không đưa lên Git, nên Huy gửi hai file zip và các dòng ghi chú (`notes.txt`) cho Phương qua Drive hoặc tin nhắn.
