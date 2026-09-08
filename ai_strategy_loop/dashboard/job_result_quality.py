"""Typed CSV admission for the existing job result route, without metric changes."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import ConfigDict, JsonValue, ValidationError

from ai_strategy_loop.dashboard.trade_csv_models import (
    CsvIssue,
    QualityModel,
    TradeCountExpectation,
    TradeCsvQuality,
    TradeQualityResult,
)
from ai_strategy_loop.dashboard.trade_csv_quality import load_trade_quality

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


class JobSourceMetadata(QualityModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    metrics: TradeCountExpectation | None = None


def inspect_job_result_source(
    csv_path: Path | None,
    record: Mapping[str, JsonValue],
) -> TradeQualityResult:
    """Reject invalid expectations; never replace missing expectations with zero."""
    try:
        metadata = JobSourceMetadata.model_validate(record)
    except ValidationError:
        issue = CsvIssue(
            code="INVALID_SCHEMA", detail="Invalid job trade_count metadata"
        )
        return TradeQualityResult(
            None,
            (),
            TradeCsvQuality(
                status="INVALID_SCHEMA",
                issues=(issue,),
                issue_codes=(issue.code,),
                issue_count=1,
            ),
        )
    count = metadata.metrics.trade_count if metadata.metrics else None
    if csv_path is None:
        issue = CsvIssue(
            code="MISSING_ARTIFACT", detail="Job has no readable CSV artifact"
        )
        return TradeQualityResult(
            None,
            (),
            TradeCsvQuality(
                status="MISSING_ARTIFACT",
                expected_row_count=count,
                issues=(issue,),
                issue_codes=(issue.code,),
                issue_count=1,
            ),
        )
    return load_trade_quality(csv_path, expected_row_count=count)
