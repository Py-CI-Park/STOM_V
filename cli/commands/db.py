"""
Database Management CLI Commands

STOM CLI - Phase 5: Database Management
Provides commands for creating, managing, and maintaining STOM databases.
"""

import click
import sqlite3
import pandas as pd
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

from utility.static import get_logger
from cli.adapters.output_adapter import OutputAdapter, OutputFormat


# Database paths
DB_BACKTEST = './_database/backtest.db'
DB_TRADELIST = './_database/tradelist.db'
DB_STRATEGY = './_database/strategy.db'
DB_SETTING = './_database/setting.db'
DB_STOCK_TICK = './_database/stock_tick_back.db'
DB_STOCK_MIN = './_database/stock_min_back.db'
DB_COIN_TICK = './_database/coin_tick_back.db'
DB_COIN_MIN = './_database/coin_min_back.db'

DB_MAP = {
    'backtest': DB_BACKTEST,
    'tradelist': DB_TRADELIST,
    'strategy': DB_STRATEGY,
    'setting': DB_SETTING,
    'stock_tick': DB_STOCK_TICK,
    'stock_min': DB_STOCK_MIN,
    'coin_tick': DB_COIN_TICK,
    'coin_min': DB_COIN_MIN,
}

logger = get_logger('DBCommand')


@click.group()
def db():
    """Database management commands."""
    pass


@db.command()
@click.option('--type', 'db_type', required=True,
              type=click.Choice(['backtest', 'tradelist']),
              help='Type of database to create')
@click.option('--force', is_flag=True,
              help='Overwrite existing database')
