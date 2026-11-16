# Sửa hạn chế sau đánh giá cuối (16/11/2026): M1 ủng, M2 mũ nhìn từ sau

Nhánh `exp/ppe6` (= `main` tại `e40e793`). Tài liệu này ghi **trước khi làm**: lý do, thiết kế, tiêu chí đã khóa, rồi
kết quả. Người dùng duyệt hướng và tiêu chí ngày 16/11/2026.

## 0. Bối cảnh và quy tắc báo cáo

- Đánh giá cuối trên holdout đã chạy **một lần** với bản cuối (bản 4 + D + C2 + F1), commit nguồn `0a47b91`,
  kết quả ở `outputs/results/close_eval/final/holdout_summary.md`. **Đó là số chính thức**, không thay.
- Sửa ở đây có động cơ từ việc xem video holdout (h2: đầu trọc quay lưng thành Chưa xác định; dép tông bị nhận là
  ủng). Vì vậy mọi lần chạy holdout sau khi sửa chỉ được ghi là **"kiểm tra sau khi sửa, không còn mù"**, không dùng
  làm kết quả khách quan. Không chọn tham số trên holdout hay video.
- Tham số chọn trên val; video 3-6, 9-17 chỉ để kiểm hồi quy.

## 1. Chẩn đoán (đã chạy, chỉ đọc)

**Ủng (h2 khung 56):** detector C4 cho hai hộp ủng (conf 0,52 và 0,24) trên dép tông; cả h2 có 21 hộp, conf trung vị
0,27. Tăng ngưỡng conf không loại được hộp 0,52. Bộ phân loại bộ phận có lớp `not_safety_foot` (dép, giày thường, chân
trần; xem tấm ghép ngẫu nhiên 40 ảnh train) nhưng ủng hiện không qua bước kiểm tra thứ hai (`part_cls.thresholds`
không có `boots`: bản 3 không đạt độ chính xác 0,90 ở t_neg 0,90).

**Mũ quay lưng:** h2: 233/282 khung D xác định quay lưng, bộ phân loại bỏ phiếu không mũ (1 − p từ 0,70 đến 0,87),
D chặn thành Chưa xác định. Video17 (53 khung D gỡ báo oan): mũ đen, tóc dài, bộ phân loại chắc không mũ với
1 − p trung vị **0,992**. Bộ phân loại chắc hơn khi sai (mũ đen) so với khi đúng (đầu trọc) nên **không có ngưỡng nào
tách được** (hướng "D2 theo ngưỡng" bị loại).

Nguyên nhân: tập train của bộ phân loại mũ (03y, nhìn từ sau theo luật D, độ sáng V HSV vùng hộp < 90 là tối):

| Nhìn từ sau | sáng | tối |
|---|---|---|
| có mũ | 476 | **10** |
| không mũ | 588 | 416 |

CHV train (chưa dùng cho bộ phân loại mũ): 432 mũ nhìn từ sau (xanh dương 65, đỏ 51, trắng 158, vàng 158), tối 9.

Tài liệu: nhầm tóc đen / mũ đen và góc nhìn từ sau được ghi nhận (Jia và cộng sự 2021, IET Image Processing; benchmark
mũ bảo hiểm xe máy); dò sai vật lạ vào lớp đã biết với độ tin cậy cao là bài toán tập mở (OpenDet, CVPR 2022).

## 2. M1: bác bỏ hộp ủng bằng bộ phân loại chân

**Thiết kế.** Khóa mới `part_cls.veto_boots: {t_veto: ...}` và `part_cls.weights_by_ppe.boots`. Khi bật: với người có ảnh
cắt chân, nếu **mọi** chân có ảnh cắt đều có 1 − p ≥ t_veto (p gộp theo `vote_window_s` như các PPE khác; bộ phân loại
rất chắc không phải ủng) thì bỏ các hộp ủng detector của người đó (has = False), như phủ quyết kính thường. Đòi mọi chân
(không phải một chân) vì tiêu chí val tính theo từng ảnh cắt; luật "mọi chân" không làm tỉ lệ bác bỏ nhầm theo người
vượt tỉ lệ theo ảnh cắt. Luật Thiếu của ủng giữ nguyên (luật cũ: vùng chân nhìn rõ mà không có
hộp). Không có dải "mâu thuẫn → Chưa xác định" (trên val, dải 0,5 ≤ 1 − p < t_veto chứa 14% ủng thật: quá đắt).
Hộp bị bác bỏ vẽ xám "Ung (bac bo)". Vắng khóa: như bản cuối.

