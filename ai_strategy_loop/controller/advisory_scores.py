"""Advisory 0-100 scores for condition-discovery dashboards.

These helpers explain and rank candidates only. They never mutate gate state,
select winners, export strategies, or approve promotion.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Mapping, Optional

from ai_strategy_loop.controller.condition_discovery import build_evidence_health


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if not math.isfinite(value):
        return lo
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _finite_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _num(data: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in data and data[key] is not None:
            number = _finite_float(data[key])
            if number is not None:
                return number
    return default


def _has_finite_number(data: Mapping[str, Any], key: str) -> bool:
    return key in data and data[key] is not None and _finite_float(data[key]) is not None


def _bool(data: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = data.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _component(name: str, points: float, max_points: float, reason: str) -> Dict[str, Any]:
    bounded = round(_clamp(points / max_points if max_points else 0.0) * max_points, 2)
    return {
        "name": name,
        "points": bounded,
        "max_points": max_points,
        "reason": reason,
    }


def _score_payload(kind: str, components: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(components)
    score = round(sum(float(row["points"]) for row in rows), 2)
    return {
        "kind": kind,
        "score": round(_clamp(score, 0.0, 100.0), 2),
        "scale": "0-100",
        "authority": "advisory_only",
        "can_promote": False,
        "can_export": False,
        "can_select_winner": False,
        "reasons": rows,
    }


def compute_performance_score_100(
    metrics: Optional[Mapping[str, Any]],
    *,
    mdd_cap: float = 25.0,
    min_daily_trades: float = 0.5,
    profit_target_krw: float = 10_000_000.0,
    calmar_norm: float = 30.0,
    payoff_target: float = 1.3,
) -> Dict[str, Any]:
    """Return a reasoned advisory performance score.

    The formula mirrors the requested dashboard explanation buckets and is bounded
    to 0-100. It is intentionally separate from hard gates and winner selection.
    """

    data = dict(metrics or {})
    profit = _num(data, "total_profit_krw", "total_profit", "profit")
    mdd = abs(_num(data, "mdd_pct", "mdd"))
    cagr = _num(data, "cagr", "cagr_pct")
    calmar = _num(data, "calmar", default=(cagr / mdd if mdd > 1e-9 else (calmar_norm if cagr > 0 else 0.0)))
    uptrend = _clamp(_num(data, "uptrend_r2", "r2"))
    daily = _num(data, "daily_avg_trades")
    trade_count = _num(data, "trade_count")
    payoff = _num(data, "payoff_ratio")
    tpi = _num(data, "tpi")
    give_back_present = _has_finite_number(data, "give_back_rate")
    give_back = _num(data, "give_back_rate")
    stability_value = _clamp(_num(data, "multiyear_stability_term", "yearly_positive_ratio"))

    profit_ratio = 0.0 if profit <= 0 else _clamp(math.log1p(profit) / math.log1p(max(profit_target_krw, 1.0)))
    mdd_ratio = 0.0 if mdd_cap <= 0 else _clamp(1.0 - (mdd / mdd_cap))
    calmar_ratio = _clamp(calmar / max(calmar_norm, 1e-9))
    if daily > 0:
        trade_ratio = _clamp(daily / max(min_daily_trades, 1e-9))
        trade_reason = f"daily_avg_trades={daily:.4g} target={min_daily_trades:.4g}"
    else:
        trade_ratio = _clamp(trade_count / 30.0)
        trade_reason = f"daily_avg_trades missing; trade_count fallback={trade_count:.0f}/30"

    payoff_ratio = _clamp((payoff - 1.0) / max(payoff_target - 1.0, 1e-9)) if payoff else 0.0
    tpi_ratio = _clamp(tpi / 1.2) if tpi else 0.0
    give_back_ratio = (1.0 - _clamp(give_back)) if give_back_present else 0.0
    exit_ratio = (payoff_ratio * 0.45) + (tpi_ratio * 0.25) + (give_back_ratio * 0.30)

    return _score_payload(
        "performance_score_100",
        [
            _component("profit", 20.0 * profit_ratio, 20.0, f"profit={profit:.0f} target={profit_target_krw:.0f}"),
            _component("mdd", 20.0 * mdd_ratio, 20.0, f"mdd={mdd:.4g}% cap={mdd_cap:.4g}%"),
            _component("calmar", 15.0 * calmar_ratio, 15.0, f"calmar={calmar:.4g} norm={calmar_norm:.4g}"),
            _component("uptrend_r2", 15.0 * uptrend, 15.0, f"uptrend_r2={uptrend:.4g}"),
            _component("trade_frequency", 10.0 * trade_ratio, 10.0, trade_reason),
            _component("exit_quality", 10.0 * exit_ratio, 10.0, f"payoff={payoff:.4g}, tpi={tpi:.4g}, give_back={give_back:.4g}"),
            _component("multi_period_stability", 10.0 * stability_value, 10.0, f"stability={stability_value:.4g}"),
        ],
    )


def _count(items: Any) -> int:
    if items is None:
        return 0
    if isinstance(items, str):
        return 1 if items.strip() else 0
    try:
        return len(list(items))
    except TypeError:
        return 0


def compute_condition_quality_score_100(features: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Return a reasoned advisory generation-quality score.

    ``features`` is deliberately generic so later prompt/static analyzers can publish
    whatever they know without forcing a breaking contract.
    """

    data = dict(features or {})
    syntax_valid = _bool(data, "syntax_valid", True)
    forbidden_count = int(_num(data, "forbidden_token_count", "forbidden_count"))
    categories = _count(data.get("variable_categories"))
    patterns = _count(data.get("composition_patterns", data.get("pattern_cards")))
    always_true = _count(data.get("always_true_flags"))
    cost_risk = str(data.get("execution_cost_risk", "low")).lower()
    window_calls = _num(data, "window_call_count", default=0.0)
    max_window_calls = max(_num(data, "max_window_calls", default=8.0), 1.0)
    exit_structure = data.get("exit_structure") if isinstance(data.get("exit_structure"), Mapping) else {}

    syntax_ratio = 1.0 if syntax_valid and forbidden_count == 0 else 0.0
    diversity_ratio = _clamp(categories / 5.0)
    niche_ratio = 1.0 if str(data.get("market_niche", "")).strip() else 0.0
    creativity_ratio = _clamp(patterns / 3.0)
    overfire_ratio = 1.0 if always_true == 0 and not _bool(data, "overfire_risk", False) else 0.0
    cost_ratio = 0.0 if cost_risk in {"high", "critical"} else _clamp(1.0 - (window_calls / (max_window_calls * 2.0)))
    exit_bits = sum(1 for key in ("stop_loss", "trailing", "time_exit", "momentum_fade") if _bool(exit_structure, key))
    exit_ratio = _clamp(exit_bits / 3.0)

    return _score_payload(
        "condition_quality_score_100",
        [
            _component("syntax_safety", 15.0 * syntax_ratio, 15.0, f"syntax_valid={syntax_valid}, forbidden_count={forbidden_count}"),
            _component("variable_diversity", 15.0 * diversity_ratio, 15.0, f"variable_categories={categories}/5"),
            _component("market_niche", 15.0 * niche_ratio, 15.0, "market niche declared" if niche_ratio else "market niche missing"),
            _component("composition_creativity", 20.0 * creativity_ratio, 20.0, f"composition_patterns={patterns}/3"),
            _component("overfire_guard", 10.0 * overfire_ratio, 10.0, f"always_true_flags={always_true}, overfire_risk={_bool(data, 'overfire_risk', False)}"),
            _component("execution_cost", 10.0 * cost_ratio, 10.0, f"execution_cost_risk={cost_risk}, window_calls={window_calls:.0f}/{max_window_calls:.0f}"),
            _component("exit_structure", 15.0 * exit_ratio, 15.0, f"exit_structure_bits={exit_bits}/3"),
        ],
    )


