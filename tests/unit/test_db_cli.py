"""US-004: stom_backtest db 서브커맨드 테스트."""
import subprocess
import sys
import os
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable


class TestDbHelp:
    def test_db_help_exits_zero(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'db', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert 'check' in result.stdout or 'db' in result.stdout

    def test_db_check_help(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'db', 'check', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_db_ensure_help(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'db', 'ensure', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_db_restore_help(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'db', 'restore', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0


class TestDbCheckJson:
    def test_check_json_has_databases(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'db', 'check', '--format', 'json'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert 'databases' in data
        assert 'strategy' in data['databases']
        assert 'backtest' in data['databases']
        assert 'stock_tick_back' in data['databases']

    def test_check_json_each_db_has_status(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'db', 'check', '--format', 'json'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        for name, info in data['databases'].items():
            assert 'exists' in info
            assert 'size_bytes' in info
            assert 'path' in info

    def test_check_tick_db_has_detail(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'db', 'check', '--format', 'json'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        tick = data['databases']['stock_tick_back']
        assert 'detail' in tick
        assert tick['detail']['status'] in ('ok', 'empty', 'missing', 'error')


class TestDbCheckText:
    def test_check_text_readable(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'db', 'check', '--format', 'text'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert 'strategy' in result.stdout.lower() or 'Database' in result.stdout


class TestDbEnsure:
    def test_ensure_tick_returns_json(self):
        """ensure는 결과를 JSON으로 반환한다 (실제 복구 여부는 환경에 따라 다름)."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'db', 'ensure', '--timeframe', 'tick'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        assert data['status'] in ('ok', 'linked', 'error')
        assert 'message' in data
