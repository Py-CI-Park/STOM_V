# Wide v1 CLI Baseline GUI Compare Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Wide v1 full-year CLI baseline backtest, compare it against the known GUI/STOM baseline, and document a PASS/HOLD/FAIL gate decision before any candidate-count run.

**Architecture:** This is an execution-and-documentation plan, not a code feature. Use the merged PR #17 CLI path on `STOM_Version_2U_C`, capture runtime JSON/CSV under ignored backtest artifact paths, derive a compact comparison report from the CLI JSON and GUI baseline constants, and commit only Markdown evidence.

**Tech Stack:** Python 3.11, PowerShell, STOM CLI `stom_backtest.py`, JSON, CSV, pytest, `scripts/verify_nonrelease_sync.py`, Markdown docs.

---

## Scope

In scope:

- Confirm the branch is based on merge commit `ed344387` or newer.
- If feature worktree CLI execution still reads local `./_database`, patch legacy `utility.setting.py` to honor the same CLI DB override contract as `utility.setting_base.py`.
- Run Wide v1 `runtime-preflight` with the same DB/strategy/timeframe settings as GUI.
- Run one full-year CLI baseline backtest for `20250101~20251231`, `090000~092800`, tick, avg 30, engines 32.
- Compare CLI result with the GUI baseline constants.
- Record PASS/HOLD/FAIL in a pilot log and update log.
- Run verification and commit only docs.

Out of scope:

- Do not run `candidate_count=5`.
- Do not regenerate or optimize conditions.
- Do not run WFO/promote.
- Do not change CLI/backtest behavior beyond the legacy `utility.setting.py` DB override compatibility fix if it blocks feature worktree execution.
- Do not commit `_database`, `backtest/temp`, `backtest/csv`, or `backtest/graph` artifacts.

## File Structure

Create:

- `docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_cli_baseline_gui_compare.md`
  - Full execution evidence: preflight, CLI baseline, checkpoint summary, metric comparison, final decision.

- `docs/update_log/2026-04-22_wide_v1_cli_baseline_gui_compare.md`
  - Short project update: where this gate fits, result, remaining risks, next command.

Runtime-only files:

- `backtest/temp/wide_v1_cli_preflight_gui_compare_20260422.json`
  - Captured preflight JSON. Do not stage.

- `backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.json`
  - Captured CLI baseline JSON. Do not stage.

- `backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.stderr.log`
  - CLI stderr/protocol log if background execution is used. Do not stage.

- `backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.stdout.log`
  - CLI stdout log if background execution is used. Do not stage.

- `backtest/csv/stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_*.csv`
  - Generated CSV. Do not stage.

Code file that may be modified if the gate is blocked by worktree-local DB loading:

- `utility/setting.py`
  - Must use `STOM_CLI_DATABASE_DIR` and individual `STOM_CLI_DB_*` overrides for DB path constants while keeping `./_database` defaults when env vars are absent.

## Gate Constants

GUI baseline:

```text
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
start=20250101
end=20251231
timeframe=tick
avg_time=30
betting=20
start_time=90000
end_time=92800
engines=32
back_count=1638
trade_count=40937
win_rate=30.02
avg_profit_pct=-0.68
total_profit_pct=-695.09
total_profit_krw=-5564960005
mdd_pct=693.76
tpi=0.60
max_hold_count=40
avg_hold_time=228.19
runtime=0:01:00.675279
betting_amount=20,000,000원
gui_csv=C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

Decision rules:

```text
PASS:
  preflight status is ok
  CLI result status is success
  CLI checkpoint_status is success
  CLI last_checkpoint is csv_detected
  CLI csv_path exists
  CLI trade_count == 40937
  CLI back_count == 1638 or checkpoint-derived back_count == 1638

HOLD:
  CLI result status is success
  CLI csv_path exists
  CLI trade_count exists
  abs(CLI trade_count - 40937) / 40937 <= 0.001
  OR back_count cannot be confirmed from JSON/checkpoints

FAIL:
  preflight status is not ok
  CLI result status is error
  timeout occurred
  CLI csv_path missing
  CLI trade_count missing
  abs(CLI trade_count - 40937) / 40937 > 0.001
```

---

### Task 1: Workspace And Preflight

**Files:**
- Runtime only: `backtest/temp/wide_v1_cli_preflight_gui_compare_20260422.json`
- No tracked file changes.

- [ ] **Step 1: Confirm branch and base merge commit**

Run:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare
git status --short --branch --untracked-files=all
git log --oneline -5 --decorate
git merge-base --is-ancestor ed344387e0ef04aff6dee9b9abffd7c6158e6da4 HEAD
if ($LASTEXITCODE -ne 0) { throw 'branch is not based on PR #17 merge commit ed344387' }
```

