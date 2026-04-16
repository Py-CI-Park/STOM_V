import pandas as pd

from cli.research_segments import (
    add_market_cap_segment,
    add_time_segment,
    analyze_single_axis_segments,
    analyze_two_axis_segments,
    infer_market_cap_unit,
)


def _segment_frame():
    rows = []
    for index in range(40):
        rows.append({
            '종목명': 'A' if index < 20 else 'B',
            '매수시간': 202501010900 + index,
            '수익률': -1.0 if index < 20 else 1.0,
            'R_MFE': 0.4 if index < 20 else 2.0,
            'R_MAE': -2.0 if index < 20 else -0.3,
            'B_시분초': 91000 if index < 20 else 100000,
            'B_시가총액': 1500 if index < 20 else 12000,
            'B_체결강도': 80 if index < 20 else 140,
        })
    return pd.DataFrame(rows)


def test_add_time_segment_labels_default_buckets():
    result = add_time_segment(_segment_frame())
    assert result['_time_segment'].iloc[0] == '장초반'
    assert result['_time_segment'].iloc[-1] == '오전'


def test_infer_market_cap_unit_detects_current_csv_like_values():
    assert infer_market_cap_unit(pd.Series([1500, 12000, 50000])) == '억원'


def test_add_market_cap_segment_uses_normalized_labels():
    result = add_market_cap_segment(_segment_frame())
    assert result['_market_cap_segment'].iloc[0] == '소형'
    assert result['_market_cap_segment'].iloc[-1] == '대형'


def test_analyze_single_axis_segments_reports_weak_segment():
    result = analyze_single_axis_segments(_segment_frame(), segment_column='_time_segment', min_samples=10)
    weak = [item for item in result if item['segment'] == '장초반'][0]
    assert weak['count'] == 20
    assert weak['avg_return'] == -1.0
    assert weak['win_rate'] == 0.0
    assert weak['avg_mae'] == -2.0


def test_analyze_two_axis_segments_combines_time_and_market_cap():
    result = analyze_two_axis_segments(_segment_frame(), first='_time_segment', second='_market_cap_segment', min_samples=10)
    assert any(
        item['first_segment'] == '장초반'
        and item['second_segment'] == '소형'
        and item['count'] == 20
        for item in result
    )
