"""US-003: stom_backtest tune 서브커맨드 테스트."""
import subprocess
import sys
import os
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable


class TestTuneHelp:
    def test_help_exits_zero(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'tune', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert 'tune' in result.stdout.lower() or '--engines' in result.stdout

    def test_help_no_unicode_error(self):
        """CP949 환경에서도 --help crash 없음."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'tune', '--help'],
            capture_output=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0


class TestTuneJson:
    def test_json_output_has_required_keys(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'tune', '--format', 'json'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert 'system' in data
        assert 'cpu_count' in data['system']
        assert 'memory_total_gb' in data['system']
        assert 'recommendation' in data
        assert 'recommended' in data['recommendation']
        assert 'memory_per_engine_mb' in data

    def test_json_output_with_engines_has_resource_check(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'tune', '--format', 'json', '--engines', '8', '--timeframe', 'tick'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert 'resource_check' in data
        assert data['resource_check']['status'] in ('ok', 'warning')

    def test_total_codes_adjusts_recommendation(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'tune', '--format', 'json', '--total-codes', '1'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data['recommendation']['recommended'] <= 1


class TestTuneText:
    def test_text_output_readable(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'tune', '--format', 'text'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert 'CPU' in result.stdout
        assert 'Recommended' in result.stdout

    def test_text_output_with_engines(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'tune', '--format', 'text', '--engines', '4'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert 'Resource check' in result.stdout
