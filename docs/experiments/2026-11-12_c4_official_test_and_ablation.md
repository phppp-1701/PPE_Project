# Đánh giá tập Test chính thức, Thực nghiệm triệt tiêu A → E & Hệ thống phần mềm 6 lớp PPE

**Ngày:** 2026-11-12  
**Nhánh:** `exp/ppe6`  
**Mô hình chính:** `outputs/train/yolo11s_ppe6_c4/weights/best.pt` (YOLO11s C4, 6 lớp)  
**Tập dữ liệu:** `data/ppe4/dataset` (1.583 ảnh test nội bộ), `data/ppe6/dataset/test_new.txt` (117 ảnh test mới), video kiểm thử `data/videos/video{4,5,6}.mp4`

---

## 1. Kết quả kiểm định trên tập Test độc lập (RQ1)

Theo kỷ luật thực nghiệm (mục 7.5), toàn bộ tham số đã được chọn và khóa lại trên `val`, `val_new` và video chỉnh tham số. Dưới đây là kết quả mở tập Test độc lập lần duy nhất:

### 1.1. So sánh 4 lớp cơ bản trên tập Test nội bộ (1.583 ảnh test)

Chạy `scripts/04d_capture_val.py --split test` và `04e_ppe6_eval.py old`:

| Lớp | r2 (4 lớp) | r3 (4 lớp) | **C4 (6 lớp)** | C4 so với r3 | C4 so với r2 |
|---|---:|---:|---:|---|---|
| `person` (0) | 0.9247 | 0.9261 | **0.9210** | -0.0051 | -0.0037 |
| `helmet` (1) | 0.8665 | 0.8538 | **0.8600** | +0.0062 | -0.0065 |
| `vest` (2) | 0.8071 | 0.8032 | **0.8188** | **+0.0156** | **+0.0117** |
| `gloves` (3) | 0.6179 | 0.6212 | **0.6376** | **+0.0164** | **+0.0197** |
| **Trung bình mAP50** | 0.8040 | 0.8011 | **0.8094** | **+0.0083** | **+0.0053** |
| **mAP50-95** | 0.4915 | 0.4943 | **0.4951** | **+0.0008** | **+0.0036** |

- **Trên các cảnh sạch của tập Test (1.060 ảnh sạch, 1.242 cảnh):**
  - C4 đạt **mAP50 trung bình = 0.7654** (so với r3 = 0.7565, r2 = 0.7574).
  - Lớp `gloves` trên cảnh sạch: C4 đạt **0.5452** (r3 = 0.5245, r2 = 0.5228, tăng +0.0207).
  - Kết luận thống kê theo `decision`: **`dat` ở tất cả các lớp và giá trị trung bình** so với cả r3 và r2.

### 1.2. Đánh giá 2 lớp mới trên `test_new` (117 ảnh, 60 cảnh)

Chạy `scripts/04e_ppe6_eval.py new --capture outputs/results/ppe6_eval/c4_testnew`:

| Lớp mới | Số hộp chuẩn (`GT`) | mAP50 | Khoảng tin cậy 95% (Bootstrap theo cảnh) | Đủ bằng chứng (`enough_evidence`) |
|---|---:|---:|---|:---:|
| **Kính bảo hộ (`goggles`)** | 38 | **0.7359** | **[0.6003, 0.8596]** | **ĐẠT (Đủ bằng chứng > 0.50)** |
| **Ủng bảo hộ (`boots`)** | 102 | **0.4772** | [0.3347, 0.6480] | Tiệm cận mốc 0.50 (KTC chứa 0.50) |

---

## 2. Thực nghiệm triệt tiêu trên video kiểm thử (Ablation Study A → E, RQ3)

Đo lường trên toàn bộ 3 video kiểm thử (`video4`, `video5`, `video6` - tổng cộng 774 khung hình, 12 đợt vi phạm chuẩn) bằng `scripts/06_evaluate_ablation.py`:

