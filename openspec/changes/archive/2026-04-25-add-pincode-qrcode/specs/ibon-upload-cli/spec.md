## MODIFIED Requirements

### Requirement: QR-code artifact is written to disk

The CLI SHALL save the client-generated QR Code as a PNG file when (and only when) the user supplies `--qr-out PATH`, so disk writes are explicit. The PNG bytes SHALL come from the in-memory `qrcode_png` field of the upload result, not from a separate ibon response.

#### Scenario: Custom output path
- **WHEN** the user runs `ibon-printer ./report.pdf --qr-out /tmp/code.png`
- **THEN** the CLI writes `result.qrcode_png` (raw PNG bytes) to `/tmp/code.png`
- **AND** the human-readable text output includes a line `QR PNG: /tmp/code.png`

#### Scenario: No --qr-out supplied
- **WHEN** the user runs `ibon-printer ./report.pdf` without `--qr-out`
- **THEN** the CLI does NOT write any QR Code file to disk
- **AND** the human-readable text output omits the `QR PNG:` line

#### Scenario: QR Code generation failure
- **WHEN** the upload succeeds but the in-memory QR Code generation produced empty bytes
- **AND** the user supplied `--qr-out /tmp/code.png`
- **THEN** the CLI writes a zero-byte file at `/tmp/code.png` and prints a stderr warning explaining QR Code generation failed

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
