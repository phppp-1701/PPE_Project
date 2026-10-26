# Đặc tả hệ thống (theo báo cáo bản 24/10/2026)

Nội dung chuyển từ Chương 1-3 của `D:\KhoaLuan\BaoCao\report_DinhHuy_HoangPhuong_24_10.docx`. Số mục, bảng, công thức trong ngoặc là số trong báo cáo. Mọi ngưỡng và tham số dưới đây **chưa có giá trị**: chọn trên tập xác thực hoặc video chỉnh tham số, ghi vào `configs/`, rồi khóa lại trước khi kiểm thử.

## 1. Bài toán (mục 3.1)

Chuyển video từ **một camera** (trực tiếp hoặc video ghi sẵn, mỗi lúc một nguồn) thành các bản ghi vi phạm PPE có thể kiểm tra lại.

**Đầu vào:**
- Khung hình kèm số thứ tự và mốc thời gian. Với video ghi sẵn, mốc thời gian là vị trí trong video. Với camera, là thời điểm nhận khung hình.
- `source_id`, `session_id` và danh sách PPE bắt buộc của nguồn.

Ảnh được đưa về kích thước đầu vào của YOLO11s, sau đó tọa độ được quy đổi về khung hình gốc.

**Đầu ra có ba mức:**
1. **Khung hình:** danh sách `(class, bbox, conf)`.
2. **Người:** `track_id`, `bbox` và trạng thái Có / Thiếu / Chưa xác định cho từng PPE bắt buộc. Găng tay được xét cả hai tay.
3. **Sự kiện:** mỗi đợt vi phạm đã xác nhận là một bản ghi. `missing_items` có thể đổi trong lúc sự kiện còn mở. Chỉ mức này được lưu lại.

### Yêu cầu chức năng (Bảng 3.1)

| Mã | Yêu cầu |
|---|---|
| FR-01 | Đọc khung hình từ camera hoặc video, kèm nguồn và phiên |
| FR-02 | Phát hiện bốn lớp: bbox, nhãn, độ tin cậy |
| FR-03 | Liên kết PPE với từng người, xử lý trường hợp nhiều người |
| FR-04 | Trạng thái Có/Thiếu/Chưa xác định cho từng PPE bắt buộc; găng tay xét riêng từng tay |
| FR-05 | Gán và duy trì mã theo dõi tạm thời qua các khung hình |
| FR-06 | Tổng hợp theo thời gian; không cảnh báo từ một khung hình riêng lẻ |
| FR-07 | Một sự kiện cho mỗi đợt vi phạm liên tục; cập nhật `missing_items`, không tạo bản ghi trùng |
| FR-08 | Lưu sự kiện kèm thời gian, nguồn, mã theo dõi, ảnh hoặc clip minh chứng |
| FR-09 | Dashboard: cảnh báo, lọc lịch sử, xem minh chứng, thống kê |
| FR-10 | Cấu hình PPE bắt buộc cho từng nguồn |

### Yêu cầu phi chức năng (Bảng 3.2)

| Mã | Yêu cầu |
|---|---|
| NFR-01 | Đo được FPS, thời gian mỗi khung hình, độ trễ cảnh báo; nêu rõ phạm vi của từng phép đo |
| NFR-02 | Đổi PPE bắt buộc và tham số mà không sửa cấu trúc module |
| NFR-03 | Mỗi sự kiện truy được nguồn, phiên, mã theo dõi, mốc thời gian, PPE thiếu, minh chứng |
| NFR-04 | Mã theo dõi chỉ có nghĩa trong (nguồn, phiên), không phải danh tính người lao động |
| NFR-05 | Phát hiện, liên kết, theo dõi, trạng thái, lưu trữ, giao diện tách riêng, kiểm thử riêng được |

## 2. Dữ liệu (mục 3.2)

### 2.1. Nguồn và ánh xạ nhãn (Bảng 3.3)

Lớp cố định khai báo trong `configs/ppe4.yaml`: **0 person, 1 helmet, 2 vest, 3 gloves**.

