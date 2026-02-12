"""Tests for `stom optimize` command group."""

from __future__ import annotations

import json
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


def _get_optimize_row(job_id: str) -> dict | None:
    con = sqlite3.connect(DB_BACKTEST)
    cursor = con.cursor()
    cursor.execute(
        "SELECT id, type, status, result, error_message FROM optimize_jobs WHERE id = ?",
        (job_id,),
    )
    row = cursor.fetchone()
    con.close()
    if not row:
        return None
    return {
        "id": row[0],
        "type": row[1],
        "status": row[2],
        "result": row[3],
        "error_message": row[4],
    }


def _latest_optimize_job_id_by_type(opt_type: str) -> str | None:
    con = sqlite3.connect(DB_BACKTEST)
    cursor = con.cursor()
    cursor.execute(
        "SELECT id FROM optimize_jobs WHERE type = ? ORDER BY created_at DESC LIMIT 1",
        (opt_type,),
    )
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


class TestOptimizeSyncExecution:
    def test_optimize_grid_sync_success_updates_job_status(
        self,
        cli_runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
    ):
        def _mock_run_sync(_run_kind, _run_kwargs):
            return {"success": True, "result": {"score": 1.23}, "error_message": None}

        monkeypatch.setattr("cli.commands.optimize._run_sync_optimization", _mock_run_sync)

        result = cli_runner.invoke(
            main,
            [
                "optimize",
                "grid",
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
                "--params",
                "{}",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["status"] == "completed"
        assert payload["sync_executed"] is True

        job_id = payload["id"]
        row = _get_optimize_row(job_id)
        assert row is not None
        assert row["status"] == "completed"
        assert row["result"] is not None

    def test_optimize_grid_sync_failure_marks_failed_and_returns_error_json(
        self,
        cli_runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
    ):
        def _mock_run_sync(_run_kind, _run_kwargs):
            return {"success": False, "result": None, "error_message": "runner failed for test"}

        monkeypatch.setattr("cli.commands.optimize._run_sync_optimization", _mock_run_sync)

        result = cli_runner.invoke(
            main,
            [
                "optimize",
                "grid",
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
                "--params",
                "{}",
                "--format",
                "json",
            ],
        )
        assert result.exit_code != 0
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "OPT_GRID_SYNC_FAILED"

        job_id = _latest_optimize_job_id_by_type("grid")
        assert job_id is not None
        row = _get_optimize_row(job_id)
        assert row is not None
        assert row["status"] == "failed"
        assert row["error_message"] is not None
        assert "runner failed for test" in row["error_message"]

    def test_optimize_bayesian_sync_exception_returns_sync_error_code(
        self,
        cli_runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
    ):
        def _mock_run_sync(_run_kind, _run_kwargs):
            raise RuntimeError("sync executor crashed")

        monkeypatch.setattr("cli.commands.optimize._run_sync_optimization", _mock_run_sync)

        result = cli_runner.invoke(
            main,
            [
                "optimize",
                "bayesian",
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
                "--trials",
                "3",
                "--format",
                "json",
            ],
        )
        assert result.exit_code != 0
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "OPT_BAYESIAN_SYNC_FAILED"

        job_id = _latest_optimize_job_id_by_type("bayesian")
        assert job_id is not None
        row = _get_optimize_row(job_id)
        assert row is not None
        assert row["status"] == "failed"
        assert row["error_message"] is not None
        assert "sync executor crashed" in row["error_message"]