**Chọn trên val** (`data/ppe6/parts/val`, ảnh cắt `safety_boot` 71, `not_safety_foot` 278): trọng số v3 hoặc v4 và
t_veto trong lưới {0,7; 0,8; 0,9}: chọn tổ hợp có t_veto nhỏ nhất đạt **ủng thật bị bác bỏ ≤ 2%**; hòa thì lấy tổ hợp
bác bỏ đúng nhiều chân không ủng hơn. Số đã đo (16/11, trước khi viết code):

| | t 0,7 | t 0,8 | t 0,9 |
|---|---|---|---|
| v3: ủng thật bị bác bỏ / bác bỏ đúng | 21,1% / 83,8% | 19,7% / 79,1% | 8,5% / 70,1% |
| v4: ủng thật bị bác bỏ / bác bỏ đúng | 5,6% / 78,1% | **0% / 71,2%** | 0% / 60,8% |

→ v4, t_veto 0,8. Giới hạn: 71 ủng thật (0/71, cận trên KTC 95% khoảng 4%); val này cũng là val của lúc train bộ
phân loại (best.pt chọn theo top1 trên val), nên hơi lạc quan.

**Kiểm hồi quy 13 video** (`06b evaluate`, bản cuối so với bản cuối + M1): ủng theo tổng nhóm: độ đúng không giảm,
"Có → Thiếu" trên nhãn Có (ủng thật mất) không tăng quá 2% số khung nhãn Có; PPE khác giống từng khung; liệt kê sự kiện
khác. Người dùng duyệt rồi mới bật.

## 3. M2: dạy lại bộ phân loại mũ cho cảnh nhìn từ sau

**Dữ liệu (bản parts v5)** = dữ liệu v4 + :
1. Mũ CHV thuộc ppe4 **train** (mọi màu, nhìn trước và sau), ảnh cắt đầu như 03y (box và kp).
2. Tăng cường làm tối cho ảnh cắt mũ nhìn từ sau (giảm V, trắng đen), ghi rõ là ảnh tạo thêm, tên file `_dark`.
3. Ảnh mũ tối màu nhìn từ sau từ nguồn công khai có giấy phép (người dùng tải, máy gán + người kiểm định; ghi nguồn,
   giấy phép, sha256 trong `data/raw/<nguồn>/README.md`). Chỉ vào train.
Không dùng video, holdout, Pictor, ppe4 val/test cho train.

**Tiêu chí (khóa 16/11/2026, người dùng duyệt), chấm trên val** (03y val + mũ CHV val như C2, `back_view_now` như D):
- **V-B1:** mũ thật nhìn từ sau có 1 − p ≥ t_neg (bị cho là không mũ) ≤ **2%**.
- **V-B2:** đầu không mũ nhìn từ sau có 1 − p ≥ t_neg ≥ **85%** (bản 4: 90%).
- **V-B3:** độ chính xác chung của mũ trên val (pos ở t_pos, neg ở t_neg như `val_select_v4.json`) không giảm quá
  **0,01** so với bản 4.
Đạt cả ba: tắt D cho mũ (giữ D cho kính), kiểm hồi quy 13 video: video17 không báo thiếu oan nhiều hơn bản cuối, độ
đúng mũ theo tổng nhóm không giảm. Người dùng duyệt rồi mới bật. Không đạt: giữ D, ghi giới hạn.

Train trên Kaggle (`04g_train_parts_cls.py`), cùng cấu hình bản 4 trừ dữ liệu.

### 3b. Sửa cách lấy dữ liệu v5: cân bằng theo tầng (người dùng duyệt 16/11/2026, trước khi train)

Lần tạo đầu (mục 4, "M2: dữ liệu parts v5 lần đầu") lấy ngẫu nhiên tối đa 9.000 ảnh mỗi kiểu từ hợp các nguồn, nên
**sai mục 3** ("dữ liệu v4 +": SH17 không mũ 6.984 → 1.283) và tạo lối tắt mới: không mũ 84% SHWD, ảnh thật tối 65% (mũ
24%), ảnh < 48 px 40% (mũ 28%); ảnh cắt theo keypoint mũ gấp đôi không mũ. Gói đó **không dùng**. Thiết kế thay thế:

1. **Gốc:** chép nguyên `data/ppe6/parts` bản 4 (train và val, mọi lớp). Lớp khác mũ không đổi.
2. **Kho nguồn mới** (`v5.pool`, chỉ có trên máy): mọi hộp đầu của CHV train, CC0, SHWD (mỗi nguồn × lớp tối đa
   `pool_max_per_src_cls` hộp, ngẫu nhiên), cắt cả hai kiểu (hộp, keypoint) như train v4 (xê dịch, tăng cường), luật D
   đánh dấu nhìn từ sau; mỗi ảnh nhìn từ sau có 2 bản làm tối (cả hai lớp). Bảng `meta.csv`: nguồn, kiểu, nhìn từ sau,
   cỡ (cạnh dài ảnh lưu), độ sáng (V trung bình nửa giữa ảnh).
