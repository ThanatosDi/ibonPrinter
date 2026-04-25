"""HTTP 層行為測試：驅動 ibon 上傳流程的四個請求。"""
from __future__ import annotations

from pathlib import Path

import pytest

from ibon_printer.client import (
    ENDPOINT_CHUNK,
    ENDPOINT_ENTRY,
    ENDPOINT_PINCODE,
    ENDPOINT_UPLOAD,
    IbonClient,
)
from ibon_printer.errors import IbonRequestError


def _entry_response(token: str = "TKN") -> dict:
    return {
        "code": 20000,
        "msg": "success",
        "result": {
            "token": token,
            "mToken": "",
            "email": "",
            "name": "",
            "uuid": "test-uuid",
        },
    }


def _pincode_response(pincode: str = "1234567890") -> dict:
    return {
        "code": 20000,
        "msg": "success",
        "result": {
            "pincode": pincode,
            "qRcode": None,
            "deadLine": "2026/05/01 12:00:00",
            "checkCode": None,
        },
    }


def test_fetch_entry_success(fake_session):
    fake_session.queue(_entry_response("TKN1"))
    client = IbonClient(session=fake_session)
    assert client._fetch_entry() == "TKN1"
    call = fake_session.calls[-1]
    assert call["url"] == ENDPOINT_ENTRY
    assert call["method"] == "POST"
    body = call["json"]["Data"]
    assert body["disposableId"] == client.disposable_id
    assert body["key"] == client.key_field
    assert body["t1"] == client.t1


def test_fetch_entry_failure(fake_session):
    fake_session.queue({"code": 99999, "msg": "boom"})
    client = IbonClient(session=fake_session)
    with pytest.raises(IbonRequestError, match="boom") as excinfo:
        client._fetch_entry()
    assert excinfo.value.result_code == "99999"


def test_fetch_pincode_sends_auth_headers(fake_session):
    fake_session.queue(_pincode_response("PIN1"))
    client = IbonClient(session=fake_session)
    payload = client._fetch_pincode("TKN1", "user", "a@b.com", "FNOMAL")
    assert payload["result"]["pincode"] == "PIN1"
    call = fake_session.calls[-1]
    assert call["url"] == ENDPOINT_PINCODE
    assert call["headers"]["Authorization"] == "TKN1"
    assert call["headers"]["key"] == client.disposable_id
    body = call["json"]["Data"]
    assert body["User"] == "user"
    assert body["Email"] == "a@b.com"
    assert body["SelectType"] == "FNOMAL"


def test_fetch_pincode_forwards_select_type(fake_session):
    fake_session.queue(_pincode_response())
    client = IbonClient(session=fake_session)
    client._fetch_pincode("TKN", "u", "e", "FA3CN2")
    body = fake_session.calls[-1]["json"]["Data"]
    assert body["SelectType"] == "FA3CN2"


def test_fetch_pincode_blank_user_uses_guest(fake_session):
    fake_session.queue(_pincode_response())
    client = IbonClient(session=fake_session)
    client._fetch_pincode("TKN", " ", "", "FNOMAL")
    body = fake_session.calls[-1]["json"]["Data"]
    assert body["User"] == "guest"
    assert body["Email"] == "guest@qware.com.tw"


def test_fetch_pincode_failure(fake_session):
    fake_session.queue({"code": 50001, "msg": "rejected"})
    client = IbonClient(session=fake_session)
    with pytest.raises(IbonRequestError, match="rejected"):
        client._fetch_pincode("TKN", "u", "e", "FNOMAL")


def test_fetch_chunk_size_returns_value(fake_session):
    fake_session.queue({"ChunkSize": 4096})
    client = IbonClient(session=fake_session)
    assert client._fetch_chunk_size() == 4096
    assert fake_session.calls[-1]["url"] == ENDPOINT_CHUNK
    assert fake_session.calls[-1]["method"] == "GET"


def test_upload_chunks_single_chunk_success(fake_session, sample_pdf: Path):
    fake_session.queue({"Function": "Upload", "Status": "S", "Description": "ok"})
    client = IbonClient(session=fake_session)
    client._upload_chunks("PIN1", str(sample_pdf), chunk_size=10 * 1024 * 1024)
    call = fake_session.calls[-1]
    assert call["url"] == ENDPOINT_UPLOAD
    body = call["json"]
    assert body["ExtParameter"]["pincode"] == "PIN1"
    assert body["ExtParameter"]["fileName"] == sample_pdf.name
    assert body["ExtParameter"]["fileSerial"] == 1
    assert body["ExtParameter"]["filesize"] == sample_pdf.stat().st_size
    assert isinstance(body["buffer"], str)


def test_upload_chunks_multi_chunk_continues(fake_session, tmp_path: Path):
    target = tmp_path / "big.pdf"
    target.write_bytes(b"A" * 25)  # 大於 chunk size 才會分塊
    fake_session.queue(
        {"Function": "Upload", "Status": "C", "Description": "next"},
        {"Function": "Upload", "Status": "C", "Description": "next"},
        {"Function": "Upload", "Status": "S", "Description": "done"},
    )
    client = IbonClient(session=fake_session)
    client._upload_chunks("PIN1", str(target), chunk_size=10)
    upload_calls = [c for c in fake_session.calls if c["url"] == ENDPOINT_UPLOAD]
    assert len(upload_calls) == 3
    serials = [c["json"]["ExtParameter"]["fileSerial"] for c in upload_calls]
    assert serials == [1, 2, 3]


def test_upload_chunks_failure_raises(fake_session, sample_pdf: Path):
    fake_session.queue({"Function": "Upload", "Status": "E", "Description": "boom"})
    client = IbonClient(session=fake_session)
    with pytest.raises(IbonRequestError, match="boom"):
        client._upload_chunks("PIN1", str(sample_pdf), chunk_size=1024 * 1024)


def test_default_session_has_chrome_ua():
    client = IbonClient()
    assert "Chrome" in client.session.headers["User-Agent"]


def test_injected_session_is_reused(fake_session, sample_pdf: Path):
    fake_session.queue(
        _entry_response("T"),
        _pincode_response("PIN"),
        {"ChunkSize": 4096},
        {"Function": "Upload", "Status": "S", "Description": "ok"},
    )
    client = IbonClient(session=fake_session)
    client.upload(str(sample_pdf))
    urls = [c["url"] for c in fake_session.calls]
    assert urls == [ENDPOINT_ENTRY, ENDPOINT_PINCODE, ENDPOINT_CHUNK, ENDPOINT_UPLOAD]
