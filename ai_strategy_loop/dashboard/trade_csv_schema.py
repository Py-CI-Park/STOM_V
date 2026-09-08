"""Official header names from GetResultDataframe owners, not column count alone."""

from __future__ import annotations

from typing import Final

from backtest.back_static import (
    TRADE_RESULT_B_COLUMNS,
    TRADE_RESULT_R_COLUMNS,
    TRADE_RESULT_S_COLUMNS,
)
from utility.setting_base import columns_bt, columns_btf

_MODERN_EXTRAS: Final = tuple(
    [*TRADE_RESULT_B_COLUMNS, *TRADE_RESULT_S_COLUMNS, *TRADE_RESULT_R_COLUMNS]
)
# Before 737d3cde's B-feature extension, the first fourteen B fields were emitted.
_LEGACY_EXTRAS: Final = tuple(
    [*TRADE_RESULT_B_COLUMNS[:14], *TRADE_RESULT_S_COLUMNS, *TRADE_RESULT_R_COLUMNS]
)
_BASES: Final = (tuple(columns_bt), tuple(columns_btf))


def official_csv_variant(headers: tuple[str, ...]) -> str | None:
    """Accept named modern/legacy schemas, allowing name-based column reordering."""
    present = frozenset(headers)
    if len(present) != len(headers):
        return None
    for base in _BASES:
        if len(headers) == 54 and present == frozenset((*base, *_MODERN_EXTRAS)):
            return "modern_54"
        if len(headers) == 37 and present == frozenset((*base, *_LEGACY_EXTRAS)):
            return "legacy_37"
    return None
