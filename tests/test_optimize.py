"""Tests for `stom optimize` command group."""

import pytest
from click.testing import CliRunner

from cli.main import main


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
