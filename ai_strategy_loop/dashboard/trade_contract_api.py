"""Read-only QSP7 artifact contract API."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_strategy_loop.dashboard.backtest_jobs import get_job_manager
from ai_strategy_loop.dashboard.trade_contract import (
    TradeArtifactContract,
    build_trade_contract_from_snapshot,
)
from ai_strategy_loop.dashboard.trade_csv_models import CsvIssue, TradeCsvQuality
from ai_strategy_loop.dashboard.trade_csv_quality import load_trade_quality


class ArtifactSpecPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    buy: str = ""
    sell: str = ""
    buy_code: str = ""
    sell_code: str = ""
    timeframe: str = "unknown"
    start_time: int | None = None
    end_time: int | None = None


class CompletedMetricsPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    trade_count: int | None = Field(default=None, ge=0, strict=True)


class CompletedJobPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    available: bool
    status: str
    csv_path: str | None = None
    spec: ArtifactSpecPayload
    metrics: CompletedMetricsPayload | None = None


class DataContractEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    available: bool
    authority: Literal["diagnostic"] = "diagnostic"
    contract: TradeArtifactContract | None = None
    reason: str = ""
    data_quality: TradeCsvQuality | None = None
    execution_status: str = "unknown"
    analysis_ready: bool = False


trade_contract_router = APIRouter(tags=["trade-path"])


@trade_contract_router.get("/data-contract", response_model=DataContractEnvelope)
def data_contract(job_id: str = "") -> DataContractEnvelope:
    """Return immutable lineage, schema availability, boundary, and cost metadata."""
    raw_record = get_job_manager().get(job_id, log_tail=0)
    try:
        record = CompletedJobPayload.model_validate(raw_record)
    except ValidationError:
        return DataContractEnvelope(available=False, reason="backtest_job_not_ready")
    if not record.available or record.status not in {"success", "error", "cancelled", "no_trades"}:
        return DataContractEnvelope(available=False, reason="backtest_job_not_ready",
                                    execution_status=record.status)
    if not record.csv_path:
        return DataContractEnvelope(
            available=False, reason="backtest_result_csv_missing",
            execution_status=record.status,
            data_quality=TradeCsvQuality(
                status="MISSING_ARTIFACT", issues=(CsvIssue(
                    code="MISSING_ARTIFACT", detail="Job has no CSV artifact path",
                ),), issue_codes=("MISSING_ARTIFACT",), issue_count=1,
            ),
        )
    expected_count = record.metrics.trade_count if record.metrics else None
    result = load_trade_quality(Path(record.csv_path), expected_row_count=expected_count)
    if result.snapshot is None:
        return DataContractEnvelope(
            available=False, reason="backtest_result_csv_unreadable",
            data_quality=result.quality, execution_status=record.status,
        )
    contract = build_trade_contract_from_snapshot(
        snapshot=result.snapshot,
        job_id=job_id,
        spec=record.spec.model_dump(),
    )
    ready = record.status == "success" and result.quality.analysis_ready
    return DataContractEnvelope(
        available=record.status == "success", contract=contract,
        data_quality=result.quality, execution_status=record.status,
        analysis_ready=ready,
        reason="" if ready else "diagnostic_only_not_analysis_ready",
    )

