"""Tests for `stom trade`, `stom positions`, and `stom orders` commands."""

import pytest
from click.testing import CliRunner

from cli.main import main


class TestTradeHelp:
    @pytest.mark.smoke
    def test_trade_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "--help"])
        assert result.exit_code == 0


class TestTradeStart:
    def test_trade_start_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "start", "--help"])
        assert result.exit_code == 0

    def test_trade_start_requires_type(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "start"])
        assert result.exit_code != 0

    def test_trade_start_stock(self, cli_runner: CliRunner, monkeypatch):
        monkeypatch.setattr("cli.commands.trade.load_settings_without_qt", lambda: {})
        result = cli_runner.invoke(main, ["trade", "start", "--type", "stock"])
        assert result.exit_code == 0

    def test_trade_start_coin(self, cli_runner: CliRunner, monkeypatch):
        monkeypatch.setattr("cli.commands.trade.load_settings_without_qt", lambda: {})
        result = cli_runner.invoke(main, ["trade", "start", "--type", "coin"])
        assert result.exit_code == 0

    def test_trade_start_rejects_legacy_options(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "trade",
                "start",
                "--type",
                "stock",
                "--buy-strategy",
                "test_buy",
            ],
        )
        assert result.exit_code != 0


class TestTradeStop:
    def test_trade_stop_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "stop", "--help"])
        assert result.exit_code == 0

    def test_trade_stop_default(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "stop"])
        assert result.exit_code == 0

    def test_trade_stop_stock(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "stop", "--type", "stock"])
        assert result.exit_code == 0

    def test_trade_stop_rejects_legacy_all_flag(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "stop", "--all"])
        assert result.exit_code != 0


class TestTradeStatus:
    def test_trade_status_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "status", "--help"])
        assert result.exit_code == 0

    def test_trade_status(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "status"])
        assert result.exit_code == 0

    def test_trade_status_json(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "status", "--format", "json"])
        assert result.exit_code == 0


class TestTradeUnsupported:
    def test_trade_config_not_supported(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "config", "--help"])
        assert result.exit_code != 0
