# Train C8-ft trên Kaggle (găng: tinh chỉnh từ c6_ft)

Kế hoạch: `docs/experiments/2026-11-16_c5_detector_plan.md`, mục C8; tiêu chí khóa ở `configs/ppe6.yaml` mục `c8_decision`.
Một lần train: tinh chỉnh từ c6_ft (như c6_ft: 40 epoch, SGD, lr0 0,002, warmup 1, không `time`), imgsz 960, **một GPU**
(khoảng 3–4 giờ). Dữ liệu: gói chính `c5_pack.zip` (đã có) + bộ phụ mới `c8_extra_pack.zip` (bộ phụ C7 + 538 ảnh găng
CCTV Safety Gloves, 7 găng thiếu nhãn, 43 vùng che, 161 ảnh mẫu âm khó găng lặp 2 lần; kèm trọng số c6_ft).

## Dữ liệu trên Kaggle

- Giữ Input: `phpp1701/khoa-luan-dataset`, `khoa-luan-ppe6-c5`.
- **Bỏ Input** bộ phụ cũ (`khoa-luan-ppe6-c7-extra`…); tạo dataset mới `khoa-luan-ppe6-c8-extra` từ
  `data/ppe6/variants/kaggle/c8_extra_pack.zip` (839 MB) và Add Input.
- Accelerator **GPU T4 x1** hoặc x2 (chỉ dùng GPU 0), Internet On.

## Cell

```python
# C8-ft: tinh chỉnh từ c6_ft, imgsz 960, dữ liệu c5_pack + c8_extra.
import glob, json, os, subprocess, time
packs = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/ready.json", recursive=True)
         if json.load(open(p)).get("variant") == "c5" and os.path.exists(os.path.join(os.path.dirname(p), "manifest.tsv"))]
assert len(packs) == 1, f"Phải có đúng 1 gói C5, thấy: {packs}"
PACK = packs[0]
assert sum(1 for l in open(f"{PACK}/manifest.tsv") if l.startswith("train\t")) == 7169
for old in ("c5_extra", "c6_extra", "c7_extra"):
    assert not glob.glob(f"/kaggle/input/**/{old}/oversample.txt", recursive=True), f"Bỏ Input bộ phụ cũ ({old})"
extras = glob.glob("/kaggle/input/**/c8_extra/oversample.txt", recursive=True)
assert len(extras) == 1, f"Phải có đúng 1 bộ phụ C8, thấy: {extras}"
EXTRA = os.path.dirname(extras[0])
W6 = f"{EXTRA}/weights/c6_ft_best.pt"
assert os.path.exists(W6)
print("PACK =", PACK, "| EXTRA =", EXTRA, "| W6 =", W6)
subprocess.run("pip install -q ultralytics==8.4.189", shell=True, check=True)
repo = "/kaggle/working/code_c8"
subprocess.run(f"rm -rf {repo}; git clone -q -b exp/ppe6 https://github.com/phppp-1701/PPE_Project.git {repo}", shell=True, check=True)
cfg = f"{repo}/configs/train.yaml"
for s in [f"s|^model: yolo11s.pt|model: {W6}|", "s|^  epochs: 100 .*|  epochs: 40|", "/^  time: 11/d",
          "s|^  imgsz: 960|  imgsz: 960\n  optimizer: SGD\n  lr0: 0.002\n  warmup_epochs: 1|"]:
    subprocess.run(["sed", "-i", s, cfg], check=True)
print(subprocess.run(f"grep -n '^model\|^  time\|^  imgsz\|^  epochs\|^  optimizer\|^  lr0\|^  warmup' {cfg}",
                     shell=True, capture_output=True, text=True).stdout)
env = dict(os.environ, CUDA_VISIBLE_DEVICES="0", YOLO_AUTOINSTALL="False")
log = open("/kaggle/working/train_c8_ft.log", "w")
p = subprocess.Popen(["python", "-u", "scripts/04_train.py", "--ppe6", PACK, "--extra", EXTRA,
                      "--run-name", "yolo11s_ppe6_c8_ft", "--out", "/kaggle/working/runs", "--data-copy", "/tmp/ppe_data_c8"],
                     cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
t0 = time.time()
while p.poll() is None and time.time() - t0 < 11.7 * 3600:
    time.sleep(1800)
    print(time.strftime("%H:%M"), open("/kaggle/working/train_c8_ft.log").read().splitlines()[-1:])
print("mã thoát", p.poll())
subprocess.run("python scripts/04f_check_run.py --run /kaggle/working/runs/yolo11s_ppe6_c8_ft", shell=True, cwd=repo)
subprocess.run(f"rm -rf {repo}; du -sh /kaggle/working/runs", shell=True)
```

Kiểm sau khoảng 10 phút: grep in `model: …/c6_ft_best.pt`, `epochs: 40`, `optimizer: SGD`, không có dòng `time`; trong
log `train_c8_ft.log` có `Bộ 6 lớp: {'train': 7169, 'val_monitor': 1070}` và sau khoảng 40 phút `Bộ phụ: … bản thêm`
(khoảng 4.027).

Tải về: `runs/yolo11s_ppe6_c8_ft` → `outputs/train/yolo11s_ppe6_c8_ft`, log `train_c8_ft.log`.
