"""FastAPI HTTP 服務：以 multipart 形式包裝 IbonClient 上傳流程。"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from contextlib import contextmanager
from typing import Iterator, Sequence

import requests
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .client import IbonClient, IbonUploadResult, PrintSpec
from .errors import IbonRequestError, IbonValidationError


class UploadResponse(BaseModel):
    pincode: str
    deadline: str
    select_type: str = "FNOMAL"
    spec_description: str | None = None
    qrcode_base64: str = ""


def _to_response(result: IbonUploadResult, spec: PrintSpec) -> UploadResponse:
    return UploadResponse(
        pincode=result.pincode,
        deadline=result.deadline.isoformat(),
        select_type=spec.select_type,
        spec_description=spec.description or None,
        qrcode_base64=result.qrcode_base64,
    )


@contextmanager
def _spool_upload(file: UploadFile) -> Iterator[str]:
    suffix = ""
    if file.filename:
        suffix = os.path.splitext(file.filename)[1]
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := file.file.read(1024 * 1024):
                out.write(chunk)
        yield path
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(IbonValidationError)
    async def _validation(_: Request, exc: IbonValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(IbonRequestError)
    async def _request(_: Request, exc: IbonRequestError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(requests.RequestException)
    async def _transport(_: Request, exc: requests.RequestException) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})


app = FastAPI(title="ibon-printer API")
_register_error_handlers(app)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


def _resolve_spec(select_type: str | None) -> PrintSpec:
    if not select_type or select_type.strip() in ("", "FNOMAL"):
        return PrintSpec.default()
    return PrintSpec(select_type.strip(), description=select_type.strip())


@app.post("/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    name: str = Form(" "),
    email: str = Form(" "),
    select_type: str = Form("FNOMAL"),
) -> UploadResponse:
    spec = _resolve_spec(select_type)
    with _spool_upload(file) as spool_path:
        client = IbonClient()
        result = client.upload(spool_path, user=name, email=email, spec=spec)
    return _to_response(result, spec)


def run(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ibon-printer-api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    import uvicorn

    uvicorn.run("ibon_printer.api:app", host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    run(sys.argv[1:])
