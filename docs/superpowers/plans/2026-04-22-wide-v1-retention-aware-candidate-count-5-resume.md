# Wide v1 Retention-Aware Candidate Count 5 Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the Wide v1 Retention-Aware `candidate_count=5` research loop after the full-year CLI baseline gate passed, then document candidate results, ranking, cleanup, and the next decision.

**Architecture:** This is an execution-and-documentation plan. It uses the existing `discovery research --run-candidates` path, keeps runtime artifacts out of Git, verifies that every CLI process points at the actual operational `_database` via `STOM_CLI_DATABASE_DIR`, and records only summarized Markdown evidence.

**Tech Stack:** Python 3.11, PowerShell, STOM CLI `stom_backtest.py`, `discovery research`, Retention-Aware candidate selection, JSON/Markdown evidence logs, pytest, `scripts/verify_nonrelease_sync.py`.

---

## Scope

In scope:

- Verify runtime DB paths through `runtime-preflight`.
- Use the PASSed Wide v1 CLI baseline CSV as candidate research input.
- Run `discovery research --run-candidates --candidate-count 5`.
- Record retention selection, candidate results, ranking, best candidate, cleanup, and remaining risks.
- Commit only Markdown logs.

Out of scope:

- Do not run WFO.
- Do not run `discovery promote`.
- Do not change condition generation code.
- Do not change candidate ranking code unless execution reveals a blocking defect.
- Do not commit runtime DB, temp JSON, candidate CSV, graph, or strategy DB artifacts.

## Runtime DB Policy

`STOM_CLI_DATABASE_DIR` must point to the actual operational `_database` folder. It must not semantically depend on the parent folder name such as `STOM_V.wt-dev`.

For this development execution, use the same operational runtime DB that passed the previous GUI compare gate:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
```

If the operational folder is renamed later, update only this env value:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\<현재_운용_폴더>\_database'
```

Before running candidates, verify these paths in `runtime-preflight`:

```text
runtime_profile.setting_db_path
runtime_profile.strategy_db_path
runtime_profile.backtest_db_path
runtime_profile.stock_back_db_path
```

All of them must point under the selected `STOM_CLI_DATABASE_DIR`.

## Inputs

Baseline strategy:

```text
base_buy_strategy=ResearchTest_Tick_B_090000_092800_Wide_20260419
base_sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
```

Baseline CSV:

```text
baseline_csv=backtest/csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
baseline_trade_count=40937
baseline_back_count=1638
```

Candidate run settings:

```text
candidate_count=5
candidate_timeout=900
candidate_pool_multiplier=3
min_estimated_retention=0.4
retention_fallback=enabled
retention_penalty=enabled
```

Runtime-only output:

```text
backtest/temp/wide_v1_retention_candidate_count_5_preflight_20260422.json
backtest/temp/wide_v1_retention_candidate_count_5_result_20260422.json
generated backtest/csv/*.csv
strategy.db temporary candidate strategies
```

Tracked output:

```text
docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_retention_candidate_count_5.md
docs/update_log/2026-04-22_wide_v1_retention_candidate_count_5.md
```

---

### Task 1: Runtime Preconditions

**Files:**
- Runtime only: `backtest/temp/wide_v1_retention_candidate_count_5_preflight_20260422.json`
- No tracked file changes.

- [ ] **Step 1: Confirm branch and clean tracked state**

Run:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare
git status --short --branch --untracked-files=all
git log --oneline -8 --decorate
```

Expected:

```text
## feature/wide-v1-cli-baseline-gui-compare
```

Only ignored/untracked runtime artifacts may exist. No tracked modifications should be present before running candidate research.

- [ ] **Step 2: Confirm baseline CSV exists**

Run:

```powershell
$baselineCsv = 'backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv'
Get-Item $baselineCsv | Select-Object FullName,Length,LastWriteTime
```

Expected:

```text
The CSV exists and Length is greater than 0.
```

If it does not exist, do not continue. Re-run the previous Wide v1 CLI baseline GUI compare plan first.

- [ ] **Step 3: Run runtime-preflight and save UTF-8 JSON**

Run:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
$out = python stom_backtest.py runtime-preflight `
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
  --timeout 900
