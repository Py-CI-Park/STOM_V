# STOM CLI User Manual

**Version**: 2.36.U1.5.C2.0
**System Trading Open Machine - Command Line Interface**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [For AI Agents (Claude Code Integration)](#for-ai-agents-claude-code-integration)
3. [Command Reference](#command-reference)
4. [Output Formats](#output-formats)
5. [Docker Usage](#docker-usage)
6. [Troubleshooting](#troubleshooting)
7. [Examples](#examples)

---

## Quick Start

### Installation

STOM CLI requires Python 3.8+ with the following dependencies:

```bash
pip install click pandas sqlite3 openpyxl
```

### Running the CLI

Ensure you are in the STOM project root directory:

```bash
python -m cli.main --help
```

Or directly:

```bash
python cli/main.py --help
```

### View Version

```bash
stom --version
# Output: stom, version 2.36.U1.5.C2.0
```

### First Commands to Try

```bash
# View all available commands
stom --help

# List all strategies
stom strategy list

# View backtest jobs
stom backtest list

# Check trading status
stom trade status

# Monitor live prices (stock)
stom monitor live --type stock --interval 5
```

---

## For AI Agents (Claude Code Integration)

This section documents how AI agents like Claude Code should interact with STOM CLI for automation and integration.

### Core Integration Principles

1. **JSON Output**: Always use `--format json` for machine parsing
2. **Error Handling**: Check exit codes and error messages in output
3. **Database State**: Verify database connections before operations
4. **Async Operations**: Use `--async` flag for non-blocking operations

### How AI Agents Should Use STOM CLI

#### Strategy Management Automation

AI agents can programmatically manage strategies:

```bash
# Export strategy to JSON (for version control)
stom strategy export "MyStrategy" output.json --format json

# Import strategy from configuration
stom strategy import --file strategy_config.json --type stock

# Validate strategy syntax before backtesting
stom strategy validate --name "MyStrategy" --type stock --buy

# Get strategy statistics as JSON for analysis
stom strategy stats --format json
```

**JSON Response Example**:
```json
{
  "Total Strategies": 3,
  "Strategies": {
    "stockbuy": 5,
    "stocksell": 3,
    "coinbuy": 2
  }
}
```

#### Backtesting Automation

Run automated backtests with JSON output for analysis:

```bash
# Run synchronous backtest and capture result
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --betting 10 \
  --format json

# Async: Register backtest and monitor separately
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --async \
  --format json

# Check backtest status
stom backtest status 20240115_143022 --format json

# List all backtest jobs with filtering
stom backtest list --limit 100 --status completed --format json
```

**JSON Status Response**:
```json
{
  "id": "20240115_143022",
  "status": "completed",
  "buy_strategy": "GoldenCross",
  "sell_strategy": "StopLoss",
  "type": "stock",
  "start_date": "20240101",
  "end_date": "20240131",
  "betting": 10.0,
  "created_at": "2024-01-15T14:30:22",
  "completed_at": "2024-01-15T15:45:33"
}
```

#### Optimization Workflows

Automate parameter optimization with multiple strategies:

```bash
# Grid search optimization
stom optimize grid \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --params '{"var1": [10, 20, 30], "var2": [0.5, 1.0, 1.5]}' \
  --format json

# Bayesian optimization (Optuna)
stom optimize bayesian \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --trials 100 \
  --format json

# Check optimization progress
stom optimize status grid_20240115_143022 --format json

# Genetic algorithm optimization (long-running)
stom optimize ga \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --generations 50 \
  --async \
  --format json
```

#### Data Analysis for AI

Extract trade data for ML analysis:

```bash
# Get trade history as JSON
stom data trades --type stock --format json

# Export all trades to CSV for analysis
stom data export --type trades --output trades.csv --format csv

# Get summary statistics
stom data summary --type stock --format json
```

**Trade Summary JSON**:
```json
{
  "Total Trades": 156,
  "Win Rate": 62.5,
  "Profit": 450000.0,
  "Loss": -120000.0,
  "Net Profit": 330000.0,
  "By Type": {
    "stockbuy": {
      "Count": 78,
      "Wins": 50,
      "Losses": 28,
      "Profit": 250000.0,
      "Loss": -80000.0
    }
  }
}
```

#### Database Management in CI/CD Pipelines

Automate database operations:

```bash
# Create backup before major changes
stom db backup --output ./backups --compress

# Get database statistics
stom db info --type backtest --format json

# Vacuum all databases for optimization
stom db vacuum --type all --yes

# Delete old test data
stom db delete --type stock --date 20230101 --yes
```

### Error Handling Patterns

AI agents should implement error handling:

```python
import subprocess
import json
import sys

def run_stom_command(args: list) -> tuple[int, dict]:
    """Run STOM CLI command and return exit code and JSON output."""
    try:
        result = subprocess.run(
            ['python', '-m', 'cli.main'] + args,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Check exit code
        if result.returncode != 0:
            return result.returncode, {'error': result.stderr}

        # Parse JSON output if requested
        if '--format json' in args and result.stdout:
            try:
                return 0, json.loads(result.stdout)
            except json.JSONDecodeError:
                return 1, {'error': 'Invalid JSON output', 'raw': result.stdout}

        return 0, {'output': result.stdout}

    except subprocess.TimeoutExpired:
        return 124, {'error': 'Command timeout'}
    except Exception as e:
        return 1, {'error': str(e)}

# Usage in automation
exit_code, result = run_stom_command([
    'backtest', 'run',
    '--type', 'stock',
    '--buy-strategy', 'Golden Cross',
    '--sell-strategy', 'Stop Loss',
    '--start-date', '20240101',
    '--end-date', '20240131',
    '--format', 'json'
])

if exit_code == 0:
    backtest_id = result.get('id')
    print(f"Backtest started: {backtest_id}")
else:
    print(f"Error: {result.get('error')}")
```

### Recommended Automation Scripts

#### Automated Daily Backtest

```bash
#!/bin/bash
# Daily backtest runner

YESTERDAY=$(date -d yesterday +%Y%m%d)
WEEK_AGO=$(date -d '7 days ago' +%Y%m%d)

# Run backtest for last week
python -m cli.main backtest run \
  --type stock \
  --buy-strategy "DailyStrategy" \
  --sell-strategy "DailyStop" \
  --start-date $WEEK_AGO \
  --end-date $YESTERDAY \
  --format json \
  --async

# List recent backtests
python -m cli.main backtest list --limit 10 --format json
```

#### Batch Strategy Validation

```bash
#!/bin/bash
# Validate all strategies before optimization

for strategy in GoldenCross MACD RSI; do
  echo "Validating $strategy..."
  python -m cli.main strategy validate \
    --name "$strategy" \
    --type stock \
    --buy
done
```

#### Trade Analysis Pipeline

```bash
#!/bin/bash
# Extract, analyze, and report trades

# Export all trades
python -m cli.main data export \
  --type trades \
  --output trades_$(date +%Y%m%d).csv

# Get statistics
python -m cli.main data summary \
  --type stock \
  --format json > trade_stats_$(date +%Y%m%d).json
```

---

## Command Reference

### strategy - Strategy Management

Manage trading strategies stored in SQLite databases.

#### strategy list

List all registered strategies with optional type filtering.

```bash
stom strategy list [OPTIONS]

Options:
  --type [stock|coin|future]  Filter by strategy type
  --format [table|json|csv]   Output format (default: table)
  --help                      Show help message
```

**Examples**:
```bash
# List all strategies (table format)
stom strategy list

# List only stock strategies (JSON format for parsing)
stom strategy list --type stock --format json

# Export to CSV
stom strategy list --format csv > strategies.csv
```

**Output (table)**:
```
전략타입    테이블          name          code                              created_at
stock       stockbuy        GoldenCross   import ta; def signal...          2024-01-01 10:00:00
stock       stocksell       StopLoss      def check_loss(price)...          2024-01-01 10:05:00
coin        coinbuy         MomentumBot   def calculate_momentum...          2024-01-02 14:30:00
```

**Output (JSON)**:
```json
{
  "strategies": [
    {
      "전략타입": "stock",
      "테이블": "stockbuy",
      "name": "GoldenCross",
      "code": "import ta; def signal...",
      "created_at": "2024-01-01 10:00:00"
    }
  ]
}
```

---

#### strategy show

Display detailed information about a specific strategy.

```bash
stom strategy show STRATEGY_NAME [OPTIONS]

Arguments:
  STRATEGY_NAME               Name of the strategy to display

Options:
  --format [table|json|csv]   Output format (default: table)
```

**Examples**:
```bash
# View GoldenCross strategy
stom strategy show GoldenCross

# View as JSON
stom strategy show GoldenCross --format json
```

---

#### strategy export

Export a strategy to a file (CSV, JSON, or Excel).

```bash
stom strategy export STRATEGY_NAME OUTPUT_FILE [OPTIONS]

Arguments:
  STRATEGY_NAME               Name of the strategy
  OUTPUT_FILE                 Output file path

Options:
  --format [csv|json|excel]   Export format (default: csv)
```

**Examples**:
```bash
# Export to CSV
stom strategy export GoldenCross strategies/golden_cross.csv

# Export to JSON
stom strategy export GoldenCross strategies/golden_cross.json --format json

# Export to Excel
stom strategy export GoldenCross strategies/golden_cross.xlsx --format excel
```

---

#### strategy stats

Display strategy statistics and counts.

```bash
stom strategy stats [OPTIONS]

Options:
  --format [table|json]       Output format (default: table)
```

**Examples**:
```bash
stom strategy stats
stom strategy stats --format json
```

**Output (table)**:
```
============================================================
전략 통계
============================================================

총 전략 수: 5

전략별 항목 수:
  stockbuy: 3
  stocksell: 2
  coinbuy: 2
```

---

#### strategy save

Save or update a strategy from inline code or file.

```bash
stom strategy save [OPTIONS]

Options:
  --name TEXT                 Strategy name (required)
  --type [stock|coin|future]  Strategy type (required)
  --buy/--sell                Buy or sell strategy (default: buy)
  --code TEXT                 Inline Python code
  --file PATH                 Strategy code file path
```

**Examples**:
```bash
# Save from inline code
stom strategy save \
  --name "MyStrategy" \
  --type stock \
  --code "def signal(): return True"

# Save from file
stom strategy save \
  --name "GoldenCross" \
  --type stock \
  --buy \
  --file strategies/golden_cross.py

# Save sell strategy
stom strategy save \
  --name "StopLoss" \
  --type stock \
  --sell \
  --code "def stop_loss(price): return price < entry * 0.95"
```

---

#### strategy delete

Delete a strategy (requires confirmation).

```bash
stom strategy delete [OPTIONS]

Options:
  --name TEXT                 Strategy name (required)
  --type [stock|coin|future]  Strategy type (required)
  --buy/--sell                Buy or sell strategy (default: buy)
```

**Examples**:
```bash
stom strategy delete --name "OldStrategy" --type stock --buy
# Prompts: "정말로 삭제하시겠습니까? (y/N)"
```

---

#### strategy import

Import strategies from JSON or CSV files.

```bash
stom strategy import [OPTIONS]

Options:
  --file PATH                 Import file path (required)
  --type [stock|coin|future]  Strategy type (required)
```

**Examples**:
```bash
# Import from JSON
stom strategy import --file strategies.json --type stock

# Import from CSV
stom strategy import --file strategies.csv --type coin
```

**Expected CSV/JSON Format**:
```csv
name,code,table
GoldenCross,"def signal()...",stockbuy
StopLoss,"def stop()...",stocksell
```

---

#### strategy validate

Validate strategy syntax and structure.

```bash
stom strategy validate [OPTIONS]

Options:
  --name TEXT                 Strategy name (required)
  --type [stock|coin|future]  Strategy type (required)
  --buy/--sell                Buy or sell strategy (default: buy)
```

**Examples**:
```bash
stom strategy validate --name "GoldenCross" --type stock --buy
```

**Output**:
```
============================================================
전략 유효성 검사: GoldenCross
============================================================

전략 코드가 유효합니다.
```

---

### data - Data Query and Export

Query trade data and backtest results.

#### data backtest-list

List recent backtest results.

```bash
stom data backtest-list [OPTIONS]

Options:
  --limit INTEGER             Maximum results (default: 20)
  --format [table|json|csv]   Output format (default: table)
```

---

#### data backtest-result

Get detailed backtest result for a specific ID.

```bash
stom data backtest-result BACKTEST_ID [OPTIONS]

Arguments:
  BACKTEST_ID                 Backtest result ID

Options:
  --format [table|json|csv]   Output format (default: table)
```

---

#### data trades

Query trade history with filtering.

```bash
stom data trades [OPTIONS]

Options:
  --type [stock|coin|future]  Filter by asset type
  --status [open|closed|cancelled]  Filter by trade status
  --limit INTEGER             Maximum results (default: 50)
  --format [table|json|csv]   Output format (default: table)
```

**Examples**:
```bash
# View all recent trades
stom data trades --limit 100

# View closed stock trades
stom data trades --type stock --status closed --format json

# Export to CSV for analysis
stom data trades --format csv > all_trades.csv
```

---

#### data summary

Show summary statistics for all trades.

```bash
stom data summary [OPTIONS]

Options:
  --type [stock|coin|future]  Filter by asset type
  --format [table|json]       Output format (default: table)
```

**Examples**:
```bash
stom data summary --type stock
stom data summary --format json
```

**Output (JSON)**:
```json
{
  "Total Trades": 156,
  "Win Rate": 62.5,
  "Profit": 450000.0,
  "Loss": -120000.0,
  "Net Profit": 330000.0,
  "By Type": {
    "stockbuy": {
      "Count": 78,
      "Wins": 50,
      "Losses": 28,
      "Profit": 250000.0,
      "Loss": -80000.0
    }
  }
}
```

---

#### data export

Export backtest results or trade history.

```bash
stom data export [OPTIONS]

Options:
  --type [backtest|trades]    Data type to export (required)
  --output PATH               Output file path (required)
  --format [csv|json|excel]   Export format (default: csv)
```

**Examples**:
```bash
# Export all trades to CSV
stom data export --type trades --output trades.csv

# Export backtest results to JSON
stom data export --type backtest --output results.json --format json

# Export to Excel
stom data export --type trades --output trades.xlsx --format excel
```

---

### backtest - Backtesting Engine

Run and manage backtests.

#### backtest run

Execute a backtest with specified strategies and parameters.

```bash
stom backtest run [OPTIONS]

Options:
  --buy-strategy TEXT         Buy strategy name (required)
  --sell-strategy TEXT        Sell strategy name (required)
  --type [stock|coin|future]  Asset type (required)
  --start-date TEXT           Start date: YYYYMMDD or YYYY-MM-DD (required)
  --end-date TEXT             End date: YYYYMMDD or YYYY-MM-DD (required)
  --start-time TEXT           Start time: HHMMSS or HHMM (optional)
  --end-time TEXT             End time: HHMMSS or HHMM (optional)
  --betting FLOAT             Betting amount (default: 1.0)
                              stock: million won, coin: USDT, future: contracts
  --avgtime INTEGER           Average ticks for calculation (default: 20)
  --multi INTEGER             Multiprocess count (default: 1)
  --divid-mode TEXT           Data division mode (default: 종목코드별 분류)
  --blacklist/--no-blacklist  Auto-add blacklist (default: false)
  --format [table|json]       Output format (default: table)
  --async                     Async execution (register job only)
```

**Examples**:
```bash
# Basic backtest
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --betting 10

# Async backtest (non-blocking)
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --betting 10 \
  --async \
  --format json

# Multiprocess backtest
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240228 \
  --multi 4 \
  --betting 10

# With specific trading hours (9:30 AM - 3:30 PM)
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --start-time 093000 \
  --end-time 153000 \
  --betting 10
```

---

#### backtest status

Check the status of a backtest job.

```bash
stom backtest status BACKTEST_ID [OPTIONS]

Arguments:
  BACKTEST_ID                 Backtest job ID (format: YYYYMMDD_HHMMSS)

Options:
  --format [table|json]       Output format (default: table)
```

**Examples**:
```bash
# Check backtest status
stom backtest status 20240115_143022

# Get JSON output for parsing
stom backtest status 20240115_143022 --format json
```

**Output (JSON)**:
```json
{
  "id": "20240115_143022",
  "buy_strategy": "GoldenCross",
  "sell_strategy": "StopLoss",
  "type": "stock",
  "start_date": "20240101",
  "end_date": "20240131",
  "betting": 10.0,
  "avgtime": 20,
  "multi": 1,
  "divid_mode": "종목코드별 분류",
  "blacklist": 0,
  "async": 0,
  "created_at": "2024-01-15T14:30:22",
  "started_at": "2024-01-15T14:30:23",
  "completed_at": "2024-01-15T15:45:33",
  "status": "completed"
}
```

---

#### backtest list

List all backtest jobs with optional filtering.

```bash
stom backtest list [OPTIONS]

Options:
  --limit INTEGER             Maximum results (default: 20)
  --status [pending|running|completed|failed]  Filter by status
  --format [table|json|csv]   Output format (default: table)
```

**Examples**:
```bash
# List recent backtests
stom backtest list --limit 50

# List completed backtests
stom backtest list --status completed --limit 100 --format json

# List failed backtests
stom backtest list --status failed
```

---

#### backtest cancel

Cancel a pending or running backtest.

```bash
stom backtest cancel BACKTEST_ID
```

**Examples**:
```bash
stom backtest cancel 20240115_143022
# Output: 백테스트 '20240115_143022'이 취소되었습니다.
```

---

#### backtest delete

Delete a backtest job from database.

```bash
stom backtest delete BACKTEST_ID
```

**Note**: Requires confirmation prompt.

---

### trade - Trading Control

Start/stop trading and manage positions/orders.

#### trade start

Start automatic trading for specified asset type.

```bash
stom trade start [OPTIONS]

Options:
  --type [stock|coin|future]  Asset type (required)
  --format [table|json]       Output format (default: table)
```

**Examples**:
```bash
stom trade start --type stock
stom trade start --type coin --format json
```

**Note**: CLI only updates status; actual trading requires STOM main application.

---

#### trade stop

Stop automatic trading.

```bash
stom trade stop [OPTIONS]

Options:
  --type [stock|coin|future|all]  Asset type to stop (default: all)
  --format [table|json]           Output format (default: table)
```

**Examples**:
```bash
# Stop all trading
stom trade stop

# Stop only stock trading
stom trade stop --type stock

# Stop multiple types with format
stom trade stop --type coin --format json
```

---

#### trade status

Check current trading status and configuration.

```bash
stom trade status [OPTIONS]

Options:
  --format [table|json]       Output format (default: table)
```

**Examples**:
```bash
stom trade status
stom trade status --format json
```

**Output (table)**:
```
======================================================================
트레이딩 상태
======================================================================

[실행 상태]

STOCK:
  상태: running
  시작 시간: 2024-01-15T09:30:00
  마지막 업데이트: 2024-01-15T14:30:00

COIN:
  상태: stopped
  마지막 업데이트: 2024-01-14T18:00:00

[설정 정보]

MAIN:
  setting_version: 2.36
  ...
```

---

#### positions list

List current positions.

```bash
stom positions list [OPTIONS]

Options:
  --type [stock|coin|future]  Filter by asset type
  --format [table|json|csv]   Output format (default: table)
```

**Examples**:
```bash
# List all positions
stom positions list

# List stock positions only
stom positions list --type stock

# Export to JSON
stom positions list --format json
```

---

#### positions close

Close specified positions.

```bash
stom positions close [OPTIONS]

Options:
  --all                       Close all positions
  --code TEXT                 Close specific asset code
  --type [stock|coin|future]  Asset type (with --all)
```

**Examples**:
```bash
# Close all stock positions
stom positions close --all --type stock

# Close specific position
stom positions close --code 005930
```

**Note**: Creates close order; actual execution requires STOM main application.

---

#### orders list

List pending and filled orders.

```bash
stom orders list [OPTIONS]

Options:
  --type [stock|coin|future]  Filter by asset type
  --status [pending|filled|cancelled]  Filter by status
  --format [table|json|csv]   Output format (default: table)
```

**Examples**:
```bash
# List all pending orders
stom orders list --status pending

# List stock orders
stom orders list --type stock --format json
```

---

#### orders cancel

Cancel pending orders.

```bash
stom orders cancel [OPTIONS]

Options:
  --all                       Cancel all pending orders
  --id TEXT                   Cancel specific order ID
  --type [stock|coin|future]  Asset type (with --all)
```

**Examples**:
```bash
# Cancel all stock orders
stom orders cancel --all --type stock

# Cancel specific order
stom orders cancel --id 12345
```

**Note**: Creates cancel request; actual execution requires STOM main application.

---

### monitor - Real-time Monitoring

Monitor live prices, P&L, and position changes.

#### monitor live

Display real-time price information.

```bash
stom monitor live [OPTIONS]

Options:
  --type [stock|coin|future]  Asset type (required)
  --interval INTEGER          Update interval in seconds (default: 5)
  --count INTEGER             Update count (0: infinite, default: 0)
  --limit INTEGER             Assets to display (default: 10)
  --format [table|json]       Output format (default: table)
```

**Examples**:
```bash
# Monitor stock prices every 5 seconds
stom monitor live --type stock

# Monitor coin prices every 3 seconds for 10 updates
stom monitor live --type coin --interval 3 --count 10

# Show 20 assets
stom monitor live --type stock --limit 20
```

**Output (table - refreshes automatically)**:
```
================================================================================
실시간 가격 (STOCK) - 2024-01-15 14:30:45
업데이트: 5회 | 간격: 5초
================================================================================
종목코드  현재가    등락율    거래량      체결시간
005930   70500.0  +2.5%    1234567    2024-01-15 14:30:45
051910   62400.0  -1.2%    567890     2024-01-15 14:30:44
...
```

---

#### monitor pnl

Display real-time profit and loss.

```bash
stom monitor pnl [OPTIONS]

Options:
  --type [stock|coin|future]  Asset type (required)
  --interval INTEGER          Update interval in seconds (default: 5)
  --count INTEGER             Update count (0: infinite, default: 0)
  --format [table|json]       Output format (default: table)
  --details/--no-details      Show position details (default: false)
```

**Examples**:
```bash
# Monitor stock P&L every 5 seconds
stom monitor pnl --type stock

# Monitor coin P&L with details
stom monitor pnl --type coin --details

# Get P&L as JSON
stom monitor pnl --type stock --count 1 --format json
```

**Output (JSON)**:
```json
{
  "total_pnl": 450000.0,
  "realized_pnl": 0.0,
  "unrealized_pnl": 450000.0,
  "position_count": 5,
  "details": [
    {
      "종목코드": "005930",
      "종목명": "Samsung",
      "수량": 100,
      "평균단가": 70000.0,
      "현재가": 70500.0,
      "수익금": 50000.0,
      "수익률": 0.71
    }
  ]
}
```

---

#### monitor positions

Track position changes in real-time.

```bash
stom monitor positions [OPTIONS]

Options:
  --type [stock|coin|future]  Asset type (required)
  --interval INTEGER          Update interval in seconds (default: 5)
  --count INTEGER             Update count (0: infinite, default: 0)
  --format [table|json]       Output format (default: table)
  --alert/--no-alert          Show changes (default: false)
```

**Examples**:
```bash
# Monitor position changes
stom monitor positions --type stock --alert

# Check once
stom monitor positions --type coin --count 1
```

---

### optimize - Strategy Optimization

Find optimal parameters using various algorithms.

#### optimize grid

Grid search over all parameter combinations.

```bash
stom optimize grid [OPTIONS]

Options:
  --type [stock|coin|future]  Asset type (required)
  --buy-strategy TEXT         Buy strategy name (required)
  --sell-strategy TEXT        Sell strategy name (required)
  --start-date TEXT           Start date: YYYYMMDD (required)
  --end-date TEXT             End date: YYYYMMDD (required)
  --params TEXT               Grid parameters as JSON (required)
  --betting FLOAT             Betting amount (default: 1.0)
  --format [table|json]       Output format (default: table)
  --async                     Async execution
```

**Examples**:
```bash
# Simple grid search
stom optimize grid \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --params '{"ma_short": [10, 20], "ma_long": [50, 100]}'

# Async grid search
stom optimize grid \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --params '{"ma_short": [10, 20, 30], "ma_long": [50, 100, 150, 200]}' \
  --async \
  --format json
```

---

#### optimize bayesian

Bayesian optimization using Optuna.

```bash
stom optimize bayesian [OPTIONS]

Options:
  --type [stock|coin|future]  Asset type (required)
  --buy-strategy TEXT         Buy strategy name (required)
  --sell-strategy TEXT        Sell strategy name (required)
  --start-date TEXT           Start date: YYYYMMDD (required)
  --end-date TEXT             End date: YYYYMMDD (required)
  --trials INTEGER            Number of trials (required)
  --betting FLOAT             Betting amount (default: 1.0)
  --format [table|json]       Output format (default: table)
  --async                     Async execution
```

**Examples**:
```bash
# Run 100 trials
stom optimize bayesian \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --trials 100

# Async with high trial count
stom optimize bayesian \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --trials 500 \
  --async \
  --format json
```

---

#### optimize ga

Genetic algorithm optimization.

```bash
stom optimize ga [OPTIONS]

Options:
  --type [stock|coin|future]  Asset type (required)
  --buy-strategy TEXT         Buy strategy name (required)
  --sell-strategy TEXT        Sell strategy name (required)
  --start-date TEXT           Start date: YYYYMMDD (required)
  --end-date TEXT             End date: YYYYMMDD (required)
  --generations INTEGER       Number of generations (required)
  --betting FLOAT             Betting amount (default: 1.0)
  --format [table|json]       Output format (default: table)
  --async                     Async execution
```

**Examples**:
```bash
# Run 50 generations
stom optimize ga \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --generations 50

# Async with more generations
stom optimize ga \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --generations 100 \
  --async
```

---

#### optimize walkforward

Walk-forward analysis for robust validation.

```bash
stom optimize walkforward [OPTIONS]

Options:
  --type [stock|coin|future]  Asset type (required)
  --strategy TEXT             Strategy name (required)
  --start-date TEXT           Start date: YYYYMMDD (required)
  --end-date TEXT             End date: YYYYMMDD (required)
  --train-weeks INTEGER       Training period in weeks (default: 4)
  --valid-weeks INTEGER       Validation period in weeks (default: 1)
  --test-weeks INTEGER        Testing period in weeks (default: 1)
  --betting FLOAT             Betting amount (default: 1.0)
  --format [table|json]       Output format (default: table)
  --async                     Async execution
```

**Examples**:
```bash
# Standard walk-forward
stom optimize walkforward \
  --type stock \
  --strategy "GoldenCross" \
  --start-date 20240101 \
  --end-date 20240331 \
  --train-weeks 4 \
  --valid-weeks 1 \
  --test-weeks 1

# Custom periods
stom optimize walkforward \
  --type stock \
  --strategy "GoldenCross" \
  --start-date 20240101 \
  --end-date 20240630 \
  --train-weeks 8 \
  --valid-weeks 2 \
  --test-weeks 2 \
  --async
```

---

#### optimize backfinder

Automatic variable combination discovery.

```bash
stom optimize backfinder [OPTIONS]

Options:
  --type [stock|coin|future]  Asset type (required)
  --start-date TEXT           Start date: YYYYMMDD (required)
  --end-date TEXT             End date: YYYYMMDD (required)
  --betting FLOAT             Betting amount (default: 1.0)
  --min-profit FLOAT          Minimum profit filter % (default: 0.0)
  --format [table|json]       Output format (default: table)
  --async                     Async execution
```

**Examples**:
```bash
# Find profitable combinations
stom optimize backfinder \
  --type stock \
  --start-date 20240101 \
  --end-date 20240131 \
  --min-profit 5.0

# Async backfinder
stom optimize backfinder \
  --type stock \
  --start-date 20240101 \
  --end-date 20240331 \
  --min-profit 3.0 \
  --async
```

---

#### optimize status

Check optimization job status.

```bash
stom optimize status JOB_ID [OPTIONS]

Arguments:
  JOB_ID                      Optimization job ID

Options:
  --format [table|json]       Output format (default: table)
```

---

#### optimize list

List optimization jobs.

```bash
stom optimize list [OPTIONS]

Options:
  --limit INTEGER             Maximum results (default: 20)
  --type [grid|bayesian|ga|walkforward|backfinder]  Filter by type
  --status [pending|running|completed|failed]       Filter by status
  --format [table|json|csv]   Output format (default: table)
```

---

#### optimize cancel

Cancel an optimization job.

```bash
stom optimize cancel JOB_ID
```

---

#### optimize delete

Delete an optimization job.

```bash
stom optimize delete JOB_ID
```

---

### db - Database Management

Manage STOM databases.

#### db create

Create a new database with schema.

```bash
stom db create [OPTIONS]

Options:
  --type [backtest|tradelist]  Database type (required)
  --force                      Overwrite if exists
```

**Examples**:
```bash
stom db create --type backtest
stom db create --type tradelist --force
```

---

#### db append

Append historical data to database.

```bash
stom db append [OPTIONS]

Options:
  --type [stock|coin|future]  Data type (required)
  --date TEXT                 Date in YYYYMMDD format (required)
  --source PATH               Source file or directory
```

---

#### db delete

Delete data by date.

```bash
stom db delete [OPTIONS]

Options:
  --type [stock|coin|future]  Data type (required)
  --date TEXT                 Date in YYYYMMDD format (required)
  --yes                       Skip confirmation
```

**Examples**:
```bash
stom db delete --type stock --date 20230101
stom db delete --type coin --date 20240101 --yes
```

---

#### db info

Show database information and statistics.

```bash
stom db info [OPTIONS]

Options:
  --type [backtest|tradelist|strategy|setting|stock_tick|stock_min|coin_tick|coin_min]  (required)
  --format [table|json|csv]   Output format (default: table)
```

**Examples**:
```bash
stom db info --type backtest
stom db info --type tradelist --format json
```

**Output (JSON)**:
```json
{
  "database": "./_database/backtest.db",
  "size_mb": 45.32,
  "modified": "2024-01-15 14:30:00",
  "tables": 3,
  "total_rows": 1250
}
```

---

#### db vacuum

Optimize database performance.

```bash
stom db vacuum [OPTIONS]

Options:
  --type [all|backtest|tradelist|...]  Database type (required)
  --yes                                Skip confirmation
```

**Examples**:
```bash
stom db vacuum --type all --yes
stom db vacuum --type backtest
```

---

#### db backup

Create timestamped backup of databases.

```bash
stom db backup [OPTIONS]

Options:
  --output PATH               Output directory (required)
  --compress                  Compress backup as ZIP
```

**Examples**:
```bash
# Create backup
stom db backup --output ./backups

# Create compressed backup
stom db backup --output ./backups --compress
```

---

## Output Formats

### Table Format (Default)

Human-readable tabular output using ASCII formatting.

```bash
stom strategy list --format table
```

**Example Output**:
```
전략타입    테이블          name          code                code_sample
stock       stockbuy        GoldenCross   import ta; def...   (truncated)
stock       stocksell       StopLoss      def check_loss...   (truncated)
```

### JSON Format

Machine-parseable JSON output for automation and integration.

```bash
stom strategy list --format json
```

**Example Output**:
```json
{
  "strategies": [
    {
      "전략타입": "stock",
      "테이블": "stockbuy",
      "name": "GoldenCross",
      "code": "import ta\ndef signal():\n  ..."
    }
  ]
}
```

**JSON Parsing in Python**:
```python
import json
import subprocess

result = subprocess.run(
    ['python', '-m', 'cli.main', 'strategy', 'list', '--format', 'json'],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)
for strategy in data.get('strategies', []):
    print(f"{strategy['name']} ({strategy['전략타입']})")
```

### CSV Format

Comma-separated values for spreadsheet import.

```bash
stom data trades --format csv > trades.csv
```

**Example Output**:
```csv
거래날짜,거래시간,자산,매수가,매도가,수익금
20240101,093000,005930,70000,70500,50000
20240102,140000,051910,62000,61900,-10000
```

---

## Docker Usage

### Building the Docker Image

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /stom

# Copy project files
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Set entrypoint to CLI
ENTRYPOINT ["python", "-m", "cli.main"]
```

**Build command**:
```bash
docker build -t stom-cli:latest .
```

### Running STOM CLI in Docker

```bash
# Run backtest in container
docker run --rm \
  -v $(pwd)/data:/stom/data \
  -v $(pwd)/_database:/stom/_database \
  stom-cli:latest backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20240101 \
  --end-date 20240131

# Get strategy list
docker run --rm \
  -v $(pwd)/_database:/stom/_database \
  stom-cli:latest strategy list --format json
```

### Docker Compose Example

```yaml
version: '3.8'

services:
  stom-cli:
    build: .
    image: stom-cli:latest
    volumes:
      - ./_database:/stom/_database
      - ./strategies:/stom/strategies
      - ./data:/stom/data
    environment:
      - PYTHONUNBUFFERED=1
    command: backtest run --type stock --buy-strategy "GoldenCross" --sell-strategy "StopLoss" --start-date 20240101 --end-date 20240131
```

**Run with docker-compose**:
```bash
docker-compose run --rm stom-cli strategy list
docker-compose run --rm stom-cli backtest run ...
```

---

## Troubleshooting

### Common Issues

#### "No module named 'cli'"

**Problem**: Python cannot find the CLI module.

**Solution**:
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run from project directory
cd /path/to/STOM_V
python -m cli.main --help
```

#### RuntimeWarning Messages

STOM may emit RuntimeWarnings about deprecated pandas or numpy features:

```
RuntimeWarning: invalid value encountered in sqrt
```

**Explanation**: These are typically from financial calculations or optimization algorithms encountering edge cases.

**Solution**: Warnings are non-fatal and can be suppressed:

```bash
python -W ignore::RuntimeWarning -m cli.main backtest run ...
```

#### Database Locked Error

**Problem**: "Database is locked" error during operations.

**Solution**:
```bash
# Vacuum/optimize database to fix locks
stom db vacuum --type backtest --yes

# Check for other processes using database
lsof _database/*.db  # On macOS/Linux
```

#### Strategy Not Found

**Problem**: "Strategy 'X' not found in database"

**Solution**:
```bash
# Verify strategy exists
stom strategy list --format json

# Check database directly
sqlite3 _database/strategy.db "SELECT name FROM stockbuy;"

# Save strategy if missing
stom strategy save --name "MyStrategy" --type stock --code "def signal(): return True"
```

#### Backtest Timeout

**Problem**: Backtest takes too long or times out.

**Solution**:
```bash
# Use async mode for long backtests
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20200101 \
  --end-date 20240131 \
  --async

# Use multiprocess to speed up
stom backtest run \
  --type stock \
  --buy-strategy "GoldenCross" \
  --sell-strategy "StopLoss" \
  --start-date 20200101 \
  --end-date 20240131 \
  --multi 4
```

#### Connection Refused

**Problem**: Cannot connect to data source.

**Solution**:
```bash
# Check if STOM main application is running
# Ensure database files exist in _database/

# Try creating databases if missing
stom db create --type backtest --force
stom db create --type tradelist --force
```

---

## Examples

### Complete Workflow: Strategy Development to Backtest

```bash
# 1. Create and save a strategy
stom strategy save \
  --name "MyGoldenCross" \
  --type stock \
  --buy \
  --code "
import ta

def signal(data):
    ma_short = ta.trend.sma_indicator(data['close'], 20)
    ma_long = ta.trend.sma_indicator(data['close'], 50)
    return ma_short > ma_long
"

# 2. Create sell strategy
stom strategy save \
  --name "MyStopLoss" \
  --type stock \
  --sell \
  --code "
def signal(price, entry_price):
    return price < entry_price * 0.95
"

# 3. Validate strategies
stom strategy validate --name "MyGoldenCross" --type stock --buy
stom strategy validate --name "MyStopLoss" --type stock --sell

# 4. Run backtest
stom backtest run \
  --type stock \
  --buy-strategy "MyGoldenCross" \
  --sell-strategy "MyStopLoss" \
  --start-date 20240101 \
  --end-date 20240131 \
  --betting 10 \
  --multi 2

# 5. Check backtest status
stom backtest list --limit 5 --format json

# 6. Analyze results
stom data summary --type stock --format json
```

### AI Agent: Automated Parameter Optimization Pipeline

```python
#!/usr/bin/env python3
"""
Automated optimization pipeline for STOM CLI.
Runs multiple optimization algorithms in parallel.
"""

import subprocess
import json
import time
from datetime import datetime, timedelta

def run_stom(args):
    """Execute STOM CLI command and return JSON result."""
    result = subprocess.run(
        ['python', '-m', 'cli.main'] + args,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except:
            return {'output': result.stdout}
    else:
        raise Exception(result.stderr)

# Configuration
asset_type = 'stock'
buy_strategy = 'GoldenCross'
sell_strategy = 'StopLoss'
end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

# 1. Grid Search
print("Running Grid Search...")
grid_result = run_stom([
    'optimize', 'grid',
    '--type', asset_type,
    '--buy-strategy', buy_strategy,
    '--sell-strategy', sell_strategy,
    '--start-date', start_date,
    '--end-date', end_date,
    '--params', '{"ma_short": [10, 20], "ma_long": [50, 100]}',
    '--async',
    '--format', 'json'
])
grid_job_id = grid_result['id']
print(f"Grid job started: {grid_job_id}")

# 2. Bayesian Optimization
print("Running Bayesian Optimization...")
bayesian_result = run_stom([
    'optimize', 'bayesian',
    '--type', asset_type,
    '--buy-strategy', buy_strategy,
    '--sell-strategy', sell_strategy,
    '--start-date', start_date,
    '--end-date', end_date,
    '--trials', '100',
    '--async',
    '--format', 'json'
])
bayesian_job_id = bayesian_result['id']
print(f"Bayesian job started: {bayesian_job_id}")

# 3. Wait for completion
print("Waiting for optimization to complete...")
for job_id in [grid_job_id, bayesian_job_id]:
    while True:
        status = run_stom(['optimize', 'status', job_id, '--format', 'json'])
        if status['status'] in ['completed', 'failed']:
            print(f"Job {job_id}: {status['status']}")
            break
        time.sleep(10)

# 4. Compare results
grid_status = run_stom(['optimize', 'status', grid_job_id, '--format', 'json'])
bayesian_status = run_stom(['optimize', 'status', bayesian_job_id, '--format', 'json'])

print("\n=== RESULTS ===")
print(f"Grid Search Result: {grid_status.get('result', 'N/A')}")
print(f"Bayesian Result: {bayesian_status.get('result', 'N/A')}")
```

### Data Export and Analysis

```bash
# Export all trades for analysis
stom data export --type trades --output analysis/trades.csv --format csv

# Get summary statistics
stom data summary --type stock --format json > analysis/summary.json

# Export backtest results
stom data export --type backtest --output analysis/backtest.xlsx --format excel

# Analyze with Python
python << 'EOF'
import pandas as pd
import json

# Load trade data
trades = pd.read_csv('analysis/trades.csv')
print(f"Total trades: {len(trades)}")
print(f"Win rate: {(trades['수익금'] > 0).sum() / len(trades) * 100:.2f}%")
print(f"Total profit: {trades['수익금'].sum():,.0f}")

# Load summary
with open('analysis/summary.json') as f:
    summary = json.load(f)
print(f"\nNet Profit: {summary['Net Profit']:,.0f}")
print(f"By Type: {summary['By Type']}")
EOF
```

---

## Version History

- **2.36.U1.5.C2.0**: Current CLI version with full command reference
- **2.36.U1.5.C1.0**: Initial CLI development review release
- **2.36.U1**: ui_mainwindow migration from .pyd to .py

---

## Support and Documentation

For detailed architecture information, see:
- `docs/AGENTS.md` - AI agent integration guide
- `docs/change_log/` - Version-specific changelog
- `docs/update_log/` - Detailed update records by date

---

**Document Last Updated**: 2024-01-15
**Maintained by**: STOM Development Team