3. **Tập kiểm riêng** (`v5.check_out`): 15% ảnh CC0 và SHWD (chọn theo ảnh, hạt giống cố định) không vào kho; ảnh train
   gần trùng (pHash ≤ `dedup_hamming`) với ảnh kiểm cũng bị bỏ. Cắt kiểu val (hình học pipeline, không tăng cường, không
   làm tối). Nhãn là nhãn gốc của bộ công khai (không phải nhãn người của project). **Chỉ để báo cáo** tỉ lệ nhầm theo
   tầng (nhìn từ sau × tối), không là tiêu chí, không dùng chọn tham số hay trọng số.
4. **Chọn theo tầng:** tầng = (kiểu cắt, tối V < 90, nhỏ < 48 px). Mỗi tầng: đích T = g × max(gốc mũ, gốc không mũ),
   g = 1; lớp thiếu lấy thêm ảnh thật từ kho, ưu tiên ảnh nhìn từ sau rồi ngẫu nhiên, mỗi nguồn mới không quá 60% số ảnh
   lấy thêm của lớp trong tầng. Ảnh nhìn từ sau được chọn kéo theo bản làm tối; rồi tầng tối được cân lại bằng ảnh thật
   không nhìn từ sau của lớp đang thiếu. Mức 90 lấy từ chẩn đoán mục 1; 48 px, 60% và g do Claude đề xuất, chạy thử trên
   kho cũ trước khi chốt (g = 1,5 và 2: SHWD lấn át lớp không mũ, nhiều tầng thiếu ảnh).
5. **Kiểm trước khi đưa lên Kaggle:** mọi tầng có tỉ lệ mũ / không mũ trong [0,8; 1,25] (ghi vào `summary.json`), báo
   bảng phân phối cho người dùng.

Tiêu chí V-B1..3 (mục 3) và cấu hình train không đổi.

## 4. Kết quả

### M1 (16/11/2026)

- Code: `part_cls.veto_boots`, `Compliance.part_ps` (tách từ `part_vote`, không đổi hành vi), `PartClassifier` cắt chân khi
  có `veto_boots`; vẽ hộp bác bỏ "Ung (bac bo)". Test `tests/test_boots_veto.py` (7); toàn bộ 203 test qua.
- Chọn trên val: `python scripts/05e_select_part_cls.py --boots-veto` → `outputs/results/parts_cls/boots_veto_val.json`:
  **v4, t_veto 0,8** (bác bỏ nhầm 0/71, bác bỏ đúng 198/278 = 71,2%), như bảng mục 2.
- Hồi quy 13 video (`outputs/results/close_eval/stepM1/`, `final` = `pipeline_final_e40e793.yaml`, `M1` = thêm
  `veto_boots {t_veto: 0.8}`, `weights_by_ppe.boots` v4):
  - video 3-6: ủng độ đúng 0,549 → 0,550 (Thiếu đúng 562 → 565, báo Có sai 1 → 0, Thiếu → Chưa xác định 340 → 338);
    ủng thật mất (nhãn Có → Thiếu) 0; mũ, áo, găng, kính giống từng khung; sự kiện giống.
  - video 9-17: không khung nào đổi (không có hộp ủng nào bị bác bỏ).
  - **Đạt** tiêu chí mục 2. Tác dụng trên video phát triển nhỏ vì gần như không có dép.
- **Người dùng duyệt bật 16/11/2026**: `configs/pipeline.yaml` thêm `part_cls.weights_by_ppe.boots` (v4) và
  `part_cls.veto_boots: {t_veto: 0.8}`, giống `stepM1/pipeline_M1.yaml` về nội dung (kiểm bằng so YAML). 203 test qua.
  Holdout chưa chạy lại; nếu chạy chỉ là "kiểm tra sau khi sửa, không còn mù".

### M2: dữ liệu parts v5 lần đầu (16/11/2026, không dùng)

- `03y` với `parts.version: 5` → `data/ppe6/parts_v5/summary.json`, gói `data/ppe6/variants/kaggle/parts_v5_pack.zip`
  (662,3 MB, SHA-256 `56b3e335b90c61d289ffb55ccfcd24af29e3941e53609a4def1448a27fdf06ea`).
