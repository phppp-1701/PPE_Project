# data/videos — Video kiểm thử

- Video lấy từ Internet, camera đặt cố định, cảnh xưởng hoặc công trường.
- `video_sources.csv`: mỗi video một dòng — `video_id`, `file`, `url` (link nguồn), `title`, `downloaded` (ngày tải), `role`, `notes`.
  - `role`: `chinh_tham_so` (video chỉnh tham số), `danh_gia` (đánh giá cuối, chỉ dùng để đo), `chay_thu` (chỉ chạy thử, không thuộc bộ đánh giá, vd. video cắt ghép), `chua_chia` (chưa quyết định).
  - Chia theo cả video: một video chỉ thuộc một nhóm; video đánh giá cuối không được dùng để chọn tham số.
- Nhãn CVAT của từng video đặt cùng tên với video.
- Video không bao giờ được dùng để huấn luyện YOLO.
- File video không đưa lên git (chỉ `README.md` và `video_sources.csv`).
