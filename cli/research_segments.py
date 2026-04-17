"""Segment analysis helpers for strategy research."""

from __future__ import annotations

import pandas as pd

from cli.research_metrics import normalize_trade_frame, summarize_trade_frame


DEFAULT_TIME_BUCKETS = (
    ('장초반', 90000, 93000),
    ('오전', 93000, 113000),
    ('점심', 113000, 130000),
    ('오후', 130000, 153000),
)

DEFAULT_MARKET_CAP_BUCKETS = (
    ('초소형', 0, 1000),
    ('소형', 1000, 3000),
    ('중형', 3000, 10000),
    ('대형', 10000, 50000),
    ('초대형', 50000, float('inf')),
)


def _assign_bucket(value: float, buckets: tuple[tuple[str, float, float], ...], default: str = '미분류') -> str:
    for name, lower, upper in buckets:
        if lower <= value < upper:
            return name
    return default


def add_time_segment(data, column: str = 'B_시분초') -> pd.DataFrame:
    """Add `_time_segment` using HHMMSS-style buy-time values."""
    df = normalize_trade_frame(data)
    if column not in df.columns:
        df['_time_segment'] = '미분류'
        return df
    values = pd.to_numeric(df[column], errors='coerce').fillna(0)
    df['_time_segment'] = [_assign_bucket(float(value), DEFAULT_TIME_BUCKETS) for value in values]
    return df


def _finite_positive_mask(values: pd.Series) -> pd.Series:
    return values.notna() & (values > 0) & (values < float('inf'))


def infer_market_cap_unit(series: pd.Series) -> str:
    """Infer market-cap unit for result CSV values."""
    values = pd.to_numeric(series, errors='coerce')
    finite_positive = values[_finite_positive_mask(values)]
    if finite_positive.empty:
        return 'unknown'
    median = float(finite_positive.median())
    if median < 1_000_000:
        return '억원'
    return 'raw'


def _normalize_market_cap_values(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors='coerce')
    valid_mask = _finite_positive_mask(values)
    normalized = values.copy()
    normalized.loc[~valid_mask] = float('nan')
    if infer_market_cap_unit(values) == 'raw':
        normalized.loc[valid_mask] = normalized.loc[valid_mask] / 100_000_000
    return normalized


def add_market_cap_segment(data, column: str = 'B_시가총액') -> pd.DataFrame:
    """Add `_market_cap_segment` using normalized market-cap buckets."""
    df = normalize_trade_frame(data)
    if column not in df.columns:
        df['_market_cap_segment'] = '미분류'
        return df
    normalized = _normalize_market_cap_values(df[column])
    df['_market_cap_segment'] = [_assign_bucket(float(value), DEFAULT_MARKET_CAP_BUCKETS) for value in normalized]
    return df


def _segment_summary(group: pd.DataFrame, baseline: dict, segment_info: dict) -> dict:
    summary = summarize_trade_frame(group)
    avg_return = summary['avg_return']
    win_rate = summary['win_rate']
    return {
        **segment_info,
        'count': summary['trade_count'],
        'avg_return': avg_return,
        'median_return': summary['median_return'],
        'win_rate': win_rate,
        'avg_mfe': summary['avg_mfe'],
        'avg_mae': summary['avg_mae'],
        'total_profit': summary['total_profit'],
        'return_diff': avg_return - baseline['avg_return'],
        'win_rate_diff': win_rate - baseline['win_rate'],
    }


def analyze_single_axis_segments(data, segment_column: str, min_samples: int = 30) -> list[dict]:
    """Summarize each segment in one segment column."""
    df = add_market_cap_segment(add_time_segment(data))
    baseline = summarize_trade_frame(df)
    if segment_column not in df.columns:
        return []
    results = []
    for segment, group in df.groupby(segment_column, dropna=False):
        if len(group) < min_samples:
            continue
        results.append(_segment_summary(group, baseline, {'segment': str(segment)}))
    return sorted(results, key=lambda item: item['avg_return'])


def analyze_two_axis_segments(data, first: str, second: str, min_samples: int = 30) -> list[dict]:
    """Summarize combinations of two segment columns."""
    df = add_market_cap_segment(add_time_segment(data))
    baseline = summarize_trade_frame(df)
    if first not in df.columns or second not in df.columns:
        return []
    results = []
    for (first_value, second_value), group in df.groupby([first, second], dropna=False):
        if len(group) < min_samples:
            continue
        results.append(_segment_summary(group, baseline, {
            'first_axis': first,
            'first_segment': str(first_value),
            'second_axis': second,
            'second_segment': str(second_value),
        }))
    return sorted(results, key=lambda item: item['avg_return'])
