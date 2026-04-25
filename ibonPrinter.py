"""已棄用的相容 shim：以 ``IBON`` 名稱重新匯出 IbonClient 供舊程式相容。

預計於 1.0 版後移除，新程式請改為：

    from ibon_printer import IbonClient
"""
from __future__ import annotations

import warnings

from ibon_printer.client import IbonClient as IBON

warnings.warn(
    "ibonPrinter 已棄用，請改用 'from ibon_printer import IbonClient'",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["IBON"]
