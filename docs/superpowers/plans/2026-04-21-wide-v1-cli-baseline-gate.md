# Wide v1 CLI Baseline Backtest Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one CLI baseline backtest for the Wide v1 ResearchTest tick strategy, compare it against the known GUI/STOM result, and document a PASS/HOLD/FAIL gate decision before any `candidate_count=5` run.

**Architecture:** This is an execution-and-documentation plan, not a feature-building plan. Use the merged `runtime-preflight` and checkpoint-enabled CLI runner from `STOM_Version_2U_C`, capture runtime output into ignored temp files, summarize only the relevant evidence in Markdown documents, and keep DB/CSV/graph/runtime artifacts out of Git.

**Tech Stack:** Python 3.11, STOM CLI (`stom_backtest.py`), PowerShell, pytest for verification, Markdown logs under `docs/research/condition_research/` and `docs/update_log/`.

---

## Scope

In scope:

- Confirm `STOM_Version_2U_C` is synchronized and only protected runtime output is untracked.
- Run `runtime-preflight` for the Wide v1 ResearchTest strategy.
- Run exactly one CLI baseline backtest with the same condition set as the GUI baseline.
- Capture JSON output under `backtest/temp/` as an ignored runtime artifact.
- Summarize the result, checkpoint state, CSV path, and GUI/CLI comparison in Markdown.
- Write a final PASS/HOLD/FAIL gate decision.
- Run lightweight verification and commit only documentation.

Out of scope:

- Do not run `candidate_count=5`.
- Do not run WFO.
- Do not promote or adopt any candidate strategy.
- Do not change CLI code unless this plan explicitly fails because required fields are unavailable.
- Do not commit runtime DB, CSV, graph, temp JSON, or stdout logs.

## File Structure

Create:

- `docs/research/condition_research/pilot_logs/2026-04-21_wide_v1_cli_baseline_backtest.md`
  - Full pilot evidence: commands, preflight result, CLI baseline result, checkpoint summary, GUI baseline, comparison, PASS/HOLD/FAIL.

- `docs/update_log/2026-04-21_wide_v1_cli_baseline_gate.md`
  - Short project update: current stage, result decision, remaining risks, next command.

Runtime-only generated files:

- `backtest/temp/wide_v1_cli_baseline_20260421.json`
  - CLI output capture. Do not stage.

- New `backtest/csv/stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_*.csv`
  - Backtest output CSV if generated. Do not stage.

- `backtest/graph/`
  - Protected generated output. Do not stage or modify intentionally.

## Gate Constants

GUI baseline:

```text
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
start=20250101
end=20251231
timeframe=tick
avg_time=30
start_time=90000
end_time=92800
engines=32
back_count=1638
trade_count=40937
runtime=0:01:00.675279
```

Decision thresholds:

```text
PASS:
  preflight ok
  CLI result status success
  CSV exists
  checkpoint_status success
  back_count == 1638
  trade_count == 40937

HOLD:
  CLI result status success
  CSV exists
  back_count == 1638
  trade_count diff ratio <= 0.001
  difference cause needs analysis

FAIL:
  preflight error
  CLI result error or timeout
  CSV missing
  back_count != 1638
  trade_count diff ratio > 0.001
```

---

### Task 1: Preflight And Workspace Baseline

**Files:**
- Runtime only: `backtest/temp/wide_v1_cli_preflight_20260421.json`
- No tracked file changes.

- [ ] **Step 1: Confirm branch and working tree**

Run:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-dev
git status --short --branch
git log --oneline -5
```

Expected:

```text
## STOM_Version_2U_C...origin/STOM_Version_2U_C [ahead 2]
?? backtest/graph/
```

The `[ahead 2]` state is the committed spec and this committed plan. `backtest/graph/` is protected generated data. Do not stage it.

- [ ] **Step 2: Create temp directory if needed**

Run:

```powershell
New-Item -ItemType Directory -Force backtest\temp | Out-Null
```

Expected:

```text
No output
```

- [ ] **Step 3: Run runtime-preflight and save JSON**

Run:

```powershell
python stom_backtest.py runtime-preflight `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900 `
  | Tee-Object -FilePath backtest\temp\wide_v1_cli_preflight_20260421.json
