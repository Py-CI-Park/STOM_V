"""Small SQLite sources and existing immutable candidate metadata for tests."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Final

from ai_strategy_loop.revision.res04_preparation_contract import (
    PreparationSource,
    Res04Preparation,
)
from tests.unit.test_res04_event_stream import day

ROOT: Final = Path(__file__).resolve().parents[2]
DOCS: Final = ROOT / "docs/research/quant_scoring_pipeline"
MANIFEST: Final = DOCS / "evidence/2026-08-15_d3_candidate_manifest.json"
PREREG: Final = DOCS / "evidence/2026-08-26_res01_lt3000_prereg.json"
PREREG_SHA: Final = "923e6bc8ad060bcdb027d84ae9a8fe826d2ffd38ed29fa28304518c02d5f0895"


def source_plan(
    tmp_path: Path, rows: int = 90, *, missing: bool = False
) -> Res04Preparation:
    """Create an isolated 54-column numeric source, never an operating DB."""
    database = tmp_path / "synthetic.db"
    ticks = day(rows)
    columns = '"index" INTEGER,' + ",".join(f'"c{i}" REAL' for i in range(1, 54))
    projection = (0, 1, 5, 7, 14, 15, 17, 18, 19, 50, 51, 53)
    values: list[tuple[int | float | None, ...]] = []
    for i in range(rows):
        record: list[int | float | None] = [0.0] * 54
        for field, position in zip(ticks.__dataclass_fields__, projection, strict=True):
            record[position] = float(getattr(ticks, field)[i])
        record[0] = int(ticks.timestamp[i])
        if missing and i == 0:
            record[1] = None
        values.append(tuple(record))
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(f'CREATE TABLE "005930" ({columns})')
        connection.executemany(
            'INSERT INTO "005930" VALUES (' + ",".join("?" * 54) + ")", values  # noqa: S608 - only fixed placeholders; values are bound
        )
        connection.commit()
    plan = Res04Preparation.model_validate_json(
        (DOCS / "planning/2026-09-07_res04p_preparation.json").read_bytes()
    )
    identity = PreparationSource(
        path=str(database),
        bytes=database.stat().st_size,
        sha256=hashlib.sha256(database.read_bytes()).hexdigest(),
        hash_mode="full_sha256",
        role="DEVELOPMENT_PREVIOUSLY_EXPOSED",
    )
    return plan.model_copy(update={"source": identity})
