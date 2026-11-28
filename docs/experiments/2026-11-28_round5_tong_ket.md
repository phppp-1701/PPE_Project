# Round5 — tổng kết (28/11/2026)

Kế hoạch, tiêu chí khóa trước, nhật ký từng thử nghiệm: `docs/experiments/2026-11-28_round5_plan.md`. Mốc: cấu hình cuối 4
(tag `cuoi4` = `2f373a9`). Bản cải tiến **r5 = cuối 4 + P3** (`part_cls.run_on_new_track: true`), nay là `configs/pipeline.yaml`
trên nhánh `exp/round5`. Kết quả: `outputs/results/round5/final/`, `outputs/results/event_eval_2/{cuoi4,r5}/`.

## Bảng so sánh

| RQ | Chỉ số | Cuối 4 | r5 | Chênh |
|---|---|---|---|---|
| RQ1 | mAP@0,5 test (người/mũ/áo/găng/kính/ủng) | 0,923 / 0,855 / 0,821 / 0,718 / 0,756 / 0,596 | như cuối 4 (cùng c6_ft, test không chạy lại) | 0 |
| RQ2 | Ủng holdout: Accuracy / Coverage / Cond. Acc. | 0,532 / 0,553 / 0,962 | **0,858 / 0,858 / 1,000** | +0,326 / +0,305 |
| RQ2 | Ủng holdout: false missing / false present | 0 / 3 | 0 / **0** | −3 |
| RQ2 | Mũ holdout: Acc / Cov / Cond / FM / FP | 0,577 / 0,601 / 0,960 / 21 / 57 | như cuối 4 | 0 |
| RQ2 | Áo holdout | 0,775 / 0,826 / 0,938 / 119 / 2 | như cuối 4 | 0 |
| RQ2 | Găng holdout | 0,669 / 0,671 / 0,997 / 0 / 1 | như cuối 4 | 0 |
| RQ2 | Kính holdout | 0,751 / 0,839 / 0,895 / 121 / 0 | như cuối 4 | 0 |
| RQ2 | Video3-6 (mọi PPE) | — | giống hệt cuối 4 | 0 |
| RQ3 | **event_eval_2** (11 video, 17 sự kiện, độc lập): Precision / Recall / F1 / trễ | 0,733 / 0,647 / 0,688 / 1,15 s | **0,786** / 0,647 / **0,710** / 1,15 s | F1 +0,022 (bớt 1 cảnh báo sai) |
| RQ3 | event_eval_2: báo theo khung F1 / Recall | 0,004 / 0,765 | 0,004 / 0,765 | — |
| RQ3 | event_eval_2: KTC 95% F1 (E) ; hiệu E − theo khung | [0,38; 1,00] ; [0,38; 0,99] | [0,41; 1,00] ; [0,41; 0,99] | |
| RQ3 | event_eval (cũ, không độc lập) F1 | 0,696 | 0,696 | 0 |
| RQ3 | Ablation video4-6 E F1 | 0,870 | 0,870 | 0 |
| RQ4 | FPS gồm giải mã (07, cùng lượt): video3 / 4 / 5 / 6 | 26,48 / 15,64 / 17,29 / 18,21 | 26,36 / 15,46 / 16,45 / 18,24 | ≤ −0,84 |
| RQ4 | FPS gộp gồm giải mã ; P95 video cao nhất | 22,71 ; 92,8 ms | 22,47 ; 94,5 ms (lượt cao nhất 99,8) | −0,24 ; +1,7 |

Lượt đo tốc độ này máy chậm hơn lượt `final5` khoảng 10% (cuối 4 video4: 15,64 so với 17,22); so sánh chỉ trong cùng lượt. Mọi
video ≥ 15 FPS và P95 ≤ 100 ms ở cả hai cấu hình.

H3 trên tập độc lập event_eval_2: vế F1 **đạt** (KTC hiệu không chứa 0); vế Recall **không đạt** (E 0,647 so với theo khung
0,765, giảm 11,8 điểm > 5). 6/17 sự kiện bị sót ở cả hai cấu hình (không phân tích sau khi xem để chỉnh, theo quy tắc tập độc lập).

## Thử nghiệm và kết luận

| Thử nghiệm | Kết quả | Quyết định |
|---|---|---|
| U0 tách S3 | Z (zoom cách khung): ủng báo oan video3 +14; P (phân loại cách khung): lỗi ủng h2 | chẩn đoán |
| P2 (phân loại cách khung chỉ dùng chân của lần chạy gần nhất) | không đổi gì → giả thuyết sai | không bật |
| **P3** (phân loại chạy ngay khi có người mới) | video3-6 giống hệt; h2 lỗi `vua_thay_co` 43 → 0; holdout ủng phục hồi | **bật** |
| U1 (ROI chân pad 0,2, 320) | val ủng +0,003; video3-6 không đổi (người nhỏ, ROI không chạy) | không bật; U2 không làm |
| H0 (h9) | lỗi mũ Có sai là đầu trọc đeo kính + mặt nạ phòng độc; detector và bộ phân loại cùng sai, không phải gán nhầm | chẩn đoán |
| H1' (mũ conf < 0,66 cần bộ phân loại) | mũ FP 23 → 18 nhưng FM 12 → 20 (tổng lỗi tăng) | không bật; H1, H2 không làm (không nhắm đúng lỗi) |
| E1/E2 (RQ3) | không làm: không còn tập để chọn tham số độc lập với event_eval_2; người dùng cho phép giữ RQ3 | — |

Phần ủng video3 còn +14 khung báo oan do zoom cách khung (detector chỉ bắt ủng ở khung lẻ 89, 93, conf 0,29 / 0,17).

## Tái lập

`git checkout exp/round5`; `bash outputs/results/round5/final/run_all.sh` (cần video, nhãn, trọng số trên máy).
