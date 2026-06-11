"""TMAP G5 — 포트폴리오 합성기: 저상관 후보 결합(일별손익 합산 근사).

'시간·횟수 확대'의 실제 메커니즘(2026-06-11 재설계 §2): 단일 만능 조건식이 아니라
저상관 니치들의 합산 — 거래수·시간 커버 ↑, MDD%는 분모 효과로 ↓(B2 감사).

1차 근사: 후보들의 일별 손익을 합산해 결합 손익·결합 MDD(낙폭금액)를 계산한다
(백테 0회 — 동시보유 자본 제약은 무시되므로 낙관 편향이 있다 → 채택 조합만
실백테로 확인하는 것이 계약). 분석/advisory 전용.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from ai_strategy_loop.fitness.overfit_stats import align_daily_matrix


def combined_metrics(series_list: Sequence[Dict[str, float]]) -> Optional[Dict[str, float]]:
    """일별 손익 dict들을 합산해 {profit, mdd_amount, n_days, score}를 계산한다."""
    if not series_list:
        return None
    merged: Dict[str, float] = {}
    for s in series_list:
        for day, v in s.items():
            merged[day] = merged.get(day, 0.0) + float(v)
    if not merged:
        return None
    days = sorted(merged)
    daily = np.array([merged[d] for d in days], dtype=float)
    cum = np.cumsum(daily)
    peak = np.maximum.accumulate(cum)
    mdd_amount = float(np.max(peak - cum)) if cum.size else 0.0
    profit = float(cum[-1])
    return {
        "profit": profit,
        "mdd_amount": mdd_amount,
        "n_days": int(daily.size),
        "score": profit / max(mdd_amount, 1.0),
    }


def _corr(a: Dict[str, float], b: Dict[str, float]) -> float:
    _days, _labels, matrix = align_daily_matrix({"a": a, "b": b})
    if matrix.shape[0] < 5:
        return 0.0
    with np.errstate(invalid="ignore"):
        c = np.corrcoef(matrix.T)
    v = float(c[0, 1])
    return 0.0 if np.isnan(v) else v


def greedy_portfolio(
    series_by_label: Dict[str, Dict[str, float]],
    *,
    max_size: int = 4,
    corr_cap: float = 0.5,
    require_positive: bool = True,
) -> Dict[str, Any]:
    """탐욕적 저상관 결합: score(=profit/MDD금액) 최대 후보부터 시작해,
    기존 결합과의 상관이 corr_cap 미만이면서 결합 score를 가장 올리는 후보를 추가한다.

    Returns:
        {"selection": [label...], "steps": [...], "combined": {...}} — 후보 부족/전부
        부적격이면 selection이 비거나 1개일 수 있다(graceful).
    """
    candidates = {
        k: v for k, v in series_by_label.items()
        if v and (not require_positive or sum(v.values()) > 0)
    }
    out: Dict[str, Any] = {"selection": [], "steps": [], "combined": None,
                           "corr_cap": corr_cap, "max_size": max_size}
    if not candidates:
        return out

    scored = {k: combined_metrics([v]) for k, v in candidates.items()}
    first = max(scored, key=lambda k: scored[k]["score"])
    selection = [first]
    combined_series = dict(candidates[first])
    out["steps"].append({"added": first, **scored[first], "corr_to_combo": None})

    while len(selection) < max_size:
        best_label, best_metrics, best_corr = None, None, None
        current = combined_metrics([combined_series])
        for label, series in candidates.items():
            if label in selection:
                continue
            corr = _corr(combined_series, series)
            if corr >= corr_cap:
                continue
            trial = combined_metrics([combined_series, series])
            if trial is None:
                continue
            if best_metrics is None or trial["score"] > best_metrics["score"]:
                best_label, best_metrics, best_corr = label, trial, corr
        if best_label is None or (current and best_metrics["score"] <= current["score"]):
            break  # 더 나아지지 않으면 멈춘다(score 단조 증가 계약).
        selection.append(best_label)
        for day, v in candidates[best_label].items():
            combined_series[day] = combined_series.get(day, 0.0) + float(v)
        out["steps"].append({"added": best_label, **best_metrics,
                             "corr_to_combo": round(float(best_corr), 4)})

    out["selection"] = selection
    out["combined"] = combined_metrics([combined_series])
    out["note"] = (
        "일별손익 합산 근사(동시보유 자본 제약 무시 — 낙관 편향). "
        "채택 조합은 실백테로 확인할 것."
    )
    return out
