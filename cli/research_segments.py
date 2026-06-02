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

# 시초 20분을 5분 셀로 세분한 버킷(Phase C-2). 시드는 09:00~09:05에 거래가 몰려
#   coarse '장초반'(09:00~09:30) 한 칸으로는 시초 시간대 신호가 안 보인다. 비-시드
#   생성 전략이 시초 분포를 드러내도록 5분 셀을 쓰되, 시초 이후 거래(오전/점심/오후)는
#   coarse 버킷으로 그대로 분류해 전 시간대를 빠짐없이 라벨링한다.
FINE_TIME_BUCKETS = (
    ('0900-0905', 90000, 90500),
    ('0905-0910', 90500, 91000),
    ('0910-0915', 91000, 91500),
    ('0915-0920', 91500, 92000),
    ('0920+', 92000, 93000),
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

# 매수 시점 등락률(B_등락율) 기준 구간. 음수(하락)·약상승·상승·급등·초급등·폭등 6단계.
DEFAULT_CHANGE_BUCKETS = (
    ('급락', float('-inf'), 0.0),
    ('약상승', 0.0, 3.0),
    ('상승', 3.0, 6.0),
    ('급등', 6.0, 10.0),
    ('초급등', 10.0, 20.0),
    ('폭등', 20.0, float('inf')),
)


def _assign_bucket(value: float, buckets: tuple[tuple[str, float, float], ...], default: str = '미분류') -> str:
    for name, lower, upper in buckets:
        if lower <= value < upper:
            return name
    return default


def add_time_segment(
    data,
    column: str = 'B_시분초',
    buckets: tuple = DEFAULT_TIME_BUCKETS,
) -> pd.DataFrame:
    """Add `_time_segment` using HHMMSS-style buy-time values.

    `buckets` defaults to DEFAULT_TIME_BUCKETS (30분 coarse) for byte-identical
    back-compat. Pass FINE_TIME_BUCKETS for 5분 시초 세분(Phase C-2).
    """
    df = normalize_trade_frame(data)
    if column not in df.columns:
        df['_time_segment'] = '미분류'
        return df
    values = pd.to_numeric(df[column], errors='coerce').fillna(0)
    df['_time_segment'] = [_assign_bucket(float(value), buckets) for value in values]
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


def add_change_segment(
    data,
    column: str = 'B_등락율',
    out_col: str = '_change_segment',
    buckets: tuple = DEFAULT_CHANGE_BUCKETS,
) -> pd.DataFrame:
    """Add `_change_segment` using buy-time change-rate (B_등락율) buckets.

    컬럼이 없거나 유효값이 없으면 전 행을 '미분류'로 채워 graceful하게 처리한다.
    buckets defaults to DEFAULT_CHANGE_BUCKETS. Pass custom buckets to override.
    """
    df = normalize_trade_frame(data)
    if column not in df.columns:
        df[out_col] = '미분류'
        return df
    values = pd.to_numeric(df[column], errors='coerce')
    df[out_col] = [
        _assign_bucket(float(v), buckets) if not pd.isna(v) else '미분류'
        for v in values
    ]
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


def analyze_single_axis_segments(
    data,
    segment_column: str,
    min_samples: int = 30,
    time_buckets: tuple = DEFAULT_TIME_BUCKETS,
) -> list[dict]:
    """Summarize each segment in one segment column.

    `time_buckets` defaults to DEFAULT_TIME_BUCKETS (byte-identical back-compat);
    pass FINE_TIME_BUCKETS for 5분 시초 세분(Phase C-2).
    """
    df = add_market_cap_segment(add_time_segment(data, buckets=time_buckets))
    baseline = summarize_trade_frame(df)
    if segment_column not in df.columns:
        return []
    results = []
    for segment, group in df.groupby(segment_column, dropna=False):
        if len(group) < min_samples:
            continue
        results.append(_segment_summary(group, baseline, {'segment': str(segment)}))
    return sorted(results, key=lambda item: item['avg_return'])


def analyze_two_axis_segments(
    data,
    first: str,
    second: str,
    min_samples: int = 30,
    time_buckets: tuple = DEFAULT_TIME_BUCKETS,
) -> list[dict]:
    """Summarize combinations of two segment columns.

    `time_buckets` defaults to DEFAULT_TIME_BUCKETS (byte-identical back-compat);
    pass FINE_TIME_BUCKETS for 5분 시초 세분(Phase C-2).
    """
    df = add_market_cap_segment(add_time_segment(data, buckets=time_buckets))
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
