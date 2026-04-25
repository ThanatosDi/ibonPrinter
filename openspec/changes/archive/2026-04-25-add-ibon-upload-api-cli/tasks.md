## 1. 專案骨架與測試環境

### 1.1 🔴 紅燈 - 撰寫骨架驗證測試
- [x] 1.1.1 在 `tests/test_packaging.py` 撰寫 `test_can_import_ibon_printer_package`：`import ibon_printer` 可成功
- [x] 1.1.2 撰寫 `test_console_scripts_registered`：解析 `pyproject.toml` 並斷言 `ibon-printer` 與 `ibon-printer-api` 皆列於 `project.scripts`
- [x] 1.1.3 執行 `pytest tests/test_packaging.py`，確認全部失敗

### 1.2 🟢 綠燈 - 建立套件骨架
- [x] 1.2.1 建立 `ibon_printer/` 並新增空的 `__init__.py`、`client.py`、`errors.py`、`cli.py`、`api.py`
- [x] 1.2.2 撰寫 `pyproject.toml`（PEP 621），含 `project.scripts = { ibon-printer = "ibon_printer.cli:main", ibon-printer-api = "ibon_printer.api:run" }`
- [x] 1.2.3 更新 `requirements.txt` 新增 `fastapi`、`uvicorn[standard]`、`python-multipart`；保留 `requests`
- [x] 1.2.4 建立 `tests/__init__.py` 與 `tests/conftest.py`（共用 fixture：假 `requests.Session`、樣本檔路徑）
- [x] 1.2.5 執行 `pytest tests/test_packaging.py`，確認全部通過

### 1.3 🔵 重構 - 整理套件骨架
- [x] 1.3.1 於 `ibon_printer/__init__.py` 明確 re-export 公開 API（`IbonClient`、`IbonUploadResult`、錯誤類別）
- [x] 1.3.2 為每個模組加上一行模組 docstring（檔案用途）
- [x] 1.3.3 重新執行測試，確認仍然通過

## 2. 錯誤類別（errors 模組）

### 2.1 🔴 紅燈 - 撰寫 errors 測試
- [x] 2.1.1 在 `tests/test_errors.py` 撰寫 `test_validation_error_is_exception`：`IbonValidationError` 繼承自 `Exception`
- [x] 2.1.2 撰寫 `test_request_error_carries_fields`：`IbonRequestError("msg", status_code=502, result_code="99")` 可由屬性讀回
- [x] 2.1.3 撰寫 `test_request_error_str_includes_message`：`str(err)` 含原始訊息
- [x] 2.1.4 執行 `pytest tests/test_errors.py`，確認全部失敗

### 2.2 🟢 綠燈 - 實作 errors 模組
- [x] 2.2.1 於 `ibon_printer/errors.py` 實作 `IbonValidationError(Exception)`
- [x] 2.2.2 實作 `IbonRequestError(Exception)`，`__init__(self, message, *, status_code=None, result_code=None)` 儲存三個屬性
- [x] 2.2.3 執行 `pytest tests/test_errors.py`，確認全部通過

### 2.3 🔵 重構 - 優化 errors 模組
- [x] 2.3.1 為兩個例外類別加上類別 docstring，說明何時被丟出
- [x] 2.3.2 將共用 base class（若有）抽出或刻意保留獨立，並在 docstring 解釋
- [x] 2.3.3 重新執行測試，確認仍然通過

## 3. 核心 client - 檔案驗證

### 3.1 🔴 紅燈 - 撰寫驗證測試
- [x] 3.1.1 在 `tests/test_client_validation.py` 撰寫 `test_missing_file_raises`：不存在路徑 → `IbonValidationError`，訊息含 "File not found"
- [x] 3.1.2 撰寫 `test_unsupported_extension_raises`：副檔名 `.heic` → `IbonValidationError`，訊息列出合法副檔名
- [x] 3.1.3 撰寫 `test_oversize_file_raises`：透過 monkeypatch `os.path.getsize` 回傳 `11 * 1024 * 1024` → `IbonValidationError`，訊息含 "10 MB"
- [x] 3.1.4 撰寫 `test_valid_file_passes`：合法 `.pdf` 且大小正常 → 不丟例外
- [x] 3.1.5 執行 `pytest tests/test_client_validation.py`，確認全部失敗

