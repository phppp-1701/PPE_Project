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

## Kết quả

(điền sau khi chạy)
