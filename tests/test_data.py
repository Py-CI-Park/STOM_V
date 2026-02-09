"""Tests for `stom data` command group."""

import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import main

DB_BACKTEST = "./_database/backtest.db"


def _ensure_backtest_results_table() -> None:
    con = sqlite3.connect(DB_BACKTEST)
    cursor = con.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_name TEXT,
            start_date TEXT,
            end_date TEXT,
            total_return REAL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            created_at TEXT
        )
        """
    )
    con.commit()
    con.close()


class TestDataHelp:
    @pytest.mark.smoke
    def test_data_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "--help"])
        assert result.exit_code == 0


class TestDataTrades:
    def test_data_trades_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "trades", "--help"])
        assert result.exit_code == 0

    def test_data_trades_basic(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "trades"])
        assert result.exit_code == 0

    def test_data_trades_with_type(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "trades", "--type", "stock"])
        assert result.exit_code == 0

    def test_data_trades_rejects_legacy_option(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "trades", "--market", "stock"])
        assert result.exit_code != 0

    def test_data_trades_json_format(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "trades", "--format", "json"])
        assert result.exit_code == 0


class TestDataSummary:
    def test_data_summary_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "summary", "--help"])
        assert result.exit_code == 0

    def test_data_summary_basic(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "summary"])
        assert result.exit_code == 0

    def test_data_summary_with_type(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "summary", "--type", "stock"])
        assert result.exit_code == 0

    def test_data_summary_rejects_legacy_period_options(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            ["data", "summary", "--start", "20260101", "--end", "20260131"],
        )
        assert result.exit_code != 0


class TestDataExport:
    def test_data_export_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "export", "--help"])
        assert result.exit_code == 0

    def test_data_export_backtest_csv(self, cli_runner: CliRunner, tmp_path: Path):
        _ensure_backtest_results_table()
        output_file = tmp_path / "export.csv"
        result = cli_runner.invoke(
            main,
            ["data", "export", "--type", "backtest", "--output", str(output_file)],
        )
        assert result.exit_code == 0

    def test_data_export_trades_json(self, cli_runner: CliRunner, tmp_path: Path):
        output_file = tmp_path / "export.json"
        result = cli_runner.invoke(
            main,
            [
                "data",
                "export",
                "--type",
                "trades",
                "--output",
                str(output_file),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0


class TestDataQuery:
    def test_data_query_not_supported(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "query", "--help"])
        assert result.exit_code != 0
