# b1_review — kiểm định dữ liệu kính bảo hộ cho B1 (25/11/2026)

- `to1_kiem_tung_hop.jpg/.csv`: 37 hộp kính của `goggles_safety` (29) và `goggles_workplace` (8), kiểm từng hộp.
- `to2_mau_kiem_dinh.jpg/.csv`: mẫu ngẫu nhiên 24 hộp `goggles_sg` và 24 hộp `goggles_ppes`.
- `quyet_dinh.csv`: `giu` = 1 là đưa vào train. **Cách ra quyết định**: Claude đưa gợi ý (máy) cho tờ 1 (25 hộp là kính bảo
  hộ: 3, 5, 6, 7, 10, 11, 13-18, 22, 26-37; còn lại kính thường hoặc kính râm) và đề xuất bỏ `goggles_ppes`; người dùng
  chọn "Đồng ý gợi ý, bỏ PPEs" ngày 25/11/2026. Đây là người dùng chấp nhận gợi ý của máy, không phải người dùng tự gán
  từng hộp; báo cáo ghi "nhãn gốc bộ dữ liệu / gợi ý của máy, người dùng duyệt".
