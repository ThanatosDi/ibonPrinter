"""PrintSpec：UI 規格 → SelectType 字串對應測試。"""
from __future__ import annotations

import pytest

from ibon_printer import PrintSpec


@pytest.mark.parametrize(
    "spec, expected",
    [
        (PrintSpec.default(), "FNOMAL"),
        (PrintSpec.a4(), "FA4BN1"),
        (PrintSpec.a4(color=True), "FA4CN1"),
        (PrintSpec.a4(duplex=True), "FA4BN2"),
        (PrintSpec.a4(color=True, duplex=True), "FA4CN2"),
        (PrintSpec.a4(special_paper=True), "FA4BS1"),
        (PrintSpec.a4(color=True, special_paper=True), "FA4CS1"),
        (PrintSpec.a4(color=True, duplex=True, special_paper=True), "FA4CS2"),
        (PrintSpec.a3(), "FA3BN1"),
        (PrintSpec.a3(color=True), "FA3CN1"),
        (PrintSpec.a3(color=True, duplex=True), "FA3CN2"),
        (PrintSpec.a3(duplex=True), "FA3BN2"),
        (PrintSpec.photo_4x6(), "F4X6N1"),
        (PrintSpec.sticker_4x6(), "F4X6S1"),
    ],
)
def test_select_type_matches_ibon_codes(spec, expected):
    assert spec.select_type == expected


def test_description_includes_chinese_summary():
    spec = PrintSpec.a3(color=True, duplex=True)
    # 描述應該至少能讓人讀懂規格組合。
    assert "A3" in spec.description
    assert "彩色" in spec.description
    assert "雙面" in spec.description


def test_explicit_select_type_passthrough():
    spec = PrintSpec("FA4CS2", "custom")
    assert spec.select_type == "FA4CS2"
    assert spec.description == "custom"