def build_authority_guard(
    *,
    evidence: Optional[Mapping[str, Any]],
    preset: str,
    hard_gate_passed: bool = False,
    human_approved: bool = False,
) -> Dict[str, Any]:
    """Document that advisory scores cannot grant promotion/export authority."""

    evidence_health = build_evidence_health(evidence, preset=preset)
    blockers = list(evidence_health["blockers"])
    if not hard_gate_passed:
        blockers.append("hard_gate_not_passed")
    if not human_approved:
        blockers.append("human_approval_required")
    review_ready = not blockers
    return {
        "score_can_promote": False,
        "score_can_export": False,
        "score_can_select_winner": False,
        "promotion_review_ready": review_ready,
        "export_allowed": False,
        "winner_authority": False,
        "blocked_by": blockers,
        "evidence_health": evidence_health,
        "authority": "scores_are_advisory_hard_gates_evidence_and_human_approval_are_authoritative",
    }


def build_advisory_score_payload(
    *,
    metrics: Optional[Mapping[str, Any]],
    quality_features: Optional[Mapping[str, Any]],
    evidence: Optional[Mapping[str, Any]],
    preset: str,
    hard_gate_passed: bool = False,
    human_approved: bool = False,
    mdd_cap: float = 25.0,
    min_daily_trades: float = 0.5,
) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "performance_score_100": compute_performance_score_100(
            metrics,
            mdd_cap=mdd_cap,
            min_daily_trades=min_daily_trades,
        ),
        "condition_quality_score_100": compute_condition_quality_score_100(quality_features),
        "authority_guard": build_authority_guard(
            evidence=evidence,
            preset=preset,
            hard_gate_passed=hard_gate_passed,
            human_approved=human_approved,
        ),
    }


__all__ = [
    "build_advisory_score_payload",
    "build_authority_guard",
    "compute_condition_quality_score_100",
    "compute_performance_score_100",
]
