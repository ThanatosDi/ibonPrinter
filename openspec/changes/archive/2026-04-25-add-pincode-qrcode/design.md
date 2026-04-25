## Context

新版 ibon `GetPincode` 端點不再回傳 QR Code 圖片（`qRcode` 欄位永遠 `null`），
但 ibon 機台是用 pincode/QR 取件，下游（CLI 列印、API 給前端嵌入、LINE Bot 等）
仍需要可掃描的 QR Code。目前每個 caller 都得自己引入 `qrcode` + `Pillow`，
並重複解決 base64 轉換、相依管理、PNG bytes 處理等問題。

把 QR Code 生成集中在 `IbonClient.upload()`，可以提供一致結果格式並避免依賴
散落。產生過程純記憶體運算，不寫檔（檔案輸出由 caller 自行決定）。

`IbonUploadResult` 為 frozen dataclass，目前欄位 `pincode` / `deadline` / `raw`。
本變更新增兩個欄位：`qrcode_png: bytes` 與 `qrcode_base64: str`。

## Goals / Non-Goals

**Goals:**
- `IbonClient.upload()` 結果一律帶 QR Code（PNG bytes + base64 字串）。
- 純記憶體產生，不額外寫檔；caller 拿到 bytes 後愛存哪存哪。
- HTTP API `UploadResponse` 多帶 `qrcode_base64`，前端可直接 `data:image/png;base64`
  嵌入。
- CLI 重新支援 `--qr-out PATH`，把 PNG 寫到磁碟。
- `qrcode` 套件不可用或產生失敗時，`upload()` 不應崩潰；改回傳空 bytes/字串並
  發 `warnings.warn`，因為 pincode 本身仍有效。

**Non-Goals:**
- 不引入第三方 QR Code 服務（HTTP API、雲端產生器等）；純本機運算。
- 不支援自訂 QR Code 樣式（顏色、logo、size 等）— 用預設參數即可。如果未來
  caller 要客製，可再開新 change。
- 不在 client 內快取 QR Code；每次 `upload()` 重新生成。
- 不改變 ibon API 呼叫流程（仍是 GetEntry → GetPincode → GetChunksize → Upload）。

## Decisions

### 1. 套件選用：`qrcode[pil]`

- **Decision**: 使用 PyPI 上的 `qrcode` 套件，並以 `[pil]` extra 拉入 Pillow，
  以便輸出 PNG bytes。
- **Why**: 純 Python、活躍維護、API 簡潔（`qrcode.make(data)` 即可），是 Python
  生態系最常見的選擇。Pillow 已是大量函式庫的間接相依，不會帶來明顯肥大。
- **Alternative**: `segno`（純 Python、無 Pillow）— 較輕量但 PyPI 流行度低、
  輸出 PNG 需另外裝 `qrcode-artistic`。標準化成本不值得；維持 `qrcode[pil]`。

### 1.1 測試 fixture：`tests/qrcode_example.png`

- **Decision**: 使用使用者提供的真實 ibon QR Code 圖片（pincode `3524627893`，含
  「取件編號」標題與底部 pincode 文字裝飾）作為驗證基準。圖片已存放於
  `tests/qrcode_example.png`。
- **Why**: 這是 ibon 實際輸出的範例，能獨立驗證我們產生的 QR Code 真的可被
  scanner 讀回相同 pincode（不只是「我們自己的編碼器解我們自己的編碼」這種
  循環邏輯）。
- **驗證策略**:
  1. 用 QR 解碼器讀 `tests/qrcode_example.png`，斷言內容為 `"3524627893"`
     （確保 fixture 就是大家以為的東西）。
  2. 呼叫 `_render_qrcode_png("3524627893")`，再用同一個解碼器讀回，斷言
     內容仍為 `"3524627893"` — 完成 fixture → 實作的 round-trip。
- **不做**: 像素或 byte-for-byte 比對 ibon 範例與本地產出，因為 ibon 範例含
  外框文字裝飾，且 `qrcode` 套件版本／PIL 版本可能影響 anti-aliasing。

### 1.2 QR 解碼器選擇：`pyzbar` (dev-only)

- **Decision**: 加入 `pyzbar>=0.1.9` 至 `dependency-groups.dev`（runtime 不含），
  專門用於測試解碼。
- **Why**: 純 Python wrapper、體積小（< 100 KB）、Windows wheel 已內建 zbar.dll、
  社群最常用的 Python QR 解碼器。
