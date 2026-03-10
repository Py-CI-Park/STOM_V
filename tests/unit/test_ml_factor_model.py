import json

import pandas as pd

from cli.ml_factor_model import analyze_results_ml, save_ml_analysis


def _sample_ml_frame():
    rows = []
    for index in range(60):
        rows.append({
            '매수시간': 20240101090000 + index,
            '수익률': 1.0 if index >= 30 else -1.0,
            'B_등락율': 3.0 + index * 0.1 if index >= 30 else 0.5 + index * 0.01,
            'B_체결강도': 120 + index if index >= 30 else 80 + index,
            'B_시가총액': 2_000_000_000_000 if index >= 30 else 100_000_000_000,
            'B_시분초': 140000 if index >= 30 else 91000,
        })
    return pd.DataFrame(rows)


def test_analyze_results_ml_returns_feature_importance():
    result = analyze_results_ml(_sample_ml_frame(), top_n=3, n_splits=3)

    assert result['status'] == 'ok'
    assert result['feature_count'] >= 4
    assert len(result['cv_scores']) == 3
    assert len(result['top_features']) == 3
    assert 'feature_importance_map' in result
    assert 'shap_status' in result
    assert result['top_features'][0]['feature'] in {'B_등락율', 'B_체결강도', 'B_시가총액', 'B_시분초'}


def test_save_ml_analysis_writes_json(tmp_path):
    result = analyze_results_ml(_sample_ml_frame(), top_n=3, n_splits=3)
    out_path = tmp_path / 'ml_analysis.json'

    save_result = save_ml_analysis(result, str(out_path))

    assert save_result['status'] == 'ok'
    saved = json.loads(out_path.read_text(encoding='utf-8'))
    assert saved['status'] == 'ok'
    assert 'top_features' in saved
