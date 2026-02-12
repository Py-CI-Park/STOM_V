"""JSON contract validation tests using jsonschema."""

from __future__ import annotations

import json
import sqlite3

import pytest
from click.testing import CliRunner
from jsonschema import validate

from cli.main import main

DB_BACKTEST = "./_database/backtest.db"


def _ensure_optimize_jobs_table() -> None:
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
    con.commit()
    con.close()


ERROR_SCHEMA = {
    "type": "object",
    "required": ["ok", "error"],
    "properties": {
        "ok": {"const": False},
        "error": {
            "type": "object",
            "required": ["code", "type", "message", "title"],
            "properties": {
                "code": {"type": "string"},
                "type": {"type": "string"},
                "message": {"type": "string"},
                "title": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}

MESSAGE_OR_LIST_SCHEMA = {
    "oneOf": [
        {"type": "array"},
        {
            "type": "object",
            "required": ["message"],
            "properties": {"message": {"type": "string"}},
            "additionalProperties": True,
        },
    ]
}

TRADE_STATUS_SCHEMA = {
    "type": "object",
    "required": ["trading_status", "configuration"],
    "properties": {
        "trading_status": {"type": "object"},
        "configuration": {"type": "object"},
    },
    "additionalProperties": True,
}

DB_INFO_SCHEMA = {
    "type": "object",
    "required": ["database", "size_mb", "modified", "tables", "total_rows", "table_info"],
    "properties": {
        "database": {"type": "string"},
        "size_mb": {"type": "number"},
        "modified": {"type": "string"},
        "tables": {"type": "number"},
        "total_rows": {"type": "number"},
        "table_info": {"type": "array"},
    },
    "additionalProperties": True,
}

MESSAGE_SCHEMA = {
    "type": "object",
    "required": ["message"],
    "properties": {
        "message": {"type": "string"},
    },
    "additionalProperties": True,
}

CLOSE_SUCCESS_SCHEMA = {
    "type": "object",
    "required": [
        "ok",
        "request_id",
        "order_type",
        "asset_type",
        "status",
        "created_at",
        "execution_mode",
        "broker_execution",
        "requires_external_executor",
        "message",
    ],
    "properties": {
        "ok": {"const": True},
        "request_id": {"type": "integer"},
        "order_type": {"type": "string"},
        "asset_type": {"type": "string"},
        "status": {"type": "string"},
        "created_at": {"type": "string"},
        "execution_mode": {"const": "request_record_only"},
        "broker_execution": {"const": "not_supported_in_cli"},
        "requires_external_executor": {"const": True},
        "message": {"type": "string"},
    },
    "additionalProperties": True,
}

CANCEL_SUCCESS_SCHEMA = {
    "type": "object",
    "required": [
        "ok",
        "request_id",
        "cancel_type",
        "asset_type",
        "status",
        "created_at",
        "execution_mode",
        "broker_execution",
        "requires_external_executor",
        "message",
    ],
    "properties": {
        "ok": {"const": True},
        "request_id": {"type": "integer"},
        "cancel_type": {"type": "string"},
        "asset_type": {"type": "string"},
        "status": {"type": "string"},
        "created_at": {"type": "string"},
        "execution_mode": {"const": "request_record_only"},
        "broker_execution": {"const": "not_supported_in_cli"},
        "requires_external_executor": {"const": True},
        "message": {"type": "string"},
    },
    "additionalProperties": True,
}

BACKTEST_STATUS_SCHEMA = {
    "type": "object",
    "required": [
        "id",
        "buy_strategy",
        "sell_strategy",
        "type",
        "start_date",
        "end_date",
        "status",
        "created_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "buy_strategy": {"type": ["string", "null"]},
        "sell_strategy": {"type": ["string", "null"]},
        "type": {"type": ["string", "null"]},
        "start_date": {"type": ["string", "null"]},
        "end_date": {"type": ["string", "null"]},
        "status": {"type": ["string", "null"]},
        "created_at": {"type": ["string", "null"]},
    },
    "additionalProperties": True,
}

BACKTEST_RUN_SCHEMA = {
    "type": "object",
    "required": [
        "id",
        "buy_strategy",
        "sell_strategy",
        "type",
        "start_date",
        "end_date",
        "status",
        "async",
        "created_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "buy_strategy": {"type": ["string", "null"]},
        "sell_strategy": {"type": ["string", "null"]},
        "type": {"type": ["string", "null"]},
        "start_date": {"type": ["string", "null"]},
        "end_date": {"type": ["string", "null"]},
        "status": {"type": ["string", "null"]},
        "async": {"type": "boolean"},
        "created_at": {"type": ["string", "null"]},
    },
    "additionalProperties": True,
}

OPTIMIZE_STATUS_SCHEMA = {
    "type": "object",
    "required": [
        "id",
        "type",
        "asset_type",
        "start_date",
        "end_date",
        "status",
        "created_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "type": {"type": ["string", "null"]},
        "asset_type": {"type": ["string", "null"]},
        "start_date": {"type": ["string", "null"]},
        "end_date": {"type": ["string", "null"]},
        "status": {"type": ["string", "null"]},
        "created_at": {"type": ["string", "null"]},
    },
    "additionalProperties": True,
}

OPTIMIZE_RUN_SCHEMA = {
    "type": "object",
    "required": [
        "id",
        "type",
        "asset_type",
        "buy_strategy",
        "sell_strategy",
        "start_date",
        "end_date",
        "params",
        "created_at",
    ],
    "properties": {
        "id": {"type": "string"},
        "type": {"type": ["string", "null"]},
        "asset_type": {"type": ["string", "null"]},
        "buy_strategy": {"type": ["string", "null"]},
        "sell_strategy": {"type": ["string", "null"]},
        "start_date": {"type": ["string", "null"]},
        "end_date": {"type": ["string", "null"]},
        "params": {"type": "object"},
        "created_at": {"type": ["string", "null"]},
    },
    "additionalProperties": True,
}


def _latest_backtest_job_id() -> str | None:
    try:
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()
        cursor.execute("SELECT id FROM backtest_jobs ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        con.close()
        return row[0] if row else None
    except Exception:
        return None


def _latest_optimize_job_id() -> str | None:
    try:
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()
        cursor.execute("SELECT id FROM optimize_jobs ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        con.close()
        return row[0] if row else None
    except Exception:
        return None


class TestJsonContractSchema:
    def test_trade_status_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["trade", "status", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=TRADE_STATUS_SCHEMA)

    def test_positions_list_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["positions", "list", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=MESSAGE_OR_LIST_SCHEMA)

    def test_orders_list_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["orders", "list", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=MESSAGE_OR_LIST_SCHEMA)

    def test_positions_list_db_error_schema(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ):
        def _raise_connect(*_args, **_kwargs):
            raise RuntimeError("db connect failed")

        monkeypatch.setattr("cli.commands.trade.sqlite3.connect", _raise_connect)

        result = cli_runner.invoke(main, ["positions", "list", "--format", "json"])
        assert result.exit_code != 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=ERROR_SCHEMA)
        assert payload["error"]["code"] == "POSITIONS_LIST_FAILED"

    def test_orders_list_db_error_schema(
        self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ):
        def _raise_connect(*_args, **_kwargs):
            raise RuntimeError("db connect failed")

        monkeypatch.setattr("cli.commands.trade.sqlite3.connect", _raise_connect)

        result = cli_runner.invoke(main, ["orders", "list", "--format", "json"])
        assert result.exit_code != 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=ERROR_SCHEMA)
        assert payload["error"]["code"] == "ORDERS_LIST_FAILED"

    def test_data_backtest_list_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["data", "backtest-list", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=MESSAGE_OR_LIST_SCHEMA)

    def test_db_info_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["db", "info", "--type", "strategy", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=DB_INFO_SCHEMA)

    def test_backtest_list_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["backtest", "list", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=MESSAGE_OR_LIST_SCHEMA)

    def test_optimize_list_schema(self, cli_runner: CliRunner):
        _ensure_optimize_jobs_table()
        result = cli_runner.invoke(main, ["optimize", "list", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=MESSAGE_OR_LIST_SCHEMA)

    def test_backtest_status_unknown_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["backtest", "status", "unknown_job_id", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=MESSAGE_SCHEMA)

    def test_optimize_status_unknown_schema(self, cli_runner: CliRunner):
        _ensure_optimize_jobs_table()
        result = cli_runner.invoke(main, ["optimize", "status", "unknown_job_id", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=MESSAGE_SCHEMA)

    def test_positions_close_invalid_error_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["positions", "close", "--yes", "--format", "json"])
        assert result.exit_code != 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=ERROR_SCHEMA)
        assert payload["error"]["code"] == "POSITIONS_CLOSE_INVALID_ARGS"

    def test_orders_cancel_invalid_error_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(main, ["orders", "cancel", "--yes", "--format", "json"])
        assert result.exit_code != 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=ERROR_SCHEMA)
        assert payload["error"]["code"] == "ORDERS_CANCEL_INVALID_ARGS"

    def test_positions_close_success_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            ["positions", "close", "--all", "--type", "stock", "--yes", "--format", "json"],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=CLOSE_SUCCESS_SCHEMA)

    def test_orders_cancel_success_schema(self, cli_runner: CliRunner):
        result = cli_runner.invoke(
            main,
            ["orders", "cancel", "--all", "--type", "stock", "--yes", "--format", "json"],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=CANCEL_SUCCESS_SCHEMA)

    def test_backtest_run_success_schema(self, cli_runner: CliRunner):
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
        payload = json.loads(result.output)
        validate(instance=payload, schema=BACKTEST_RUN_SCHEMA)

    def test_optimize_run_success_schema(self, cli_runner: CliRunner):
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
                "--async",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=OPTIMIZE_RUN_SCHEMA)

    def test_backtest_run_db_error_schema(self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch):
        def _raise_connect(*_args, **_kwargs):
            raise sqlite3.OperationalError("db unavailable")

        monkeypatch.setattr("cli.commands.backtest.sqlite3.connect", _raise_connect)

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
        assert result.exit_code != 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=ERROR_SCHEMA)
        assert payload["error"]["code"] == "BACKTEST_RUN_FAILED"

    def test_optimize_run_invalid_params_error_schema(self, cli_runner: CliRunner):
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
                "{bad-json}",
                "--async",
                "--format",
                "json",
            ],
        )
        assert result.exit_code != 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=ERROR_SCHEMA)
        assert payload["error"]["code"] == "OPT_GRID_INVALID_PARAMS"

    def test_optimize_run_db_error_schema(self, cli_runner: CliRunner, monkeypatch: pytest.MonkeyPatch):
        def _raise_save(*_args, **_kwargs):
            raise sqlite3.OperationalError("db unavailable")

        monkeypatch.setattr("cli.commands.optimize.save_optimize_job", _raise_save)

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
                "--async",
                "--format",
                "json",
            ],
        )
        assert result.exit_code != 0
        payload = json.loads(result.output)
        validate(instance=payload, schema=ERROR_SCHEMA)
        assert payload["error"]["code"] == "OPT_GRID_FAILED"

    def test_backtest_status_success_schema(self, cli_runner: CliRunner):
        job_id = _latest_backtest_job_id()
        if not job_id:
            pytest.skip("No backtest job found for success schema validation")
        status_result = cli_runner.invoke(
            main,
            ["backtest", "status", job_id, "--format", "json"],
        )
        assert status_result.exit_code == 0
        status_payload = json.loads(status_result.output)
        validate(instance=status_payload, schema=BACKTEST_STATUS_SCHEMA)

    def test_optimize_status_success_schema(self, cli_runner: CliRunner):
        job_id = _latest_optimize_job_id()
        if not job_id:
            pytest.skip("No optimize job found for success schema validation")
        status_result = cli_runner.invoke(
            main,
            ["optimize", "status", job_id, "--format", "json"],
        )
        assert status_result.exit_code == 0
        status_payload = json.loads(status_result.output)
        validate(instance=status_payload, schema=OPTIMIZE_STATUS_SCHEMA)