Expected:

```text
## feature/wide-v1-cli-baseline-gui-compare
9f09d447 ... Wide v1 CLI baseline GUI 비교 설계를 작성한다
ed344387 ... Merge pull request #17 from Py-CI-Park/feature/cli-child-runtime-db-override
```

No tracked changes should be present before runtime commands.

- [ ] **Step 2: Create runtime temp directory**

Run:

```powershell
New-Item -ItemType Directory -Force backtest\temp | Out-Null
```

Expected:

```text
No output.
```

- [ ] **Step 3: Run runtime-preflight and save JSON**

Run:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
python stom_backtest.py runtime-preflight `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --betting 20 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900 `
  | Tee-Object -FilePath backtest\temp\wide_v1_cli_preflight_gui_compare_20260422.json
```

Expected:

```text
JSON is printed and written to backtest\temp\wide_v1_cli_preflight_gui_compare_20260422.json.
```

- [ ] **Step 4: Verify preflight fields**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path('backtest/temp/wide_v1_cli_preflight_gui_compare_20260422.json')
payload = json.loads(path.read_text(encoding='utf-8-sig'))

checks = {
    'status': payload.get('status'),
    'failed_checks': payload.get('failed_checks'),
    'validation_errors': payload.get('validation_errors'),
    'timeframe_match': payload.get('timeframe_match', {}).get('status'),
    'buy_status': payload.get('strategies', {}).get('buy', {}).get('status'),
    'sell_status': payload.get('strategies', {}).get('sell', {}).get('status'),
    'stock_back_db_usable': payload.get('runtime_profile', {}).get('stock_back_db_usable'),
    'stock_back_db_integrity': payload.get('runtime_profile', {}).get('stock_back_db_integrity'),
}
for key, value in checks.items():
    print(key, value)

if checks['status'] != 'ok':
    raise SystemExit(1)
if checks['failed_checks'] != []:
    raise SystemExit(1)
if checks['validation_errors'] != []:
    raise SystemExit(1)
if checks['timeframe_match'] != 'ok':
    raise SystemExit(1)
if checks['buy_status'] != 'ok':
    raise SystemExit(1)
if checks['sell_status'] != 'ok':
    raise SystemExit(1)
if checks['stock_back_db_usable'] is not True:
    raise SystemExit(1)
'@ | python -
```

Expected:

```text
status ok
failed_checks []
validation_errors []
timeframe_match ok
buy_status ok
sell_status ok
stock_back_db_usable True
stock_back_db_integrity table_probe_only
```

If this command exits non-zero, skip Task 2 and continue to Task 4 with `decision=FAIL`.

---

### Task 1A: Legacy Setting DB Override Fix If Needed

**Files:**
- Modify: `utility/setting.py`
- Modify: `tests/unit/test_setting_base_cli_overrides.py`

Run this task only if `python stom_backtest.py ...` fails before backtest execution with `utility.setting` opening a worktree-local empty `./_database/setting.db`.

- [ ] **Step 1: Add source contract test**

Append this test to `tests/unit/test_setting_base_cli_overrides.py`:

```python
def test_legacy_setting_uses_cli_database_override_resolver():
    content = Path('utility/setting.py').read_text(encoding='utf-8')

    assert "os.environ.get('STOM_CLI_DATABASE_DIR', './_database')" in content
    assert "def _resolve_db(filename, env_name):" in content
    assert "DB_SETTING          = _resolve_db('setting.db', 'STOM_CLI_DB_SETTING')" in content
    assert "DB_STRATEGY         = _resolve_db('strategy.db', 'STOM_CLI_DB_STRATEGY')" in content
    assert "DB_BACKTEST         = _resolve_db('backtest.db', 'STOM_CLI_DB_BACKTEST')" in content
    assert "DB_STOCK_BACK_TICK  = _resolve_db('stock_tick_back.db', 'STOM_CLI_DB_STOCK_BACK_TICK')" in content
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_setting_base_cli_overrides.py::test_legacy_setting_uses_cli_database_override_resolver -q
```

Expected:

```text
FAIL because utility.setting.py still hardcodes ./_database paths.
```

- [ ] **Step 3: Patch utility.setting DB constants**

In `utility/setting.py`, replace the hardcoded DB path section with the same resolver pattern used by `utility.setting_base`:

