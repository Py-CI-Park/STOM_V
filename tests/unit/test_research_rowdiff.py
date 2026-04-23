import json

import pandas as pd

from cli.research_rowdiff import (
    analyze_row_diff,
    feature_bucket_summary,
    split_trade_sets,
    top_trade_rows,
)


def _frame(rows):
    return pd.DataFrame(rows)


def _row(name, buy_time, sell_time, buy_price, sell_price, ret, profit, cap=100, amount=1000):
    return {
        '종목명': name,
        '매수시간': buy_time,
        '매도시간': sell_time,
        '매수가': buy_price,
        '매도가': sell_price,
        '수익률': ret,
        '수익금': profit,
        '보유시간': sell_time - buy_time,
        'R_MFE': max(ret, 0),
        'R_MAE': min(ret, 0),
        'B_시가총액': cap,
        'B_당일거래대금': amount,
    }


def test_split_trade_sets_returns_common_left_only_and_right_only():
    left = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000),
        _row('B', 20250101090200, 20250101090300, 100, 99, -1.0, -1000),
    ])
    right = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000),
        _row('C', 20250101090400, 20250101090500, 100, 98, -2.0, -2000),
    ])

    result = split_trade_sets(left, right)

    assert result['counts'] == {
        'left': 2,
        'right': 2,
        'common': 1,
        'left_only': 1,
        'right_only': 1,
    }
    assert result['common']['종목명'].tolist() == ['A']
    assert result['left_only']['종목명'].tolist() == ['B']
    assert result['right_only']['종목명'].tolist() == ['C']


def test_feature_bucket_summary_summarizes_existing_numeric_feature():
    frame = _frame([
        _row('A', 1, 2, 100, 101, 1.0, 1000, cap=100),
        _row('B', 3, 4, 100, 99, -1.0, -1000, cap=200),
        _row('C', 5, 6, 100, 98, -2.0, -2000, cap=300),
    ])

    result = feature_bucket_summary(frame, 'B_시가총액', bins=2)

    assert result['feature'] == 'B_시가총액'
    assert result['bucket_count'] == 2
    assert sum(item['trade_count'] for item in result['buckets']) == 3
    assert all('avg_return' in item for item in result['buckets'])


def test_feature_bucket_summary_handles_numeric_strings():
    frame = _frame([
        _row('A', 1, 2, 100, 101, 1.0, 1000, cap='100'),
        _row('B', 3, 4, 100, 99, -1.0, -1000, cap='200'),
        _row('C', 5, 6, 100, 98, -2.0, -2000, cap='300'),
    ])

    result = feature_bucket_summary(frame, 'B_시가총액', bins=2)

    assert result['bucket_count'] == 2
    assert sum(item['trade_count'] for item in result['buckets']) == 3


def test_feature_bucket_summary_keeps_constant_numeric_feature_as_single_bucket():
    frame = _frame([
        _row('A', 1, 2, 100, 101, 1.0, 1000, cap='100'),
        _row('B', 3, 4, 100, 99, -1.0, -1000, cap='100'),
        _row('C', 5, 6, 100, 98, -2.0, -2000, cap='100'),
    ])
    feature = next(column for column in frame.columns if column.startswith('B_'))

    result = feature_bucket_summary(frame, feature, bins=5)

    assert result['bucket_count'] == 1
    assert result['buckets'][0]['bucket'] == 'constant:100'
    assert result['buckets'][0]['trade_count'] == 3


def test_top_trade_rows_returns_loss_and_profit_rows():
    frame = _frame([
        _row('A', 1, 2, 100, 101, 1.0, 1000),
        _row('B', 3, 4, 100, 97, -3.0, -3000),
        _row('C', 5, 6, 100, 103, 3.0, 3000),
    ])

    result = top_trade_rows(frame, n=1)

    assert result['top_losses'][0]['종목명'] == 'B'
    assert result['top_profits'][0]['종목명'] == 'C'


def test_analyze_row_diff_builds_summary_payload():
    left = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000, cap=100),
        _row('B', 20250101090200, 20250101090300, 100, 99, -1.0, -1000, cap=200),
    ])
    right = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000, cap=100),
        _row('C', 20250101090400, 20250101090500, 100, 98, -2.0, -2000, cap=300),
    ])

    result = analyze_row_diff(left, right, feature_columns=['B_시가총액'])

    assert result['status'] == 'ok'
    assert result['counts']['left_only'] == 1
    assert result['summaries']['left_only']['total_profit'] == -1000.0
    assert result['summaries']['right_only']['total_profit'] == -2000.0
    assert result['feature_buckets']['left_only'][0]['feature'] == 'B_시가총액'
    assert result['decision_inputs']['left_only_total_profit'] == -1000.0
    assert result['summaries']['common_left']['total_profit'] == 1000.0
    assert result['summaries']['common_right']['total_profit'] == 1000.0
    assert result['decision_inputs']['common_avg_return_delta'] == 0.0


def test_analyze_row_diff_reports_common_left_right_deltas():
    left = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000),
    ])
    right = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 102, 2.0, 2000),
    ])

    result = analyze_row_diff(left, right)

    assert result['counts']['common'] == 1
    assert result['summaries']['common_left']['avg_return'] == 1.0
    assert result['summaries']['common_right']['avg_return'] == 2.0
    assert result['decision_inputs']['common_avg_return_delta'] == 1.0
    assert result['decision_inputs']['common_total_profit_delta'] == 1000.0


def test_analyze_row_diff_returns_strict_json_safe_non_finite_metrics():
    left = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000),
        _row('B', 20250101090200, 20250101090300, 100, 102, 2.0, 2000),
    ])
    right = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000),
        _row('B', 20250101090200, 20250101090300, 100, 102, 2.0, 2000),
    ])

    result = analyze_row_diff(left, right)

    json.dumps(result, allow_nan=False)
    assert result['summaries']['left']['profit_factor'] is None
    assert result['summaries']['right']['profit_factor'] is None
