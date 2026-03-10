import json

import pandas as pd

from cli.analyzer import (
    analyze_result_frame,
    benjamini_hochberg,
    get_feature_columns,
    save_analysis,
)


def _sample_result_frame():
    rows = []
    for index in range(60):
        if index < 20:
            market_cap = 100_000_000_000
            hms = 91000
            pct = 0.5 + index * 0.05
            ret = -1.0
        elif index < 40:
            market_cap = 800_000_000_000
            hms = 100000
            pct = 2.0 + (index - 20) * 0.05
            ret = 0.5
        else:
            market_cap = 2_000_000_000_000
            hms = 140000
            pct = 3.5 + (index - 40) * 0.05
            ret = 1.5
        rows.append({
            '종목명': f'종목{index}',
            '수익률': ret,
            'B_등락율': pct,
            'B_시가총액': market_cap,
            'B_시분초': hms,
            'B_체결강도': 90 + index,
        })
    return pd.DataFrame(rows)


def test_get_feature_columns_filters_b_prefix():
    df = _sample_result_frame()
    assert get_feature_columns(df) == ['B_등락율', 'B_시가총액', 'B_시분초', 'B_체결강도']


def test_analyze_result_frame_returns_candidates():
    result = analyze_result_frame(_sample_result_frame(), min_samples=10, quantiles=4)

    assert result['status'] == 'ok'
    assert result['row_count'] == 60
    assert any(candidate['feature'] == 'B_시가총액' for candidate in result['market_cap_candidates'])
    assert any(candidate['feature'] == 'B_시분초' for candidate in result['time_candidates'])
    assert any(candidate['feature'] == 'B_등락율' for candidate in result['quantile_candidates'])
    assert len(result['recommended_candidates']) >= 3


def test_benjamini_hochberg_flags_small_p_values():
    results = benjamini_hochberg([0.001, 0.01, 0.2], alpha=0.05)
    assert results[0]['accepted_fdr'] is True
    assert results[1]['accepted_fdr'] is True
    assert results[2]['accepted_fdr'] is False


def test_save_analysis_writes_json(tmp_path):
    result = analyze_result_frame(_sample_result_frame(), min_samples=10, quantiles=4)
    out_path = tmp_path / 'analysis.json'

    save_result = save_analysis(result, str(out_path))

    assert save_result['status'] == 'ok'
    saved = json.loads(out_path.read_text(encoding='utf-8'))
    assert saved['status'] == 'ok'
    assert 'recommended_candidates' in saved