| Nguồn | Vai trò | Ánh xạ | Bỏ |
|---|---|---|---|
| SH17 (8.099 ảnh, 17 lớp) | Nguồn chính | person→0, helmet→1, vest→2, gloves→3; chỉ giữ helmet/gloves khi đúng là **mũ, găng bảo hộ** | 13 lớp còn lại, gồm `shoes` |
| CHV (1.330 ảnh, 6 lớp) | Bổ sung mũ, áo | person→0, 4 lớp mũ theo màu→1 (giữ nguyên hộp), vest→2; **gán bổ sung găng tay**, ảnh gán không đủ rõ thì loại | — |
| Construction-PPE (1.416 ảnh, 11 lớp, AGPL-3.0) | Bổ sung, chủ yếu găng tay, sau kiểm tra nhãn bằng mắt | Person→0, helmet→1, vest→2, gloves→3 | boots, goggles, none, mọi nhãn `no_*` |
| Pictor-PPE (phần công khai) | **Chỉ kiểm thử ngoài** | worker→0, hat→1, vest→2 | không có găng tay; báo cáo riêng theo lớp |

Nhãn `no_*` không trở thành lớp đầu ra. Trạng thái Thiếu do bước xử lý theo người quyết định, không do detector.

### 2.2. Làm sạch (`scripts/01_convert_labels.py`, `02_check_data.py`)

- Dữ liệu gốc trong `data/raw/` giữ nguyên; kết quả ghi sang `data/ppe4/`.
- Mỗi nguồn ghi lại phiên bản, link tải, định dạng nhãn, điều kiện sử dụng và số ảnh thực tế dùng.
- Nhãn lưu theo định dạng YOLO: `class cx cy w h`, chuẩn hóa theo kích thước ảnh.
- **Mỗi ảnh phải được gán đủ cả 4 lớp.** Đối tượng bị che thì hộp chỉ bao phần nhìn thấy.
- **Ba bước kiểm tra:**
  1. **Kỹ thuật:** ảnh đọc được, có file nhãn, mã lớp 0-3, hộp có kích thước khác 0 và nằm trong ảnh.
  2. **Nội dung:** tìm nhãn sót, sai lớp, hộp lệch, nhãn không thống nhất giữa các nguồn. Găng tay cần chú ý riêng. Mỗi lần sửa ghi lại ảnh, nhãn trước, nhãn sau, lý do.
  3. **Trùng lặp:** tìm ảnh trùng hoặc gần trùng giữa các nguồn (CHV lấy lại ảnh từ GDUT-HWD và SHWD). Ảnh cùng cảnh mang cùng `group_id`.
- Giữ ảnh khó (che, tối, mờ, vật nhỏ) nếu nhãn đáng tin. Chỉ loại ảnh không xác định được loại PPE.
- **Thống kê sau làm sạch:** số ảnh theo nguồn, số đối tượng theo lớp, phân bố kích thước hộp, số nhãn đã sửa, số mẫu bị loại.

### 2.3. Chia tập (`scripts/03_split_data.py`)

- train/val/test ≈ **70/15/15**. Đơn vị chia là **nhóm ảnh** (`group_id`), không phải từng ảnh. Lưu `group_id` và tập của từng ảnh vào `data/ppe4/stats.csv`.
- Sau khi chia, kiểm tra: găng tay không dồn vào một tập, tập test không chỉ có ảnh của một nguồn. Nếu cần cân bằng thì chia lại theo nhóm.
- Pictor-PPE nằm ngoài phép chia. Trước khi kiểm thử, loại khỏi Pictor-PPE các ảnh trùng với dữ liệu huấn luyện.
- Video chia theo **cả video**: video dùng chỉnh tham số tách khỏi video dùng đánh giá cuối. Không video nào được dùng để huấn luyện.

### 2.4. Tăng cường dữ liệu

- Chỉ áp dụng cho train, sau khi chia tập. Lưu cấu hình để tái lập.
- **Các phép được xem xét:** độ sáng/tương phản, nhiễu, làm mờ, nhòe chuyển động, đổi tỷ lệ, cắt ảnh, xoay góc nhỏ, mosaic. Chọn phép nào dùng theo kết quả trên val.
- **Không dùng:** lật dọc, xoay góc lớn. Khi cắt ảnh, đối tượng mất hết phần nhìn thấy thì bỏ nhãn của nó.
- Nếu găng tay ít mẫu: lấy mẫu nhiều hơn ảnh có găng hoặc tăng cường có chọn lọc.

