# Pictor-PPE: kiểm thử ngoài detector (RQ1)

774 ảnh (`data/ppe4/pictor_test`, đã loại ảnh trùng với dữ liệu huấn luyện). imgsz 960, conf/iou mặc định `model.val`. Chỉ kiểm thử, không dùng để chọn ngưỡng. Pictor không có nhãn găng, kính, ủng. P, R ở conf cho F1 lớn nhất của từng mô hình (số mô tả, không phải ngưỡng hệ thống). KTC 95% của AP50: bootstrap theo ảnh, 2000 lần.

## c6_ft (6 lớp, bản cuối 26/11)

`outputs/train/yolo11s_ppe6_c6_ft/weights/best.pt`

| Lớp | Số hộp | P | R | F1 | AP50 [KTC 95%] | AP50-95 |
|---|---|---|---|---|---|---|
| person | 2497 | 0,914 | 0,744 | 0,820 | 0,851 [0,833; 0,869] | 0,577 |
| helmet | 1645 | 0,931 | 0,565 | 0,703 | 0,681 [0,643; 0,715] | 0,392 |
| vest | 42 | 0,437 | 0,524 | 0,476 | 0,477 [0,258; 0,686] | 0,218 |

TB 3 lớp: AP50 0,670, AP50-95 0,396. Thời gian (ms/ảnh, batch 4, trong model.val): tiền xử lý 1.5, suy luận 20.1, hậu xử lý 1.3.

## C4 (6 lớp, bản cuối 16/11)

`outputs/train/yolo11s_ppe6_c4/weights/best.pt`

| Lớp | Số hộp | P | R | F1 | AP50 [KTC 95%] | AP50-95 |
|---|---|---|---|---|---|---|
| person | 2497 | 0,923 | 0,722 | 0,810 | 0,851 [0,830; 0,869] | 0,580 |
| helmet | 1645 | 0,969 | 0,469 | 0,632 | 0,685 [0,649; 0,719] | 0,407 |
| vest | 42 | 0,536 | 0,500 | 0,517 | 0,419 [0,198; 0,646] | 0,241 |

TB 3 lớp: AP50 0,652, AP50-95 0,409. Thời gian (ms/ảnh, batch 4, trong model.val): tiền xử lý 1.7, suy luận 19.4, hậu xử lý 1.2.

## r2 (4 lớp, đối chứng)

`outputs/train/yolo11s_ppe4_r2/weights/best.pt`

| Lớp | Số hộp | P | R | F1 | AP50 [KTC 95%] | AP50-95 |
|---|---|---|---|---|---|---|
| person | 2497 | 0,862 | 0,773 | 0,815 | 0,842 [0,818; 0,863] | 0,565 |
| helmet | 1645 | 0,923 | 0,559 | 0,697 | 0,669 [0,632; 0,706] | 0,390 |
| vest | 42 | 0,374 | 0,524 | 0,437 | 0,447 [0,240; 0,653] | 0,215 |

TB 3 lớp: AP50 0,652, AP50-95 0,390. Thời gian (ms/ảnh, batch 4, trong model.val): tiền xử lý 1.9, suy luận 19.4, hậu xử lý 1.2.