```python
DB_PATH             = os.environ.get('STOM_CLI_DATABASE_DIR', './_database')


def _resolve_db(filename, env_name):
    override = os.environ.get(env_name)
    if override:
        return override
    return f'{DB_PATH}/{filename}'


DB_SETTING          = _resolve_db('setting.db', 'STOM_CLI_DB_SETTING')
DB_BACKTEST         = _resolve_db('backtest.db', 'STOM_CLI_DB_BACKTEST')
DB_TRADELIST        = _resolve_db('tradelist.db', 'STOM_CLI_DB_TRADELIST')
DB_STRATEGY         = _resolve_db('strategy.db', 'STOM_CLI_DB_STRATEGY')
DB_OPTUNA           = f"sqlite:///{_resolve_db('optuna.db', 'STOM_CLI_DB_OPTUNA')}"
DB_STOCK_TICK       = _resolve_db('stock_tick.db', 'STOM_CLI_DB_STOCK_TICK')
DB_STOCK_MIN        = _resolve_db('stock_min.db', 'STOM_CLI_DB_STOCK_MIN')
DB_STOCK_BACK_TICK  = _resolve_db('stock_tick_back.db', 'STOM_CLI_DB_STOCK_BACK_TICK')
DB_STOCK_BACK_MIN   = _resolve_db('stock_min_back.db', 'STOM_CLI_DB_STOCK_BACK_MIN')
DB_COIN_TICK        = _resolve_db('coin_tick.db', 'STOM_CLI_DB_COIN_TICK')
DB_COIN_MIN         = _resolve_db('coin_min.db', 'STOM_CLI_DB_COIN_MIN')
DB_COIN_BACK_TICK   = _resolve_db('coin_tick_back.db', 'STOM_CLI_DB_COIN_BACK_TICK')
DB_COIN_BACK_MIN    = _resolve_db('coin_min_back.db', 'STOM_CLI_DB_COIN_BACK_MIN')
DB_FUTURE_TICK      = _resolve_db('future_tick.db', 'STOM_CLI_DB_FUTURE_TICK')
DB_FUTURE_MIN       = _resolve_db('future_min.db', 'STOM_CLI_DB_FUTURE_MIN')
DB_FUTURE_BACK_TICK = _resolve_db('future_tick_back.db', 'STOM_CLI_DB_FUTURE_BACK_TICK')
DB_FUTURE_BACK_MIN  = _resolve_db('future_min_back.db', 'STOM_CLI_DB_FUTURE_BACK_MIN')
DB_CODE_INFO        = _resolve_db('code_info.db', 'STOM_CLI_DB_CODE_INFO')
```

- [ ] **Step 4: Run related tests**

Run:

```powershell
python -m pytest tests/unit/test_setting_base_cli_overrides.py tests/unit/test_runner_helpers.py tests/unit/test_output.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 5: Commit fix**

Run:

```powershell
git add utility/setting.py tests/unit/test_setting_base_cli_overrides.py
git commit -m "legacy setting도 CLI DB override를 따르게 한다" -m "feature worktree에서 CLI baseline 실행 시 utility.setting이 ./_database/setting.db를 직접 열어 빈 DB를 보는 문제를 막기 위해 legacy setting DB 상수도 STOM_CLI_DATABASE_DIR와 개별 STOM_CLI_DB_* override를 따르게 했다.

