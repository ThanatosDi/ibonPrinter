"""例外型別：區分本機驗證失敗與 ibon 端回傳的失敗。"""
from __future__ import annotations


class IbonValidationError(Exception):
    """本機前置條件不通過時於發網路請求前拋出。

    涵蓋檔案不存在、副檔名不支援、檔案過大等情境。
    呼叫端可視為使用者可自行修正的輸入錯誤（對應 HTTP 400 一類）。
    """


class IbonRequestError(Exception):
    """ibon 端或傳輸層回報失敗時拋出。

    封裝上游回傳的 ``Message``、HTTP ``status_code`` 與 ibon
    ``ResultCode``，讓呼叫端不必解析 ``str(exc)`` 即可區分
    傳輸層失敗與伺服器回報的業務錯誤。
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        result_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.result_code = result_code
