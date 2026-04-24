"""Pure helpers for Wide v1 iteration loop v4 row-set diversity."""

from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportMissingTypeStubs=none, reportUnknownArgumentType=none, reportUnknownMemberType=none, reportUnknownVariableType=none

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from typing import Any, TypeAlias, cast

import pandas as pd
from pandas.api.types import is_bool_dtype

from cli.condition_generator import candidate_to_expression
from cli.research_iteration_v2 import candidate_signature
from cli.research_iteration_v3 import parse_best_expression_conditions

JsonDict: TypeAlias = dict[str, Any]
ProxySignature: TypeAlias = frozenset[int]
ConditionInterval: TypeAlias = tuple[float | None, bool, float | None, bool]

DEFAULT_FAMILY_TARGETS = {
    'v4_repair_trade_amount': 2,
    'v4_replace_secondary': 2,
    'v4_tighten_secondary': 2,
    'v4_relax_trade_amount': 2,
}


def _score_value(candidate: JsonDict, key: str) -> float:
    try:
        return float(candidate.get(key, candidate.get('score', 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _candidate_expression(candidate: JsonDict) -> str:
    if candidate.get('source') != 'best_context' and candidate.get('expression'):
        return str(candidate['expression'])
    return candidate_to_expression(candidate, runtime_context=True)


def _combo_candidate(
    conditions: list[JsonDict],
    *,
    candidate_type: str,
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
        'source': 'v4_candidate_pool',
        'primary_feature': primary_feature,
        'trade_amount_feature': trade_amount_feature,
        'secondary_feature': secondary_feature,
        'retention_estimate': deepcopy(source_candidate.get('retention_estimate') or {}),
        'retention_filter_passed': source_candidate.get('retention_filter_passed'),
        'retention_fallback_used': source_candidate.get('retention_fallback_used', False),
        'v4_candidate_type': candidate_type,
        'conditions': [deepcopy(condition) for condition in conditions],
    }
    if 'original_index' in source_candidate:
        item['original_index'] = source_candidate.get('original_index')
    item['expression'] = ' and '.join(_candidate_expression(condition) for condition in item['conditions'])
    return item


def _control_candidate(best_context: JsonDict) -> JsonDict:
    return {
        'v4_candidate_type': 'v4_control_keep_best',
        'strategy_name': best_context.get('strategy_name'),
        'expression': best_context.get('expression'),
        'reference_adjusted_score': best_context.get('reference_adjusted_score'),
        'skip_backtest': True,
    }


def _numeric_bound(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, str | int | float):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _condition_interval(candidate: JsonDict) -> ConditionInterval | None:
    operator = candidate.get('operator')
    if operator == 'between':
        lower = _numeric_bound(candidate.get('lower_bound'))
        upper = _numeric_bound(candidate.get('upper_bound'))
        if lower is None or upper is None:
            return None
        return lower, True, upper, False

    threshold = _numeric_bound(candidate.get('threshold'))
    if threshold is None:
        return None
    if operator == '>=':
        return threshold, True, None, True
    if operator == '>':
        return threshold, False, None, True
    if operator == '<=':
        return None, True, threshold, True
    if operator == '<':
        return None, True, threshold, False
    return None


def _lower_bound_covers(
    candidate_lower: float | None,
    candidate_inclusive: bool,
    best_lower: float | None,
    best_inclusive: bool,
) -> bool:
    if best_lower is None:
        return candidate_lower is None
    if candidate_lower is None:
        return True
    if candidate_lower < best_lower:
        return True
    if candidate_lower > best_lower:
        return False
    return candidate_inclusive or not best_inclusive


def _upper_bound_covers(
    candidate_upper: float | None,
    candidate_inclusive: bool,
    best_upper: float | None,
    best_inclusive: bool,
) -> bool:
    if best_upper is None:
        return candidate_upper is None
    if candidate_upper is None:
        return True
    if candidate_upper > best_upper:
        return True
    if candidate_upper < best_upper:
        return False
    return candidate_inclusive or not best_inclusive


def _is_trade_amount_relax(candidate: JsonDict, best_trade_amount: JsonDict) -> bool:
    candidate_interval = _condition_interval(candidate)
    best_interval = _condition_interval(best_trade_amount)
    if candidate_interval is None or best_interval is None:
        return False
    candidate_lower, candidate_lower_inclusive, candidate_upper, candidate_upper_inclusive = candidate_interval
    best_lower, best_lower_inclusive, best_upper, best_upper_inclusive = best_interval
    return _lower_bound_covers(
        candidate_lower,
        candidate_lower_inclusive,
        best_lower,
        best_lower_inclusive,
    ) and _upper_bound_covers(
        candidate_upper,
        candidate_upper_inclusive,
        best_upper,
        best_upper_inclusive,
    )


def _dedupe_candidates(candidates: list[JsonDict]) -> list[JsonDict]:
    selected: list[JsonDict] = []
    seen: set[tuple[object, object, object]] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            str(item.get('v4_candidate_type') or ''),
            -_score_value(item, 'combined_score'),
            str(item.get('expression') or ''),
        ),
    ):
        key = (
            candidate.get('v4_candidate_type'),
            candidate.get('expression'),
            candidate_signature(candidate),
        )
        if key in seen:
            continue
        seen.add(key)
        selected.append(candidate)
    return selected


def build_v4_candidate_pool(
    analysis_candidates: list[JsonDict],
    *,
    best_context: JsonDict | None = None,
    primary_feature: str = 'B_시가총액',
    trade_amount_feature: str = 'B_당일거래대금',
    secondary_features: list[str] | None = None,
    min_estimated_retention: float | None = 0.4,
    retention_tolerance: float = 0.02,
) -> JsonDict:
    _ = min_estimated_retention
    _ = retention_tolerance
    if not best_context:
        return {
            'status': 'disabled',
            'mode': 'best_feature_mix_v4',
            'primary_feature': primary_feature,
            'trade_amount_feature': trade_amount_feature,
            'secondary_features': list(secondary_features or []),
            'control_candidate': None,
            'candidates': [],
            'candidate_count': 0,
            'type_counts': {},
            'reason': 'best_context is required',
        }

    best_primary, best_trade_amount = parse_best_expression_conditions(
        str(best_context.get('expression') or ''),
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
    )
    secondary_feature_set = set(secondary_features or []) - {primary_feature, trade_amount_feature}
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

    candidates: list[JsonDict] = []
    for secondary in secondary_candidates:
        secondary_feature = str(secondary.get('feature') or '')
        candidates.append(_combo_candidate(
            [best_primary, best_trade_amount, secondary],
            candidate_type='v4_tighten_secondary',
            source_candidate=secondary,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
            secondary_feature=secondary_feature,
        ))
        candidates.append(_combo_candidate(
            [best_primary, secondary],
            candidate_type='v4_replace_secondary',
            source_candidate=secondary,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
            secondary_feature=secondary_feature,
        ))

    for trade_amount in trade_amount_candidates:
        candidate_type = (
            'v4_relax_trade_amount'
            if _is_trade_amount_relax(trade_amount, best_trade_amount)
            else 'v4_repair_trade_amount'
        )
        candidates.append(_combo_candidate(
            [best_primary, trade_amount],
            candidate_type=candidate_type,
            source_candidate=trade_amount,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
        ))

    candidates = _dedupe_candidates(candidates)
    type_counts = Counter(str(item.get('v4_candidate_type')) for item in candidates)
    type_counts['v4_control_keep_best'] += 1
    return {
        'status': 'ok',
        'mode': 'best_feature_mix_v4',
        'primary_feature': primary_feature,
        'trade_amount_feature': trade_amount_feature,
        'secondary_features': list(secondary_features or []),
        'best_conditions': [best_primary, best_trade_amount],
        'control_candidate': _control_candidate(best_context),
        'candidates': candidates,
        'candidate_count': len(candidates),
        'type_counts': dict(type_counts),
    }


def _signature_hash(signature: ProxySignature) -> str:
    payload = json.dumps(sorted(signature), separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


def _prepare_proxy_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    for column in list(prepared.columns):
        if isinstance(column, str) and column.startswith('B_'):
            runtime_name = column[2:]
            if runtime_name not in prepared.columns:
                prepared[runtime_name] = prepared[column]
    return prepared


def _evaluate_mask(frame: pd.DataFrame, expression: str) -> tuple[pd.Series, str | None]:
    prepared = _prepare_proxy_frame(frame)
    full_remove_mask = pd.Series([True] * len(prepared), index=prepared.index)
    try:
        mask = prepared.eval(expression, engine='python')
    except Exception as exc:
        return full_remove_mask, str(exc)
    if not isinstance(mask, pd.Series):
        return full_remove_mask, 'expression did not return a row mask'
    if not is_bool_dtype(mask.dtype):
        return full_remove_mask, 'expression did not return a boolean row mask'
    return mask.fillna(False).astype(bool), None


def estimate_candidate_rowset_proxy(frame: pd.DataFrame, expression: str) -> JsonDict:
    baseline_trade_count = int(len(frame))
    if baseline_trade_count <= 0:
        signature: ProxySignature = frozenset()
        return {
            'baseline_trade_count': 0,
            'proxy_removed_count': 0,
            'proxy_kept_count': 0,
            'proxy_retention': 0.0,
            'proxy_signature': signature,
            'proxy_signature_hash': _signature_hash(signature),
            'evaluation_error': None,
        }

    mask, evaluation_error = _evaluate_mask(frame, expression)
    removed_positions = {
        position for position, should_remove in enumerate(mask.tolist())
        if bool(should_remove)
    }
    kept_signature = frozenset(
        position for position in range(baseline_trade_count)
        if position not in removed_positions
    )
    kept = len(kept_signature)
    return {
        'baseline_trade_count': baseline_trade_count,
        'proxy_removed_count': len(removed_positions),
        'proxy_kept_count': kept,
        'proxy_retention': kept / baseline_trade_count,
        'proxy_signature': kept_signature,
        'proxy_signature_hash': _signature_hash(kept_signature),
        'evaluation_error': evaluation_error,
    }


def annotate_candidate_rowset_proxy(
    candidates: list[JsonDict],
    baseline_frame: pd.DataFrame,
    *,
    min_retention: float,
) -> list[JsonDict]:
    annotated: list[JsonDict] = []
    for candidate in candidates:
        item = dict(candidate)
        proxy = estimate_candidate_rowset_proxy(
            baseline_frame,
            str(item.get('expression') or ''),
        )
        proxy['proxy_filter_passed'] = (
            proxy['evaluation_error'] is None
            and float(proxy['proxy_retention']) >= float(min_retention)
        )
        item['rowset_proxy'] = proxy
        item['retention_estimate'] = {
            'estimated_retention': proxy['proxy_retention'],
            'evaluation_error': proxy['evaluation_error'],
        }
        item['retention_filter_passed'] = proxy['proxy_filter_passed']
        item['retention_fallback_used'] = False
        annotated.append(item)
    return annotated


def _quota_summary(
    selected: list[JsonDict],
    family_targets: dict[str, int],
) -> dict[str, JsonDict]:
    selected_counts = Counter(str(item.get('v4_candidate_type') or '') for item in selected)
    return {
        family: {
            'target': target,
            'selected': selected_counts.get(family, 0),
            'shortfall': max(target - selected_counts.get(family, 0), 0),
        }
        for family, target in family_targets.items()
    }


def _proxy_sort_key(candidate: JsonDict) -> tuple[float, float, int]:
    proxy = candidate.get('rowset_proxy') or {}
    proxy_retention = float(proxy.get('proxy_retention') or 0.0)
    target_distance = min(abs(proxy_retention - 0.80), abs(proxy_retention - 0.95))
    original_index = int(candidate.get('original_index') or 0)
    return (target_distance, -_score_value(candidate, 'combined_score'), original_index)


def _proxy_retention(candidate: JsonDict) -> float:
    proxy = candidate.get('rowset_proxy') or {}
    try:
        value = float(proxy.get('proxy_retention') or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) else 0.0


def _is_proxy_eligible(candidate: JsonDict, min_retention: float) -> bool:
    proxy = candidate.get('rowset_proxy') or {}
    return (
        proxy.get('proxy_filter_passed') is True
        and not proxy.get('evaluation_error')
        and _proxy_retention(candidate) >= min_retention
    )


def _coerce_proxy_signature(value: object) -> ProxySignature | None:
    if not isinstance(value, frozenset):
        return None
    if not all(isinstance(item, int) for item in value):
        return None
    return cast(ProxySignature, value)


def select_rowset_diverse_candidates(
    candidates: list[JsonDict],
    *,
    candidate_count: int,
    min_retention: float,
    family_targets: dict[str, int] | None = None,
) -> tuple[list[JsonDict], JsonDict]:
    requested_count = max(int(candidate_count), 0)
    targets = dict(DEFAULT_FAMILY_TARGETS if family_targets is None else family_targets)
    eligible = [
        dict(candidate) for candidate in candidates
        if _is_proxy_eligible(candidate, min_retention)
    ]
    eligible.sort(key=_proxy_sort_key)

    selected: list[JsonDict] = []
    used_signatures: set[ProxySignature] = set()

    def try_add(candidate: JsonDict) -> bool:
        proxy = candidate.get('rowset_proxy') or {}
        signature = _coerce_proxy_signature(proxy.get('proxy_signature'))
        if signature is None:
            return False
        if signature in used_signatures:
            return False
        selected.append(candidate)
        used_signatures.add(signature)
        return True

    for family, target in targets.items():
        for candidate in eligible:
            if len(selected) >= requested_count:
                break
            if candidate.get('v4_candidate_type') != family:
                continue
            family_selected = sum(1 for item in selected if item.get('v4_candidate_type') == family)
            if family_selected >= target:
                break
            _ = try_add(candidate)

    for candidate in eligible:
        if len(selected) >= requested_count:
            break
        if candidate in selected:
            continue
        _ = try_add(candidate)

    skipped_duplicate_proxy_count = 0
    for candidate in eligible:
        if candidate in selected:
            continue
        signature = _coerce_proxy_signature((candidate.get('rowset_proxy') or {}).get('proxy_signature'))
        if signature is not None and signature in used_signatures:
            skipped_duplicate_proxy_count += 1

    summary = {
        'status': 'ok',
        'phase': 'rowset_diverse_candidates_selected',
        'pool_count': len(candidates),
        'passed_count': len(eligible),
        'fallback_count': 0,
        'eligible_count': len(eligible),
        'selected_count': len(selected),
        'requested_count': requested_count,
        'min_estimated_retention': min_retention,
        'allow_retention_fallback': False,
        'proxy_group_count': len(used_signatures),
        'selected_proxy_groups': [
            str((item.get('rowset_proxy') or {}).get('proxy_signature_hash') or '')
            for item in selected
        ],
        'skipped_duplicate_proxy_count': skipped_duplicate_proxy_count,
        'quota_summary': _quota_summary(selected, targets),
    }
    return selected, summary
