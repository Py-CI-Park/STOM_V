"""One bounded byte snapshot; hash and CSV parsing never reopen the file."""

from __future__ import annotations

import csv
import hashlib
import io
import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, override

from ai_strategy_loop.dashboard.trade_csv_models import CsvSnapshot, QualityStatus

if TYPE_CHECKING:
    from pathlib import Path

MAX_CSV_BYTES: Final = 64 * 1024 * 1024
MAX_CSV_ROWS: Final = 250_000
MAX_CSV_CELLS: Final = 5_000_000
MAX_CSV_COLUMNS: Final = 128


@dataclass(frozen=True, slots=True)
class CsvSnapshotError(Exception):
    code: QualityStatus
    detail: str
    sha256: str | None = None
    size: int | None = None

    @override
    def __str__(self) -> str:
        return self.detail


def read_csv_snapshot(path: Path) -> CsvSnapshot:
    """Capture a regular UTF-8 CSV; reject malformed/truncated oversized input."""
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            raise CsvSnapshotError("IO_ERROR", "CSV is not a regular file")
        with path.open("rb") as handle:
            data = handle.read(MAX_CSV_BYTES + 1)
    except FileNotFoundError as exc:
        raise CsvSnapshotError("MISSING_ARTIFACT", "CSV file is missing") from exc
    except OSError as exc:
        raise CsvSnapshotError("IO_ERROR", "CSV cannot be read") from exc
    if len(data) > MAX_CSV_BYTES:
        raise CsvSnapshotError("RESOURCE_LIMIT", "CSV byte limit exceeded")
    sha = hashlib.sha256(data).hexdigest()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvSnapshotError(
            "ENCODING_ERROR", "CSV must be UTF-8", sha, len(data)
        ) from exc
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    rows: list[tuple[str, ...]] = []
    cells = 0
    try:
        headers = tuple(next(reader, ()))
        if len(headers) > MAX_CSV_COLUMNS:
            raise CsvSnapshotError(
                "RESOURCE_LIMIT", "CSV column limit exceeded", sha, len(data)
            )
        for record in reader:
            cells += len(record)
            if len(rows) >= MAX_CSV_ROWS or cells > MAX_CSV_CELLS:
                raise CsvSnapshotError(
                    "RESOURCE_LIMIT", "CSV row/cell limit exceeded", sha, len(data)
                )
            rows.append(tuple(record))
    except csv.Error as exc:
        raise CsvSnapshotError(
            "INVALID_SCHEMA", "Malformed CSV record", sha, len(data)
        ) from exc
    return CsvSnapshot(str(path.absolute()), sha, len(data), headers, tuple(rows))
