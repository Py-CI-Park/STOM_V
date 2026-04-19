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
