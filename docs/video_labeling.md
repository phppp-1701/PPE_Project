# Gán nhãn video trên CVAT

Áp dụng cho video chỉnh tham số và video đánh giá (spec 2.5, 7.4). Hai người gán đọc trước khi làm. Người gán không xem kết quả của hệ thống trên video đó, để nhãn độc lập với dự đoán.

## 1. Tạo task

1. Vào app.cvat.ai, chọn **Tasks** → **+** → **Create a new task**.
2. **Name:** tên video, ví dụ `video2`. **Project:** để trống, vì project `CHV gloves` có bộ nhãn khác.
3. Ở phần **Labels**, mở tab **Raw**, xóa nội dung cũ, dán đoạn dưới rồi bấm **Done**:

```json
[
  {
    "name": "person",
    "type": "rectangle",
    "attributes": [
      {"name": "helmet", "input_type": "select", "mutable": true, "default_value": "chua_xac_dinh", "values": ["chua_xac_dinh", "co", "thieu"]},
      {"name": "vest", "input_type": "select", "mutable": true, "default_value": "chua_xac_dinh", "values": ["chua_xac_dinh", "co", "thieu"]},
      {"name": "glove_left", "input_type": "select", "mutable": true, "default_value": "chua_xac_dinh", "values": ["chua_xac_dinh", "co", "thieu"]},
      {"name": "glove_right", "input_type": "select", "mutable": true, "default_value": "chua_xac_dinh", "values": ["chua_xac_dinh", "co", "thieu"]},
      {"name": "goggles", "input_type": "select", "mutable": true, "default_value": "chua_xac_dinh", "values": ["chua_xac_dinh", "co", "thieu"]},
      {"name": "boots", "input_type": "select", "mutable": true, "default_value": "chua_xac_dinh", "values": ["chua_xac_dinh", "co", "thieu"]}
    ]
  }
]
```

4. Ở **Select files**, tải file video lên.
5. Mở **Advanced configuration**, đặt **Image quality** là 100. Các mục còn lại giữ nguyên.
6. Bấm **Submit & Open**, rồi mở job. Kiểm tra số khung trong job bằng số khung của video (`video2`: 102 khung).

## 2. Vẽ khung người

Dùng chế độ **Track**, không dùng Shape: mỗi người là một track, nên ID giữ nguyên suốt video.

1. Ở khung đầu tiên người đó xuất hiện, chọn công cụ hình chữ nhật, nhãn `person`, bấm **Track**, rồi vẽ.
2. Cứ khoảng 5 khung, chỉnh lại hộp một lần. Người đứng yên có thể giãn thưa hơn, người đi nhanh thì dày hơn. CVAT tự nội suy các khung ở giữa.
3. Xem lại cả track: hộp phải bám người ở mọi khung, kể cả khung nội suy.

| Tình huống | Cách làm |
|---|---|
| Ai cần gán | Mọi người mà mắt nhìn ra là người, kể cả người xa hay ở mép khung |
| Hộp bao đến đâu | Phần cơ thể **nhìn thấy** của đúng người đó; không đoán phần bị che, không ôm sang người bên cạnh |
| Bị che một phần | Giữ hộp trên phần nhìn thấy, bật **Occluded** (phím Q) |
| Ra khỏi khung hoặc bị che hoàn toàn | Bật **Outside** (phím O) từ khung đó |
| Quay lại sau khi khuất | Dùng **cùng track**: tới khung người đó xuất hiện lại, tắt Outside và chỉnh hộp. Không tạo track mới |
| Không chắc có phải cùng một người không | Xem kỹ quần áo và hướng đi; vẫn không chắc thì tạo track mới và ghi vào mục 5 |

## 3. Gán trạng thái PPE

Mỗi track có 6 thuộc tính ở bảng **Objects** bên phải (4 thuộc tính đầu từ bản 4 lớp; `goggles`, `boots` thêm cho bản 6 lớp, nhãn video 3-6 đã có). Thuộc tính giữ nguyên ở các khung sau cho tới khi bạn đổi, nên chỉ cần đổi **tại khung trạng thái thay đổi**.

