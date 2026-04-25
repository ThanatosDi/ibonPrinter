"""驗證 README 涵蓋安裝、兩個 console scripts、限制與停用通告。"""
from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def _text() -> str:
    return README.read_text(encoding="utf-8")


def test_readme_mentions_pip_install():
    assert "pip install ." in _text()


def test_readme_mentions_both_console_scripts():
    body = _text()
    assert "ibon-printer" in body
    assert "ibon-printer-api" in body


def test_readme_documents_limits():
    body = _text()
    assert "15 MB" in body
    for ext in ("pdf", "jpg", "jpeg", "png", "docx"):
        assert ext in body


def test_readme_deprecation_notice():
    body = _text()
    assert "ibonPrinter" in body
    assert "deprecat" in body.lower()


def test_readme_documents_qrcode_field():
    body = _text()
    # README 必須提到本變更的 QR Code 相關介面
    assert "qrcode_base64" in body
    assert "--qr-out" in body
    assert "qrcode[pil]" in body
