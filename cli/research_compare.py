"""Baseline/candidate trade-set comparison."""

from __future__ import annotations

import pandas as pd

from cli.research_metrics import normalize_trade_frame, summarize_trade_frame


INSTRUMENT_COLUMNS = ('종목코드', '종목명')
REQUIRED_KEY_COLUMNS = ('매수시간',)
OPTIONAL_KEY_COLUMNS = ('매수가',)
TRADE_KEY_COLUMNS = INSTRUMENT_COLUMNS + REQUIRED_KEY_COLUMNS + OPTIONAL_KEY_COLUMNS


def _is_usable(value) -> bool:
    if pd.isna(value):
        return False
    return not (isinstance(value, str) and value.strip() == '')


def _format_key_part(value) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value)


def _first_usable(row, columns: tuple[str, ...]):
    for column in columns:
        if column in row.index and _is_usable(row[column]):
            return row[column]
    return None


def make_trade_key(row) -> str:
    """Build a stable trade key from currently available result columns."""
    instrument = _first_usable(row, INSTRUMENT_COLUMNS)
    buy_time = _first_usable(row, REQUIRED_KEY_COLUMNS)
    if instrument is None or buy_time is None:
        raise ValueError('trade row lacks required identity fields')

    parts = [_format_key_part(instrument), _format_key_part(buy_time)]
    for column in OPTIONAL_KEY_COLUMNS:
        if column in row.index and _is_usable(row[column]):
            parts.append(_format_key_part(row[column]))
    return '|'.join(parts)


def _with_trade_key(data) -> pd.DataFrame:
    df = normalize_trade_frame(data)
    if df.empty:
        df['_trade_key'] = []
        df['_trade_occurrence'] = []
        return df
    df['_trade_key'] = df.apply(make_trade_key, axis=1)
    df['_trade_occurrence'] = df.groupby('_trade_key').cumcount()
    return df


def _trade_id_pairs(df: pd.DataFrame) -> set[tuple[str, int]]:
    if df.empty:
        return set()
    return set(zip(df['_trade_key'], df['_trade_occurrence']))


def _subset_by_trade_ids(df: pd.DataFrame, trade_ids: set[tuple[str, int]]) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    row_ids = pd.Series(zip(df['_trade_key'], df['_trade_occurrence']), index=df.index)
    return df[row_ids.isin(trade_ids)].copy()


def compare_trade_sets(baseline_data, candidate_data) -> dict:
    """Compare baseline and candidate trade result frames."""
    baseline = _with_trade_key(baseline_data)
    candidate = _with_trade_key(candidate_data)
    baseline_ids = _trade_id_pairs(baseline)
    candidate_ids = _trade_id_pairs(candidate)
    common_ids = baseline_ids & candidate_ids
    excluded_ids = baseline_ids - candidate_ids
    new_ids = candidate_ids - baseline_ids
    common = _subset_by_trade_ids(candidate, common_ids)
    excluded = _subset_by_trade_ids(baseline, excluded_ids)
    new = _subset_by_trade_ids(candidate, new_ids)
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