def create(db_type: str, force: bool):
    """Create new database.

    Creates a new empty database file with the appropriate schema.
    """
    adapter = OutputAdapter()

    try:
        db_path = DB_MAP[db_type]

        # Check if database already exists
        if os.path.exists(db_path) and not force:
            click.echo(click.style(
                f"Database {db_path} already exists. Use --force to overwrite.",
                fg='yellow'
            ))
            return

        # Create database directory if needed
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Create database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables based on type
        if db_type == 'backtest':
            _create_backtest_schema(cursor)
        elif db_type == 'tradelist':
            _create_tradelist_schema(cursor)

        conn.commit()
        conn.close()

        click.echo(OutputAdapter.format_success(f"Database created: {db_path}"))
        logger.info(f"Database created: {db_path}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(f"Failed to create database: {str(e)}"))
        logger.error(f"Database creation failed: {str(e)}")
        raise click.Abort()


@db.command()
@click.option('--type', 'data_type', required=True,
              type=click.Choice(['stock', 'coin', 'future']),
              help='Type of data to append')
@click.option('--date', required=True,
              help='Date in YYYYMMDD format')
@click.option('--source', type=click.Path(exists=True),
              help='Source file or directory containing data')
def append(data_type: str, date: str, source: Optional[str]):
    """Append data to database.

    Appends historical tick or minute data to the appropriate database.
    """
    adapter = OutputAdapter()

    try:
        # Validate date format
        datetime.strptime(date, '%Y%m%d')

        # Determine target database
        if data_type == 'stock':
            db_tick = DB_STOCK_TICK
            db_min = DB_STOCK_MIN
        elif data_type == 'coin':
            db_tick = DB_COIN_TICK
            db_min = DB_COIN_MIN
        else:
            click.echo(OutputAdapter.format_error("Future data not yet supported"))
            raise click.Abort()

        # Check if databases exist
        if not os.path.exists(db_tick) or not os.path.exists(db_min):
            click.echo(OutputAdapter.format_error(f"Database files not found. Create them first."))
            raise click.Abort()

        if source:
            click.echo(OutputAdapter.format_info(f"Appending data from {source} to {data_type} databases for {date}"))
            # TODO: Implement actual data loading logic
            click.echo(OutputAdapter.format_warning("Data loading not yet implemented"))
        else:
            click.echo(OutputAdapter.format_info(f"Would append {data_type} data for {date}"))
            click.echo(OutputAdapter.format_warning("No source specified - dry run"))

        logger.info(f"Data append: type={data_type}, date={date}")

    except ValueError:
        click.echo(OutputAdapter.format_error("Invalid date format. Use YYYYMMDD"))
        raise click.Abort()
    except Exception as e:
        click.echo(OutputAdapter.format_error(f"Failed to append data: {str(e)}"))
        logger.error(f"Data append failed: {str(e)}")
        raise click.Abort()


@db.command()
@click.option('--type', 'data_type', required=True,
              type=click.Choice(['stock', 'coin', 'future']),
              help='Type of data to delete')
@click.option('--date', required=True,
              help='Date in YYYYMMDD format')
@click.option('--yes', is_flag=True,
              help='Skip confirmation prompt')
def delete(data_type: str, date: str, yes: bool):
    """Delete data by date.

    Removes all data for a specific date from the database.
    """
    adapter = OutputAdapter()

    try:
        # Validate date format
        datetime.strptime(date, '%Y%m%d')

        # Confirmation prompt
        if not yes:
            click.confirm(
                f"Are you sure you want to delete all {data_type} data for {date}?",
                abort=True
            )

        # Determine target database
        if data_type == 'stock':
            db_tick = DB_STOCK_TICK
            db_min = DB_STOCK_MIN
        elif data_type == 'coin':
            db_tick = DB_COIN_TICK
            db_min = DB_COIN_MIN
        else:
            click.echo(OutputAdapter.format_error("Future data not yet supported"))
            raise click.Abort()

        # Delete from both tick and minute databases
        deleted_count = 0
        for db_path in [db_tick, db_min]:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Get table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                for (table_name,) in tables:
                    cursor.execute(f"DELETE FROM {table_name} WHERE 체결시간 LIKE ?", (f"{date}%",))
                    deleted_count += cursor.rowcount

                conn.commit()
                conn.close()

        click.echo(OutputAdapter.format_success(f"Deleted {deleted_count} rows for {date}"))
        logger.info(f"Data deleted: type={data_type}, date={date}, rows={deleted_count}")

    except ValueError:
        click.echo(OutputAdapter.format_error("Invalid date format. Use YYYYMMDD"))
        raise click.Abort()
    except Exception as e:
        click.echo(OutputAdapter.format_error(f"Failed to delete data: {str(e)}"))
        logger.error(f"Data deletion failed: {str(e)}")
        raise click.Abort()


@db.command()
@click.option('--type', 'db_type', required=True,
              type=click.Choice(['backtest', 'tradelist', 'strategy', 'setting',
                                'stock_tick', 'stock_min', 'coin_tick', 'coin_min']),
              help='Type of database to inspect')
@click.option('--format', 'output_format',
              type=click.Choice(['table', 'json', 'csv']),
              default='table',
              help='Output format')
def info(db_type: str, output_format: str):
    """Show database information.

    Displays metadata about the database including size, tables, and row counts.
    """
    try:
        adapter = OutputAdapter(format=OutputFormat(output_format))
        db_path = DB_MAP[db_type]

        if not os.path.exists(db_path):
            click.echo(
                OutputAdapter.format_error(
                    f"Database not found: {db_path}",
                    output_format=OutputFormat(output_format),
                    error_code="DB_INFO_NOT_FOUND",
                )
            )
            raise click.Abort()

        # Get file info
        file_size = os.path.getsize(db_path)
        modified_time = datetime.fromtimestamp(os.path.getmtime(db_path))

        # Get database info
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        # Get row counts
        table_info = []
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            table_info.append({
                'table': table_name,
                'rows': row_count
            })

        conn.close()

        # Prepare output data
        info_data = {
            'database': db_path,
            'size_mb': round(file_size / (1024 * 1024), 2),
            'modified': modified_time.strftime('%Y-%m-%d %H:%M:%S'),
            'tables': len(tables),
            'total_rows': sum(t['rows'] for t in table_info)
        }

        if output_format == 'json':
            payload = dict(info_data)
            payload['table_info'] = table_info
            adapter.output(payload)
        else:
            # Display summary
            click.echo(OutputAdapter.format_info(f"\nDatabase: {db_path}"))
            click.echo(OutputAdapter.format_info(f"Size: {info_data['size_mb']} MB"))
            click.echo(OutputAdapter.format_info(f"Modified: {info_data['modified']}"))
            click.echo(OutputAdapter.format_info(f"Tables: {info_data['tables']}"))
            click.echo(OutputAdapter.format_info(f"Total Rows: {info_data['total_rows']:,}\n"))

            # Display table details
            if table_info:
                df = pd.DataFrame(table_info)
                adapter.output(df, title="Table Details")

        logger.info(f"Database info displayed: {db_type}")

    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                f"Failed to get database info: {str(e)}",
                output_format=OutputFormat(output_format),
                error_code="DB_INFO_FAILED",
            )
        )
        logger.error(f"Database info failed: {str(e)}")
        raise click.Abort()


