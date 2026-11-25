# -*- mode: python ; coding: utf-8 -*-
"""Cấu hình đóng gói PyInstaller chế độ thư mục (onedir) cho PPE Monitor (docs/desktop_app_plan.md mục 6, M1, M6).

Hai chế độ đóng gói:
- Mặc định (M6 — bản đầy đủ): kèm đầy đủ PyTorch, Ultralytics, ByteTrack và các tệp trọng số đang khai báo trong
  `configs/pipeline.yaml` (nếu đã giải nén vào repo).
- `PPE_EMPTY_BUILD=1` (M1 — bản đóng gói rỗng kiểm thử vỏ ứng dụng): lược bỏ `torch`, `torchvision`, `ultralytics`
  để kiểm tra nhanh cửa sổ `pywebview`, máy chủ nền `uvicorn`, khóa phiên bản, màn hình chờ và đóng sạch.
"""

import os
from pathlib import Path
import yaml
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

SPEC_DIR = Path(SPECPATH).resolve()
REPO_ROOT = SPEC_DIR.parent
EMPTY_BUILD = os.environ.get("PPE_EMPTY_BUILD", "").strip().lower() in ("1", "true", "yes")

# Tài nguyên tĩnh bắt buộc của ứng dụng
datas = [
    (str(REPO_ROOT / "configs"), "configs"),
    (str(REPO_ROOT / "dashboard"), "dashboard"),
    (str(REPO_ROOT / "desktop" / "assets"), "desktop/assets"),
    (str(REPO_ROOT / "scripts" / "05_run_video.py"), "scripts"),
    (str(REPO_ROOT / "src" / "ppe"), "ppe"),
]

# Khi đóng gói bản đầy đủ (M6), tự động kèm các tệp trọng số trong configs/pipeline.yaml nếu có trên máy
if not EMPTY_BUILD:
    pipe_cfg = yaml.safe_load((REPO_ROOT / "configs" / "pipeline.yaml").read_text(encoding="utf-8")) or {}
    weight_paths = set()
    if (pipe_cfg.get("detector") or {}).get("weights"):
        weight_paths.add(pipe_cfg["detector"]["weights"])
    if (pipe_cfg.get("pose") or {}).get("weights"):
        weight_paths.add(pipe_cfg["pose"]["weights"])
    pc = pipe_cfg.get("part_cls") or {}
    if pc.get("weights"):
        weight_paths.add(pc["weights"])
    for wp in (pc.get("weights_by_ppe") or {}).values():
        if wp:
            weight_paths.add(wp)
    for rel in sorted(weight_paths):
        src_file = REPO_ROOT / rel
        if src_file.exists():
            dest_parent = str(Path(rel).parent).replace("\\", "/")
            datas.append((str(src_file), dest_parent if dest_parent != "" else "."))
    datas += collect_data_files("ultralytics")

datas += collect_data_files("webview")

hiddenimports = [
    "backend",
    "backend.app",
    "backend.db",
    "backend.live",
    "backend.video_file",
    "desktop",
    "desktop.paths",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
    "clr_loader",
    "pythonnet",
]

if not EMPTY_BUILD:
    hiddenimports += collect_submodules("ppe")
    hiddenimports += [
        "ultralytics",
        "ultralytics.trackers",
        "ultralytics.trackers.byte_tracker",
        "lap",
    ]

# Không bao giờ đóng gói các thư viện chỉ phục vụ gán nhãn offline / kiểm thử phát triển
excludes = [
    "cvat_sdk",
    "transformers",
    "tokenizers",
    "huggingface_hub",
    "safetensors",
    "pytest",
    "tkinter",
]

if EMPTY_BUILD:
    excludes += [
        "torch",
        "torchvision",
        "ultralytics",
        "matplotlib",
        "polars",
        "sympy",
        "scipy",
    ]

icon_file = REPO_ROOT / "desktop" / "assets" / "icon.ico"

a = Analysis(
    [str(REPO_ROOT / "desktop" / "main.py")],
    pathex=[str(REPO_ROOT), str(REPO_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PPEMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PPEMonitor",
)

