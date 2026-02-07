"""Boundary and failure-path tests for strategy commands."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import main


@pytest.fixture
def strategy_db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "strategy.db"
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute(
        """
        CREATE TABLE stockbuy (
            name TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE coinbuy (
            name TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        "INSERT INTO stockbuy (name, code) VALUES (?, ?)",
        ("valid_buy", "def signal():\n    return 'BUY'"),
    )
    cur.execute(
        "INSERT INTO stockbuy (name, code) VALUES (?, ?)",
        ("invalid_buy", "def signal(:\n    return 1"),
    )
    con.commit()
    con.close()

    monkeypatch.setattr("cli.commands.strategy.DB_STRATEGY", str(db_path))
    return db_path


class TestStrategyBoundaryCases:
    def test_strategy_list_type_without_rows(self, cli_runner: CliRunner, strategy_db: Path):
        result = cli_runner.invoke(main, ["strategy", "list", "--type", "future"])
        assert result.exit_code == 0
        assert "전략이 없습니다" in result.output

    def test_strategy_show_missing_table(self, cli_runner: CliRunner, strategy_db: Path):
        result = cli_runner.invoke(main, ["strategy", "show", "missing_table"])
        assert result.exit_code == 0
        assert "찾을 수 없습니다" in result.output

    def test_strategy_show_existing_table_json(self, cli_runner: CliRunner, strategy_db: Path):
        result = cli_runner.invoke(main, ["strategy", "show", "stockbuy", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert isinstance(payload, list)
        assert len(payload) >= 1
        assert payload[0]["name"] == "valid_buy"

    def test_strategy_export_missing_table(self, cli_runner: CliRunner, strategy_db: Path, tmp_path: Path):
        output_file = tmp_path / "missing.csv"
        result = cli_runner.invoke(main, ["strategy", "export", "missing", str(output_file)])
        assert result.exit_code == 0
        assert "찾을 수 없습니다" in result.output
        assert not output_file.exists()

    def test_strategy_export_existing_table_json(self, cli_runner: CliRunner, strategy_db: Path, tmp_path: Path):
        output_file = tmp_path / "stockbuy.json"
        result = cli_runner.invoke(
            main,
            ["strategy", "export", "stockbuy", str(output_file), "--format", "json"],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        exported = json.loads(output_file.read_text(encoding="utf-8"))
        assert len(exported) >= 1

    def test_strategy_save_requires_code_or_file(self, cli_runner: CliRunner, strategy_db: Path):
        result = cli_runner.invoke(
            main,
            ["strategy", "save", "--name", "new_strategy", "--type", "stock", "--buy"],
        )
        assert result.exit_code != 0
        assert "--code 또는 --file" in result.output

    def test_strategy_save_rejects_code_and_file_together(
        self, cli_runner: CliRunner, strategy_db: Path, tmp_path: Path
    ):
        code_file = tmp_path / "strategy.py"
        code_file.write_text("def signal():\n    return 'BUY'\n", encoding="utf-8")
        result = cli_runner.invoke(
            main,
            [
                "strategy",
                "save",
                "--name",
                "dup_strategy",
                "--type",
                "stock",
                "--buy",
                "--code",
                "def signal(): return 'BUY'",
                "--file",
                str(code_file),
            ],
        )
        assert result.exit_code != 0
        assert "동시에 사용할 수 없습니다" in result.output

    def test_strategy_save_from_file_persists(self, cli_runner: CliRunner, strategy_db: Path, tmp_path: Path):
        code_file = tmp_path / "strategy_file.py"
        code_file.write_text("def signal():\n    return 'BUY'\n", encoding="utf-8")
        result = cli_runner.invoke(
            main,
            [
                "strategy",
                "save",
                "--name",
                "saved_from_file",
                "--type",
                "stock",
                "--buy",
                "--file",
                str(code_file),
            ],
        )
        assert result.exit_code == 0
        assert "저장되었습니다" in result.output or "업데이트되었습니다" in result.output

        con = sqlite3.connect(strategy_db)
        row = con.execute("SELECT code FROM stockbuy WHERE name = ?", ("saved_from_file",)).fetchone()
        con.close()
        assert row is not None
        assert "def signal()" in row[0]

    def test_strategy_delete_missing_strategy(self, cli_runner: CliRunner, strategy_db: Path):
        result = cli_runner.invoke(
            main,
            ["strategy", "delete", "--name", "missing_name", "--type", "stock", "--buy", "--yes"],
        )
        assert result.exit_code == 0
        assert "찾을 수 없습니다" in result.output

    def test_strategy_import_rejects_unsupported_extension(
        self, cli_runner: CliRunner, strategy_db: Path, tmp_path: Path
    ):
        text_file = tmp_path / "strategies.txt"
        text_file.write_text("not supported", encoding="utf-8")
        result = cli_runner.invoke(
            main,
            ["strategy", "import", "--file", str(text_file), "--type", "stock"],
        )
        assert result.exit_code != 0
        assert "지원되지 않는 파일 형식" in result.output

    def test_strategy_import_empty_json(self, cli_runner: CliRunner, strategy_db: Path, tmp_path: Path):
        import_file = tmp_path / "empty.json"
        import_file.write_text("[]", encoding="utf-8")
        result = cli_runner.invoke(
            main,
            ["strategy", "import", "--file", str(import_file), "--type", "stock"],
        )
        assert result.exit_code == 0
        assert "데이터가 없습니다" in result.output

    def test_strategy_validate_missing_strategy(self, cli_runner: CliRunner, strategy_db: Path):
        result = cli_runner.invoke(
            main,
            ["strategy", "validate", "--name", "missing", "--type", "stock", "--buy"],
        )
        assert result.exit_code == 0
        assert "찾을 수 없습니다" in result.output

    def test_strategy_validate_syntax_error_path(self, cli_runner: CliRunner, strategy_db: Path):
        result = cli_runner.invoke(
            main,
            ["strategy", "validate", "--name", "invalid_buy", "--type", "stock", "--buy"],
        )
        assert result.exit_code == 0
        assert "구문 오류" in result.output
