"""Retention-aware candidate helpers for discovery research."""

from __future__ import annotations

import math

import pandas as pd
from pandas.api.types import is_bool_dtype


def _finite_float(value, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _prepare_retention_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    for column in list(prepared.columns):
        if isinstance(column, str) and column.startswith('B_'):
            runtime_name = column[2:]
            if runtime_name not in prepared.columns:
                prepared[runtime_name] = prepared[column]
    return prepared


def _safe_eval_mask(frame: pd.DataFrame, expression: str) -> tuple[pd.Series, str | None]:
    prepared = _prepare_retention_frame(frame)
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


def estimate_candidate_retention(frame: pd.DataFrame, expression: str) -> dict:
    baseline_trade_count = int(len(frame))
    if baseline_trade_count <= 0:
        return {
            'baseline_trade_count': 0,
            'estimated_removed_count': 0,
            'estimated_kept_count': 0,
            'estimated_retention': 0.0,
            'evaluation_error': None,
        }

    mask, evaluation_error = _safe_eval_mask(frame, expression)
    removed = int(mask.sum())
    kept = max(baseline_trade_count - removed, 0)
    return {
        'baseline_trade_count': baseline_trade_count,
        'estimated_removed_count': removed,
        'estimated_kept_count': kept,
        'estimated_retention': kept / baseline_trade_count,
        'evaluation_error': evaluation_error,
    }


def annotate_candidate_retention(
    candidates: list[dict],
    baseline_frame: pd.DataFrame,
    min_retention: float,
) -> list[dict]:
    threshold = _finite_float(min_retention, 0.0)
    annotated = []
    for candidate in candidates:
        item = dict(candidate)
        estimate = estimate_candidate_retention(
            baseline_frame,
            str(item.get('expression') or ''),
        )
        item['retention_estimate'] = estimate
        item['retention_filter_passed'] = (
            estimate['evaluation_error'] is None
            and estimate['estimated_retention'] >= threshold
        )
        item['retention_fallback_used'] = False
        annotated.append(item)
    return annotated


def retention_penalty(actual_retention, min_retention) -> float:
    retention = max(_finite_float(actual_retention), 0.0)
    threshold = _finite_float(min_retention, 0.0)
    if threshold <= 0:
        return 1.0
    if retention >= threshold:
        return 1.0
    return retention / threshold


def apply_retention_penalty(rank_score: dict, min_retention) -> dict:
    result = dict(rank_score)
    promotion_score = _finite_float(result.get('promotion_score'))
    trade_count_retention = _finite_float(result.get('trade_count_retention'))
    penalty = retention_penalty(trade_count_retention, min_retention)
    result['promotion_score'] = promotion_score
    result['trade_count_retention'] = trade_count_retention
    result['retention_penalty'] = penalty
    result['adjusted_score'] = promotion_score * penalty
    return result


def _candidate_score(candidate: dict) -> float:
    for key in ('combined_score', 'score', 'base_score'):
        if key in candidate:
            return _finite_float(candidate.get(key))
    return 0.0


def _retention_value(candidate: dict) -> float:
    estimate = candidate.get('retention_estimate') or {}
    return _finite_float(estimate.get('estimated_retention'))


def _has_evaluation_error(candidate: dict) -> bool:
    estimate = candidate.get('retention_estimate') or {}
    return bool(estimate.get('evaluation_error'))


def _retention_selection_summary(
    *,
    status: str,
    phase: str,
    pool_count: int,
    passed_count: int,
    fallback_count: int,
    selected_count: int,
    requested_count: int,
    min_retention,
    allow_fallback: bool,
    message: str | None = None,
) -> dict:
    summary = {
        'status': status,
        'phase': phase,
        'pool_count': pool_count,
        'passed_count': passed_count,
        'fallback_count': fallback_count,
        'selected_count': selected_count,
        'requested_count': requested_count,
        'min_estimated_retention': min_retention,
        'allow_retention_fallback': allow_fallback,
    }
    if message is not None:
        summary['message'] = message
    return summary


def select_retention_aware_candidates(
    candidates: list[dict],
    candidate_count: int,
    allow_fallback: bool,
    min_retention,
) -> tuple[list[dict], dict]:
    pool = [dict(candidate) for candidate in candidates]
    requested_count = max(int(candidate_count), 0)
    passed = [
        candidate for candidate in pool
        if candidate.get('retention_filter_passed') and not _has_evaluation_error(candidate)
    ]
    failed = [
        candidate for candidate in pool
        if not candidate.get('retention_filter_passed') and not _has_evaluation_error(candidate)
    ]
    sort_key = lambda item: (-_retention_value(item), -_candidate_score(item))
    passed.sort(key=sort_key)
    failed.sort(key=sort_key)

    if len(passed) < requested_count and not allow_fallback:
        message = (
            f'candidate_count={requested_count} requested but only {len(passed)} '
            f'candidates passed min_estimated_retention={min_retention}'
        )
        return [], _retention_selection_summary(
            status='error',
            phase='insufficient_retention_candidates',
            pool_count=len(pool),
            passed_count=len(passed),
            fallback_count=0,
            selected_count=0,
            requested_count=requested_count,
            min_retention=min_retention,
            allow_fallback=allow_fallback,
            message=message,
        )

    selected = []
    for item in passed[:requested_count]:
        item['retention_fallback_used'] = False
        selected.append(item)

    fallback_needed = max(requested_count - len(selected), 0)
    for item in failed[:fallback_needed]:
        item['retention_fallback_used'] = True
        selected.append(item)

    fallback_count = sum(1 for item in selected if item.get('retention_fallback_used'))
    return selected, _retention_selection_summary(
        status='ok',
        phase='retention_candidates_selected',
        pool_count=len(pool),
        passed_count=len(passed),
        fallback_count=fallback_count,
        selected_count=len(selected),
        requested_count=requested_count,
        min_retention=min_retention,
        allow_fallback=allow_fallback,
    )
