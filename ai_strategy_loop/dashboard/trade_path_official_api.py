"""Official-result pair and buy×sell matrix routes for QSP7."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from ai_strategy_loop.autopsy.exit_transition import compare_official_results
from ai_strategy_loop.dashboard.backtest_jobs import get_job_manager
from ai_strategy_loop.dashboard.trade_path_api_models import MatrixRequest, OfficialPairRequest, PromotionGateRequest
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


def _period(record: dict[str, object]) -> tuple[int, int] | None:
    spec = record.get("spec") if isinstance(record.get("spec"), dict) else {}
    try:
        return int(spec["start"]), int(spec["end"])
    except (KeyError, TypeError, ValueError):
        return None


@official_trade_path_router.post("/promotion-gate")
def promotion_gate(payload: PromotionGateRequest) -> dict[str, object]:
    """Adopt only when separate official design and OOS pairs both improve."""
    manager = get_job_manager()
    design = official_pair(OfficialPairRequest(
        baseline_job_id=payload.design_baseline_job_id,
        candidate_job_id=payload.design_candidate_job_id,
    ))
    oos = official_pair(OfficialPairRequest(
        baseline_job_id=payload.oos_baseline_job_id,
        candidate_job_id=payload.oos_candidate_job_id,
    ))
    blockers: list[str] = []
    if not design.get("available"):
        blockers.append("design_pair_unavailable")
    if not oos.get("available"):
        blockers.append("oos_pair_unavailable")
    design_period = _period(manager.get(payload.design_baseline_job_id, log_tail=0))
    oos_period = _period(manager.get(payload.oos_baseline_job_id, log_tail=0))
    if design_period is None or oos_period is None:
        blockers.append("period_metadata_missing")
    elif not (design_period[1] < oos_period[0] or oos_period[1] < design_period[0]):
        blockers.append("design_oos_period_overlap")
    design_delta = ((design.get("pair") or {}).get("delta_profit_krw")
                    if isinstance(design.get("pair"), dict) else None)
    oos_delta = ((oos.get("pair") or {}).get("delta_profit_krw")
                 if isinstance(oos.get("pair"), dict) else None)
    if design_delta is not None and design_delta <= 0:
        blockers.append("design_not_improved")
    if oos_delta is not None and oos_delta <= 0:
        blockers.append("oos_not_improved")
    return jsonable_encoder({
        "available": not blockers,
        "authority": "official",
        "verdict": "adoptable" if not blockers else "blocked",
        "design": design,
        "oos": oos,
        "periods": {"design": design_period, "oos": oos_period},
        "blockers": blockers,
        "rule": "설계와 비중첩 OOS 공식 pair가 모두 개선될 때만 채택 가능",
    })


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
