import pandas as pd

from cli.research_metrics import (
    calculate_concentration,
    calculate_profit_factor,
    normalize_trade_frame,
    summarize_trade_frame,
)


def _sample_frame():
    return pd.DataFrame([
        {'종목명': 'A', '매수시간': 202501010900, '매도시간': 202501010910, '매수가': 1000, '수익률': 1.5, '수익금': 1500, 'R_MFE': 2.0, 'R_MAE': -0.5, '매도조건': '익절'},
        {'종목명': 'B', '매수시간': 202501010930, '매도시간': 202501010940, '매수가': 2000, '수익률': -1.0, '수익금': -1000, 'R_MFE': 0.2, 'R_MAE': -1.8, '매도조건': '손절'},
        {'종목명': 'A', '매수시간': 202501020900, '매도시간': 202501020910, '매수가': 1000, '수익률': 0.5, '수익금': 500, 'R_MFE': 1.0, 'R_MAE': -0.3, '매도조건': '익절'},
    ])


def test_normalize_trade_frame_adds_trade_date_and_numeric_columns():
    df = normalize_trade_frame(_sample_frame())
    assert df['매수시간'].dtype.kind in {'i', 'u'}
    assert df['수익률'].dtype.kind == 'f'
    assert df['_trade_date'].tolist() == [20250101, 20250101, 20250102]


def test_calculate_profit_factor_uses_profit_amounts():
    df = normalize_trade_frame(_sample_frame())
    assert calculate_profit_factor(df) == 2.0


def test_calculate_concentration_returns_largest_share():
    df = normalize_trade_frame(_sample_frame())
    assert calculate_concentration(df, '종목명') == 2 / 3
    assert calculate_concentration(df, '_trade_date') == 2 / 3


def test_summarize_trade_frame_returns_baseline_metrics():
    summary = summarize_trade_frame(_sample_frame())
    assert summary['trade_count'] == 3
    assert summary['win_rate'] == 2 / 3
    assert summary['avg_return'] == (1.5 - 1.0 + 0.5) / 3
    assert summary['total_profit'] == 1000
    assert summary['avg_mfe'] == (2.0 + 0.2 + 1.0) / 3
    assert summary['avg_mae'] == (-0.5 - 1.8 - 0.3) / 3
    assert summary['symbol_concentration'] == 2 / 3
    assert summary['date_concentration'] == 2 / 3
    assert summary['sell_condition_counts'] == {'익절': 2, '손절': 1}


def test_summarize_trade_frame_empty_frame_is_safe():
    summary = summarize_trade_frame(pd.DataFrame(columns=['수익률', '수익금']))
    assert summary['trade_count'] == 0
    assert summary['win_rate'] == 0.0
    assert summary['profit_factor'] == 0.0
