# Kế hoạch app desktop Windows cho hệ thống giám sát PPE

Tài liệu dành cho thành viên làm app desktop. Đọc kèm `CLAUDE.md` (luật làm việc của project), `docs/spec.md` (đặc tả,
bảng FR / NFR), `backend/README.md`, `dashboard/README.md`. Kế hoạch lập 18/11/2026, người dùng (chủ project) đã duyệt
các điểm ở mục 1. Hạn khóa luận 30/11/2026.

## 1. Mục tiêu và phạm vi (đã chốt)

| Điểm | Chốt |
|---|---|
| Hệ điều hành | **Chỉ Windows 10/11, 64 bit** |
| Phần cứng | Có **GPU NVIDIA** (như laptop RTX 3050 4 GB của project); vẫn phải chạy được trên CPU (chậm) khi không có GPU |
| Nguồn | **Webcam** (đã có ở bản web) và **file video** (`.mp4`, `.avi`, mới) |
| Xuất dữ liệu | **CSV** danh sách sự kiện + ảnh minh chứng |
| Cài đặt | Một bộ cài; người dùng cuối không cần Python, không gõ lệnh |

App phải làm được mọi việc của bản web hiện tại (camera trực tiếp, bật / tắt PPE bắt buộc áp dụng ngay, danh sách sự kiện,
chi tiết minh chứng, phản hồi giám sát viên, thống kê) và thêm: chạy file video, màn hình cài đặt, xuất CSV, đóng app an
toàn.

**Không thuộc phạm vi:** đổi mô hình, ngưỡng, luật nhận diện; nhiều camera cùng lúc; tài khoản / đăng nhập; macOS, Linux.

## 2. Nguyên tắc (bắt buộc)

1. **Không sửa phần nhận diện:** `src/ppe/`, `configs/pipeline.yaml`, `configs/ppe6.yaml`, trọng số trong `outputs/train/`.
   Mọi số đo trong báo cáo (mAP, FPS, Event F1) được đo trên đúng code này; app chỉ là vỏ. Cần đổi gì ở đây thì hỏi chủ
   project trước.
2. **Dùng lại backend và dashboard**, không viết lại logic. Một bản code nhận diện duy nhất cho web, desktop và script đo.
3. **Không cài gói mới khi chưa hỏi**; khi cài phải khóa phiên bản trong `requirements.txt` và `requirements-lock.txt`.
4. Tham số vận hành (cổng, thư mục dữ liệu, camera mặc định, độ phân giải…) để trong `configs/desktop.yaml`, không viết
   cứng trong code. Ngưỡng nhận diện **không** đưa ra màn hình cài đặt (chỉ hiển thị để đọc).
5. Tên file, biến, hàm tiếng Anh; giao diện, tài liệu, chú thích tiếng Việt. Mỗi thư mục / script mới có giải thích trong
   README tương ứng.
6. Không train, không dùng video cho huấn luyện; webcam của người dùng chỉ để chạy thử.
7. Làm trên nhánh riêng `feat/desktop` tách từ `exp/ppe6`; quy trình Git, Pull Request ở mục 12, chuẩn bị máy ở mục 13. Không push trọng số, video, dữ liệu.

## 3. Kiến trúc

```
┌──────────────── PPE Monitor.exe (một tiến trình) ────────────────┐
│ Cửa sổ app (pywebview, dùng Microsoft Edge WebView2 có sẵn trên Win) │
│     └─ hiển thị http://127.0.0.1:<cổng>/  (dashboard HTML/JS)      │
│ Luồng nền: uvicorn chạy backend.app (FastAPI), chỉ nghe 127.0.0.1  │
│     ├─ LiveCamera (backend/live.py): webcam hoặc file video        │
│     │     └─ PPEPipeline (src/ppe) → detector, pose, tracker, ...  │
│     ├─ SQLite: %LOCALAPPDATA%\PPEMonitor\ppe.db                    │
│     └─ Ảnh minh chứng: %LOCALAPPDATA%\PPEMonitor\evidence\         │
└──────────────────────────────────────────────────────────────────┘
```

- **Vỏ:** `pywebview` mở một cửa sổ Windows nhúng trang dashboard. Đóng cửa sổ → dừng camera (đóng phiên với lý do
  `session_ended_unverified` như bản web), tắt uvicorn, đóng SQLite.
