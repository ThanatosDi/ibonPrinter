## Why

ibon 雲端列印於新 API 改版後，`GetPincode` 回應中 `qRcode` 欄位永遠為 `null` —
取件編號不再附帶 QR Code 圖片。對於需要顯示 QR Code 的下游（CLI 列印、API 給前端
嵌入 `<img>`、LINE Bot 等）這代表 caller 必須自行處理 QR Code 產生。

把 QR Code 產生封裝在 `IbonClient.upload()` 裡集中處理，可以讓所有 caller 拿到一致
的結果格式，不必各自引入 qrcode/Pillow 並重複實作。

## What Changes

- 新增執行期相依：`qrcode[pil]`（含 Pillow，用於產出 PNG bytes）。
- `IbonClient.upload()` 在拿到 pincode 後，於記憶體中以 `qrcode` 函式庫產生 PNG，
  並將 raw bytes 與 base64 字串放入 `IbonUploadResult`。
- **BREAKING**（雖屬未發行版本內的調整）：`IbonUploadResult` 新增兩個欄位：
  - `qrcode_png: bytes` — PNG 原始 bytes
  - `qrcode_base64: str` — `qrcode_png` 的 base64 字串（不含 data URI 前綴）
- HTTP API `UploadResponse` 新增 `qrcode_base64: str`，方便前端直接以
  `data:image/png;base64,...` 嵌入。
- CLI 沿用文字／JSON 模式：文字模式不顯示 QR（避免在 stdout 印出超大 base64），
  JSON 模式 `qrcode_base64` 會出現在輸出中；保留可選 `--qr-out PATH` 讓使用者把
  PNG 寫到指定檔案。
- `qrcode` 產生失敗（例：不可預期的環境問題）視為非致命：仍回傳 pincode，但
  `qrcode_png` 與 `qrcode_base64` 為 `b""`／`""`，並透過 `warnings.warn` 提示。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities
- `ibon-upload-core`: `IbonUploadResult` schema 新增 `qrcode_png` 與 `qrcode_base64`
  欄位；`upload()` 流程在最後一步補上「以 pincode 在記憶體中產生 QR Code PNG」的需求。
- `ibon-upload-api`: `UploadResponse` schema 新增 `qrcode_base64` 欄位。
- `ibon-upload-cli`: `--qr-out` 旗標重新出現，把 PNG 寫到指定路徑；JSON 模式輸出
  新增 `qrcode_base64`。

## Impact

- **新依賴**：`qrcode[pil]` 加入 `pyproject.toml` / `requirements.txt`；Pillow 為
  間接相依。
- **程式碼**：
  - `ibon_printer/client.py` — `IbonUploadResult` 多兩欄；`IbonClient.upload()` 末段
    加上 QR 產生。
  - `ibon_printer/api.py` — `UploadResponse` 多 `qrcode_base64`；handler 直接帶過去。
  - `ibon_printer/cli.py` — 重新加回 `--qr-out`；`_format_json` 多 `qrcode_base64`。
- **測試**：擴充 `test_client_upload.py`、`test_api.py`、`test_cli.py`；新增針對
  QR PNG bytes 為 `b"\x89PNG..."` 起頭、base64 解碼後與 PNG bytes 相同的斷言。
- **文件**：README 在 `IbonUploadResult`、API response、CLI 說明處補上 `qrcode_*`
  欄位與 `--qr-out` 範例。
- 不影響既有 ibon API 呼叫；純粹是 client 端在 happy path 之後做一次本機計算。
