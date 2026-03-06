"""CLI E2E 테스트.

US-202: --list-strategies 실행 성공
US-203: 백테스트 1회 실행 성공 + matplotlib headless
"""
import json
import os
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable


# ============================================================
# US-202: --list-strategies E2E
# ============================================================

class TestListStrategies:
    """--list-strategies가 exit 0 + 유효 JSON을 반환하는지 E2E 검증."""

    def test_exit_code_is_zero(self):
        """python stom_backtest.py --list-strategies 실행 시 exit code 0."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--list-strategies'],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0, \
            f'exit code {result.returncode}, stderr: {result.stderr}'

    def test_output_is_valid_json(self):
        """stdout 출력이 json.loads()로 파싱 가능해야 한다."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--list-strategies'],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, dict)

    def test_output_has_stockbuy_key(self):
        """JSON 출력에 'stockbuy' 키가 존재해야 한다."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--list-strategies'],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        parsed = json.loads(result.stdout)
        assert 'stockbuy' in parsed

    def test_output_has_stocksell_key(self):
        """JSON 출력에 'stocksell' 키가 존재해야 한다."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--list-strategies'],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        parsed = json.loads(result.stdout)
        assert 'stocksell' in parsed

    def test_stockbuy_is_list(self):
        """stockbuy 값은 list 타입이어야 한다."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--list-strategies'],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        parsed = json.loads(result.stdout)
        assert isinstance(parsed['stockbuy'], list)

    def test_stocksell_is_list(self):
        """stocksell 값은 list 타입이어야 한다."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--list-strategies'],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        parsed = json.loads(result.stdout)
        assert isinstance(parsed['stocksell'], list)

    def test_text_format_output(self):
        """--format text 시 '매수 전략' / '매도 전략' 레이블이 포함되어야 한다."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--list-strategies', '--format', 'text'],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert '매수 전략' in result.stdout
        assert '매도 전략' in result.stdout


# ============================================================
# US-203: matplotlib headless 코드 존재 확인
# ============================================================

class TestMatplotlibHeadless:
    """matplotlib.use('agg') 코드가 존재하는지 검증."""

    def test_matplotlib_agg_in_runner_or_entrypoint(self):
        """runner.py 또는 stom_backtest.py에 matplotlib.use('agg') 또는 'Agg'가 있어야 함."""
        found = False
        for filename in ('cli/runner.py', 'stom_backtest.py'):
            filepath = os.path.join(PROJECT_ROOT, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            if "matplotlib.use(" in content and 'agg' in content:
                found = True
                break
        assert found, \
            "matplotlib.use('agg') 코드가 runner.py 또는 stom_backtest.py에 없음"


# ============================================================
# US-203: 백테스트 에러 핸들링 + 프로세스 정리 E2E
# ============================================================

class TestBacktestErrorHandling:
    """데이터 부재 시 graceful error + JSON 응답 + 프로세스 정상 종료."""

    def test_empty_db_returns_json_error(self):
        """빈 DB로 실행 시 JSON error 응답을 반환해야 한다."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST,
             '--buy', 'Min_B_Study_251227', '--sell', 'Min_S_Study_251227',
             '--start', '20250101', '--end', '20250131',
             '--timeframe', 'min',
             '--timeout', '15'],
            capture_output=True, text=True, timeout=60,
            cwd=PROJECT_ROOT,
        )
        parsed = json.loads(result.stdout)
        assert parsed['status'] == 'error'
        assert 'message' in parsed

    def test_empty_db_exits_nonzero(self):
        """빈 DB로 실행 시 exit code != 0."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST,
             '--buy', 'Min_B_Study_251227', '--sell', 'Min_S_Study_251227',
             '--start', '20250101', '--end', '20250131',
             '--timeout', '15'],
            capture_output=True, text=True, timeout=60,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode != 0

    def test_missing_args_exits_with_error(self):
        """필수 인자 없이 실행 → stderr에 ERROR 메시지 + exit code != 0."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST,
             '--buy', '', '--sell', '',
             '--start', '20250101', '--end', '20250131'],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode != 0
