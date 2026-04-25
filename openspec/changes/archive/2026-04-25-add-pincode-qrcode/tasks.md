## 1. 相依與骨架

- [x] 1.1 在 `pyproject.toml` `dependencies` 加入 `qrcode[pil]>=7,<9`
- [x] 1.2 在 `pyproject.toml` `dependency-groups.dev` 加入 `pyzbar>=0.1.9`（測試用 QR 解碼器）
- [x] 1.3 在 `requirements.txt` 加入 `qrcode[pil]>=7,<9`
- [x] 1.4 執行 `uv sync`，確認 `qrcode`、`Pillow`、`pyzbar` 均安裝成功
- [x] 1.5 撰寫 `tests/conftest.py` fixture `qrcode_example_path`：回傳 `Path("tests/qrcode_example.png")`
- [x] 1.6 撰寫 `tests/conftest.py` helper `decode_qrcode(png_bytes_or_path) -> str`：使用 `pyzbar.decode` 把 PNG bytes 或檔案路徑解出文字內容（多筆時取第一筆）
- [x] 1.7 跑 `uv run pytest -q`，確認既有 73 項測試仍綠（baseline）

## 2. 驗證 fixture 本身（紅燈→綠燈）

- [x] 2.1 在 `tests/test_qrcode_fixture.py` 撰寫 `test_example_image_decodes_to_known_pincode`：`decode_qrcode(qrcode_example_path) == "3524627893"`
- [x] 2.2 執行 `uv run pytest tests/test_qrcode_fixture.py`，確認通過（fixture 與 decoder 工作正確）

## 3. QR Code 產生 helper（紅燈）

- [x] 3.1 在 `tests/test_qrcode.py` 撰寫 `test_render_qrcode_returns_png_bytes`：呼叫 `_render_qrcode_png("1234567890")` → 回傳 `bytes` 且開頭為 `b"\x89PNG\r\n\x1a\n"`
- [x] 3.2 撰寫 `test_render_qrcode_round_trips_via_decoder`：以 fixture 的 pincode `"3524627893"` 呼叫 `_render_qrcode_png(...)`，再用 `decode_qrcode(...)` 解碼 → 應為 `"3524627893"`（與 ibon 範例同 payload，獨立驗證）
- [x] 3.3 撰寫 `test_render_qrcode_round_trips_arbitrary_pincode`：`decode_qrcode(_render_qrcode_png(p)) == p` 對 `p in ("0000000000", "1234567890", "9876543210")`
- [x] 3.4 撰寫 `test_render_qrcode_rejects_empty_input`：`_render_qrcode_png("")` → `ValueError`
- [x] 3.5 執行 `uv run pytest tests/test_qrcode.py`，確認全部失敗

## 4. QR Code 產生 helper（綠燈）

- [x] 4.1 於 `ibon_printer/client.py` 實作 `_render_qrcode_png(text: str) -> bytes`：使用 `qrcode.make(text)` 取得 PIL `Image`，再 `image.save(BytesIO, "PNG")` 拉出 bytes
- [x] 4.2 在 helper 內前置檢查空字串 → 丟 `ValueError("text must be non-empty")`
- [x] 4.3 執行 `uv run pytest tests/test_qrcode.py tests/test_qrcode_fixture.py`，確認全部通過

## 5. `IbonUploadResult` 欄位擴充（紅燈）

- [x] 5.1 在 `tests/test_client_upload.py` 撰寫 `test_result_has_qrcode_png_bytes`：upload 成功時 `result.qrcode_png` 開頭為 `b"\x89PNG\r\n\x1a\n"`
- [x] 5.2 撰寫 `test_result_qrcode_base64_round_trips`：`base64.b64decode(result.qrcode_base64) == result.qrcode_png`
- [x] 5.3 撰寫 `test_result_qrcode_encodes_pincode`：在 mock 流程把 pincode 設為 `"5678901234"` 時，產生的 PNG bytes 與 `_render_qrcode_png("5678901234")` 相同
- [x] 5.4 執行 `uv run pytest tests/test_client_upload.py`，確認新測試失敗

## 6. `IbonUploadResult` 欄位擴充（綠燈）

- [x] 6.1 在 `IbonUploadResult` dataclass 新增 `qrcode_png: bytes = b""` 與 `qrcode_base64: str = ""` 兩個欄位
- [x] 6.2 修改 `IbonClient.upload()`：成功取得 `IbonUploadResult` 之後，呼叫 `_render_qrcode_png(result.pincode)`，把回傳 bytes 與 `base64.b64encode(...).decode("ascii")` 寫進 `qrcode_png`、`qrcode_base64`，再回傳新 result（用 `dataclasses.replace`）
- [x] 6.3 執行 `uv run pytest tests/test_client_upload.py`，確認通過

## 7. 失敗處理（紅燈→綠燈）

- [x] 7.1 撰寫 `test_upload_warns_when_qrcode_generation_fails`：用 `monkeypatch.setattr` 把 `_render_qrcode_png` 改成丟 `RuntimeError`；upload 仍回傳 `IbonUploadResult`，但 `qrcode_png == b""` 且 `qrcode_base64 == ""`
- [x] 7.2 撰寫 `test_upload_emits_warnings_warn_on_failure`：使用 `pytest.warns(UserWarning)` 驗證
- [x] 7.3 在 `IbonClient.upload()` QR 產生段加 `try/except Exception` 包住，except 區塊呼叫 `warnings.warn(f"QR Code generation failed: {exc}", stacklevel=2)`，並把欄位設為空值
- [x] 7.4 執行 `uv run pytest tests/test_client_upload.py`，確認全部通過

