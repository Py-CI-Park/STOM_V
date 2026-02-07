"""
Optimize command group for STOM CLI.

This module stores optimization jobs in backtest.db and exposes job status APIs.
Actual heavy execution is delegated to runners and may be queued only.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

import click
import pandas as pd

from cli.adapters.output_adapter import OutputAdapter, OutputFormat
from cli.adapters.schema_adapter import detect_strategy_name_column
from utility.static import get_logger

logger_ = get_logger("OptimizeCommand")

DB_BACKTEST = "./_database/backtest.db"
DB_STRATEGY = "./_database/strategy.db"


def create_optimize_jobs_table(con: sqlite3.Connection):
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


def save_optimize_job(job_config: Dict[str, Any]) -> str:
    con = sqlite3.connect(DB_BACKTEST)
    create_optimize_jobs_table(con)
    cursor = con.cursor()
    cursor.execute(
        """
        INSERT INTO optimize_jobs
        (id, type, asset_type, buy_strategy, sell_strategy, start_date, end_date,
         betting, params, trials, generations, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_config["id"],
            job_config["type"],
            job_config["asset_type"],
            job_config.get("buy_strategy"),
            job_config.get("sell_strategy"),
            job_config["start_date"],
            job_config["end_date"],
            job_config.get("betting", 1.0),
            json.dumps(job_config.get("params", {}), ensure_ascii=False),
            job_config.get("trials"),
            job_config.get("generations"),
            "pending",
            job_config["created_at"],
        ),
    )
    con.commit()
    con.close()
    logger_.info(f"Optimization job created: {job_config['id']}")
    return job_config["id"]


def validate_strategy_exists(strategy_name: str, asset_type: str) -> bool:
    """Return True if strategy exists in {asset}buy/{asset}sell tables."""
    try:
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()
        prefix = {"stock": "stock", "coin": "coin", "future": "future"}.get(asset_type, "stock")

        for table_name in [f"{prefix}buy", f"{prefix}sell"]:
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            if cursor.fetchone()[0] == 0:
                continue

            name_col = detect_strategy_name_column(con, table_name)
            if not name_col:
                continue

            cursor.execute(
                f'SELECT COUNT(*) FROM "{table_name}" WHERE "{name_col}"=?',
                (strategy_name,),
            )
            if cursor.fetchone()[0] > 0:
                con.close()
                return True

        con.close()
        return False
    except Exception as e:
        logger_.error(f"Error validating strategy: {e}")
        return False


def _normalize_date(value: str) -> str:
    return value.replace("-", "")


def _render_job(output_adapter: OutputAdapter, job_config: Dict[str, Any], as_json: bool):
    if as_json:
        output_adapter.output(job_config, title="Optimization Job")
        return

    lines = []
    lines.append("=" * 70)
    lines.append("Optimization Job Queued")
    lines.append("=" * 70)
    lines.append(f"\nJob ID: {job_config['id']}")
    lines.append(f"Type: {job_config['type']}")
    lines.append(f"Asset: {job_config['asset_type']}")
    lines.append(f"Start/End: {job_config['start_date']} ~ {job_config['end_date']}")
    if job_config.get("buy_strategy"):
        lines.append(f"Buy Strategy: {job_config['buy_strategy']}")
    if job_config.get("sell_strategy"):
        lines.append(f"Sell Strategy: {job_config['sell_strategy']}")
    lines.append(f"Betting: {job_config.get('betting', 1.0)}")
    lines.append(f"Status: pending")
    lines.append(f"\nCheck: stom optimize status {job_config['id']}")
    click.echo("\n".join(lines))


@click.group()
def optimize():
    """Optimization commands."""
    pass


