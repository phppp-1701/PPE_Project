# Train C6 trên Kaggle (c6_scratch và c6_ft, song song T4 x2)

Kế hoạch: `docs/experiments/2026-11-16_c5_detector_plan.md`, mục C6; tiêu chí khóa ở `configs/ppe6.yaml` mục `c6_decision`.
Cùng dữ liệu: gói chính `c5_pack.zip` (đã có trên Kaggle) + bộ phụ mới `c6_extra_pack.zip` (bộ phụ C5 + 906 ảnh ủng ngoài,
lặp ảnh có ủng, kèm trọng số C5-s960). Hai bản, imgsz 960:

- `c6_scratch` (GPU 0): từ `yolo11s.pt`, tham số như C5 (100 epoch, patience 20, time 11).
- `c6_ft` (GPU 1): tinh chỉnh từ C5-s960, 40 epoch, SGD, lr0 0,002, warmup 1 (optimizer phải đặt rõ, `auto` bỏ qua lr0); **bỏ `time`** vì khi có `time` Ultralytics tính lại số epoch cho đủ giờ (trainer.py, "time mode re-estimates epochs").

## Dữ liệu trên Kaggle

- Giữ Input: `phpp1701/khoa-luan-dataset`, `khoa-luan-ppe6-c5` (gói `c5_pack.zip`).
- **Bỏ Input** `khoa-luan-ppe6-c5-extra`; tạo dataset mới `khoa-luan-ppe6-c6-extra` từ
  `data/ppe6/variants/kaggle/c6_extra_pack.zip` (507 MB) và Add Input. Cell kiểm có đúng một `c6_extra/oversample.txt`.
- Accelerator **GPU T4 x2**, Internet On.

## Cell

```python
# C6: c6_scratch (GPU 0, từ yolo11s.pt) và c6_ft (GPU 1, tinh chỉnh từ C5-s960) song song, cùng dữ liệu, imgsz 960.
import glob, json, os, subprocess, time, torch
assert torch.cuda.device_count() >= 2, "Cần Accelerator = GPU T4 x2"
packs = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/ready.json", recursive=True)
         if json.load(open(p)).get("variant") == "c5" and os.path.exists(os.path.join(os.path.dirname(p), "manifest.tsv"))]
assert len(packs) == 1, f"Phải có đúng 1 gói C5, thấy: {packs}"
PACK = packs[0]
assert sum(1 for l in open(f"{PACK}/manifest.tsv") if l.startswith("train\t")) == 7169
assert not glob.glob("/kaggle/input/**/c5_extra/oversample.txt", recursive=True), "Bỏ Input bộ phụ C5 (khoa-luan-ppe6-c5-extra)"
extras = glob.glob("/kaggle/input/**/c6_extra/oversample.txt", recursive=True)
assert len(extras) == 1, f"Phải có đúng 1 bộ phụ C6, thấy: {extras}"
EXTRA = os.path.dirname(extras[0])
W5 = f"{EXTRA}/weights/c5_s960_best.pt"
assert os.path.exists(W5)
print("PACK =", PACK, "| EXTRA =", EXTRA, "| W5 =", W5)
subprocess.run("pip install -q ultralytics==8.4.189", shell=True, check=True)

RUNS = {"c6_scratch": (0, []),
        "c6_ft": (1, [f"s|^model: yolo11s.pt|model: {W5}|", "s|^  epochs: 100 .*|  epochs: 40|",
                      "/^  time: 11/d",   # có `time` thì Ultralytics tự kéo số epoch cho đủ giờ; tinh chỉnh cần đúng 40 epoch
                      "s|^  imgsz: 960|  imgsz: 960\\n  optimizer: SGD\\n  lr0: 0.002\\n  warmup_epochs: 1|"])}
procs, t0 = {}, time.time()
for name, (gpu, seds) in RUNS.items():
    repo = f"/kaggle/working/code_{name}"
    subprocess.run(f"rm -rf {repo}; git clone -q -b exp/ppe6 https://github.com/phppp-1701/PPE_Project.git {repo}", shell=True, check=True)
    cfg = f"{repo}/configs/train.yaml"
    for s in seds:
        subprocess.run(["sed", "-i", s, cfg], check=True)
    print(name, subprocess.run(f"grep -n '^model\\|^  time\\|^copy_max_side\\|^  imgsz\\|^  epochs\\|^  optimizer\\|^  lr0\\|^  warmup' {cfg}",
                               shell=True, capture_output=True, text=True).stdout)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), YOLO_AUTOINSTALL="False")
    log = open(f"/kaggle/working/train_{name}.log", "w")
    procs[name] = subprocess.Popen(
        ["python", "-u", "scripts/04_train.py", "--ppe6", PACK, "--extra", EXTRA,
         "--run-name", f"yolo11s_ppe6_{name}", "--out", "/kaggle/working/runs", "--data-copy", f"/tmp/ppe_data_{name}"],
        cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    time.sleep(120)

def last(name, n=1):
    return open(f"/kaggle/working/train_{name}.log").read().splitlines()[-n:]
for _ in range(30):   # chờ tới khi cả hai bản in dòng "Bộ 6 lớp" (tối đa 15 phút)
    heads = {n: [l for l in open(f"/kaggle/working/train_{n}.log").read().splitlines() if l.startswith(("Bộ 6 lớp", "Bộ phụ", "Traceback"))] for n in procs}
    if all(heads.values()):
        break
    time.sleep(30)
print(heads)
while any(p.poll() is None for p in procs.values()) and time.time() - t0 < 11.7 * 3600:
    time.sleep(1800)
    for n in procs:
        print(time.strftime("%H:%M"), n, last(n))
for n, p in procs.items():
    print(n, "mã thoát", p.poll())
    subprocess.run(f"python scripts/04f_check_run.py --run /kaggle/working/runs/yolo11s_ppe6_{n}", shell=True, cwd=f"/kaggle/working/code_{n}")
subprocess.run("rm -rf /kaggle/working/code_c6_scratch /kaggle/working/code_c6_ft; du -sh /kaggle/working/runs", shell=True)
```

Kiểm sau khoảng 10 phút: `PACK = …` không lỗi; `c6_scratch` có dòng `time: 11`, `c6_ft` **không có** dòng `time`; với `c6_ft` grep in `model: /kaggle/input/…/c5_s960_best.pt`, `epochs: 40`,
`optimizer: SGD`, `lr0: 0.002`; dòng `heads` có `Bộ 6 lớp: {'train': 7169, 'val_monitor': 1070}` cho cả hai bản (dòng
`Bộ phụ` in sau khi chép ảnh xong, khoảng 30 phút, nên có thể chưa có).

Tải về: thư mục `runs` → `outputs/train/yolo11s_ppe6_c6_scratch`, `..._c6_ft`; log `train_*.log`.