### 2.5. Video kiểm thử (`data/videos/`)

- Video từ Internet, camera cố định, cảnh xưởng hoặc công trường.
- Cần có: một người và nhiều người, di chuyển, che khuất, người thiếu trang bị, ưu tiên video thấy rõ tay.
- Loại video cắt ghép, chuyển cảnh liên tục, hoặc có chữ chèn che người. Ghi link nguồn của từng video vào `video_sources.csv`.
- **Gán nhãn bằng CVAT:**
  - Mỗi người một ID nhất quán qua các khung hình.
  - Mỗi PPE bắt buộc gán Có, Thiếu hoặc Chưa xác định theo những gì nhìn thấy.
  - Sự kiện chuẩn gán độc lập với dự đoán (mục 7.4).
- Minh chứng chỉ dùng cho nghiên cứu, không công bố lại.

## 3. Detector YOLO11s (mục 3.3.1, `scripts/04_train.py`)

- Khởi tạo từ trọng số tiền huấn luyện, thay head theo 4 lớp. Không so sánh nhiều thế hệ YOLO.
- Huấn luyện trên Kaggle (ultralytics==8.4.189, cùng phiên bản với máy); laptop chỉ dùng để suy luận, chạy hệ thống và đo hiệu năng.
- **Mỗi lần huấn luyện ghi vào `docs/experiments/`:**
  - Loại GPU Kaggle đã dùng.
  - Phiên bản Ultralytics, trọng số khởi tạo, `imgsz`, `epochs`, `batch`, optimizer, learning rate, `seed`, cấu hình tăng cường.
  - Phiên bản dữ liệu và đường dẫn trọng số tạo ra.
- Chọn trọng số theo **mAP@0.5:0.95 trên val**. Báo cáo kèm P, R, F1, mAP@0.5 **từng lớp**, và xem trực quan các lỗi bỏ sót, nhầm, hộp lệch.
- Ngưỡng `conf` và NMS IoU chọn trên val, cân nhắc cả FP lẫn FN. Có thể dùng `conf` riêng cho từng loại PPE.
- Đo thời gian suy luận và FPS của riêng YOLO11s.

## 4. Phương pháp đối chứng theo khung hình, cấu hình A (mục 3.3.2)

Dùng cùng trọng số YOLO11s và xử lý từng khung hình độc lập.

- Lọc theo `conf`, tách thành tập người và tập PPE theo lớp. Bỏ qua người có hộp quá nhỏ hoặc không hợp lệ.
- **Ứng viên:** tâm hộp PPE nằm trong hộp người và đúng vùng theo chiều dọc. Vị trí tương đối `r_y = (y_c − y1)/(y2 − y1)` (3.2). Mũ ở phần trên, áo ở thân, găng trong vùng rộng quanh tay. Giới hạn vùng chọn trên val.
- PPE rơi vào vùng của nhiều người thì gán cho người có khoảng cách chuẩn hóa nhỏ nhất. Mỗi hộp chỉ gán cho một người.
- **Trạng thái** (3.3): `S = 1[|M_{p,k,t}| ≥ m_k]`, với `m_mũ = m_áo = 1` và `m_găng = 2`. Không kiểm tra hai găng có thuộc hai tay khác nhau không. Chỉ có Có/Thiếu, **không có Chưa xác định**.
- Cảnh báo ở mọi khung hình có Thiếu. Không tracker, không cửa sổ thời gian, không sự kiện.

## 5. Phương pháp đề xuất (mục 3.4)

**Sáu bước mỗi khung hình:**
1. YOLO11s phát hiện người và PPE.
2. ByteTrack theo dõi **chỉ hộp người**.
3. Gán PPE theo vùng cơ thể.
4. Kiểm tra khả năng quan sát, kết luận ba trạng thái.
5. Xác nhận qua cửa sổ thời gian.
6. Quản lý sự kiện và minh chứng.

Detector và tracker không ghi trực tiếp vào cơ sở dữ liệu.