$out | Set-Content -LiteralPath backtest\temp\wide_v1_retention_candidate_count_5_preflight_20260422.json -Encoding UTF8
$out
```

Expected:

```text
status is ok.
failed_checks is [].
validation_errors is [].
buy and sell status are ok.
stock_back_db_usable is true.
```

- [ ] **Step 4: Verify preflight and runtime DB paths programmatically**

Run:

```powershell
@'
import json
from pathlib import Path

expected_root = r'C:\System_Trading\STOM\STOM_V.wt-dev\_database'
path = Path('backtest/temp/wide_v1_retention_candidate_count_5_preflight_20260422.json')
payload = json.loads(path.read_text(encoding='utf-8-sig'))
runtime = payload.get('runtime_profile') or {}

for key in [
    'setting_db_path',
    'strategy_db_path',
    'backtest_db_path',
    'stock_back_db_path',
]:
    value = runtime.get(key)
    print(key, value)
    if not value or not value.startswith(expected_root):
        raise SystemExit(f'{key} does not use expected runtime DB root')

print('status', payload.get('status'))
print('failed_checks', payload.get('failed_checks'))
print('validation_errors', payload.get('validation_errors'))
print('buy_status', payload.get('strategies', {}).get('buy', {}).get('status'))
print('sell_status', payload.get('strategies', {}).get('sell', {}).get('status'))
print('stock_back_db_usable', runtime.get('stock_back_db_usable'))

if payload.get('status') != 'ok':
    raise SystemExit('preflight status is not ok')
if payload.get('failed_checks') != []:
    raise SystemExit('preflight failed_checks is not empty')
if payload.get('validation_errors') != []:
    raise SystemExit('preflight validation_errors is not empty')
if payload.get('strategies', {}).get('buy', {}).get('status') != 'ok':
    raise SystemExit('buy strategy is not ok')
if payload.get('strategies', {}).get('sell', {}).get('status') != 'ok':
    raise SystemExit('sell strategy is not ok')
if runtime.get('stock_back_db_usable') is not True:
    raise SystemExit('stock_back_db_usable is not true')
