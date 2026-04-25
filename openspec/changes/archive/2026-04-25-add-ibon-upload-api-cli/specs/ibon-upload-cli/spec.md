## ADDED Requirements

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

The CLI SHALL save the returned QR code as a PNG file so the user can scan it or attach it elsewhere.

#### Scenario: Default output path
- **WHEN** the upload of `report.pdf` succeeds and `--qr-out` is not supplied
- **THEN** the CLI writes the decoded PNG to `./report.pdf.qr.png` (next to the source file) and prints that path

#### Scenario: Custom output path
- **WHEN** `--qr-out /tmp/code.png` is supplied
- **THEN** the CLI writes the PNG to `/tmp/code.png` exactly

### Requirement: Clear error reporting

The CLI SHALL translate exceptions from the core client into human-readable messages on stderr and a non-zero exit code.

#### Scenario: Validation error
- **WHEN** the selected file exceeds 10 MB or has an unsupported extension
- **THEN** the CLI writes the error message to stderr and exits with status `2`

#### Scenario: Network or server error
- **WHEN** the core client raises `IbonRequestError`
- **THEN** the CLI writes the underlying `Message` (Chinese text from ibon, if any) to stderr and exits with status `1`

### Requirement: JSON output mode

The CLI SHALL support a `--json` flag that emits the raw response as a single JSON line on stdout for scripting.

#### Scenario: JSON mode
- **WHEN** the user runs `ibon-printer ./report.pdf --json`
- **THEN** stdout contains a single JSON object with keys `pincode`, `deadline`, `file_date`, `qrcode_path`
- **AND** no human-readable table is printed