### 5.1. Phát hiện và theo dõi (`detector.py`, `tracker.py`)

- Tách kết quả thành tập người và 3 tập PPE, quy đổi về tọa độ gốc. **Không track PPE.** Lịch sử trạng thái lưu theo `track_id` của người.
- Dùng `ultralytics.trackers.byte_tracker.BYTETracker`, gọi trực tiếp với hộp người. Không dùng `model.track()`, vì nó track mọi lớp.
- ByteTrack dùng cả hộp có độ tin cậy thấp khi ghép. Tuy vậy, **chỉ hộp người đạt ngưỡng ở khung hiện tại mới được dùng để xác định trạng thái**. Quỹ đạo chỉ còn được giữ bằng dự đoán hoặc hộp có độ tin cậy thấp thì vẫn giữ mã, nhưng trạng thái khung đó là Chưa xác định.
- Ngưỡng ghép và `track_buffer` chọn trên video chỉnh tham số.
- `track_id` chỉ có nghĩa trong (`source_id`, `session_id`). Phiên mới thì khởi tạo lại tracker và lịch sử. Khi đổi ID, không tự ghép hai mã.

### 5.2. Gán PPE theo vùng cơ thể (`association.py`, mục 3.4.3)

Cho hộp người `(x1, y1, x2, y2)`, với `w_p = x2 − x1` và `h_p = y2 − y1`:
- **Mũ:** từ `y1` đến `y1 + τ_h·h_p`.
- **Áo:** từ `y1 + τ_v1·h_p` đến `y1 + τ_v2·h_p`.
- **Găng:** hai vùng trái, phải (theo hướng ảnh).

Các hệ số vùng chọn trên val.

- **Ứng viên:** tâm hộp PPE thuộc vùng. **Khoảng cách chuẩn hóa** (3.4): `d = sqrt(((c_x − a_x)/w_p)² + ((c_y − a_y)/h_p)²)`, với `a` là tâm vùng.
- Gán cho ứng viên gần nhất nếu `d ≤ max_distance`. Hai ứng viên tốt nhất chênh nhau dưới `ambiguity_margin` thì đánh dấu **tranh chấp**, không gán.
- Mỗi hộp PPE chỉ gán cho một người. Mỗi hộp găng chỉ gán cho một tay. Hai găng cùng ở một tay **không** được tính là đeo đủ găng hai tay.
- Lưu mọi trường hợp bị từ chối (vượt ngưỡng, tranh chấp, không rõ bên) để xét Chưa xác định và phân tích lỗi.

**YOLO11n-pose là tùy chọn có điều kiện.** Chỉ thêm khi val cho thấy quy tắc hình học gây nhiều lỗi gán. Nếu thêm:
- Giữ nguyên trọng số tiền huấn luyện. Ghép một-một với hộp người theo độ chồng lấp.
- Dùng cổ tay trái/phải làm tâm vùng găng. Ứng viên nằm trong elip (3.5): `((c_x − q_x)/(ρ_x·w_p))² + ((c_y − q_y)/(ρ_y·h_p))² ≤ 1`.
- Chỉ dùng cổ tay có tọa độ hợp lệ và độ tin cậy đạt ngưỡng. Đo lại chất lượng và thời gian trước khi giữ.

### 5.3. Khả năng quan sát và ba trạng thái (`compliance.py`, mục 3.4.4)

Với vùng `R`, khung hình `F` và `U` là hợp hộp của những người khác:
- `v = area(R∩F)/area(R)` và `o = area(R∩U)/area(R)` (3.6). `A` là diện tích phần `R` nằm trong ảnh.
- `G = 1` khi hộp người hợp lệ, đủ độ tin cậy và vùng đạt điều kiện hình học. Vùng tay không phân biệt được hai bên thì `G = 0`.
- Vùng đủ quan sát (3.7): `O = 1 ⇔ v ≥ τ_in,k ∧ o ≤ τ_occ,k ∧ A ≥ A_min,k ∧ G = 1`.

**Trạng thái (Bảng 3.5):**
- **Mũ, áo:**
  - Có nếu `O = 1` và có PPE gán hợp lệ.
  - Thiếu nếu `O = 1`, không có PPE hợp lệ và không còn tranh chấp.
  - Còn lại là Chưa xác định.
