"""Resolve governed backtest job artifacts into QSP7 source contracts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ai_strategy_loop.autopsy.trade_path_analysis import source_contract
from ai_strategy_loop.autopsy.trade_path_models import RunSource, Timeframe
from ai_strategy_loop.dashboard.backtest_jobs import get_job_manager


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class ResolvedTradePathSource:
    source: RunSource
    database_dir: Path
    code_info_db: Path


def _existing_csv(raw_path: object) -> Path | None:
    if not raw_path:
        return None
    path = Path(str(raw_path))
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return None
    return resolved if resolved.is_file() else None


def resolve_job_source(
    job_id: str, *, forced_liquidation_time: int,
) -> ResolvedTradePathSource:
    record = get_job_manager().get(job_id, log_tail=0)
    if not record.get("available"):
        raise ValueError("backtest_job_not_found")
    if record.get("status") not in ("success", "error"):
        raise ValueError("backtest_result_not_ready")
    csv_path = _existing_csv(record.get("csv_path"))
    if csv_path is None:
        raise ValueError("backtest_result_csv_missing")
    spec = record.get("spec") if isinstance(record.get("spec"), dict) else {}
    timeframe = Timeframe.TICK if spec.get("timeframe") == "tick" else Timeframe.MIN
    database_dir = Path(
        os.environ.get("STOM_TRADE_PATH_DATABASE_DIR") or REPO_ROOT / "_database"
    ).resolve()
    code_info_db = Path(
        os.environ.get("STOM_TRADE_PATH_CODE_INFO_DB") or database_dir / "code_info.db"
    ).resolve()
    source = source_contract(
        run_id=job_id,
        csv_path=csv_path,
        timeframe=timeframe,
        forced_liquidation_time=forced_liquidation_time,
        buy=str(spec.get("buy") or ""),
        sell=str(spec.get("sell") or ""),
        buy_code=str(spec.get("buy_code") or ""),
        sell_code=str(spec.get("sell_code") or ""),
    )
    return ResolvedTradePathSource(source, database_dir, code_info_db)