'@ | python -
```

Expected:

```text
All four DB paths start with the selected runtime DB root.
The script exits 0.
```

If this fails, do not run Task 2. Document `decision=FAIL` in Task 4.

---

### Task 2: Candidate Count 5 Execution

**Files:**
- Runtime only: `backtest/temp/wide_v1_retention_candidate_count_5_result_20260422.json`
- Runtime only: generated `backtest/csv/*.csv`
- Runtime only: temporary candidate strategies in strategy DB
- No tracked file changes.

- [ ] **Step 1: Record candidate strategy rows before execution**

Run:

```powershell
@'
import os
import sqlite3

db = os.environ.get('STOM_CLI_DB_STRATEGY') or r'C:\System_Trading\STOM\STOM_V.wt-dev\_database\strategy.db'
prefix = 'WideV1RetentionCand5_20260422__cand'
con = sqlite3.connect(db)
try:
    rows = con.execute(
        "SELECT `index` FROM stockbuy WHERE `index` LIKE ? ORDER BY `index`",
        (prefix + '%',),
    ).fetchall()
finally:
    con.close()
print('strategy_db', db)
print('existing_candidate_rows', [row[0] for row in rows])
'@ | python -
```

Expected:

```text
existing_candidate_rows []
```

If rows already exist, record them in the pilot log and allow the research loop cleanup behavior to handle them only if they are clearly from this exact run prefix.

- [ ] **Step 2: Run candidate_count=5 research**

Run:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
python stom_backtest.py discovery research WideV1RetentionCand5_20260422 `
  --baseline-csv backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv `
  --base-buy-strategy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --base-sell-strategy ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --run-candidates `
  --candidate-count 5 `
  --candidate-timeout 900 `
  --min-estimated-retention 0.4 `
  --candidate-pool-multiplier 3 `
  | Set-Content -LiteralPath backtest\temp\wide_v1_retention_candidate_count_5_result_20260422.json -Encoding UTF8
```

Expected success shape:

```text
Command exits 0.
JSON result file exists.
result status is ok or a documented non-fatal candidate quality phase.
candidate_results or equivalent candidate list is present.
```

Expected failure shape:

```text
Command exits non-zero, or result phase explains failure.
The JSON file may still contain structured failure data.
```

- [ ] **Step 3: Confirm result file exists**

Run:

```powershell
Get-Item backtest\temp\wide_v1_retention_candidate_count_5_result_20260422.json |
  Select-Object FullName,Length,LastWriteTime
```

Expected:

```text
Length is greater than 0.
```

- [ ] **Step 4: Record candidate strategy rows after execution**

Run:

```powershell
@'
import os
import sqlite3

db = os.environ.get('STOM_CLI_DB_STRATEGY') or r'C:\System_Trading\STOM\STOM_V.wt-dev\_database\strategy.db'
prefix = 'WideV1RetentionCand5_20260422__cand'
con = sqlite3.connect(db)
try:
    rows = con.execute(
        "SELECT `index` FROM stockbuy WHERE `index` LIKE ? ORDER BY `index`",
        (prefix + '%',),
    ).fetchall()
finally:
    con.close()
print('strategy_db', db)
print('remaining_candidate_rows', [row[0] for row in rows])
'@ | python -
```

Expected:

```text
remaining_candidate_rows []
```

If rows remain, document them as cleanup risk and do not delete manually unless the cleanup policy says they are failed/lost candidates for this exact prefix.

---

### Task 3: Result Extraction And Decision

**Files:**
- Runtime only: reads `backtest/temp/wide_v1_retention_candidate_count_5_result_20260422.json`
- No tracked file changes.

- [ ] **Step 1: Print top-level result summary**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path('backtest/temp/wide_v1_retention_candidate_count_5_result_20260422.json')
payload = json.loads(path.read_text(encoding='utf-8-sig'))

for key in [
    'status',
    'phase',
    'message',
    'strategy_name',
    'best_candidate',
]:
    print(key, payload.get(key))

for key in [
    'iteration_plan',
    'retention_selection',
    'ranking',
    'candidate_results',
    'candidates',
    'cleanup',
]:
    value = payload.get(key)
    if isinstance(value, list):
        print(key, 'list', len(value))
    elif isinstance(value, dict):
        print(key, 'dict', sorted(value.keys()))
    else:
        print(key, type(value).__name__, value)
'@ | python -
```

Expected:

```text
Top-level status/phase/message and candidate-related sections are printed.
```

- [ ] **Step 2: Extract candidate table**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path('backtest/temp/wide_v1_retention_candidate_count_5_result_20260422.json')
payload = json.loads(path.read_text(encoding='utf-8-sig'))

candidates = (
    payload.get('candidate_results')
    or payload.get('candidates')
    or payload.get('ranked_candidates')
    or []
)

print('candidate_count_observed', len(candidates))
for index, item in enumerate(candidates, start=1):
    score = item.get('score') or item.get('comparison') or item
    retention_estimate = item.get('retention_estimate') or {}
    print('--- candidate', index)
    print('strategy_name', item.get('strategy_name'))
    print('expression', item.get('expression'))
    print('status', item.get('status'))
    print('estimated_retention', retention_estimate.get('estimated_retention'))
    print('retention_filter_passed', item.get('retention_filter_passed'))
    print('retention_fallback_used', item.get('retention_fallback_used'))
    print('trade_count', score.get('trade_count'))
    print('trade_count_retention', score.get('trade_count_retention'))
    print('promotion_score', score.get('promotion_score'))
    print('retention_penalty', score.get('retention_penalty'))
    print('adjusted_score', score.get('adjusted_score'))
    print('csv_path', item.get('csv_path'))
    print('cleanup_status', item.get('cleanup_status') or item.get('cleanup'))
'@ | python -
```

Expected:

```text
Five candidate blocks or a clear lower count with explanation.
```

- [ ] **Step 3: Determine execution decision**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path('backtest/temp/wide_v1_retention_candidate_count_5_result_20260422.json')
payload = json.loads(path.read_text(encoding='utf-8-sig'))

candidates = (
    payload.get('candidate_results')
    or payload.get('candidates')
    or payload.get('ranked_candidates')
    or []
)
status = payload.get('status')
phase = payload.get('phase')
message = payload.get('message')
best_candidate = payload.get('best_candidate')

candidate_count_observed = len(candidates)
has_ranking = bool(payload.get('ranking') or payload.get('ranked_candidates') or candidates)
cleanup_known = True
for item in candidates:
    if 'cleanup_status' not in item and 'cleanup' not in item:
        cleanup_known = False

all_promotion_failed = False
if candidate_count_observed:
    pass_values = []
    for item in candidates:
        score = item.get('score') or item.get('comparison') or item
        passed = score.get('passed')
        if passed is not None:
            pass_values.append(bool(passed))
    all_promotion_failed = bool(pass_values) and not any(pass_values)

if candidate_count_observed >= 5 and has_ranking:
    if all_promotion_failed:
        decision = 'PASS_WITH_NO_PROMOTION'
        reason = 'candidate_count=5 executed and all candidates failed promotion gate; this is a quality result, not runtime failure.'
    else:
        decision = 'PASS_FOR_EXECUTION'
        reason = 'candidate_count=5 executed and ranking data is present.'
elif status in ('ok', 'success') and candidate_count_observed > 0:
    decision = 'HOLD'
    reason = 'candidate execution completed but fewer than 5 candidates or incomplete ranking/cleanup data was observed.'
else:
    decision = 'FAIL'
    reason = f'candidate execution did not produce usable candidate results: status={status}, phase={phase}, message={message}'

print('status', status)
print('phase', phase)
print('candidate_count_observed', candidate_count_observed)
print('has_ranking', has_ranking)
print('cleanup_known', cleanup_known)
print('best_candidate', best_candidate)
print('all_promotion_failed', all_promotion_failed)
print('decision', decision)
print('reason', reason)
'@ | python -
```

Expected:

```text
decision PASS_FOR_EXECUTION
```

`PASS_WITH_NO_PROMOTION` is also acceptable if all candidates ran but failed quality gates.

---

### Task 4: Pilot Log Documentation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_retention_candidate_count_5.md`

- [ ] **Step 1: Generate pilot log**

Run:

```powershell
@'
import json
from pathlib import Path

preflight_path = Path('backtest/temp/wide_v1_retention_candidate_count_5_preflight_20260422.json')
result_path = Path('backtest/temp/wide_v1_retention_candidate_count_5_result_20260422.json')
out_path = Path('docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_retention_candidate_count_5.md')
out_path.parent.mkdir(parents=True, exist_ok=True)

preflight = json.loads(preflight_path.read_text(encoding='utf-8-sig'))
payload = json.loads(result_path.read_text(encoding='utf-8-sig'))
runtime = preflight.get('runtime_profile') or {}
candidates = (
    payload.get('candidate_results')
    or payload.get('candidates')
    or payload.get('ranked_candidates')
    or []
)

candidate_lines = []
for index, item in enumerate(candidates, start=1):
    score = item.get('score') or item.get('comparison') or item
    retention_estimate = item.get('retention_estimate') or {}
    candidate_lines.extend([
        f'candidate_{index}.strategy_name={item.get("strategy_name")}',
        f'candidate_{index}.status={item.get("status")}',
        f'candidate_{index}.estimated_retention={retention_estimate.get("estimated_retention")}',
        f'candidate_{index}.retention_filter_passed={item.get("retention_filter_passed")}',
        f'candidate_{index}.retention_fallback_used={item.get("retention_fallback_used")}',
        f'candidate_{index}.trade_count={score.get("trade_count")}',
        f'candidate_{index}.trade_count_retention={score.get("trade_count_retention")}',
        f'candidate_{index}.promotion_score={score.get("promotion_score")}',
        f'candidate_{index}.retention_penalty={score.get("retention_penalty")}',
        f'candidate_{index}.adjusted_score={score.get("adjusted_score")}',
        f'candidate_{index}.csv_path={item.get("csv_path")}',
        f'candidate_{index}.cleanup_status={item.get("cleanup_status") or item.get("cleanup")}',
    ])

candidate_count_observed = len(candidates)
has_ranking = bool(payload.get('ranking') or payload.get('ranked_candidates') or candidates)
pass_values = []
for item in candidates:
    score = item.get('score') or item.get('comparison') or item
    passed = score.get('passed')
    if passed is not None:
        pass_values.append(bool(passed))
all_promotion_failed = bool(pass_values) and not any(pass_values)

if candidate_count_observed >= 5 and has_ranking:
    if all_promotion_failed:
        decision = 'PASS_WITH_NO_PROMOTION'
        reason = 'candidate_count=5 executed and all candidates failed promotion gate; this is a quality result, not runtime failure.'
        next_command = '$brainstorming Wide v1 후보 결과 분석 및 반복 개선 루프 v2 설계'
    else:
        decision = 'PASS_FOR_EXECUTION'
        reason = 'candidate_count=5 executed and ranking data is present.'
        next_command = '$brainstorming Wide v1 후보 결과 분석 및 반복 개선 루프 v2 설계'
elif payload.get('status') in ('ok', 'success') and candidate_count_observed > 0:
    decision = 'HOLD'
    reason = 'candidate execution completed but fewer than 5 candidates or incomplete ranking/cleanup data was observed.'
    next_command = '$brainstorming Wide v1 candidate_count=5 부분 실행 원인 분석 설계'
else:
    decision = 'FAIL'
    reason = f"candidate execution did not produce usable candidate results: status={payload.get('status')}, phase={payload.get('phase')}, message={payload.get('message')}"
    next_command = '$brainstorming Wide v1 candidate_count=5 실행 실패 checkpoint 분석 설계'

lines = [
    '# Wide v1 Retention-Aware Candidate Count 5 Pilot',
    '',
    '## 목적',
    '',
    'Wide v1 CLI baseline PASS 이후 Retention-Aware 후보 5개 자동 백테스트를 재개하고, 후보별 실행 결과와 ranking/cleanup 상태를 확인한다.',
    '',
    '## 전체 플로우',
    '',
    '```text',
    '[Wide v1 CLI baseline PASS]',
    '        |',
    '        v',
    '[runtime-preflight]',
    '        |',
    '        v',
    '[discovery research --run-candidates --candidate-count 5]',
    '        |',
    '        v',
    '[candidate ranking / cleanup 확인]',
    '        |',
    '        v',
    f'[{decision}]',
    '```',
    '',
    '## runtime DB path 검증',
    '',
    '```text',
    f"setting_db_path={runtime.get('setting_db_path')}",
    f"strategy_db_path={runtime.get('strategy_db_path')}",
    f"backtest_db_path={runtime.get('backtest_db_path')}",
    f"stock_back_db_path={runtime.get('stock_back_db_path')}",
    f"stock_back_db_usable={runtime.get('stock_back_db_usable')}",
    '```',
    '',
    '## 실행 조건',
    '',
    '```text',
    'baseline_csv=backtest/csv\\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv',
    'base_buy_strategy=ResearchTest_Tick_B_090000_092800_Wide_20260419',
    'base_sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419',
    'candidate_count=5',
    'candidate_timeout=900',
    'min_estimated_retention=0.4',
    'candidate_pool_multiplier=3',
    'retention_fallback=enabled',
    'retention_penalty=enabled',
    '```',
    '',
    '## 결과 요약',
    '',
    '```text',
    f"status={payload.get('status')}",
    f"phase={payload.get('phase')}",
    f"message={payload.get('message')}",
    f"candidate_count_observed={candidate_count_observed}",
    f"has_ranking={has_ranking}",
    f"best_candidate={payload.get('best_candidate')}",
    '```',
    '',
    '## 후보별 결과',
    '',
    '```text',
    *(candidate_lines or ['candidate_results=not_present']),
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
    '- best_candidate는 최종 채택이 아니다.',
    '- 최종 채택 전에는 반복 개선 루프 v2, promote 또는 WFO 검증이 필요하다.',
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
docs\research\condition_research\pilot_logs\2026-04-22_wide_v1_retention_candidate_count_5.md
decision PASS_FOR_EXECUTION
```

`PASS_WITH_NO_PROMOTION` is acceptable if all candidates ran but failed quality gates.

- [ ] **Step 2: Verify pilot log has no unresolved markers**

Run:

```powershell
$patterns = @('T' + 'BD', 'TO' + 'DO', 'FIX' + 'ME', 'actual' + '_', 'observ' + 'ed') -join '|'
rg -n $patterns docs\research\condition_research\pilot_logs\2026-04-22_wide_v1_retention_candidate_count_5.md
```

Expected:

```text
No output.
```

---

### Task 5: Update Log Documentation

**Files:**
- Create: `docs/update_log/2026-04-22_wide_v1_retention_candidate_count_5.md`

- [ ] **Step 1: Generate update log**

Run:

```powershell
@'
from pathlib import Path
import re

pilot_path = Path('docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_retention_candidate_count_5.md')
out_path = Path('docs/update_log/2026-04-22_wide_v1_retention_candidate_count_5.md')
text = pilot_path.read_text(encoding='utf-8')

def extract(name):
    match = re.search(rf'^{re.escape(name)}=(.*)$', text, flags=re.MULTILINE)
    return match.group(1).strip() if match else 'not_present'

decision = extract('decision')
next_command = extract('next_command')

lines = [
    '# 2026-04-22 Wide v1 Retention-Aware Candidate Count 5',
    '',
    '## 목적',
    '',
    'Wide v1 CLI baseline PASS 이후 Retention-Aware 후보 5개 자동 백테스트를 재개하고 실행 결과를 문서화했다.',
    '',
    '## 전체 플로우',
    '',
    '```text',
    '[완료] Wide v1 CLI baseline GUI compare PASS',
    '        |',
    '        v',
    '[이번 작업] candidate_count=5 실행',
    '        |',
    '        v',
    '[이번 작업] ranking / cleanup 확인',
    '        |',
    '        v',
    f'[판정] {decision}',
    '```',
    '',
    '## 결과 요약',
    '',
    '```text',
    f"status={extract('status')}",
    f"phase={extract('phase')}",
    f"candidate_count_observed={extract('candidate_count_observed')}",
    f"best_candidate={extract('best_candidate')}",
    f"decision={decision}",
    '```',
    '',
    '## 판정',
    '',
    '```text',
    f"decision={decision}",
    f"reason={extract('reason')}",
    f"next_command={next_command}",
    '```',
    '',
    '## 남은 리스크',
    '',
    '- best_candidate는 최종 채택이 아니다.',
    '- 최종 채택 전에는 반복 개선 루프 v2, promote 또는 WFO 검증이 필요하다.',
    '- 후보가 모두 promotion gate를 통과하지 못했다면 후보 품질 개선이 다음 단계다.',
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
docs\update_log\2026-04-22_wide_v1_retention_candidate_count_5.md
decision PASS_FOR_EXECUTION
```

- [ ] **Step 2: Verify update log has no unresolved markers**

Run:

```powershell
$patterns = @('T' + 'BD', 'TO' + 'DO', 'FIX' + 'ME', 'actual' + '_', 'observ' + 'ed') -join '|'
rg -n $patterns docs\update_log\2026-04-22_wide_v1_retention_candidate_count_5.md
```

Expected:

```text
No output.
```

---

### Task 6: Verification And Commit

**Files:**
- Commit:
  - `docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_retention_candidate_count_5.md`
  - `docs/update_log/2026-04-22_wide_v1_retention_candidate_count_5.md`

Do not commit:

```text
backtest/temp/*.json
backtest/csv/*.csv
backtest/graph/
_database/*.db
```

- [ ] **Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py tests/unit/test_setting_base_cli_overrides.py -q
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
?? docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_retention_candidate_count_5.md
?? docs/update_log/2026-04-22_wide_v1_retention_candidate_count_5.md
```

Runtime files may exist but must not be staged.

- [ ] **Step 3: Commit documentation**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_retention_candidate_count_5.md docs/update_log/2026-04-22_wide_v1_retention_candidate_count_5.md
git commit -m "Wide v1 후보 5개 실행 결과를 기록한다" -m "Wide v1 CLI baseline PASS 이후 Retention-Aware candidate_count=5 실행 결과와 ranking, cleanup, 다음 판정을 문서화했다.

Constraint: runtime DB, CSV, graph, temp JSON 산출물은 커밋하지 않음
Confidence: medium
Scope-risk: narrow
Tested: runtime-preflight, discovery research candidate_count=5 command, focused unit tests, verify_nonrelease_sync.py
Not-tested: WFO, promote"
```

---

## Final Decision Routing

Use the documented decision:

```text
PASS_FOR_EXECUTION or PASS_WITH_NO_PROMOTION:
  $brainstorming Wide v1 후보 결과 분석 및 반복 개선 루프 v2 설계

HOLD:
  $brainstorming Wide v1 candidate_count=5 부분 실행 원인 분석 설계

FAIL:
  $brainstorming Wide v1 candidate_count=5 실행 실패 checkpoint 분석 설계
```

## Self-Review Checklist

Spec coverage:

```text
runtime DB path policy: Task 1
preflight: Task 1
candidate_count=5 execution: Task 2
candidate result extraction: Task 3
PASS/HOLD/FAIL decision: Task 3 and Task 4
pilot/update logs: Task 4 and Task 5
artifact exclusion and verification: Task 6
```

No WFO, promote, condition regeneration, or code changes are planned. If candidate execution fails because of missing runtime fields or parser issues, stop and create a failure-analysis design rather than silently changing research loop behavior.
