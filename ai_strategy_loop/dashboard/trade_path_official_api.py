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
    window = (payload.period.t_start, payload.period.t_end) if payload.period else None
    pair = compare_official_results(
        baseline_job_id=payload.baseline_job_id,
        baseline_csv=Path(baseline),
        candidate_job_id=payload.candidate_job_id,
        candidate_csv=Path(candidate),
        axis=payload.axis,
        period=window,
    )
    response = jsonable_encoder({
        "available": True, "pair": asdict(pair),
        "axis": payload.axis, "authority": "official",
        "period": ({"t_start": window[0], "t_end": window[1]} if window else None),
    })
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


def _edge_blockers(
    *, axis: str, design: dict[str, object], holdout: dict[str, object], label: str,
) -> list[str]:
    """두 구간 판정에 공통으로 쓰는 개선 요구 — 총손익 + (매수 축이면) 건당 엣지·유지율."""
    blockers: list[str] = []
    if not design.get("available"):
        blockers.append("design_pair_unavailable")
    if not holdout.get("available"):
        blockers.append(f"{label}_pair_unavailable")
    for name, payload in (("design", design), (label, holdout)):
        delta = _pair_metric(payload, "delta_profit_krw")
        if delta is not None and delta <= 0:
            blockers.append(f"{name}_not_improved")
    if axis == "buy":
        for name, payload in (("design", design), (label, holdout)):
            edge = _pair_metric(payload, "delta_per_trade_krw")
            if edge is not None and edge <= 0:
                blockers.append(f"{name}_per_trade_edge_not_improved")
            ratio = _trade_ratio(payload)
            if ratio is not None and ratio < _MIN_TRADE_RATIO:
                blockers.append(f"{name}_trade_count_collapsed")
    return blockers


def _window(period) -> tuple[int, int]:
    return (period.t_start, period.t_end)


def _disjoint(left: tuple[int, int] | None, right: tuple[int, int] | None) -> bool:
    if left is None or right is None:
        return False
    return left[1] < right[0] or right[1] < left[0]


def _promotion_gate_split(payload: PromotionGateRequest) -> dict[str, object]:
    """v2 — 연속 1회 런 한 쌍을 기간으로 갈라 판정한다(후보당 백테스트 1회).

    자본이 이어지므로 홀드아웃 총손익은 설계 구간 결과에 영향을 받는다. 그래서
    "OOS" 가 아니라 "홀드아웃"이라 부르고, 매수 축에서는 건당 엣지를 함께 요구한다.
    """
    design_window = _window(payload.design_period)
    holdout_window = _window(payload.holdout_period)
    design = official_pair(OfficialPairRequest(
        baseline_job_id=payload.baseline_job_id,
        candidate_job_id=payload.candidate_job_id,
        axis=payload.axis, period=payload.design_period,
    ))
    holdout = official_pair(OfficialPairRequest(
        baseline_job_id=payload.baseline_job_id,
        candidate_job_id=payload.candidate_job_id,
        axis=payload.axis, period=payload.holdout_period,
    ))
    whole = official_pair(OfficialPairRequest(
        baseline_job_id=payload.baseline_job_id,
        candidate_job_id=payload.candidate_job_id,
        axis=payload.axis,
    ))
    blockers = _edge_blockers(
        axis=payload.axis, design=design, holdout=holdout, label="holdout",
    )
    if not _disjoint(design_window, holdout_window):
        blockers.append("design_holdout_period_overlap")

    # 검산 — 두 구간 거래 합이 전체와 같아야 한다. 다르면 분할이 구간을 빠뜨렸거나
    # 런 범위 밖 거래가 있다는 뜻이므로 판정을 신뢰할 수 없다.
    parts = sum(
        _pair_metric(item, "baseline_trade_count") or 0.0 for item in (design, holdout)
    )
    total = _pair_metric(whole, "baseline_trade_count")
    reconciled = total is not None and abs(parts - total) < 0.5
    if not reconciled:
        blockers.append("split_does_not_reconcile")

    return jsonable_encoder({
        "available": not blockers,
        "authority": "official",
        "mode": "2job_split",
        "axis": payload.axis,
        "verdict": "adoptable" if not blockers else "blocked",
        "design": design,
        "holdout": holdout,
        "whole_run": whole,
        "periods": {"design": design_window, "holdout": holdout_window},
        "design_per_trade_delta": _pair_metric(design, "delta_per_trade_krw"),
        "holdout_per_trade_delta": _pair_metric(holdout, "delta_per_trade_krw"),
        "design_trade_ratio": _trade_ratio(design),
        "holdout_trade_ratio": _trade_ratio(holdout),
        "split_reconciled": reconciled,
        "split_trade_counts": {"parts": parts, "whole": total},
        "min_trade_ratio": _MIN_TRADE_RATIO,
        "blockers": blockers,
        "rule": (
            "연속 1회 런을 날짜로 나눠 설계·홀드아웃이 모두 개선될 때만 채택 가능"
            + (" · 매수 축은 건당 엣지 개선과 거래 유지율도 함께 요구"
               if payload.axis == "buy" else "")
        ),
        "caveat": (
            "연속 런은 자본이 이어집니다. 홀드아웃은 독립 OOS 가 아니며 "
            "총손익보다 건당 손익으로 판단하세요."
        ),
    })


@official_trade_path_router.post("/promotion-gate")
def promotion_gate(payload: PromotionGateRequest) -> dict[str, object]:
    """Adopt only when both evaluation windows improve.

    2-job 분할 모드(v2)와 기존 4-job 독립 런 모드를 모두 지원한다.
    """
    if payload.mode == "2job_split":
        return _promotion_gate_split(payload)
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
    blockers = _edge_blockers(axis=payload.axis, design=design, holdout=oos, label="oos")
    design_period = _period(manager.get(payload.design_baseline_job_id, log_tail=0))
    oos_period = _period(manager.get(payload.oos_baseline_job_id, log_tail=0))
    if design_period is None or oos_period is None:
        blockers.append("period_metadata_missing")
    elif not _disjoint(design_period, oos_period):
        blockers.append("design_oos_period_overlap")

    return jsonable_encoder({
        "available": not blockers,
        "authority": "official",
        "mode": "4job_independent",
        "axis": payload.axis,
        "verdict": "adoptable" if not blockers else "blocked",
        "design": design,
        "oos": oos,
        "periods": {"design": design_period, "oos": oos_period},
        "design_per_trade_delta": _pair_metric(design, "delta_per_trade_krw"),
        "oos_per_trade_delta": _pair_metric(oos, "delta_per_trade_krw"),
        "design_trade_ratio": _trade_ratio(design),
        "oos_trade_ratio": _trade_ratio(oos),
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