- **Cổng:** chọn cổng trống lúc mở app (không cố định 8000, tránh trùng server khác); chỉ nghe `127.0.0.1`.
- **Đường dẫn:** khi chạy từ bộ cài, code, cấu hình, trọng số nằm trong thư mục cài (chỉ đọc); dữ liệu người dùng (DB,
  minh chứng, CSV xuất, log) nằm trong `%LOCALAPPDATA%\PPEMonitor\`. Hiện `backend/db.py` dùng `outputs/ppe.db`: thêm một
  lớp `paths` đọc `configs/desktop.yaml` / biến môi trường, mặc định giữ đường dẫn cũ để bản web và test không đổi.
- **Một tiến trình, một mô hình:** chỉ một nguồn chạy tại một thời điểm (như `LiveCamera` hiện tại). Không mở hai
  cửa sổ app cùng lúc (khóa bằng file lock).

### Thư mục, file mới (dự kiến, chủ project đã duyệt tạo `desktop/`)

| Đường dẫn | Nội dung |
|---|---|
| `desktop/main.py` | điểm vào: đọc cấu hình, chọn cổng, chạy uvicorn ở luồng nền, mở cửa sổ pywebview, xử lý đóng app |
| `desktop/paths.py` | đường dẫn khi chạy từ mã nguồn và khi chạy từ bộ cài (`sys._MEIPASS` của PyInstaller) |
| `desktop/ppe_monitor.spec` | cấu hình PyInstaller |
| `desktop/README.md` | cách chạy từ mã nguồn, cách đóng gói, kiểm tra trên máy sạch |
| `configs/desktop.yaml` | cổng (0 = tự chọn), thư mục dữ liệu, camera mặc định, độ phân giải, giữ dữ liệu bao nhiêu ngày, thiết bị (cuda / cpu) |
| `backend/video_file.py` | nguồn file video cho `LiveCamera` (mục 4.1) |
| `dashboard/` | tách `index.html` (1.310 dòng) thành `index.html`, `css/`, `js/` (mục 5.10); trang trợ giúp `dashboard/help/` (mục 5.4) |
| `desktop/CHANGELOG.md`, `desktop/LICENSES.txt`, `desktop/assets/` | nhật ký phiên bản, giấy phép, biểu tượng, màn hình chờ (mục 7) |
| `tests/test_desktop.py` | test API mới (TestClient, DB tạm như `tests/test_live.py`) |

## 4. Việc ở backend

### 4.1 Nguồn file video

- `LiveCamera` hiện đọc webcam, **bỏ khung cũ** để luôn xử lý khung mới nhất (đúng cho camera). Với file video không được
  bỏ khung tùy tiện vì thời gian sự kiện phải khớp video: đọc tuần tự, thời gian `t = chỉ_số_khung / fps_video`.
- Hai chế độ phát: **thời gian thực** (đợi cho khớp tốc độ video, giống camera, để xem) và **nhanh nhất có thể** (để xử lý
  cả file). Mặc định: thời gian thực.
- Điều khiển: Bắt đầu, Tạm dừng / Tiếp tục, Dừng; tiến độ (khung hiện tại / tổng, giây). Hết file → kết thúc phiên như
  bấm Dừng.
- Mỗi lần chạy file là một phiên mới, nguồn `video_<tên file>` (tạo bằng `ensure_source`, loại `video`), giữ đúng
  NFR-03, NFR-04 (mã theo dõi chỉ có nghĩa trong (nguồn, phiên)).
- Cách làm gợi ý: `LiveCamera` nhận `capture_factory` sẵn (đã dùng trong `tests/test_live.py` với `FakeCap`), thêm cờ
  `sequential` để luồng đọc không bỏ khung và trả thời gian theo khung; kiểm lại kết quả với `scripts/05_run_video.py`
  trên `data/videos/video4.mp4` (số sự kiện, PPE thiếu phải khớp ở chế độ nhanh nhất có thể).

### 4.2 API mới hoặc sửa

| API | Việc |
|---|---|
| `POST /api/live/start` | thêm thân `{source: "camera" \| "file", camera_index?, path?, mode?: "realtime" \| "fast"}`; mặc định camera như cũ |
| `POST /api/live/pause`, `POST /api/live/resume` | chỉ cho file video |
| `GET /api/live/status` | thêm `source_type`, `file_name`, `frame`, `total_frames`, `position_s`, `duration_s`, `paused` |
| `GET /api/cameras` | thử mở camera 0…`max_index` (cấu hình), trả danh sách mở được, độ phân giải |
| `GET /api/settings`, `PUT /api/settings` | đọc / ghi phần cho phép sửa của `configs/desktop.yaml` (lưu bản người dùng trong thư mục dữ liệu, không ghi đè file trong bộ cài) |
| `GET /api/system` | phiên bản app, commit, trọng số detector (tên + sha256 ngắn), GPU / CPU, đường dẫn dữ liệu, ngưỡng chính (chỉ đọc) |
| `GET /api/export/events.csv` | xuất sự kiện theo bộ lọc hiện tại (phiên, nguồn, trạng thái, PPE, khoảng thời gian) |
| `GET /api/export/events.zip` | CSV + ảnh minh chứng của các sự kiện đó |

Cột CSV (gợi ý): `event_id, source_id, session_id, track_id, status, missing_items, started_at (giờ thật),
confirmed_at (giây trong phiên), closed_at, close_reason, policy_version, evidence_count, feedback`. Mã hóa UTF-8 có BOM
để Excel đọc đúng tiếng Việt.

Mọi API mới có test trong `tests/test_desktop.py`; toàn bộ test hiện có (`pytest`) vẫn phải qua.

## 5. Kế hoạch giao diện chi tiết

### 5.1 Nguyên tắc chung

- Một cửa sổ, **thanh điều hướng bên trái** với 6 mục: Giám sát, Sự kiện, Thống kê, Cài đặt, Trợ giúp, Giới thiệu. Thanh trạng
  thái dưới cùng luôn hiện: nguồn đang chạy, FPS xử lý, GPU / CPU, số sự kiện đang mở, đồng hồ.
- Cửa sổ tối thiểu 1280 × 720; mở mặc định phóng to. Giữ giao diện tối như dashboard hiện tại, chữ tiếng Việt, cỡ chữ
  ≥ 14 px, nút ≥ 36 px cao.
- **Màu trạng thái thống nhất toàn app**, khớp với hình vẽ trên khung video (`scripts/05_run_video.py`):
  **Có = xanh lá, Thiếu = đỏ, Chưa xác định = trắng / xám**; người chưa đủ dữ liệu = xanh dương; mất dấu tạm = xám nét đứt.
  Không chỉ dựa vào màu: luôn kèm chữ (Có / Thiếu / Chưa xác định) hoặc biểu tượng.
- Chữ viết tắt PPE dùng như trên khung hình: **M** mũ, **A** áo, **G** găng, **K** kính, **U** ủng; tooltip ghi đủ tên.
- Mỗi màn hình có ba trạng thái: đang tải, rỗng (ví dụ "Chưa có sự kiện nào trong phiên này"), lỗi (thông báo dễ hiểu +
  việc nên làm, ví dụ "Không mở được webcam 0. Kiểm tra ứng dụng khác có đang dùng webcam không, hoặc chọn webcam khác
  trong Cài đặt").
- Mã theo dõi hiển thị là "Người #12 (tạm thời trong phiên)"; không hiện hay lưu danh tính người lao động (NFR-04).

### 5.2 Màn hình Giám sát (màn hình chính)

```
┌ Nguồn: (•) Webcam [Webcam 0 ▾]  ( ) File video [Chọn file…]   [▶ Bắt đầu] [⏸] [■ Dừng] ┐
├────────────────────────────────────────────┬───────────────────────────────┤
│                                            │ PPE bắt buộc                    │
│        Khung hình đã nhận diện             │  [x] Mũ  [x] Áo  [x] Găng        │
│        (MJPEG, giữ tỉ lệ, nền đen)         │  [x] Kính [x] Ủng   (áp dụng ngay)│
│                                            ├───────────────────────────────┤
│                                            │ Người trong khung (3)           │
│                                            │  #4  M● A● G○ K● U●  Thiếu: Găng │
│ [══════════●────────] 00:41 / 01:30 (file) │  #7  M● A● G◌ K◌ U●  Chưa đủ     │
├────────────────────────────────────────────┤ Cảnh báo mới nhất               │
│ FPS 24,1 | Camera 30 | Phiên 2026-11-18-… │  10:21:05 #4 Thiếu Găng [Xem]   │
└────────────────────────────────────────────┴───────────────────────────────┘
```

- **Chọn nguồn:** Webcam (danh sách từ `GET /api/cameras`) hoặc File video (hộp thoại chọn file của Windows, lọc `.mp4`,
  `.avi`, `.mov`); với file thêm lựa chọn "Thời gian thực / Nhanh nhất có thể".
- **Nút:** Bắt đầu, Tạm dừng / Tiếp tục (chỉ file), Dừng. Khi đang chạy không cho đổi nguồn; nút đổi trạng thái rõ.
- **Khung hình:** chiếm phần lớn màn hình; chú thích màu nhỏ ở góc. Khi tắt: ảnh nền hướng dẫn "Chọn nguồn rồi bấm Bắt
  đầu".
- **Công tắc PPE:** khối riêng, mô tả đầy đủ ở mục 5.3.
- **Danh sách người trong khung:** mỗi người một dòng, 5 ô trạng thái theo màu, PPE đang thiếu viết rõ. Bấm một dòng →
  khung video viền nổi người đó (tùy chọn, làm sau nếu kịp).
- **Cảnh báo mới nhất:** 5 sự kiện gần nhất của phiên; sự kiện mới hiện thông báo góc màn hình (toast, tự tắt sau 5 giây)
  và có thể bật tiếng "bíp" trong Cài đặt (mặc định tắt). Nút Xem mở chi tiết sự kiện (mục 5.5).
- **Thanh tiến độ** (chỉ file): khung / tổng, giây; không cho tua (tua làm sai thời gian sự kiện).
- **Chú thích** luôn hiện dưới khung hình (gập lại được): màu hộp người, ý nghĩa chữ M / A / G / K / U và ba màu trạng
  thái, nét đứt = mất dấu tạm (mẫu ở mục 5.3).

### 5.3 Khối "PPE bắt buộc" (bật / tắt PPE)

Đây là chức năng người dùng chạm vào nhiều nhất; phải hiểu được mà không cần đọc hướng dẫn.

```
┌ PPE bắt buộc cho nguồn: Webcam 0 ─────────────────────── (!) ┐
│  [■] M  Mũ bảo hộ        Bắt buộc                              │
│  [■] A  Áo phản quang    Bắt buộc                              │
│  [■] G  Găng tay         Bắt buộc   (xét riêng từng tay)       │
│  [□] K  Kính bảo hộ      Không kiểm   (kính cận, kính râm không tính) │
│  [■] U  Ủng bảo hộ       Bắt buộc   (giày thường không tính)   │
│  Đang kiểm 4/5 món · Quy định phiên bản 7 · áp dụng 10:21:05   │
│  [Bật tất cả] [Tắt tất cả] [Mẫu: Công trường ▾]                │
└───────────────────────────────────────────────────────────────┘
```

- **Mỗi dòng:** công tắc lớn, chữ viết tắt in đậm (đúng chữ trên khung hình), tên đầy đủ, trạng thái chữ "Bắt buộc" /
  "Không kiểm" bên cạnh (không chỉ dựa vào màu công tắc), ghi chú định nghĩa ngắn cho món dễ nhầm (kính: chỉ kính bảo hộ
  đang đeo trên mắt; ủng: chỉ ủng / giày bảo hộ nhìn rõ; găng: từng tay).
- **Áp dụng ngay**, không có nút Lưu (như bản web, lưu tự động sau 0,6 giây). Sau mỗi lần đổi hiện thông báo ngắn:
  "Đã áp dụng: không kiểm Kính. Các cảnh báo đang mở được đóng với lý do 'Đổi quy định PPE'." Đổi khi đang chạy → phiên
  bản quy định tăng, ghi vào sự kiện (NFR-03).
- **Tắt hết:** hỏi xác nhận "Không kiểm món nào: hệ thống chỉ theo dõi người, không tạo cảnh báo. Tiếp tục?"; khung hình chỉ
  còn hộp người, không còn chữ.
- **Mẫu nhanh** (lưu trong `configs/desktop.yaml`, sửa được): "Công trường" (M, A, G, U), "Hàn / mài" (M, A, G, K, U),
  "Kho" (M, A). Chọn mẫu = bật / tắt các công tắc tương ứng, vẫn áp dụng ngay.
- **Theo nguồn:** quy định gắn với nguồn (webcam 0, mỗi file video). Tiêu đề khối ghi rõ đang sửa nguồn nào.
- **Khóa khi chưa có nguồn:** chưa chạy vẫn cho chỉnh (áp dụng cho lần chạy tới), ghi "Sẽ áp dụng khi bắt đầu".
- **Chú thích trạng thái** (cạnh khung hình và trong trợ giúp):

| Hiển thị | Nghĩa |
|---|---|
| Chữ **xanh lá** (vd **G**) | Có: đang đeo món đó |
| Chữ **đỏ** | Thiếu: không đeo (sau khi xác nhận qua vài giây, không báo từ một khung) |
| Chữ **trắng** | Chưa xác định: bị che, quá nhỏ, ra ngoài khung — hệ thống không kết luận |
| Không có chữ | Món đó đang "Không kiểm" |
| Hộp người xanh dương | Người mới vào, chưa đủ dữ liệu để kết luận |
| Hộp người nét đứt xám | Mất dấu tạm thời (bị che, đi ra) |

### 5.4 Trợ giúp (nút "!")

- **Nút "!" tròn** ở góc mỗi khối khó hiểu (PPE bắt buộc, khung hình, bộ lọc sự kiện, xuất CSV, cài đặt thiết bị) và trên
  thanh điều hướng. Bấm → bảng nhỏ giải thích khối đó trong 3–6 dòng, có hình minh họa nếu cần, nút "Xem thêm" mở trang
  trợ giúp đúng mục.
- **Tooltip** khi rê chuột trên mọi nút, công tắc, chữ viết tắt, cột bảng (vd rê lên **K** → "Kính bảo hộ: Chưa xác
  định — mắt bị che hoặc quá nhỏ").
- **Hướng dẫn lần đầu** (tự hiện lần đầu mở app, xem lại được trong Trợ giúp): 4–5 bước có mũi tên chỉ vào màn hình — chọn
  nguồn → chọn PPE bắt buộc → bấm Bắt đầu → đọc chữ trên khung hình → xem sự kiện. Có nút "Bỏ qua", "Không hiện lại".
- **Trang Trợ giúp** (mục thứ 6 trên thanh điều hướng, phím `F1`): mục lục; bắt đầu nhanh; ý nghĩa màu và chữ; bật / tắt
  PPE; chạy file video; đọc và xử lý sự kiện (phản hồi báo sai); xuất dữ liệu; cài đặt; **câu hỏi thường gặp** (vì sao
  kính cận không được tính, vì sao người ở xa luôn "Chưa xác định", vì sao cảnh báo trễ vài giây, webcam không mở được, máy
  không có GPU chạy chậm); **giới hạn của hệ thống** (lấy từ báo cáo: điều kiện ánh sáng, cỡ người tối thiểu, mức chính xác
  đã đo từng PPE). Nội dung viết bằng HTML tĩnh trong `dashboard/help/`, chạy không cần Internet, có ô tìm kiếm.
- **Thông báo lỗi có hướng dẫn:** mỗi lỗi có câu "Nên làm gì" và liên kết tới mục trợ giúp tương ứng.

### 5.5 Màn hình Sự kiện

- **Bộ lọc** trên cùng: phiên (Phiên gần nhất / Mọi phiên / chọn phiên), nguồn, trạng thái (Đang mở / Đã đóng / Chờ xác
  minh…), PPE thiếu, khoảng thời gian (hôm nay, 7 ngày, tùy chọn), ô tìm theo mã sự kiện.
- **Bảng:** thời điểm (giờ thật + giây trong phiên), nguồn, phiên, người #, PPE thiếu (chip màu), trạng thái, thời lượng, số
  ảnh minh chứng, phản hồi. Sắp xếp theo cột, phân trang 50 dòng, mới nhất trước (như bản web: theo giờ hệ thống).
- **Chi tiết sự kiện** (bảng trượt từ phải hoặc hộp thoại, giữ nội dung bản web): dải ảnh minh chứng theo mốc thời gian,
  ảnh lớn có hộp, dòng thời gian (mở, cập nhật PPE thiếu, đóng và lý do), phản hồi giám sát viên (báo sai từng PPE, ghi
  chú, lịch sử phản hồi).
- **Xuất:** "Xuất CSV" (theo bộ lọc đang chọn) và "Xuất CSV + ảnh (ZIP)"; hộp thoại lưu file của Windows; thông báo đường
  dẫn khi xong, nút "Mở thư mục".

### 5.6 Màn hình Thống kê

- Thẻ số liệu: tổng sự kiện, đang mở, đã đóng, chờ xác minh, tỉ lệ báo sai theo phản hồi (nếu có).
- Biểu đồ: vi phạm theo PPE (cột), theo giờ trong ngày (cột), theo nguồn / phiên (bảng). Lọc theo khoảng thời gian.
- Vẽ bằng SVG / CSS thuần (như thanh thống kê hiện có); muốn dùng thư viện biểu đồ thì hỏi chủ project, tải cục bộ (app
  chạy không cần Internet).

### 5.7 Màn hình Cài đặt

| Nhóm | Mục | Ghi chú |
|---|---|---|
| Camera | webcam mặc định, độ phân giải xin webcam (720p / 1080p), nút "Thử webcam" | lưu `configs/desktop.yaml` bản người dùng |
| Xử lý | thiết bị: Tự động / GPU / CPU | hiển thị GPU phát hiện được; đổi thì cần khởi động lại nguồn |
| Dữ liệu | thư mục lưu, giữ dữ liệu N ngày, nút "Xóa dữ liệu cũ hơn N ngày" (hỏi xác nhận), nút "Mở thư mục dữ liệu" | không xóa khi chưa xác nhận |
| Cảnh báo | âm thanh khi có sự kiện mới (bật / tắt) | |
| Mô hình (chỉ đọc) | tên trọng số detector, ngày, sha256 ngắn; ngưỡng chính lấy từ `configs/pipeline.yaml` | không cho sửa trong app |

### 5.8 Màn hình Giới thiệu

Tên đề tài, nhóm, phiên bản app, commit, mô hình (C5-s960), danh sách nguồn dữ liệu và giấy phép (lấy từ
`data/raw/*/README.md`), đường dẫn hướng dẫn sử dụng.

### 5.9 Hành vi khác

- Đóng cửa sổ khi đang chạy nguồn: hỏi "Đang giám sát. Dừng và thoát?"; đồng ý → dừng, đóng phiên, thoát.
- Mất webcam giữa chừng: hiện lỗi trên màn hình Giám sát, phiên đóng như bấm Dừng (đã có ở `LiveCamera`).
- Phím tắt: `Space` Bắt đầu / Tạm dừng, `Esc` đóng chi tiết, `Ctrl+E` xuất CSV, `F1` Trợ giúp, `F11` toàn màn hình; danh sách phím tắt có trong trang Trợ giúp.

### 5.10 Kỹ thuật giao diện

- Giữ **HTML / CSS / JS thuần** (stack đã chốt trong `CLAUDE.md`), không dùng công cụ build.
- Tách `dashboard/index.html` thành `index.html` + `css/app.css` + `js/` (ES module: `api.js` gọi API, `monitor.js`,
  `events.js`, `stats.js`, `settings.js`, `ui.js` thành phần chung). Giữ được chạy như bản web (trình duyệt) để test.
- Mọi gọi API qua `api.js` dùng `window.location.origin` (đã có `API_BASE`), không viết cứng cổng.
- Hộp thoại chọn / lưu file của Windows: gọi qua API `js_api` của pywebview (`window.pywebview.api.pick_video()`,
  `save_file()`); khi chạy trong trình duyệt thường thì ẩn hoặc dùng `<input type="file">`.

## 6. Đóng gói và cài đặt

- **PyInstaller, chế độ thư mục (onedir)**, không dùng một file đơn (PyTorch rất lớn, một file đơn mở rất chậm vì phải giải
  nén mỗi lần chạy). Kèm: code `src/`, `backend/`, `dashboard/`, `configs/`, trọng số đang dùng (detector C5-s960, pose
  `yolo11n-pose.pt`, các bộ phân loại bộ phận trong `configs/pipeline.yaml`), không kèm dữ liệu train, video.
- **Bộ cài:** nén thư mục thành bộ cài (Inno Setup hoặc ZIP tự giải nén; công cụ nào cũng phải hỏi chủ project trước), tạo
  lối tắt Desktop / Start Menu, gỡ cài đặt được.
- **Kích thước:** PyTorch bản CUDA rất lớn, bộ cài có thể vài GB (**chưa đo**). Đo ở mốc M6; nếu quá lớn, cân nhắc xuất
  ONNX / TensorRT — chỉ làm khi chủ project đồng ý, và phải đo lại tốc độ, độ chính xác so với bản PyTorch.
- WebView2 có sẵn trên Windows 10/11 cập nhật; bộ cài kiểm tra và báo nếu thiếu.
- **Đặt `YOLO_AUTOINSTALL=False`** trong app (Ultralytics tự cài gói khi thiếu, không được để xảy ra trên máy người dùng).
- Gói cần thêm (hỏi trước, khóa phiên bản): `pywebview`, `pyinstaller`; có thể `filelock` nếu chưa có.

## 7. Các phần để thành một sản phẩm phần mềm đầy đủ

Ngoài chức năng chính, app cần các phần sau. Cột "Mức": **Bắt buộc** = phải có khi nộp; **Nên có** = làm nếu kịp;
**Ghi chú** = không làm, chỉ ghi rõ trong tài liệu.

| Nhóm | Nội dung | Mức |
|---|---|---|
| **Kiểm tra lúc mở app** | Màn hình chờ (logo, "Đang nạp mô hình…", thanh tiến độ, vì nạp mô hình mất vài giây); kiểm tra GPU, WebView2, quyền ghi thư mục dữ liệu, webcam; lỗi nào thì báo rõ, vẫn mở được app ở chế độ hạn chế | Bắt buộc |
| **Yêu cầu hệ thống** | Ghi trong hướng dẫn và trang Giới thiệu: Windows 10/11 64 bit, RAM, dung lượng đĩa (đo ở M6), GPU NVIDIA khuyến nghị, webcam 720p | Bắt buộc |
| **Quyền camera Windows** | Windows có thể chặn ứng dụng desktop dùng webcam (Cài đặt > Quyền riêng tư > Camera); khi mở webcam lỗi, thông báo chỉ đúng chỗ bật | Bắt buộc |
| **Phiên bản** | Số phiên bản `MAJOR.MINOR.PATCH` (bắt đầu 1.0.0), hiện ở thanh tiêu đề, Giới thiệu, tên bộ cài; ghi kèm commit git và tên trọng số detector | Bắt buộc |
| **Nhật ký phiên bản** | `desktop/CHANGELOG.md`: mỗi bản ghi đã thêm / sửa gì | Bắt buộc |
| **Ghi log** | Log xoay vòng trong `%LOCALAPPDATA%\PPEMonitor\logs\` (giữ 7 file); mức INFO; không ghi ảnh, không ghi thông tin cá nhân | Bắt buộc |
| **Báo lỗi** | Lỗi không lường trước: hộp thoại "Đã xảy ra lỗi", nút "Lưu gói chẩn đoán" (ZIP: log, phiên bản, cấu hình, thông tin GPU; không có ảnh, video) để gửi nhóm phát triển | Bắt buộc |
| **Phục hồi** | App bị tắt đột ngột: lần mở sau đóng các phiên còn mở với lý do riêng (`app_crash_recovered`), không để sự kiện "mở" mãi | Bắt buộc |
| **Một phiên bản chạy** | Mở app lần hai → đưa cửa sổ đang mở lên trước, không chạy tiến trình thứ hai | Bắt buộc |
| **Dữ liệu và riêng tư** | Dữ liệu chỉ lưu trên máy, không gửi đi đâu, không cần Internet; trang "Dữ liệu và quyền riêng tư" trong Trợ giúp: lưu gì (sự kiện, ảnh minh chứng), ở đâu, bao lâu (theo cài đặt), xóa thế nào; mã theo dõi không phải danh tính (NFR-04) | Bắt buộc |
| **Sao lưu / khôi phục** | Cài đặt > Dữ liệu: "Sao lưu" (ZIP gồm DB + minh chứng + cấu hình người dùng), "Khôi phục" (hỏi xác nhận, sao lưu bản hiện tại trước khi ghi đè) | Nên có |
| **Dọn dữ liệu** | Tự xóa sự kiện / ảnh cũ hơn N ngày (cài đặt, mặc định tắt); cảnh báo khi đĩa còn dưới 2 GB | Nên có |
| **Cài đặt / gỡ** | Bộ cài có tên app, biểu tượng, vị trí cài, lối tắt; gỡ cài đặt hỏi có giữ dữ liệu người dùng không; cài đè bản mới giữ dữ liệu | Bắt buộc |
| **Biểu tượng, nhận diện** | Biểu tượng app (.ico nhiều cỡ), tên app (chốt với chủ project), màn hình chờ, tiêu đề cửa sổ | Bắt buộc |
| **Chữ ký số** | Bộ cài chưa ký sẽ bị Windows SmartScreen cảnh báo "Unknown publisher"; hướng dẫn ghi cách bấm "More info > Run anyway". Chữ ký số tốn phí, không làm trong khóa luận | Ghi chú |
| **Giấy phép, ghi nguồn** | `LICENSES.txt` trong bộ cài: giấy phép các thư viện (Ultralytics AGPL-3.0, PyTorch, OpenCV, FastAPI, pywebview…) và bộ dữ liệu (lấy từ `data/raw/*/README.md`); trang Giới thiệu liệt kê. **Lưu ý:** Ultralytics là AGPL-3.0, phát hành app kèm Ultralytics phải công khai mã nguồn theo AGPL; repo đã công khai, ghi rõ đường dẫn | Bắt buộc |
| **Khả năng tiếp cận** | Dùng được bằng bàn phím (Tab, Enter, phím tắt); độ tương phản chữ đủ đọc; không chỉ dùng màu để truyền tin | Bắt buộc |
| **Cập nhật** | Không tự cập nhật qua mạng; bản mới = cài đè bộ cài mới (giữ dữ liệu), ghi trong hướng dẫn | Ghi chú |
| **Tài liệu** | (1) Hướng dẫn sử dụng (PDF + trang Trợ giúp trong app) cho người giám sát; (2) Hướng dẫn cài đặt; (3) `desktop/README.md` cho người phát triển: chạy từ mã nguồn, đóng gói, kiểm thử, phát hành | Bắt buộc |
| **Kiểm thử chấp nhận** | Một người chưa từng dùng (không phải người làm app) tự cài và dùng theo hướng dẫn 4 việc: bật webcam, tắt kính, chạy video, xuất CSV; ghi lại chỗ vướng, sửa trước khi nộp | Bắt buộc |
| **Theo dõi lỗi** | Ghi lỗi tìm được và cách sửa vào GitHub Issues (hoặc bảng trong `desktop/README.md`) | Nên có |

## 8. Mốc và kiểm tra (khoảng 9–10 ngày làm việc, xong trước 28/11 để còn viết báo cáo)

| Mốc | Việc | Kiểm tra để coi là xong |
|---|---|---|
| M0 (0,5 ngày) | Đọc tài liệu, chạy được bản web từ mã nguồn (`backend/README.md`); hỏi duyệt cài `pywebview`, `pyinstaller`; chốt tên app, biểu tượng | bản web chạy camera; danh sách gói được duyệt |
| M1 (1 ngày) | `desktop/main.py`, `desktop/paths.py`, `configs/desktop.yaml`: cửa sổ app, backend chạy nền, cổng tự chọn, đóng app dừng sạch, một phiên bản chạy, màn hình chờ; đóng gói thử bản rỗng | mở / đóng app 5 lần, không còn tiến trình python sót; bản đóng gói rỗng chạy được |
| M2 (1,5 ngày) | Tách dashboard thành `css/`, `js/`; bố cục 6 mục, thanh trạng thái; màn hình Giám sát với webcam; **khối PPE bắt buộc** đầy đủ (mục 5.3) và chú thích | mọi chức năng bản web còn chạy; test hiện có qua; bật / tắt từng PPE, tắt hết, mẫu nhanh đúng như mục 5.3 |
| M3 (1,5 ngày) | Nguồn file video (mục 4.1), tạm dừng / tiếp tục, tiến độ | video4 chế độ nhanh: số sự kiện, PPE thiếu khớp `05_run_video.py`; test mới qua |
| M4 (1 ngày) | Màn hình Sự kiện (lọc, phân trang, chi tiết), xuất CSV / ZIP, Thống kê | CSV mở đúng tiếng Việt trong Excel; số dòng khớp bộ lọc |
| M5 (1,5 ngày) | **Trợ giúp** (nút "!", tooltip, hướng dẫn lần đầu, trang Trợ giúp, FAQ); Cài đặt, Giới thiệu; log, báo lỗi, phục hồi sau khi tắt đột ngột | mọi khối có nút "!"; F1 mở Trợ giúp; tắt app bằng Task Manager rồi mở lại: không còn phiên mở |
| M6 (1 ngày) | Đường dẫn dữ liệu `%LOCALAPPDATA%`; đóng gói PyInstaller, bộ cài, gỡ cài đặt, `LICENSES.txt`, `CHANGELOG.md`; đo kích thước | cài / gỡ / cài đè trên máy dev, dữ liệu giữ đúng lựa chọn |
| M7 (1 ngày) | Thử trên **máy Windows khác chưa cài Python**; đo FPS trong app; kiểm thử chấp nhận với một người chưa dùng; sửa lỗi | 4 việc của kiểm thử chấp nhận làm được; số FPS ghi lại |
| M8 (0,5 ngày) | Hướng dẫn sử dụng (PDF) có ảnh chụp màn hình, hướng dẫn cài đặt; cập nhật bảng FR (`outputs/results/close_eval/final/fr_table.md`); phát hành 1.0.0 | chủ project duyệt |

## 9. Kiểm thử

- **Tự động:** `pytest` toàn bộ (hiện 195 test qua) + `tests/test_desktop.py` cho API mới (nguồn file với video ngắn tự
  tạo bằng OpenCV, không dùng video đánh giá; xuất CSV; settings; phục hồi phiên sau khi tắt đột ngột).
- **Thủ công (checklist trong `desktop/README.md`):** mở app; chọn webcam; tắt / bật từng PPE khi đang chạy; tắt hết PPE
  (hỏi xác nhận, không còn chữ); chọn mẫu nhanh; chạy file video thời gian thực và nhanh; tạm dừng / tiếp tục; dừng giữa
  chừng; rút webcam khi đang chạy; tắt quyền camera của Windows; đóng app khi đang chạy; tắt app bằng Task Manager; mở app
  lần hai; xuất CSV / ZIP; sao lưu / khôi phục; mọi nút "!" và F1; chỉ dùng bàn phím; máy không có GPU (CPU).
- **Hiệu năng:** đo FPS xử lý, độ trễ khung trong app so với bản web (cùng máy, cùng video4), không được chậm hơn rõ rệt;
  ghi số thật, không ước lượng. Mốc chấp nhận của demo: ≥ 20 khung/giây, p95 ≤ 100 ms (kế hoạch C5, 17/11/2026).
- **Không dùng** video đánh giá cuối, holdout hay Pictor-PPE để chỉnh gì trong app.

## 10. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Bộ cài quá lớn (PyTorch CUDA) | đo ở M6; thử loại bớt thư viện không dùng; ONNX chỉ khi chủ project đồng ý và đo lại |
| PyInstaller thiếu file của Ultralytics / torch khi đóng gói | thêm `hiddenimports`, `datas` trong `.spec`; đóng gói thử sớm (M1) |
| Máy khác thiếu driver NVIDIA / CUDA không khớp | tự rơi về CPU, báo rõ trên thanh trạng thái |
| Chạy file video làm sai thời gian sự kiện | đọc tuần tự, thời gian theo khung, kiểm khớp với `05_run_video.py` (M3) |
| Sửa nhầm phần nhận diện | review mọi thay đổi trong `src/ppe/`, `configs/pipeline.yaml` trước khi gộp |
| Trễ hạn | ưu tiên: M1 → M2 → M3 → M6 → M7 → phần bắt buộc của M5 (nút "!", trang Trợ giúp, phục hồi) → M4; phần "Nên có" ở mục 7, Thống kê nâng cao, bấm chọn người, âm thanh có thể bỏ |

## 11. Câu hỏi còn mở (hỏi chủ project khi tới mốc)

1. Tên app và biểu tượng (M0).
2. Công cụ tạo bộ cài: Inno Setup hay ZIP tự giải nén (M6).
3. Có cần bản CPU riêng nhẹ hơn không (sau khi đo kích thước ở M6).
4. Thư viện biểu đồ cho màn hình Thống kê, nếu SVG thuần không đủ.
5. Các mẫu PPE nhanh (mục 5.3) có đúng thực tế nghề nghiệp không.

## 12. Quy trình làm việc, Git và Pull Request

### 12.1 Nhánh

```
main ── (bản ổn định; chỉ gộp khi chủ project đồng ý)
 └─ exp/ppe6 ── (chủ project: mô hình C6, đánh giá, báo cáo)
      └─ feat/desktop ── (thành viên làm app: mọi việc trong tài liệu này)
