"""核心 client：編排 ibon 上傳流程（GetEntry → GetPincode → Upload）。"""
from __future__ import annotations

import base64
import dataclasses
import os
import warnings
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import qrcode
import requests

from .errors import IbonRequestError, IbonValidationError


def _render_qrcode_png(text: str) -> bytes:
    """用 qrcode 套件把純文字產生成 PNG bytes（純記憶體運算）。"""
    if not text:
        raise ValueError("text must be non-empty")
    image = qrcode.make(text)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _attach_qrcode(result: "IbonUploadResult") -> "IbonUploadResult":
    """以 result.pincode 產生 QR Code 並把 base64 字串補上；失敗時 warn + 空字串。"""
    try:
        png = _render_qrcode_png(result.pincode)
        b64 = base64.b64encode(png).decode("ascii")
    except Exception as exc:  # noqa: BLE001 — pincode 仍有效，QR 失敗不該作廢上傳
        warnings.warn(
            f"QR Code generation failed: {exc}", UserWarning, stacklevel=2
        )
        b64 = ""
    return dataclasses.replace(result, qrcode_base64=b64)

_TAIPEI = ZoneInfo("Asia/Taipei")
_DATE_FMT = "%Y/%m/%d %H:%M:%S"

ALLOWED_EXTENSIONS = frozenset(
    {
        "doc",
        "docx",
        "xls",
        "xlsx",
        "ppt",
        "pptx",
        "txt",
        "ini",
        "pdf",
        "jpg",
        "jpeg",
        "bmp",
        "gif",
        "png",
    }
)
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024
MAX_FILE_SIZE_LABEL = "15 MB"
DEFAULT_CHUNK_SIZE = 2 * 1024 * 1024

ENDPOINT_ENTRY = "https://print-api.ibon.com.tw/api/BaseEntry/GetEntry"
ENDPOINT_PINCODE = "https://print-api.ibon.com.tw/api/IbonUpload/GetPincode"
ENDPOINT_CHUNK = "https://www.ibon.com.tw/qwsapi2/api/GetChunksize"
ENDPOINT_UPLOAD = "https://www.ibon.com.tw/qwsapi2/api/Upload"

SUCCESS_CODE = 20000
_FV = "4.2.2"
_DEFAULT_DISPOSABLE_ID = "79627-28172-49319-98742-99804.14"
_DEFAULT_KEY_FIELD = (
    "TnprMk1wamN0TWpneE56SXRORGt6TVRrdE9UZzNOREl0T1RrNE1EUXVNVFF0WjBwQ1ZGbz0="
)
_DEFAULT_T1 = "1-5-p--gJBTZ"
_DEFAULT_GUEST_USER = "guest"
_DEFAULT_GUEST_EMAIL = "guest@qware.com.tw"
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)


def _format_extensions() -> str:
    return ", ".join(sorted(ALLOWED_EXTENSIONS))


def _check_exists(path: str) -> None:
    if not os.path.isfile(path):
        raise IbonValidationError(f"找不到檔案：{path}")


def _check_extension(path: str) -> None:
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise IbonValidationError(
            f"不支援的副檔名 '.{ext}'。可用副檔名：{_format_extensions()}。"
        )


def _check_size(path: str) -> None:
    size = os.path.getsize(path)
    if size > MAX_FILE_SIZE_BYTES:
        raise IbonValidationError(
            f"檔案超過 {MAX_FILE_SIZE_LABEL} 上限（實際 {size} bytes）。"
        )


def _now_taipei() -> datetime:
    return datetime.now(tz=_TAIPEI)


def _format_upload_time(now: datetime) -> str:
    return now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"


@dataclass(frozen=True)
class IbonUploadResult:
    """成功上傳後解析過的結果。"""

    pincode: str
    deadline: datetime
    raw: dict
    qrcode_base64: str = ""

    @classmethod
    def from_pincode_response(cls, payload: dict) -> "IbonUploadResult":
        result = payload.get("result") or {}
        deadline = datetime.strptime(result["deadLine"], _DATE_FMT).replace(tzinfo=_TAIPEI)
        return cls(pincode=result["pincode"], deadline=deadline, raw=payload)


@dataclass(frozen=True)
class PrintSpec:
    """ibon 預選列印規格 — 對應 GetPincode 的 ``SelectType`` 欄位。

    與其手寫 SelectType 字串（如 ``"FA3CN2"``），可使用便利方法：

        spec = PrintSpec.a3(color=True, duplex=True)
        client.upload("file.pdf", spec=spec)
    """

    select_type: str
    description: str = ""

    @classmethod
    def default(cls) -> "PrintSpec":
        """不預選規格（在 ibon 機台再選擇規格）。"""
        return cls("FNOMAL", "不預選規格")

    @classmethod
    def a4(
        cls,
        *,
        color: bool = False,
        duplex: bool = False,
        special_paper: bool = False,
    ) -> "PrintSpec":
        c = "C" if color else "B"
        p = "S" if special_paper else "N"
        s = "2" if duplex else "1"
        desc = (
            "A4、"
            f"{'彩色' if color else '黑白'}、"
            f"{'雙面' if duplex else '單面'}列印、"
            f"{'特殊用紙' if special_paper else '一般用紙'}"
        )
        return cls(f"FA4{c}{p}{s}", desc)

    @classmethod
    def a3(cls, *, color: bool = False, duplex: bool = False) -> "PrintSpec":
        # ibon 端 A3 僅提供一般紙。
        c = "C" if color else "B"
        s = "2" if duplex else "1"
        desc = (
            "A3、"
            f"{'彩色' if color else '黑白'}、"
            f"{'雙面' if duplex else '單面'}列印、一般用紙"
        )
        return cls(f"FA3{c}N{s}", desc)

    @classmethod
    def photo_4x6(cls) -> "PrintSpec":
        """4X6 PO 相片紙、彩色、單面。"""
        return cls("F4X6N1", "4X6、相片紙、彩色、單面")

    @classmethod
    def sticker_4x6(cls) -> "PrintSpec":
        """4X6 貼紙、彩色、單面。"""
        return cls("F4X6S1", "4X6、貼紙、彩色、單面")


