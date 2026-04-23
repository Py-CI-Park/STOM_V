"""Pure helpers for Wide v1 iteration loop v3 candidate generation."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re

from cli.condition_generator import candidate_to_expression
from cli.research_iteration_v2 import (
    candidate_from_expression,
    candidate_signature,
    filter_duplicate_v2_candidates,
)


def parse_best_expression_conditions(
    expression: str,
    *,
    primary_feature: str,
    trade_amount_feature: str,
) -> list[dict]:
    parts = [part.strip() for part in re.split(r'\s+and\s+', expression.strip())]
    if len(parts) != 2 or any(not part for part in parts):
        raise ValueError('best expression must contain exactly two conditions joined by "and"')

    parsed_by_feature = {}
    for part in parts:
        for feature in (primary_feature, trade_amount_feature):
            try:
                parsed = candidate_from_expression(part, feature=feature)
            except ValueError:
                continue
            parsed_by_feature[feature] = parsed
            break
        else:
            raise ValueError(f'unsupported best expression condition: {part}')

    missing = [
        feature for feature in (primary_feature, trade_amount_feature)
        if feature not in parsed_by_feature
    ]
    if missing:
        raise ValueError(f'best expression missing expected feature: {missing[0]}')

    return [parsed_by_feature[primary_feature], parsed_by_feature[trade_amount_feature]]


def _score_value(candidate: dict, key: str) -> float:
    return float(candidate.get(key, candidate.get('score', 0.0)) or 0.0)


def _candidate_expression(candidate: dict) -> str:
    if candidate.get('source') != 'best_context' and candidate.get('expression'):
        return candidate['expression']
    return candidate_to_expression(candidate, runtime_context=True)


def _combo_candidate(
    conditions: list[dict],
    *,
    candidate_type: str,
    source_candidate: dict,
    primary_feature: str,
    trade_amount_feature: str,
    secondary_feature: str | None = None,
) -> dict:
    item = {
        'feature': source_candidate.get('feature'),
        'operator': source_candidate.get('operator'),
        'lower_bound': source_candidate.get('lower_bound'),
        'upper_bound': source_candidate.get('upper_bound'),
        'threshold': source_candidate.get('threshold'),
        'score': sum(_score_value(condition, 'score') for condition in conditions),
        'combined_score': sum(_score_value(condition, 'combined_score') for condition in conditions),
        'source': 'v3_candidate_pool',
        'primary_feature': primary_feature,
        'trade_amount_feature': trade_amount_feature,
        'secondary_feature': secondary_feature,
        'retention_estimate': deepcopy(source_candidate.get('retention_estimate') or {}),
        'retention_filter_passed': source_candidate.get('retention_filter_passed'),
        'retention_fallback_used': source_candidate.get('retention_fallback_used', False),
        'v3_candidate_type': candidate_type,
        'conditions': [deepcopy(condition) for condition in conditions],
    }
    item['expression'] = ' and '.join(_candidate_expression(condition) for condition in item['conditions'])
    return item


def _dedupe_v3_candidates(candidates: list[dict], *, retention_tolerance: float) -> list[dict]:
    ranked = sorted(
        candidates,
        key=lambda item: (
            item.get('v3_candidate_type') or '',
            _score_value(item, 'combined_score'),
        ),
        reverse=True,
    )
    signature_deduped = filter_duplicate_v2_candidates(
        ranked,
        retention_tolerance=retention_tolerance,
    )

    selected = []
    seen = set()
    for candidate in signature_deduped:
        key = (candidate.get('v3_candidate_type'), candidate.get('expression'), candidate_signature(candidate))
        if key in seen:
            continue
        seen.add(key)
        selected.append(candidate)

    return sorted(
        selected,
        key=lambda item: (
            item.get('v3_candidate_type') or '',
            _score_value(item, 'combined_score'),
        ),
    )


def _control_candidate(best_context: dict) -> dict:
    return {
        'v3_candidate_type': 'v3_control_keep_best',
        'strategy_name': best_context.get('strategy_name'),
        'expression': best_context.get('expression'),
        'reference_adjusted_score': best_context.get('reference_adjusted_score'),
        'skip_backtest': True,
    }


def build_v3_candidate_pool(
    analysis_candidates: list[dict],
    *,
    best_context: dict | None = None,
    primary_feature: str = 'B_시가총액',
    trade_amount_feature: str = 'B_당일거래대금',
    secondary_features: list[str] | None = None,
    min_estimated_retention: float | None = 0.4,
    retention_tolerance: float = 0.02,
) -> dict:
    if not best_context:
        return {
            'status': 'disabled',
            'mode': 'best_feature_mix_v3',
            'primary_feature': primary_feature,
            'trade_amount_feature': trade_amount_feature,
            'secondary_features': list(secondary_features or []),
            'control_candidate': None,
            'candidates': [],
            'candidate_count': 0,
            'type_counts': {},
            'reason': 'best_context is required',
        }

    best_conditions = parse_best_expression_conditions(
        best_context.get('expression', ''),
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
    )
    best_primary, best_trade_amount = best_conditions
    secondary_features = list(secondary_features or [])
    secondary_feature_set = set(secondary_features) - {primary_feature, trade_amount_feature}

    eligible_candidates = [deepcopy(candidate) for candidate in analysis_candidates]
    secondary_candidates = [
        candidate for candidate in eligible_candidates
        if candidate.get('feature') in secondary_feature_set
    ]
    trade_amount_candidates = [
        candidate for candidate in eligible_candidates
        if candidate.get('feature') == trade_amount_feature
        and candidate_signature(candidate) != candidate_signature(best_trade_amount)
    ]

    candidates = []
    for secondary in secondary_candidates:
        candidates.append(_combo_candidate(
            [best_primary, best_trade_amount, secondary],
            candidate_type='v3_tighten_secondary',
            source_candidate=secondary,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
            secondary_feature=secondary.get('feature'),
        ))
        candidates.append(_combo_candidate(
            [best_primary, secondary],
            candidate_type='v3_replace_secondary',
            source_candidate=secondary,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
            secondary_feature=secondary.get('feature'),
        ))

    for trade_amount in trade_amount_candidates:
        candidates.append(_combo_candidate(
            [best_primary, trade_amount],
            candidate_type='v3_repair_trade_amount',
            source_candidate=trade_amount,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
        ))

    candidates = _dedupe_v3_candidates(
        candidates,
        retention_tolerance=retention_tolerance,
    )
    type_counts = Counter(item.get('v3_candidate_type') for item in candidates)
    type_counts['v3_control_keep_best'] += 1

    return {
        'status': 'ok',
        'mode': 'best_feature_mix_v3',
        'primary_feature': primary_feature,
        'trade_amount_feature': trade_amount_feature,
        'secondary_features': secondary_features,
        'best_conditions': best_conditions,
        'control_candidate': _control_candidate(best_context),
        'candidates': candidates,
        'candidate_count': len(candidates),
        'type_counts': dict(type_counts),
    }