Chỉ dựa vào **những gì nhìn thấy trong khung đang xét**. Không suy từ khung trước, khung sau hay từ người bên cạnh.

| Giá trị | Khi nào dùng |
|---|---|
| `co` | Nhìn rõ PPE đang được đeo hoặc mặc đúng vị trí |
| `thieu` | Nhìn rõ vùng cơ thể đó và chắc chắn không có PPE |
| `chua_xac_dinh` | Vùng bị che, ra ngoài khung, quá mờ hoặc quá nhỏ để kết luận |

Khi phân vân giữa `thieu` và `chua_xac_dinh`, chọn `chua_xac_dinh`.

**Từng loại PPE:**

- **`helmet`:** chỉ mũ bảo hộ cứng mới là `co`. Mũ lưỡi trai, mũ vải, mũ len, khăn hoặc đầu trần nhìn rõ là `thieu`. Mũ đang cầm tay, treo hoặc để trên bàn không tính.
- **`vest`:** áo phản quang hoặc áo gile bảo hộ mặc trên người là `co`, nhìn từ trước, sau hay bên đều được. Chỉ thấy một phần áo nhưng chắc chắn là áo phản quang vẫn là `co`. Áo màu cam hoặc vàng không có dải phản quang và không phải gile bảo hộ là `thieu`. Áo cầm tay hoặc treo trên giá không tính.
- **`glove_left`, `glove_right`:** xét từng tay. `left` là tay nằm **bên trái ảnh** so với giữa thân người, `right` là bên phải ảnh, không phải tay trái hay phải của người đó. Thấy rõ da bàn tay là `thieu`. Bàn tay khuất sau thân, bàn, thùng hoặc chỉ còn vài điểm ảnh mờ là `chua_xac_dinh`. Cầm vật màu trắng không tự động là găng; không chắc thì `chua_xac_dinh`.

- **`goggles`:** kính bảo hộ **đang đeo trên mắt** là `co` (tròng ôm mặt hoặc có tấm chắn bên, gọng dày kiểu kính an toàn, kính kín kiểu goggle; định nghĩa ở `docs/annotation_rules.md`). Mắt nhìn rõ mà không đeo kính, hoặc đeo **kính cận, kính râm thời trang** là `thieu`. Kính cầm tay, đẩy lên đầu, treo áo cũng là `thieu` nếu mắt nhìn rõ. Người quay lưng, mặt khuất, quá nhỏ là `chua_xac_dinh`. Mặt nghiêng mà vẫn thấy rõ kính thì vẫn là `co`.
- **`boots`:** theo định nghĩa ủng bản 3 ở `docs/annotation_rules.md`, chỉ nhìn chính chiếc giày: ủng cao su, nhựa, giày công trình cổ cao đế dày là `co`; giày thể thao, giày tây, dép, giày vải là `thieu`; chân ra ngoài khung, bị che, quá tối, giày da thấp cổ không rõ là `chua_xac_dinh`. Hai chân khác nhau: một chân nhìn rõ không có ủng là `thieu`.

## 4. Lưu và xuất

1. Bấm **Save** thường xuyên.
2. Xong thì người thứ hai xem lại cả video và sửa những chỗ sai rõ ràng. Chỗ hai người không thống nhất thì ghi vào mục 5.
3. Xuất nhãn: **Actions** → **Export task dataset** → định dạng **CVAT for video 1.1**, **không** chọn lưu kèm ảnh.
4. Đổi tên file tải về theo tên video (ví dụ `video2_cvat.zip`) rồi đặt vào `data/videos/`.

## 5. Ghi chú trường hợp khó

Ghi lại vào một file `<tên video>_notes.txt` cùng thư mục: số khung, track nào, việc gì chưa chắc. Không tự đổi quy tắc giữa chừng; nếu cần đổi thì sửa file này trước, rồi rà lại phần đã gán.
