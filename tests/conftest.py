"""ibon_printer 測試共用 fixture。"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Union
from unittest.mock import MagicMock

import pytest

TESTS_DIR = Path(__file__).resolve().parent


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """寫入一個極小但合法的 PDF；小到能通過大小檢查。"""
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF-1.4\n%EOF\n")
    return path


@pytest.fixture
def qrcode_example_path() -> Path:
    """ibon 實際輸出的 QR Code 範例（pincode 3524627893）。"""
    return TESTS_DIR / "qrcode_example.png"


def decode_qrcode(source: Union[bytes, Path, str]) -> str:
    """以 pyzbar 解出 QR Code 內容；多筆時取第一筆。"""
    from PIL import Image
    from pyzbar.pyzbar import decode as pyzbar_decode

    if isinstance(source, bytes):
        image = Image.open(BytesIO(source))
    else:
        image = Image.open(source)
    results = pyzbar_decode(image)
    if not results:
        raise AssertionError("no QR Code detected in image")
    return results[0].data.decode("utf-8")


class FakeSession:
    """可預先排程的 requests.Session 替身。

    透過 ``.queue(...)`` 排入 JSON 回應；每次呼叫 ``.request(...)`` 或
    ``.post(...)`` 會依序取出下一筆預設回應並記錄該次呼叫。
    """

    def __init__(self) -> None:
        self._responses: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self.headers: dict[str, str] = {}

    def queue(self, *responses: dict[str, Any]) -> None:
        self._responses.extend(responses)

    def _next_response(self) -> MagicMock:
        if not self._responses:
            raise AssertionError("FakeSession ran out of queued responses")
        payload = self._responses.pop(0)
        resp = MagicMock()
        resp.json.return_value = payload
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        return resp

    def request(self, method: str, url: str, **kwargs: Any) -> MagicMock:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self._next_response()

    def post(self, url: str, **kwargs: Any) -> MagicMock:
        return self.request("POST", url, **kwargs)

    def get(self, url: str, **kwargs: Any) -> MagicMock:
        return self.request("GET", url, **kwargs)


@pytest.fixture
def fake_session() -> FakeSession:
    return FakeSession()