### 3.2 🟢 綠燈 - 實作檔案驗證
- [x] 3.2.1 於 `ibon_printer/client.py` 定義模組常數 `ALLOWED_EXTENSIONS = {"doc","docx","ppt","pptx","xls","xlsx","txt","ini","pdf","jpg","gif","bmp"}`
- [x] 3.2.2 定義 `MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024`
- [x] 3.2.3 實作 `IbonClient._validate(path)`：依序檢查存在、副檔名、大小，並丟出對應 `IbonValidationError`
- [x] 3.2.4 執行 `pytest tests/test_client_validation.py`，確認全部通過

### 3.3 🔵 重構 - 優化驗證邏輯
- [x] 3.3.1 將錯誤訊息抽成 `ibon_printer/client.py` 內的常數或函式，避免字串散落
- [x] 3.3.2 若 `_validate` 過長，拆成 `_check_exists` / `_check_extension` / `_check_size`
- [x] 3.3.3 重新執行測試，確認仍然通過

## 4. 核心 client - 三階段 HTTP 流程

### 4.1 🔴 紅燈 - 撰寫 HTTP 流程測試
- [x] 4.1.1 在 `tests/test_client_http.py` 撰寫 `test_fetch_hash_success`：mock session 回傳 `{"Hash": "abc", "ResultCode": "00"}` → `_fetch_hash()` 回傳 `"abc"` 且 POST 至 `.../FileUpload`
- [x] 4.1.2 撰寫 `test_fetch_hash_failure`：`{"ResultCode": "99", "Message": "oops"}` → `IbonRequestError(message="oops", result_code="99")`
- [x] 4.1.3 撰寫 `test_upload_file_sends_multipart`：mock session 捕捉呼叫並斷言含 `files=` 且 form 含 `hash`、`fileName`
- [x] 4.1.4 撰寫 `test_upload_file_failure`：`ResultCode != "00"` → `IbonRequestError`
- [x] 4.1.5 撰寫 `test_request_pincode_returns_raw_dict`：mock session 回傳完整 pincode 字典 → `_request_pincode()` 直接回傳該字典
- [x] 4.1.6 撰寫 `test_request_pincode_failure`：非零 ResultCode → `IbonRequestError`
- [x] 4.1.7 撰寫 `test_default_session_has_chrome_ua`：預設建構的 client 之 `session.headers["User-Agent"]` 含 `"Chrome"`
- [x] 4.1.8 撰寫 `test_injected_session_is_reused`：傳入自製 session，三個步驟皆使用它
- [x] 4.1.9 執行 `pytest tests/test_client_http.py`，確認全部失敗

### 4.2 🟢 綠燈 - 實作 HTTP 流程
- [x] 4.2.1 實作 `IbonClient.__init__(self, session=None, timeout=10)`，未傳入 session 時建立預設含 Chrome UA 的 `requests.Session`
- [x] 4.2.2 實作 `_fetch_hash()`：POST JSON `{"hash": ""}` 至 `https://printadmin.ibon.com.tw/IbonUpload/IbonUpload/FileUpload`，檢查 ResultCode，回傳 `Hash`
- [x] 4.2.3 實作 `_upload_file(path, hash)`：以 multipart 上傳至 `.../LocalFileUpload`，form 欄位 `hash`、`fileName`
- [x] 4.2.4 實作 `_request_pincode(hash, user, email)`：form-encoded POST 至 `.../IbonFileUpload`，回傳 JSON dict
- [x] 4.2.5 為每個步驟加上錯誤檢查：任何 `ResultCode != "00"` 皆丟 `IbonRequestError`
- [x] 4.2.6 執行 `pytest tests/test_client_http.py`，確認全部通過

### 4.3 🔵 重構 - 優化 HTTP 流程
- [x] 4.3.1 抽出共用 `_post(endpoint, **kwargs) -> dict`，統一處理 timeout、逾時錯誤、JSON 解析、ResultCode 檢查
- [x] 4.3.2 將三個 endpoint URL 集中為模組常數（例：`ENDPOINT_HASH`、`ENDPOINT_UPLOAD`、`ENDPOINT_PINCODE`）
- [x] 4.3.3 重新執行 `pytest tests/test_client_http.py`，確認仍然通過

## 5. 核心 client - `upload()` 編排與結果解析

