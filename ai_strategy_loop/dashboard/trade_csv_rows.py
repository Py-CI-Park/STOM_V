"""Validate consumed CSV cells before reusing the existing row normalizer."""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING, Final

from pydantic import ValidationError

from ai_strategy_loop.dashboard.backtest_analysis import _normalize_row
from ai_strategy_loop.dashboard.trade_csv_models import CsvIssue, NormalizedTrade

if TYPE_CHECKING:
    from collections.abc import Mapping

REQUIRED_COLUMNS: Final = (
    "종목명",
    "매수시간",
    "매도시간",
    "보유시간",
    "수익률",
    "수익금",
)
_NUMERIC: Final = (
    "보유시간",
    "수익률",
    "수익금",
    "매수금액",
    "매도금액",
    "R_MFE",
    "R_MAE",
    "B_체결강도",
    "B_매수총잔량",
    "B_매도총잔량",
    "B_전일동시간비",
    "B_등락율",
)


def normalize_csv_record(
    headers: tuple[str, ...],
    cells: tuple[str, ...],
    row_number: int,
) -> tuple[NormalizedTrade | None, tuple[CsvIssue, ...]]:
    """Keep 0 intact; reject missing/invalid/nonfinite cells instead of coercing."""
    if len(cells) != len(headers):
        return None, (
            CsvIssue(
                code="ROW_PARSE_PARTIAL",
                row=row_number,
                detail="Column count differs from header",
            ),
        )
    row = dict(zip(headers, cells, strict=True))
    issues: list[CsvIssue] = []
    for column in REQUIRED_COLUMNS:
        if not row[column].strip():
            issues.append(
                CsvIssue(
                    code="ROW_PARSE_PARTIAL",
                    row=row_number,
                    column=column,
                    detail="Required value is empty",
                )
            )
    issues.extend(_numeric_issues(row, row_number))
    buy, sell = row["매수시간"].strip(), row["매도시간"].strip()
    if not _valid_timestamps(buy, sell):
        issues.append(
            CsvIssue(
                code="ROW_PARSE_PARTIAL",
                row=row_number,
                detail="Invalid or reversed trade timestamps",
            )
        )
    if issues:
        return None, tuple(issues)
    try:
        trade = NormalizedTrade.model_validate(_normalize_row(row))
    except ValidationError:
        return None, (
            CsvIssue(
                code="ROW_PARSE_PARTIAL",
                row=row_number,
                detail="Normalized trade violates the typed contract",
            ),
        )
    return trade, ()


def _numeric_issues(row: Mapping[str, str], row_number: int) -> tuple[CsvIssue, ...]:
    """Inspect consumed numeric fields without changing their values."""
    issues: list[CsvIssue] = []
    numeric_columns = dict.fromkeys(
        (*_NUMERIC, *(name for name in row if name.startswith(("B_", "S_", "R_"))))
    )
    for column in numeric_columns:
        value = row.get(column, "").strip()
        if not value:
            continue
        try:
            number = float(value)
        except ValueError:
            issues.append(
                CsvIssue(
                    code="ROW_PARSE_PARTIAL",
                    row=row_number,
                    column=column,
                    detail="Numeric value cannot be parsed",
                )
            )
            continue
        if not math.isfinite(number):
            issues.append(
                CsvIssue(
                    code="NONFINITE_VALUE",
                    row=row_number,
                    column=column,
                    detail="Numeric value must be finite",
                )
            )
        elif column == "보유시간" and number < 0:
            issues.append(
                CsvIssue(
                    code="ROW_PARSE_PARTIAL",
                    row=row_number,
                    column=column,
                    detail="Holding duration is negative",
                )
            )
    return tuple(issues)


def _valid_timestamps(buy: str, sell: str) -> bool:
    """Require paired ASCII calendar timestamps and nonnegative duration."""
    if len(buy) != len(sell) or len(sell) not in (12, 14):
        return False
    if not (buy.isascii() and buy.isdigit() and sell.isascii() and sell.isdigit()):
        return False
    fmt = "%Y%m%d%H%M%S" if len(sell) == 14 else "%Y%m%d%H%M"
    try:
        return datetime.strptime(sell, fmt) >= datetime.strptime(buy, fmt)
    except ValueError:
        return False