Constraint: GUI 환경에서는 환경변수가 없으면 기존 ./_database 경로를 유지해야 함
Confidence: high
Scope-risk: moderate
Tested: tests/unit/test_setting_base_cli_overrides.py, tests/unit/test_runner_helpers.py, tests/unit/test_output.py
Not-tested: full-year CLI baseline after this fix"
```

---

### Task 2: Full-Year CLI Baseline Execution

**Files:**
- Runtime only: `backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.json`
- Runtime only: generated `backtest/csv/*.csv`
- No tracked file changes.

- [ ] **Step 1: Record latest existing ResearchTest CSV before execution**

Run:

```powershell
Get-ChildItem backtest\csv -Filter 'stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419*.csv' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 5 FullName,Length,LastWriteTime
```

Expected:

```text
Existing GUI or prior CLI CSV files are listed if present.
The known GUI baseline may be present:
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

- [ ] **Step 2: Run the full-year CLI baseline**

Run:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --betting 20 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900 `
  --format json `
  -o backtest\temp\wide_v1_cli_baseline_gui_compare_20260422.json
```

Expected success shape:

```text
Command exits 0.
backtest\temp\wide_v1_cli_baseline_gui_compare_20260422.json exists.
JSON status is success.
JSON csv_path points to a generated CSV.
```

Expected failure shape:

```text
Command exits non-zero.
JSON status is error if run_backtest reached result formatting.
JSON checkpoint_status and last_checkpoint explain the failure if available.
```

- [ ] **Step 3: Confirm JSON exists and is non-empty**

Run:

```powershell
Get-Item backtest\temp\wide_v1_cli_baseline_gui_compare_20260422.json |
  Select-Object FullName,Length,LastWriteTime
```

Expected:

```text
Length is greater than 0.
```

- [ ] **Step 4: Record latest ResearchTest CSV after execution**

Run:

```powershell
Get-ChildItem backtest\csv -Filter 'stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419*.csv' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 5 FullName,Length,LastWriteTime
```

Expected:

```text
If the CLI run succeeded, the newest CSV timestamp is later than the command start time.
```

---

### Task 3: Comparison Extraction And Gate Decision

**Files:**
- Runtime only: reads `backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.json`
- No tracked file changes.

- [ ] **Step 1: Extract CLI result and checkpoint summary**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path('backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.json')
payload = json.loads(path.read_text(encoding='utf-8-sig'))
metrics = payload.get('metrics') or {}
checkpoints = payload.get('checkpoints') or []

print('status', payload.get('status'))
print('message', payload.get('message'))
print('csv_path', payload.get('csv_path'))
print('checkpoint_status', payload.get('checkpoint_status'))
print('last_checkpoint', payload.get('last_checkpoint'))
print('elapsed_seconds', payload.get('elapsed_seconds'))
print('checkpoint_names', ','.join(item.get('name', '') for item in checkpoints))
print('metrics', metrics)
for item in checkpoints:
    if item.get('name') in ('back_count_ready', 'engine_data_load_completed', 'csv_detected'):
        print('checkpoint_detail', item.get('name'), item.get('detail'))
'@ | python -
```

Expected:

```text
status, csv_path, checkpoint_status, last_checkpoint, elapsed_seconds, checkpoint_names, and metrics are printed.
checkpoint_detail lines include back_count_ready when present.
```

- [ ] **Step 2: Compute metric differences**

Run:

```powershell
@'
import json
from pathlib import Path

GUI = {
    'back_count': 1638,
    'trade_count': 40937,
    'win_rate': 30.02,
    'avg_profit_pct': -0.68,
    'total_profit_pct': -695.09,
    'total_profit_krw': -5564960005,
    'mdd_pct': 693.76,
    'tpi': 0.60,
    'max_hold_count': 40,
    'avg_hold_time': 228.19,
}

path = Path('backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.json')
payload = json.loads(path.read_text(encoding='utf-8-sig'))
metrics = payload.get('metrics') or {}
checkpoints = payload.get('checkpoints') or []

def pick_metric(*names):
    for name in names:
        if name in metrics:
            return metrics[name]
    return None

def checkpoint_back_count():
    for item in checkpoints:
        if item.get('name') == 'back_count_ready':
            detail = item.get('detail') or {}
            if 'back_count' in detail:
                return detail['back_count']
    return None

cli = {
    'back_count': pick_metric('back_count') if pick_metric('back_count') is not None else checkpoint_back_count(),
    'trade_count': pick_metric('trade_count', 'total_trade_count'),
    'win_rate': pick_metric('win_rate'),
    'avg_profit_pct': pick_metric('avg_profit_pct', 'avg_return'),
    'total_profit_pct': pick_metric('total_profit_pct', 'total_return'),
    'total_profit_krw': pick_metric('total_profit_krw'),
    'mdd_pct': pick_metric('mdd_pct', 'max_drawdown'),
    'tpi': pick_metric('tpi'),
    'max_hold_count': pick_metric('max_hold_count'),
    'avg_hold_time': pick_metric('avg_hold_time'),
}

for key, gui_value in GUI.items():
    cli_value = cli.get(key)
    if cli_value is None:
        print(f'{key}: cli=missing gui={gui_value} diff=missing diff_ratio=missing')
        continue
    diff = float(cli_value) - float(gui_value)
    ratio = abs(diff) / abs(float(gui_value)) if float(gui_value) != 0 else 0.0
    print(f'{key}: cli={cli_value} gui={gui_value} diff={diff} diff_ratio={ratio}')
'@ | python -
```

Expected:

```text
Each comparison key prints cli, gui, diff, and diff_ratio.
Missing CLI fields are printed as missing.
```

- [ ] **Step 3: Compute final gate decision**

Run:

```powershell
@'
import json
from pathlib import Path

GUI_BACK_COUNT = 1638
GUI_TRADE_COUNT = 40937
TRADE_HOLD_RATIO = 0.001

path = Path('backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.json')
payload = json.loads(path.read_text(encoding='utf-8-sig'))
metrics = payload.get('metrics') or {}
checkpoints = payload.get('checkpoints') or []
checkpoint_names = {item.get('name') for item in checkpoints}

def pick_metric(*names):
    for name in names:
        if name in metrics:
            return metrics[name]
    return None

def checkpoint_back_count():
    for item in checkpoints:
        if item.get('name') == 'back_count_ready':
            detail = item.get('detail') or {}
            if 'back_count' in detail:
                return detail['back_count']
    return None

csv_path = payload.get('csv_path')
csv_exists = bool(csv_path) and Path(csv_path).exists()
status = payload.get('status')
checkpoint_status = payload.get('checkpoint_status')
last_checkpoint = payload.get('last_checkpoint')
trade_count = pick_metric('trade_count', 'total_trade_count')
back_count = pick_metric('back_count')
if back_count is None:
    back_count = checkpoint_back_count()

required_checkpoints = {'backtest_process_started', 'backtest_process_finished', 'csv_detected'}
has_required_checkpoints = required_checkpoints.issubset(checkpoint_names)

trade_diff_ratio = None
if trade_count is not None:
    trade_diff_ratio = abs(int(trade_count) - GUI_TRADE_COUNT) / GUI_TRADE_COUNT

if (
    status == 'success'
    and checkpoint_status == 'success'
    and last_checkpoint == 'csv_detected'
    and csv_exists
    and has_required_checkpoints
    and trade_count is not None
    and int(trade_count) == GUI_TRADE_COUNT
    and back_count is not None
    and int(back_count) == GUI_BACK_COUNT
):
    decision = 'PASS'
    reason = 'CLI full-year baseline matched GUI trade_count and back_count exactly.'
elif (
    status == 'success'
    and checkpoint_status == 'success'
    and csv_exists
    and trade_count is not None
    and trade_diff_ratio is not None
    and trade_diff_ratio <= TRADE_HOLD_RATIO
):
    decision = 'HOLD'
    reason = 'CLI baseline completed but one or more hard gate values differ or cannot be confirmed.'
else:
    decision = 'FAIL'
    reason = 'CLI baseline did not satisfy PASS or HOLD gate conditions.'

print('status', status)
print('checkpoint_status', checkpoint_status)
print('last_checkpoint', last_checkpoint)
print('csv_exists', csv_exists)
print('has_required_checkpoints', has_required_checkpoints)
print('back_count', back_count)
print('trade_count', trade_count)
print('trade_diff_ratio', trade_diff_ratio)
print('decision', decision)
print('reason', reason)
'@ | python -
```

Expected:

```text
decision PASS
```

If the decision is `HOLD` or `FAIL`, use that exact value in Task 4 and Task 5.

---

### Task 4: Pilot Log Documentation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_cli_baseline_gui_compare.md`

- [ ] **Step 1: Generate pilot log from runtime JSON**

Run:

```powershell
@'
import json
from pathlib import Path

GUI = {
    'back_count': 1638,
    'trade_count': 40937,
    'win_rate': 30.02,
    'avg_profit_pct': -0.68,
    'total_profit_pct': -695.09,
    'total_profit_krw': -5564960005,
    'mdd_pct': 693.76,
    'tpi': 0.60,
    'max_hold_count': 40,
    'avg_hold_time': 228.19,
}
GUI_CSV = r'C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv'

preflight_path = Path('backtest/temp/wide_v1_cli_preflight_gui_compare_20260422.json')
baseline_path = Path('backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.json')
out_path = Path('docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_cli_baseline_gui_compare.md')
out_path.parent.mkdir(parents=True, exist_ok=True)

preflight = json.loads(preflight_path.read_text(encoding='utf-8-sig'))
baseline = json.loads(baseline_path.read_text(encoding='utf-8-sig'))
metrics = baseline.get('metrics') or {}
checkpoints = baseline.get('checkpoints') or []
checkpoint_names = [item.get('name') for item in checkpoints]

def pick_metric(*names):
    for name in names:
        if name in metrics:
            return metrics[name]
    return None

def checkpoint_back_count():
    for item in checkpoints:
        if item.get('name') == 'back_count_ready':
            detail = item.get('detail') or {}
            if 'back_count' in detail:
                return detail['back_count']
    return None

cli = {
    'back_count': pick_metric('back_count') if pick_metric('back_count') is not None else checkpoint_back_count(),
    'trade_count': pick_metric('trade_count', 'total_trade_count'),
    'win_rate': pick_metric('win_rate'),
    'avg_profit_pct': pick_metric('avg_profit_pct', 'avg_return'),
    'total_profit_pct': pick_metric('total_profit_pct', 'total_return'),
    'total_profit_krw': pick_metric('total_profit_krw'),
    'mdd_pct': pick_metric('mdd_pct', 'max_drawdown'),
    'tpi': pick_metric('tpi'),
    'max_hold_count': pick_metric('max_hold_count'),
    'avg_hold_time': pick_metric('avg_hold_time'),
}

csv_path = baseline.get('csv_path')
csv_exists = bool(csv_path) and Path(csv_path).exists()
required_checkpoints = {'backtest_process_started', 'backtest_process_finished', 'csv_detected'}
has_required_checkpoints = required_checkpoints.issubset(set(checkpoint_names))

trade_count = cli['trade_count']
back_count = cli['back_count']
trade_diff_ratio = None
if trade_count is not None:
    trade_diff_ratio = abs(int(trade_count) - GUI['trade_count']) / GUI['trade_count']

if (
    preflight.get('status') == 'ok'
    and baseline.get('status') == 'success'
    and baseline.get('checkpoint_status') == 'success'
    and baseline.get('last_checkpoint') == 'csv_detected'
    and csv_exists
    and has_required_checkpoints
    and trade_count is not None
    and int(trade_count) == GUI['trade_count']
    and back_count is not None
    and int(back_count) == GUI['back_count']
):
    decision = 'PASS'
    reason = 'CLI full-year baseline matched GUI trade_count and back_count exactly.'
    next_command = '$brainstorming Wide v1 Retention-Aware candidate_count=5 실행 재개 설계'
elif (
    baseline.get('status') == 'success'
    and baseline.get('checkpoint_status') == 'success'
    and csv_exists
    and trade_count is not None
    and trade_diff_ratio is not None
    and trade_diff_ratio <= 0.001
):
    decision = 'HOLD'
    reason = 'CLI baseline completed, but one or more hard gate values differ or cannot be confirmed.'
    next_command = '$brainstorming Wide v1 CLI/GUI 결과 차이 원인 분석 설계'
else:
    decision = 'FAIL'
    reason = 'CLI baseline did not satisfy PASS or HOLD gate conditions.'
    next_command = '$brainstorming CLI baseline backtest failure checkpoint 분석 설계'

comparison_lines = []
for key, gui_value in GUI.items():
    cli_value = cli.get(key)
    if cli_value is None:
        comparison_lines.append(f'{key}: cli=missing gui={gui_value} diff=missing diff_ratio=missing')
    else:
        diff = float(cli_value) - float(gui_value)
        ratio = abs(diff) / abs(float(gui_value)) if float(gui_value) != 0 else 0.0
        comparison_lines.append(f'{key}: cli={cli_value} gui={gui_value} diff={diff} diff_ratio={ratio}')

lines = [
    '# Wide v1 CLI Baseline GUI Compare Pilot',
    '',
    '## 목적',
    '',
    'Wide v1 ResearchTest tick 조건식을 CLI full-year로 실행하고 GUI 기준 결과와 비교해 후보 자동 백테스트 진입 가능 여부를 판단한다.',
    '',
    '## 전체 플로우',
    '',
    '```text',
    '[PR #17 merge 완료]',
    '        |',
    '        v',
    '[runtime-preflight]',
    '        |',
    '        v',
    '[full-year CLI baseline]',
    '        |',
    '        v',
    '[GUI 기준 결과와 비교]',
    '        |',
    '        v',
    f'[{decision}]',
    '```',
    '',
    '## 실행 조건',
    '',
    '```text',
    'buy=ResearchTest_Tick_B_090000_092800_Wide_20260419',
    'sell=ResearchTest_Tick_S_090000_092800_Wide_20260419',
    'start=20250101',
    'end=20251231',
    'timeframe=tick',
    'avg_time=30',
    'betting=20',
    'start_time=90000',
    'end_time=92800',
    'engines=32',
    'timeout=900',
    r'runtime_db=C:\System_Trading\STOM\STOM_V.wt-dev\_database',
    '```',
    '',
    '## preflight 결과',
    '',
    '```text',
    f"status={preflight.get('status')}",
    f"failed_checks={preflight.get('failed_checks')}",
    f"validation_errors={preflight.get('validation_errors')}",
    f"timeframe_match={preflight.get('timeframe_match', {}).get('status')}",
    f"buy_status={preflight.get('strategies', {}).get('buy', {}).get('status')}",
    f"sell_status={preflight.get('strategies', {}).get('sell', {}).get('status')}",
    f"stock_back_db_usable={preflight.get('runtime_profile', {}).get('stock_back_db_usable')}",
    f"stock_back_db_integrity={preflight.get('runtime_profile', {}).get('stock_back_db_integrity')}",
    '```',
    '',
    '## CLI baseline 결과',
    '',
    '```text',
    f"status={baseline.get('status')}",
    f"message={baseline.get('message')}",
    f"checkpoint_status={baseline.get('checkpoint_status')}",
    f"last_checkpoint={baseline.get('last_checkpoint')}",
    f"elapsed_seconds={baseline.get('elapsed_seconds')}",
    f"csv_path={csv_path}",
    f"csv_exists={csv_exists}",
    f"checkpoint_names={','.join(name for name in checkpoint_names if name)}",
    '```',
    '',
    '## GUI 기준',
    '',
    '```text',
    f"gui_csv={GUI_CSV}",
    *[f'{key}={value}' for key, value in GUI.items()],
    '```',
    '',
    '## 비교 결과',
    '',
    '```text',
    *comparison_lines,
    '```',
    '',
    '## 판정',
    '',
    '```text',
    f'decision={decision}',
    f'reason={reason}',
    f'next_command={next_command}',
    '```',
    '',
    '## 남은 리스크',
    '',
    '- PASS가 아니면 후보 N개 자동 백테스트로 넘어가지 않는다.',
    '- scalar 비교만 수행했으며 row-level CSV 비교는 필요 시 별도 설계로 분리한다.',
    '- runtime JSON/CSV/graph 산출물은 Git에 포함하지 않는다.',
    '',
]

out_path.write_text('\n'.join(lines), encoding='utf-8')
print(out_path)
print('decision', decision)
print('reason', reason)
'@ | python -
```

Expected:

```text
docs\research\condition_research\pilot_logs\2026-04-22_wide_v1_cli_baseline_gui_compare.md
decision PASS
```

If `decision` is `HOLD` or `FAIL`, keep that value and route accordingly.

- [ ] **Step 2: Verify pilot log has no unresolved markers**

Run:

```powershell
$patterns = @('T' + 'BD', 'TO' + 'DO', 'FIX' + 'ME', 'actual' + '_', 'observ' + 'ed') -join '|'
rg -n $patterns docs\research\condition_research\pilot_logs\2026-04-22_wide_v1_cli_baseline_gui_compare.md
```

Expected:

```text
No output.
```

---

### Task 5: Update Log Documentation

**Files:**
- Create: `docs/update_log/2026-04-22_wide_v1_cli_baseline_gui_compare.md`

- [ ] **Step 1: Generate update log from pilot log**

Run:

```powershell
@'
import json
from pathlib import Path
import re

pilot_path = Path('docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_cli_baseline_gui_compare.md')
preflight_path = Path('backtest/temp/wide_v1_cli_preflight_gui_compare_20260422.json')
baseline_path = Path('backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.json')
out_path = Path('docs/update_log/2026-04-22_wide_v1_cli_baseline_gui_compare.md')
text = pilot_path.read_text(encoding='utf-8')
preflight = json.loads(preflight_path.read_text(encoding='utf-8-sig'))
baseline = json.loads(baseline_path.read_text(encoding='utf-8-sig'))
metrics = baseline.get('metrics') or {}

def extract(name):
    match = re.search(rf'^{re.escape(name)}=(.*)$', text, flags=re.MULTILINE)
    return match.group(1).strip() if match else 'not_present'

def pick_metric(*names):
    for name in names:
        if name in metrics:
            return metrics[name]
    return 'not_present'

decision = extract('decision')
next_command = extract('next_command')
reason = extract('reason')
trade_count = pick_metric('trade_count', 'total_trade_count')

lines = [
    '# 2026-04-22 Wide v1 CLI Baseline GUI Compare',
    '',
    '## 목적',
    '',
    'PR #17 이후 Wide v1 ResearchTest tick 조건식을 CLI full-year로 실행하고 GUI 기준 결과와 비교해 후보 자동 백테스트 진입 가능 여부를 판단했다.',
    '',
    '## 전체 플로우',
    '',
    '```text',
    '[완료] PR #17 child DB / timeout protocol / tick 설정 키 보강',
    '        |',
    '        v',
    '[이번 작업] full-year CLI baseline',
    '        |',
    '        v',
    '[이번 작업] GUI 결과와 비교',
    '        |',
    '        v',
    f'[판정] {decision}',
    '```',
    '',
    '## 결과 요약',
    '',
    '```text',
    f"preflight_status={preflight.get('status')}",
    f"cli_status={baseline.get('status')}",
    f"checkpoint_status={baseline.get('checkpoint_status')}",
    f"last_checkpoint={baseline.get('last_checkpoint')}",
    f"elapsed_seconds={baseline.get('elapsed_seconds')}",
    f"csv_path={baseline.get('csv_path')}",
    f"trade_count={trade_count}",
    f"decision={decision}",
    '```',
    '',
    '## 판정',
    '',
    '```text',
    f"decision={decision}",
    f"reason={reason}",
    f"next_command={next_command}",
    '```',
    '',
    '## 남은 리스크',
    '',
    '- PASS가 아니면 후보 N개 자동 백테스트로 넘어가지 않는다.',
    '- PASS라도 row-level CSV parity는 별도 추가 검증으로 남을 수 있다.',
    '- 최종 실전 채택 전에는 promote/WFO 검증이 필요하다.',
    '',
    '## 다음 단계',
    '',
    '```text',
    next_command,
    '```',
    '',
]

out_path.write_text('\n'.join(lines), encoding='utf-8')
print(out_path)
print('decision', decision)
'@ | python -
```

Expected:

```text
docs\update_log\2026-04-22_wide_v1_cli_baseline_gui_compare.md
decision PASS
```

- [ ] **Step 2: Verify update log has no unresolved markers**

Run:

```powershell
$patterns = @('T' + 'BD', 'TO' + 'DO', 'FIX' + 'ME', 'actual' + '_', 'observ' + 'ed') -join '|'
rg -n $patterns docs\update_log\2026-04-22_wide_v1_cli_baseline_gui_compare.md
```

Expected:

```text
No output.
```

---

### Task 6: Verification And Commit

**Files:**
- Commit:
  - `docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_cli_baseline_gui_compare.md`
  - `docs/update_log/2026-04-22_wide_v1_cli_baseline_gui_compare.md`

- Do not commit:
  - `backtest/temp/wide_v1_cli_preflight_gui_compare_20260422.json`
  - `backtest/temp/wide_v1_cli_baseline_gui_compare_20260422.json`
  - `backtest/temp/*.log`
  - generated `backtest/csv/*.csv`
  - `backtest/graph/`
  - `_database/*.db`

- [ ] **Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_runner_helpers.py tests/unit/test_output.py -q
python scripts/verify_nonrelease_sync.py
git diff --check
```

Expected:

```text
Focused tests pass.
verify_nonrelease_sync.py passes.
git diff --check has no output.
```

- [ ] **Step 2: Confirm runtime artifacts are not staged**

Run:

```powershell
git status --short --untracked-files=all
```

Expected tracked/untracked shape:

```text
?? docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_cli_baseline_gui_compare.md
?? docs/update_log/2026-04-22_wide_v1_cli_baseline_gui_compare.md
```

Runtime files under `backtest/temp`, `backtest/csv`, and `backtest/graph` may exist, but they must not be staged. If they appear as tracked modifications, stop before committing.

- [ ] **Step 3: Commit documentation**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_cli_baseline_gui_compare.md docs/update_log/2026-04-22_wide_v1_cli_baseline_gui_compare.md
git commit -m "Wide v1 CLI baseline GUI 비교 결과를 기록한다" -m "PR #17 이후 Wide v1 ResearchTest tick 조건식을 CLI full-year로 실행하고 GUI 기준 결과와 비교한 PASS/HOLD/FAIL gate 판정을 문서화했다.

Constraint: runtime DB, CSV, graph, temp JSON 산출물은 커밋하지 않음
Confidence: medium
Scope-risk: narrow
Tested: runtime-preflight, full-year CLI baseline command, focused unit tests, verify_nonrelease_sync.py
Not-tested: candidate_count=5, WFO, promote"
```

---

## Final Decision Routing

Use the documented decision:

```text
PASS:
  $brainstorming Wide v1 Retention-Aware candidate_count=5 실행 재개 설계

HOLD:
  $brainstorming Wide v1 CLI/GUI 결과 차이 원인 분석 설계

FAIL:
  $brainstorming CLI baseline backtest failure checkpoint 분석 설계
```

Do not run `candidate_count=5` until this gate is PASS.

## Self-Review Checklist

Spec coverage:

```text
PR #17 기반 확인: Task 1
runtime-preflight: Task 1
full-year CLI baseline: Task 2
metric/checkpoint/CSV extraction: Task 3
GUI comparison and PASS/HOLD/FAIL: Task 3 and Task 4
pilot/update logs: Task 4 and Task 5
verification and artifact exclusion: Task 6
```

No code changes are planned. If runtime execution reveals missing runner fields, stop and create a new design for result-field hardening rather than silently expanding this plan.
