"""ML 기반 팩터 분석기 (library-only).

현재는 RandomForest / GradientBoosting 기반 피처 중요도 분석과
TimeSeriesSplit 검증을 제공한다. SHAP이 설치된 경우에만 SHAP 요약을 추가한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import TimeSeriesSplit

try:  # pragma: no cover - optional dependency
    import shap
except ImportError:  # pragma: no cover - optional dependency
    shap = None

from cli.analyzer import get_feature_columns


def _ensure_dataframe(data) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.read_csv(data)


def _sort_result_frame(df: pd.DataFrame) -> pd.DataFrame:
    for column in ('매수시간', '매도시간', 'index'):
        if column in df.columns:
            return df.sort_values(column).reset_index(drop=True)
    return df.reset_index(drop=True)


def _build_model(model_type: str, random_state: int):
    if model_type == 'random_forest':
        return RandomForestClassifier(
            n_estimators=200,
            random_state=random_state,
            n_jobs=-1,
            class_weight='balanced',
        )
    if model_type == 'gradient_boosting':
        return GradientBoostingClassifier(random_state=random_state)
    raise ValueError(f"unsupported model_type: {model_type}")


def analyze_results_ml(
    data,
    target_col: str = '수익률',
    model_type: str = 'random_forest',
    top_n: int = 10,
    n_splits: int = 5,
    random_state: int = 42,
) -> dict:
    df = _sort_result_frame(_ensure_dataframe(data))
    feature_columns = [
        column for column in get_feature_columns(df)
        if pd.api.types.is_numeric_dtype(df[column])
    ]
    if target_col not in df.columns:
        return {'status': 'error', 'message': f"target column '{target_col}' not found"}
    if len(df) < 20:
        return {'status': 'error', 'message': 'ML 분석에는 최소 20행 이상이 필요합니다.'}
    if not feature_columns:
        return {'status': 'error', 'message': 'numeric B_* feature columns not found'}

    X = df[feature_columns].fillna(0)
    y = (df[target_col] > 0).astype(int)

    max_splits = min(n_splits, max(2, len(df) // 10), len(df) - 1)
    if max_splits < 2:
        return {'status': 'error', 'message': 'TimeSeriesSplit을 위한 데이터가 부족합니다.'}

    cv_scores = []
    splitter = TimeSeriesSplit(n_splits=max_splits)
    for train_idx, test_idx in splitter.split(X):
        model = _build_model(model_type, random_state)
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        pred = model.predict(X.iloc[test_idx])
        cv_scores.append(float(accuracy_score(y.iloc[test_idx], pred)))

    model = _build_model(model_type, random_state)
    model.fit(X, y)
    feature_importance = pd.Series(model.feature_importances_, index=feature_columns).sort_values(ascending=False)
    top_features = [
        {'feature': feature, 'importance': float(importance)}
        for feature, importance in feature_importance.head(top_n).items()
    ]
    feature_importance_map = {item['feature']: item['importance'] for item in top_features}

    shap_summary = []
    shap_available = shap is not None
    shap_status = 'available' if shap_available else 'unavailable'
    shap_message = None if shap_available else 'shap 패키지가 설치되어 있지 않아 SHAP 요약을 생략했습니다.'
    if shap_available:
        try:  # pragma: no cover - optional dependency
            sample_X = X.head(min(200, len(X)))
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(sample_X)
            if isinstance(shap_values, list):
                shap_values = shap_values[-1]
            shap_importance = np.abs(shap_values).mean(axis=0)
            shap_series = pd.Series(shap_importance, index=feature_columns).sort_values(ascending=False)
            shap_summary = [
                {'feature': feature, 'importance': float(importance)}
                for feature, importance in shap_series.head(top_n).items()
            ]
        except Exception:
            shap_available = False
            shap_status = 'failed'
            shap_message = 'SHAP 계산 중 오류가 발생하여 fallback 처리했습니다.'
            shap_summary = []

    return {
        'status': 'ok',
        'model_type': model_type,
        'row_count': int(len(df)),
        'feature_count': len(feature_columns),
        'class_balance': {
            'positive_ratio': float(y.mean()),
            'negative_ratio': float(1 - y.mean()),
        },
        'cv_scores': cv_scores,
        'mean_cv_score': float(sum(cv_scores) / len(cv_scores)),
        'top_features': top_features,
        'feature_importance_map': feature_importance_map,
        'shap_available': shap_available,
        'shap_status': shap_status,
        'shap_message': shap_message,
        'top_shap_features': shap_summary,
    }


def save_ml_analysis(result: dict, path: str) -> dict:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(result, fp, ensure_ascii=False, indent=2)
        return {'status': 'ok', 'path': path}
    except Exception as e:
        return {'status': 'error', 'path': path, 'error': str(e)}
