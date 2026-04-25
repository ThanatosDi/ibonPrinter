"""FastAPI endpoint 行為測試：/upload 與 /healthz。"""
from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from ibon_printer import api as api_module
from ibon_printer.client import IbonUploadResult
from ibon_printer.errors import IbonRequestError, IbonValidationError


import base64 as _base64

_FAKE_PNG = b"\x89PNG\r\n\x1a\nfake-api-png"
_FAKE_PNG_B64 = _base64.b64encode(_FAKE_PNG).decode("ascii")


def _make_result(*, qrcode_base64: str = _FAKE_PNG_B64) -> IbonUploadResult:
    tz = ZoneInfo("Asia/Taipei")
    return IbonUploadResult(
        pincode="87654321",
        deadline=datetime(2026, 5, 1, 12, 0, 0, tzinfo=tz),
        raw={
            "code": 20000,
            "msg": "success",
            "result": {
                "pincode": "87654321",
                "deadLine": "2026/05/01 12:00:00",
                "qRcode": None,
                "checkCode": None,
            },
        },
        qrcode_base64=qrcode_base64,
    )


class FakeApiClient:
    instances_created = 0

    def __init__(self, *, raises: Exception | None = None):
        self._raises = raises
        self.calls: list[dict] = []

    def upload(self, path: str, user: str = " ", email: str = " ", spec=None):
        self.calls.append(
            {"path": path, "user": user, "email": email, "spec": spec}
        )
        if self._raises is not None:
            raise self._raises
        return _make_result()


@pytest.fixture
def install_fake_client(monkeypatch):
    created: list[FakeApiClient] = []

    def install(raises: Exception | None = None) -> FakeApiClient:
        client = FakeApiClient(raises=raises)
        created.append(client)

        def _factory(*args, **kwargs):
            FakeApiClient.instances_created += 1
            return client

        FakeApiClient.instances_created = 0
        monkeypatch.setattr(api_module, "IbonClient", _factory)
        return client

    return install


@pytest.fixture
def client() -> TestClient:
    return TestClient(api_module.app)


def test_upload_success_returns_expected_schema(install_fake_client, client, sample_pdf: Path):
    install_fake_client()
    with sample_pdf.open("rb") as fh:
        resp = client.post("/upload", files={"file": ("sample.pdf", fh, "application/pdf")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pincode"] == "87654321"
    assert body["deadline"] == "2026-05-01T12:00:00+08:00"
    # 未指定時應為 FNOMAL（不預選規格）。
    assert body["select_type"] == "FNOMAL"
    # 帶上 client 端產生的 QR Code base64
    assert body["qrcode_base64"] == _FAKE_PNG_B64


def test_upload_response_qrcode_empty_on_generation_failure(
    install_fake_client, client, sample_pdf: Path, monkeypatch
):
    install_fake_client()
    # 把 fake client 改成回傳空 QR
    monkeypatch.setattr(
        FakeApiClient,
        "upload",
        lambda self, path, user=" ", email=" ", spec=None: _make_result(
            qrcode_base64=""
        ),
    )
    with sample_pdf.open("rb") as fh:
        resp = client.post("/upload", files={"file": ("sample.pdf", fh, "application/pdf")})
    assert resp.status_code == 200
    assert resp.json()["qrcode_base64"] == ""


def test_upload_forwards_select_type_form_field(install_fake_client, client, sample_pdf: Path):
    fake = install_fake_client()
    with sample_pdf.open("rb") as fh:
        resp = client.post(
            "/upload",
            files={"file": ("sample.pdf", fh, "application/pdf")},
            data={"select_type": "FA3CN2"},
        )
    assert resp.status_code == 200
    assert resp.json()["select_type"] == "FA3CN2"
    assert fake.calls[0]["spec"].select_type == "FA3CN2"


def test_upload_forwards_name_email_form_fields(install_fake_client, client, sample_pdf: Path):
    fake = install_fake_client()
    with sample_pdf.open("rb") as fh:
        resp = client.post(
            "/upload",
            files={"file": ("sample.pdf", fh, "application/pdf")},
            data={"name": "陳大寶", "email": "a@b.com"},
        )
    assert resp.status_code == 200
    assert fake.calls[0]["user"] == "陳大寶"
    assert fake.calls[0]["email"] == "a@b.com"


def test_upload_missing_file_returns_422(install_fake_client, client):
    install_fake_client()
    resp = client.post("/upload")
    assert resp.status_code == 422


def test_upload_validation_error_returns_400(install_fake_client, client, sample_pdf: Path):
    install_fake_client(raises=IbonValidationError("too big"))
    with sample_pdf.open("rb") as fh:
        resp = client.post("/upload", files={"file": ("sample.pdf", fh, "application/pdf")})
    assert resp.status_code == 400
    assert resp.json() == {"detail": "too big"}


def test_upload_request_error_returns_502(install_fake_client, client, sample_pdf: Path):
    install_fake_client(raises=IbonRequestError("upstream"))
    with sample_pdf.open("rb") as fh:
        resp = client.post("/upload", files={"file": ("sample.pdf", fh, "application/pdf")})
    assert resp.status_code == 502
    assert resp.json() == {"detail": "upstream"}


def test_healthz_returns_ok_without_calling_ibon(install_fake_client, client):
    install_fake_client()
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert FakeApiClient.instances_created == 0


def test_temp_file_removed_after_upload(install_fake_client, client, sample_pdf: Path, monkeypatch, tmp_path: Path):
    install_fake_client()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    before = set(tmp_path.iterdir()) if tmp_path.exists() else set()
    with sample_pdf.open("rb") as fh:
        resp = client.post("/upload", files={"file": ("sample.pdf", fh, "application/pdf")})
    assert resp.status_code == 200
    after = set(tmp_path.iterdir())
    # 請求結束後不應殘留任何暫存檔。
    assert after == before