## 8. HTTP API 整合（紅燈）

- [x] 8.1 在 `tests/test_api.py` 撰寫 `test_upload_response_includes_qrcode_base64`：`/upload` 200 response 含 `qrcode_base64` 欄位，且 `base64.b64decode(...)` 開頭為 `b"\x89PNG"`
- [x] 8.2 撰寫 `test_upload_response_qrcode_empty_on_generation_failure`：fake client 回傳 `qrcode_png=b""`、`qrcode_base64=""` 時，response 中 `qrcode_base64 == ""`
- [x] 8.3 修改既有 `test_upload_success_returns_expected_schema` 與 fake `_make_result()`，補上 `qrcode_png`、`qrcode_base64`
- [x] 8.4 執行 `uv run pytest tests/test_api.py`，確認新測試失敗

## 9. HTTP API 整合（綠燈）

- [x] 9.1 在 `ibon_printer/api.py` `UploadResponse` 新增 `qrcode_base64: str = ""`
- [x] 9.2 修改 `_to_response(result, spec)`：把 `result.qrcode_base64` 帶入 response
- [x] 9.3 執行 `uv run pytest tests/test_api.py`，確認通過

## 10. CLI `--qr-out` 與 JSON 輸出（紅燈）

- [x] 10.1 在 `tests/test_cli.py` 撰寫 `test_cli_qr_out_writes_png_bytes`：傳 `--qr-out /tmp/x.png` 時檔案被寫入，內容等於 fake result 的 `qrcode_png`
- [x] 10.2 撰寫 `test_cli_no_qr_out_does_not_write_file`：未傳 `--qr-out` 時 stdout 不含 `QR PNG:` 行，且工作目錄無新檔
- [x] 10.3 撰寫 `test_cli_text_output_includes_qr_path_when_qr_out_given`：傳 `--qr-out` 時 stdout 含 `QR PNG: <path>` 行
- [x] 10.4 撰寫 `test_cli_json_includes_qrcode_base64`：`--json` 時輸出 JSON 含 `qrcode_base64` 欄位且為非空字串
- [x] 10.5 撰寫 `test_cli_json_with_qr_out_includes_qrcode_path`：同時帶 `--qr-out` 與 `--json` 時 JSON 多 `qrcode_path`
- [x] 10.6 撰寫 `test_cli_qr_out_failure_writes_zero_byte_and_warns`：fake result `qrcode_png=b""` 時，`--qr-out` 路徑寫出零位元組檔，stderr 含警告
- [x] 10.7 修改既有 fake `_make_result()` 與相關 fixture，補上 `qrcode_png`、`qrcode_base64`
- [x] 10.8 執行 `uv run pytest tests/test_cli.py`，確認新測試失敗

## 11. CLI `--qr-out` 與 JSON 輸出（綠燈）

- [x] 11.1 在 `ibon_printer/cli.py` `_build_parser()` 加回 `--qr-out PATH` 旗標（type=str, default=None）
- [x] 11.2 在 `main()` 內，upload 完成後若 `args.qr_out` 給定：呼叫 `Path(args.qr_out).write_bytes(result.qrcode_png)`；若 `result.qrcode_png == b""` 則 `print("QR Code generation failed; wrote zero-byte file", file=sys.stderr)`
- [x] 11.3 修改 `_format_text(result, spec, qr_path=None)`：若 `qr_path` 給定則多印一行 `QR PNG: <qr_path>`
- [x] 11.4 修改 `_format_json(result, spec, qr_path=None)`：JSON 內必含 `qrcode_base64`；若 `qr_path` 給定，再加 `qrcode_path`
- [x] 11.5 執行 `uv run pytest tests/test_cli.py`，確認通過

## 12. 重構與整合驗證

- [x] 12.1 把 `_render_qrcode_png` 與 `IbonUploadResult` QR 包裝邏輯整理成各自獨立、可單獨呼叫
- [x] 12.2 在 `ibon_printer/__init__.py` 確認 `IbonUploadResult` 仍有正確 re-export（無新類別需匯出）
- [x] 12.3 執行 `uv run pytest -q`，確認**全部**測試通過
- [x] 12.4 對真實 ibon 進行 smoke test：`uv run python test.py`，肉眼確認 `result.qrcode_png[:8] == b"\x89PNG\r\n\x1a\n"`、`result.qrcode_base64` 為非空字串

## 13. 文件更新

- [x] 13.1 更新 `README.md`：在 Python API 範例加上 `result.qrcode_png` / `qrcode_base64` 用法
- [x] 13.2 更新 `README.md`：CLI 段落加入 `--qr-out` 旗標說明與範例
- [x] 13.3 更新 `README.md`：HTTP API response 範例加上 `qrcode_base64` 欄位
- [x] 13.4 更新 `README.md`：在「執行期相依」段落加上 `qrcode[pil]`
- [x] 13.5 在 `tests/test_readme.py` 加 `test_readme_documents_qrcode_field`：README 含 `qrcode_base64` 與 `--qr-out` 字樣
- [x] 13.6 跑完整測試 `uv run pytest -q`，確認 README 測試通過
