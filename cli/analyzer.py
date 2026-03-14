"""자동 조건식 탐색용 결과 분석기 (library-only).

백테스트 상세 CSV/DataFrame에서 `B_*` 피처를 중심으로
시간대/시가총액 구간 분석, 분위수 기반 후보 추출, t-test 기반 후보 추출을 수행한다.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

try:
    from scipy import stats
except ImportError:  # pragma: no cover - optional dependency
    stats = None


DEFAULT_MARKET_CAP_BUCKETS = (
    ('소형주', 0, 300_000_000_000),
    ('중형주', 300_000_000_000, 1_000_000_000_000),
    ('대형주', 1_000_000_000_000, 5_000_000_000_000),
    ('초대형주', 5_000_000_000_000, float('inf')),
)
DEFAULT_TIME_BUCKETS = (
    ('장초반', 90000, 93000),
    ('오전', 93000, 113000),
    ('점심', 113000, 130000),
    ('오후', 130000, 153000),
)


def _to_builtin(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if pd.isna(value):
        return None
    return value


def _ensure_dataframe(data) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.read_csv(data)


def _overall_metrics(df: pd.DataFrame, return_col: str):
    returns = df[return_col].dropna()
    if returns.empty:
        return {
            'count': 0,
            'mean_return': 0.0,
            'median_return': 0.0,
            'win_rate': 0.0,
        }
    return {
        'count': int(len(returns)),
        'mean_return': float(returns.mean()),
        'median_return': float(returns.median()),
        'win_rate': float((returns > 0).mean()),
    }


def get_feature_columns(df: pd.DataFrame, prefix: str = 'B_') -> list[str]:
    return [column for column in df.columns if column.startswith(prefix)]


def add_outcome_columns(df: pd.DataFrame, return_col: str = '수익률', label_col: str = '수익여부') -> pd.DataFrame:
    df = df.copy()
    df[label_col] = (df[return_col] > 0).astype(int)
    return df


def analyze_group_performance(df: pd.DataFrame, group_col: str, return_col: str = '수익률', min_samples: int = 30) -> list[dict]:
    results = []
    overall = _overall_metrics(df, return_col)

    for group_value, group_df in df.groupby(group_col, dropna=False):
        count = int(len(group_df))
        if count < min_samples:
            continue
        mean_return = float(group_df[return_col].mean())
        median_return = float(group_df[return_col].median())
        win_rate = float((group_df[return_col] > 0).mean())
        results.append({
            'group': _to_builtin(group_value),
            'count': count,
            'mean_return': mean_return,
            'median_return': median_return,
            'win_rate': win_rate,
            'mean_return_diff': mean_return - overall['mean_return'],
            'win_rate_diff': win_rate - overall['win_rate'],
        })
    return results


def _apply_named_buckets(df: pd.DataFrame, column: str, buckets: Iterable[tuple], label_col: str) -> pd.DataFrame:
    df = df.copy()
    labels = []
    for value in df[column].fillna(0):
        assigned = '미분류'
        for name, lower, upper in buckets:
            if lower <= value < upper:
                assigned = name
                break
        labels.append(assigned)
    df[label_col] = labels
    return df


def _segment_candidates_from_results(
    results: list[dict],
    feature: str,
    buckets: Iterable[tuple],
    source: str,
    min_return_diff: float = 0.0,
    min_win_rate_diff: float = 0.0,
) -> list[dict]:
    bucket_map = {name: (lower, upper) for name, lower, upper in buckets}
    candidates = []

    for item in results:
        if item['mean_return_diff'] >= -min_return_diff and item['win_rate_diff'] >= -min_win_rate_diff:
            continue
        lower, upper = bucket_map.get(item['group'], (None, None))
        score = abs(min(item['mean_return_diff'], 0.0)) + abs(min(item['win_rate_diff'], 0.0))
        candidates.append({
            'feature': feature,
            'source': source,
            'label': item['group'],
            'operator': 'between',
            'lower_bound': lower,
            'upper_bound': upper,
            'count': item['count'],
            'mean_return': item['mean_return'],
            'win_rate': item['win_rate'],
            'mean_return_diff': item['mean_return_diff'],
            'win_rate_diff': item['win_rate_diff'],
            'score': float(score),
        })
    return candidates


def analyze_market_cap_segments(
    df: pd.DataFrame,
    column: str = 'B_시가총액',
    return_col: str = '수익률',
    min_samples: int = 30,
    buckets: Iterable[tuple] = DEFAULT_MARKET_CAP_BUCKETS,
) -> dict:
    if column not in df.columns:
        return {'status': 'error', 'message': f"column '{column}' not found", 'results': [], 'candidates': []}

    bucketed = _apply_named_buckets(df, column, buckets, '_시가총액구간')
    results = analyze_group_performance(bucketed, '_시가총액구간', return_col=return_col, min_samples=min_samples)
    candidates = _segment_candidates_from_results(results, column, buckets, 'market_cap')
    return {'status': 'ok', 'results': results, 'candidates': candidates}


def analyze_time_segments(
    df: pd.DataFrame,
    column: str = 'B_시분초',
    return_col: str = '수익률',
    min_samples: int = 30,
    buckets: Iterable[tuple] = DEFAULT_TIME_BUCKETS,
) -> dict:
    if column not in df.columns:
        return {'status': 'error', 'message': f"column '{column}' not found", 'results': [], 'candidates': []}

    bucketed = _apply_named_buckets(df, column, buckets, '_시간대')
    results = analyze_group_performance(bucketed, '_시간대', return_col=return_col, min_samples=min_samples)
    candidates = _segment_candidates_from_results(results, column, buckets, 'time_of_day')
    return {'status': 'ok', 'results': results, 'candidates': candidates}


def benjamini_hochberg(p_values: Iterable[float], alpha: float = 0.05) -> list[dict]:
    pairs = [(index, float(value)) for index, value in enumerate(p_values) if value is not None and not np.isnan(value)]
    total = len(pairs)
    if total == 0:
        return []

    sorted_positions = sorted(range(total), key=lambda i: pairs[i][1])
    adjusted = [None] * total
    accept = [False] * total

    min_adjusted = 1.0
    for reverse_rank, pos in enumerate(reversed(sorted_positions), start=1):
        rank = total - reverse_rank + 1
        p_value = pairs[pos][1]
        adj = min(min_adjusted, p_value * total / rank)
        min_adjusted = adj
        adjusted[pos] = min(adj, 1.0)

    max_rank = 0
    for rank, pos in enumerate(sorted_positions, start=1):
        if pairs[pos][1] <= alpha * rank / total:
            max_rank = rank
    for rank, pos in enumerate(sorted_positions, start=1):
        accept[pos] = rank <= max_rank

    results = []
    for pos, (original_index, p_value) in enumerate(pairs):
        results.append({
            'index': original_index,
            'p_value': p_value,
            'p_value_adj': adjusted[pos],
            'accepted_fdr': accept[pos],
        })
    return results


def _make_range_candidate(feature: str, interval, metrics: dict, overall: dict, source: str, extra: dict | None = None) -> dict:
    left = None if interval.left == -np.inf else float(interval.left)
    right = None if interval.right == np.inf else float(interval.right)
    if left is None and right is not None:
        operator = '<='
        threshold = right
    elif left is not None and right is None:
        operator = '>='
        threshold = left
    else:
        operator = 'between'
        threshold = None
    score = abs(min(metrics['mean_return'] - overall['mean_return'], 0.0)) + abs(min(metrics['win_rate'] - overall['win_rate'], 0.0))
    candidate = {
        'feature': feature,
        'source': source,
        'operator': operator,
        'threshold': threshold,
        'lower_bound': left,
        'upper_bound': right,
        'count': metrics['count'],
        'mean_return': metrics['mean_return'],
        'win_rate': metrics['win_rate'],
        'mean_return_diff': metrics['mean_return'] - overall['mean_return'],
        'win_rate_diff': metrics['win_rate'] - overall['win_rate'],
        'score': float(score),
    }
    if extra:
        candidate.update(extra)
    return candidate


def generate_quantile_candidates(
    df: pd.DataFrame,
    feature_columns: Iterable[str] | None = None,
    return_col: str = '수익률',
    min_samples: int = 30,
    quantiles: int = 10,
    min_return_diff: float = 0.0,
    min_win_rate_diff: float = 0.0,
) -> list[dict]:
    overall = _overall_metrics(df, return_col)
    feature_columns = list(feature_columns or get_feature_columns(df))
    candidates = []

    for feature in feature_columns:
        series = df[feature].dropna()
        if len(series) < max(min_samples, quantiles):
            continue
        try:
            bucket_series = pd.qcut(df[feature], q=quantiles, duplicates='drop')
        except ValueError:
            continue
        bucketed = df.assign(_bucket=bucket_series)
        for interval, group_df in bucketed.groupby('_bucket', dropna=True, observed=False):
            metrics = {
                'count': int(len(group_df)),
                'mean_return': float(group_df[return_col].mean()),
                'win_rate': float((group_df[return_col] > 0).mean()),
            }
            if metrics['count'] < min_samples:
                continue
            if metrics['mean_return'] >= overall['mean_return'] - min_return_diff and \
                    metrics['win_rate'] >= overall['win_rate'] - min_win_rate_diff:
                continue
            candidates.append(_make_range_candidate(feature, interval, metrics, overall, 'quantile'))

    return sorted(candidates, key=lambda item: item['score'], reverse=True)


def analyze_ttest_candidates(
    df: pd.DataFrame,
    feature_columns: Iterable[str] | None = None,
    return_col: str = '수익률',
    min_samples: int = 30,
    alpha: float = 0.05,
) -> list[dict]:
    if stats is None:
        return []

    feature_columns = list(feature_columns or get_feature_columns(df))
    raw_candidates = []
    p_values = []

    for feature in feature_columns:
        series = df[feature].dropna()
        if len(series) < max(min_samples * 2, 4):
            continue
        median = float(series.median())
        low_group = df[df[feature] <= median][return_col].dropna()
        high_group = df[df[feature] > median][return_col].dropna()
        if len(low_group) < min_samples or len(high_group) < min_samples:
            continue
        t_stat, p_value = stats.ttest_ind(low_group, high_group, equal_var=False)
        low_mean = float(low_group.mean())
        high_mean = float(high_group.mean())
        if low_mean <= high_mean:
            operator = '<='
            worse_mean = low_mean
            count = int(len(low_group))
        else:
            operator = '>'
            worse_mean = high_mean
            count = int(len(high_group))
        raw_candidates.append({
            'feature': feature,
            'source': 'ttest',
            'operator': operator,
            'threshold': median,
            'lower_bound': None,
            'upper_bound': None,
            'count': count,
            'mean_return': worse_mean,
            'other_mean_return': high_mean if operator == '<=' else low_mean,
            't_stat': float(t_stat),
            'p_value': float(p_value),
            'score': abs(low_mean - high_mean),
        })
        p_values.append(float(p_value))

    bh_results = {item['index']: item for item in benjamini_hochberg(p_values, alpha=alpha)}
    filtered = []
    for index, candidate in enumerate(raw_candidates):
        bh = bh_results.get(index, {})
        candidate['p_value_adj'] = bh.get('p_value_adj')
        candidate['accepted_fdr'] = bh.get('accepted_fdr', False)
        if candidate['accepted_fdr']:
            filtered.append(candidate)
    return sorted(filtered, key=lambda item: item['score'], reverse=True)


def analyze_result_frame(
    data,
    return_col: str = '수익률',
    min_samples: int = 30,
    quantiles: int = 10,
    alpha: float = 0.05,
) -> dict:
    df = add_outcome_columns(_ensure_dataframe(data), return_col=return_col)
    feature_columns = get_feature_columns(df)

    market_cap_analysis = analyze_market_cap_segments(df, return_col=return_col, min_samples=min_samples)
    time_analysis = analyze_time_segments(df, return_col=return_col, min_samples=min_samples)
    quantile_candidates = generate_quantile_candidates(
        df, feature_columns=feature_columns, return_col=return_col, min_samples=min_samples, quantiles=quantiles
    )
    ttest_candidates = analyze_ttest_candidates(
        df, feature_columns=feature_columns, return_col=return_col, min_samples=min_samples, alpha=alpha
    )

    recommended_candidates = sorted(
        market_cap_analysis.get('candidates', []) + time_analysis.get('candidates', []) +
        quantile_candidates + ttest_candidates,
        key=lambda item: item['score'],
        reverse=True
    )

    return {
        'status': 'ok',
        'created_at': datetime.now().isoformat(),
        'row_count': int(len(df)),
        'feature_columns': feature_columns,
        'market_cap_analysis': market_cap_analysis.get('results', []),
        'market_cap_candidates': market_cap_analysis.get('candidates', []),
        'time_analysis': time_analysis.get('results', []),
        'time_candidates': time_analysis.get('candidates', []),
        'quantile_candidates': quantile_candidates,
        'ttest_candidates': ttest_candidates,
        'recommended_candidates': recommended_candidates,
    }


def analyze_result_csv(path: str, **kwargs) -> dict:
    return analyze_result_frame(Path(path), **kwargs)


def save_analysis(result: dict, path: str) -> dict:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(result, fp, ensure_ascii=False, indent=2, default=_to_builtin)
        return {'status': 'ok', 'path': path}
    except Exception as e:
        return {'status': 'error', 'path': path, 'error': str(e)}
