import pandas as pd
import pytest

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


def test_compare_trade_sets_keeps_extra_baseline_duplicates_excluded():
    baseline = pd.concat([_baseline().iloc[[0]], _baseline().iloc[[0]]], ignore_index=True)
    candidate = _baseline().iloc[[0]].copy()
    result = compare_trade_sets(baseline, candidate)
    assert result['common_summary']['trade_count'] == 1
    assert result['excluded_summary']['trade_count'] == 1
    assert result['new_summary']['trade_count'] == 0


def test_compare_trade_sets_keeps_extra_candidate_duplicates_new():
    baseline = _baseline().iloc[[0]].copy()
    candidate = pd.concat([_baseline().iloc[[0]], _baseline().iloc[[0]]], ignore_index=True)
    result = compare_trade_sets(baseline, candidate)
    assert result['common_summary']['trade_count'] == 1
    assert result['excluded_summary']['trade_count'] == 0
    assert result['new_summary']['trade_count'] == 1


def test_make_trade_key_requires_identity_column():
    row = pd.Series({'매수시간': 202501010900, '매수가': 1000, '매도시간': 202501010910})
    with pytest.raises(ValueError, match='trade row lacks required identity fields'):
        make_trade_key(row)


def test_make_trade_key_rejects_all_null_identity_fields():
    row = pd.Series({'종목코드': None, '종목명': None, '매수시간': 202501010900})
    with pytest.raises(ValueError, match='trade row lacks required identity fields'):
        make_trade_key(row)


def test_compare_trade_sets_prefers_code_when_display_name_changes():
    baseline = pd.DataFrame([
        {'종목코드': '000001', '종목명': 'Old', '매수시간': 202501010900, '매도시간': 202501010910, '매수가': 1000},
    ])
    candidate = pd.DataFrame([
        {'종목코드': '000001', '종목명': 'New', '매수시간': 202501010900, '매도시간': 202501010910, '매수가': 1000},
    ])
    assert make_trade_key(baseline.iloc[0]) == '000001|202501010900|1000|202501010910'
    result = compare_trade_sets(baseline, candidate)
    assert result['common_summary']['trade_count'] == 1
    assert result['excluded_summary']['trade_count'] == 0
    assert result['new_summary']['trade_count'] == 0


def test_compare_trade_sets_empty_frames_are_safe():
    result = compare_trade_sets(pd.DataFrame(), pd.DataFrame())
    assert result['baseline_summary']['trade_count'] == 0
    assert result['candidate_summary']['trade_count'] == 0
    assert result['common_summary']['trade_count'] == 0
    assert result['excluded_summary']['trade_count'] == 0
    assert result['new_summary']['trade_count'] == 0
    assert result['counts'] == {'baseline': 0, 'candidate': 0, 'common': 0, 'excluded': 0, 'new': 0}
    assert result['trade_count_retention'] == 0.0
    assert result['trade_count_expansion'] == 0.0
