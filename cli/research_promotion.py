"""Promotion gates and scoring for segment research candidates."""

from __future__ import annotations


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


def _delta(candidate: dict, baseline: dict, key: str) -> float:
    return float(candidate.get(key, 0.0) or 0.0) - float(baseline.get(key, 0.0) or 0.0)


def evaluate_research_candidate(comparison: dict, gates: dict | None = None, weights: dict | None = None) -> dict:
    """Evaluate mandatory gates and weighted score for a candidate comparison."""
    gates = {**BALANCED_GATES, **(gates or {})}
    weights = {**BALANCED_WEIGHTS, **(weights or {})}
    baseline = comparison.get('baseline_summary') or {}
    candidate = comparison.get('candidate_summary') or {}
    excluded = comparison.get('excluded_summary') or {}
    reasons = []

    trade_count = int(candidate.get('trade_count', 0) or 0)
    if trade_count < gates['min_trade_count']:
        reasons.append(f"trade_count<{gates['min_trade_count']}")

    retention = float(comparison.get('trade_count_retention', 0.0) or 0.0)
    if retention < gates['min_trade_count_retention']:
        reasons.append(f"trade_count_retention<{gates['min_trade_count_retention']}")
    if retention > gates['max_trade_count_retention']:
        reasons.append(f"trade_count_retention>{gates['max_trade_count_retention']}")

    date_concentration = float(candidate.get('date_concentration', 0.0) or 0.0)
    if date_concentration > gates['max_date_concentration']:
        reasons.append(f"date_concentration>{gates['max_date_concentration']}")

    symbol_concentration = float(candidate.get('symbol_concentration', 0.0) or 0.0)
    if symbol_concentration > gates['max_symbol_concentration']:
        reasons.append(f"symbol_concentration>{gates['max_symbol_concentration']}")

    avg_return_delta = _delta(candidate, baseline, 'avg_return')
    win_rate_delta = _delta(candidate, baseline, 'win_rate')
    avg_mae_delta = _delta(candidate, baseline, 'avg_mae')
    total_profit_delta = _delta(candidate, baseline, 'total_profit')
    excluded_quality = abs(min(float(excluded.get('avg_return', 0.0) or 0.0), 0.0))
    score = (
        avg_return_delta * weights['avg_return_delta']
        + win_rate_delta * weights['win_rate_delta']
        + avg_mae_delta * weights['avg_mae_delta']
        + (total_profit_delta / 10_000.0) * weights['total_profit_delta']
        + excluded_quality * weights['excluded_quality']
    )
    return {
        'status': 'ok',
        'passed': len(reasons) == 0 and score > 0,
        'reasons': reasons if reasons else ([] if score > 0 else ['score<=0']),
        'score': float(score),
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