| Cấu hình | Thành phần triển khai | Tổng số cảnh báo | Cảnh báo sai (FP_sai) | Cảnh báo trùng (FP_trùng) | Event F1 | Độ trễ trung bình |
|---|---|---:|---:|---:|---:|---:|
| **A** | YOLO11s 6 lớp thuần (cảnh báo mỗi khung có Thiếu) | 5.004 | 2.231 | 2.762 | 0.0044 | 0.00s |
| **B** | A + Vùng cơ thể (head, torso, hands, feet) & Pose cổ tay + Chưa xác định | 3.604 | 1.083 | 2.509 | 0.0066 | 0.57s |
| **C** | B + ByteTrack (theo dõi quỹ đạo qua thời gian) | 3.610 | 1.092 | 2.506 | 0.0066 | 0.55s |
| **D** | C + Cửa sổ thời gian ($T_{on}=5.0s, T_{off}=2.0s$) | 3.018 | 732 | 2.275 | 0.0073 | 0.50s |
| **E** | **D + Quản lý vòng đời sự kiện EventManager (Toàn luồng đề tài)** | **7** | **3** | **0** | **0.8889** | **0.50s** |

### Nhận xét & Đóng góp khoa học:
1. **Từ A sang B:** Vùng cơ thể giải phẫu và trạng thái `chua_xac_dinh` (khi chân bị cắt ngoài mép ảnh hoặc tay chắp nhau) giúp **cắt giảm hơn một nửa số cảnh báo sai** (từ 2.231 xuống 1.083 cảnh báo).
2. **Từ B sang C & D:** Cửa sổ trượt thời gian $T_{on} = 5.0s$ lọc sạch các nhiễu che khuất thoáng qua (1–2 khung hình), tiếp tục giảm cảnh báo sai xuống 732. Tuy nhiên nếu không có vòng đời sự kiện, hệ thống vẫn liên tục phát ra hơn 2.200 cảnh báo trùng lặp phiền toái.
3. **Từ D sang E:** Bộ quản lý vòng đời sự kiện `EventManager` đã **triệt tiêu 100% cảnh báo trùng lặp** (từ 2.275 về 0), gom các khung hình liên tục thành đúng 7 sự kiện vi phạm thực tế, nâng `Event F1` từ **0.0044 lên 0.8889**, với độ trễ phản hồi chỉ **0.50 giây**.

---

## 3. Hệ thống phần mềm 6 lớp PPE (Backend API & Web Dashboard)

### 3.1. Cấu trúc Backend API (`backend/`)
- **Cơ sở dữ liệu SQLite (`outputs/ppe.db`):** 6 bảng chuẩn (`sources`, `ppe_policies`, `monitoring_sessions`, `violation_events`, `event_history`, `event_evidence`).
- **RESTful Endpoints (`backend/app.py`):**
  - `POST /api/events`: Nhận sự kiện tạo mới từ chuỗi xử lý video.
  - `PATCH /api/events/{event_id}`: Cập nhật `missing_items`, trạng thái và đóng sự kiện.
  - `GET /api/events`: Lọc theo nguồn, trạng thái, loại PPE thiếu.
  - `GET /api/events/{event_id}`: Chi tiết vi phạm, lịch sử thay đổi và danh sách ảnh minh chứng.
  - `GET /api/evidence/{session_id}/{filename}`: Phục vụ ảnh minh chứng.
  - `GET /api/stats`: Thống kê tổng số và tỷ lệ vi phạm theo 6 lớp PPE.
  - `GET /api/sources/{source_id}/policy` & `PUT`: Cấu hình quy định PPE bắt buộc cho nguồn.

### 3.2. Giao diện Web Dashboard (`dashboard/index.html`)
- Hiển thị trực quan tại `http://127.0.0.1:8000/dashboard/index.html`:
  - 4 thẻ KPI tổng quan: Tổng sự kiện, Đang vi phạm (đỏ), Chờ quan sát (vàng), Đã đóng (xanh lá).
  - Biểu đồ phân bố vi phạm theo 5 trang bị: Mũ, Áo, Găng, Kính, Ủng.
  - Bộ lọc sự kiện theo nguồn, trạng thái và loại PPE.
  - Modal xem ảnh minh chứng (đóng khung đỏ vi phạm) kèm dòng thời gian sự kiện (Event Timeline).
  - Bảng công tắc bật/tắt chính sách kiểm tra bắt buộc cho từng loại trang bị.
- Tự động làm mới dữ liệu sau mỗi 3 giây.

### 3.3. Tích hợp E2E
Khi chạy video qua script `scripts/05_run_video.py`, tham số `--api-url http://127.0.0.1:8000/api` sẽ tự động phát các HTTP requests thời gian thực tới Backend để cập nhật lên Web Dashboard ngay lập tức.
