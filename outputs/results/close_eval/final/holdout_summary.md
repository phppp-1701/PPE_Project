# Đánh giá cuối trên holdout: tóm tắt (16/11/2026)

Chạy **một lần duy nhất** theo cho phép của người dùng, sau khi kiểm manifest đạt (commit nguồn `0a47b91`, HEAD
`3a4c44a`). 8 video niêm phong (h1-h5, h7-h9; h6 loại trước mọi dự đoán). **Nhãn máy qua hai lượt, chưa người kiểm
định**, nên mọi số dưới đây là "so với nhãn máy". Không chỉnh tham số, logic sau khi xem kết quả. Chi tiết:
`holdout/results.md`, `holdout/results.json` (số đếm). `holdout/transitions.csv` có nhãn từng khung nên **chỉ giữ ở
máy, không đưa lên Git**.

Đơn vị: khung-người. Độ đúng = (Có đúng + Thiếu đúng) / (nhãn Có + nhãn Thiếu), cùng công thức với kiểm hồi quy 13 video.

| PPE | Bản 4: độ đúng | Bản cuối: độ đúng | Ghi chú |
|---|---|---|---|
| Mũ | 2.046 / 3.247 = **0,630** | 1.761 / 3.247 = **0,542** | **Giảm**. Chi tiết bên dưới |
| Áo | 1.656 / 2.374 = 0,698 | 0,698 | Giống hệt |
| Găng | 293 / 589 = 0,497 | 0,497 | Giống hệt |
| Kính | 724 / 1.371 = **0,528** | 1.018 / 1.371 = **0,743** | **Tăng** (F1 kính theo mắt). Có đúng 127 → 421, báo thiếu oan 115 → 92, Có → Chưa xác định 348 → 77 (h9) |
| Ủng | 35 / 141 = 0,248 | 0,248 | Giống hệt; ủng là điểm yếu (h2: 88 khung Thiếu thành Chưa xác định, 18 khung báo Có sai) |

## Mũ: bản cuối ít báo sai nhưng bỏ sót người thiếu mũ

| Mũ (khung-người) | Bản 4 | Bản cuối |
|---|---|---|
| Thiếu đúng (nhãn Thiếu 853) | 241 | **15** |
| Báo thiếu oan (nhãn Có, hệ thống Thiếu) | 274 | **12** |
| Báo Có sai (nhãn Thiếu, hệ thống Có) | 145 | 113 |
| Thiếu → Chưa xác định | 467 | 725 |
| Có → Chưa xác định | 307 | 628 |

- **h2:** 220 khung người không mũ (nhãn Thiếu) bản 4 báo Thiếu đúng, bản cuối thành Chưa xác định. Sự kiện #1 của h2
  không còn mũ trong `missing_items`. Đây là **bỏ sót vi phạm thật**, tác dụng phụ đáng kể nhất.
- **h3:** 262 khung có mũ (nhãn Có) bản 4 báo Thiếu oan, bản cuối thành Chưa xác định: hết cảnh báo sai.
- **h9:** người không mũ, bản 4 báo Có sai 145 khung, bản cuối 113 (32 khung C2 chuyển sang Chưa xác định).
- **h1, h7:** 32 và 27 khung có mũ đúng thành Chưa xác định.

**Nguyên nhân (suy từ logic code, chưa chạy riêng để xác nhận):** ở h2, h3, h7, h8 các khung đổi là Thiếu → Chưa xác
định khi không có hộp mũ. C2 chỉ xét khi có hộp mũ, F1 chỉ đổi kính, nên thay đổi này đến từ **D (nhìn từ sau, không
có hộp mũ → Chưa xác định)**. D được thiết kế để tránh báo thiếu oan khi thấy gáy (đúng ở h3), nhưng ở h2 nó cũng chặn
báo thiếu cho người không mũ. Chưa kiểm h2 có thật là cảnh nhìn từ sau hay D bật nhầm (vai đảo do pose sai). Muốn biết
chắc phải chạy chẩn đoán trên h2 (bật, tắt D). Việc này chỉ để giải thích, không được dùng để chỉnh tham số.

Trên 13 video phát triển, D làm báo thiếu oan 53 → 0 và không giảm độ đúng (`stepCD/`). Trên holdout, D cũng làm
báo thiếu oan 274 → 12 nhưng đồng thời làm mất 226 khung Thiếu đúng. Như vậy kết quả trên video phát triển không
tổng quát hết sang holdout.

## Sự kiện

Số sự kiện giống nhau ở mọi video (bản 4 và bản cuối đều 12). Khác ở nội dung: h2 #1 mất mũ, h3 #1 mất mũ (đúng, vì
nhãn là Có mũ), h7, h8, h9 chỉ khác mốc thời gian trong `missing_history`. Holdout không có nhãn sự kiện nên **không
tính Event F1**. Tất cả sự kiện đóng ở dạng `session_ended_unverified` vì video kết thúc khi vi phạm còn tiếp diễn.

## Kết luận trung thực cho báo cáo

- Bản cuối **không tốt hơn bản 4 về mũ** trên holdout (0,630 → 0,542 so với nhãn máy). Bản cuối giảm mạnh cảnh báo sai
  (274 → 12) nhưng bỏ sót phần lớn người thiếu mũ (241 → 15 khung Thiếu đúng).
- Bản cuối **tốt hơn rõ về kính** (0,528 → 0,743). Áo, găng, ủng không đổi.
- Bản cuối được chọn trước khi xem holdout. Theo quy tắc đóng băng, không đổi bản sau khi xem kết quả. Báo cáo cả hai
  bản và ghi D là giới hạn: đánh đổi giữa cảnh báo sai và bỏ sót.
