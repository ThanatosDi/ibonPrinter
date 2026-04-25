## ADDED Requirements

### Requirement: Three-step ibon upload flow

The core client SHALL perform the ibon upload as three sequential HTTP POST calls and expose a single high-level `upload(path, user, email)` method that orchestrates them.

#### Scenario: Happy-path upload returns pincode payload
- **WHEN** `upload("receipt.pdf", user="陳大寶", email="a@b.com")` is called with a valid file
- **THEN** the client POSTs `{"hash": ""}` to `https://printadmin.ibon.com.tw/IbonUpload/IbonUpload/FileUpload` and extracts the returned `Hash`
- **AND** POSTs the file as multipart together with `fileName` and `hash` to `.../IbonUpload/LocalFileUpload`
- **AND** POSTs `{hash, user, email}` to `.../IbonUpload/IbonFileUpload`
- **AND** returns a typed result containing `Pincode`, `DeadLine`, `FileQrcode` (base64 PNG), `FileDate`, `ResultCode`, and `Message`

#### Scenario: Hash step fails
- **WHEN** the `FileUpload` step returns `ResultCode != "00"` or a non-JSON response
- **THEN** the client raises `IbonRequestError` with the server `Message` (or HTTP status) and does NOT attempt the remaining steps

#### Scenario: File upload step fails
- **WHEN** the `LocalFileUpload` step returns `ResultCode != "00"`
- **THEN** the client raises `IbonRequestError` with the server `Message` and does NOT call `IbonFileUpload`

### Requirement: File validation before upload

The core client SHALL validate the input file before making any network request.

#### Scenario: Unsupported extension
- **WHEN** `upload("picture.heic", ...)` is called
- **THEN** the client raises `IbonValidationError` with a message listing the allowed extensions (doc, docx, ppt, pptx, xls, xlsx, txt, ini, pdf, jpg, gif, bmp)

#### Scenario: File too large
- **WHEN** the input file exceeds 10 MB
- **THEN** the client raises `IbonValidationError` stating the 10 MB limit and the observed size

#### Scenario: File does not exist
- **WHEN** `upload("/no/such/file.pdf", ...)` is called
- **THEN** the client raises `IbonValidationError` with message `"File not found: /no/such/file.pdf"`

### Requirement: Configurable transport

The core client SHALL accept an injected `requests.Session` (or equivalent) and a configurable timeout so tests and API hosts can control retries, proxies, and connection pooling.

#### Scenario: Default session
- **WHEN** the client is constructed without arguments
- **THEN** it creates a `requests.Session` with a desktop Chrome `User-Agent` header and a 10-second timeout

#### Scenario: Injected session
- **WHEN** the client is constructed with `IbonClient(session=my_session, timeout=30)`
- **THEN** all three upload calls reuse `my_session` and apply the 30-second timeout

### Requirement: Typed result object

The core client SHALL return a dataclass (or `TypedDict`) rather than a raw dict so callers get attribute access and IDE autocomplete.

#### Scenario: Result shape
- **WHEN** `upload(...)` succeeds
- **THEN** the returned object exposes `.pincode: str`, `.deadline: datetime`, `.qrcode_png: bytes`, `.file_date: datetime`, `.raw: dict` fields
- **AND** `qrcode_png` is the base-64-decoded PNG image bytes (not the base64 string)