- **Găng, xét từng tay:**
  - Một tay nhìn rõ mà không có găng → Thiếu.
  - Cả hai tay có găng → Có.
  - Các tay nhìn thấy đều có găng nhưng còn tay chưa kiểm tra được → Chưa xác định.
- **Không phát hiện được PPE không đồng nghĩa với Thiếu.**

### 5.4. Xác nhận theo thời gian (`temporal.py`, mục 3.4.5)

- Mỗi cặp (`track_id`, PPE) có một cửa sổ **theo giây**, không theo số khung hình. Chưa xác định được lưu nhưng không tính vào số quan sát.
- Tỷ lệ thiếu (3.8): `R_missing = N_thiếu/(N_có + N_thiếu)` trong `T_on`. Mẫu số bằng 0 thì không xác nhận.
- **Xác nhận thiếu:** có ít nhất `n_on` quan sát hợp lệ, `R_missing ≥ θ_on`, và trạng thái hiện tại là Thiếu.
- **Xác nhận khắc phục:** trong `T_off`, có ít nhất `n_off` quan sát hợp lệ, tỷ lệ Có ≥ `θ_off`, và trạng thái hiện tại là Có. Chưa xác định không bao giờ là bằng chứng khắc phục.
- Sáu tham số `T_on, T_off, n_on, n_off, θ_on, θ_off` chọn trên video chỉnh tham số, cân nhắc cảnh báo sai, vi phạm bị sót và độ trễ.

### 5.5. Sự kiện và minh chứng (`events.py`, mục 3.4.6)

- Mỗi `(source_id, session_id, track_id)` có tối đa **một** sự kiện đang mở. PPE không nằm trong khóa.
- Chưa có sự kiện mà một PPE được xác nhận thiếu → tạo sự kiện.
- Sự kiện đang mở:
  - PPE mới được xác nhận thiếu → thêm vào `missing_items`.
  - PPE được xác nhận khắc phục → bỏ khỏi `missing_items`.
  - PPE chuyển sang Chưa xác định → giữ kết quả xác nhận gần nhất.
- **Đóng `recovered`** chỉ khi **mọi** PPE bắt buộc đạt điều kiện khắc phục. `missing_items` rỗng chưa đủ để đóng.
- Không có quan sát hợp lệ mới → `pending_observation`, không có timeout.
- Phiên kết thúc mà chưa có bằng chứng khắc phục → đóng `session_ended_unverified`.
- Đổi PPE bắt buộc và áp dụng ngay → kết thúc phiên, đóng với `policy_changed`.
- Đổi ID → track mới tạo sự kiện mới; sự kiện dư tính là cảnh báo trùng khi đánh giá.
- **Minh chứng:**
  - Lúc xác nhận lần đầu, lưu ảnh có hộp người, `track_id` và PPE thiếu. Có thể lưu thêm ảnh khi `missing_items` đổi.
  - Clip là tùy chọn.
  - Tệp lưu ở `outputs/evidence/`; cơ sở dữ liệu chỉ lưu đường dẫn.

### 5.6. Vòng lặp (`pipeline.py`, Bảng 3.6)

1. Khởi tạo phiên: PPE bắt buộc, YOLO11s, ByteTrack, bộ đệm trạng thái, sự kiện đang mở.
2. Đọc khung hình, chạy YOLO11s, quy đổi tọa độ.
3. Tách người và PPE, lọc theo ngưỡng.
4. Cập nhật ByteTrack.
5. Gán PPE, xử lý tranh chấp (cổ tay nếu đã chọn pose).
6. Kiểm tra khả năng quan sát, gán ba trạng thái.
7. Cập nhật cửa sổ thời gian, kiểm tra xác nhận thiếu hoặc khắc phục.
8. Mở, cập nhật hoặc đóng sự kiện.
9. Lưu minh chứng, gửi cho backend.
10. Kết thúc phiên: đóng sự kiện chưa xác minh, giải phóng tài nguyên.

Camera và video dùng chung vòng lặp này. **Ghi thời gian từng bước**: detector, tracker, gán PPE, trạng thái, sự kiện, pose nếu có.

