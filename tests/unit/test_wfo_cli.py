"""US-007: stom_backtest wfo 서브커맨드 테스트."""
import subprocess
import sys
import os
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable


class TestWfoHelp:
    def test_help_exits_zero(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'wfo', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert '--train-window-days' in result.stdout
        assert '--test-window-days' in result.stdout
        assert '--dry-run' in result.stdout


class TestWfoDryRun:
    def test_dry_run_outputs_windows(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'wfo',
             '--start', '20240101', '--end', '20251231',
             '--train-window-days', '180', '--test-window-days', '60',
             '--dry-run'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data['status'] == 'dry-run'
        assert data['round_count'] > 0
        assert isinstance(data['windows'], list)
        assert data['train_window_days'] == 180
        assert data['test_window_days'] == 60

    def test_step_days_defaults_to_test_window_days(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'wfo',
             '--start', '20240101', '--end', '20251231',
             '--train-window-days', '180', '--test-window-days', '60',
             '--dry-run'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        assert data['step_days'] == 60  # test-window-days 기본값

    def test_custom_step_days(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'wfo',
             '--start', '20240101', '--end', '20251231',
             '--train-window-days', '180', '--test-window-days', '60',
             '--step-days', '30',
             '--dry-run'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        assert data['step_days'] == 30

    def test_purge_embargo_passed_through(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'wfo',
             '--start', '20240101', '--end', '20251231',
             '--train-window-days', '180', '--test-window-days', '60',
             '--purge-days', '5', '--embargo-days', '3',
             '--dry-run'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        assert data['purge_days'] == 5
        assert data['embargo_days'] == 3

    def test_dry_run_no_buy_sell_ok(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'wfo',
             '--start', '20240101', '--end', '20251231',
             '--train-window-days', '180', '--test-window-days', '60',
             '--dry-run'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_no_dry_run_without_buy_sell_fails(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'wfo',
             '--start', '20240101', '--end', '20251231',
             '--train-window-days', '180', '--test-window-days', '60'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 1
