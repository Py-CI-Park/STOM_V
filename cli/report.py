"""결과 집계 리포트 — DataFrame 변환 + CSV/Excel 출력.

현재는 공식 `stom_backtest.py` 서브커맨드로 직접 노출하지 않는 library-only 모듈이다.
"""

import pandas as pd


def results_to_dataframe(results: list) -> pd.DataFrame:
    """백테스트 결과 리스트를 DataFrame으로 변환한다.

    각 결과의 metrics를 행으로 펼치고, 'params' 키가 있으면 컬럼으로 flatten한다.

    Args:
        results: run_backtest() 또는 run_sweep() 반환값 리스트.

    Returns:
        pd.DataFrame.
    """
    if not results:
        return pd.DataFrame()

    rows = []
    for r in results:
        metrics = r.get('metrics') or {}
        row = {
            'trade_count': metrics.get('trade_count', 0),
            'win_rate': metrics.get('win_rate', 0.0),
            'cagr': metrics.get('cagr', 0.0),
            'mdd_pct': metrics.get('mdd_pct', 0.0),
            'total_profit': metrics.get('total_profit_krw', 0),
            'tpi': metrics.get('tpi', 0.0),
        }
        if 'params' in r:
            row.update(r['params'])
        rows.append(row)

    return pd.DataFrame(rows)


def save_csv(df: pd.DataFrame, path: str) -> dict:
    """DataFrame을 CSV 파일로 저장한다.

    Args:
        df:   저장할 DataFrame.
        path: 저장 경로 문자열.

    Returns:
        {'status': 'ok'|'error', 'path': str, 'error': str(오류 시만)}
    """
    try:
        df.to_csv(path, index=False, encoding='utf-8-sig')
        return {'status': 'ok', 'path': path}
    except Exception as e:
        return {'status': 'error', 'path': path, 'error': str(e)}


def save_excel(df: pd.DataFrame, path: str) -> dict:
    """DataFrame을 Excel 파일로 저장한다.

    Args:
        df:   저장할 DataFrame.
        path: 저장 경로 문자열 (.xlsx).

    Returns:
        {'status': 'ok'|'error', 'path': str, 'error': str(오류 시만)}
    """
    try:
        df.to_excel(path, index=False, engine='openpyxl')
        return {'status': 'ok', 'path': path}
    except Exception as e:
        return {'status': 'error', 'path': path, 'error': str(e)}


def summary_stats(df: pd.DataFrame) -> dict:
    """집계 통계를 계산한다.

    Args:
        df: results_to_dataframe() 반환 DataFrame.

    Returns:
        mean_cagr, median_cagr, best_cagr, worst_cagr 등을 포함한 dict.
    """
    if df.empty or 'cagr' not in df.columns:
        return {
            'mean_cagr': None,
            'median_cagr': None,
            'best_cagr': None,
            'worst_cagr': None,
        }

    return {
        'mean_cagr': df['cagr'].mean(),
        'median_cagr': df['cagr'].median(),
        'best_cagr': df['cagr'].max(),
        'worst_cagr': df['cagr'].min(),
    }
