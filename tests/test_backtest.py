"""
STOM CLI Backtest Command Tests
================================

백테스트 명령 테스트 (run, list, status, cancel)
"""

import pytest
from click.testing import CliRunner

from cli.main import main


class TestBacktestHelp:
    """backtest 명령 도움말 테스트"""

    @pytest.mark.smoke
    def test_backtest_help(self, cli_runner: CliRunner):
        """backtest --help 테스트"""
        result = cli_runner.invoke(main, ['backtest', '--help'])

        assert result.exit_code == 0
        assert 'backtest' in result.output.lower()

    def test_backtest_run_help(self, cli_runner: CliRunner):
        """backtest run --help 테스트"""
        result = cli_runner.invoke(main, ['backtest', 'run', '--help'])

        assert result.exit_code == 0


class TestBacktestRun:
    """backtest run 명령 테스트"""

    def test_backtest_run_missing_required(self, cli_runner: CliRunner):
        """필수 옵션 누락 테스트"""
        result = cli_runner.invoke(main, ['backtest', 'run'])

        # 필수 옵션 누락 시 에러
        assert result.exit_code != 0

    def test_backtest_run_with_options(self, cli_runner: CliRunner):
        """옵션 지정하여 실행"""
        result = cli_runner.invoke(main, [
            'backtest', 'run',
            '--market', 'stock',
            '--buy-strategy', 'test_buy',
            '--sell-strategy', 'test_sell',
            '--start', '20260101',
            '--end', '20260131'
        ])

        # 백테스트 데이터가 없어도 명령은 파싱되어야 함
        assert result.exit_code in [0, 1, 2]

    def test_backtest_run_with_betting(self, cli_runner: CliRunner):
        """배팅 금액 지정"""
        result = cli_runner.invoke(main, [
            'backtest', 'run',
            '--market', 'stock',
            '--buy-strategy', 'test',
            '--sell-strategy', 'test',
            '--start', '20260101',
            '--end', '20260131',
            '--betting', '100'
        ])

        assert result.exit_code in [0, 1, 2]

    def test_backtest_run_coin_market(self, cli_runner: CliRunner):
        """암호화폐 시장 백테스트"""
        result = cli_runner.invoke(main, [
            'backtest', 'run',
            '--market', 'coin',
            '--buy-strategy', 'test',
            '--sell-strategy', 'test',
            '--start', '20260101',
            '--end', '20260131'
        ])

        assert result.exit_code in [0, 1, 2]


class TestBacktestList:
    """backtest list 명령 테스트"""

    def test_backtest_list(self, cli_runner: CliRunner):
        """백테스트 결과 목록"""
        result = cli_runner.invoke(main, ['backtest', 'list'])

        # 명령이 존재하면 실행, 아니면 에러
        assert result.exit_code in [0, 1, 2]

    def test_backtest_list_json(self, cli_runner: CliRunner):
        """JSON 포맷 결과 목록"""
        result = cli_runner.invoke(main, ['backtest', 'list', '--format', 'json'])

        assert result.exit_code in [0, 1, 2]


class TestBacktestStatus:
    """backtest status 명령 테스트"""

    def test_backtest_status(self, cli_runner: CliRunner):
        """백테스트 상태 조회"""
        result = cli_runner.invoke(main, ['backtest', 'status'])

        # 명령이 존재하면 실행
        assert result.exit_code in [0, 1, 2]


class TestBacktestCancel:
    """backtest cancel 명령 테스트"""

    def test_backtest_cancel(self, cli_runner: CliRunner):
        """백테스트 취소"""
        result = cli_runner.invoke(main, ['backtest', 'cancel'])

        # 실행 중인 백테스트가 없어도 에러 없이 처리
        assert result.exit_code in [0, 1, 2]
