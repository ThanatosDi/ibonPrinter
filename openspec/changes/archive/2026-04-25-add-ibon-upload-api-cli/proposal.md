## Why

The repo currently exposes ibon 雲端列印 uploads only through a small `IBON` class and a bare-bones `cli.py` that does not print results or validate inputs. There is no HTTP-service entry point, no file-size/extension validation, and no QR-code output for end users. We want one cohesive package that drives the ibon upload flow from both a local CLI and a remote HTTP API so other tooling (bots, automations, internal services) can reuse it.

## What Changes

- Refactor the existing upload logic into a reusable core module (`ibon_printer/client.py`) that preserves the 3-step ibon flow: **get hash → upload file → request pincode**.
- Add file-level validation (extension whitelist per ibon rules: doc/docx/ppt/pptx/xls/xlsx/txt/ini/pdf/jpg/gif/bmp; max 10 MB).
- Replace the current `cli.py` with a full CLI (`ibon_printer/cli.py`) that prints `Pincode`, `DeadLine`, `FileDate`, and saves `FileQrcode` (base64 PNG) to disk. Exits non-zero on failure with human-readable error.
- Add an HTTP API (`ibon_printer/api.py`) built on FastAPI exposing `POST /upload` (multipart file + optional name/email) returning JSON with pincode, deadline, and either base64 or a PNG URL for the QR code. Include `GET /healthz`.
- Package entry points via `pyproject.toml`: `ibon-printer` (CLI) and `ibon-printer-api` (uvicorn launcher).
- **BREAKING**: The top-level `ibonPrinter.IBON` import path is retained as a thin shim; new code should import from `ibon_printer`. Existing `cli.py` at repo root is removed in favor of the package-based entry point.

## Capabilities

### New Capabilities
- `ibon-upload-core`: Shared client library that performs the 3-step ibon upload flow with validation and typed results.
- `ibon-upload-cli`: Command-line interface that uploads a file and prints/saves the pincode + QR code.
- `ibon-upload-api`: HTTP API that accepts a multipart upload and returns pincode metadata as JSON.

### Modified Capabilities
<!-- None: no existing specs in openspec/specs/ to modify -->

## Impact

- **Code**: adds `ibon_printer/` package; legacy `ibonPrinter.py` becomes a compatibility shim; `cli.py` at repo root is removed.
- **Dependencies**: adds `fastapi`, `uvicorn`, `python-multipart`, and `click` (or retains `argparse`) to `requirements.txt`; pins a tested `requests` version.
- **External contract**: calls `https://printadmin.ibon.com.tw/IbonUpload/IbonUpload/{FileUpload,LocalFileUpload,IbonFileUpload}`; no new third-party services.
- **Packaging**: introduces `pyproject.toml` with console-script entry points.
- **Risk**: ibon endpoints are undocumented and can change without notice; the client must fail loudly with actionable error messages.
