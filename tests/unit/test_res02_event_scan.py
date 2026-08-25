from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_strategy_loop.revision.mcap_event_contract import (
    DevelopmentFold,
    EventCandidate,
    PreregisteredEventGate,
)
from ai_strategy_loop.revision.mcap_event_scan import scan_event_gate
from utility.sqlite_readonly import sqlite_sidefile_snapshot


def _candidate() -> EventCandidate:
    return EventCandidate(
        candidate_id="D3_ABSORPTION_REVERSAL_MCAP_A_LT3000_fixture",
        band_id="MCAP_A_LT3000",
        family_id="ABSORPTION_REVERSAL",
        parameters={
            "book_window": 10,
            "prior_book_max": 0.6,
            "price_window": 5,
            "recovery_rate": 0.05,
            "flow_window": 10,
            "flow_ratio": 1.0,
        },
        source="source",
        source_sha256="a" * 64,
        canonical_sha256="b" * 64,
        window_contract_sha256="c" * 64,
    )


def _source_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    columns = ", ".join(["[index] INTEGER", *[f"c{i} REAL" for i in range(1, 54)]])
    connection.execute(f'CREATE TABLE "000001" ({columns})')
    connection.execute("CREATE TABLE moneytop ([index] INTEGER, membership TEXT)")
    connection.execute(
        "INSERT INTO moneytop VALUES (?, ?)",
        (20220401090030, "000001"),
    )
    rows: list[tuple[int | float, ...]] = []
    for offset in range(75):
        values: list[int | float] = [0] * 54
        values[0] = 20220401090000 + offset
        values[1] = 2000.0 if offset < 70 else 2020.0
        values[5] = -1.0
        values[7] = 100.0
        values[14] = 2000.0
        values[15] = 0.0
        values[17] = 4000.0
        values[18] = 1.0
        values[19] = 100.0
        values[50] = 100.0
        values[51] = 100.0
        values[53] = 1.0
        rows.append(tuple(values))
    placeholders = ",".join("?" for _ in range(54))
    connection.executemany(f'INSERT INTO "000001" VALUES ({placeholders})', rows)
    connection.commit()
    connection.close()


def test_readonly_scan_counts_only_triggered_engine_rows(tmp_path: Path) -> None:
    path = tmp_path / "source.db"
    _source_db(path)
    before = sqlite_sidefile_snapshot(path)
    result = scan_event_gate(
        path,
        candidates=(_candidate(),),
        folds=(DevelopmentFold(id="DEV", start=20220401, end=20220430),),
        gate=PreregisteredEventGate(
            observations_may_include=(
                "candidate_id",
                "fold_id",
                "day",
                "symbol",
                "timestamp",
                "triggered",
            ),
            forbidden_fields=(
                "profit",
                "return",
                "mdd",
                "win_rate",
                "future_price",
                "exit_result",
            ),
            min_total_events=1,
            min_events_per_fold=1,
            min_distinct_days=1,
            min_distinct_symbols=1,
        ),
        window_start=90000,
        window_end_exclusive=93000,
    )
    assert result.estimates[0].total_events == 4
    assert result.estimates[0].fold_counts == {"DEV": 4}
    assert result.estimates[0].verdict == "EVENT_COUNT_PASS"
    assert result.stats.tick_rows == 75
    assert result.stats.base_eligible_tick_rows == 15
    assert sqlite_sidefile_snapshot(path) == before