```

- Lấy về: `git fetch origin` rồi `git switch feat/desktop` (nhánh đã có sẵn tài liệu này).
- **Không commit thẳng** vào `exp/ppe6`, `main`. Không `push --force` lên nhánh đã chia sẻ.
- **Cập nhật từ `exp/ppe6` ít nhất mỗi 2 ngày và trước khi mở PR**, bằng `git merge origin/exp/ppe6` (không rebase nhánh đã
  push), để luôn chạy với mô hình mới nhất; chạy lại `pytest` sau mỗi lần cập nhật.
- Có thể tách nhánh con cho từng mốc (`feat/desktop-m3-video-file`) rồi mở PR vào `feat/desktop`; hoặc làm thẳng trên
  `feat/desktop` với commit nhỏ. Chọn một cách và giữ nguyên.

### 12.2 Phân vùng file để tránh xung đột

| Ai sửa | File |
|---|---|
| Chủ project (nhánh `exp/ppe6`) | `src/ppe/`, `configs/pipeline.yaml`, `configs/ppe6.yaml`, `configs/train.yaml`, `scripts/0[1-4]*`, `docs/experiments/` |
| Thành viên làm app (`feat/desktop`) | `desktop/`, `configs/desktop.yaml`, `dashboard/`, `backend/` (trừ phần nhận diện), `tests/test_desktop.py`, tài liệu app |
| Phải báo trước khi sửa | `backend/live.py`, `backend/app.py`, `backend/db.py` (cả hai bên có thể đụng), `requirements*.txt`, `README.md` gốc |

### 12.3 Commit

- Mỗi commit một việc, chạy được, test qua. Không gộp "sửa nhiều thứ" vào một commit.
- Thông điệp tiếng Việt, dòng đầu ≤ 72 ký tự, dạng `<phạm vi>: <việc đã làm>`; thân giải thích vì sao nếu cần. Ví dụ:
  `desktop: mở cửa sổ pywebview, backend chạy nền ở cổng tự chọn`,
  `backend: nguồn file video đọc tuần tự, thời gian theo khung`,
  `dashboard: khối PPE bắt buộc có chú thích và mẫu nhanh`.
- **Không commit:** trọng số (`*.pt`), video, ảnh minh chứng, `*.db`, bộ cài, thư mục `build/`, `dist/` của PyInstaller
  (thêm vào `.gitignore` ở M1), log, thông tin cá nhân.

### 12.4 Pull Request

- Mở PR **sớm ở dạng Draft** ngay sau commit đầu (M1), cập nhật dần; chuyển "Ready for review" khi xong mốc.
- **Một PR cho mỗi mốc** (hoặc nhóm mốc nhỏ), không dồn cả app vào một PR cuối; PR cuối `feat/desktop` → `exp/ppe6` khi
  xong M8, chủ project gộp sau khi đã gộp mô hình C6.
- Tiêu đề: `[desktop] M3: nguồn file video, tạm dừng / tiếp tục`.
- **Nội dung PR (chép mẫu dưới, điền đủ):**

```markdown
## Mục đích
Mốc M_ trong docs/desktop_app_plan.md: <một câu>.

