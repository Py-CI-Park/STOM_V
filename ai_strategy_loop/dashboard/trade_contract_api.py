"""Read-only QSP7 artifact contract API."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, ValidationError

from ai_strategy_loop.dashboard.backtest_jobs import get_job_manager
from ai_strategy_loop.dashboard.trade_contract import (
    TradeArtifactContract,
    build_trade_artifact_contract,
)


class ArtifactSpecPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    buy: str = ""
    sell: str = ""
    buy_code: str = ""
    sell_code: str = ""
    timeframe: str = "unknown"
    start_time: int | None = None
    end_time: int | None = None


class CompletedJobPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    available: bool
    status: str
    csv_path: str
    spec: ArtifactSpecPayload


class DataContractEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    available: bool
    authority: Literal["diagnostic"] = "diagnostic"
    contract: TradeArtifactContract | None = None
    reason: str = ""


trade_contract_router = APIRouter(tags=["trade-path"])


@trade_contract_router.get("/data-contract", response_model=DataContractEnvelope)
def data_contract(job_id: str = "") -> DataContractEnvelope:
    """Return immutable lineage, schema availability, boundary, and cost metadata."""
    raw_record = get_job_manager().get(job_id, log_tail=0)
    try:
        record = CompletedJobPayload.model_validate(raw_record)
    except ValidationError:
        return DataContractEnvelope(available=False, reason="backtest_job_not_ready")
    if not record.available or record.status != "success":
        return DataContractEnvelope(available=False, reason="backtest_job_not_ready")
    try:
        csv_path = Path(record.csv_path).resolve(strict=True)
    except OSError:
        return DataContractEnvelope(available=False, reason="backtest_result_csv_missing")
    if not csv_path.is_file():
        return DataContractEnvelope(available=False, reason="backtest_result_csv_missing")
    contract = build_trade_artifact_contract(
        csv_path=csv_path,
        job_id=job_id,
        spec=record.spec.model_dump(),
    )
    return DataContractEnvelope(available=True, contract=contract)