- Nguồn thêm (chỉ train): CHV ppe4 train 845 ảnh (bỏ 119 ảnh cùng cảnh với ảnh đánh giá), `hard_hat_cc0` 4.999 ảnh (bỏ
  1 ảnh trùng ảnh đánh giá theo pHash), SHWD 7.445 ảnh (bỏ 126 ảnh trùng). Ảnh so trùng: 4.060 ảnh ppe4 val/test,
  Pictor, test_new.
- Train vùng đầu: `helmet` 20.815 ảnh (hộp 8.636, keypoint 7.455, làm tối 4.724), `no_helmet` 15.895 (8.515; 3.754;
  3.626). Ảnh gốc nhìn từ sau (luật D): mũ 1.131 + 1.231 (hộp + keypoint), không mũ 758 + 1.055; mỗi ảnh có 2 bản làm
  tối. Lớp khác như bản 4 (tối đa 4.000 mỗi kiểu).
- Val: lần tạo đầu cắt lại val vùng đầu theo keypoint bằng `geometry.head` hiện tại (bản 4 cắt bằng hình học giữa
  khoảng vì lúc đó chưa có `geometry.head`), nên khác bản 4. Để giữ "cùng cấu hình bản 4 trừ dữ liệu train", thêm
  `parts.v5.val_from: data/ppe6/parts/val` (03y chép nguyên val bản 4) và áp bước này lên kết quả đã tạo: val v5 giống
  val bản 4 từng byte. Train giữ kết quả lần chạy đó (val không dùng số ngẫu nhiên nên nội dung train như code hiện
  tại; chỉ tên file khác vì bộ đếm). Tiêu chí V-B không phụ thuộc thư mục này (05e cắt lại từ ảnh gốc).
- **Không dùng**: sai mục 3 và có lối tắt (phân tích phân phối ở mục 3b); thay bằng thiết kế mục 3b (`val_from` được
  thay bằng `base_from`: chép nguyên cả train và val bản 4).

### M2: dữ liệu parts v5 cân bằng theo tầng (16/11/2026, mục 3b)

Lệnh: `python scripts/03y_ppe6_part_crops.py` (`parts.version: 5`), log `data/ppe6/parts_v5_build.log`. Gói
`data/ppe6/variants/kaggle/parts_v5_pack.zip` 669,2 MB, SHA-256
`46335a488b11b0051560b8a14befab7006b0d0b16b1d0537f2cc8c5a9f0fada1`. **Chưa đưa lên Kaggle** (chờ người dùng, xem
"Điểm cần quyết định").

- Nguồn: CHV train 845 ảnh (bỏ 119 cùng cảnh đánh giá), CC0 4.999 (bỏ 1 trùng ảnh đánh giá), SHWD 7.445 (bỏ 126).
  Tập kiểm: 1.867 ảnh CC0 / SHWD; **1.687 ảnh train bị bỏ vì gần trùng ảnh tập kiểm** (pHash ≤ 6: hai bộ công khai có
  nhiều ảnh gần giống nhau). Hộp quá nhỏ bị bỏ: 4.499. Kho (hộp): CHV mũ 2.042; CC0 mũ 12.000, không mũ 4.634; SHWD mũ
  6.825, không mũ 12.000.
- Train vùng đầu: **mũ 11.774** (v4 5.627 + ảnh thật thêm 3.199 + bản làm tối 2.948), **không mũ 11.242** (v4 7.964 +
  2.732 + 546). Nguồn mũ: SHWD 2.685, cppe2 2.466, CC0 2.410, cppe1 2.094, SH17 1.067, CHV 1.052; không mũ: SH17 6.984,
  SHWD 2.266, CC0 1.012, cppe2 591, cppe1 389. Tỉ lệ tối (mọi ảnh / ảnh thật): mũ 0,584 / 0,451, không mũ 0,568 / 0,547;
  nhỏ < 48 px: 0,090 / 0,095; kiểu box / kp: mũ 5.466 / 6.308, không mũ 5.466 / 5.776. Ảnh nhìn từ sau thêm: mũ 1.474
  (tối 852), không mũ 321 (tối 95). Lớp khác, val: như bản 4.
- Bảng tầng (mũ / không mũ; trong ngoặc: bản làm tối mũ / không mũ): box sáng lớn 2.284 / 2.284; box sáng nhỏ 203 /
  203; box tối lớn 2.701 / 2.701 (1.138 / 14); box tối nhỏ 278 / 278 (0 / 212); kp sáng lớn 2.232 / 2.180 (52 / 0); kp
  sáng nhỏ 181 / 185 (0 / 4); kp tối lớn 3.495 / 3.011 (1.758 / 0); kp tối nhỏ 400 / 400 (0 / 316). **Mọi tầng trong
  [0,8; 1,25]** (lệch nhất kp tối lớn 1,161: thiếu 484 ảnh không mũ thật không nhìn từ sau trong kho khi cân lại, do
  giới hạn 60% mỗi nguồn).
