"""Tests for `stom backtest` command group."""

import sqlite3

import pytest
from click.testing import CliRunner

from cli.main import main

DB_BACKTEST = "./_database/backtest.db"


def _latest_job_id() -> str | None:
    con = sqlite3.connect(DB_BACKTEST)
    cursor = con.cursor()
    cursor.execute(
        "SELECT id FROM backtest_jobs ORDER BY created_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    con.close()
    return row[0] if row else None


class TestBacktestHelp:
    @pytest.mark.smoke
    def test_backtest_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["backtest", "--help"])
        assert result.exit_code == 0
        assert "backtest" in result.output.lower()

    def test_backtest_run_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["backtest", "run", "--help"])
        assert result.exit_code == 0


class TestBacktestRun:
    def test_backtest_run_missing_required(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["backtest", "run"])
        assert result.exit_code != 0

    def test_backtest_run_async_stock(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "backtest",
                "run",
                "--type",
                "stock",
                "--buy-strategy",
                "test_buy",
                "--sell-strategy",
                "test_sell",
                "--start-date",
                "20260101",
                "--end-date",
                "20260131",
                "--async",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_backtest_run_rejects_legacy_options(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "backtest",
                "run",
                "--market",
                "stock",
                "--buy-strategy",
                "test",
                "--sell-strategy",
                "test",
                "--start",
                "20260101",
                "--end",
                "20260131",
            ],
        )
        assert result.exit_code != 0


class TestBacktestListStatusCancel:
    def test_backtest_list_json(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["backtest", "list", "--format", "json"])
        assert result.exit_code == 0

    def test_backtest_status_with_latest_id(self, cli_runner: CliRunner):
        job_id = _latest_job_id()
        if not job_id:
            pytest.skip("No backtest job found")
        result = cli_runner.invoke(main, ["backtest", "status", job_id, "--format", "json"])
        assert result.exit_code == 0

    def test_backtest_cancel_with_unknown_id(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["backtest", "cancel", "unknown_job_id"])
        assert result.exit_code == 0
