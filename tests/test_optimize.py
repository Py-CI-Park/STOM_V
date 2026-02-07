"""Tests for `stom optimize` command group."""

from datetime import datetime
import sqlite3

import pytest
from click.testing import CliRunner

from cli.main import main

DB_BACKTEST = "./_database/backtest.db"


def _insert_optimize_job(job_id: str, status: str = "pending") -> None:
    con = sqlite3.connect(DB_BACKTEST)
    cursor = con.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS optimize_jobs (
            id TEXT PRIMARY KEY,
            type TEXT,
            asset_type TEXT,
            buy_strategy TEXT,
            sell_strategy TEXT,
            start_date TEXT,
            end_date TEXT,
            betting REAL,
            params TEXT,
            trials INTEGER,
            generations INTEGER,
            status TEXT,
            created_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            result TEXT,
            error_message TEXT
        )
        """
    )
    cursor.execute(
        """
        INSERT OR REPLACE INTO optimize_jobs
        (id, type, asset_type, buy_strategy, sell_strategy, start_date, end_date,
         betting, params, trials, generations, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            "grid",
            "stock",
            "test_buy",
            "test_sell",
            "20260101",
            "20260131",
            1.0,
            "{}",
            None,
            None,
            status,
            datetime.now().isoformat(),
        ),
    )
    con.commit()
    con.close()


def _get_optimize_status(job_id: str) -> str | None:
    con = sqlite3.connect(DB_BACKTEST)
    cursor = con.cursor()
    cursor.execute("SELECT status FROM optimize_jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    con.close()
    return row[0] if row else None


class TestOptimizeHelp:
    @pytest.mark.smoke
    def test_optimize_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "--help"])
        assert result.exit_code == 0


class TestOptimizeGrid:
    def test_optimize_grid_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "grid", "--help"])
        assert result.exit_code == 0

    def test_optimize_grid_requires_options(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "grid"])
        assert result.exit_code != 0

    def test_optimize_grid_async(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "optimize",
                "grid",
                "--type",
                "stock",
                "--buy-strategy",
                "test",
                "--sell-strategy",
                "test",
                "--start-date",
                "20260101",
                "--end-date",
                "20260131",
                "--params",
                "{}",
                "--async",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_optimize_grid_invalid_params_json(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "optimize",
                "grid",
                "--type",
                "stock",
                "--buy-strategy",
                "test",
                "--sell-strategy",
                "test",
                "--start-date",
                "20260101",
                "--end-date",
                "20260131",
                "--params",
                "{bad-json}",
            ],
        )
        assert result.exit_code != 0


class TestOptimizeBayesian:
    def test_optimize_bayesian_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "bayesian", "--help"])
        assert result.exit_code == 0

    def test_optimize_bayesian_async(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "optimize",
                "bayesian",
                "--type",
                "stock",
                "--buy-strategy",
                "test",
                "--sell-strategy",
                "test",
                "--start-date",
                "20260101",
                "--end-date",
                "20260131",
                "--trials",
                "10",
                "--async",
            ],
        )
        assert result.exit_code == 0


class TestOptimizeGA:
    def test_optimize_ga_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "ga", "--help"])
        assert result.exit_code == 0

    def test_optimize_ga_async(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "optimize",
                "ga",
                "--type",
                "stock",
                "--buy-strategy",
                "test",
                "--sell-strategy",
                "test",
                "--start-date",
                "20260101",
                "--end-date",
                "20260131",
                "--generations",
                "5",
                "--async",
            ],
        )
        assert result.exit_code == 0


class TestOptimizeWalkforward:
    def test_optimize_walkforward_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "walkforward", "--help"])
        assert result.exit_code == 0

    def test_optimize_walkforward_async(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "optimize",
                "walkforward",
                "--type",
                "stock",
                "--strategy",
                "test",
                "--start-date",
                "20260101",
                "--end-date",
                "20260131",
                "--async",
            ],
        )
        assert result.exit_code == 0

    def test_optimize_walkforward_rejects_legacy_windows(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "optimize",
                "walkforward",
                "--type",
                "stock",
                "--strategy",
                "test",
                "--start-date",
                "20260101",
                "--end-date",
                "20260131",
                "--train-window",
                "60",
            ],
        )
        assert result.exit_code != 0


class TestOptimizeBackfinder:
    def test_optimize_backfinder_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "backfinder", "--help"])
        assert result.exit_code == 0

    def test_optimize_backfinder_async(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            [
                "optimize",
                "backfinder",
                "--type",
                "stock",
                "--start-date",
                "20260101",
                "--end-date",
                "20260131",
                "--async",
            ],
        )
        assert result.exit_code == 0


class TestOptimizeListStatusCancel:
    def test_optimize_list_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "list", "--help"])
        assert result.exit_code == 0

    def test_optimize_list_basic(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "list"])
        assert result.exit_code == 0

    def test_optimize_status_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "status", "--help"])
        assert result.exit_code == 0

    def test_optimize_status_unknown_job(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "status", "unknown_job"])
        assert result.exit_code == 0

    def test_optimize_cancel_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "cancel", "--help"])
        assert result.exit_code == 0

    def test_optimize_cancel_unknown_job(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["optimize", "cancel", "unknown_job"])
        assert result.exit_code == 0

    def test_optimize_status_table_with_existing_job(self, cli_runner: CliRunner):
        job_id = f"opt_status_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        _insert_optimize_job(job_id, status="pending")

        result = cli_runner.invoke(main, ["optimize", "status", job_id])
        assert result.exit_code == 0
        assert "Optimization Status" in result.output
        assert job_id in result.output

    def test_optimize_list_table_with_existing_job(self, cli_runner: CliRunner):
        job_id = f"opt_list_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        _insert_optimize_job(job_id, status="pending")

        result = cli_runner.invoke(main, ["optimize", "list", "--limit", "5"])
        assert result.exit_code == 0
        assert job_id in result.output

    def test_optimize_cancel_pending_job(self, cli_runner: CliRunner):
        job_id = f"opt_cancel_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        _insert_optimize_job(job_id, status="pending")

        result = cli_runner.invoke(main, ["optimize", "cancel", job_id])
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()
        assert _get_optimize_status(job_id) == "cancelled"
