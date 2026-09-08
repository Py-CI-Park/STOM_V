"""Reject oversized SQLite values before Python materializes invalid cells."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest

from ai_strategy_loop.revision import res04_tick_source as source
from tests.unit.res04_binding_fixtures import source_plan


def test_oversized_sqlite_blob_rejected_at_sqlite_boundary(tmp_path: Path) -> None:
    # Given: a 64KiB invalid price cell in a hash-matched disposable source.
    plan = source_plan(tmp_path)
    path = Path(plan.source.path)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            'UPDATE "005930" SET c1=? '
            'WHERE "index"=(SELECT MIN("index") FROM "005930")',
            (b"x" * 65536,),
        )
        connection.commit()
    identity = plan.source.model_copy(
        update={
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
    plan = plan.model_copy(update={"source": identity})
    # When / Then: SQLite size error, not late Pydantic numeric rejection.
    with pytest.raises(ValueError, match="SOURCE_CELL_LIMIT"):
        source.read_tick_slice(
            plan, source.SourceRequest(symbol="005930", session_day=date(2022, 4, 1))
        )