@optimize.command("grid")
@click.option("--type", "asset_type", type=click.Choice(["stock", "coin", "future"]), required=True)
@click.option("--buy-strategy", type=str, required=True)
@click.option("--sell-strategy", type=str, required=True)
@click.option("--start-date", type=str, required=True)
@click.option("--end-date", type=str, required=True)
@click.option("--params", type=str, required=True, help="Grid parameters JSON")
@click.option("--betting", type=float, default=1.0)
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
@click.option("--async", "is_async", is_flag=True)
def grid(
    asset_type: str,
    buy_strategy: str,
    sell_strategy: str,
    start_date: str,
    end_date: str,
    params: str,
    betting: float,
    format: str,
    is_async: bool,
):
    """Queue a grid-search optimization job."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        params_dict = json.loads(params)

        if not validate_strategy_exists(buy_strategy, asset_type):
            logger_.warning(f"Buy strategy not found: {buy_strategy}")
        if not validate_strategy_exists(sell_strategy, asset_type):
            logger_.warning(f"Sell strategy not found: {sell_strategy}")

        job_config = {
            "id": f"grid_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "type": "grid",
            "asset_type": asset_type,
            "buy_strategy": buy_strategy,
            "sell_strategy": sell_strategy,
            "start_date": _normalize_date(start_date),
            "end_date": _normalize_date(end_date),
            "betting": betting,
            "params": params_dict,
            "created_at": datetime.now().isoformat(),
        }
        save_optimize_job(job_config)
        _render_job(output_adapter, job_config, format == "json")

        if not is_async:
            click.echo("Warning: execution runner integration is not enabled in this command.")
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON format for --params: {e}")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "Grid optimization failed",
                output_format=OutputFormat(format),
                error_code="OPT_GRID_FAILED",
            )
        )
        logger_.error(f"Error running grid optimization: {e}")
        raise click.ClickException(str(e))


@optimize.command("bayesian")
@click.option("--type", "asset_type", type=click.Choice(["stock", "coin", "future"]), required=True)
@click.option("--buy-strategy", type=str, required=True)
@click.option("--sell-strategy", type=str, required=True)
@click.option("--start-date", type=str, required=True)
@click.option("--end-date", type=str, required=True)
@click.option("--trials", type=int, required=True)
@click.option("--betting", type=float, default=1.0)
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
@click.option("--async", "is_async", is_flag=True)
def bayesian(
    asset_type: str,
    buy_strategy: str,
    sell_strategy: str,
    start_date: str,
    end_date: str,
    trials: int,
    betting: float,
    format: str,
    is_async: bool,
):
    """Queue a bayesian optimization job."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        if not validate_strategy_exists(buy_strategy, asset_type):
            logger_.warning(f"Buy strategy not found: {buy_strategy}")
        if not validate_strategy_exists(sell_strategy, asset_type):
            logger_.warning(f"Sell strategy not found: {sell_strategy}")

        job_config = {
            "id": f"bayesian_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "type": "bayesian",
            "asset_type": asset_type,
            "buy_strategy": buy_strategy,
            "sell_strategy": sell_strategy,
            "start_date": _normalize_date(start_date),
            "end_date": _normalize_date(end_date),
            "betting": betting,
            "trials": trials,
            "created_at": datetime.now().isoformat(),
        }
        save_optimize_job(job_config)
        _render_job(output_adapter, job_config, format == "json")
        if not is_async:
            click.echo("Warning: execution runner integration is not enabled in this command.")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "Bayesian optimization failed",
                output_format=OutputFormat(format),
                error_code="OPT_BAYESIAN_FAILED",
            )
        )
        logger_.error(f"Error running bayesian optimization: {e}")
        raise click.ClickException(str(e))


