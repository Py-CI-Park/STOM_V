"""Immutable data contract for one official backtest trade artifact."""

from __future__ import annotations

import csv
import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias

from backtest.back_static import (
    TRADE_RESULT_B_COLUMNS,
    TRADE_RESULT_R_COLUMNS,
    TRADE_RESULT_S_COLUMNS,
)


Scalar: TypeAlias = str | int | float | bool | None
ColumnStatus: TypeAlias = Literal["available", "zero_only", "missing"]

_MODERN_COLUMN_COUNT: Final[int] = 54
_LEGACY_COLUMN_COUNT: Final[int] = 37
_GROUPS: Final[tuple[tuple[str, Sequence[str]], ...]] = (
    ("B", TRADE_RESULT_B_COLUMNS),
    ("S", TRADE_RESULT_S_COLUMNS),
    ("R", TRADE_RESULT_R_COLUMNS),
)


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    path: str
    sha256: str
    bytes: int
    row_count: int
    column_count: int
    schema_variant: str


@dataclass(frozen=True, slots=True)
class ColumnAvailability:
    name: str
    group: str
    status: ColumnStatus
    populated_count: int
    non_zero_count: int


@dataclass(frozen=True, slots=True)
class GroupAvailability:
    group: str
    expected_count: int
    present_count: int
    available_count: int
    zero_only_count: int
    missing_count: int


@dataclass(frozen=True, slots=True)
class SessionBoundary:
    start_time: int | None
    forced_liquidation_time: int | None
    source: str
    confidence: str


@dataclass(frozen=True, slots=True)
class CostPolicy:
    engine: str
    tax_rate_pct: float
    buy_fee_rate_pct: float
    sell_fee_rate_pct: float
    round_trip_rate_pct: float
    result_profit_state: str


@dataclass(frozen=True, slots=True)
class StrategyIdentity:
    buy: str
    sell: str
    buy_sha256: str
    sell_sha256: str


@dataclass(frozen=True, slots=True)
class TradeArtifactContract:
    schema_version: str
    job_id: str
    timeframe: str
    artifact: ArtifactIdentity
    boundary: SessionBoundary
    cost_policy: CostPolicy
    strategy: StrategyIdentity
    groups: tuple[GroupAvailability, ...]
    columns: tuple[ColumnAvailability, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_sha256(value: Scalar) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _non_zero(value: str | None) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    try:
        number = float(text.replace(",", ""))
    except ValueError:
        return True
    return math.isfinite(number) and number != 0.0


def _schema_variant(column_count: int) -> str:
    if column_count == _MODERN_COLUMN_COUNT:
        return "modern_54"
    if column_count == _LEGACY_COLUMN_COUNT:
        return "legacy_37"
    return f"custom_{column_count}"


def _column_profiles(
    fieldnames: Sequence[str], rows: Sequence[Mapping[str, str]],
) -> tuple[ColumnAvailability, ...]:
    present = set(fieldnames)
    profiles: list[ColumnAvailability] = []
    for group, expected_columns in _GROUPS:
        for name in expected_columns:
            if name not in present:
                profiles.append(ColumnAvailability(name, group, "missing", 0, 0))
                continue
            values = [str(row.get(name) or "").strip() for row in rows]
            populated = sum(bool(value) for value in values)
            non_zero = sum(_non_zero(value) for value in values)
            status: ColumnStatus = "available" if non_zero else "zero_only"
            profiles.append(ColumnAvailability(name, group, status, populated, non_zero))
    return tuple(profiles)


def _group_profiles(
    columns: Sequence[ColumnAvailability],
) -> tuple[GroupAvailability, ...]:
    result: list[GroupAvailability] = []
    for group, expected in _GROUPS:
        rows = [row for row in columns if row.group == group]
        result.append(GroupAvailability(
            group=group,
            expected_count=len(expected),
            present_count=sum(row.status != "missing" for row in rows),
            available_count=sum(row.status == "available" for row in rows),
            zero_only_count=sum(row.status == "zero_only" for row in rows),
            missing_count=sum(row.status == "missing" for row in rows),
        ))
    return tuple(result)


def _optional_int(value: Scalar) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def build_trade_artifact_contract(
    *, csv_path: Path, job_id: str, spec: Mapping[str, Scalar],
) -> TradeArtifactContract:
    """Profile an immutable official CSV without changing its contents."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        rows = tuple(reader)
    columns = _column_profiles(fieldnames, rows)
    end_time = _optional_int(spec.get("end_time"))
    boundary = SessionBoundary(
        start_time=_optional_int(spec.get("start_time")),
        forced_liquidation_time=end_time,
        source="job_spec_end_time" if end_time is not None else "missing",
        confidence="official" if end_time is not None else "unknown",
    )
    artifact = ArtifactIdentity(
        path=str(csv_path.resolve()),
        sha256=_sha256(csv_path),
        bytes=csv_path.stat().st_size,
        row_count=len(rows),
        column_count=len(fieldnames),
        schema_variant=_schema_variant(len(fieldnames)),
    )
    return TradeArtifactContract(
        schema_version="qsp7-trade-artifact-v1",
        job_id=job_id,
        timeframe=str(spec.get("timeframe") or "unknown"),
        artifact=artifact,
        boundary=boundary,
        cost_policy=CostPolicy("GetKiwoomPgSgSp", 0.18, 0.015, 0.015, 0.21, "already_net"),
        strategy=StrategyIdentity(
            buy=str(spec.get("buy") or ""),
            sell=str(spec.get("sell") or ""),
            buy_sha256=_text_sha256(spec.get("buy_code")),
            sell_sha256=_text_sha256(spec.get("sell_code")),
        ),
        groups=_group_profiles(columns),
        columns=columns,
    )