### 5.1 🔴 紅燈 - 撰寫編排與結果解析測試
- [x] 5.1.1 在 `tests/test_client_upload.py` 撰寫 `test_upload_end_to_end_happy_path`：mock 依序回傳 hash → upload ok → pincode 字典，`upload()` 回傳 `IbonUploadResult` 並含正確 `pincode`、`deadline`、`file_date`、`qrcode_png`（bytes）、`raw`（dict）
- [x] 5.1.2 撰寫 `test_result_decodes_base64_png`：`qrcode_png` 為 base64 解碼後的原始 bytes，且以 PNG 魔術字開頭（`b"\x89PNG"`）
- [x] 5.1.3 撰寫 `test_result_dates_are_taipei_tz`：`deadline.tzinfo` 與 `file_date.tzinfo` 皆為 `ZoneInfo("Asia/Taipei")`
- [x] 5.1.4 撰寫 `test_upload_aborts_on_hash_failure`：第一步失敗時不呼叫第二、第三步
- [x] 5.1.5 撰寫 `test_upload_aborts_on_upload_failure`：第二步失敗時不呼叫第三步
- [x] 5.1.6 撰寫 `test_upload_forwards_user_email`：傳入 `user="陳大寶"`、`email="a@b.com"` 時第三步 payload 含該欄位
- [x] 5.1.7 執行 `pytest tests/test_client_upload.py`，確認全部失敗

### 5.2 🟢 綠燈 - 實作 upload 編排
- [x] 5.2.1 定義 `@dataclass(frozen=True) IbonUploadResult`，欄位 `pincode: str`、`deadline: datetime`、`qrcode_png: bytes`、`file_date: datetime`、`raw: dict`
- [x] 5.2.2 實作 `IbonClient.upload(self, path, user=" ", email=" ") -> IbonUploadResult`：依序呼叫 `_validate` → `_fetch_hash` → `_upload_file` → `_request_pincode`
- [x] 5.2.3 在 `upload()` 內將 pincode 字典解析為 `IbonUploadResult`：base64 解碼 `FileQrcode`，以 `datetime.strptime(..., "%Y/%m/%d %H:%M:%S")` + `ZoneInfo("Asia/Taipei")` 解析日期
- [x] 5.2.4 執行 `pytest tests/test_client_upload.py`，確認全部通過

### 5.3 🔵 重構 - 優化 upload 程式碼
- [x] 5.3.1 將 pincode 字典 → `IbonUploadResult` 轉換抽成 `IbonUploadResult.from_raw(dict)` 類別方法
- [x] 5.3.2 移除 `upload()` 內任何重複的錯誤處理或字串組合
- [x] 5.3.3 重新執行全部 client 測試，確認仍然通過

## 6. CLI（`ibon_printer/cli.py`）

### 6.1 🔴 紅燈 - 撰寫 CLI 測試
- [x] 6.1.1 在 `tests/test_cli.py` 建立 fixture：以 monkeypatch 將 `ibon_printer.cli.IbonClient` 換成回傳預設 `IbonUploadResult` 的 fake
- [x] 6.1.2 撰寫 `test_cli_happy_path_text_output`：`main(["file.pdf"])` 退出碼 0，stdout 含 `Pincode`、`DeadLine`、`FileDate`、QR 路徑
- [x] 6.1.3 撰寫 `test_cli_forwards_name_email`：`main(["file.pdf", "--name", "陳大寶", "--email", "a@b.com"])` 時 fake client 收到對應參數
- [x] 6.1.4 撰寫 `test_cli_default_qr_path`：未提供 `--qr-out` → PNG 寫入 `<file>.qr.png`
- [x] 6.1.5 撰寫 `test_cli_custom_qr_path`：`--qr-out /tmp/code.png` → PNG 寫入該路徑
- [x] 6.1.6 撰寫 `test_cli_json_mode`：`--json` 時 stdout 僅為一行 JSON，含 `pincode`、`deadline`、`file_date`、`qrcode_path` 四個鍵
- [x] 6.1.7 撰寫 `test_cli_validation_error_exit_2`：fake client 丟 `IbonValidationError` → 退出碼 2，錯誤寫 stderr
- [x] 6.1.8 撰寫 `test_cli_request_error_exit_1`：fake client 丟 `IbonRequestError` → 退出碼 1
- [x] 6.1.9 執行 `pytest tests/test_cli.py`，確認全部失敗

