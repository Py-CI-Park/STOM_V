"""Typed diagnostic states for the production trade CSV adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

QualityStatus = Literal[
    "VALID",
    "NO_TRADES",
    "MISSING_ARTIFACT",
    "INVALID_SCHEMA",
    "ROW_PARSE_PARTIAL",
    "ROW_COUNT_MISMATCH",
    "NONFINITE_VALUE",
    "IDENTITY_MISMATCH",
    "IO_ERROR",
    "ENCODING_ERROR",
    "RESOURCE_LIMIT",
]


class QualityModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, extra="forbid", allow_inf_nan=False
    )


class CsvIssue(QualityModel):
    code: QualityStatus
    row: int | None = None
    column: str = ""
    detail: str


class TradeCsvQuality(QualityModel):
    schema_version: Literal["stom.trade_csv_quality.v1"] = "stom.trade_csv_quality.v1"
    status: QualityStatus
    source_sha256: str | None = None
    source_bytes: int | None = None
    raw_count: int | None = None
    accepted_count: int | None = None
    rejected_count: int | None = None
    expected_row_count: int | None = None
    parse_complete: bool = False
    analysis_ready: bool = False
    issues: tuple[CsvIssue, ...] = ()
    issue_codes: tuple[QualityStatus, ...] = ()
    official_schema: str | None = None
    issue_count: int = 0
    issues_truncated: bool = False
    authority: Literal["diagnostic_no_execution_grant"] = (
        "diagnostic_no_execution_grant"
    )


class NormalizedTrade(QualityModel):
    name: str
    buy_time: str
    sell_time: str
    day: int
    timeframe: Literal["tick", "min"]
    hold_sec: float
    hold_min: float
    profit_pct: float
    profit_krw: float
    buy_amount: float | None
    sell_amount: float | None
    mfe: float | None
    mae: float | None
    exit_reason: str
    of_strength: float | None
    of_buy_rest: float | None
    of_sell_rest: float | None
    of_prevday: float | None
    of_updown: float | None


@dataclass(frozen=True, slots=True)
class CsvSnapshot:
    path: str
    sha256: str
    size: int
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class TradeQualityResult:
    snapshot: CsvSnapshot | None
    trades: tuple[NormalizedTrade, ...]
    quality: TradeCsvQuality
