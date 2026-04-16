import pandas as pd

from cli.research_compare import compare_trade_sets, make_trade_key


def _baseline():
    return pd.DataFrame([
        {'종목명': 'A', '매수시간': 202501010900, '매도시간': 202501010910, '매수가': 1000, '수익률': 1.0, '수익금': 1000, 'R_MFE': 2.0, 'R_MAE': -0.5},
        {'종목명': 'B', '매수시간': 202501010930, '매도시간': 202501010940, '매수가': 2000, '수익률': -2.0, '수익금': -2000, 'R_MFE': 0.1, 'R_MAE': -2.5},
    ])


def _candidate():
    return pd.DataFrame([
        {'종목명': 'A', '매수시간': 202501010900, '매도시간': 202501010910, '매수가': 1000, '수익률': 1.0, '수익금': 1000, 'R_MFE': 2.0, 'R_MAE': -0.5},
        {'종목명': 'C', '매수시간': 202501011000, '매도시간': 202501011010, '매수가': 3000, '수익률': 0.5, '수익금': 500, 'R_MFE': 1.2, 'R_MAE': -0.4},
    ])


def test_make_trade_key_uses_available_stable_columns():
    row = _baseline().iloc[0]
    assert make_trade_key(row) == 'A|202501010900|1000|202501010910'


def test_compare_trade_sets_splits_common_excluded_new():
    result = compare_trade_sets(_baseline(), _candidate())
    assert result['baseline_summary']['trade_count'] == 2
    assert result['candidate_summary']['trade_count'] == 2
    assert result['common_summary']['trade_count'] == 1
    assert result['excluded_summary']['trade_count'] == 1
    assert result['new_summary']['trade_count'] == 1
    assert result['trade_count_retention'] == 1.0
    assert result['trade_count_expansion'] == 0.5
    assert result['excluded_summary']['avg_return'] == -2.0
    assert result['new_summary']['avg_return'] == 0.5
