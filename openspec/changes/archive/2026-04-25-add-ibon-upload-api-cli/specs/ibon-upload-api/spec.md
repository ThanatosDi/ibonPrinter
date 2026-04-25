## ADDED Requirements

### Requirement: HTTP upload endpoint

The package SHALL expose an HTTP API with a `POST /upload` endpoint that accepts a multipart-encoded file and returns the ibon pincode metadata as JSON.

#### Scenario: Successful upload via multipart
- **WHEN** a client POSTs `multipart/form-data` with field `file=@report.pdf` and optional form fields `name`, `email` to `/upload`
- **THEN** the API returns `200 OK` with a JSON body `{"pincode": str, "deadline": ISO8601 str, "file_date": ISO8601 str, "qrcode_base64": str}`
- **AND** `qrcode_base64` is the raw base64 PNG string returned by ibon (unchanged)

#### Scenario: Missing file field
- **WHEN** the request omits the `file` field
- **THEN** the API returns `422 Unprocessable Entity` with a FastAPI-style validation error body

### Requirement: Validation errors surface as 4xx

The API SHALL map `IbonValidationError` from the core client to HTTP `400 Bad Request` so clients can distinguish user errors from ibon-side errors.

#### Scenario: Oversize upload
- **WHEN** the uploaded file exceeds 10 MB
- **THEN** the API returns `400` with body `{"detail": "File exceeds 10 MB limit (actual: <N> bytes)"}`

#### Scenario: Unsupported extension
- **WHEN** the uploaded filename has a disallowed extension
- **THEN** the API returns `400` with body `{"detail": "Unsupported file extension: <ext>. Allowed: doc, docx, ppt, pptx, xls, xlsx, txt, ini, pdf, jpg, gif, bmp"}`

### Requirement: Upstream errors surface as 502

The API SHALL map `IbonRequestError` to HTTP `502 Bad Gateway` because ibon is an upstream dependency, not the caller's fault.

#### Scenario: Ibon returns non-zero ResultCode
- **WHEN** any of the three ibon calls returns `ResultCode != "00"`
- **THEN** the API returns `502` with body `{"detail": "<ibon Message>"}` and logs the full response server-side

### Requirement: Health probe

The API SHALL expose `GET /healthz` for liveness checks.

#### Scenario: Health probe
- **WHEN** a client calls `GET /healthz`
- **THEN** the API returns `200 OK` with body `{"status": "ok"}`
- **AND** the handler performs NO network call to ibon

### Requirement: Console-script launcher

The package SHALL install an `ibon-printer-api` console script that starts the API with uvicorn on a configurable host/port.

#### Scenario: Default launch
- **WHEN** the user runs `ibon-printer-api`
- **THEN** uvicorn binds `127.0.0.1:8000` and serves the FastAPI app

#### Scenario: Custom host/port via flags
- **WHEN** the user runs `ibon-printer-api --host 0.0.0.0 --port 9000`
- **THEN** uvicorn binds `0.0.0.0:9000`
