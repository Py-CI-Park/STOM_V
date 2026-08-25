"""Typed, read-only SQLite source access for the RES-02 Event Gate."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from typing import cast

import numpy as np

from ai_strategy_loop.revision.mcap_event_contract import (
    DevelopmentFold,
    EventGateContractError,
)
from ai_strategy_loop.revision.mcap_event_logic import TickDay

SqlScalar = int | float | str | bytes | None
SqlRow = tuple[SqlScalar, ...]
_CODE = re.compile(r"^\d{6}$")
_TICK_COLUMN_POSITIONS = (0, 1, 5, 7, 14, 15, 17, 18, 19, 50, 51, 53)


@dataclass(frozen=True, slots=True)
class TickProjection:
    columns: tuple[str, ...]

    @property
    def select_list(self) -> str:
        return ", ".join(
            f'"{column.replace(chr(34), chr(34) * 2)}"' for column in self.columns
        )


@dataclass(frozen=True, slots=True)
class EventSourceScope:
    code_days: dict[str, set[int]]
    day_to_fold: dict[int, str]
    moneytop_rows: int
    available_tables: set[str]
    tick_projection: TickProjection


def number(value: SqlScalar) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bytes):
        raise EventGateContractError("binary value in numeric tick column")
    try:
        return float(value)
    except ValueError as exc:
        raise EventGateContractError(f"non-numeric tick value: {value!r}") from exc


def timestamp(value: SqlScalar) -> int:
    numeric = number(value)
    if not numeric.is_integer():
        raise EventGateContractError(f"non-integral tick timestamp: {value!r}")
    return int(numeric)


def tick_day(rows: list[SqlRow]) -> TickDay:
    if not rows or any(len(row) != len(_TICK_COLUMN_POSITIONS) for row in rows):
        raise EventGateContractError("stock tick projection must contain 12 columns")

    def floats(position: int) -> np.ndarray:
        values = np.asarray([number(row[position]) for row in rows], dtype=np.float64)
        return np.nan_to_num(values)

    return TickDay(
        timestamp=np.asarray([timestamp(row[0]) for row in rows], dtype=np.int64),
        price=floats(1),
        rate=floats(2),
        strength=floats(3),
        market_cap=floats(4),
        round_figure=floats(5),
        vi_price=floats(6),
        vi_unit=floats(7),
        second_money=floats(8),
        ask_total=floats(9),
        bid_total=floats(10),
        interest=floats(11),
    )


def _validate_folds(folds: tuple[DevelopmentFold, ...]) -> None:
    if not folds or len({fold.id for fold in folds}) != len(folds):
        raise EventGateContractError("development folds must be non-empty and unique")
    for fold in folds:
        if fold.start > fold.end or fold.end >= 20260101:
            raise EventGateContractError("invalid or holdout-touching development fold")
        for prior in folds:
            if prior.id != fold.id and max(fold.start, prior.start) <= min(
                fold.end, prior.end
            ):
                raise EventGateContractError("development folds overlap")


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {
        str(row[0])
        for row in iter_sql_rows(rows)
        if row and row[0] is not None and _CODE.fullmatch(str(row[0]))
    }


def iter_sql_rows(cursor: sqlite3.Cursor) -> Iterator[SqlRow]:
    while True:
        row = cast(SqlRow | None, cursor.fetchone())
        if row is None:
            return
        yield row


def _load_tick_projection(
    connection: sqlite3.Connection, available_tables: set[str]
) -> TickProjection:
    if not available_tables:
        raise EventGateContractError("stock tick database has no six-digit tables")
    sample_table = min(available_tables)
    schema = tuple(
        iter_sql_rows(connection.execute(f'PRAGMA table_info("{sample_table}")'))
    )
    if len(schema) < 54 or any(len(row) < 2 or row[1] is None for row in schema):
        raise EventGateContractError("stock tick table must expose 54 base columns")
    names = tuple(str(schema[position][1]) for position in _TICK_COLUMN_POSITIONS)
    if len(set(names)) != len(names):
        raise EventGateContractError("stock tick projection columns must be unique")
    return TickProjection(columns=names)


def load_source_scope(
    connection: sqlite3.Connection,
    folds: tuple[DevelopmentFold, ...],
    window_start: int,
    window_end_exclusive: int,
) -> EventSourceScope:
    _validate_folds(folds)
    code_days: dict[str, set[int]] = {}
    day_to_fold: dict[int, str] = {}
    row_count = 0
    start_time = max(window_start, 90030)
    for fold in folds:
        rows = connection.execute(
            "SELECT * FROM moneytop WHERE [index] >= ? AND [index] <= ?",
            (
                fold.start * 1_000_000 + start_time,
                fold.end * 1_000_000 + window_end_exclusive,
            ),
        )
        for row in iter_sql_rows(rows):
            if len(row) < 2:
                raise EventGateContractError(
                    "moneytop row is missing membership column"
                )
            day = timestamp(row[0]) // 1_000_000
            day_to_fold[day] = fold.id
            members = () if row[1] is None else tuple(str(row[1]).split(";"))
            for code in members:
                if _CODE.fullmatch(code):
                    code_days.setdefault(code, set()).add(day)
            row_count += 1
    available_tables = _table_names(connection)
    return EventSourceScope(
        code_days,
        day_to_fold,
        row_count,
        available_tables,
        _load_tick_projection(connection, available_tables),
    )


def query_code_rows(
    connection: sqlite3.Connection,
    code: str,
    days: set[int],
    window_start: int,
    window_end_exclusive: int,
    projection: TickProjection,
) -> sqlite3.Cursor:
    if not _CODE.fullmatch(code):
        raise EventGateContractError(f"unsafe symbol table name: {code!r}")
    clauses: list[str] = []
    parameters: list[int] = []
    for day in sorted(days):
        clauses.append("([index] >= ? AND [index] <= ?)")
        parameters.extend(
            (
                day * 1_000_000 + window_start,
                day * 1_000_000 + window_end_exclusive,
            )
        )
    return connection.execute(
        f'SELECT {projection.select_list} FROM "{code}" WHERE {" OR ".join(clauses)}',
        parameters,
    )
