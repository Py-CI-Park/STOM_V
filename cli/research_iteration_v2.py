"""Pure helpers for Wide v1 iteration loop v2 candidate generation."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy

from cli.condition_generator import candidate_to_expression


def _retention_value(candidate: dict) -> float | None:
    estimate = candidate.get('retention_estimate') or {}
    value = estimate.get('estimated_retention')
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def candidate_signature(candidate: dict) -> tuple:
    conditions = candidate.get('conditions') or []
    if len(conditions) > 1:
        return tuple(candidate_signature(condition) for condition in conditions)
    return (
        candidate.get('feature'),
        candidate.get('operator'),
        candidate.get('lower_bound'),
        candidate.get('upper_bound'),
        candidate.get('threshold'),
    )


def filter_duplicate_v2_candidates(candidates: list[dict], retention_tolerance: float = 0.02) -> list[dict]:
    selected = []
    for candidate in candidates:
        signature = candidate_signature(candidate)
        retention = _retention_value(candidate)
        duplicate = False
        for existing in selected:
            if candidate_signature(existing) != signature:
                continue
            existing_retention = _retention_value(existing)
            if retention is None or existing_retention is None:
                duplicate = True
                break
            if abs(retention - existing_retention) < retention_tolerance:
                duplicate = True
                break
        if not duplicate:
            selected.append(candidate)
    return selected


def _copy_with_type(candidate: dict, candidate_type: str) -> dict:
    item = deepcopy(candidate)
    item['v2_candidate_type'] = candidate_type
    item['expression'] = candidate_to_expression(item, runtime_context=True)
    item['conditions'] = [deepcopy(item)]
    return item


def _score_value(candidate: dict, key: str) -> float:
    return float(candidate.get(key, candidate.get('score', 0.0)) or 0.0)


def _combo_candidate(primary: dict, secondary: dict) -> dict:
    item = {
        'feature': primary.get('feature'),
        'operator': primary.get('operator'),
        'lower_bound': primary.get('lower_bound'),
        'upper_bound': primary.get('upper_bound'),
        'threshold': primary.get('threshold'),
        'score': _score_value(primary, 'score') + _score_value(secondary, 'score'),
        'combined_score': _score_value(primary, 'combined_score') + _score_value(secondary, 'combined_score'),
        'source': 'v2_combo',
        'primary_feature': primary.get('feature'),
        'secondary_feature': secondary.get('feature'),
        'retention_estimate': deepcopy(primary.get('retention_estimate') or {}),
        'retention_filter_passed': primary.get('retention_filter_passed'),
        'retention_fallback_used': primary.get('retention_fallback_used', False),
        'v2_candidate_type': 'primary_secondary_combo',
        'conditions': [deepcopy(primary), deepcopy(secondary)],
    }
    item['expression'] = ' and '.join(
        candidate_to_expression(condition, runtime_context=True)
        for condition in item['conditions']
    )
    return item


def build_v2_candidate_pool(
    analysis_candidates: list[dict],
    *,
    best_context: dict | None = None,
    primary_feature: str = 'B_시가총액',
    secondary_features: list[str] | None = None,
    include_secondary_only: bool = True,
    max_secondary_only: int = 1,
    retention_tolerance: float = 0.02,
) -> dict:
    if not best_context:
        return {
            'status': 'disabled',
            'mode': 'best_feature_mix',
            'candidates': [],
            'candidate_count': 0,
            'type_counts': {},
            'reason': 'best_context is required',
        }

    secondary_features = list(secondary_features or [])
    secondary_feature_set = set(secondary_features)
    primary_candidates = [
        item for item in analysis_candidates
        if item.get('feature') == primary_feature
    ]
    secondary_candidates = [
        item for item in analysis_candidates
        if item.get('feature') in secondary_feature_set
    ]

    candidates = []
    for candidate in primary_candidates:
        candidates.append(_copy_with_type(candidate, 'primary_variant'))

    primary_seed = primary_candidates[0] if primary_candidates else (best_context.get('source_candidate') or {})
    for secondary in secondary_candidates:
        if primary_seed:
            candidates.append(_combo_candidate(primary_seed, secondary))

    if include_secondary_only and max_secondary_only > 0:
        for candidate in secondary_candidates[:max_secondary_only]:
            candidates.append(_copy_with_type(candidate, 'secondary_only'))

    candidates = filter_duplicate_v2_candidates(candidates, retention_tolerance=retention_tolerance)
    type_counts = Counter(item.get('v2_candidate_type') for item in candidates)

    return {
        'status': 'ok',
        'mode': 'best_feature_mix',
        'primary_feature': primary_feature,
        'secondary_features': secondary_features,
        'candidates': candidates,
        'candidate_count': len(candidates),
        'type_counts': dict(type_counts),
    }
