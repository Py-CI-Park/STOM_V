"""Runtime preflight checks for CLI backtest execution."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from cli.config import BacktestConfig
from cli.paths import (
    DB_BACKTEST,
    DB_SETTING,
    DB_STOCK_BACK_MIN,
    DB_STOCK_BACK_TICK,
    DB_STRATEGY,
    PROJECT_ROOT,
)
from cli.strategy import evaluate_strategy
from cli.timeframe_detector import validate_timeframe_match


MIN_STRATEGY_CODE_LENGTH = 12


def default_runtime_paths() -> dict[str, str]:
    """Return the default runtime paths used by CLI backtests."""
    return {
        "project_root": str(PROJECT_ROOT),
        "strategy_db": DB_STRATEGY,
        "setting_db": DB_SETTING,
        "backtest_db": DB_BACKTEST,
        "stock_tick_back_db": DB_STOCK_BACK_TICK,
        "stock_min_back_db": DB_STOCK_BACK_MIN,
        "csv_dir": str(PROJECT_ROOT / "backtest" / "csv"),
    }


def check_strategy_code(
    strategy_db: str,
    strategy_name: str,
    strategy_type: str,
    min_code_length: int = MIN_STRATEGY_CODE_LENGTH,
) -> dict[str, Any]:
    """Evaluate a strategy and classify preflight-specific code failures."""
    try:
        result = evaluate_strategy(strategy_db, strategy_name, strategy_type)
    except Exception as exc:
        result = {"status": "error", "message": str(exc)}

    code = result.get("code")

    if isinstance(code, str):
        compact = "".join(code.split())
        if compact and set(compact) == {"?"}:
            return _strategy_error(
                strategy_name,
                strategy_type,
                "suspicious_question_marks",
                result,
                code,
            )
        if len(code) < min_code_length:
            return _strategy_error(
                strategy_name,
                strategy_type,
                "code_too_short",
                result,
                code,
            )

    if result.get("status") == "ok" and not isinstance(code, str):
        return _strategy_error(
            strategy_name,
            strategy_type,
            "evaluate_failed",
            result,
            None,
        )

    if result.get("status") != "ok":
        return _strategy_error(
            strategy_name,
            strategy_type,
            "evaluate_failed",
            result,
            code if isinstance(code, str) else None,
        )

    assert isinstance(code, str)
    return {
        "status": "ok",
        "strategy_name": strategy_name,
        "strategy_type": strategy_type,
        "code_length": len(code),
        "message": result.get("message", ""),
    }


def run_runtime_preflight(
    config: BacktestConfig,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run runtime path and strategy checks before heavy backtest execution."""
    runtime_paths = default_runtime_paths()
    if paths:
        runtime_paths.update(paths)

    stock_back_key = "stock_tick_back_db" if config.is_tick else "stock_min_back_db"
    runtime_profile = _runtime_profile(runtime_paths, stock_back_key)
    failed_checks = _failed_runtime_checks(runtime_profile)
    validation_errors = _validate_config(config)
    if validation_errors:
        failed_checks.append("config")

    if runtime_profile["strategy_db_exists"]:
        strategies = {
            "buy": check_strategy_code(
                runtime_paths["strategy_db"],
                config.buy_strategy,
                "buy",
            ),
            "sell": check_strategy_code(
                runtime_paths["strategy_db"],
                config.sell_strategy,
                "sell",
            ),
        }
    else:
        strategies = {
            "buy": _strategy_error(
                config.buy_strategy,
                "buy",
                "strategy_db_missing",
                {"message": "strategy DB is missing"},
                None,
            ),
            "sell": _strategy_error(
                config.sell_strategy,
                "sell",
                "strategy_db_missing",
                {"message": "strategy DB is missing"},
                None,
            ),
        }

    if strategies["buy"]["status"] != "ok":
        failed_checks.append("buy_strategy")
    if strategies["sell"]["status"] != "ok":
        failed_checks.append("sell_strategy")

    timeframe_match = _validate_timeframe_if_usable(
        config,
        runtime_paths["strategy_db"],
        runtime_profile["strategy_db_exists"],
        strategies,
    )
    if timeframe_match.get("status") == "error":
        failed_checks.append("timeframe_match")

    return {
        "status": "error" if failed_checks else "ok",
        "failed_checks": failed_checks,
        "validation_errors": validation_errors,
        "timeframe_match": timeframe_match,
        "runtime_profile": runtime_profile,
        "strategies": strategies,
        "config": _config_summary(config),
    }


