import json
from unittest.mock import patch

import numpy as np
import pandas as pd

from cli.analyzer import (
    analyze_market_cap_segments,
    analyze_result_frame,
    analyze_time_segments,
    analyze_ttest_candidates,
    benjamini_hochberg,
    generate_quantile_candidates,
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


# ============================================================
# benjamini_hochberg 경계 조건
# ============================================================

def test_benjamini_hochberg_empty_input():
    assert benjamini_hochberg([]) == []


def test_benjamini_hochberg_single_value_significant():
    results = benjamini_hochberg([0.01], alpha=0.05)
    assert len(results) == 1
    assert results[0]['accepted_fdr'] is True


def test_benjamini_hochberg_single_value_not_significant():
    results = benjamini_hochberg([0.1], alpha=0.05)
    assert len(results) == 1
    assert results[0]['accepted_fdr'] is False


def test_benjamini_hochberg_all_significant():
    results = benjamini_hochberg([0.001, 0.002, 0.003], alpha=0.05)
    assert all(r['accepted_fdr'] is True for r in results)


def test_benjamini_hochberg_none_significant():
    results = benjamini_hochberg([0.5, 0.6, 0.9], alpha=0.05)
    assert all(r['accepted_fdr'] is False for r in results)


def test_benjamini_hochberg_handles_nan_values():
    results = benjamini_hochberg([0.01, float('nan'), 0.8], alpha=0.05)
    assert len(results) == 2
    assert results[0]['accepted_fdr'] is True


# ============================================================
# analyze_market_cap_segments 경계 조건
# ============================================================

def test_analyze_market_cap_missing_column():
    df = pd.DataFrame({'수익률': [1.0, -1.0], 'B_등락율': [0.5, 1.5]})
    result = analyze_market_cap_segments(df)
    assert result['status'] == 'error'
    assert 'not found' in result['message']
    assert result['results'] == []
    assert result['candidates'] == []


def test_analyze_market_cap_min_samples_filters():
    df = _sample_result_frame()
    result = analyze_market_cap_segments(df, min_samples=100)
    assert result['status'] == 'ok'
    assert result['results'] == []


# ============================================================
# analyze_time_segments 경계 조건
# ============================================================

def test_analyze_time_missing_column():
    df = pd.DataFrame({'수익률': [1.0, -1.0], 'B_등락율': [0.5, 1.5]})
    result = analyze_time_segments(df)
    assert result['status'] == 'error'
    assert 'not found' in result['message']
    assert result['results'] == []
    assert result['candidates'] == []


# ============================================================
# analyze_ttest_candidates 경계 조건
# ============================================================

def test_analyze_ttest_returns_empty_when_scipy_unavailable():
    with patch('cli.analyzer.stats', None):
        result = analyze_ttest_candidates(_sample_result_frame(), min_samples=10)
    assert result == []


def test_analyze_ttest_independent():
    df = _sample_result_frame()
    candidates = analyze_ttest_candidates(df, min_samples=10, alpha=0.05)
    assert isinstance(candidates, list)
    for c in candidates:
        assert 'feature' in c
        assert 'operator' in c
        assert c['operator'] in ('<=', '>')
        assert 'p_value' in c
        assert 'accepted_fdr' in c
        assert c['accepted_fdr'] is True


def test_analyze_ttest_operator_direction():
    """low_mean < high_mean이면 operator='<='"""
    n = 100
    df = pd.DataFrame({
        'B_test': list(range(n)),
        '수익률': [-2.0] * (n // 2) + [2.0] * (n // 2),
    })
    candidates = analyze_ttest_candidates(df, feature_columns=['B_test'], min_samples=10, alpha=0.50)
    if candidates:
        assert candidates[0]['operator'] == '<='


def test_analyze_ttest_min_samples_threshold():
    df = pd.DataFrame({
        'B_test': list(range(10)),
        '수익률': [-1.0] * 5 + [1.0] * 5,
    })
    candidates = analyze_ttest_candidates(df, feature_columns=['B_test'], min_samples=30)
    assert candidates == []


# ============================================================
# analyze_result_frame 경계 조건
# ============================================================

def test_analyze_result_frame_empty_dataframe():
    df = pd.DataFrame({'수익률': pd.Series(dtype=float)})
    result = analyze_result_frame(df, min_samples=1, quantiles=2)
    assert result['status'] == 'ok'
    assert result['row_count'] == 0
    assert result['feature_columns'] == []
    assert result['recommended_candidates'] == []


def test_analyze_result_frame_no_b_columns():
    df = pd.DataFrame({'수익률': [1.0, -1.0, 0.5] * 20, 'other_col': range(60)})
    result = analyze_result_frame(df, min_samples=10, quantiles=3)
    assert result['status'] == 'ok'
    assert result['feature_columns'] == []
    assert result['quantile_candidates'] == []
    assert result['ttest_candidates'] == []


# ============================================================
# generate_quantile_candidates 경계 조건
# ============================================================

def test_generate_quantile_candidates_insufficient_data():
    df = pd.DataFrame({'B_test': [1, 2, 3], '수익률': [0.1, -0.1, 0.2]})
    candidates = generate_quantile_candidates(df, min_samples=30, quantiles=10)
    assert candidates == []