@optimize.command("ga")
@click.option("--type", "asset_type", type=click.Choice(["stock", "coin", "future"]), required=True)
@click.option("--buy-strategy", type=str, required=True)
@click.option("--sell-strategy", type=str, required=True)
@click.option("--start-date", type=str, required=True)
@click.option("--end-date", type=str, required=True)
@click.option("--generations", type=int, required=True)
@click.option("--betting", type=float, default=1.0)
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
@click.option("--async", "is_async", is_flag=True)
def ga(
    asset_type: str,
    buy_strategy: str,
    sell_strategy: str,
    start_date: str,
    end_date: str,
    generations: int,
    betting: float,
    format: str,
    is_async: bool,
):
    """Queue a genetic algorithm optimization job."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        if not validate_strategy_exists(buy_strategy, asset_type):
            logger_.warning(f"Buy strategy not found: {buy_strategy}")
        if not validate_strategy_exists(sell_strategy, asset_type):
            logger_.warning(f"Sell strategy not found: {sell_strategy}")

        job_config = {
            "id": f"ga_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "type": "ga",
            "asset_type": asset_type,
            "buy_strategy": buy_strategy,
            "sell_strategy": sell_strategy,
            "start_date": _normalize_date(start_date),
            "end_date": _normalize_date(end_date),
            "betting": betting,
            "generations": generations,
            "created_at": datetime.now().isoformat(),
        }
        save_optimize_job(job_config)
        _render_job(output_adapter, job_config, format == "json")
        if not is_async:
            click.echo("Warning: execution runner integration is not enabled in this command.")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "GA optimization failed",
                output_format=OutputFormat(format),
                error_code="OPT_GA_FAILED",
            )
        )
        logger_.error(f"Error running GA optimization: {e}")
        raise click.ClickException(str(e))


@optimize.command("walkforward")
@click.option("--type", "asset_type", type=click.Choice(["stock", "coin", "future"]), required=True)
@click.option("--strategy", type=str, required=True)
@click.option("--start-date", type=str, required=True)
@click.option("--end-date", type=str, required=True)
@click.option("--train-weeks", type=int, default=4)
@click.option("--valid-weeks", type=int, default=1)
@click.option("--test-weeks", type=int, default=1)
@click.option("--betting", type=float, default=1.0)
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
@click.option("--async", "is_async", is_flag=True)
def walkforward(
    asset_type: str,
    strategy: str,
    start_date: str,
    end_date: str,
    train_weeks: int,
    valid_weeks: int,
    test_weeks: int,
    betting: float,
    format: str,
    is_async: bool,
):
    """Queue a walk-forward optimization job."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        if not validate_strategy_exists(strategy, asset_type):
            logger_.warning(f"Strategy not found: {strategy}")

        job_config = {
            "id": f"walkforward_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "type": "walkforward",
            "asset_type": asset_type,
            "buy_strategy": strategy,
            "sell_strategy": strategy,
            "start_date": _normalize_date(start_date),
            "end_date": _normalize_date(end_date),
            "betting": betting,
            "params": {
                "train_weeks": train_weeks,
                "valid_weeks": valid_weeks,
                "test_weeks": test_weeks,
            },
            "created_at": datetime.now().isoformat(),
        }
        save_optimize_job(job_config)
        _render_job(output_adapter, job_config, format == "json")
        if not is_async:
            click.echo("Warning: execution runner integration is not enabled in this command.")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "Walk-forward optimization failed",
                output_format=OutputFormat(format),
                error_code="OPT_WALKFORWARD_FAILED",
            )
        )
        logger_.error(f"Error running walk-forward optimization: {e}")
        raise click.ClickException(str(e))


