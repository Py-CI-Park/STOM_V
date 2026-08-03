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


def _condition_differs(left: dict[str, object], right: dict[str, object], side: str) -> bool:
    name_key = side
    code_key = f"{side}_code"
    if left.get(name_key) != right.get(name_key):
        return True
    return bool(
        left.get(code_key) and right.get(code_key)
        and left.get(code_key) != right.get(code_key)
    )


def _pair_mismatches(
    baseline: dict[str, object], candidate: dict[str, object], axis: str = "sell",
) -> list[str]:
    """한 라운드 한 축: 바꾼 축 반대편은 반드시 같아야 한다(R2-1).

    axis="sell" 이면 매수식 고정(진입 고정 전제), axis="buy" 이면 매도식 고정.
    """
    left = baseline.get("spec") if isinstance(baseline.get("spec"), dict) else {}
    right = candidate.get("spec") if isinstance(candidate.get("spec"), dict) else {}
    mismatches: list[str] = []
    for key in ("timeframe", "start", "end"):
        if left.get(key) in (None, "") or right.get(key) in (None, "") or left.get(key) != right.get(key):
            mismatches.append(key)
    locked_side = "buy" if axis == "sell" else "sell"
    if _condition_differs(left, right, locked_side):
        mismatches.append(f"{locked_side}_condition")
    for key in ("divid_mode", "one_code", "back_db_override"):
        if left.get(key) != right.get(key):
            mismatches.append(key)
    return mismatches


@official_trade_path_router.post("/official-pair")
def official_pair(payload: OfficialPairRequest) -> dict[str, object]:
    manager = get_job_manager()
    baseline_record = manager.get(payload.baseline_job_id, log_tail=0)
    candidate_record = manager.get(payload.candidate_job_id, log_tail=0)
    mismatches = _pair_mismatches(baseline_record, candidate_record, payload.axis)
    if mismatches:
        return {
            "available": False,
            "reason": "incompatible_official_pair",
            "mismatches": mismatches,
            "axis": payload.axis,
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
        axis=payload.axis,
    )
    response = jsonable_encoder({"available": True, "pair": asdict(pair),
                                 "axis": payload.axis, "authority": "official"})
    trade_path_coordinator().add_official_pair(response)
    return response


def _period(record: dict[str, object]) -> tuple[int, int] | None:
    spec = record.get("spec") if isinstance(record.get("spec"), dict) else {}
    try:
        return int(spec["start"]), int(spec["end"])
    except (KeyError, TypeError, ValueError):
        return None


_MIN_TRADE_RATIO = 0.40  # 거래가 60% 넘게 사라지면 '개선'이 아니라 표본 붕괴로 본다.


def _pair_metric(payload: dict[str, object], key: str) -> float | None:
    pair = payload.get("pair")
    if not isinstance(pair, dict):
        return None
    value = pair.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _trade_ratio(payload: dict[str, object]) -> float | None:
    baseline = _pair_metric(payload, "baseline_trade_count")
    candidate = _pair_metric(payload, "candidate_trade_count")
    if not baseline:
        return None
    return round((candidate or 0.0) / baseline, 4)


@official_trade_path_router.post("/promotion-gate")
def promotion_gate(payload: PromotionGateRequest) -> dict[str, object]:
    """Adopt only when separate official design and OOS pairs both improve."""
    manager = get_job_manager()
    design = official_pair(OfficialPairRequest(
        baseline_job_id=payload.design_baseline_job_id,
        candidate_job_id=payload.design_candidate_job_id,
        axis=payload.axis,
    ))
    oos = official_pair(OfficialPairRequest(
        baseline_job_id=payload.oos_baseline_job_id,
        candidate_job_id=payload.oos_candidate_job_id,
        axis=payload.axis,
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

    # R2-1 — 매수 축은 진입 자체가 줄어들 수 있다. 총손익만 보면 "거래를 줄여서
    #   좋아진 것"을 개선으로 오인한다(QSP3 실측 교훈). 건당 엣지와 거래 유지율을
    #   함께 게이트에 넣는다.
    design_edge = _pair_metric(design, "delta_per_trade_krw")
    oos_edge = _pair_metric(oos, "delta_per_trade_krw")
    design_ratio = _trade_ratio(design)
    oos_ratio = _trade_ratio(oos)
    if payload.axis == "buy":
        if design_edge is not None and design_edge <= 0:
            blockers.append("design_per_trade_edge_not_improved")
        if oos_edge is not None and oos_edge <= 0:
            blockers.append("oos_per_trade_edge_not_improved")
        for label, ratio in (("design", design_ratio), ("oos", oos_ratio)):
            if ratio is not None and ratio < _MIN_TRADE_RATIO:
                blockers.append(f"{label}_trade_count_collapsed")

    return jsonable_encoder({
        "available": not blockers,
        "authority": "official",
        "axis": payload.axis,
        "verdict": "adoptable" if not blockers else "blocked",
        "design": design,
        "oos": oos,
        "periods": {"design": design_period, "oos": oos_period},
        "design_per_trade_delta": design_edge,
        "oos_per_trade_delta": oos_edge,
        "design_trade_ratio": design_ratio,
        "oos_trade_ratio": oos_ratio,
        "min_trade_ratio": _MIN_TRADE_RATIO,
        "blockers": blockers,
        "rule": (
            "설계와 비중첩 OOS 공식 pair가 모두 개선될 때만 채택 가능"
            + (" · 매수 축은 건당 엣지 개선과 거래 유지율도 함께 요구"
               if payload.axis == "buy" else "")
        ),
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
