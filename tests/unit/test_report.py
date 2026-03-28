"""cli/report.py 단위 테스트.

대상: results_to_dataframe, save_csv, save_excel, summary_stats
"""
import os
import sys
import tempfile

import pytest
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.report import (
    results_to_dataframe,
    save_csv,
    save_excel,
    summary_stats,
)


# ============================================================
# 공통 픽스처
# ============================================================

def _make_result(trade_count=10, win_rate=0.6, cagr=0.15, mdd_pct=0.05,
                 total_profit=100000, tpi=1.2):
    return {
        'status': 'success',
        'message': '완료',
        'metrics': {
            'trade_count': trade_count,
            'win_rate': win_rate,
            'cagr': cagr,
            'mdd_pct': mdd_pct,
            'total_profit_krw': total_profit,
            'tpi': tpi,
        },
    }


def _make_sweep_result(avg_time=60, betting='1', **kwargs):
    r = _make_result(**kwargs)
    r['params'] = {'avg_time': avg_time, 'betting': betting}
    return r


# ============================================================
# TestResultsToDataframe
# ============================================================

class TestResultsToDataframe:
    """results_to_dataframe 함수 단위 테스트."""

    def test_empty_list_returns_empty_dataframe(self):
        """빈 리스트는 빈 DataFrame을 반환해야 한다."""
        df = results_to_dataframe([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_single_result_returns_one_row(self):
        """결과 1개는 행이 1개인 DataFrame이어야 한다."""
        df = results_to_dataframe([_make_result()])
        assert len(df) == 1

    def test_multiple_results_row_count(self):
        """결과 N개는 행이 N개인 DataFrame이어야 한다."""
        results = [_make_result(trade_count=i) for i in range(5)]
        df = results_to_dataframe(results)
        assert len(df) == 5

    def test_contains_trade_count_column(self):
        """trade_count 컬럼이 존재해야 한다."""
        df = results_to_dataframe([_make_result()])
        assert 'trade_count' in df.columns

    def test_contains_win_rate_column(self):
        """win_rate 컬럼이 존재해야 한다."""
        df = results_to_dataframe([_make_result()])
        assert 'win_rate' in df.columns

    def test_contains_cagr_column(self):
        """cagr 컬럼이 존재해야 한다."""
        df = results_to_dataframe([_make_result()])
        assert 'cagr' in df.columns

    def test_contains_mdd_pct_column(self):
        """mdd_pct 컬럼이 존재해야 한다."""
        df = results_to_dataframe([_make_result()])
        assert 'mdd_pct' in df.columns

    def test_contains_tpi_column(self):
        """tpi 컬럼이 존재해야 한다."""
        df = results_to_dataframe([_make_result()])
        assert 'tpi' in df.columns

    def test_sweep_results_flatten_params_to_columns(self):
        """params 키가 있으면 해당 키/값이 컬럼으로 펼쳐져야 한다."""
        results = [_make_sweep_result(avg_time=60, betting='1')]
        df = results_to_dataframe(results)
        assert 'avg_time' in df.columns
        assert 'betting' in df.columns

    def test_sweep_params_values_correct(self):
        """펼쳐진 params 값이 원본과 일치해야 한다."""
        results = [_make_sweep_result(avg_time=120, betting='3')]
        df = results_to_dataframe(results)
        assert df.iloc[0]['avg_time'] == 120
        assert df.iloc[0]['betting'] == '3'


# ============================================================
# TestSaveCsv
# ============================================================

class TestSaveCsv:
    """save_csv 함수 단위 테스트."""

    def test_save_csv_returns_ok_status(self):
        """정상 저장 시 status가 'ok'여야 한다."""
        df = results_to_dataframe([_make_result()])
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            path = f.name
        try:
            result = save_csv(df, path)
            assert result['status'] == 'ok'
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_save_csv_returns_path(self):
        """반환 dict의 'path' 키가 저장된 파일 경로여야 한다."""
        df = results_to_dataframe([_make_result()])
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            path = f.name
        try:
            result = save_csv(df, path)
            assert result['path'] == path
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_save_csv_file_exists_after_save(self):
        """저장 후 파일이 존재해야 한다."""
        df = results_to_dataframe([_make_result()])
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            path = f.name
        try:
            save_csv(df, path)
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_save_csv_readable_back(self):
        """저장된 CSV를 다시 읽으면 행 수가 동일해야 한다."""
        results = [_make_result(trade_count=i) for i in range(3)]
        df = results_to_dataframe(results)
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            path = f.name
        try:
            save_csv(df, path)
            df_read = pd.read_csv(path)
            assert len(df_read) == 3
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_save_csv_error_on_invalid_path(self):
        """존재하지 않는 디렉토리에 저장하면 status가 'error'여야 한다."""
        df = results_to_dataframe([_make_result()])
        result = save_csv(df, '/nonexistent_dir_xyz/out.csv')
        assert result['status'] == 'error'


# ============================================================
# TestSummaryStats
# ============================================================

class TestSummaryStats:
    """summary_stats 함수 단위 테스트."""

    def _make_df(self):
        results = [
            _make_result(trade_count=10, win_rate=0.6, cagr=0.10, mdd_pct=0.05, total_profit=100000, tpi=1.0),
            _make_result(trade_count=20, win_rate=0.7, cagr=0.20, mdd_pct=0.10, total_profit=200000, tpi=2.0),
            _make_result(trade_count=30, win_rate=0.8, cagr=0.30, mdd_pct=0.15, total_profit=300000, tpi=3.0),
        ]
        return results_to_dataframe(results)

    def test_summary_stats_returns_dict(self):
        """summary_stats는 dict를 반환해야 한다."""
        df = self._make_df()
        stats = summary_stats(df)
        assert isinstance(stats, dict)

    def test_summary_stats_contains_mean_cagr(self):
        """mean_cagr 키가 있어야 한다."""
        df = self._make_df()
        stats = summary_stats(df)
        assert 'mean_cagr' in stats

    def test_summary_stats_contains_median_cagr(self):
        """median_cagr 키가 있어야 한다."""
        df = self._make_df()
        stats = summary_stats(df)
        assert 'median_cagr' in stats

    def test_summary_stats_contains_best_cagr(self):
        """best_cagr 키가 있어야 한다."""
        df = self._make_df()
        stats = summary_stats(df)
        assert 'best_cagr' in stats

    def test_summary_stats_contains_worst_cagr(self):
        """worst_cagr 키가 있어야 한다."""
        df = self._make_df()
        stats = summary_stats(df)
        assert 'worst_cagr' in stats

    def test_summary_stats_mean_cagr_correct(self):
        """mean_cagr 값이 정확해야 한다."""
        df = self._make_df()
        stats = summary_stats(df)
        assert abs(stats['mean_cagr'] - 0.20) < 1e-9

    def test_summary_stats_best_cagr_correct(self):
        """best_cagr은 cagr 최댓값이어야 한다."""
        df = self._make_df()
        stats = summary_stats(df)
        assert abs(stats['best_cagr'] - 0.30) < 1e-9

    def test_summary_stats_worst_cagr_correct(self):
        """worst_cagr은 cagr 최솟값이어야 한다."""
        df = self._make_df()
        stats = summary_stats(df)
        assert abs(stats['worst_cagr'] - 0.10) < 1e-9

    def test_summary_stats_empty_dataframe(self):
        """빈 DataFrame은 예외 없이 dict를 반환해야 한다."""
        df = pd.DataFrame()
        stats = summary_stats(df)
        assert isinstance(stats, dict)
