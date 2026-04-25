# ibon-printer

![Python](https://img.shields.io/static/v1?label=Python&message=3.11%2B&style=flat-square&color=success&logo=python&logoColor=64BAFF)

提供 CLI 與 HTTP API，可將單一檔案上傳至 7-11 ibon 雲端列印。將舊版 `ibonPrinter.IBON` 流程重構為可安裝的套件，並提供兩個 console scripts。

## 安裝

```bash
pip install .
```

執行期相依：`requests`、`fastapi`、`uvicorn[standard]`、`python-multipart`、`qrcode[pil]`（用於本機產生取件 QR Code，含 Pillow）；Windows 另需 `tzdata` 才能解析 `Asia/Taipei` 時區。

安裝後會註冊兩個 console scripts：

- `ibon-printer` — 從命令列上傳
- `ibon-printer-api` — 啟動 HTTP 服務

## 限制（依 ibon 雲端列印網實測）

- **單檔總大小：** 15 MB。
- **允許副檔名：** Microsoft Office 系列 (`doc`、`docx`、`xls`、`xlsx`、`ppt`、`pptx`)，以及 `txt`、`ini`、`pdf`、`jpg`、`jpeg`、`bmp`、`gif`、`png`。

兩項限制都會在發出任何網路請求前於本機檢查，不合法時直接快速失敗。

## 上傳流程（新版）

從 2025 年起，ibon 將舊的 `printadmin.ibon.com.tw/IbonUpload/...` 三步流程改為四個 endpoint：

1. `POST https://print-api.ibon.com.tw/api/BaseEntry/GetEntry` — 取得 JWT token。
2. `POST https://print-api.ibon.com.tw/api/IbonUpload/GetPincode` — 取得取件編號與列印期限。
3. `GET  https://www.ibon.com.tw/qwsapi2/api/GetChunksize` — 取得分塊大小（預設 2 MiB）。
4. `POST https://www.ibon.com.tw/qwsapi2/api/Upload` — 以 base64 上傳檔案內容；大檔會分塊送多次。

新版回應**不再附帶取件 QR Code 圖片**，僅回傳取件編號與期限。

## CLI 使用方式

```bash
# 最簡用法 — 寄件人欄位留空、不預選規格
ibon-printer ./document.pdf

# 帶寄件人資訊
ibon-printer ./document.pdf --name "陳大寶" --email a@b.com

# 預選列印規格（A3 彩色雙面一般紙）
ibon-printer ./document.pdf --spec a3-color-duplex

# 把取件 QR Code 寫成 PNG
ibon-printer ./document.pdf --qr-out ./qrcode.png

# 機器可讀格式輸出
ibon-printer ./document.pdf --json
```

`--json` 會輸出單行 JSON，包含 `pincode`、`deadline`、`select_type`、`qrcode_base64`；
若同時帶 `--qr-out` 還會多一個 `qrcode_path`。

`--qr-out PATH` 讓 CLI 把 client 端產生的取件 QR Code（PNG）寫到指定路徑。
不帶這個旗標時，CLI 不會寫入任何檔案。

### 預選列印規格 (`--spec`)

未指定 `--spec` 時會送 `FNOMAL`（不預選規格，至 ibon 機台再選），這也是 ibon 網站的預設。
若想直接帶規格上傳，可使用 alias 或直接傳 ibon 的 `SelectType` 字串：

| Alias                           | SelectType | 對應規格                          |
|---------------------------------|------------|-----------------------------------|
| `default`                       | `FNOMAL`   | 不預選                            |
| `a4`                            | `FA4BN1`   | A4 黑白 一般 單面                 |
| `a4-color`                      | `FA4CN1`   | A4 彩色 一般 單面                 |
| `a4-duplex`                     | `FA4BN2`   | A4 黑白 一般 雙面                 |
| `a4-color-duplex`               | `FA4CN2`   | A4 彩色 一般 雙面                 |
| `a4-special`                    | `FA4BS1`   | A4 黑白 特殊 單面                 |
| `a4-color-special`              | `FA4CS1`   | A4 彩色 特殊 單面                 |
| `a4-color-duplex-special`       | `FA4CS2`   | A4 彩色 特殊 雙面                 |
| `a3`                            | `FA3BN1`   | A3 黑白 一般 單面                 |
| `a3-color`                      | `FA3CN1`   | A3 彩色 一般 單面                 |
| `a3-duplex`                     | `FA3BN2`   | A3 黑白 一般 雙面                 |
| `a3-color-duplex`               | `FA3CN2`   | A3 彩色 一般 雙面                 |
| `photo-4x6`                     | `F4X6N1`   | 4X6 PO 相片紙、彩色、單面         |
| `sticker-4x6`                   | `F4X6S1`   | 4X6 貼紙、彩色、單面              |

未列入 alias 的字串會視為 raw `SelectType` 直接轉送（例如 `--spec FA3CN2`）。

### 退出碼

| 退出碼 | 意義                                              |
|--------|---------------------------------------------------|
| 0      | 成功                                              |
| 1      | 上游 / 請求錯誤（或其他未預期錯誤）               |
| 2      | 本機驗證錯誤（檔案不存在、超過大小限制等）        |

## HTTP API 使用方式

```bash
ibon-printer-api --host 0.0.0.0 --port 9000
```

可用端點：

- `POST /upload` — multipart；form 欄位 `file`（必填）、`name`、`email`、`select_type`（預設 `FNOMAL`）。
- `GET /healthz` — 存活檢查。

```bash
# 不預選規格
curl -F file=@small.pdf -F name=test -F email=test@example.com \
     http://127.0.0.1:9000/upload

# 預選 A3 彩色雙面
curl -F file=@small.pdf -F select_type=FA3CN2 \
     http://127.0.0.1:9000/upload
```

回應 (`UploadResponse`)：

```json
{
  "pincode": "12345678",
  "deadline": "2026-05-01T12:00:00+08:00",
  "select_type": "FA3CN2",
  "spec_description": "FA3CN2",
  "qrcode_base64": "iVBORw0KGgoAAAA..."
}
```

`qrcode_base64` 為 server 端用 `qrcode[pil]` 對取件編號產生的 PNG 之 base64 字串
（不含 `data:image/png;base64,` 前綴）；前端可直接用
`<img src="data:image/png;base64,${qrcode_base64}">` 嵌入。
產生失敗時回傳空字串 `""`，但 `pincode` 仍有效。

### HTTP 狀態碼對應

| 狀態碼 | 何時回傳                                                |
|--------|---------------------------------------------------------|
| 200    | 成功                                                    |
| 400    | 本機驗證錯誤（檔案大小／副檔名／不存在）                |
| 422    | FastAPI 請求 schema 驗證失敗（例：缺少 `file`）         |
| 502    | ibon 上游回傳失敗 code 或傳輸層失敗                     |

API 為**無狀態**設計 — 上傳的檔案會 stream 至短期暫存檔，請求結束後立即刪除，伺服器端不會保留任何檔案。

## Python API 範例

```python
from ibon_printer import IbonClient, PrintSpec

client = IbonClient()

# 不預選規格
result = client.upload("./document.pdf")
print(result.pincode, result.deadline)

# 取件 QR Code（client 端用 qrcode 套件以 pincode 產生，純記憶體）
print(result.qrcode_base64)              # base64 字串，可直接 embed
# 若需要原始 PNG bytes，由呼叫端自行解碼：
# import base64
# png_bytes = base64.b64decode(result.qrcode_base64)

# 預選 A3 彩色雙面
result = client.upload(
    "./document.pdf",
    user="陳大寶",
    email="a@b.com",
    spec=PrintSpec.a3(color=True, duplex=True),
)
```

`PrintSpec` 提供的便利建構式：

- `PrintSpec.default()` — `FNOMAL`，不預選
- `PrintSpec.a4(color=, duplex=, special_paper=)` — A4 規格組合
- `PrintSpec.a3(color=, duplex=)` — A3 規格組合（A3 僅支援一般紙）
- `PrintSpec.photo_4x6()` — 4X6 相片紙
- `PrintSpec.sticker_4x6()` — 4X6 貼紙

也可直接用 `PrintSpec("FA3CN2")` 傳入原始 SelectType 字串。

## 已棄用：`ibonPrinter`

舊版扁平模組仍可匯入一個版本：

```python
from ibonPrinter import IBON  # 會發出 DeprecationWarning，請改用下方新路徑
```

請改用：

```python
from ibon_printer import IbonClient
```

`ibonPrinter.py` 將於後續版本移除。

## LICENSE

[MIT License](./LICENSE)