```

Expected JSON fields:

```text
status=ok
failed_checks=[]
validation_errors=[]
timeframe_match.status=ok
strategies.buy.status=ok
strategies.sell.status=ok
runtime_profile.stock_back_db_usable=true
runtime_profile.stock_back_db_integrity=table_probe_only
```

- [ ] **Step 4: Verify preflight status programmatically**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path('backtest/temp/wide_v1_cli_preflight_20260421.json')
payload = json.loads(path.read_text(encoding='utf-8'))
print('status', payload.get('status'))
print('failed_checks', payload.get('failed_checks'))
print('validation_errors', payload.get('validation_errors'))
print('timeframe_match', payload.get('timeframe_match', {}).get('status'))
print('buy_status', payload.get('strategies', {}).get('buy', {}).get('status'))
print('sell_status', payload.get('strategies', {}).get('sell', {}).get('status'))
print('stock_back_db_usable', payload.get('runtime_profile', {}).get('stock_back_db_usable'))
print('stock_back_db_integrity', payload.get('runtime_profile', {}).get('stock_back_db_integrity'))

if payload.get('status') != 'ok':
    raise SystemExit(1)
if payload.get('failed_checks') != []:
    raise SystemExit(1)
if payload.get('validation_errors') != []:
    raise SystemExit(1)
if payload.get('timeframe_match', {}).get('status') != 'ok':
    raise SystemExit(1)
if payload.get('strategies', {}).get('buy', {}).get('status') != 'ok':
    raise SystemExit(1)
if payload.get('strategies', {}).get('sell', {}).get('status') != 'ok':
    raise SystemExit(1)
if payload.get('runtime_profile', {}).get('stock_back_db_usable') is not True:
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

- [ ] **Step 5: Stop if preflight fails**

If Step 4 exits non-zero, do not run the baseline backtest. Create the pilot log with FAIL status using the template in Task 4 and explain the failed preflight fields.

---

### Task 2: CLI Baseline Backtest Execution

**Files:**
- Runtime only: `backtest/temp/wide_v1_cli_baseline_20260421.json`
- Runtime only: generated `backtest/csv/*.csv`
- No tracked file changes.

- [ ] **Step 1: Capture current latest ResearchTest CSV before running**

Run:

```powershell
Get-ChildItem backtest\csv -Filter 'stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419*.csv' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 3 FullName,Length,LastWriteTime
```

Expected:

```text
The existing GUI baseline CSV may appear:
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

- [ ] **Step 2: Run one CLI baseline backtest and save JSON**

Run:

```powershell
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900 `
  --format json `
  -o backtest\temp\wide_v1_cli_baseline_20260421.json
```

Expected success shape:

```text
Command exits 0.
backtest/temp/wide_v1_cli_baseline_20260421.json exists.
JSON status is success.
JSON contains checkpoint fields.
```

Expected failure shape:

```text
Command exits non-zero, or JSON status is error.
JSON contains checkpoint fields when runner reached run_backtest().
```

- [ ] **Step 3: Confirm JSON output file exists**

Run:

```powershell
Get-Item backtest\temp\wide_v1_cli_baseline_20260421.json |
  Select-Object FullName,Length,LastWriteTime
```

Expected:

```text
FullName points to backtest\temp\wide_v1_cli_baseline_20260421.json
Length is greater than 0
```

- [ ] **Step 4: Capture latest ResearchTest CSV after running**

Run:

```powershell
Get-ChildItem backtest\csv -Filter 'stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419*.csv' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 5 FullName,Length,LastWriteTime
```

Expected:

```text
If CLI generated a CSV, the newest file should have a timestamp after the command start.
```

---

### Task 3: Result Extraction And Gate Calculation

**Files:**
- Runtime only: reads `backtest/temp/wide_v1_cli_baseline_20260421.json`
- No tracked file changes.

- [ ] **Step 1: Extract CLI result summary**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path('backtest/temp/wide_v1_cli_baseline_20260421.json')
payload = json.loads(path.read_text(encoding='utf-8'))
metrics = payload.get('metrics') or {}
checkpoints = payload.get('checkpoints') or []

print('status', payload.get('status'))
print('message', payload.get('message'))
print('csv_path', payload.get('csv_path'))
print('checkpoint_status', payload.get('checkpoint_status'))
print('last_checkpoint', payload.get('last_checkpoint'))
print('elapsed_seconds', payload.get('elapsed_seconds'))
print('checkpoint_names', ','.join(item.get('name', '') for item in checkpoints))
print('metrics_keys', ','.join(sorted(metrics.keys())))
for key in [
    'back_count',
    'trade_count',
    'total_trade_count',
    'win_rate',
    'avg_return',
    'total_return',
    'tpi',
    'max_drawdown',
    'avg_hold_time',
]:
    if key in metrics:
        print(f'{key}', metrics[key])
'@ | python -
```

Expected:

```text
The output must show status, message, csv_path, checkpoint_status, last_checkpoint, elapsed_seconds, checkpoint_names.
Metric key names depend on existing runner extraction. If back_count or trade_count is absent, record that in the pilot log.
```

- [ ] **Step 2: Compute initial gate values**

Run:

```powershell
@'
import json
from pathlib import Path

GUI_BACK_COUNT = 1638
GUI_TRADE_COUNT = 40937

path = Path('backtest/temp/wide_v1_cli_baseline_20260421.json')
payload = json.loads(path.read_text(encoding='utf-8'))
metrics = payload.get('metrics') or {}

def pick(*names):
    for name in names:
        if name in metrics:
            return metrics[name]
    return None

back_count = pick('back_count')
trade_count = pick('trade_count', 'total_trade_count')
status = payload.get('status')
checkpoint_status = payload.get('checkpoint_status')
csv_path = payload.get('csv_path')

print('status', status)
print('checkpoint_status', checkpoint_status)
print('csv_path_present', bool(csv_path))
print('back_count', back_count)
print('trade_count', trade_count)

if back_count is not None:
    print('back_count_diff', int(back_count) - GUI_BACK_COUNT)
else:
    print('back_count_diff', 'missing')

if trade_count is not None:
    diff = int(trade_count) - GUI_TRADE_COUNT
    ratio = abs(diff) / GUI_TRADE_COUNT
    print('trade_count_diff', diff)
    print('trade_count_diff_pct', ratio)
else:
    print('trade_count_diff', 'missing')
    print('trade_count_diff_pct', 'missing')
'@ | python -
```

Expected:

```text
If metrics expose back_count and trade_count, diffs are printed.
If metrics do not expose them, missing is printed and the gate decision becomes HOLD or FAIL depending on CSV/checkpoint state.
```

- [ ] **Step 3: Check generated CSV row count if csv_path exists**

Run:

```powershell
@'
import csv
import json
from pathlib import Path

path = Path('backtest/temp/wide_v1_cli_baseline_20260421.json')
payload = json.loads(path.read_text(encoding='utf-8'))
csv_path = payload.get('csv_path')
print('csv_path', csv_path)
if not csv_path:
    raise SystemExit(0)

csv_file = Path(csv_path)
print('csv_exists', csv_file.exists())
print('csv_size', csv_file.stat().st_size if csv_file.exists() else 0)
if csv_file.exists():
    with csv_file.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        row_count = sum(1 for _ in reader)
    print('csv_physical_rows_including_header', row_count)
'@ | python -
```

Expected:

```text
csv_exists True if result produced a CSV.
csv_physical_rows_including_header is printed for reference.
```

- [ ] **Step 4: Decide PASS / HOLD / FAIL**

Use this rule:

```text
PASS:
  status == success
  csv_path exists
  checkpoint_status == success
  checkpoint_names include backtest_process_started, backtest_process_finished, csv_detected
  back_count == 1638
  trade_count == 40937

HOLD:
  status == success
  csv_path exists
  checkpoint_status == success
  back_count == 1638
  trade_count exists
  abs(trade_count - 40937) / 40937 <= 0.001

FAIL:
  status != success
  csv_path missing
  checkpoint_status == timeout
  required checkpoints missing
  back_count != 1638
  trade_count diff ratio > 0.001
```

Write the decision into the pilot log in Task 4.

---

### Task 4: Pilot Log Documentation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-21_wide_v1_cli_baseline_backtest.md`

- [ ] **Step 1: Generate the pilot log from captured JSON**

Run this script after Tasks 1-3 have produced `backtest/temp/wide_v1_cli_preflight_20260421.json` and `backtest/temp/wide_v1_cli_baseline_20260421.json`.

```powershell
@'
import json
from pathlib import Path

GUI_BACK_COUNT = 1638
GUI_TRADE_COUNT = 40937
GUI_RUNTIME = '0:01:00.675279'

preflight_path = Path('backtest/temp/wide_v1_cli_preflight_20260421.json')
baseline_path = Path('backtest/temp/wide_v1_cli_baseline_20260421.json')
out_path = Path('docs/research/condition_research/pilot_logs/2026-04-21_wide_v1_cli_baseline_backtest.md')
out_path.parent.mkdir(parents=True, exist_ok=True)

preflight = json.loads(preflight_path.read_text(encoding='utf-8'))
baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
metrics = baseline.get('metrics') or {}
checkpoints = baseline.get('checkpoints') or []
checkpoint_names = [item.get('name', '') for item in checkpoints]

def pick(*names):
    for name in names:
        if name in metrics:
            return metrics[name]
    return None

def value_text(value):
    if value is None:
        return 'not_present_in_runner_json'
    return str(value)

cli_back_count = pick('back_count')
cli_trade_count = pick('trade_count', 'total_trade_count')
back_count_diff = None if cli_back_count is None else int(cli_back_count) - GUI_BACK_COUNT
trade_count_diff = None if cli_trade_count is None else int(cli_trade_count) - GUI_TRADE_COUNT
trade_count_diff_pct = None if trade_count_diff is None else abs(trade_count_diff) / GUI_TRADE_COUNT

required_checkpoints = {'backtest_process_started', 'backtest_process_finished', 'csv_detected'}
has_required_checkpoints = required_checkpoints.issubset(set(checkpoint_names))
csv_path = baseline.get('csv_path')
csv_exists = bool(csv_path) and Path(csv_path).exists()
status = baseline.get('status')
checkpoint_status = baseline.get('checkpoint_status')

if (
    preflight.get('status') == 'ok'
    and status == 'success'
    and csv_exists
    and checkpoint_status == 'success'
    and has_required_checkpoints
    and cli_back_count is not None
    and int(cli_back_count) == GUI_BACK_COUNT
    and cli_trade_count is not None
    and int(cli_trade_count) == GUI_TRADE_COUNT
):
    decision = 'PASS'
    reason = 'CLI baseline result matched GUI back_count and trade_count exactly.'
    next_command = '$brainstorming Wide v1 Retention-Aware candidate_count=5 실행 재개 설계'
elif (
    preflight.get('status') == 'ok'
    and status == 'success'
    and csv_exists
    and checkpoint_status == 'success'
    and cli_back_count is not None
    and int(cli_back_count) == GUI_BACK_COUNT
    and cli_trade_count is not None
    and trade_count_diff_pct is not None
    and trade_count_diff_pct <= 0.001
):
    decision = 'HOLD'
    reason = 'CLI baseline completed, but trade_count differs within the HOLD threshold and needs cause analysis.'
    next_command = '$brainstorming Wide v1 CLI/GUI 결과 차이 원인 분석 설계'
else:
    decision = 'FAIL'
    reason = 'CLI baseline did not satisfy PASS or HOLD gate criteria.'
    next_command = '$brainstorming CLI baseline backtest failure checkpoint 분석 설계'

lines = [
    '# Wide v1 CLI Baseline Backtest Pilot',
    '',
    '## 목적',
    '',
    'GUI/STOM에서 성공한 ResearchTest wide 기준 전략을 CLI에서 1회 실행해, Wide v1 Retention-Aware 후보 5개 루프 진입 가능 여부를 판단한다.',
    '',
    '## 전체 흐름',
    '',
    '~~~text',
    '[runtime-preflight]',
    '        |',
    '        v',
    '[CLI baseline 1회 백테스트]',
    '        |',
    '        v',
    '[GUI 기준 결과와 비교]',
    '        |',
    '        v',
    '[PASS/HOLD/FAIL 판정]',
    '~~~',
    '',
    '## 실행 조건',
    '',
    '~~~text',
    'buy=ResearchTest_Tick_B_090000_092800_Wide_20260419',
    'sell=ResearchTest_Tick_S_090000_092800_Wide_20260419',
    'start=20250101',
    'end=20251231',
    'timeframe=tick',
    'avg_time=30',
    'start_time=90000',
    'end_time=92800',
    'engines=32',
    'timeout=900',
    '~~~',
    '',
    '## preflight 결과',
    '',
    '~~~text',
    f"status={preflight.get('status')}",
    f"failed_checks={preflight.get('failed_checks')}",
    f"validation_errors={preflight.get('validation_errors')}",
    f"timeframe_match.status={preflight.get('timeframe_match', {}).get('status')}",
    f"buy.status={preflight.get('strategies', {}).get('buy', {}).get('status')}",
    f"sell.status={preflight.get('strategies', {}).get('sell', {}).get('status')}",
    f"stock_back_db_usable={preflight.get('runtime_profile', {}).get('stock_back_db_usable')}",
    f"stock_back_db_integrity={preflight.get('runtime_profile', {}).get('stock_back_db_integrity')}",
    f"stock_back_db_table_count={preflight.get('runtime_profile', {}).get('stock_back_db_table_count')}",
    '~~~',
    '',
    '## CLI baseline 결과',
    '',
    '~~~text',
    f"status={baseline.get('status')}",
    f"message={baseline.get('message')}",
    f"csv_path={baseline.get('csv_path')}",
    f"csv_exists={csv_exists}",
    f"checkpoint_status={baseline.get('checkpoint_status')}",
    f"last_checkpoint={baseline.get('last_checkpoint')}",
    f"elapsed_seconds={baseline.get('elapsed_seconds')}",
    f"checkpoint_names={','.join(checkpoint_names)}",
    '~~~',
    '',
    '## GUI 기준 결과',
    '',
    '~~~text',
    f'back_count={GUI_BACK_COUNT}',
    f'trade_count={GUI_TRADE_COUNT}',
    f'runtime={GUI_RUNTIME}',
    'win_rate=30.02%',
    'avg_return=-0.68%',
    'total_return=-695.09%',
    'tpi=0.60',
    '~~~',
    '',
    '## 비교 결과',
    '',
    '~~~text',
    f'cli_back_count={value_text(cli_back_count)}',
    f'cli_trade_count={value_text(cli_trade_count)}',
    f'back_count_diff={value_text(back_count_diff)}',
    f'trade_count_diff={value_text(trade_count_diff)}',
    f'trade_count_diff_pct={value_text(trade_count_diff_pct)}',
    '~~~',
    '',
    '## 판정',
    '',
    '~~~text',
    f'decision={decision}',
    f'reason={reason}',
    '~~~',
    '',
    '## 다음 단계',
    '',
    '~~~text',
    next_command,
    '~~~',
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
docs\research\condition_research\pilot_logs\2026-04-21_wide_v1_cli_baseline_backtest.md
decision PASS
```

If the printed decision is `HOLD` or `FAIL` instead of `PASS`, that value must match the generated document and determines the next brainstorming command.

- [ ] **Step 2: Verify the pilot log has no unresolved markers**

Run:

```powershell
rg -n "<" docs\research\condition_research\pilot_logs\2026-04-21_wide_v1_cli_baseline_backtest.md
```

Expected:

```text
No output
```

---

### Task 5: Update Log Documentation

**Files:**
- Create: `docs/update_log/2026-04-21_wide_v1_cli_baseline_gate.md`

- [ ] **Step 1: Generate update log from pilot evidence**

Run:

```powershell
@'
from pathlib import Path
import re

pilot_path = Path('docs/research/condition_research/pilot_logs/2026-04-21_wide_v1_cli_baseline_backtest.md')
out_path = Path('docs/update_log/2026-04-21_wide_v1_cli_baseline_gate.md')
text = pilot_path.read_text(encoding='utf-8')

def extract(name):
    match = re.search(rf'^{re.escape(name)}=(.*)$', text, flags=re.MULTILINE)
    return match.group(1).strip() if match else 'not_present_in_pilot_log'

decision = extract('decision')
next_command = {
    'PASS': '$brainstorming Wide v1 Retention-Aware candidate_count=5 실행 재개 설계',
    'HOLD': '$brainstorming Wide v1 CLI/GUI 결과 차이 원인 분석 설계',
    'FAIL': '$brainstorming CLI baseline backtest failure checkpoint 분석 설계',
}.get(decision, '$brainstorming CLI baseline gate 결과 판정 재검토')

lines = [
    '# 2026-04-21 Wide v1 CLI Baseline Gate',
    '',
    '## 목적',
    '',
    'runtime-preflight가 통과한 ResearchTest wide 조건식을 CLI로 1회 baseline 백테스트하고, GUI 기준 결과와 비교해 후보 5개 루프 진입 가능 여부를 판단했다.',
    '',
    '## 전체 흐름',
    '',
    '~~~text',
    '[완료] runtime-preflight',
    '        |',
    '        v',
    '[이번 작업] CLI baseline 1회 백테스트',
    '        |',
    '        v',
    '[이번 작업] GUI 결과와 비교',
    '        |',
    '        v',
    f'[판정] {decision}',
    '~~~',
    '',
    '## 실행 결과 요약',
    '',
    '~~~text',
    f"preflight_status={extract('status')}",
    f"cli_status={extract('status')}",
    f"csv_path={extract('csv_path')}",
    f"checkpoint_status={extract('checkpoint_status')}",
    f"last_checkpoint={extract('last_checkpoint')}",
    f"cli_back_count={extract('cli_back_count')}",
    f"cli_trade_count={extract('cli_trade_count')}",
    f"decision={decision}",
    '~~~',
    '',
    '## 판정 근거',
    '',
    f"- preflight와 CLI baseline 실행 결과를 기준으로 `{decision}` 판정을 기록했다.",
    f"- `back_count_diff={extract('back_count_diff')}` 및 `trade_count_diff={extract('trade_count_diff')}`를 기준값과 비교했다.",
    f"- 다음 작업은 `{next_command}`이다.",
    '',
    '## 남은 리스크',
    '',
    '- CLI baseline 1회 결과는 확보했지만, 후보 5개 백테스트는 아직 실행하지 않았다.',
    '- GUI/CLI 비교에서 HOLD 또는 FAIL이면 후보 루프 전에 원인 분석이 필요하다.',
    '- runner JSON에 비교 필드가 부족하면 결과 수집 보강이 필요하다.',
    '',
    '## 다음 단계',
    '',
    '~~~text',
    next_command,
    '~~~',
    '',
]

out_path.write_text('\n'.join(lines), encoding='utf-8')
print(out_path)
print('decision', decision)
'@ | python -
```

Expected:

```text
docs\update_log\2026-04-21_wide_v1_cli_baseline_gate.md
decision PASS
```

If the printed decision is `HOLD` or `FAIL` instead of `PASS`, that value must match the pilot log decision.

- [ ] **Step 2: Verify the update log has no unresolved markers**

Run:

```powershell
rg -n "<" docs\update_log\2026-04-21_wide_v1_cli_baseline_gate.md
```

Expected:

```text
No output
```

---

### Task 6: Verification And Commit

**Files:**
- Commit:
  - `docs/research/condition_research/pilot_logs/2026-04-21_wide_v1_cli_baseline_backtest.md`
  - `docs/update_log/2026-04-21_wide_v1_cli_baseline_gate.md`
- Do not commit:
  - `backtest/temp/wide_v1_cli_preflight_20260421.json`
  - `backtest/temp/wide_v1_cli_baseline_20260421.json`
  - generated `backtest/csv/*.csv`
  - `backtest/graph/`
  - `_database/*.db`

- [ ] **Step 1: Run documentation diff check**

Run:

```powershell
git diff --check -- `
  docs\research\condition_research\pilot_logs\2026-04-21_wide_v1_cli_baseline_backtest.md `
  docs\update_log\2026-04-21_wide_v1_cli_baseline_gate.md
```

Expected:

```text
No whitespace errors
```

- [ ] **Step 2: Confirm no runtime artifacts are staged**

Run:

```powershell
git status --short --untracked-files=all
```

Expected:

```text
?? backtest/graph/
?? docs/research/condition_research/pilot_logs/2026-04-21_wide_v1_cli_baseline_backtest.md
?? docs/update_log/2026-04-21_wide_v1_cli_baseline_gate.md
```

If `backtest/temp/*.json`, `_database/*.db`, or `backtest/csv/*.csv` appear as tracked/staged changes, stop and correct before committing.

- [ ] **Step 3: Run lightweight verification**

Run:

```powershell
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_runner_helpers.py -q
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
Focused tests pass.
verify_nonrelease_sync.py passes.
```

- [ ] **Step 4: Commit documentation**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-21_wide_v1_cli_baseline_backtest.md docs/update_log/2026-04-21_wide_v1_cli_baseline_gate.md
git commit -m "Wide v1 CLI 기준 백테스트 게이트 결과를 기록한다" -m "runtime-preflight가 통과한 ResearchTest wide 조건식을 CLI로 1회 baseline 백테스트하고 GUI 기준 결과와 비교한 판정 결과를 문서화했다.

Constraint: runtime DB, CSV, graph, temp JSON 산출물은 커밋하지 않음
Confidence: medium
Scope-risk: narrow
Tested: runtime-preflight, CLI baseline command, focused unit tests, verify_nonrelease_sync.py
Not-tested: candidate_count=5, WFO, promote"
```

---

## Final Decision Routing

After Task 6, use the documented decision:

```text
PASS:
  $brainstorming Wide v1 Retention-Aware candidate_count=5 실행 재개 설계

HOLD:
  $brainstorming Wide v1 CLI/GUI 결과 차이 원인 분석 설계

FAIL:
  $brainstorming CLI baseline backtest failure checkpoint 분석 설계
```

Do not run `candidate_count=5` until this gate is PASS or a HOLD has a documented, accepted explanation.

## Self-Review Checklist

Spec coverage:

```text
runtime-preflight required before baseline: Task 1
CLI baseline command: Task 2
JSON/checkpoint/CSV result collection: Task 3
GUI comparison: Task 3 and Task 4
PASS/HOLD/FAIL decision: Task 3, Task 4, Task 5
pilot log and update log: Task 4 and Task 5
runtime artifact exclusion: Task 6
```

No code changes are planned. If execution reveals missing runner fields, stop and create a new design/plan for result-field hardening rather than silently expanding this execution plan.
