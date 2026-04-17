"""Candidate filter generation for segment strategy research."""

from __future__ import annotations

from typing import Any


LEAKY_PREFIXES = ('S_', 'R_')
BINARY_OPERATORS = ('<', '<=', '>', '>=')


def _runtime_feature(feature: str) -> str:
    return feature[2:] if feature.startswith('B_') else feature


def _format_value(value) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f'{value:.6f}'.rstrip('0').rstrip('.')
    return repr(value)


def reject_leaky_expression(expression: str) -> bool:
    """Return True when an expression contains sell-time or result labels."""
    return any(prefix in expression for prefix in LEAKY_PREFIXES)


def condition_to_expression(condition: dict) -> str:
    """Convert a condition dict into a STOM runtime expression."""
    feature = _runtime_feature(condition['feature'])
    operator = condition['operator']
    if operator == 'between':
        return f"{_format_value(condition['lower_bound'])} <= {feature} < {_format_value(condition['upper_bound'])}"
    if operator not in BINARY_OPERATORS:
        raise ValueError(f'unsupported operator: {operator}')
    return f"{feature} {operator} {_format_value(condition['threshold'])}"


def candidate_to_expression(candidate: dict) -> str:
    """Convert all candidate conditions into an `and` expression."""
    expression = ' and '.join(condition_to_expression(condition) for condition in candidate.get('conditions', []))
    if reject_leaky_expression(expression):
        raise ValueError(f'leaky expression is not allowed: {expression}')
    return expression


def _weakness_score(row: dict) -> float:
    return abs(min(float(row.get('return_diff', 0.0) or 0.0), 0.0)) + abs(min(float(row.get('win_rate_diff', 0.0) or 0.0), 0.0))


def generate_segment_filter_candidates(
    segment_rows: list[dict],
    axis: str,
    segment_to_condition: dict,
    min_samples: int = 30,
    max_candidates: int = 10,
) -> list[dict]:
    """Generate filter candidates from weak segment rows."""
    candidates: list[dict[str, Any]] = []
    for row in segment_rows:
        count = int(row.get('count', 0) or 0)
        if count < min_samples:
            continue
        score = _weakness_score(row)
        if score <= 0:
            continue
        segment = row.get('segment')
        condition = segment_to_condition.get(segment)
        if not condition:
            continue
        candidate = {
            'level': 2,
            'source': 'segment',
            'axis': axis,
            'segment': segment,
            'conditions': [condition],
            'count': count,
            'score': score,
            'reason': 'weak_segment',
            'metrics': row,
        }
        candidate['expression'] = candidate_to_expression(candidate)
        candidates.append(candidate)
    candidates.sort(key=lambda item: float(item['score']), reverse=True)
    return candidates[:max_candidates]
