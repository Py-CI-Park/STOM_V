"""Quality-aware production CSV loading; no cache or execution authority."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from ai_strategy_loop.dashboard.trade_csv_models import (
    CsvIssue,
    CsvSnapshot,
    NormalizedTrade,
    QualityStatus,
    TradeCsvQuality,
    TradeQualityResult,
)
from ai_strategy_loop.dashboard.trade_csv_rows import (
    REQUIRED_COLUMNS,
    normalize_csv_record,
)
from ai_strategy_loop.dashboard.trade_csv_schema import official_csv_variant
from ai_strategy_loop.dashboard.trade_csv_snapshot import (
    CsvSnapshotError,
    read_csv_snapshot,
)

if TYPE_CHECKING:
    from pathlib import Path

_ISSUE_LIMIT: Final = 100
_PRIORITY: Final[tuple[QualityStatus, ...]] = (
    "IDENTITY_MISMATCH",
    "INVALID_SCHEMA",
    "ROW_COUNT_MISMATCH",
    "NONFINITE_VALUE",
    "ROW_PARSE_PARTIAL",
)


def _has_required_headers(headers: tuple[str, ...]) -> bool:
    return (
        len(headers) == len(set(headers))
        and all(name in headers for name in REQUIRED_COLUMNS)
        and all(name.strip() for name in headers)
    )


def _summary_status(codes: set[QualityStatus], has_trades: bool) -> QualityStatus:
    for code in _PRIORITY:
        if code in codes:
            return code
    return "VALID" if has_trades else "NO_TRADES"


def _expectation_issues(
    snapshot: CsvSnapshot,
    count: int | None,
    sha256: str | None,
) -> tuple[CsvIssue, ...]:
    issues: list[CsvIssue] = []
    if sha256 is not None and snapshot.sha256 != sha256:
        issues.append(
            CsvIssue(code="IDENTITY_MISMATCH", detail="Expected source hash differs")
        )
    if count is not None and len(snapshot.rows) != count:
        issues.append(
            CsvIssue(code="ROW_COUNT_MISMATCH", detail="Expected raw row count differs")
        )
    return tuple(issues)


def inspect_trade_snapshot(
    snapshot: CsvSnapshot,
    *,
    expected_row_count: int | None = None,
    expected_sha256: str | None = None,
) -> TradeQualityResult:
    """Inspect one snapshot, retaining all issue categories and bounded row details."""
    issues: list[CsvIssue] = []
    codes: set[QualityStatus] = set()
    issue_count = 0

    def add(issue: CsvIssue) -> None:
        nonlocal issue_count
        issue_count += 1
        codes.add(issue.code)
        if len(issues) < _ISSUE_LIMIT:
            issues.append(issue)

    for issue in _expectation_issues(snapshot, expected_row_count, expected_sha256):
        add(issue)
    schema_valid = _has_required_headers(snapshot.headers)
    trades: list[NormalizedTrade] = []
    official_schema = official_csv_variant(snapshot.headers)
    if official_schema is None:
        add(
            CsvIssue(
                code="INVALID_SCHEMA",
                detail="Not a supported official 54/37-column schema",
            )
        )
    if not schema_valid:
        add(
            CsvIssue(
                code="INVALID_SCHEMA", detail="Duplicate/empty/missing required header"
            )
        )
    else:
        for index, cells in enumerate(snapshot.rows, start=2):
            trade, row_issues = normalize_csv_record(snapshot.headers, cells, index)
            for issue in row_issues:
                add(issue)
            if trade is not None:
                trades.append(trade)
        if len(trades) != len(snapshot.rows):
            add(
                CsvIssue(
                    code="ROW_PARSE_PARTIAL", detail="Rejected rows are diagnostic only"
                )
            )
    status = _summary_status(codes, bool(trades))
    return TradeQualityResult(
        snapshot,
        tuple(trades),
        TradeCsvQuality(
            status=status,
            source_sha256=snapshot.sha256,
            source_bytes=snapshot.size,
            raw_count=len(snapshot.rows),
            accepted_count=len(trades),
            rejected_count=len(snapshot.rows) - len(trades),
            expected_row_count=expected_row_count,
            parse_complete=True,
            analysis_ready=status == "VALID",
            issues=tuple(issues),
            issue_codes=tuple(sorted(codes)),
            official_schema=official_schema,
            issue_count=issue_count,
            issues_truncated=issue_count > len(issues),
        ),
    )


def load_trade_quality(
    csv_path: Path,
    *,
    expected_row_count: int | None = None,
    expected_sha256: str | None = None,
) -> TradeQualityResult:
    """Read-only typed counterpart to the preserved legacy list-returning loader."""
    try:
        snapshot = read_csv_snapshot(csv_path)
    except CsvSnapshotError as exc:
        issue = CsvIssue(code=exc.code, detail=exc.detail)
        return TradeQualityResult(
            None,
            (),
            TradeCsvQuality(
                status=exc.code,
                source_sha256=exc.sha256,
                source_bytes=exc.size,
                expected_row_count=expected_row_count,
                issues=(issue,),
                issue_codes=(exc.code,),
                issue_count=1,
            ),
        )
    return inspect_trade_snapshot(
        snapshot, expected_row_count=expected_row_count, expected_sha256=expected_sha256
    )
