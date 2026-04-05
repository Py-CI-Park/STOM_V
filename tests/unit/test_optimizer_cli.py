"""US-005: stom_backtest optimize 서브커맨드 테스트."""
import subprocess
import sys
import os
import json
import tempfile
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable


class TestOptimizeHelp:
    def test_help_exits_zero(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'optimize', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert '--param-space' in result.stdout
        assert '--method' in result.stdout

    def test_help_no_unicode_error(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'optimize', '--help'],
            capture_output=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0


class TestOptimizeValidation:
    def test_missing_param_space_file_returns_error(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'optimize',
             '--buy', 'TestBuy', '--sell', 'TestSell',
             '--start', '20250101', '--end', '20250131',
             '--param-space', '/nonexistent/params.json'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 1

    def test_invalid_json_param_space_returns_error(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json{{{')
            f.flush()
            tmp_path = f.name
        try:
            result = subprocess.run(
                [PYTHON, STOM_BACKTEST, 'optimize',
                 '--buy', 'TestBuy', '--sell', 'TestSell',
                 '--start', '20250101', '--end', '20250131',
                 '--param-space', tmp_path],
                capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
            assert result.returncode == 1
        finally:
            os.unlink(tmp_path)

    def test_empty_param_space_returns_error(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({}, f)
            f.flush()
            tmp_path = f.name
        try:
            result = subprocess.run(
                [PYTHON, STOM_BACKTEST, 'optimize',
                 '--buy', 'TestBuy', '--sell', 'TestSell',
                 '--start', '20250101', '--end', '20250131',
                 '--param-space', tmp_path],
                capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
            assert result.returncode == 1
        finally:
            os.unlink(tmp_path)


class TestOptimizeParserAcceptsAll:
    def test_grid_method_accepted(self):
        """argparse가 --method grid를 허용하는지 확인 (실행은 하지 않음)."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'optimize', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert 'grid' in result.stdout
        assert 'random' in result.stdout
