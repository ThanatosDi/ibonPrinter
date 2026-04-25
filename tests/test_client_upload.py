"""upload() 端到端編排與結果解析測試。"""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from ibon_printer import client as client_module
from ibon_printer.client import (
    ENDPOINT_CHUNK,
    ENDPOINT_ENTRY,
    ENDPOINT_PINCODE,
    ENDPOINT_UPLOAD,
    IbonClient,
    IbonUploadResult,
    PrintSpec,
    _render_qrcode_png,
)
from ibon_printer.errors import IbonRequestError

from .conftest import decode_qrcode

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _entry() -> dict:
    return {
        "code": 20000,
        "msg": "success",
        "result": {"token": "TKN", "uuid": "u"},
    }


def _pincode(*, pincode: str = "12345678", deadline: str = "2026/05/01 12:00:00") -> dict:
    return {
        "code": 20000,
        "msg": "success",
        "result": {
            "pincode": pincode,
            "qRcode": None,
            "deadLine": deadline,
            "checkCode": None,
        },
    }


def _chunk(size: int = 2 * 1024 * 1024) -> dict:
    return {"ChunkSize": size}


def _upload_ok() -> dict:
    return {"Function": "Upload", "Status": "S", "Description": "ok"}


def test_upload_end_to_end_happy_path(fake_session, sample_pdf: Path):
    fake_session.queue(_entry(), _pincode(), _chunk(), _upload_ok())
    client = IbonClient(session=fake_session)
    result = client.upload(str(sample_pdf))
    assert isinstance(result, IbonUploadResult)
    assert result.pincode == "12345678"
    assert result.deadline == datetime(
        2026, 5, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Taipei")
    )
    assert result.raw["result"]["pincode"] == "12345678"


def test_result_deadline_is_taipei_tz(fake_session, sample_pdf: Path):
    fake_session.queue(_entry(), _pincode(), _chunk(), _upload_ok())
    client = IbonClient(session=fake_session)
    result = client.upload(str(sample_pdf))
    assert result.deadline.tzinfo == ZoneInfo("Asia/Taipei")


def test_upload_aborts_on_entry_failure(fake_session, sample_pdf: Path):
    fake_session.queue({"code": 99999, "msg": "no entry"})
    client = IbonClient(session=fake_session)
    with pytest.raises(IbonRequestError):
        client.upload(str(sample_pdf))
    # 只走到 GetEntry 就應該失敗。
    assert len(fake_session.calls) == 1


def test_upload_aborts_on_pincode_failure(fake_session, sample_pdf: Path):
    fake_session.queue(_entry(), {"code": 50001, "msg": "rejected"})
    client = IbonClient(session=fake_session)
    with pytest.raises(IbonRequestError, match="rejected"):
        client.upload(str(sample_pdf))
    assert len(fake_session.calls) == 2


def test_upload_aborts_on_chunk_upload_failure(fake_session, sample_pdf: Path):
    fake_session.queue(
        _entry(),
        _pincode(),
        _chunk(),
        {"Function": "Upload", "Status": "E", "Description": "broken"},
    )
    client = IbonClient(session=fake_session)
    with pytest.raises(IbonRequestError, match="broken"):
        client.upload(str(sample_pdf))


def test_upload_forwards_user_email(fake_session, sample_pdf: Path):
    fake_session.queue(_entry(), _pincode(), _chunk(), _upload_ok())
    client = IbonClient(session=fake_session)
    client.upload(str(sample_pdf), user="陳大寶", email="a@b.com")
    pincode_call = next(c for c in fake_session.calls if c["url"] == ENDPOINT_PINCODE)
    body = pincode_call["json"]["Data"]
    assert body["User"] == "陳大寶"
    assert body["Email"] == "a@b.com"


def test_upload_visits_endpoints_in_order(fake_session, sample_pdf: Path):
    fake_session.queue(_entry(), _pincode(), _chunk(), _upload_ok())
    client = IbonClient(session=fake_session)
    client.upload(str(sample_pdf))
    urls = [c["url"] for c in fake_session.calls]
    assert urls == [ENDPOINT_ENTRY, ENDPOINT_PINCODE, ENDPOINT_CHUNK, ENDPOINT_UPLOAD]


def test_upload_default_spec_uses_FNOMAL(fake_session, sample_pdf: Path):
    fake_session.queue(_entry(), _pincode(), _chunk(), _upload_ok())
    client = IbonClient(session=fake_session)
    client.upload(str(sample_pdf))
    pincode_call = next(c for c in fake_session.calls if c["url"] == ENDPOINT_PINCODE)
    assert pincode_call["json"]["Data"]["SelectType"] == "FNOMAL"


def test_upload_forwards_print_spec(fake_session, sample_pdf: Path):
    fake_session.queue(_entry(), _pincode(), _chunk(), _upload_ok())
    client = IbonClient(session=fake_session)
    client.upload(str(sample_pdf), spec=PrintSpec.a3(color=True, duplex=True))
    pincode_call = next(c for c in fake_session.calls if c["url"] == ENDPOINT_PINCODE)
    assert pincode_call["json"]["Data"]["SelectType"] == "FA3CN2"


def test_result_qrcode_base64_decodes_to_png(fake_session, sample_pdf: Path):
    fake_session.queue(_entry(), _pincode(), _chunk(), _upload_ok())
    client = IbonClient(session=fake_session)
    result = client.upload(str(sample_pdf))
    assert isinstance(result.qrcode_base64, str)
    assert base64.b64decode(result.qrcode_base64).startswith(PNG_MAGIC)


def test_result_qrcode_encodes_pincode(fake_session, sample_pdf: Path):
    fake_session.queue(_entry(), _pincode(pincode="5678901234"), _chunk(), _upload_ok())
    client = IbonClient(session=fake_session)
    result = client.upload(str(sample_pdf))
    decoded_png = base64.b64decode(result.qrcode_base64)
    assert decode_qrcode(decoded_png) == "5678901234"
    # 與獨立呼叫 helper 等價
    assert decoded_png == _render_qrcode_png("5678901234")


def test_upload_warns_when_qrcode_generation_fails(
    fake_session, sample_pdf: Path, monkeypatch
):
    fake_session.queue(_entry(), _pincode(), _chunk(), _upload_ok())

    def _boom(_text: str) -> bytes:
        raise RuntimeError("simulated qrcode failure")

    monkeypatch.setattr(client_module, "_render_qrcode_png", _boom)
    client = IbonClient(session=fake_session)
    with pytest.warns(UserWarning, match="QR Code generation failed"):
        result = client.upload(str(sample_pdf))
    assert result.pincode == "12345678"
    assert result.qrcode_base64 == ""
