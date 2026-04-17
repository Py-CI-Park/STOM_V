"""Segment research-loop metrics helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from cli._utils import ensure_dataframe as _ensure_dataframe


NUMERIC_COLUMNS = (
    '매수시간', '매도시간', '매수가', '매도가', '보유시간',
    '수익률', '수익금', '수익금합계', 'R_MFE', 'R_MAE',
)


def normalize_trade_frame(data) -> pd.DataFrame:
    """Return a copy of a backtest result frame with stable numeric helper columns."""
    df = _ensure_dataframe(Path(data) if isinstance(data, str) else data).copy()
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce')
    if '매수시간' in df.columns:
        buy_times = df['매수시간'].where(np.isfinite(df['매수시간']), 0).fillna(0)
        df['_trade_date'] = buy_times.astype('int64').astype(str).str[:8].astype('int64')
    else:
        df['_trade_date'] = 0
    return df


def calculate_profit_factor(df: pd.DataFrame, profit_col: str = '수익금') -> float:
    """Return gross profit divided by absolute gross loss.

    Returns ``float('inf')`` when profitable rows exist without any losses, and
    ``0.0`` when there is no gross profit to compare against losses.
    """
    if profit_col not in df.columns or df.empty:
        return 0.0
    profits = pd.to_numeric(df[profit_col], errors='coerce').fillna(0.0)
    gross_profit = float(profits[profits > 0].sum())
    gross_loss = abs(float(profits[profits < 0].sum()))
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def calculate_concentration(df: pd.DataFrame, column: str) -> float:
    """Return the largest row-count share for a column."""
    if column not in df.columns or df.empty:
        return 0.0
    counts = df[column].value_counts(dropna=False)
    if counts.empty:
        return 0.0
    return float(counts.iloc[0] / len(df))


def _mean_or_zero(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or df.empty:
        return 0.0
    values = pd.to_numeric(df[column], errors='coerce').dropna()
    return 0.0 if values.empty else float(values.mean())


def summarize_trade_frame(data, return_col: str = '수익률') -> dict:
    """Calculate baseline metrics for executed backtest trades."""
    df = normalize_trade_frame(data)
    returns = pd.Series(dtype='float64')
    if return_col in df.columns and not df.empty:
        returns = pd.to_numeric(df[return_col], errors='coerce').dropna()

    sell_counts = {}
    if '매도조건' in df.columns and not df.empty:
        sell_counts = {str(key): int(value) for key, value in df['매도조건'].value_counts(dropna=False).items()}

    total_profit = 0.0
    if '수익금' in df.columns:
        total_profit = float(pd.to_numeric(df['수익금'], errors='coerce').fillna(0.0).sum())

    return {
        'trade_count': int(len(df)),
        'win_rate': 0.0 if returns.empty else float((returns > 0).mean()),
        'avg_return': 0.0 if returns.empty else float(returns.mean()),
        'median_return': 0.0 if returns.empty else float(returns.median()),
        'total_return': 0.0 if returns.empty else float(returns.sum()),
        'total_profit': total_profit,
        'avg_hold_time': _mean_or_zero(df, '보유시간'),
        'avg_mfe': _mean_or_zero(df, 'R_MFE'),
        'avg_mae': _mean_or_zero(df, 'R_MAE'),
        'profit_factor': calculate_profit_factor(df),
        'date_concentration': calculate_concentration(df, '_trade_date'),
        'symbol_concentration': calculate_concentration(df, '종목명'),
        'sell_condition_counts': sell_counts,
    }