- Ảnh trắng đen (S trung bình < 8, Claude đo): mũ 3.287 / 11.774 (27,9%; ảnh thật 17,7%), không mũ 2.237 / 11.242
  (19,9%; ảnh thật 17,9%).

**Mốc bản 4 trên tập kiểm riêng** (`05e --helmet-check`, chỉ báo cáo, nhãn gốc CC0 / SHWD,
`outputs/results/parts_cls/helmet_check_v5.json`; "cho là không mũ" = 1 − p ≥ t_neg):

| Tầng | n | v4 cho là không mũ | v4 cho là có mũ |
|---|---|---|---|
| mũ, nhìn trước, sáng | 4.847 | 5,9% | 82,1% |
| mũ, nhìn trước, tối | 214 | **20,6%** | 55,6% |
| mũ, nhìn từ sau, sáng | 928 | 3,6% | 87,4% |
| mũ, nhìn từ sau, tối | 37 | 8,1% | 67,6% |
| không mũ, nhìn trước, sáng / tối | 8.065 / 10.522 | 93,4% / 96,7% | 1,1% / 0,1% |
| không mũ, nhìn từ sau, sáng / tối | 704 / 2.300 | 93,6% / 98,6% | 1,4% / 0,2% |

Mũ tối bị cho là không mũ nhiều nhất (20,6%), đúng loại lỗi M2 nhắm tới; mũ tối nhìn từ sau trong tập kiểm chỉ có 37 ảnh
(ít, chỉ để tham khảo).

**Điểm cần quyết định (Claude nêu, chưa sửa):** bản làm tối lệch về lớp mũ: ở hai tầng tối lớn, 42% (box) và 50% (kp)
ảnh mũ là ảnh làm tối, ảnh không mũ gần như không có (14 và 0). Nếu ảnh làm tối có "dấu vết" riêng (tối đều, trắng
đen), bộ phân loại có thể học "dấu vết làm tối → mũ" (lối tắt ngược). Ảnh trắng đen: mũ 27,9% so với không mũ 19,9%.
Hướng sửa đề xuất: trong mỗi tầng tối, cho tỉ lệ ảnh làm tối của không mũ bằng của mũ (làm tối thêm ảnh không mũ sáng
trong kho, thay bớt ảnh không mũ tối thật), giữ tổng mỗi tầng như bảng trên. Hoặc chấp nhận và train luôn gói hiện tại.

**Người dùng chọn hướng sửa (16/11/2026): cân bản làm tối.** Thêm vào bước chọn của `03y` (chạy `--reuse-pool`, kho
giữ nguyên, log `data/ppe6/parts_v5_select.log`): mỗi tầng tối, số bản làm tối của không mũ đưa về tỉ lệ của mũ (thay
ảnh không mũ thật đã thêm bằng bản làm tối của ảnh không mũ sáng cùng kiểu, cùng cỡ trong kho, tên `_dark2_`; tầng mà
mũ không có bản làm tối thì thay bản làm tối không mũ bằng ảnh không mũ tối thật). Tổng mỗi tầng và gốc v4 không đổi.

| Tầng tối | bản làm tối mũ | không mũ trước | không mũ sau |
|---|---|---|---|
| box lớn | 1.138 / 2.701 (42,1%) | 14 | 1.138 / 2.701 (42,1%) |
| box nhỏ | 0 | 212 | 0 |
| kp lớn | 1.758 / 3.495 (50,3%) | 0 | 1.274 / 3.011 (42,3%; tối đa vì gốc v4 giữ nguyên) |
| kp nhỏ | 0 | 316 | 0 |

Sau khi cân: mũ 11.774 (thêm thật 3.199, làm tối 2.948), không mũ 11.242 (thêm thật 862, làm tối 2.416). Tỉ lệ tối của
ảnh thật mũ / không mũ 0,451 / 0,451; ảnh trắng đen 27,9% / 25,6% (ảnh thật 17,7% / 17,3%). Mọi tầng vẫn trong
[0,8; 1,25]. Gói `data/ppe6/variants/kaggle/parts_v5_pack.zip` 667,9 MB, SHA-256
`7c100cd0a9914a4eeecdc073530baeb5cb1fcf8a95fd8061bd523a14417024a6` (thay gói ở trên). Bước tiếp: người dùng train trên
Kaggle (`yolo11n_cls_parts_v5`).
