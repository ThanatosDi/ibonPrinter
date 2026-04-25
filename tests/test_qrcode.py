"""_render_qrcode_png helper 的單元測試。"""
from __future__ import annotations

import pytest

from ibon_printer.client import _render_qrcode_png

from .conftest import decode_qrcode


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_render_qrcode_returns_png_bytes() -> None:
    data = _render_qrcode_png("1234567890")
    assert isinstance(data, bytes)
    assert data.startswith(PNG_MAGIC)


def test_render_qrcode_round_trips_via_decoder() -> None:
    # 與 ibon 範例 (tests/qrcode_example.png) 相同 pincode；獨立解碼驗證。
    data = _render_qrcode_png("3524627893")
    assert decode_qrcode(data) == "3524627893"


@pytest.mark.parametrize("pincode", ["0000000000", "1234567890", "9876543210"])
def test_render_qrcode_round_trips_arbitrary_pincode(pincode: str) -> None:
    assert decode_qrcode(_render_qrcode_png(pincode)) == pincode


def test_render_qrcode_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        _render_qrcode_png("")
