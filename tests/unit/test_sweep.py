"""cli/sweep.py 단위 테스트.

대상: generate_combinations, generate_rolling_windows, run_sweep, run_rolling
"""
import os
import sys
from unittest.mock import patch, MagicMock, call

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.config import BacktestConfig
from cli.sweep import (
    generate_combinations,
    generate_rolling_windows,
    run_sweep,
    run_rolling,
)


# ============================================================
# TestGenerateCombinations
# ============================================================

class TestGenerateCombinations:
    """generate_combinations 함수 단위 테스트."""

    def test_empty_params_returns_one_empty_combo(self):
        """파라미터가 없으면 빈 dict 하나를 포함한 리스트를 반환해야 한다."""
        result = generate_combinations({})
        assert result == [{}]

    def test_single_param_single_value(self):
        """단일 파라미터, 단일 값이면 조합 1개를 반환해야 한다."""
        result = generate_combinations({'avg_time': [60]})
        assert result == [{'avg_time': 60}]

    def test_single_param_multiple_values(self):
        """단일 파라미터, 복수 값이면 해당 값 개수만큼 조합을 반환해야 한다."""
        result = generate_combinations({'avg_time': [60, 120, 180]})
        assert len(result) == 3
        assert {'avg_time': 60} in result
        assert {'avg_time': 120} in result
        assert {'avg_time': 180} in result

    def test_two_params_cartesian_product(self):
        """두 파라미터의 데카르트 곱을 반환해야 한다."""
        result = generate_combinations({'avg_time': [60, 120], 'betting': ['1', '3']})
        assert len(result) == 4
        assert {'avg_time': 60, 'betting': '1'} in result
        assert {'avg_time': 60, 'betting': '3'} in result
        assert {'avg_time': 120, 'betting': '1'} in result
        assert {'avg_time': 120, 'betting': '3'} in result

    def test_three_params_count(self):
        """세 파라미터의 조합 수는 각 값 수의 곱이어야 한다."""
        result = generate_combinations({
            'avg_time': [60, 120],
            'betting': ['1', '3'],
            'engine_count': [2, 4],
        })
        assert len(result) == 8

    def test_each_combo_is_dict(self):
        """각 조합은 dict 타입이어야 한다."""
        result = generate_combinations({'avg_time': [60, 120]})
        for combo in result:
            assert isinstance(combo, dict)

    def test_does_not_mutate_input(self):
        """입력 sweep_params를 변경하지 않아야 한다."""
        params = {'avg_time': [60, 120], 'betting': ['1']}
        original = {'avg_time': [60, 120], 'betting': ['1']}
        generate_combinations(params)
        assert params == original


# ============================================================
# TestGenerateRollingWindows
# ============================================================

class TestGenerateRollingWindows:
    """generate_rolling_windows 함수 단위 테스트."""

    def test_basic_window_returns_tuples(self):
        """반환값은 (start, end) int 튜플 리스트여야 한다."""
        windows = generate_rolling_windows(20240101, 20240201, 30, 30)
        assert len(windows) >= 1
        for w in windows:
            assert isinstance(w, tuple)
            assert len(w) == 2

    def test_first_window_starts_at_start_date(self):
        """첫 번째 윈도우의 시작은 start_date여야 한다."""
        windows = generate_rolling_windows(20240101, 20240601, 30, 7)
        assert windows[0][0] == 20240101

    def test_window_length_is_window_days(self):
        """각 윈도우의 길이가 window_days와 일치해야 한다."""
        from datetime import datetime
        windows = generate_rolling_windows(20240101, 20240601, 30, 30)
        for start_int, end_int in windows:
            start = datetime.strptime(str(start_int), '%Y%m%d')
            end = datetime.strptime(str(end_int), '%Y%m%d')
            assert (end - start).days == 29  # window_days - 1 (inclusive end)

    def test_step_controls_spacing(self):
        """step_days가 윈도우 시작 간격을 결정해야 한다."""
        from datetime import datetime
        windows = generate_rolling_windows(20240101, 20240401, 30, 7)
        assert len(windows) >= 2
        start1 = datetime.strptime(str(windows[0][0]), '%Y%m%d')
        start2 = datetime.strptime(str(windows[1][0]), '%Y%m%d')
        assert (start2 - start1).days == 7

    def test_windows_do_not_exceed_end_date(self):
        """윈도우 시작일이 end_date를 초과하지 않아야 한다."""
        windows = generate_rolling_windows(20240101, 20240601, 30, 7)
        for start_int, _ in windows:
            assert start_int <= 20240601

    def test_single_window_when_range_equals_window(self):
        """날짜 범위가 window_days와 같으면 최소 1개 윈도우를 반환해야 한다."""
        windows = generate_rolling_windows(20240101, 20240130, 30, 30)
        assert len(windows) >= 1

    def test_returns_list(self):
        """반환 타입은 list여야 한다."""
        windows = generate_rolling_windows(20240101, 20240601, 30, 7)
        assert isinstance(windows, list)


# ============================================================
# TestRunSweep
# ============================================================

