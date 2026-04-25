"""打包層 smoke test：套件可被匯入、console scripts 已註冊。"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_can_import_ibon_printer_package():
    # 清除快取的匯入，避免先前失敗的 import 留下殘根。
    sys.modules.pop("ibon_printer", None)
    module = importlib.import_module("ibon_printer")
    assert module is not None


def test_console_scripts_registered():
    pyproject = REPO_ROOT / "pyproject.toml"
    assert pyproject.is_file(), "pyproject.toml missing at repo root"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    scripts = data.get("project", {}).get("scripts", {})
    assert scripts.get("ibon-printer") == "ibon_printer.cli:main"
    assert scripts.get("ibon-printer-api") == "ibon_printer.api:run"
