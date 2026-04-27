"""Recovery candidate pool helpers for Wide v2 v5 runs."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, TypeAlias

from cli.condition_generator import candidate_to_expression
from cli.research_iteration_v2 import candidate_signature
from cli.research_iteration_v3 import parse_best_expression_conditions

JsonDict: TypeAlias = dict[str, Any]


def _score_value(candidate: JsonDict, key: str) -> float:
    try:
        return float(candidate.get(key, candidate.get('score', 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _candidate_expression(candidate: JsonDict) -> str:
    if candidate.get('source') != 'best_context' and candidate.get('expression'):
        return str(candidate['expression'])
    return candidate_to_expression(candidate, runtime_context=True)


def _with_original_indexes(candidates: list[JsonDict]) -> list[JsonDict]:
    indexed: list[JsonDict] = []
    for index, candidate in enumerate(candidates):
        item = deepcopy(candidate)
        item.setdefault('original_index', index)
        indexed.append(item)
    return indexed


def _combo_candidate(
    conditions: list[JsonDict],
    *,
    v4_candidate_type: str,
    v5_candidate_source: str,
    source_candidate: JsonDict,
    primary_feature: str,
    trade_amount_feature: str,
    secondary_feature: str | None = None,
) -> JsonDict:
    item: JsonDict = {
        'feature': source_candidate.get('feature'),
        'operator': source_candidate.get('operator'),
        'lower_bound': source_candidate.get('lower_bound'),
        'upper_bound': source_candidate.get('upper_bound'),
        'threshold': source_candidate.get('threshold'),
        'score': sum(_score_value(condition, 'score') for condition in conditions),
        'combined_score': sum(_score_value(condition, 'combined_score') for condition in conditions),
        'source': 'v5_recovery_pool',
        'primary_feature': primary_feature,
        'trade_amount_feature': trade_amount_feature,
        'secondary_feature': secondary_feature,
        'v4_candidate_type': v4_candidate_type,
        'v5_candidate_source': v5_candidate_source,
        'conditions': [deepcopy(condition) for condition in conditions],
        'retention_estimate': deepcopy(source_candidate.get('retention_estimate') or {}),
        'retention_filter_passed': source_candidate.get('retention_filter_passed'),
        'retention_fallback_used': source_candidate.get('retention_fallback_used', False),
    }
    if 'original_index' in source_candidate:
        item['original_index'] = source_candidate.get('original_index')
    item['expression'] = ' and '.join(_candidate_expression(condition) for condition in item['conditions'])
    return item


def _ranked_candidates(candidates: list[JsonDict]) -> list[JsonDict]:
    ranked = _with_original_indexes(candidates)
    ranked.sort(
        key=lambda candidate: (
            -_score_value(candidate, 'combined_score'),
            -_score_value(candidate, 'score'),
            int(candidate.get('original_index') or 0),
            str(candidate.get('feature') or ''),
        )
    )
    return ranked


def _dedupe_candidates(candidates: list[JsonDict]) -> list[JsonDict]:
    deduped: list[JsonDict] = []
    seen: set[tuple[object, object, object]] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            str(item.get('v5_candidate_source') or ''),
            -_score_value(item, 'combined_score'),
            str(item.get('expression') or ''),
        ),
    ):
        key = (
            candidate.get('v5_candidate_source'),
            candidate.get('expression'),
            candidate_signature(candidate),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _non_seed_candidates(
    candidates: list[JsonDict],
    *,
    primary_feature: str,
    trade_amount_feature: str,
) -> list[JsonDict]:
    return [
        candidate for candidate in candidates
        if candidate.get('feature') not in {primary_feature, trade_amount_feature}
    ]


def _secondary_candidates(
    candidates: list[JsonDict],
    *,
    primary_feature: str,
    trade_amount_feature: str,
    secondary_features: list[str] | None,
    candidate_count: int,
) -> list[JsonDict]:
    explicit = [
        candidate for candidate in candidates
        if candidate.get('feature') in set(secondary_features or [])
        and candidate.get('feature') not in {primary_feature, trade_amount_feature}
    ]
    if explicit or secondary_features:
        return explicit

    auto: list[JsonDict] = []
    seen_features: set[object] = set()
    for candidate in _non_seed_candidates(
        candidates,
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
    ):
        feature = candidate.get('feature')
        if feature in seen_features:
            continue
        seen_features.add(feature)
        auto.append(candidate)
        if len(auto) >= max(int(candidate_count), 1):
            break
    return auto


def _family_counts(candidates: list[JsonDict]) -> dict[str, int]:
    return dict(Counter(str(candidate.get('v5_candidate_source') or '') for candidate in candidates))


def build_v5_recovery_candidate_pool(
    *,
    full_recommended_candidates: list[JsonDict],
    existing_v4_result: JsonDict | None,
    best_context: JsonDict,
    primary_feature: str,
    trade_amount_feature: str,
    secondary_features: list[str] | None,
    candidate_count: int,
) -> JsonDict:
    existing_v4_result = existing_v4_result or {}
    existing_candidates = [dict(candidate) for candidate in existing_v4_result.get('candidates') or []]
    initial_v4_candidate_count = int(existing_v4_result.get('candidate_count') or len(existing_candidates))
    if existing_candidates:
        for candidate in existing_candidates:
            candidate.setdefault('v5_candidate_source', 'direct_v4')
        return {
            'status': 'ok',
            'mode': 'best_feature_mix_v5_recovery',
            'recovery_attempted': False,
            'recovery_reason': 'direct_v4_available',
            'initial_v4_candidate_count': initial_v4_candidate_count,
            'candidates': existing_candidates,
            'candidate_count': len(existing_candidates),
            'recovery_family_counts': {'direct_v4': len(existing_candidates)},
            'final_candidate_pool_count': len(existing_candidates),
        }

    best_primary, best_trade_amount = parse_best_expression_conditions(
        str(best_context.get('expression') or ''),
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
    )
    recommended = _ranked_candidates(full_recommended_candidates)
    candidates: list[JsonDict] = []

    for trade_candidate in recommended:
        if trade_candidate.get('feature') != trade_amount_feature:
            continue
        if candidate_signature(trade_candidate) == candidate_signature(best_trade_amount):
            continue
        candidates.append(_combo_candidate(
            [best_primary, trade_candidate],
            v4_candidate_type='v4_repair_trade_amount',
            v5_candidate_source='recovered_trade_feature',
            source_candidate=trade_candidate,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
        ))

    for secondary in _secondary_candidates(
        recommended,
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
        secondary_features=secondary_features,
        candidate_count=candidate_count,
    ):
        secondary_feature = str(secondary.get('feature') or '')
        candidates.append(_combo_candidate(
            [best_primary, best_trade_amount, secondary],
            v4_candidate_type='v4_tighten_secondary',
            v5_candidate_source='auto_secondary_feature',
            source_candidate=secondary,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
            secondary_feature=secondary_feature,
        ))
        candidates.append(_combo_candidate(
            [best_primary, secondary],
            v4_candidate_type='v4_replace_secondary',
            v5_candidate_source='auto_secondary_feature',
            source_candidate=secondary,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
            secondary_feature=secondary_feature,
        ))

    if len(candidates) < max(int(candidate_count), 1):
        for fallback in _non_seed_candidates(
            recommended,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
        ):
            candidates.append(_combo_candidate(
                [best_primary, fallback],
                v4_candidate_type='v4_replace_secondary',
                v5_candidate_source='safe_recommended_fallback',
                source_candidate=fallback,
                primary_feature=primary_feature,
                trade_amount_feature=trade_amount_feature,
                secondary_feature=str(fallback.get('feature') or ''),
            ))
            if len(candidates) >= max(int(candidate_count), 1):
                break

    candidates = _dedupe_candidates(candidates)
    return {
        'status': 'ok',
        'mode': 'best_feature_mix_v5_recovery',
        'recovery_attempted': True,
        'recovery_reason': 'v4_candidate_pool_empty',
        'initial_v4_candidate_count': initial_v4_candidate_count,
        'candidates': candidates,
        'candidate_count': len(candidates),
        'recovery_family_counts': _family_counts(candidates),
        'final_candidate_pool_count': len(candidates),
    }
