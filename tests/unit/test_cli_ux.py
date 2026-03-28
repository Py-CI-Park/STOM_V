"""US-301: CLI UX 테스트 — --version, --verbose, --quiet, --dry-run"""
import subprocess, sys, os, json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable
sys.path.insert(0, PROJECT_ROOT)

class TestVersion:
    def test_version_flag_exits_zero(self):
        result = subprocess.run([PYTHON, STOM_BACKTEST, '--version'], capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_version_output_contains_version_string(self):
        result = subprocess.run([PYTHON, STOM_BACKTEST, '--version'], capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        output = result.stdout.strip()
        assert 'STOM' in output or '2.51' in output or '.' in output

class TestVerboseQuiet:
    def test_verbose_default_is_true(self):
        from cli.config import parse_args
        config = parse_args(['--buy', 'A', '--sell', 'B', '--start', '20250101', '--end', '20250131'])
        assert config.verbose is True

    def test_quiet_sets_verbose_false(self):
        from cli.config import parse_args
        config = parse_args(['--buy', 'A', '--sell', 'B', '--start', '20250101', '--end', '20250131', '--quiet'])
        assert config.verbose is False

    def test_config_has_verbose_field(self):
        from cli.config import BacktestConfig
        config = BacktestConfig()
        assert hasattr(config, 'verbose')
        assert config.verbose is True

class TestDryRun:
    def test_dry_run_flag_parsed(self):
        from cli.config import parse_args
        config = parse_args(['--buy', 'A', '--sell', 'B', '--start', '20250101', '--end', '20250131', '--dry-run'])
        assert config.dry_run is True

    def test_dry_run_default_is_false(self):
        from cli.config import parse_args
        config = parse_args(['--buy', 'A', '--sell', 'B', '--start', '20250101', '--end', '20250131'])
        assert config.dry_run is False

    def test_config_has_dry_run_field(self):
        from cli.config import BacktestConfig
        config = BacktestConfig()
        assert hasattr(config, 'dry_run')
        assert config.dry_run is False

    def test_dry_run_e2e_exits_zero(self):
        """--dry-run은 검증만 수행하고 exit 0으로 종료해야 한다."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--buy', 'Min_B_Study_251227', '--sell', 'Min_S_Study_251227',
             '--start', '20250101', '--end', '20250131', '--dry-run'],
            capture_output=True, text=True, timeout=15, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_dry_run_e2e_outputs_config_json(self):
        """--dry-run은 설정 JSON을 출력해야 한다."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, '--buy', 'Min_B_Study_251227', '--sell', 'Min_S_Study_251227',
             '--start', '20250101', '--end', '20250131', '--dry-run'],
            capture_output=True, text=True, timeout=15, cwd=PROJECT_ROOT)
        parsed = json.loads(result.stdout)
        assert 'status' in parsed