@optimize.command("backfinder")
@click.option("--type", "asset_type", type=click.Choice(["stock", "coin", "future"]), required=True)
@click.option("--start-date", type=str, required=True)
@click.option("--end-date", type=str, required=True)
@click.option("--betting", type=float, default=1.0)
@click.option("--min-profit", type=float, default=0.0)
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
@click.option("--async", "is_async", is_flag=True)
def backfinder(
    asset_type: str,
    start_date: str,
    end_date: str,
    betting: float,
    min_profit: float,
    format: str,
    is_async: bool,
):
    """Queue a backfinder job."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        job_config = {
            "id": f"backfinder_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "type": "backfinder",
            "asset_type": asset_type,
            "start_date": _normalize_date(start_date),
            "end_date": _normalize_date(end_date),
            "betting": betting,
            "params": {"min_profit": min_profit},
            "created_at": datetime.now().isoformat(),
        }
        save_optimize_job(job_config)
        _render_job(output_adapter, job_config, format == "json")
        if not is_async:
            click.echo("Warning: execution runner integration is not enabled in this command.")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "Backfinder failed",
                output_format=OutputFormat(format),
                error_code="OPT_BACKFINDER_FAILED",
            )
        )
        logger_.error(f"Error running backfinder: {e}")
        raise click.ClickException(str(e))


@optimize.command("status")
@click.argument("job_id")
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
def status(job_id: str, format: str):
    """Show one optimization job status."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()
        cursor.execute("SELECT * FROM optimize_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            con.close()
            output_adapter.output(f"Optimization job '{job_id}' not found.", title="Optimization Status")
            return

        columns = [d[0] for d in cursor.description]
        result = dict(zip(columns, row))
        con.close()

        for key in ("params", "result"):
            if result.get(key):
                try:
                    result[key] = json.loads(result[key])
                except Exception:
                    pass

        if format == "json":
            output_adapter.output(result, title="Optimization Status")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("Optimization Status")
            lines.append("=" * 70)
            for key, value in result.items():
                lines.append(f"{key}: {value}")
            click.echo("\n".join(lines))
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "Optimization status query failed",
                output_format=OutputFormat(format),
                error_code="OPT_STATUS_FAILED",
            )
        )
        logger_.error(f"Error getting optimization status: {e}")
        raise click.ClickException(str(e))


@optimize.command("list")
@click.option("--limit", type=int, default=20)
@click.option("--type", "opt_type", type=click.Choice(["grid", "bayesian", "ga", "walkforward", "backfinder"]))
@click.option("--status", type=click.Choice(["pending", "running", "completed", "failed", "cancelled"]))
@click.option("--format", type=click.Choice(["table", "json", "csv"]), default="table")
def list_jobs(limit: int, opt_type: Optional[str], status: Optional[str], format: str):
    """List optimization jobs."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        con = sqlite3.connect(DB_BACKTEST)
        conditions = []
        params = []
        if opt_type:
            conditions.append("type = ?")
            params.append(opt_type)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM optimize_jobs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit}
        """
        df = pd.read_sql(query, con, params=params if params else None)
        con.close()

        if df.empty:
            output_adapter.output("최적화 작업이 없습니다.", title="최적화 목록")
            return
        output_adapter.output(df, title="최적화 목록")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "Optimization list query failed",
                output_format=OutputFormat(format),
                error_code="OPT_LIST_FAILED",
            )
        )
        logger_.error(f"Error listing optimization jobs: {e}")
        raise click.ClickException(str(e))


@optimize.command("cancel")
@click.argument("job_id")
def cancel(job_id: str):
    """Cancel a queued/running optimization job."""
    try:
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()
        cursor.execute("SELECT status FROM optimize_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            con.close()
            click.echo(f"Error: Optimization job '{job_id}' not found.")
            return

        current = row[0]
        if current in ["completed", "failed", "cancelled"]:
            con.close()
            click.echo(f"Error: Job status '{current}' cannot be cancelled.")
            return

        cursor.execute(
            "UPDATE optimize_jobs SET status = 'cancelled', completed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), job_id),
        )
        con.commit()
        con.close()
        click.echo(f"Optimization job '{job_id}' cancelled.")
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "Optimization cancel failed"))
        logger_.error(f"Error cancelling optimization job: {e}")
        raise click.ClickException(str(e))


@optimize.command("delete")
@click.argument("job_id")
@click.confirmation_option(prompt="Delete this optimization job?")
def delete(job_id: str):
    """Delete one optimization job."""
    try:
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()
        cursor.execute("DELETE FROM optimize_jobs WHERE id = ?", (job_id,))
        if cursor.rowcount == 0:
            click.echo(f"Error: Optimization job '{job_id}' not found.")
        else:
            click.echo(f"Optimization job '{job_id}' deleted.")
        con.commit()
        con.close()
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "Optimization delete failed"))
        logger_.error(f"Error deleting optimization job: {e}")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    optimize()
