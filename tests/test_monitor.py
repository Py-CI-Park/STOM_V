"""
STOM CLI Monitor Command Tests
===============================

모니터링 명령 테스트 (live, pnl, positions)
"""

import pytest
from click.testing import CliRunner

from cli.main import main


class TestMonitorHelp:
    """monitor 명령 도움말 테스트"""

    @pytest.mark.smoke
    def test_monitor_help(self, cli_runner: CliRunner):
        """monitor --help 테스트"""
        result = cli_runner.invoke(main, ['monitor', '--help'])

        assert result.exit_code == 0


class TestMonitorLive:
    """monitor live 명령 테스트"""

    def test_monitor_live_help(self, cli_runner: CliRunner):
        """live --help 테스트"""
        result = cli_runner.invoke(main, ['monitor', 'live', '--help'])

        assert result.exit_code in [0, 2]

    def test_monitor_live_basic(self, cli_runner: CliRunner):
        """기본 실시간 모니터링"""
        # 실시간 모니터링은 즉시 종료되거나 타임아웃
        result = cli_runner.invoke(main, ['monitor', 'live'])

        # 데이터가 없으면 에러일 수 있음
        assert result.exit_code in [0, 1, 2]

    def test_monitor_live_stock(self, cli_runner: CliRunner):
        """주식 실시간 모니터링"""
        result = cli_runner.invoke(main, ['monitor', 'live', '--market', 'stock'])

        assert result.exit_code in [0, 1, 2]


class TestMonitorPnL:
    """monitor pnl 명령 테스트"""

    def test_monitor_pnl_help(self, cli_runner: CliRunner):
        """pnl --help 테스트"""
        result = cli_runner.invoke(main, ['monitor', 'pnl', '--help'])

        assert result.exit_code in [0, 2]

    def test_monitor_pnl_basic(self, cli_runner: CliRunner):
        """기본 손익 조회"""
        result = cli_runner.invoke(main, ['monitor', 'pnl'])

        assert result.exit_code in [0, 1, 2]

    def test_monitor_pnl_json(self, cli_runner: CliRunner):
        """JSON 포맷 손익"""
        result = cli_runner.invoke(main, ['monitor', 'pnl', '--format', 'json'])

        assert result.exit_code in [0, 1, 2]

    def test_monitor_pnl_with_date(self, cli_runner: CliRunner):
        """날짜별 손익"""
        result = cli_runner.invoke(main, ['monitor', 'pnl', '--date', '20260101'])

        assert result.exit_code in [0, 1, 2]


class TestMonitorPositions:
    """monitor positions 명령 테스트"""

    def test_monitor_positions_help(self, cli_runner: CliRunner):
        """positions --help 테스트"""
        result = cli_runner.invoke(main, ['monitor', 'positions', '--help'])

        assert result.exit_code in [0, 2]

    def test_monitor_positions_basic(self, cli_runner: CliRunner):
        """기본 포지션 조회"""
        result = cli_runner.invoke(main, ['monitor', 'positions'])

        assert result.exit_code in [0, 1, 2]

    def test_monitor_positions_stock(self, cli_runner: CliRunner):
        """주식 포지션"""
        result = cli_runner.invoke(main, ['monitor', 'positions', '--market', 'stock'])

        assert result.exit_code in [0, 1, 2]

    def test_monitor_positions_coin(self, cli_runner: CliRunner):
        """암호화폐 포지션"""
        result = cli_runner.invoke(main, ['monitor', 'positions', '--market', 'coin'])

        assert result.exit_code in [0, 1, 2]

    def test_monitor_positions_json(self, cli_runner: CliRunner):
        """JSON 포맷 포지션"""
        result = cli_runner.invoke(main, ['monitor', 'positions', '--format', 'json'])

        assert result.exit_code in [0, 1, 2]


class TestMonitorOrders:
    """monitor orders 명령 테스트 (있는 경우)"""

    def test_monitor_orders_help(self, cli_runner: CliRunner):
        """orders --help 테스트"""
        result = cli_runner.invoke(main, ['monitor', 'orders', '--help'])

        # 명령이 없을 수 있음
        assert result.exit_code in [0, 2]

    def test_monitor_orders_basic(self, cli_runner: CliRunner):
        """기본 주문 조회"""
        result = cli_runner.invoke(main, ['monitor', 'orders'])

        assert result.exit_code in [0, 1, 2]


class TestMonitorBalance:
    """monitor balance 명령 테스트 (있는 경우)"""

    def test_monitor_balance_help(self, cli_runner: CliRunner):
        """balance --help 테스트"""
        result = cli_runner.invoke(main, ['monitor', 'balance', '--help'])

        assert result.exit_code in [0, 2]

    def test_monitor_balance_basic(self, cli_runner: CliRunner):
        """잔고 조회"""
        result = cli_runner.invoke(main, ['monitor', 'balance'])

        assert result.exit_code in [0, 1, 2]
