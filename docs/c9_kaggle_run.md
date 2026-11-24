# Train C9-ft trên Kaggle (ảnh cắt người ở độ phân giải gốc: tinh chỉnh từ c6_ft)

Kế hoạch: `docs/experiments/2026-11-16_c5_detector_plan.md`, mục C9; tiêu chí khóa ở `configs/ppe6.yaml` mục `c9_decision`.
Một lần train: tinh chỉnh từ c6_ft (như c6_ft, C8-ft: 40 epoch, SGD, lr0 0,002, warmup 1, không `time`), imgsz 960, **một
GPU** (dự kiến khoảng 3–5 giờ). Dữ liệu: gói chính `c5_pack.zip` (đã có) + bộ phụ mới `c9_extra_pack.zip` = bộ phụ của c6_ft
(`c6_extra`: 4.369 ảnh, 3.197 bản lặp) + 3.000 ảnh cắt người `zoom__*` (`scripts/03zd_c9_zoom_crops.py`); kèm trọng số c6_ft.

## Dữ liệu trên Kaggle

- Giữ Input: dataset chính (`ppe4_main_960.zip` đã tải lên tài khoản mới) và `khoa-luan-ppe6-c5` (`c5_pack.zip`).
- **Bỏ Input** mọi bộ phụ cũ (`khoa-luan-ppe6-c8-extra`…); tạo dataset mới `khoa-luan-ppe6-c9-extra` từ
  `data/ppe6/variants/kaggle/c9_extra_pack.zip` (909 MB) và Add Input.
- Accelerator **GPU T4 x1** hoặc x2 (chỉ dùng GPU 0), Internet On.

## Cell

```python
# C9-ft: tinh chỉnh từ c6_ft, imgsz 960, dữ liệu c5_pack + c9_extra.
import glob, json, os, subprocess, time
packs = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/ready.json", recursive=True)
         if json.load(open(p)).get("variant") == "c5" and os.path.exists(os.path.join(os.path.dirname(p), "manifest.tsv"))]
assert len(packs) == 1, f"Phải có đúng 1 gói C5, thấy: {packs}"
PACK = packs[0]
assert sum(1 for l in open(f"{PACK}/manifest.tsv") if l.startswith("train\t")) == 7169
for old in ("c5_extra", "c6_extra", "c7_extra", "c8_extra"):
    assert not glob.glob(f"/kaggle/input/**/{old}/oversample.txt", recursive=True), f"Bỏ Input bộ phụ cũ ({old})"
extras = glob.glob("/kaggle/input/**/c9_extra/oversample.txt", recursive=True)
assert len(extras) == 1, f"Phải có đúng 1 bộ phụ C9, thấy: {extras}"
EXTRA = os.path.dirname(extras[0])
W6 = f"{EXTRA}/weights/c6_ft_best.pt"
assert os.path.exists(W6)
print("PACK =", PACK, "| EXTRA =", EXTRA, "| W6 =", W6)
subprocess.run("pip install -q ultralytics==8.4.189", shell=True, check=True)
repo = "/kaggle/working/code_c9"
subprocess.run(f"rm -rf {repo}; git clone -q -b exp/ppe6 https://github.com/phppp-1701/PPE_Project.git {repo}", shell=True, check=True)
cfg = f"{repo}/configs/train.yaml"
for s in [f"s|^model: yolo11s.pt|model: {W6}|", "s|^  epochs: 100 .*|  epochs: 40|", "/^  time: 11/d",
          "s|^  imgsz: 960|  imgsz: 960\\n  optimizer: SGD\\n  lr0: 0.002\\n  warmup_epochs: 1|"]:
    subprocess.run(["sed", "-i", s, cfg], check=True)
print(subprocess.run(f"grep -n '^model\\|^  time\\|^  imgsz\\|^  epochs\\|^  optimizer\\|^  lr0\\|^  warmup' {cfg}",
                     shell=True, capture_output=True, text=True).stdout)
env = dict(os.environ, CUDA_VISIBLE_DEVICES="0", YOLO_AUTOINSTALL="False")
log = open("/kaggle/working/train_c9_ft.log", "w")
p = subprocess.Popen(["python", "-u", "scripts/04_train.py", "--ppe6", PACK, "--extra", EXTRA,
                      "--run-name", "yolo11s_ppe6_c9_ft", "--out", "/kaggle/working/runs", "--data-copy", "/tmp/ppe_data_c9"],
                     cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
t0 = time.time()
while p.poll() is None and time.time() - t0 < 11.7 * 3600:
    time.sleep(1800)
    print(time.strftime("%H:%M"), open("/kaggle/working/train_c9_ft.log").read().splitlines()[-1:])
print("mã thoát", p.poll())
subprocess.run("python scripts/04f_check_run.py --run /kaggle/working/runs/yolo11s_ppe6_c9_ft", shell=True, cwd=repo)
subprocess.run(f"rm -rf {repo}; du -sh /kaggle/working/runs", shell=True)
```

Kiểm sau khoảng 10 phút: grep in `model: …/c6_ft_best.pt`, `epochs: 40`, `optimizer: SGD`, không có dòng `time`; trong
log `train_c9_ft.log` có `Bộ 6 lớp: {'train': 7169, 'val_monitor': 1070}` và sau đó `Bộ phụ: 7369 ảnh cắt, 3197 bản thêm;
train còn 17735 ảnh`.

Tải về: `runs/yolo11s_ppe6_c9_ft` → `outputs/train/yolo11s_ppe6_c9_ft`, log `train_c9_ft.log`.
