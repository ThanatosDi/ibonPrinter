## MODIFIED Requirements

### Requirement: HTTP upload endpoint

The package SHALL expose an HTTP API with a `POST /upload` endpoint that accepts a multipart-encoded file and returns the ibon pincode metadata together with a client-generated QR Code as JSON.

#### Scenario: Successful upload via multipart
- **WHEN** a client POSTs `multipart/form-data` with field `file=@report.pdf` and optional form fields `name`, `email` to `/upload`
- **THEN** the API returns `200 OK` with a JSON body containing `pincode: str`, `deadline: ISO8601 str`, and `qrcode_base64: str`
- **AND** `qrcode_base64` is the base64-encoded PNG of the pincode QR Code that the API server generated locally (not relayed from ibon)
- **AND** the value is suitable for embedding via `<img src="data:image/png;base64,{qrcode_base64}">`

#### Scenario: QR Code field is always present even on generation failure
- **WHEN** the upload pipeline succeeds but client-side QR Code generation fails
- **THEN** the response body still includes `qrcode_base64`, but its value is the empty string `""`

#### Scenario: Missing file field
- **WHEN** the request omits the `file` field
- **THEN** the API returns `422 Unprocessable Entity` with a FastAPI-style validation error body
