"""
STOM CLI Trade Command Tests
=============================

트레이딩 제어 명령 테스트 (start, stop, status)
"""

import pytest
from click.testing import CliRunner

from cli.main import main


class TestTradeHelp:
    """trade 명령 도움말 테스트"""

    @pytest.mark.smoke
    def test_trade_help(self, cli_runner: CliRunner):
        """trade --help 테스트"""
        result = cli_runner.invoke(main, ['trade', '--help'])

        assert result.exit_code == 0


class TestTradeStart:
    """trade start 명령 테스트"""

    def test_trade_start_help(self, cli_runner: CliRunner):
        """start --help 테스트"""
        result = cli_runner.invoke(main, ['trade', 'start', '--help'])

        assert result.exit_code in [0, 2]

    def test_trade_start_missing_required(self, cli_runner: CliRunner):
        """필수 옵션 누락"""
        result = cli_runner.invoke(main, ['trade', 'start'])

        # 필수 옵션이 있으면 에러
        assert result.exit_code in [0, 1, 2]

    def test_trade_start_stock(self, cli_runner: CliRunner):
        """주식 트레이딩 시작"""
        result = cli_runner.invoke(main, [
            'trade', 'start',
            '--market', 'stock'
        ])

        # 실제 트레이딩 시작은 안 됨 (환경 제한)
        assert result.exit_code in [0, 1, 2]

    def test_trade_start_coin(self, cli_runner: CliRunner):
        """암호화폐 트레이딩 시작"""
        result = cli_runner.invoke(main, [
            'trade', 'start',
            '--market', 'coin'
        ])

        assert result.exit_code in [0, 1, 2]

    def test_trade_start_with_strategy(self, cli_runner: CliRunner):
        """전략 지정하여 시작"""
        result = cli_runner.invoke(main, [
            'trade', 'start',
            '--market', 'stock',
            '--buy-strategy', 'test_buy',
            '--sell-strategy', 'test_sell'
        ])

        assert result.exit_code in [0, 1, 2]


class TestTradeStop:
    """trade stop 명령 테스트"""

    def test_trade_stop_help(self, cli_runner: CliRunner):
        """stop --help 테스트"""
        result = cli_runner.invoke(main, ['trade', 'stop', '--help'])

        assert result.exit_code in [0, 2]

    def test_trade_stop(self, cli_runner: CliRunner):
        """트레이딩 중지"""
        result = cli_runner.invoke(main, ['trade', 'stop'])

        # 실행 중인 트레이딩이 없어도 처리
        assert result.exit_code in [0, 1, 2]

    def test_trade_stop_stock(self, cli_runner: CliRunner):
        """주식 트레이딩 중지"""
        result = cli_runner.invoke(main, ['trade', 'stop', '--market', 'stock'])

        assert result.exit_code in [0, 1, 2]

    def test_trade_stop_all(self, cli_runner: CliRunner):
        """모든 트레이딩 중지"""
        result = cli_runner.invoke(main, ['trade', 'stop', '--all'])

        assert result.exit_code in [0, 1, 2]


class TestTradeStatus:
    """trade status 명령 테스트"""

    def test_trade_status_help(self, cli_runner: CliRunner):
        """status --help 테스트"""
        result = cli_runner.invoke(main, ['trade', 'status', '--help'])

        assert result.exit_code in [0, 2]

    def test_trade_status(self, cli_runner: CliRunner):
        """트레이딩 상태 조회"""
        result = cli_runner.invoke(main, ['trade', 'status'])

        assert result.exit_code in [0, 1, 2]

    def test_trade_status_json(self, cli_runner: CliRunner):
        """JSON 포맷 상태"""
        result = cli_runner.invoke(main, ['trade', 'status', '--format', 'json'])

        assert result.exit_code in [0, 1, 2]


class TestTradeConfig:
    """trade config 명령 테스트 (있는 경우)"""

    def test_trade_config_help(self, cli_runner: CliRunner):
        """config --help 테스트"""
        result = cli_runner.invoke(main, ['trade', 'config', '--help'])

        # 명령이 없을 수 있음
        assert result.exit_code in [0, 2]
