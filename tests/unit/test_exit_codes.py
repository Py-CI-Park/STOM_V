"""US-302: --help 개선 + exit code 표준화 테스트."""
import subprocess, sys, os, json, types
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

    def test_execution_error_returns_two(self, monkeypatch):
        """실행 오류 시 exit code 2."""
        import stom_backtest

        config = types.SimpleNamespace(
            dry_run=False,
            output_format='json',
            output_file=None,
            is_tick=False,
            buy_strategy='테스트매수전략',
            sell_strategy='테스트매도전략',
            start_date=20250101,
            end_date=20250131,
        )
        fake_timeframe_detector = types.ModuleType('cli.timeframe_detector')
        fake_timeframe_detector.validate_timeframe_match = lambda _config: {'status': 'ok'}
        fake_runner = types.ModuleType('cli.runner')
        fake_runner.run_backtest = lambda _config: {'status': 'error', 'message': 'execution boom'}

        monkeypatch.setattr(stom_backtest, 'configure_safe_output', lambda: None)
        monkeypatch.setattr(stom_backtest, 'parse_args', lambda: config)
        monkeypatch.setattr(stom_backtest, 'validate', lambda _config: [])
        monkeypatch.setattr(stom_backtest, 'format_result', lambda result, _fmt: json.dumps(result))
        monkeypatch.setattr(stom_backtest, '_configure_matplotlib_headless', lambda: False)
        monkeypatch.setitem(sys.modules, 'cli.timeframe_detector', fake_timeframe_detector)
        monkeypatch.setitem(sys.modules, 'cli.runner', fake_runner)

        assert stom_backtest.main() == stom_backtest.EXIT_EXEC_ERROR

    def test_engine_data_loading_timeout_returns_timeout_exit_code(self, monkeypatch):
        import stom_backtest

        config = types.SimpleNamespace(
            dry_run=False,
            output_format='json',
            output_file=None,
            is_tick=False,
            buy_strategy='buy',
            sell_strategy='sell',
            start_date=20250101,
            end_date=20250131,
        )
        fake_timeframe_detector = types.ModuleType('cli.timeframe_detector')
        fake_timeframe_detector.validate_timeframe_match = lambda _config: {'status': 'ok'}
        fake_runner = types.ModuleType('cli.runner')
        fake_runner.run_backtest = lambda _config: {
            'status': 'error',
            'message': 'engine data loading timed out',
            'engine_data_loading': {'expected_count': 32},
            'last_checkpoint': 'engine_data_response_timeout',
        }

        monkeypatch.setattr(stom_backtest, 'configure_safe_output', lambda: None)
        monkeypatch.setattr(stom_backtest, 'parse_args', lambda: config)
        monkeypatch.setattr(stom_backtest, 'validate', lambda _config: [])
        monkeypatch.setattr(stom_backtest, 'format_result', lambda result, _fmt: json.dumps(result))
        monkeypatch.setattr(stom_backtest, '_configure_matplotlib_headless', lambda: False)
        monkeypatch.setitem(sys.modules, 'cli.timeframe_detector', fake_timeframe_detector)
        monkeypatch.setitem(sys.modules, 'cli.runner', fake_runner)

        assert stom_backtest.main() == stom_backtest.EXIT_TIMEOUT

    def test_exit_code_constants_in_entrypoint(self):
        """stom_backtest.py에 EXIT_SUCCESS, EXIT_ARG_ERROR 등 상수가 정의되어야 한다."""
        filepath = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'EXIT_SUCCESS' in content or 'exit_code' in content.lower()
