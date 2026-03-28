"""US-006: stom_backtest sweep 서브커맨드 테스트."""
import subprocess
import sys
import os
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable


class TestSweepHelp:
    def test_sweep_help_exits_zero(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'sweep', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert 'param' in result.stdout or 'rolling' in result.stdout

    def test_sweep_param_help(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'sweep', 'param', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert '--params' in result.stdout

    def test_sweep_rolling_help(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'sweep', 'rolling', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert '--window-days' in result.stdout
        assert '--dry-run' in result.stdout


class TestSweepRollingDryRun:
    def test_dry_run_outputs_windows(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'sweep', 'rolling',
             '--start', '20240101', '--end', '20241231',
             '--window-days', '90', '--step-days', '30',
             '--dry-run'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data['status'] == 'dry-run'
        assert data['window_count'] > 0
        assert isinstance(data['windows'], list)
        assert len(data['windows']) == data['window_count']

    def test_dry_run_window_is_pair(self):
        """각 윈도우는 [start_date, end_date] 형태의 2-element 리스트."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'sweep', 'rolling',
             '--start', '20240101', '--end', '20240601',
             '--window-days', '60', '--step-days', '30',
             '--dry-run'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        for w in data['windows']:
            assert isinstance(w, list) and len(w) == 2
            assert isinstance(w[0], int) and isinstance(w[1], int)

    def test_dry_run_no_buy_sell_ok(self):
        """--dry-run 시 --buy/--sell 없어도 동작."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'sweep', 'rolling',
             '--start', '20240101', '--end', '20241231',
             '--window-days', '90', '--step-days', '30',
             '--dry-run'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_no_dry_run_without_buy_sell_fails(self):
        """--dry-run 없이 --buy/--sell 미지정 시 에러."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'sweep', 'rolling',
             '--start', '20240101', '--end', '20241231',
             '--window-days', '90', '--step-days', '30'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 1
