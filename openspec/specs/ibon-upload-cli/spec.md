# ibon-upload-cli Specification

## Purpose

Command-line interface for the ibon upload core client. Provides a single-shot `ibon-printer` console script that uploads a file, saves the returned QR-code PNG, and reports pincode metadata to stdout (human-readable or JSON).

## Requirements

### Requirement: CLI entry point

The package SHALL install a console script named `ibon-printer` that uploads a single file and reports the result to stdout.

#### Scenario: Successful upload prints pincode
- **WHEN** the user runs `ibon-printer ./report.pdf`
- **THEN** the CLI exits with status `0`
- **AND** stdout contains `Pincode`, `DeadLine`, `FileDate`, and the path of the saved QR-code PNG

#### Scenario: Optional user/email flags are forwarded
- **WHEN** the user runs `ibon-printer ./report.pdf --name 陳大寶 --email me@example.com`
- **THEN** the CLI calls the core client with `user="陳大寶"` and `email="me@example.com"` so ibon emails the pincode/QR to the user

### Requirement: QR-code artifact is written to disk

The CLI SHALL save the client-generated QR Code as a PNG file when (and only when) the user supplies `--qr-out PATH`, so disk writes are explicit. The PNG bytes SHALL be obtained by `base64.b64decode(result.qrcode_base64)`, not from a separate ibon response.

#### Scenario: Custom output path
- **WHEN** the user runs `ibon-printer ./report.pdf --qr-out /tmp/code.png`
- **THEN** the CLI writes `base64.b64decode(result.qrcode_base64)` (raw PNG bytes) to `/tmp/code.png`
- **AND** the human-readable text output includes a line `QR PNG: /tmp/code.png`

#### Scenario: No --qr-out supplied
- **WHEN** the user runs `ibon-printer ./report.pdf` without `--qr-out`
- **THEN** the CLI does NOT write any QR Code file to disk
- **AND** the human-readable text output omits the `QR PNG:` line

#### Scenario: QR Code generation failure
- **WHEN** the upload succeeds but the in-memory QR Code generation produced empty bytes
- **AND** the user supplied `--qr-out /tmp/code.png`
- **THEN** the CLI writes a zero-byte file at `/tmp/code.png` and prints a stderr warning explaining QR Code generation failed

### Requirement: Clear error reporting

The CLI SHALL translate exceptions from the core client into human-readable messages on stderr and a non-zero exit code.

#### Scenario: Validation error
- **WHEN** the selected file exceeds 10 MB or has an unsupported extension
- **THEN** the CLI writes the error message to stderr and exits with status `2`

#### Scenario: Network or server error
- **WHEN** the core client raises `IbonRequestError`
- **THEN** the CLI writes the underlying `Message` (Chinese text from ibon, if any) to stderr and exits with status `1`

### Requirement: JSON output mode

The CLI SHALL support a `--json` flag that emits the result as a single JSON line on stdout for scripting.

#### Scenario: JSON mode without QR file
- **WHEN** the user runs `ibon-printer ./report.pdf --json`
- **THEN** stdout contains a single JSON object with keys `pincode`, `deadline`, `select_type`, and `qrcode_base64`
- **AND** `qrcode_base64` is the base64 encoding of the in-memory QR Code PNG bytes (empty string if generation failed)
- **AND** no human-readable text is printed

#### Scenario: JSON mode with --qr-out
- **WHEN** the user runs `ibon-printer ./report.pdf --qr-out /tmp/code.png --json`
- **THEN** the JSON object additionally includes `qrcode_path: "/tmp/code.png"`
