# Train C7-m trên Kaggle (YOLO11m, 2 GPU T4 cho một lần train)

Kế hoạch: `docs/experiments/2026-11-16_c5_detector_plan.md`, mục C7; tiêu chí khóa ở `configs/ppe6.yaml` mục
`c7_decision`. Một lần train YOLO11m (`yolo11m.pt`, COCO), imgsz 960, chia trên **cả hai GPU T4** (DDP) để nhanh hơn;
batch 16 (8 mỗi GPU; DDP không dùng được AutoBatch). Dữ liệu: gói chính `c5_pack.zip` (đã có) + bộ phụ mới
`c7_extra_pack.zip` (bộ phụ C6 + 63 hộp ủng thiếu nhãn, 216 ủng báo thừa thành mẫu âm khó lặp 2 lần, ảnh SH17 có áo lặp
thêm 1 lần, 270 ảnh gốc sửa nhãn / che).

## Dữ liệu trên Kaggle

- Giữ Input: `phpp1701/khoa-luan-dataset`, `khoa-luan-ppe6-c5` (gói `c5_pack.zip`).
- **Bỏ Input** bộ phụ cũ (`khoa-luan-ppe6-c5-extra`, `khoa-luan-ppe6-c6-extra`); tạo dataset mới `khoa-luan-ppe6-c7-extra` từ
  `data/ppe6/variants/kaggle/c7_extra_pack.zip` (676 MB) và Add Input.
- Accelerator **GPU T4 x2**, Internet On. Code phải ở commit có `04_train.py` mới (ảnh bộ phụ thay ảnh gốc, tên lặp trong
  `oversample.txt`, val một GPU) — đã push lên `exp/ppe6`.

## Cell

```python
# C7-m: YOLO11m, imgsz 960, DDP trên 2 GPU T4, dữ liệu c5_pack + c7_extra.
import glob, json, os, subprocess, time, torch
assert torch.cuda.device_count() >= 2, "Cần Accelerator = GPU T4 x2"
packs = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/ready.json", recursive=True)
         if json.load(open(p)).get("variant") == "c5" and os.path.exists(os.path.join(os.path.dirname(p), "manifest.tsv"))]
assert len(packs) == 1, f"Phải có đúng 1 gói C5, thấy: {packs}"
PACK = packs[0]
assert sum(1 for l in open(f"{PACK}/manifest.tsv") if l.startswith("train\t")) == 7169
for old in ("c5_extra", "c6_extra"):
    assert not glob.glob(f"/kaggle/input/**/{old}/oversample.txt", recursive=True), f"Bỏ Input bộ phụ cũ ({old})"
extras = glob.glob("/kaggle/input/**/c7_extra/oversample.txt", recursive=True)
assert len(extras) == 1, f"Phải có đúng 1 bộ phụ C7, thấy: {extras}"
EXTRA = os.path.dirname(extras[0])
print("PACK =", PACK, "| EXTRA =", EXTRA)
subprocess.run("pip install -q ultralytics==8.4.189", shell=True, check=True)

repo = "/kaggle/working/code_c7"
subprocess.run(f"rm -rf {repo}; git clone -q -b exp/ppe6 https://github.com/phppp-1701/PPE_Project.git {repo}", shell=True, check=True)
cfg = f"{repo}/configs/train.yaml"
for s in ["s|^model: yolo11s.pt|model: yolo11m.pt|", "s|^  batch: -1 .*|  batch: 16|", "s|^  device: 0 .*|  device: 0,1|"]:
    subprocess.run(["sed", "-i", s, cfg], check=True)
print(subprocess.run(f"grep -n '^model\\|^copy_max_side\\|^  imgsz\\|^  epochs\\|^  batch\\|^  device\\|^  time\\|^  patience' {cfg}",
                     shell=True, capture_output=True, text=True).stdout)
env = dict(os.environ, YOLO_AUTOINSTALL="False")
t0 = time.time()
log = open("/kaggle/working/train_c7_m.log", "w")
p = subprocess.Popen(["python", "-u", "scripts/04_train.py", "--ppe6", PACK, "--extra", EXTRA,
                      "--run-name", "yolo11m_ppe6_c7", "--out", "/kaggle/working/runs", "--data-copy", "/tmp/ppe_data_c7"],
                     cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)

def tail(n=1):
    return open("/kaggle/working/train_c7_m.log").read().splitlines()[-n:]
for _ in range(30):
    heads = [l for l in open("/kaggle/working/train_c7_m.log").read().splitlines() if l.startswith(("Bộ 6 lớp", "Bộ phụ", "Traceback"))]
    if heads:
        break
    time.sleep(30)
print(heads)
while p.poll() is None and time.time() - t0 < 11.7 * 3600:
    time.sleep(1800)
    print(time.strftime("%H:%M"), tail())
print("mã thoát", p.poll())
subprocess.run("python scripts/04f_check_run.py --run /kaggle/working/runs/yolo11m_ppe6_c7", shell=True, cwd=repo)
subprocess.run(f"rm -rf {repo}; du -sh /kaggle/working/runs", shell=True)
```

Kiểm sau khoảng 10 phút: grep in `model: yolo11m.pt`, `batch: 16`, `device: 0,1`, `time: 11`; `heads` có `Bộ 6 lớp:
{'train': 7169, 'val_monitor': 1070}`; sau khoảng 40 phút có dòng `Bộ phụ: ... bản thêm` (số bản thêm khoảng 3.705) và log
epoch hiện `0/1` GPU, mỗi epoch dài hơn C6 (ước lượng 9–12 phút, chưa đo).

Tải về: `runs/yolo11m_ppe6_c7` → `outputs/train/yolo11m_ppe6_c7`, log `train_c7_m.log`.