def _strategy_error(
    strategy_name: str,
    strategy_type: str,
    reason: str,
    evaluate_result: dict[str, Any],
    code: str | None,
) -> dict[str, Any]:
    return {
        "status": "error",
        "strategy_name": strategy_name,
        "strategy_type": strategy_type,
        "reason": reason,
        "code_length": len(code) if isinstance(code, str) else 0,
        "message": evaluate_result.get("message", ""),
    }


def _runtime_profile(paths: dict[str, str], stock_back_key: str) -> dict[str, Any]:
    strategy_db = paths["strategy_db"]
    setting_db = paths["setting_db"]
    backtest_db = paths["backtest_db"]
    stock_back_db = paths[stock_back_key]
    csv_dir = paths["csv_dir"]
    setting_status = _sqlite_usability(setting_db)
    backtest_status = _sqlite_usability(backtest_db)
    stock_back_status = _sqlite_table_probe(stock_back_db)

    return {
        "project_root": str(paths.get("project_root", PROJECT_ROOT)),
        "strategy_db_path": strategy_db,
        "setting_db_path": setting_db,
        "backtest_db_path": backtest_db,
        "stock_back_db_path": stock_back_db,
        "stock_back_db_kind": "tick" if stock_back_key == "stock_tick_back_db" else "min",
        "csv_output_dir": csv_dir,
        "strategy_db_exists": Path(strategy_db).is_file(),
        "setting_db_exists": Path(setting_db).is_file(),
        "backtest_db_exists": Path(backtest_db).is_file(),
        "stock_back_db_exists": Path(stock_back_db).is_file(),
        "csv_output_dir_exists": Path(csv_dir).is_dir(),
        "setting_db_usable": setting_status["usable"],
        "setting_db_integrity": setting_status["integrity_check"],
        "setting_db_message": setting_status["message"],
        "backtest_db_usable": backtest_status["usable"],
        "backtest_db_integrity": backtest_status["integrity_check"],
        "backtest_db_message": backtest_status["message"],
        "stock_back_db_usable": stock_back_status["usable"],
        "stock_back_db_integrity": stock_back_status["integrity_check"],
        "stock_back_db_message": stock_back_status["message"],
        "stock_back_db_table_count": stock_back_status["table_count"],
    }


def _failed_runtime_checks(runtime_profile: dict[str, Any]) -> list[str]:
    missing_checks = [
        ("strategy_db", "strategy_db_exists"),
        ("setting_db", "setting_db_exists"),
        ("backtest_db", "backtest_db_exists"),
        ("stock_back_db", "stock_back_db_exists"),
        ("csv_output_dir", "csv_output_dir_exists"),
    ]
    failed_checks = [
        check_name
        for check_name, exists_key in missing_checks
        if not runtime_profile[exists_key]
    ]

    usability_checks = [
        ("setting_db", "setting_db_exists", "setting_db_usable"),
        ("backtest_db", "backtest_db_exists", "backtest_db_usable"),
        ("stock_back_db", "stock_back_db_exists", "stock_back_db_usable"),
    ]
    for check_name, exists_key, usable_key in usability_checks:
        if runtime_profile[exists_key] and not runtime_profile[usable_key]:
            failed_checks.append(check_name)

    return failed_checks


