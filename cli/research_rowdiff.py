from __future__ import annotations

import math
from numbers import Real
from pathlib import Path

import pandas as pd

from cli.research_compare import (
    INSTRUMENT_COLUMNS,
    OPTIONAL_KEY_COLUMNS,
    REQUIRED_KEY_COLUMNS,
    _subset_by_trade_ids,
    _trade_id_pairs,
    _with_trade_key,
)
from cli.research_metrics import NUMERIC_COLUMNS, normalize_trade_frame, summarize_trade_frame


KEY_VARIANTS = {
    'current_buy_identity': (
        INSTRUMENT_COLUMNS[1],
        REQUIRED_KEY_COLUMNS[0],
        OPTIONAL_KEY_COLUMNS[0],
    ),
    'with_sell_identity': (
        INSTRUMENT_COLUMNS[1],
        REQUIRED_KEY_COLUMNS[0],
        OPTIONAL_KEY_COLUMNS[0],
        NUMERIC_COLUMNS[1],
        NUMERIC_COLUMNS[3],
    ),
    'with_hold_identity': (
        INSTRUMENT_COLUMNS[1],
        REQUIRED_KEY_COLUMNS[0],
        OPTIONAL_KEY_COLUMNS[0],
        NUMERIC_COLUMNS[1],
        NUMERIC_COLUMNS[3],
        NUMERIC_COLUMNS[4],
    ),
}


def split_trade_sets(left_data, right_data) -> dict:
    left = _with_trade_key(left_data)
    right = _with_trade_key(right_data)
    left_ids = _trade_id_pairs(left)
    right_ids = _trade_id_pairs(right)
    common_ids = left_ids & right_ids
    left_only_ids = left_ids - right_ids
    right_only_ids = right_ids - left_ids
    common = _subset_by_trade_ids(left, common_ids)
    common_right = _subset_by_trade_ids(right, common_ids)
    left_only = _subset_by_trade_ids(left, left_only_ids)
    right_only = _subset_by_trade_ids(right, right_only_ids)
    return {
        'left': left,
        'right': right,
        'common': common,
        'common_left': common,
        'common_right': common_right,
        'left_only': left_only,
        'right_only': right_only,
        'counts': {
            'left': len(left),
            'right': len(right),
            'common': len(common),
            'left_only': len(left_only),
            'right_only': len(right_only),
        },
        'key_columns': [
            column
            for column in ('종목명', '종목코드', '매수시간', '매수가')
            if column in left.columns or column in right.columns
        ],
    }


def _json_safe_summary(summary: dict) -> dict:
    safe = {}
    for key, value in summary.items():
        if isinstance(value, Real) and not math.isfinite(float(value)):
            safe[key] = None
        else:
            safe[key] = value
    return safe


def _single_feature_bucket(feature: str, usable: pd.DataFrame) -> dict:
    summary = _json_safe_summary(summarize_trade_frame(usable))
    return {
        'feature': feature,
        'bucket_count': 1,
        'buckets': [{
            'bucket': f'constant:{usable[feature].iloc[0]}',
            'trade_count': summary.get('trade_count', 0),
            'avg_return': summary.get('avg_return', 0.0),
            'win_rate': summary.get('win_rate', 0.0),
            'total_profit': summary.get('total_profit', 0.0),
        }],
    }


def _format_key_value(value) -> str:
    if pd.isna(value):
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _keys_for_columns(frame, columns: tuple[str, ...]) -> tuple[list[str], pd.Series]:
    data = normalize_trade_frame(frame)
    present = [column for column in columns if column in data.columns]
    if data.empty or not present:
        return present, pd.Series(dtype='object')
    keys = data[present].apply(
        lambda row: '|'.join(_format_key_value(row[column]) for column in present),
        axis=1,
    )
    return present, keys


def _key_summary(frame, columns: tuple[str, ...]) -> dict:
    present, keys = _keys_for_columns(frame, columns)
    if keys.empty:
        return {
            'present_columns': present,
            'unique_keys': 0,
            'duplicate_rows': 0,
            'duplicate_groups': 0,
            'max_occurrence': 0,
        }
    counts = keys.value_counts()
    return {
        'present_columns': present,
        'unique_keys': int(keys.nunique()),
        'duplicate_rows': int(keys.duplicated(keep=False).sum()),
        'duplicate_groups': int((counts > 1).sum()),
        'max_occurrence': int(counts.max()),
    }


def _set_counts_for_keys(left, right, columns: tuple[str, ...]) -> dict:
    _, left_keys = _keys_for_columns(left, columns)
    _, right_keys = _keys_for_columns(right, columns)
    left_set = set(left_keys)
    right_set = set(right_keys)
    common = left_set & right_set
    return {
        'common_unique': len(common),
        'left_only_unique': len(left_set - common),
        'right_only_unique': len(right_set - common),
    }