### 6.2 🟢 綠燈 - 實作 CLI
- [x] 6.2.1 在 `ibon_printer/cli.py` 建立 `argparse` parser：positional `file`；選項 `--name`、`--email`、`--qr-out`、`--json`、`--debug`
- [x] 6.2.2 實作 `main(argv=None)`：建立 `IbonClient`、呼叫 `upload()`、將 `qrcode_png` 寫入目的路徑
- [x] 6.2.3 文字模式印出四欄資訊；`--json` 模式改印單行 JSON（使用 `json.dumps`，ISO8601 日期）
- [x] 6.2.4 實作例外對應：`IbonValidationError` → stderr + `return 2`；`IbonRequestError` → stderr + `return 1`；其他例外 → `return 1`（`--debug` 時保留 traceback）
- [x] 6.2.5 確保 `if __name__ == "__main__": sys.exit(main())`
- [x] 6.2.6 執行 `pytest tests/test_cli.py`，確認全部通過

### 6.3 🔵 重構 - 優化 CLI
- [x] 6.3.1 將「文字輸出格式化」與「JSON 輸出格式化」拆成獨立函式 `_format_text(result, qr_path)` / `_format_json(result, qr_path)`
- [x] 6.3.2 將例外對應整理成單一 `_handle_error(exc, debug)` 函式
- [x] 6.3.3 重新執行 `pytest tests/test_cli.py`，確認仍然通過

## 7. HTTP API（`ibon_printer/api.py`）

### 7.1 🔴 紅燈 - 撰寫 API 測試
- [x] 7.1.1 在 `tests/test_api.py` 建立 FastAPI `TestClient` fixture，並 monkeypatch `ibon_printer.api.IbonClient` 為可控 fake
- [x] 7.1.2 撰寫 `test_upload_success_returns_expected_schema`：`POST /upload` 帶 multipart `file` → 200，JSON 含 `pincode`、`deadline`、`file_date`、`qrcode_base64`
- [x] 7.1.3 撰寫 `test_upload_forwards_name_email_form_fields`：form 欄位 `name`、`email` 傳遞至 fake client
- [x] 7.1.4 撰寫 `test_upload_missing_file_returns_422`：不附 file → 422
- [x] 7.1.5 撰寫 `test_upload_validation_error_returns_400`：fake client 丟 `IbonValidationError("too big")` → 400，body `{"detail": "too big"}`
- [x] 7.1.6 撰寫 `test_upload_request_error_returns_502`：fake client 丟 `IbonRequestError` → 502
- [x] 7.1.7 撰寫 `test_healthz_returns_ok_without_calling_ibon`：`GET /healthz` → 200 `{"status":"ok"}`，且 fake client 未被建立
- [x] 7.1.8 撰寫 `test_temp_file_removed_after_upload`：監視臨時目錄，請求結束後無殘留檔
- [x] 7.1.9 執行 `pytest tests/test_api.py`，確認全部失敗

### 7.2 🟢 綠燈 - 實作 API
- [x] 7.2.1 在 `ibon_printer/api.py` 建立 FastAPI `app`
- [x] 7.2.2 定義 `UploadResponse` pydantic 模型（`pincode: str`、`deadline: str`、`file_date: str`、`qrcode_base64: str`）
- [x] 7.2.3 實作 `POST /upload` handler：接 `UploadFile` + optional form `name`/`email`；寫入 `tempfile.NamedTemporaryFile(suffix=<原副檔名>, delete=False)`；呼叫 `IbonClient.upload()`；`finally` 刪除臨時檔
- [x] 7.2.4 回傳時將 `IbonUploadResult` 轉為 `UploadResponse`，`qrcode_base64` 取自 `result.raw["FileQrcode"]`
- [x] 7.2.5 註冊例外處理器：`IbonValidationError` → 400；`IbonRequestError` → 502；`requests.RequestException` → 502
- [x] 7.2.6 實作 `GET /healthz` 回傳 `{"status": "ok"}`
- [x] 7.2.7 實作 `run(argv=None)`：`argparse` 處理 `--host`/`--port`，呼叫 `uvicorn.run("ibon_printer.api:app", ...)`
- [x] 7.2.8 執行 `pytest tests/test_api.py`，確認全部通過

### 7.3 🔵 重構 - 優化 API
- [x] 7.3.1 將 `IbonUploadResult` → `UploadResponse` 轉換抽成 `_to_response(result)` 函式
- [x] 7.3.2 將三個例外處理器整合為單一設定函式 `_register_error_handlers(app)`
- [x] 7.3.3 將 tempfile 寫入/刪除封裝成 context manager `_spool_upload(file)`
- [x] 7.3.4 重新執行 `pytest tests/test_api.py`，確認仍然通過