class IbonClient:
    """驅動 7-11 ibon 雲端列印上傳流程的 client。"""

    def __init__(
        self,
        session: Any | None = None,
        timeout: float = 30.0,
        disposable_id: str = _DEFAULT_DISPOSABLE_ID,
        key_field: str = _DEFAULT_KEY_FIELD,
        t1: str = _DEFAULT_T1,
    ) -> None:
        if session is None:
            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": _DEFAULT_UA,
                    "Origin": "https://print.ibon.com.tw",
                    "Referer": "https://print.ibon.com.tw/",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                }
            )
        self.session = session
        self.timeout = timeout
        self.disposable_id = disposable_id
        self.key_field = key_field
        self.t1 = t1

    def _validate(self, path: str) -> None:
        _check_exists(path)
        _check_extension(path)
        _check_size(path)

    def _post_json(self, url: str, payload: dict, *, headers: dict | None = None) -> dict:
        try:
            response = self.session.post(
                url, json=payload, headers=headers or {}, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise IbonRequestError(f"請求 {url} 失敗：{exc}") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise IbonRequestError(
                f"{url} 回傳非 JSON 內容：{exc}",
                status_code=getattr(response, "status_code", None),
            ) from exc

    def _check_print_api(self, payload: dict) -> dict:
        if payload.get("code") != SUCCESS_CODE:
            raise IbonRequestError(
                payload.get("msg", "ibon 回傳失敗"),
                result_code=str(payload.get("code")),
            )
        return payload

    def _fetch_entry(self) -> str:
        body = {
            "Data": {
                "t2": "1",
                "fV": _FV,
                "disposableId": self.disposable_id,
                "memberToken": "",
                "key": self.key_field,
                "t1": self.t1,
            }
        }
        payload = self._post_json(ENDPOINT_ENTRY, body)
        self._check_print_api(payload)
        return payload["result"]["token"]

    def _fetch_pincode(
        self, token: str, user: str, email: str, select_type: str
    ) -> dict:
        headers = {
            "Authorization": token,
            "key": self.disposable_id,
            "fv": _FV,
        }
        body = {
            "Data": {
                "User": user.strip() or _DEFAULT_GUEST_USER,
                "Email": email.strip() or _DEFAULT_GUEST_EMAIL,
                "SelectType": select_type,
            }
        }
        payload = self._post_json(ENDPOINT_PINCODE, body, headers=headers)
        return self._check_print_api(payload)

    def _fetch_chunk_size(self) -> int:
        try:
            response = self.session.get(ENDPOINT_CHUNK, timeout=self.timeout)
            return int(response.json().get("ChunkSize", DEFAULT_CHUNK_SIZE))
        except (requests.RequestException, ValueError):
            return DEFAULT_CHUNK_SIZE

    def _upload_chunks(self, pincode: str, path: str, chunk_size: int) -> None:
        file_path = Path(path)
        file_size = file_path.stat().st_size
        upload_time = _format_upload_time(_now_taipei())
        with file_path.open("rb") as fh:
            serial = 1
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                body = {
                    "ExtParameter": {
                        "useMode": "API",
                        "note1": None,
                        "note2": None,
                        "note3": None,
                        "pincode": pincode,
                        "fileName": file_path.name,
                        "filesize": file_size,
                        "isMultiFile": False,
                        "fileSerial": serial,
                        "uploadTime": upload_time,
                    },
                    "buffer": base64.b64encode(chunk).decode("ascii"),
                }
                payload = self._post_json(ENDPOINT_UPLOAD, body)
                status = payload.get("Status")
                if status == "S":
                    return
                if status != "C":
                    raise IbonRequestError(
                        payload.get("Description", "Upload 失敗"),
                        result_code=status,
                    )
                serial += 1

    def upload(
        self,
        path: str,
        user: str = " ",
        email: str = " ",
        spec: PrintSpec | None = None,
    ) -> IbonUploadResult:
        select_type = (spec or PrintSpec.default()).select_type
        self._validate(path)
        token = self._fetch_entry()
        pincode_response = self._fetch_pincode(token, user, email, select_type)
        chunk_size = self._fetch_chunk_size()
        result = IbonUploadResult.from_pincode_response(pincode_response)
        self._upload_chunks(result.pincode, path, chunk_size)
        return _attach_qrcode(result)