## Thay đổi
- <file / thư mục>: <việc>
- ...

## Không thay đổi (xác nhận)
- [ ] Không sửa src/ppe/, configs/pipeline.yaml, configs/ppe6.yaml, trọng số
- [ ] Không thêm gói mới / gói mới đã được chủ project duyệt và khóa phiên bản: <tên==phiên bản>

## Kiểm thử
- [ ] `pytest` toàn bộ: <số> passed (dán dòng kết quả)
- [ ] Test mới: <tên test>
- [ ] Thủ công trên máy <cấu hình>: <các bước đã làm, kết quả>
- [ ] Số đo (nếu có): FPS, p95, kích thước bộ cài — số thật, ghi cách đo

## Ảnh chụp màn hình / video ngắn
<trước / sau cho mọi thay đổi giao diện>

## Việc còn lại, rủi ro
- ...

## Tài liệu
- [ ] README thư mục liên quan đã cập nhật
- [ ] desktop/CHANGELOG.md đã thêm mục
```

- **Điều kiện được gộp (Definition of Done):** đạt cột "Kiểm tra" của mốc ở mục 8; `pytest` qua toàn bộ; không có xung
  đột với `exp/ppe6`; README / CHANGELOG cập nhật; chủ project review và bấm duyệt. Người viết PR không tự gộp.
- **Review:** chủ project xem trong 1 ngày; góp ý ghi trực tiếp vào dòng code trên GitHub; người làm sửa bằng commit mới (không
  sửa lịch sử) và trả lời từng góp ý ("Đã sửa ở <commit>" hoặc lý do không sửa).

### 12.5 Báo cáo tiến độ

Cuối mỗi ngày làm việc, một tin nhắn ngắn: đã xong gì (link commit / PR), đang vướng gì, ngày mai làm gì. Vướng quá nửa
ngày ở một chỗ thì hỏi ngay, không chờ.

## 13. Chuẩn bị máy để bắt đầu (M0)

1. Cài Python 3.12, Git; clone repo, `git switch feat/desktop`.
2. Tạo môi trường và cài gói: theo `requirements.txt` (PyTorch bản CUDA 12.8 từ chỉ mục riêng, đã ghi trong file).
3. **Trọng số mô hình không có trong git**; chủ project gửi riêng gói `ppe_desktop_weights.zip`, giải nén ở **thư mục gốc
   repo** (giữ nguyên đường dẫn bên trong), rồi kiểm sha256:

| File | sha256 |
|---|---|
| `outputs/train/yolo11s_ppe6_c5_s960/weights/best.pt` (detector C5-s960) | `aeea881af38830569336219a87f8e2c4eef4366a31ed4761922605bc3d3bbebe` |
| `outputs/train/yolo11n_cls_parts_v2/weights/best.pt` (phân loại tay) | `a46924d05dbc095a97057de9fd70d5222230e25adb0b050c1e917048b1172f2d` |
| `outputs/train/yolo11n_cls_parts_v3/weights/best.pt` (phân loại bộ phận, kính) | `1317cb7d00919c789cb97a2784161cd14e9065d4ecb2c61958b31eaa4b62f48c` |
| `outputs/train/yolo11n_cls_parts_v4/weights/best.pt` (phân loại mũ, ủng) | `08d29990b43819b780ba89835ff5335186aca7e3ac804cb815caf9dee5017526` |
| `yolo11n-pose.pt` (pose) | `869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0` |

   Khi chủ project đổi mô hình (C6), sẽ gửi trọng số mới kèm sha256 và commit `configs/pipeline.yaml` trên `exp/ppe6`;
   app phải đọc đường dẫn trọng số từ cấu hình, không viết cứng.
4. Video để thử: chủ project gửi riêng; không đưa vào git. Không dùng video đánh giá cuối, holdout để chỉnh app.
5. Chạy `pytest` (phải qua toàn bộ), rồi chạy bản web theo `backend/README.md`, bật camera — xong M0.
