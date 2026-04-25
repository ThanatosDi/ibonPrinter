"""驗證 tests/qrcode_example.png 確實為 ibon 在 pincode 3524627893 下產出的 QR Code。"""
from __future__ import annotations

from pathlib import Path

from .conftest import decode_qrcode


def test_example_image_decodes_to_known_pincode(qrcode_example_path: Path) -> None:
    assert decode_qrcode(qrcode_example_path) == "3524627893"
