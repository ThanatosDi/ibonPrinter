"""發出網路請求前的本機檔案驗證。"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from ibon_printer.client import IbonClient
from ibon_printer.errors import IbonValidationError


def test_missing_file_raises(tmp_path: Path):
    client = IbonClient()
    missing = tmp_path / "does_not_exist.pdf"
    with pytest.raises(IbonValidationError, match="找不到檔案"):
        client._validate(str(missing))


def test_unsupported_extension_raises(tmp_path: Path):
    client = IbonClient()
    bad = tmp_path / "photo.heic"
    bad.write_bytes(b"fake")
    with pytest.raises(IbonValidationError) as excinfo:
        client._validate(str(bad))
    msg = str(excinfo.value)
    # 錯誤訊息需列出新版允許的副檔名供使用者參考。
    for ext in ("pdf", "jpg", "jpeg", "png", "docx"):
        assert ext in msg


def test_oversize_file_raises(monkeypatch, sample_pdf: Path):
    client = IbonClient()
    # 16 MB > 15 MB 限制。
    monkeypatch.setattr(os.path, "getsize", lambda _p: 16 * 1024 * 1024)
    with pytest.raises(IbonValidationError, match="15 MB"):
        client._validate(str(sample_pdf))


def test_valid_file_passes(sample_pdf: Path):
    client = IbonClient()
    # 預期不應拋出例外。
    client._validate(str(sample_pdf))


def test_png_is_now_allowed(tmp_path: Path):
    client = IbonClient()
    target = tmp_path / "foo.png"
    target.write_bytes(b"\x89PNG\r\n\x1a\n")
    client._validate(str(target))
