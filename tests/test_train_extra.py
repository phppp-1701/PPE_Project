"""Kiểm tra ghép bộ phụ của scripts/04_train.py (add_extra): ảnh cùng tên thay ảnh gốc, tên lặp trong oversample.txt
tạo nhiều bản thêm (C7). Dữ liệu giả tạo trong thư mục tạm."""

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _train_module():
    spec = importlib.util.spec_from_file_location("train04", ROOT / "scripts" / "04_train.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _can_symlink(tmp_path):
    try:
        (tmp_path / "l").symlink_to(tmp_path)
        return True
    except OSError:
        return False


def test_add_extra_override_and_repeat(tmp_path, monkeypatch):
    if not _can_symlink(tmp_path):
        pytest.skip("máy không cho tạo liên kết tượng trưng")
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    base, src = tmp_path / "base", tmp_path / "src" / "c7_extra"
    for d in (base / "images" / "train", base / "labels" / "train", src / "images" / "train", src / "labels" / "train"):
        d.mkdir(parents=True)
    (base / "data.yaml").write_text("", encoding="utf-8")
    (base / "images" / "train" / "a.jpg").write_text("goc", encoding="utf-8")
    (base / "labels" / "train" / "a.txt").write_text("0 0.5 0.5 0.1 0.1\n", encoding="utf-8")
    (src / "images" / "train" / "a.jpg").write_text("moi", encoding="utf-8")        # cùng tên: thay ảnh gốc
    (src / "labels" / "train" / "a.txt").write_text("5 0.5 0.5 0.1 0.1\n", encoding="utf-8")
    (src / "images" / "train" / "c.jpg").write_text("c", encoding="utf-8")
    (src / "labels" / "train" / "c.txt").write_text("1 0.5 0.5 0.1 0.1\n", encoding="utf-8")
    (src / "oversample.txt").write_text("a.jpg\na.jpg\nc.jpg\n", encoding="utf-8")
    m = _train_module()
    m.add_extra(str(tmp_path / "src"), str(base / "data.yaml"))
    img, lab = base / "images" / "train", base / "labels" / "train"
    assert (img / "a.jpg").read_text(encoding="utf-8") == "moi"
    assert (lab / "a.txt").read_text(encoding="utf-8").startswith("5 ")
    assert sorted(p.name for p in img.iterdir()) == ["a.jpg", "c.jpg", "rep1__a.jpg", "rep__a.jpg", "rep__c.jpg"]
    assert (lab / "rep1__a.txt").read_text(encoding="utf-8").startswith("5 ")
    assert os.path.realpath(img / "rep1__a.jpg") == os.path.realpath(img / "a.jpg")
