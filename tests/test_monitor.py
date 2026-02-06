"""Tests for `stom monitor` command group."""

import pytest
from click.testing import CliRunner

from cli.main import main


class TestMonitorHelp:
    @pytest.mark.smoke
    def test_monitor_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["monitor", "--help"])
        assert result.exit_code == 0


class TestMonitorLive:
    def test_monitor_live_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["monitor", "live", "--help"])
        assert result.exit_code == 0

    def test_monitor_live_requires_type(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["monitor", "live"])
        assert result.exit_code != 0

    def test_monitor_live_stock_once(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            ["monitor", "live", "--type", "stock", "--count", "1", "--interval", "1"],
        )
        assert result.exit_code == 0


class TestMonitorPnL:
    def test_monitor_pnl_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["monitor", "pnl", "--help"])
        assert result.exit_code == 0

    def test_monitor_pnl_requires_type(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["monitor", "pnl"])
        assert result.exit_code != 0

    def test_monitor_pnl_json_once(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "monitor",
                "pnl",
                "--type",
                "stock",
                "--count",
                "1",
                "--interval",
                "1",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_monitor_pnl_rejects_legacy_date(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            ["monitor", "pnl", "--type", "stock", "--date", "20260101"],
        )
        assert result.exit_code != 0


class TestMonitorPositions:
    def test_monitor_positions_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["monitor", "positions", "--help"])
        assert result.exit_code == 0

    def test_monitor_positions_requires_type(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["monitor", "positions"])
        assert result.exit_code != 0

    def test_monitor_positions_stock_once(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            ["monitor", "positions", "--type", "stock", "--count", "1", "--interval", "1"],
        )
        assert result.exit_code == 0

    def test_monitor_positions_coin_json_once(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "monitor",
                "positions",
                "--type",
                "coin",
                "--count",
                "1",
                "--interval",
                "1",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0


class TestMonitorUnsupported:
    def test_monitor_orders_not_supported(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["monitor", "orders", "--help"])
        assert result.exit_code != 0

    def test_monitor_balance_not_supported(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["monitor", "balance", "--help"])
        assert result.exit_code != 0
