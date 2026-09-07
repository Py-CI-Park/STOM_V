"""Bounded, immutable-read SQLite slices with full-file identity verification."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Final, Literal

from pydantic import ConfigDict, Field, FiniteFloat, StringConstraints, TypeAdapter

from ai_strategy_loop.controller.research_truth_models import (
    FrozenContract,
    Sha256Text,
    TruthContractViolation,
)
from ai_strategy_loop.revision.mcap_event_contract import SourceFingerprint
from ai_strategy_loop.revision.mcap_event_source import (
    _load_tick_projection,
    iter_sql_rows,
    tick_day,
)
from utility.sqlite_readonly import connect_existing_db_readonly, sqlite_fingerprint

if TYPE_CHECKING:
    from ai_strategy_loop.revision.mcap_event_logic import TickDay
    from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation

_MAX_DB_BYTES: Final = 32 * 1024**3
_SIDEFILES: Final = ("-wal", "-shm", "-journal")
_PROGRESS_INTERVAL: Final = 10_000
_MAX_PROGRESS_CALLS: Final = 1_000
_MAX_SQLITE_VALUE_BYTES: Final = 16_384
ProjectedRow = tuple[
    int,
    FiniteFloat,
    FiniteFloat,
    FiniteFloat,
    FiniteFloat,
    FiniteFloat,
    FiniteFloat,
    FiniteFloat,
    FiniteFloat,
    FiniteFloat,
    FiniteFloat,
    FiniteFloat,
]
_ROW: Final = TypeAdapter(ProjectedRow, config=ConfigDict(strict=True))


class SourceRequest(FrozenContract):
    """One symbol/day; not a campaign or an execution grant."""

    symbol: Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]
    session_day: date
    max_rows: int = Field(default=3000, ge=1, le=10_000)


class SliceReceipt(FrozenContract):
    """Identity was checked around the bounded read, not merely declared."""

    path: str
    sha256: Sha256Text
    size_bytes: int
    access: Literal["IMMUTABLE_READONLY"] = "IMMUTABLE_READONLY"
    symbol: str
    session_day: date
    fold: str
    row_count: int
    columns: tuple[str, ...]
    query_sha256: Sha256Text
    first_timestamp: int
    last_timestamp: int


@dataclass(frozen=True, slots=True)
class TickSlice:
    """Internal validated arrays plus the source read receipt."""

    ticks: TickDay
    receipt: SliceReceipt


def _no_sidefiles(path: Path) -> None:
    if any(Path(str(path) + suffix).exists() for suffix in _SIDEFILES):
        raise TruthContractViolation("SOURCE_SIDEFILE_PRESENT")


def _source_path(
    preparation: Res04Preparation, request: SourceRequest
) -> tuple[Path, str]:
    """Reject scope errors before any database file is opened."""
    folds = tuple(
        f for f in preparation.folds if f.start <= request.session_day < f.end_exclusive
    )
    if len(folds) != 1:
        raise TruthContractViolation("SOURCE_FOLD_NOT_ALLOWED")
    if (
        not time(9)
        <= preparation.window_start
        < preparation.window_end_exclusive
        <= time(9, 30)
    ):
        raise TruthContractViolation("SOURCE_SESSION_NOT_SUPPORTED")
    path = Path(preparation.source.path)
    if not path.is_absolute() or path.as_posix().startswith("//"):
        raise TruthContractViolation("SOURCE_LOCAL_ABSOLUTE_PATH_REQUIRED")
    path = path.resolve(strict=True)
    if path.as_posix().startswith("//"):
        raise TruthContractViolation("SOURCE_LOCAL_ABSOLUTE_PATH_REQUIRED")
    return path, folds[0].id


def _query_rows(
    connection: sqlite3.Connection,
    request: SourceRequest,
    parameters: tuple[int, int, int],
) -> tuple[list[ProjectedRow], tuple[str, ...], str]:
    """Bound SQL work and value sizes, then parse each row before retaining it."""
    remaining = _MAX_PROGRESS_CALLS

    def exhausted() -> int:
        """Mutable query-local VM budget, released with its connection."""
        nonlocal remaining
        remaining -= 1
        return int(remaining < 0)

    validated: list[ProjectedRow] = []
    _ = connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, _MAX_SQLITE_VALUE_BYTES)
    connection.set_progress_handler(exhausted, _PROGRESS_INTERVAL)
    try:
        kind = connection.execute(
            "SELECT type FROM sqlite_master WHERE name = ?", (request.symbol,)
        ).fetchone()
        if kind != ("table",):
            raise TruthContractViolation("SOURCE_SYMBOL_TABLE_REQUIRED")
        projection = _load_tick_projection(connection, {request.symbol})
        query = (
            f'SELECT {projection.select_list} FROM "{request.symbol}" '  # noqa: S608 - strict symbol; owner quotes columns
            'WHERE "index" >= ? AND "index" < ? ORDER BY "index" LIMIT ?'
        )
        for row in iter_sql_rows(connection.execute(query, parameters)):
            if len(validated) >= request.max_rows:
                raise TruthContractViolation("SOURCE_ROW_LIMIT")
            validated.append(_ROW.validate_python(row))
    except sqlite3.DataError as exc:
        raise TruthContractViolation("SOURCE_CELL_LIMIT") from exc
    except sqlite3.OperationalError as exc:
        raise TruthContractViolation("SOURCE_QUERY_FAILED_OR_LIMITED") from exc
    return validated, projection.columns, query


def read_tick_slice(preparation: Res04Preparation, request: SourceRequest) -> TickSlice:
    """Read a stable local source only; caller must hold research-use authority.

    No writes or permission grants. Production invocation remains gated outside
    this library. Full hashes are deliberately uncached and potentially costly.
    """
    path, fold_id = _source_path(preparation, request)
    _no_sidefiles(path)
    size = path.stat().st_size
    if size != preparation.source.bytes:
        raise TruthContractViolation("SOURCE_IDENTITY_SIZE_MISMATCH")
    if not 0 < size <= _MAX_DB_BYTES:
        raise TruthContractViolation("SOURCE_RESOURCE_LIMIT")
    before = SourceFingerprint.model_validate(
        sqlite_fingerprint(path, full_hash_limit=_MAX_DB_BYTES)
    )
    if before.sha256 != preparation.source.sha256 or before.hash_mode != "full":
        raise TruthContractViolation("SOURCE_IDENTITY_HASH_MISMATCH")
    _no_sidefiles(path)
    day_number = int(request.session_day.strftime("%Y%m%d"))
    end = preparation.window_end_exclusive
    parameters = (
        day_number * 1_000_000 + 90000,
        day_number * 1_000_000 + end.hour * 10000 + end.minute * 100 + end.second,
        request.max_rows + 1,
    )
    with closing(connect_existing_db_readonly(path)) as connection:
        validated, columns, query = _query_rows(connection, request, parameters)
    _no_sidefiles(path)
    after = SourceFingerprint.model_validate(
        sqlite_fingerprint(path, full_hash_limit=_MAX_DB_BYTES)
    )
    _no_sidefiles(path)
    if after != before:
        raise TruthContractViolation("SOURCE_CHANGED_DURING_READ")
    if not validated:
        raise TruthContractViolation("SOURCE_NO_ROWS")
    ticks = tick_day(list(validated))
    return TickSlice(
        ticks,
        SliceReceipt(
            path=str(path),
            sha256=before.sha256,
            size_bytes=size,
            symbol=request.symbol,
            session_day=request.session_day,
            fold=fold_id,
            row_count=len(validated),
            columns=columns,
            query_sha256=hashlib.sha256(
                json.dumps([query, parameters]).encode()
            ).hexdigest(),
            first_timestamp=validated[0][0],
            last_timestamp=validated[-1][0],
        ),
    )
