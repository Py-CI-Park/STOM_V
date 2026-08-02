"""Official-result pair and buy×sell matrix routes for QSP7."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from ai_strategy_loop.autopsy.exit_transition import compare_official_results
from ai_strategy_loop.dashboard.backtest_jobs import get_job_manager
from ai_strategy_loop.dashboard.trade_path_api_models import MatrixRequest, OfficialPairRequest
from ai_strategy_loop.dashboard.trade_path_jobs import trade_path_coordinator


official_trade_path_router = APIRouter()


def _pair_mismatches(baseline: dict[str, object], candidate: dict[str, object]) -> list[str]:
    left = baseline.get("spec") if isinstance(baseline.get("spec"), dict) else {}
    right = candidate.get("spec") if isinstance(candidate.get("spec"), dict) else {}
    mismatches: list[str] = []
    for key in ("timeframe", "start", "end"):
        if left.get(key) in (None, "") or right.get(key) in (None, "") or left.get(key) != right.get(key):
            mismatches.append(key)
    if left.get("buy") != right.get("buy") or (
        left.get("buy_code") and right.get("buy_code")
        and left.get("buy_code") != right.get("buy_code")
    ):
        mismatches.append("buy_condition")
    for key in ("divid_mode", "one_code", "back_db_override"):
        if left.get(key) != right.get(key):
            mismatches.append(key)
    return mismatches


@official_trade_path_router.post("/official-pair")
def official_pair(payload: OfficialPairRequest) -> dict[str, object]:
    manager = get_job_manager()
    baseline_record = manager.get(payload.baseline_job_id, log_tail=0)
    candidate_record = manager.get(payload.candidate_job_id, log_tail=0)
    mismatches = _pair_mismatches(baseline_record, candidate_record)
    if mismatches:
        return {
            "available": False,
            "reason": "incompatible_official_pair",
            "mismatches": mismatches,
            "authority": "official",
        }
    baseline = manager.result_csv_path(payload.baseline_job_id)
    candidate = manager.result_csv_path(payload.candidate_job_id)
    if not baseline or not candidate or not Path(baseline).is_file() or not Path(candidate).is_file():
        return {"available": False, "reason": "official_result_missing"}
    pair = compare_official_results(
        baseline_job_id=payload.baseline_job_id,
        baseline_csv=Path(baseline),
        candidate_job_id=payload.candidate_job_id,
        candidate_csv=Path(candidate),
    )
    response = jsonable_encoder({"available": True, "pair": asdict(pair), "authority": "official"})
    trade_path_coordinator().add_official_pair(response)
    return response


@official_trade_path_router.post("/matrix")
def official_matrix(payload: MatrixRequest) -> dict[str, object]:
    manager = get_job_manager()
    cells: list[dict[str, object]] = []
    for cell in payload.cells:
        record = manager.get(cell.job_id, log_tail=0)
        metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
        cells.append({
            "job_id": cell.job_id,
            "buy": cell.buy,
            "sell": cell.sell,
            "status": record.get("status", "missing"),
            "metrics": metrics,
        })
    return {
        "available": True,
        "authority": "official",
        "cells": cells,
        "note": "각 셀은 공식 엔진 job 결과이며 미실행 조합은 자동 추정하지 않습니다.",
    }
