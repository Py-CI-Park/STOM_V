"""Runtime preflight checks for CLI backtest execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cli.paths import (
    DB_BACKTEST,
    DB_SETTING,
    DB_STOCK_BACK_MIN,
    DB_STOCK_BACK_TICK,
    DB_STRATEGY,
    PROJECT_ROOT,
)
from cli.strategy import evaluate_strategy


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
    min_code_length: int = 12,
) -> dict[str, Any]:
    """Evaluate a strategy and classify preflight-specific code failures."""
    result = evaluate_strategy(strategy_db, strategy_name, strategy_type)
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

    if result.get("status") != "ok":
        return _strategy_error(
            strategy_name,
            strategy_type,
            "evaluate_failed",
            result,
            code if isinstance(code, str) else None,
        )

    return {
        "status": "ok",
        "strategy_name": strategy_name,
        "strategy_type": strategy_type,
        "code_length": len(code) if isinstance(code, str) else 0,
        "message": result.get("message", ""),
    }


def run_runtime_preflight(config: Any, paths: dict[str, str] | None = None) -> dict[str, Any]:
    """Run runtime path and strategy checks before heavy backtest execution."""
    runtime_paths = default_runtime_paths()
    if paths:
        runtime_paths.update(paths)

    stock_back_key = "stock_tick_back_db" if config.is_tick else "stock_min_back_db"
    runtime_profile = _runtime_profile(runtime_paths, stock_back_key)
    failed_checks = _failed_runtime_checks(runtime_profile)

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

    if strategies["buy"]["status"] != "ok":
        failed_checks.append("buy_strategy")
    if strategies["sell"]["status"] != "ok":
        failed_checks.append("sell_strategy")

    return {
        "status": "error" if failed_checks else "ok",
        "failed_checks": failed_checks,
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
    }


def _failed_runtime_checks(runtime_profile: dict[str, Any]) -> list[str]:
    checks = [
        ("strategy_db", "strategy_db_exists"),
        ("setting_db", "setting_db_exists"),
        ("backtest_db", "backtest_db_exists"),
        ("stock_back_db", "stock_back_db_exists"),
        ("csv_output_dir", "csv_output_dir_exists"),
    ]
    return [
        check_name
        for check_name, exists_key in checks
        if not runtime_profile[exists_key]
    ]


def _config_summary(config: Any) -> dict[str, Any]:
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
