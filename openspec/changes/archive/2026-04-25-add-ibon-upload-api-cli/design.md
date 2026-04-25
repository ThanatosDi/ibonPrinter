## Context

The existing repo ships `ibonPrinter.py` (a 60-line `IBON` class) and `cli.py` (argparse skeleton that ignores the return value). The upload flow itself is already understood from the existing code and from historical observation of the site:

1. `POST https://printadmin.ibon.com.tw/IbonUpload/IbonUpload/FileUpload` with JSON `{"hash": ""}` → returns `{"Hash": "...", "ResultCode": "00", ...}`.
2. `POST https://printadmin.ibon.com.tw/IbonUpload/IbonUpload/LocalFileUpload` as `multipart/form-data` with fields `hash`, `fileName` and file payload → returns `{"ResultCode": "00", ...}`.
3. `POST https://printadmin.ibon.com.tw/IbonUpload/IbonUpload/IbonFileUpload` as form-encoded body `hash`, `user`, `email` → returns `{"Pincode", "DeadLine", "FileQrcode", "FileDate", "ResultCode": "00", "Message"}`.

`FileQrcode` is a base64-encoded PNG. `DeadLine` and `FileDate` are strings of the form `YYYY/MM/DD HH:MM:SS` in the Asia/Taipei timezone.

We want the same flow reachable through both a CLI and an HTTP API without duplicating transport code.

## Goals / Non-Goals

**Goals:**
- One client module reused by CLI and API.
- Fail fast with clear errors for files ibon will reject (extension/size).
- Typed result (dataclass) instead of a raw dict.
- Installable package with two console scripts.
- Zero regression in upload behavior vs. the current `IBON` class.

**Non-Goals:**
- Multi-file / batch uploads (ibon portal itself is single-file).
- Browser automation or login. This change only targets the public upload flow that does not require authentication.
- Persistent storage of uploads, pincodes, or QR images on the API side — the endpoint is stateless.
- Rate limiting, auth, HTTPS termination for the API — leave those to the deployment layer.
- Windows-installer or distro packaging beyond a plain `pip install .`.

## Decisions

### 1. Layout: `ibon_printer/` package, not flat modules
- **Decision**: Create a package `ibon_printer/` with `client.py`, `cli.py`, `api.py`, `errors.py`, `__init__.py`. Keep the old `ibonPrinter.py` as a one-line shim: `from ibon_printer.client import IbonClient as IBON`.
- **Why**: Two entry points (CLI, API) sharing one transport module beats either (a) duplicating the flow or (b) stacking more code into the old flat file.
- **Alternative**: Keep `ibonPrinter.py` flat and put CLI/API next to it. Rejected — three modules at repo root crowd the surface.

### 2. HTTP framework: FastAPI + uvicorn
- **Decision**: FastAPI for the API, launched with uvicorn.
- **Why**: Multipart handling and typed request/response come for free; auto `/docs` helps us hand off to other consumers; widely deployed.
- **Alternative**: Flask — viable but we'd hand-roll schemas and docs. Starlette alone — too low-level for the small savings.

### 3. CLI framework: `argparse` (stdlib)
- **Decision**: Stay on `argparse`. One positional `file`, four flags (`--name`, `--email`, `--qr-out`, `--json`).
- **Why**: No new runtime dep, matches existing `cli.py`, flag surface is tiny.
- **Alternative**: `click`/`typer` — nicer ergonomics but unjustified for ~5 flags.

### 4. Result type: `@dataclass IbonUploadResult`
- **Decision**: Return a frozen dataclass with parsed types (`datetime` for dates, `bytes` for decoded PNG) and a `.raw: dict` escape hatch.
- **Why**: Attribute access for callers; parsing once at the edge keeps downstream code clean.
- **Alternative**: Return the raw `dict`. Rejected — pushes parsing onto every caller; Windows filename from `FileDate` would be re-parsed repeatedly.

### 5. Error model
- **Decision**: Two exception types in `ibon_printer/errors.py`:
  - `IbonValidationError` — local preflight failures (missing file, bad extension, too large).
  - `IbonRequestError` — anything the server returned or transport-level failures; carries `.status_code`, `.result_code`, `.message`.
- **Why**: Callers (especially the API layer) need to distinguish 4xx-worthy input problems from 5xx-worthy upstream problems.

### 6. File-size check: stream stat before read
- **Decision**: Check `os.path.getsize(path) > 10 * 1024 * 1024` before opening the file. The `requests` multipart body then streams without a second sizing pass.
- **Why**: Avoids reading a huge file into RAM just to reject it.

### 7. API contract: return base64 string, not binary PNG
- **Decision**: `POST /upload` returns `qrcode_base64` (the untouched base64 string from ibon) in a JSON body. No binary response.
- **Why**: Easy to embed via `<img src="data:image/png;base64,...">`; JSON keeps the contract uniform. A future `GET /upload/{id}/qr.png` could serve a decoded PNG, but we have no storage layer, so skip it now.

### 8. Packaging: `pyproject.toml` (PEP 621)
- **Decision**: Add a minimal `pyproject.toml` with `project.scripts`:
  ```
  ibon-printer = "ibon_printer.cli:main"
  ibon-printer-api = "ibon_printer.api:run"
  ```
- **Why**: Standard install path (`pip install .`) and registers both console scripts in one place.

### 9. Timezone handling
- **Decision**: Parse `DeadLine` and `FileDate` as naive `datetime` and attach `ZoneInfo("Asia/Taipei")`.
- **Why**: ibon renders these in TPE time; attaching the tz prevents the ISO output from misleading API consumers.

## Risks / Trade-offs

- **[ibon endpoints are undocumented and may change]** → Keep URLs and payload shapes in one module (`client.py`) and add a smoke test (manual, not CI) to re-check after upstream UI changes. Surface the raw `Message` in errors so breakage is diagnosable without repo inspection.
- **[Uploading user files through a relay API raises privacy concerns]** → Document in `README` that the API is stateless: files stream through to ibon and are not written to disk. Don't log file bytes or filenames at INFO level.
- **[Chinese encoding in error messages]** → `requests` handles JSON decoding; we forward `Message` unchanged. Ensure stderr is UTF-8 on Windows consoles (set `PYTHONIOENCODING=utf-8` in docs).
- **[10 MB is our guess, not a documented limit]** → Make the limit a module-level constant so it's one line to tweak if ibon changes it.
- **[BREAKING import path shift]** → Keep `ibonPrinter.IBON` working as a deprecation shim for one release; document removal timeline in README.

## Migration Plan

1. Add `ibon_printer/` package + `pyproject.toml` + new `requirements.txt` entries.
2. Reimplement flow in `ibon_printer/client.py`, ported from `ibonPrinter.IBON`.
3. Rewrite CLI and ship API.
4. Replace `ibonPrinter.py` contents with a shim re-exporting `IbonClient` as `IBON` and emitting a `DeprecationWarning`.
5. Delete root-level `cli.py` in the same commit as the console-script entry is registered.
6. Update `README.md` with install (`pip install .`) and both entry-point usages.
7. No data migration; no rollback plan needed — this is additive plus a shim.

## Open Questions

- Should the API's `/upload` also accept a raw binary body (`application/pdf`, etc.) in addition to multipart? Defer — multipart is enough for the immediate callers.
- Do we want a `--save-raw` CLI flag to persist the raw JSON response? Defer — easy to add later if anyone asks.
