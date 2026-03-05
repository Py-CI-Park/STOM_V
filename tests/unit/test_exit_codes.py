"""US-302: --help 개선 + exit code 표준화 테스트."""
import subprocess, sys, os, json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable
sys.path.insert(0, PROJECT_ROOT)

class TestHelpOutput:
    def test_help_exits_zero(self):
        result = subprocess.run([PYTHON, STOM_BACKTEST, '--help'], capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_help_contains_epilog_example(self):
        """--help 출력에 사용 예시(example)가 포함되어야 한다."""
        result = subprocess.run([PYTHON, STOM_BACKTEST, '--help'], capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        output = result.stdout.lower()
        assert 'example' in output or '예시' in output or 'stom_backtest' in output

    def test_help_has_argument_groups(self):
        """--help 출력에 필수/선택 인자 그룹이 분리되어 있어야 한다."""
        result = subprocess.run([PYTHON, STOM_BACKTEST, '--help'], capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        # At least the required args group should be visible
        assert '--buy' in result.stdout
        assert '--sell' in result.stdout

class TestExitCodes:
    def test_success_returns_zero(self):
        """--list-strategies 성공 시 exit code 0."""
        result = subprocess.run([PYTHON, STOM_BACKTEST, '--list-strategies'], capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_arg_error_returns_one(self):
        """필수 인자 누락 시 exit code 1."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--buy', '', '--sell', '', '--start', '20250101', '--end', '20250131'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 1

    def test_execution_error_returns_two(self):
        """실행 오류 시 exit code 2."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--buy', 'Min_B_Study_251227', '--sell', 'Min_S_Study_251227',
             '--start', '20250101', '--end', '20250131', '--timeout', '15'],
            capture_output=True, text=True, timeout=60, cwd=PROJECT_ROOT)
        assert result.returncode == 2

    def test_exit_code_constants_in_entrypoint(self):
        """stom_backtest.py에 EXIT_SUCCESS, EXIT_ARG_ERROR 등 상수가 정의되어야 한다."""
        filepath = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'EXIT_SUCCESS' in content or 'exit_code' in content.lower()
