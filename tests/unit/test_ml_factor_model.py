import json
from unittest.mock import patch

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


# ============================================================
# 경계 조건 테스트
# ============================================================

def test_class_imbalance_extreme():
    """수익/손실 비율이 극단적일 때 class_weight='balanced'가 동작하는지 확인"""
    rows = []
    for i in range(100):
        rows.append({
            '매수시간': 20240101090000 + i,
            '수익률': 1.0 if i >= 95 else -1.0,
            'B_등락율': float(i),
            'B_체결강도': float(50 + i),
        })
    df = pd.DataFrame(rows)
    result = analyze_results_ml(df, n_splits=2)
    assert result['status'] == 'ok'
    assert result['class_balance']['positive_ratio'] == 0.05


def test_min_splits_auto_adjustment():
    """데이터가 적을 때 n_splits가 자동 조정되는지 확인"""
    rows = []
    for i in range(25):
        rows.append({
            '매수시간': 20240101090000 + i,
            '수익률': 1.0 if i >= 12 else -1.0,
            'B_등락율': float(i),
            'B_체결강도': float(50 + i),
        })
    df = pd.DataFrame(rows)
    result = analyze_results_ml(df, n_splits=10)
    assert result['status'] == 'ok'
    assert len(result['cv_scores']) == 2


def test_gradient_boosting_model():
    """model_type='gradient_boosting' 정상 동작 확인"""
    rows = []
    for i in range(60):
        rows.append({
            '매수시간': 20240101090000 + i,
            '수익률': 1.0 if i % 3 == 0 else -1.0,
            'B_등락율': float(i) * 0.1,
            'B_체결강도': float(50 + i),
        })
    df = pd.DataFrame(rows)
    result = analyze_results_ml(df, model_type='gradient_boosting', top_n=2, n_splits=2)
    assert result['status'] == 'ok'
    assert result['model_type'] == 'gradient_boosting'
    assert len(result['top_features']) == 2


def test_no_numeric_b_features():
    """숫자형 B_* 컬럼이 없을 때 status='error' 반환"""
    df = pd.DataFrame({
        '매수시간': range(30),
        '수익률': [1.0] * 15 + [-1.0] * 15,
        'B_종목명': ['종목A'] * 30,
    })
    result = analyze_results_ml(df)
    assert result['status'] == 'error'
    assert 'not found' in result['message']


def test_feature_importance_keys_match_columns():
    """feature_importance_map의 키가 B_* 컬럼명과 일치"""
    result = analyze_results_ml(_sample_ml_frame(), top_n=10, n_splits=2)
    assert result['status'] == 'ok'
    for key in result['feature_importance_map']:
        assert key.startswith('B_')


def test_shap_fallback_when_unavailable():
    """shap 미설치 시 shap_status='unavailable'으로 정상 완료"""
    with patch('cli.ml_factor_model.shap', None):
        result = analyze_results_ml(_sample_ml_frame(), top_n=3, n_splits=2)
    assert result['status'] == 'ok'
    assert result['shap_status'] == 'unavailable'
    assert result['shap_available'] is False
    assert result['top_shap_features'] == []
    assert result['shap_message'] is not None


def test_missing_target_column():
    """target column이 없을 때 status='error' 반환"""
    df = pd.DataFrame({'B_등락율': range(30)})
    result = analyze_results_ml(df, target_col='수익률')
    assert result['status'] == 'error'
    assert 'not found' in result['message']


def test_too_few_rows():
    """데이터가 20행 미만이면 status='error' 반환"""
    df = pd.DataFrame({
        '수익률': [1.0] * 10,
        'B_등락율': range(10),
    })
    result = analyze_results_ml(df)
    assert result['status'] == 'error'
    assert '20행' in result['message']


def test_fillna_uses_median_not_zero():
    """결측값이 0이 아닌 피처별 중앙값으로 대체되는지 확인"""
    rows = []
    for i in range(60):
        rows.append({
            '매수시간': 20240101090000 + i,
            '수익률': 1.0 if i % 2 == 0 else -1.0,
            'B_시가총액': 500_000_000_000 if i < 55 else None,
            'B_등락율': float(i),
        })
    df = pd.DataFrame(rows)
    result = analyze_results_ml(df, n_splits=2)
    assert result['status'] == 'ok'
