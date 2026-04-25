"""ibon_printer.errors 例外型別的測試。"""
from __future__ import annotations

from ibon_printer.errors import IbonRequestError, IbonValidationError


def test_validation_error_is_exception():
    assert issubclass(IbonValidationError, Exception)
    err = IbonValidationError("bad file")
    assert isinstance(err, Exception)


def test_request_error_carries_fields():
    err = IbonRequestError("msg", status_code=502, result_code="99")
    assert err.status_code == 502
    assert err.result_code == "99"
    assert err.message == "msg"


def test_request_error_str_includes_message():
    err = IbonRequestError("server blew up", status_code=500, result_code="99")
    assert "server blew up" in str(err)


def test_request_error_optional_fields_default_to_none():
    err = IbonRequestError("just a message")
    assert err.status_code is None
    assert err.result_code is None
    assert err.message == "just a message"
