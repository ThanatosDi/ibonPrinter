"""相容性 shim：ibonPrinter.IBON 仍能對應到新的 IbonClient。"""
from __future__ import annotations

import importlib
import os
import sys
import warnings
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _reload_shim():
    sys.modules.pop("ibonPrinter", None)
    # 確保不論測試從哪個 cwd 執行，repo 根目錄都可被匯入。
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    return importlib.import_module("ibonPrinter")


def test_legacy_import_path_still_works():
    mod = _reload_shim()
    assert mod.IBON() is not None


def test_legacy_instance_is_ibon_client():
    from ibon_printer.client import IbonClient

    mod = _reload_shim()
    assert isinstance(mod.IBON(), IbonClient)


def test_legacy_import_emits_deprecation_warning():
    sys.modules.pop("ibonPrinter", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _reload_shim()
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_legacy_root_cli_removed():
    assert not (REPO_ROOT / "cli.py").exists()
