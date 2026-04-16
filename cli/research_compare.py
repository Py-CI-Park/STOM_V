"""Baseline/candidate trade-set comparison."""

from __future__ import annotations

import pandas as pd

from cli.research_metrics import normalize_trade_frame, summarize_trade_frame


TRADE_KEY_COLUMNS = ('종목코드', '종목명', '매수시간', '매수가', '매도시간')


def make_trade_key(row) -> str:
    """Build a stable trade key from currently available result columns."""
    parts = []
    for column in TRADE_KEY_COLUMNS:
        if column in row.index and pd.notna(row[column]):
            value = row[column]
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            parts.append(str(value))
    return '|'.join(parts)


def _with_trade_key(data) -> pd.DataFrame:
    df = normalize_trade_frame(data)
    if df.empty:
        df['_trade_key'] = []
        return df
    df['_trade_key'] = df.apply(make_trade_key, axis=1)
    return df


def _subset_by_keys(df: pd.DataFrame, keys: set[str]) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df[df['_trade_key'].isin(keys)].copy()


def compare_trade_sets(baseline_data, candidate_data) -> dict:
    """Compare baseline and candidate trade result frames."""
    baseline = _with_trade_key(baseline_data)
    candidate = _with_trade_key(candidate_data)
    baseline_keys = set(baseline['_trade_key'])
    candidate_keys = set(candidate['_trade_key'])
    common_keys = baseline_keys & candidate_keys
    excluded_keys = baseline_keys - candidate_keys
    new_keys = candidate_keys - baseline_keys
    common = _subset_by_keys(candidate, common_keys)
    excluded = _subset_by_keys(baseline, excluded_keys)
    new = _subset_by_keys(candidate, new_keys)
    baseline_count = len(baseline)
    return {
        'baseline_summary': summarize_trade_frame(baseline),
        'candidate_summary': summarize_trade_frame(candidate),
        'common_summary': summarize_trade_frame(common),
        'excluded_summary': summarize_trade_frame(excluded),
        'new_summary': summarize_trade_frame(new),
        'counts': {
            'baseline': baseline_count,
            'candidate': len(candidate),
            'common': len(common),
            'excluded': len(excluded),
            'new': len(new),
        },
        'trade_count_retention': 0.0 if baseline_count == 0 else len(candidate) / baseline_count,
        'trade_count_expansion': 0.0 if baseline_count == 0 else len(new) / baseline_count,
        'matching_key_columns': [
            column for column in TRADE_KEY_COLUMNS
            if column in baseline.columns or column in candidate.columns
        ],
    }
