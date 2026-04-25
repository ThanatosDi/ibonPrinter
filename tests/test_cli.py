"""CLI 行為測試：文字／JSON 輸出、錯誤退出碼。"""
from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from ibon_printer import cli as cli_module
from ibon_printer.client import IbonUploadResult
from ibon_printer.errors import IbonRequestError, IbonValidationError


_FAKE_PNG = b"\x89PNG\r\n\x1a\nfake-cli-png"
_FAKE_PNG_B64 = base64.b64encode(_FAKE_PNG).decode("ascii")


def _make_result(*, qrcode_base64: str = _FAKE_PNG_B64) -> IbonUploadResult:
    tz = ZoneInfo("Asia/Taipei")
    return IbonUploadResult(
        pincode="12345678",
        deadline=datetime(2026, 5, 1, 12, 0, 0, tzinfo=tz),
        raw={
            "code": 20000,
            "msg": "success",
            "result": {
                "pincode": "12345678",
                "deadLine": "2026/05/01 12:00:00",
                "qRcode": None,
                "checkCode": None,
            },
        },
        qrcode_base64=qrcode_base64,
    )


class FakeClient:
    def __init__(
        self,
        *,
        raises: Exception | None = None,
        result: IbonUploadResult | None = None,
    ):
        self._raises = raises
        self._result = result
        self.upload_calls: list[dict] = []

    def upload(self, path: str, user: str = " ", email: str = " ", spec=None):
        self.upload_calls.append(
            {"path": path, "user": user, "email": email, "spec": spec}
        )
        if self._raises is not None:
            raise self._raises
        return self._result if self._result is not None else _make_result()


@pytest.fixture
def fake_client_factory(monkeypatch):
    created: list[FakeClient] = []

    def install(
        raises: Exception | None = None,
        result: IbonUploadResult | None = None,
    ) -> FakeClient:
        client = FakeClient(raises=raises, result=result)
        created.append(client)
        monkeypatch.setattr(cli_module, "IbonClient", lambda *a, **kw: client)
        return client

    return install


def test_cli_happy_path_text_output(fake_client_factory, sample_pdf: Path, capsys):
    fake_client_factory()
    rc = cli_module.main([str(sample_pdf)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "取件編號" in out
    assert "12345678" in out
    assert "列印期限" in out


def test_cli_forwards_name_email(fake_client_factory, sample_pdf: Path):
    client = fake_client_factory()
    rc = cli_module.main([str(sample_pdf), "--name", "陳大寶", "--email", "a@b.com"])
    assert rc == 0
    assert client.upload_calls[0]["user"] == "陳大寶"
    assert client.upload_calls[0]["email"] == "a@b.com"


def test_cli_json_mode(fake_client_factory, sample_pdf: Path, capsys):
    fake_client_factory()
    rc = cli_module.main([str(sample_pdf), "--json"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    # JSON 模式應為單行輸出。
    assert "\n" not in out
    data = json.loads(out)
    assert data["pincode"] == "12345678"
    assert data["deadline"].startswith("2026-05-01T12:00:00")


def test_cli_validation_error_exit_2(fake_client_factory, sample_pdf: Path, capsys):
    fake_client_factory(raises=IbonValidationError("檔案太大"))
    rc = cli_module.main([str(sample_pdf)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "檔案太大" in err


def test_cli_request_error_exit_1(fake_client_factory, sample_pdf: Path, capsys):
    fake_client_factory(raises=IbonRequestError("upstream", result_code="99"))
    rc = cli_module.main([str(sample_pdf)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "upstream" in err


def test_cli_default_spec_is_fnomal(fake_client_factory, sample_pdf: Path):
    client = fake_client_factory()
    rc = cli_module.main([str(sample_pdf)])
    assert rc == 0
    assert client.upload_calls[0]["spec"].select_type == "FNOMAL"


def test_cli_alias_resolves_to_select_type(fake_client_factory, sample_pdf: Path, capsys):
    client = fake_client_factory()
    rc = cli_module.main([str(sample_pdf), "--spec", "a3-color-duplex"])
    assert rc == 0
    assert client.upload_calls[0]["spec"].select_type == "FA3CN2"
    out = capsys.readouterr().out
    assert "列印規格" in out
    assert "A3" in out


def test_cli_passes_raw_select_type(fake_client_factory, sample_pdf: Path):
    client = fake_client_factory()
    rc = cli_module.main([str(sample_pdf), "--spec", "FA4CS2"])
    assert rc == 0
    assert client.upload_calls[0]["spec"].select_type == "FA4CS2"


def test_cli_json_includes_select_type(fake_client_factory, sample_pdf: Path, capsys):
    fake_client_factory()
    rc = cli_module.main([str(sample_pdf), "--spec", "a4-color", "--json"])
    assert rc == 0
    import json as _json

    data = _json.loads(capsys.readouterr().out.strip())
    assert data["select_type"] == "FA4CN1"
    assert "spec_description" in data


def test_cli_qr_out_writes_png_bytes(fake_client_factory, sample_pdf: Path, tmp_path: Path):
    fake_client_factory()
    target = tmp_path / "x.png"
    rc = cli_module.main([str(sample_pdf), "--qr-out", str(target)])
    assert rc == 0
    assert target.read_bytes() == _FAKE_PNG


def test_cli_no_qr_out_does_not_write_file(fake_client_factory, sample_pdf: Path, tmp_path: Path, monkeypatch, capsys):
    fake_client_factory()
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    rc = cli_module.main([str(sample_pdf)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "QR PNG" not in out
    # 不應有任何新檔產生。
    assert set(tmp_path.iterdir()) == before


def test_cli_text_output_includes_qr_path_when_qr_out_given(
    fake_client_factory, sample_pdf: Path, tmp_path: Path, capsys
):
    fake_client_factory()
    target = tmp_path / "out.png"
    rc = cli_module.main([str(sample_pdf), "--qr-out", str(target)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "QR PNG" in out
    assert str(target) in out


def test_cli_json_includes_qrcode_base64(fake_client_factory, sample_pdf: Path, capsys):
    fake_client_factory()
    rc = cli_module.main([str(sample_pdf), "--json"])
    assert rc == 0
    import json as _json

    data = _json.loads(capsys.readouterr().out.strip())
    assert data["qrcode_base64"] == _FAKE_PNG_B64


def test_cli_json_with_qr_out_includes_qrcode_path(
    fake_client_factory, sample_pdf: Path, tmp_path: Path, capsys
):
    fake_client_factory()
    target = tmp_path / "code.png"
    rc = cli_module.main([str(sample_pdf), "--qr-out", str(target), "--json"])
    assert rc == 0
    import json as _json

    data = _json.loads(capsys.readouterr().out.strip())
    assert data["qrcode_path"] == str(target)


def test_cli_qr_out_failure_writes_zero_byte_and_warns(
    fake_client_factory, sample_pdf: Path, tmp_path: Path, capsys
):
    fake_client_factory(result=_make_result(qrcode_base64=""))
    target = tmp_path / "fail.png"
    rc = cli_module.main([str(sample_pdf), "--qr-out", str(target)])
    assert rc == 0
    assert target.read_bytes() == b""
    err = capsys.readouterr().err
    assert "QR Code generation failed" in err