- **Alternative**: `opencv-python` 的 `cv2.QRCodeDetector` — 體積大（~30 MB），
  為了測試而拉這麼多相依不划算。`qreader` — 仍依賴 pyzbar，多一層包裝。

### 2. 生成函式介面：模組層 helper `_render_qrcode_png(text: str) -> bytes`

- **Decision**: 在 `ibon_printer/client.py` 內定義 `_render_qrcode_png(text)` 私有
  helper，內部用 `qrcode.make(text)` 產 PIL `Image`，再 `image.save(BytesIO, "PNG")`
  取出 bytes。`upload()` 末段呼叫該 helper 一次，產生 bytes 後 base64 編碼。
- **Why**: 把 I/O 與 client 主流程切開，方便單元測試（直接 import helper 驗證
  PNG magic bytes）。維持為私有 `_` 前綴，不對外承諾穩定 API。
- **Alternative**: 用 dataclass `__post_init__` 自動產生 — 太隱晦，且失敗處理
  不好寫；保持顯式呼叫。

### 3. QR Code 內容：純 pincode 字串

- **Decision**: QR Code 編碼的內容就是 `pincode` 字串本身（10 碼數字）。
- **Why**: ibon 機台讀的就是 pincode；不需要包 URL、JSON 或其他結構。
- **Alternative**: 包成 URL（如 `https://print.ibon.com.tw/pickupSearch?pincode=...`）
  讓使用者掃出來能進查詢頁 — 但 ibon 機台讀的不是 URL；雙用場景不存在，且會
  讓 QR Code 變大、解析率下降。維持純數字。

### 4. 失敗處理：warn + 空值，不丟例外

- **Decision**: 在 `upload()` 末段以 `try/except Exception` 包住 QR 產生流程；
  失敗時呼叫 `warnings.warn(...)` 並讓 `qrcode_png=b""`、`qrcode_base64=""`，
  仍正常回傳 `IbonUploadResult`。
- **Why**: pincode 本身（從 ibon 取得）才是 caller 真正在意的東西。為了讓
  `qrcode` 套件的環境問題（極端情境）不要讓整個上傳作廢，採取「最佳努力」策略。
- **Alternative**: 直接丟 `IbonRequestError` — 但這違反語意（不是 ibon 錯誤）；
  另設新例外 `IbonQRCodeError` — 增加複雜度，但 caller 幾乎不會分別處理。
  維持 warn + 空值。

### 5. CLI `--qr-out` 行為

- **Decision**: 加回 `--qr-out PATH` 旗標。給定時把 `qrcode_png` 寫到該路徑；
  未給時不寫檔。文字模式輸出多一行 `QR PNG: <path>`（僅當 `--qr-out` 給定時）；
  JSON 模式無論有無 `--qr-out`，都輸出 `qrcode_base64`，並在有 `--qr-out` 時
  附上 `qrcode_path`。
- **Why**: 文字模式 stdout 印 base64 對人類無意義。`--qr-out` 是常見需求（直接
  獲得可用的 PNG），保留入口。

### 6. `IbonUploadResult` 為 frozen dataclass — 欄位增加是否破壞？

- **Decision**: 新增欄位不視為 BREAKING（位置型構造少有人用；`from_pincode_response`
  classmethod 內部一併產出，呼叫端通常用屬性存取）。`raw` 欄位保留不變。
- **Why**: 套件還在 0.x；增量演進。如果有 caller 用 positional args 構造
  `IbonUploadResult`，本變更會打到他們，但這種用法極為罕見且 frozen dataclass
  幾乎都用 keyword。

## Risks / Trade-offs

- **[Pillow 相依會讓 wheel 變大]** → Pillow 已是事實標準的圖片處理庫；多數 Python
  環境本來就有；接受。
- **[`qrcode` 套件未來改 API]** → 包在 `_render_qrcode_png` helper 內，未來換掉
  套件只動一處。
- **[極大 base64 字串塞進 JSON 結果]** → QR Code PNG 約 1–3 KB，base64 後 ≤4 KB；
  對 HTTP API 與 CLI JSON 輸出皆可接受。
- **[QR Code 失敗 warn 不夠醒目]** → `warnings.warn` 預設會印到 stderr；如果
  caller 隱藏 warning 才會錯過，但他們本來就有義務處理 warning 過濾。
- **[相依名稱 `qrcode[pil]` 與另一同名套件混淆]** → 在 `pyproject.toml` 標明
  `qrcode[pil]>=7,<9` 並於 README 說明來源，降低混淆。