@db.command()
@click.option('--type', 'db_type', required=True,
              type=click.Choice(['all', 'backtest', 'tradelist', 'strategy', 'setting',
                                'stock_tick', 'stock_min', 'coin_tick', 'coin_min']),
              help='Type of database to vacuum')
@click.option('--yes', is_flag=True,
              help='Skip confirmation prompt')
def vacuum(db_type: str, yes: bool):
    """Optimize database files.

    Runs VACUUM command to reclaim space and optimize database performance.
    """
    adapter = OutputAdapter()

    try:
        # Determine which databases to vacuum
        if db_type == 'all':
            db_paths = list(DB_MAP.values())
        else:
            db_paths = [DB_MAP[db_type]]

        # Confirmation prompt
        if not yes:
            click.confirm(
                f"Are you sure you want to vacuum {db_type} database(s)?",
                abort=True
            )

        click.echo(OutputAdapter.format_info("Starting database optimization..."))

        for db_path in db_paths:
            if not os.path.exists(db_path):
                click.echo(OutputAdapter.format_warning(f"Skipping {db_path} (not found)"))
                continue

            try:
                size_before = os.path.getsize(db_path)

                conn = sqlite3.connect(db_path)
                conn.execute("VACUUM")
                conn.close()

                size_after = os.path.getsize(db_path)
                saved = size_before - size_after
                saved_pct = (saved / size_before * 100) if size_before > 0 else 0

                click.echo(OutputAdapter.format_success(
                    f"Optimized {os.path.basename(db_path)}: "
                    f"saved {saved / (1024*1024):.2f} MB ({saved_pct:.1f}%)"
                ))

            except Exception as e:
                click.echo(OutputAdapter.format_error(f"Failed to vacuum {db_path}: {str(e)}"))

        click.echo(OutputAdapter.format_success("Database optimization complete"))
        logger.info(f"Database vacuum: type={db_type}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(f"Failed to vacuum databases: {str(e)}"))
        logger.error(f"Database vacuum failed: {str(e)}")
        raise click.Abort()


@db.command()
@click.option('--output', required=True,
              type=click.Path(),
              help='Output directory for backup')
@click.option('--compress', is_flag=True,
              help='Compress backup files')
def backup(output: str, compress: bool):
    """Backup all databases.

    Creates a timestamped backup of all database files.
    """
    adapter = OutputAdapter()

    try:
        # Create timestamped backup directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(output, f"stom_backup_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)

        click.echo(OutputAdapter.format_info(f"Backing up databases to {backup_dir}"))

        backed_up = []
        total_size = 0

        for db_name, db_path in DB_MAP.items():
            if os.path.exists(db_path):
                dest_path = os.path.join(backup_dir, os.path.basename(db_path))
                shutil.copy2(db_path, dest_path)

                file_size = os.path.getsize(dest_path)
                total_size += file_size
                backed_up.append({
                    'database': db_name,
                    'file': os.path.basename(db_path),
                    'size_mb': round(file_size / (1024 * 1024), 2)
                })

                click.echo(OutputAdapter.format_info(f"Backed up {db_name}"))

        # Create backup manifest
        manifest_path = os.path.join(backup_dir, 'manifest.txt')
        with open(manifest_path, 'w') as f:
            f.write(f"STOM Database Backup\n")
            f.write(f"Created: {timestamp}\n")
            f.write(f"Total Size: {total_size / (1024 * 1024):.2f} MB\n")
            f.write(f"Files: {len(backed_up)}\n\n")
            for item in backed_up:
                f.write(f"{item['database']}: {item['file']} ({item['size_mb']} MB)\n")

        # Compress if requested
        if compress:
            click.echo(OutputAdapter.format_info("Compressing backup..."))
            archive_path = shutil.make_archive(backup_dir, 'zip', backup_dir)
            shutil.rmtree(backup_dir)
            click.echo(OutputAdapter.format_success(f"Backup created: {archive_path}"))
        else:
            click.echo(OutputAdapter.format_success(f"Backup created: {backup_dir}"))

        click.echo(OutputAdapter.format_info(f"Total size: {total_size / (1024 * 1024):.2f} MB"))
        logger.info(f"Database backup created: {backup_dir}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(f"Failed to backup databases: {str(e)}"))
        logger.error(f"Database backup failed: {str(e)}")
        raise click.Abort()


def _create_backtest_schema(cursor: sqlite3.Cursor):
    """Create backtest database schema."""
    # Example schema - adjust based on actual STOM schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_return REAL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _create_tradelist_schema(cursor: sqlite3.Cursor):
    """Create tradelist database schema."""
    # Example schema - adjust based on actual STOM schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            trade_time TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