## 8. 向下相容 shim

### 8.1 🔴 紅燈 - 撰寫相容性測試
- [x] 8.1.1 在 `tests/test_legacy_shim.py` 撰寫 `test_legacy_import_path_still_works`：`from ibonPrinter import IBON; IBON()` 不拋例外
- [x] 8.1.2 撰寫 `test_legacy_instance_is_ibon_client`：上述 `IBON()` 為 `IbonClient` 實例
- [x] 8.1.3 撰寫 `test_legacy_import_emits_deprecation_warning`：使用 `pytest.warns(DeprecationWarning)` 驗證 import 時發警告
- [x] 8.1.4 撰寫 `test_legacy_root_cli_removed`：斷言 `ibonPrinter/cli.py` 已被移除（`os.path.exists` 為 False）
- [x] 8.1.5 執行 `pytest tests/test_legacy_shim.py`，確認全部失敗

### 8.2 🟢 綠燈 - 建立相容 shim
- [x] 8.2.1 以 `ibon_printer/client.py` 匯出的 `IbonClient` 取代 `ibonPrinter.py` 內容：`from ibon_printer.client import IbonClient as IBON`
- [x] 8.2.2 在該檔頂端加 `warnings.warn("ibonPrinter is deprecated; use ibon_printer", DeprecationWarning, stacklevel=2)`
- [x] 8.2.3 刪除根目錄的 `cli.py`（由 `ibon-printer` console script 取代）
- [x] 8.2.4 執行 `pytest tests/test_legacy_shim.py`，確認全部通過

### 8.3 🔵 重構 - 整理 shim
- [x] 8.3.1 在 `ibonPrinter.py` 加上簡短 module docstring 指向新 import 路徑與移除時程
- [x] 8.3.2 確認 `ibonPrinter.py` 內容僅剩 import、警告、`__all__`，沒有其他邏輯
- [x] 8.3.3 重新執行全測試套件，確認仍然通過

## 9. 文件與最終驗證

### 9.1 🔴 紅燈 - 撰寫文件與安裝驗證測試
- [x] 9.1.1 在 `tests/test_readme.py` 撰寫 `test_readme_mentions_pip_install`：`README.md` 含 `pip install .`
- [x] 9.1.2 撰寫 `test_readme_mentions_both_console_scripts`：`README.md` 同時提到 `ibon-printer` 與 `ibon-printer-api`
- [x] 9.1.3 撰寫 `test_readme_documents_limits`：`README.md` 內容含 "10 MB" 與副檔名列表
- [x] 9.1.4 撰寫 `test_readme_deprecation_notice`：`README.md` 含 `ibonPrinter` 將停用的說明
- [x] 9.1.5 執行 `pytest tests/test_readme.py`，確認全部失敗

### 9.2 🟢 綠燈 - 更新文件
- [x] 9.2.1 重寫 `README.md` 安裝章節：`pip install .`、依賴清單
- [x] 9.2.2 新增 CLI 使用範例：positional file、全部旗標、輸出樣本、退出碼表格
- [x] 9.2.3 新增 API 使用範例：`ibon-printer-api --host 0.0.0.0 --port 9000`、`curl -F file=@x.pdf` 範例、回應 schema、錯誤碼對照
- [x] 9.2.4 新增 10 MB / 副檔名限制說明，並強調 API 不在伺服器端保存檔案
- [x] 9.2.5 加上 `ibonPrinter` 停用通告
- [x] 9.2.6 執行 `pytest tests/test_readme.py`，確認全部通過

### 9.3 🔵 重構與最終驗證
- [x] 9.3.1 在全新的 venv 執行 `pip install .`，確認 `ibon-printer`、`ibon-printer-api` 皆可從 PATH 呼叫
- [x] 9.3.2 冒煙測試：`ibon-printer ./small.pdf --name test --email test@example.com` 實打 ibon，確認產出 pincode 與 QR PNG
- [x] 9.3.3 冒煙測試：啟動 `ibon-printer-api` 後 `curl -F file=@small.pdf -F name=test -F email=test@example.com http://127.0.0.1:8000/upload`，回應符合 `UploadResponse`
- [x] 9.3.4 執行完整測試套件 `pytest`，確認全部通過
- [x] 9.3.5 於 `README.md` 或 `CHANGELOG` 記錄冒煙測試結果（日期、ibon 回傳樣本雜湊）
