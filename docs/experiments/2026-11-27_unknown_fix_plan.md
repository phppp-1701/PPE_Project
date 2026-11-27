# Sửa "Chưa xác định" sai của áo — 27/11/2026

Viết trước khi chạy. Người dùng giao (27/11/2026): tối ưu "Chưa xác định" (CXĐ); đồng ý hướng đề xuất: sửa áo theo
ngoại lệ, mũ ghi vào Hạn chế.

## Chẩn đoán (đã chạy, `outputs/results/close_eval/diag_unknown/`, `scripts/06d_diagnose_unknown.py`)

Chỉ video chỉnh tham số 3-6 (nhãn người) và `kiem_thu_gan` 9-17 (nhãn máy, chỉ đo). Không chạy holdout.

- Holdout (đọc số đếm có sẵn `final2/holdout_check`, không dò lý do): CXĐ của găng, kính, ủng đúng với nhãn 0,92 / 0,90 /
  0,99; của mũ 0,26, áo 0,33.
- **Áo** (nhãn Có → CXĐ): 258 khung có hộp áo trong hộp người nhưng bị loại `outside` (tâm áo ngoài vùng thân cố định);
  188 trong đó người chạm mép dưới khung (đứng gần, bị cắt). Lỗi ở luật gán.
- **Mũ** (nhãn Có → CXĐ): quay lưng (D) 28 + 333 (video17, bộ phân loại vùng đầu phiếu `neg` sai), cổng khung xương 140
  (video4, người xa); detector không có hộp mũ. Bỏ luật sẽ thành báo thiếu oan; gốc ở detector → **Hạn chế**, không sửa.

## Thay đổi thử (V)

Bật `association.torso_strict` với đúng tham số F2 đã chọn trên val ngày 16/11/2026
(`outputs/results/pipeline_calib_val/assoc_pose.json`, `tham_so.F2`): `kp_conf 0.5, kx 1.259, ky0 -0.297, kh 0.123,
slope_max_deg 48.3, s_min 1.116, edge_frac 0.112`. Không chọn lại tham số.

**Đã biết trước (val 16/11):** F2 không đạt tiêu chí V3b (gán nhầm áo người phía sau bị bỏ sót 18 → 19 ở cắt 55%,
20 → 21 ở cắt 65%). Nếu bật là **ngoại lệ người dùng duyệt** (27/11/2026), ghi rõ trong báo cáo.

## Tiêu chí (khóa trước khi chạy)

Hồi quy video3-6 (nhãn người, `06b evaluate`, mốc = `configs/pipeline.yaml` hiện tại, `28ad782` + chẩn đoán):

1. Áo: "Có đúng" tăng.
2. Áo: "báo Có sai" không tăng; "báo Thiếu oan" không tăng.
3. Mũ, găng, kính, ủng: mọi số không đổi (V chỉ chạm áo).
4. Sự kiện: số sự kiện mỗi video không đổi, hoặc chỉ bớt mục áo của sự kiện ứng với khung nhãn Có áo.

Đạt cả 4 → bật V trong `configs/pipeline.yaml`, chạy lại holdout (ghi "kiểm tra sau sửa, không mù"; số chính thức vẫn
16/11) và `kiem_thu_gan` 9-17 (chỉ báo cáo). Không đạt → không bật, ghi Hạn chế.

## Kết quả V (27/11/2026): không đổi gì

`outputs/results/close_eval/stepV/dev36/`: mọi số, mọi PPE, mọi sự kiện video3-6 giống hệt bản hiện tại → không bật.
Thăm dò (scratchpad, video3-5, chỉ đọc): hộp áo bị loại `outside` đều do **lệch ngang** (u trung vị 0,29 video4; 0,73
video5; 0,76 video3; vùng thân x 0,309-0,665), chiều dọc đúng. Xem ảnh: hộp người bị **tay dang ra** kéo rộng (bắt tay,
ngồi xổm vươn tay), vùng thân theo tỉ lệ nằm giữa hộp nên lệch khỏi thân thật. B2 cố ý không nới ngang nên không có tác dụng.

## V2 — vùng thân đặt theo hai vai (ghi trước khi code và chạy)

`association.torso_shift {kp_conf, kx}`: khi `shoulder_geometry` (hai vai >= kp_conf, vai trong hộp người, hông thấp hơn
vai nếu thấy) hợp lệ, thêm vùng R: ngang [mx - kx·sw, mx + kx·sw] (mx trung điểm vai, sw bề rộng vai), dọc giữ như vùng
thân cũ, cắt theo hộp người; tâm áo trong vùng cũ hoặc R đều là ứng viên (khoảng cách chuẩn hóa nhỏ hơn được lấy). Tham số:
`kp_conf 0.5`, `kx 1.259` (= `kx` của B2/F2 chọn trên val 15-16/11/2026). Không chọn tham số mới.

Tiêu chí V2 (khóa): như tiêu chí 1-4 ở trên trên video3-6 (nhãn người), thêm (5) "Có mới trên người không có nhãn" của áo
không tăng (chặn gán áo cho người không có trong nhãn). Chưa đo V3b trên val (chưa có chế độ 05a cho V2; ghi rõ là giới hạn).
Đạt → bật, chạy lại holdout ("kiểm tra sau sửa, không mù") và 9-17 (chỉ báo cáo).

## Kết quả V2 (27/11/2026), `outputs/results/close_eval/stepV/dev36_V2/`

| Áo, video3-6 | base | V2 |
|---|---|---|
| Có đúng / 2.630 | 2.430 | **2.506** |
| Thiếu đúng / 1.043 | 1.002 | 1.001 |
| Báo thiếu oan | 48 | 47 |
| Báo Có sai | 3 | **4** |
| Có → CXĐ | 114 | **39** |

Theo video: video4 Có→CXĐ 34 → 5, video5 66 → 20, video3 +1 Có đúng, video6 không đổi. Mũ, găng, kính, ủng giống hệt.
Sự kiện: số sự kiện giống ở cả 4 video; video3 #5 chỉ lệch mốc bỏ mục áo trong `missing_history` 39,840 → 39,806 s.
Có mới trên người không có nhãn: 0.

Áp tiêu chí: (1) đạt; (2) **không đạt**: báo Có sai 3 → 4 (một khung, video3 f1152, nhãn người 5 không áo nhận Có;
cùng khung người 6 có áo từ Thiếu oan thành Có đúng; đây cũng là khung đã làm B1 không đạt 15/11); báo thiếu oan đạt;
(3) đạt; (4) đạt; (5) đạt. → Theo tiêu chí đã khóa: **không đạt**, chờ người dùng quyết định (ngoại lệ hay không).

Người dùng (27/11/2026): không bật V2, "phân tích và tìm phương án khác để cải thiện".

## V3 — V2 thêm cổng cỡ áo (ghi trước khi code và chạy)

Phân tích (scratchpad, chỉ đọc, video3-5 chỉnh tham số): f1152 video3 hộp người 5 gộp hai người (người trước không áo,
người sau có áo không được phát hiện riêng); hai "vai" thuộc hai người nên sw phình: rộng áo / sw 0,90, sw / rộng hộp
người 0,67. 79 áo V2 ghép đúng (video4, 5): rộng áo / sw 1,46-2,90 (p5-p95), sw / rộng hộp 0,24-0,41.

V3: như V2, chỉ dùng vùng theo vai khi rộng hộp áo >= `s_min` x sw, `s_min` 1,116 = cổng cỡ áo G5 của B2 chọn trên val
15/11/2026 (`pipeline_calib_val/torso_strict.json`). Không chọn ngưỡng mới. Tiêu chí: như V2 (1-5), video3-6.