## 6. Lưu trữ, API, dashboard (mục 3.5)

**Trường sự kiện (Bảng 3.7):** `event_id, source_id, session_id, track_id, start_time, confirmed_at, last_seen_time, missing_items, event_state, end_time, close_reason, evidence_refs, policy_version`.
- `event_state ∈ {active, pending_observation, closed}`.
- `close_reason ∈ {recovered, session_ended_unverified, policy_changed}`.
- Với video, tách thời gian trong video khỏi thời điểm hệ thống ghi.

**Sáu nhóm bảng:**
- `Source`
- `PPE Policy` (có version)
- `Monitoring Session` (lưu bản chụp policy đang dùng)
- `Violation Event`
- `Event PPE History`
- `Event Evidence`

Có ràng buộc duy nhất cho sự kiện đang mở trên `(source_id, session_id, track_id)`.

**API (Bảng 3.8):**

| Thao tác | Mục đích |
|---|---|
| `POST /events` | Tạo sự kiện; gửi lại cùng `event_id` không tạo trùng |
| `PATCH /events/{event_id}` | Cập nhật `missing_items`, trạng thái, `last_seen_time`, thông tin đóng |
| `GET /events` | Lọc theo nguồn, thời gian, PPE, trạng thái |
| `GET /events/{event_id}` | Chi tiết, lịch sử PPE, minh chứng |
| `GET /events/{event_id}/evidence` | Ảnh và clip minh chứng |
| `GET /events/stats` | Thống kê theo thời gian, nguồn, PPE, trạng thái |
| `GET /sources/{source_id}/ppe-policy` | Đọc PPE bắt buộc |
| `PUT /sources/{source_id}/ppe-policy` | Cập nhật PPE bắt buộc và version |

- `event_id` do chuỗi xử lý sinh ra.
- Lưu tệp minh chứng **trước**, ghi đường dẫn vào cơ sở dữ liệu **sau**.
- Dashboard cập nhật qua WebSocket hoặc truy vấn định kỳ.

**Dashboard:**
- Chỉ hiển thị, không tự quyết định vi phạm.
- Mỗi người thiếu nhiều PPE vẫn chỉ có **một dòng**. Mỗi dòng gồm thời điểm xác nhận, nguồn, `track_id`, PPE thiếu và trạng thái.
- `pending_observation` hiển thị khác `recovered`. Sự kiện đã đóng ghi lý do đóng.
- Lọc theo thời gian, nguồn, PPE, trạng thái. Mở từng sự kiện xem lịch sử và minh chứng.
- **Thống kê:** "số sự kiện" đếm theo `event_id`. "Lượt vi phạm theo PPE" có thể lớn hơn số sự kiện, nên đặt tên khác nhau.
- Mỗi nguồn có công tắc bật/tắt mũ, áo, găng. Cấu hình mới áp dụng từ phiên sau, trừ khi chọn áp dụng ngay.

## 7. Thực nghiệm (mục 3.6, `scripts/06_evaluate.py`)

### 7.1. Ablation study (Bảng 3.11)

Tất cả cấu hình dùng cùng video và cùng kết quả phát hiện, xuất cùng định dạng `(video_id, t, person_bbox, missing_ppe[])`.

| Cấu hình | Thành phần |
|---|---|
| A | YOLO11s + hình học đơn giản + Có/Thiếu; cảnh báo mỗi khung có Thiếu |
| B | A + kiểm tra vùng cơ thể, tranh chấp, Chưa xác định; vẫn cảnh báo theo khung |
| C | B + ByteTrack; vẫn cảnh báo theo khung |
| D | C + cửa sổ thời gian; chưa có sự kiện |
| E | D + vòng đời sự kiện (phương án triển khai) |

- A-D chỉ dùng để đối chứng. Với A và B, cảnh báo ghép với người chuẩn theo vị trí.
- Báo cáo riêng các tình huống: nhiều người, vùng cơ thể bị che, găng chỉ ở một tay.

### 7.2. Câu hỏi nghiên cứu (Bảng 3.9)

