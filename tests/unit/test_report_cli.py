"""US-010: stom_backtest report 서브커맨드 테스트."""
import subprocess
import sys
import os
import json
import tempfile
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable


class TestReportHelp:
    def test_report_help_exits_zero(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'report', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert '--source' in result.stdout
        assert '--summary' in result.stdout


class TestReportBacktestJson:
    def test_backtest_json_has_data(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'report', '--source', 'backtest', '--format', 'json'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data['status'] == 'ok'
        assert 'row_count' in data
        assert 'data' in data

    def test_backtest_json_with_limit(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'report', '--source', 'backtest',
             '--format', 'json', '--limit', '5'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data['row_count'] <= 5

    def test_backtest_summary_json(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'report', '--source', 'backtest',
             '--format', 'json', '--summary'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data['status'] == 'ok'
        assert 'row_count' in data


class TestReportCsv:
    def test_backtest_csv_creates_file(self):
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            tmp_path = f.name
        try:
            result = subprocess.run(
                [PYTHON, STOM_BACKTEST, 'report', '--source', 'backtest',
                 '--format', 'csv', '-o', tmp_path, '--limit', '5'],
                capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
            assert result.returncode == 0
            assert os.path.exists(tmp_path)
            assert os.path.getsize(tmp_path) > 0
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_csv_without_output_file_fails(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'report', '--source', 'backtest', '--format', 'csv'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 1
