"""Promotion gates and scoring for segment research candidates."""

from __future__ import annotations

import math


BALANCED_GATES = {
    'min_trade_count': 20,
    'min_trade_count_retention': 0.40,
    'max_trade_count_retention': 2.00,
    'max_date_concentration': 0.50,
    'max_symbol_concentration': 0.50,
}

BALANCED_WEIGHTS = {
    'avg_return_delta': 0.35,
    'win_rate_delta': 0.20,
    'avg_mae_delta': 0.20,
    'total_profit_delta': 0.15,
    'excluded_quality': 0.10,
}


TRADE_COUNT_RETENTION_SEMANTICS = 'candidate_trade_count / baseline_trade_count'


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _coerce_finite(value, reason: str, reasons: list[str], default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        _add_reason(reasons, reason)
        return default
    if not math.isfinite(number):
        _add_reason(reasons, reason)
        return default
    return number


def _summary(comparison: dict, key: str, reason: str, reasons: list[str]) -> dict:
    summary = comparison.get(key)
    if not isinstance(summary, dict) or not summary:
        _add_reason(reasons, reason)
        return {}
    return summary


def _delta(candidate: dict, baseline: dict, key: str, reason: str, reasons: list[str]) -> float:
    candidate_value = _coerce_finite(candidate.get(key), reason, reasons)
    baseline_value = _coerce_finite(baseline.get(key), reason, reasons)
    return candidate_value - baseline_value


def evaluate_research_candidate(comparison: dict, gates: dict | None = None, weights: dict | None = None) -> dict:
    """Evaluate mandatory gates and weighted score for a candidate comparison."""
    gates = {**BALANCED_GATES, **(gates or {})}
    weights = {**BALANCED_WEIGHTS, **(weights or {})}
    reasons = []
    baseline = _summary(comparison, 'baseline_summary', 'missing_baseline_summary', reasons)
    candidate = _summary(comparison, 'candidate_summary', 'missing_candidate_summary', reasons)
    excluded = comparison.get('excluded_summary')
    if not isinstance(excluded, dict) or 'avg_return' not in excluded:
        _add_reason(reasons, 'invalid_excluded_quality')
        excluded = {}

    trade_count = int(_coerce_finite(candidate.get('trade_count'), 'invalid_trade_count', reasons))
    if trade_count < gates['min_trade_count']:
        _add_reason(reasons, f"trade_count<{gates['min_trade_count']}")

    retention = _coerce_finite(
        comparison.get('trade_count_retention'),
        'invalid_trade_count_retention',
        reasons,
    )
    if retention < gates['min_trade_count_retention']:
        _add_reason(reasons, f"trade_count_retention<{gates['min_trade_count_retention']}")
    if retention > gates['max_trade_count_retention']:
        _add_reason(reasons, f"trade_count_retention>{gates['max_trade_count_retention']}")

    date_concentration = _coerce_finite(
        candidate.get('date_concentration'),
        'invalid_date_concentration',
        reasons,
    )
    if date_concentration > gates['max_date_concentration']:
        _add_reason(reasons, f"date_concentration>{gates['max_date_concentration']}")

    symbol_concentration = _coerce_finite(
        candidate.get('symbol_concentration'),
        'invalid_symbol_concentration',
        reasons,
    )
    if symbol_concentration > gates['max_symbol_concentration']:
        _add_reason(reasons, f"symbol_concentration>{gates['max_symbol_concentration']}")

    avg_return_delta = _delta(candidate, baseline, 'avg_return', 'invalid_avg_return_delta', reasons)
    win_rate_delta = _delta(candidate, baseline, 'win_rate', 'invalid_win_rate_delta', reasons)
    avg_mae_delta = _delta(candidate, baseline, 'avg_mae', 'invalid_avg_mae_delta', reasons)
    total_profit_delta = _delta(candidate, baseline, 'total_profit', 'invalid_total_profit_delta', reasons)
    excluded_avg_return = _coerce_finite(
        excluded.get('avg_return', 0.0),
        'invalid_excluded_quality',
        reasons,
    )
    excluded_quality = abs(min(excluded_avg_return, 0.0))
    score = (
        avg_return_delta * weights['avg_return_delta']
        + win_rate_delta * weights['win_rate_delta']
        + avg_mae_delta * weights['avg_mae_delta']
        + (total_profit_delta / 10_000.0) * weights['total_profit_delta']
        + excluded_quality * weights['excluded_quality']
    )
    if not math.isfinite(score):
        _add_reason(reasons, 'invalid_score')
        score = 0.0
    if score <= 0 and 'score<=0' not in reasons:
        _add_reason(reasons, 'score<=0')

    return {
        'status': 'ok',
        'passed': len(reasons) == 0 and score > 0,
        'reasons': reasons,
        'score': float(score),
        'trade_count_retention_semantics': TRADE_COUNT_RETENTION_SEMANTICS,
        'gates': gates,
        'weights': weights,
        'deltas': {
            'avg_return_delta': avg_return_delta,
            'win_rate_delta': win_rate_delta,
            'avg_mae_delta': avg_mae_delta,
            'total_profit_delta': total_profit_delta,
            'excluded_quality': excluded_quality,
        },
    }