| RQ | Dữ liệu | Độ đo |
|---|---|---|
| RQ1 phát hiện | test nội bộ, Pictor-PPE riêng | P, R, F1, AP, mAP@0.5, mAP@0.5:0.95 từng lớp; thời gian suy luận |
| RQ2 gán PPE, trạng thái | video kiểm thử | tỷ lệ gán đúng, ma trận 3×3, P/R/F1 từng trạng thái, macro-F1, Coverage |
| RQ3 theo dõi, cảnh báo | video kiểm thử, A-E | MOTA, IDF1, IDSW (khi đủ nhãn); Event P/R/F1, cảnh báo sai, cảnh báo trùng, độ trễ |
| RQ4 hệ thống | video và camera | bảng FR-01…10 (Đạt/Không đạt/Chưa kiểm thử kèm bằng chứng), FPS, thời gian từng bước (p50/p95), CPU/GPU/RAM |

### 7.3. Công thức (Chương 2)

- `IoU = |A∩B|/|A∪B|`
- `P = TP/(TP+FP)`, `R = TP/(TP+FN)`, `F1 = 2PR/(P+R)`
- `Coverage = (N_có + N_thiếu)/N_tổng`. Luôn báo cáo cùng F1.
- `MOTA = 1 − Σ(m_t + fp_t + mme_t)/Σ g_t`; `IDF1 = 2·IDTP/(2·IDTP + IDFP + IDFN)`

### 7.4. Quy tắc ghép với nhãn chuẩn (Bảng 3.12)

- **Trạng thái:**
  - Ghép người một-một khi IoU ≥ 0,5, rồi so trạng thái trong ma trận 3×3.
  - **Chưa xác định vẫn nằm trong ma trận.** Coverage tính trên các cặp đã ghép; tỷ lệ người bị bỏ sót báo cáo riêng.
  - Gán sai người hoặc sai tay là lỗi gán, không tính cho detector.
- **Theo dõi:** chỉ tính MOTA/IDF1/IDSW khi đủ nhãn quỹ đạo. Cảnh báo trùng không phải IDSW.
- **Sự kiện:**
  - Cảnh báo khớp sự kiện chuẩn khi: cùng video, IoU người ≥ 0,5, thời điểm nằm trong khoảng sự kiện, có ít nhất một PPE trùng.
  - Ghép theo thời gian. Cảnh báo khớp đầu tiên là `TP_event`; các cảnh báo sau cho cùng đợt là cảnh báo trùng; cảnh báo không khớp là cảnh báo sai.
  - Cảnh báo trùng và cảnh báo sai đều thuộc `FP_event` nhưng báo cáo riêng. Sự kiện chuẩn không có cảnh báo là `FN_event`.
  - Với E, kiểm tra thêm việc cập nhật `missing_items` và điều kiện đóng. Đóng do hết video không tính là đóng đúng.
- **Sự kiện chuẩn:**
  - Bắt đầu khi lần đầu có đủ bằng chứng thiếu ít nhất một PPE bắt buộc; kết thúc khi mọi PPE bắt buộc được nhìn thấy đầy đủ.
  - Khoảng Chưa xác định không gán thành Có hay Thiếu. Hết video mà chưa khắc phục thì ghi chưa xác minh.
- **Độ trễ:** từ lúc sự kiện chuẩn đủ bằng chứng đến lúc cảnh báo, chỉ tính cho sự kiện ghép được, luôn đi kèm Event Recall. Với video, tính theo mốc thời gian khung hình.
- **FPS toàn luồng** = số khung hình xử lý xong / thời gian thực. Ghi kèm `imgsz`, batch, phiên bản.

### 7.5. Kỷ luật tham số

- Chọn mọi tham số trên val hoặc video chỉnh tham số, ghi vào `configs/`, khóa lại rồi mới chạy test.
- Gán PPE: chọn theo F1 **và** Coverage. Thời gian: chọn theo Event F1, cảnh báo sai, cảnh báo trùng, độ trễ.
- Test chỉ dùng để đo. Nếu kết quả test dẫn tới thay đổi thì ghi thành vòng phát triển mới, cần dữ liệu đánh giá độc lập khác.

## 8. Phần cứng

Laptop Intel Core i5-11500H, NVIDIA RTX 3050 Laptop 4 GB, RAM 32 GB.