def trade_key_diagnostics(left_data, right_data, variants: dict[str, tuple[str, ...]] | None = None) -> dict:
    left = normalize_trade_frame(left_data)
    right = normalize_trade_frame(right_data)
    variants = variants or KEY_VARIANTS
    diagnostics = {}
    baseline_counts = None
    drift = False
    for name, columns in variants.items():
        left_summary = _key_summary(left, columns)
        right_summary = _key_summary(right, columns)
        counts = _set_counts_for_keys(left, right, columns)
        diagnostics[name] = {
            'left': left_summary,
            'right': right_summary,
            'left_duplicate_rows': left_summary['duplicate_rows'],
            'right_duplicate_rows': right_summary['duplicate_rows'],
            **counts,
        }
        comparable = (
            counts['common_unique'],
            counts['left_only_unique'],
            counts['right_only_unique'],
        )
        if baseline_counts is None:
            baseline_counts = comparable
        elif comparable != baseline_counts:
            drift = True
    return {
        'status': 'ok',
        'variants': diagnostics,
        'key_drift_observed': drift,
    }


def feature_bucket_summary(frame, feature: str, bins: int = 5) -> dict:
    data = normalize_trade_frame(frame)
    if feature not in data.columns or data.empty:
        return {'feature': feature, 'bucket_count': 0, 'buckets': []}
    series = pd.to_numeric(data[feature], errors='coerce')
    usable = data[series.notna()].copy()
    if usable.empty:
        return {'feature': feature, 'bucket_count': 0, 'buckets': []}
    usable[feature] = series[series.notna()]
    if usable[feature].nunique(dropna=True) == 1:
        return _single_feature_bucket(feature, usable)
    bucket_count = min(max(int(bins), 1), len(usable))
    try:
        usable['_bucket'] = pd.qcut(usable[feature], q=bucket_count, duplicates='drop')
    except ValueError:
        usable['_bucket'] = pd.cut(usable[feature], bins=bucket_count, duplicates='drop')
    buckets = []
    for bucket, group in usable.groupby('_bucket', observed=False):
        summary = _json_safe_summary(summarize_trade_frame(group))
        buckets.append({
            'bucket': str(bucket),
            'trade_count': summary.get('trade_count', 0),
            'avg_return': summary.get('avg_return', 0.0),
            'win_rate': summary.get('win_rate', 0.0),
            'total_profit': summary.get('total_profit', 0.0),
        })
    return {'feature': feature, 'bucket_count': len(buckets), 'buckets': buckets}


def _row_records(frame, n: int, ascending: bool) -> list[dict]:
    data = normalize_trade_frame(frame)
    if data.empty or '수익률' not in data.columns:
        return []
    sorted_frame = data.sort_values('수익률', ascending=ascending).head(max(n, 0))
    columns = [
        column
        for column in ('종목명', '매수시간', '매도시간', '수익률', '수익금', 'R_MFE', 'R_MAE')
        if column in sorted_frame.columns
    ]
    return sorted_frame[columns].to_dict('records')


def top_trade_rows(frame, n: int = 10) -> dict:
    return {
        'top_losses': _row_records(frame, n, ascending=True),
        'top_profits': _row_records(frame, n, ascending=False),
    }


def _load_if_path(data):
    if isinstance(data, (str, Path)):
        return normalize_trade_frame(Path(data))
    return normalize_trade_frame(data)


def analyze_row_diff(left_data, right_data, feature_columns: list[str] | None = None, top_n: int = 10) -> dict:
    left = _load_if_path(left_data)
    right = _load_if_path(right_data)
    sets = split_trade_sets(left, right)
    key_diagnostics = trade_key_diagnostics(left, right)
    summaries = {
        'left': _json_safe_summary(summarize_trade_frame(sets['left'])),
        'right': _json_safe_summary(summarize_trade_frame(sets['right'])),
        'common': _json_safe_summary(summarize_trade_frame(sets['common'])),
        'common_left': _json_safe_summary(summarize_trade_frame(sets['common_left'])),
        'common_right': _json_safe_summary(summarize_trade_frame(sets['common_right'])),
        'left_only': _json_safe_summary(summarize_trade_frame(sets['left_only'])),
        'right_only': _json_safe_summary(summarize_trade_frame(sets['right_only'])),
    }
    common_avg_return_delta = (
        (summaries['common_right'].get('avg_return') or 0.0)
        - (summaries['common_left'].get('avg_return') or 0.0)
    )
    common_total_profit_delta = (
        (summaries['common_right'].get('total_profit') or 0.0)
        - (summaries['common_left'].get('total_profit') or 0.0)
    )
    feature_columns = feature_columns or []
    feature_buckets = {
        name: [
            feature_bucket_summary(sets[name], feature)
            for feature in feature_columns
        ]
        for name in ('common', 'left_only', 'right_only')
    }
    top_rows = {
        'left_only': top_trade_rows(sets['left_only'], n=top_n),
        'right_only': top_trade_rows(sets['right_only'], n=top_n),
    }
    return {
        'status': 'ok',
        'counts': sets['counts'],
        'key_columns': sets['key_columns'],
        'key_diagnostics': key_diagnostics,
        'summaries': summaries,
        'feature_buckets': feature_buckets,
        'top_rows': top_rows,
        'decision_inputs': {
            'left_only_total_profit': summaries['left_only'].get('total_profit'),
            'left_only_avg_return': summaries['left_only'].get('avg_return'),
            'left_only_win_rate': summaries['left_only'].get('win_rate'),
            'right_only_total_profit': summaries['right_only'].get('total_profit'),
            'right_only_avg_return': summaries['right_only'].get('avg_return'),
            'right_only_win_rate': summaries['right_only'].get('win_rate'),
            'common_avg_return_delta': common_avg_return_delta,
            'common_total_profit_delta': common_total_profit_delta,
        },
    }
