"""Adversarial SQLite source boundaries, using only disposable fixtures."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ai_strategy_loop.revision import res04_tick_source as source
from tests.unit.res04_binding_fixtures import source_plan

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ai_strategy_loop.revision.mcap_event_source import SqlRow


def test_empty_source_is_not_successful_no_trades(tmp_path: Path) -> None:
    # Given: valid schema, no market rows in a synthetic source.
    plan = source_plan(tmp_path, rows=0)
    # When / Then: absence remains a source error, not a trading result.
    with pytest.raises(ValueError, match="SOURCE_NO_ROWS"):
        source.read_tick_slice(
            plan, source.SourceRequest(symbol="005930", session_day=date(2022, 4, 1))
        )


def test_view_cannot_masquerade_as_symbol_table(tmp_path: Path) -> None:
    # Given: even a hash-matched DB must expose a physical symbol table.
    plan = source_plan(tmp_path)
    path = Path(plan.source.path)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute('ALTER TABLE "005930" RENAME TO original')
        connection.execute('CREATE VIEW "005930" AS SELECT * FROM original')
        connection.commit()
    identity = plan.source.model_copy(
        update={
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
    plan = plan.model_copy(update={"source": identity})
    # When / Then.
    with pytest.raises(ValueError, match="SOURCE_SYMBOL_TABLE_REQUIRED"):
        source.read_tick_slice(
            plan, source.SourceRequest(symbol="005930", session_day=date(2022, 4, 1))
        )


def test_query_budget_interrupts_without_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a deliberately tiny VM budget, without a costly query.
    plan = source_plan(tmp_path)
    monkeypatch.setattr(source, "_MAX_PROGRESS_CALLS", 0)
    monkeypatch.setattr(source, "_PROGRESS_INTERVAL", 1)
    # When / Then: normal boundary error, no partial successful slice.
    with pytest.raises(ValueError, match="SOURCE_QUERY_FAILED_OR_LIMITED"):
        source.read_tick_slice(
            plan, source.SourceRequest(symbol="005930", session_day=date(2022, 4, 1))
        )


def test_changed_file_during_read_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a local fixture changed after its rows have been read.
    plan = source_plan(tmp_path)
    original = source.iter_sql_rows

    def mutate_after_rows(cursor: sqlite3.Cursor) -> Iterator[SqlRow]:
        yield from original(cursor)
        with Path(plan.source.path).open("ab") as handle:
            handle.write(b"changed")

    monkeypatch.setattr(source, "iter_sql_rows", mutate_after_rows)
    # When / Then: before/after full fingerprints differ and no output escapes.
    with pytest.raises(ValueError, match="SOURCE_CHANGED_DURING_READ"):
        source.read_tick_slice(
            plan, source.SourceRequest(symbol="005930", session_day=date(2022, 4, 1))
        )


@pytest.mark.parametrize("symbol", ['005930" UNION SELECT 1', "../005930", "٠٠٥٩٣٠"])
def test_symbol_identifiers_are_strict_ascii(symbol: str) -> None:
    # Given / When / Then: reject before any file access or SQL interpolation.
    with pytest.raises(ValidationError):
        source.SourceRequest(symbol=symbol, session_day=date(2022, 4, 1))