class TestRunSweep:
    """run_sweep 함수 단위 테스트."""

    def _make_config(self):
        return BacktestConfig(
            buy_strategy='BuyA',
            sell_strategy='SellA',
            start_date=20240101,
            end_date=20240131,
            avg_time=60,
            betting='1',
        )

    def _mock_result(self, **kwargs):
        base = {
            'status': 'success',
            'message': '완료',
            'metrics': {
                'trade_count': 10,
                'win_rate': 0.6,
                'cagr': 0.15,
                'mdd_pct': 0.05,
                'total_profit_krw': 100000,
                'tpi': 1.2,
            },
        }
        base.update(kwargs)
        return base

    def test_run_sweep_returns_list(self):
        """run_sweep은 리스트를 반환해야 한다."""
        config = self._make_config()
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()):
            results = run_sweep(config, {'avg_time': [60, 120]})
        assert isinstance(results, list)

    def test_run_sweep_calls_run_backtest_for_each_combo(self):
        """조합 수만큼 run_backtest가 호출되어야 한다."""
        config = self._make_config()
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()) as mock_rb:
            run_sweep(config, {'avg_time': [60, 120], 'betting': ['1', '3']})
        assert mock_rb.call_count == 4  # 2x2

    def test_run_sweep_result_contains_params_key(self):
        """각 결과 dict에 'params' 키가 있어야 한다."""
        config = self._make_config()
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()):
            results = run_sweep(config, {'avg_time': [60, 120]})
        for r in results:
            assert 'params' in r

    def test_run_sweep_does_not_mutate_base_config(self):
        """base_config를 변경하지 않아야 한다 (불변성)."""
        config = self._make_config()
        original_avg_time = config.avg_time
        original_betting = config.betting
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()):
            run_sweep(config, {'avg_time': [999], 'betting': ['99']})
        assert config.avg_time == original_avg_time
        assert config.betting == original_betting

    def test_run_sweep_progress_callback_called(self):
        """on_progress 콜백이 조합 수만큼 호출되어야 한다."""
        config = self._make_config()
        callback = MagicMock()
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()):
            run_sweep(config, {'avg_time': [60, 120]}, on_progress=callback)
        assert callback.call_count == 2

    def test_run_sweep_empty_sweep_params(self):
        """sweep_params가 비어있으면 단일 결과를 반환해야 한다."""
        config = self._make_config()
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()) as mock_rb:
            results = run_sweep(config, {})
        assert len(results) == 1
        assert mock_rb.call_count == 1


# ============================================================
# TestRunRolling
# ============================================================

class TestRunRolling:
    """run_rolling 함수 단위 테스트."""

    def _make_config(self):
        return BacktestConfig(
            buy_strategy='BuyA',
            sell_strategy='SellA',
            start_date=20240101,
            end_date=20240601,
            avg_time=60,
            betting='1',
        )

    def _mock_result(self):
        return {
            'status': 'success',
            'message': '완료',
            'metrics': {
                'trade_count': 5,
                'win_rate': 0.5,
                'cagr': 0.10,
                'mdd_pct': 0.03,
                'total_profit_krw': 50000,
                'tpi': 1.0,
            },
        }

    def test_run_rolling_returns_list(self):
        """run_rolling은 리스트를 반환해야 한다."""
        config = self._make_config()
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()):
            results = run_rolling(config, window_days=30, step_days=30)
        assert isinstance(results, list)

    def test_run_rolling_result_contains_window_key(self):
        """각 결과 dict에 'window' 키가 있어야 한다."""
        config = self._make_config()
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()):
            results = run_rolling(config, window_days=30, step_days=30)
        for r in results:
            assert 'window' in r

    def test_run_rolling_window_is_tuple_of_ints(self):
        """'window' 값은 (int, int) 튜플이어야 한다."""
        config = self._make_config()
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()):
            results = run_rolling(config, window_days=30, step_days=30)
        for r in results:
            w = r['window']
            assert isinstance(w, tuple)
            assert len(w) == 2
            assert isinstance(w[0], int)
            assert isinstance(w[1], int)

    def test_run_rolling_does_not_mutate_base_config(self):
        """base_config를 변경하지 않아야 한다 (불변성)."""
        config = self._make_config()
        original_start = config.start_date
        original_end = config.end_date
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()):
            run_rolling(config, window_days=30, step_days=30)
        assert config.start_date == original_start
        assert config.end_date == original_end

    def test_run_rolling_calls_run_backtest_per_window(self):
        """생성된 윈도우 수만큼 run_backtest가 호출되어야 한다."""
        config = self._make_config()
        windows = generate_rolling_windows(
            config.start_date, config.end_date, 30, 30
        )
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()) as mock_rb:
            run_rolling(config, window_days=30, step_days=30)
        assert mock_rb.call_count == len(windows)

    def test_run_rolling_progress_callback_called(self):
        """on_progress 콜백이 윈도우 수만큼 호출되어야 한다."""
        config = self._make_config()
        callback = MagicMock()
        with patch('cli.sweep.run_backtest', return_value=self._mock_result()):
            results = run_rolling(config, window_days=30, step_days=30, on_progress=callback)
        assert callback.call_count == len(results)