def _sqlite_usability(db_path: str, require_tables: bool = False) -> dict[str, Any]:
    if not Path(db_path).is_file():
        return {
            "usable": False,
            "integrity_check": "missing",
            "message": "database file is missing",
            "table_count": 0,
        }

    con = None
    try:
        uri = Path(db_path).resolve().as_uri() + "?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        row = con.execute("PRAGMA integrity_check").fetchone()
        integrity = str(row[0]) if row else "no result"
        if integrity.lower() != "ok":
            return {
                "usable": False,
                "integrity_check": integrity,
                "message": f"integrity_check failed: {integrity}",
                "table_count": 0,
            }

        table_count = int(con.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0])
        if require_tables and table_count < 1:
            return {
                "usable": False,
                "integrity_check": integrity,
                "message": "database has no user tables",
                "table_count": table_count,
            }

        return {
            "usable": True,
            "integrity_check": integrity,
            "message": "",
            "table_count": table_count,
        }
    except sqlite3.Error as exc:
        return {
            "usable": False,
            "integrity_check": "error",
            "message": str(exc),
            "table_count": 0,
        }
    finally:
        if con is not None:
            con.close()


def _sqlite_table_probe(db_path: str) -> dict[str, Any]:
    if not Path(db_path).is_file():
        return {
            "usable": False,
            "integrity_check": "missing",
            "message": "database file is missing",
            "table_count": 0,
        }

    con = None
    try:
        uri = Path(db_path).resolve().as_uri() + "?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        table_count = int(con.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0])
        if table_count < 1:
            return {
                "usable": False,
                "integrity_check": "table_probe_only",
                "message": "database has no user tables",
                "table_count": table_count,
            }

        return {
            "usable": True,
            "integrity_check": "table_probe_only",
            "message": "",
            "table_count": table_count,
        }
    except sqlite3.Error as exc:
        return {
            "usable": False,
            "integrity_check": "table_probe_only",
            "message": str(exc),
            "table_count": 0,
        }
    finally:
        if con is not None:
            con.close()


def _validate_config(config: BacktestConfig) -> list[str]:
    errors = []
    start_valid = _is_yyyymmdd(config.start_date)
    end_valid = _is_yyyymmdd(config.end_date)

    if not start_valid:
        errors.append(f"start_date must be a valid YYYYMMDD date: {config.start_date}")
    if not end_valid:
        errors.append(f"end_date must be a valid YYYYMMDD date: {config.end_date}")
    if start_valid and end_valid and int(config.start_date) > int(config.end_date):
        errors.append(
            f"start_date must be less than or equal to end_date: "
            f"{config.start_date} > {config.end_date}"
        )
    if int(getattr(config, "engine_count", 0) or 0) < 1:
        errors.append("engine_count must be at least 1")
    if not str(getattr(config, "buy_strategy", "") or "").strip():
        errors.append("buy strategy name must be non-empty")
    if not str(getattr(config, "sell_strategy", "") or "").strip():
        errors.append("sell strategy name must be non-empty")

    return errors


def _is_yyyymmdd(value: object) -> bool:
    text = str(value)
    if len(text) != 8 or not text.isdigit():
        return False
    try:
        datetime.strptime(text, "%Y%m%d")
    except ValueError:
        return False
    return True


def _validate_timeframe_if_usable(
    config: BacktestConfig,
    strategy_db: str,
    strategy_db_exists: bool,
    strategies: dict[str, dict[str, Any]],
) -> dict[str, str]:
    if not strategy_db_exists:
        return {
            "status": "skipped",
            "message": "strategy DB is missing",
        }
    if strategies["buy"]["status"] != "ok" or strategies["sell"]["status"] != "ok":
        return {
            "status": "skipped",
            "message": "strategy checks failed",
        }

    try:
        return validate_timeframe_match(config, db_path=strategy_db)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"timeframe validation failed: {exc}",
        }


def _config_summary(config: BacktestConfig) -> dict[str, Any]:
    return {
        "buy_strategy": config.buy_strategy,
        "sell_strategy": config.sell_strategy,
        "start": config.start_date,
        "end": config.end_date,
        "timeframe": "tick" if config.is_tick else "min",
        "avg_time": config.avg_time,
        "start_time": config.start_time,
        "end_time": config.end_time,
        "engines": config.engine_count,
        "timeout": config.timeout,
        "betting": config.betting,
        "oms": config.oms,
        "blacklist": config.blacklist,
        "back_club": config.back_club,
        "divid_mode": config.divid_mode,
        "one_code": config.one_code,
    }
