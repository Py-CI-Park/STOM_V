"""JSON contract validation tests using jsonschema."""

from __future__ import annotations

import json

from click.testing import CliRunner
from jsonschema import validate

from cli.main import main


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

CLOSE_SUCCESS_SCHEMA = {
    "type": "object",
    "required": ["ok", "order_type", "asset_type", "status", "message"],
    "properties": {
        "ok": {"const": True},
        "order_type": {"type": "string"},
        "asset_type": {"type": "string"},
        "status": {"type": "string"},
        "message": {"type": "string"},
    },
    "additionalProperties": True,
}

CANCEL_SUCCESS_SCHEMA = {
    "type": "object",
    "required": ["ok", "cancel_type", "asset_type", "status", "message"],
    "properties": {
        "ok": {"const": True},
        "cancel_type": {"type": "string"},
        "asset_type": {"type": "string"},
        "status": {"type": "string"},
        "message": {"type": "string"},
    },
    "additionalProperties": True,
}


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
