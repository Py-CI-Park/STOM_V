# Wide v1 Retention-Aware Candidate Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one Retention-Aware candidate improvement round using the Wide v1 tick baseline CSV, then record candidate ranking, cleanup, and next-step decisions.

**Architecture:** This is an execution-and-documentation plan. Use the existing `discovery research --run-candidates` path; do not add code. Record results under `docs/research/condition_research/pilot_logs/` and `docs/update_log/`, while keeping `strategy.db`, generated CSV files, and graph data out of Git.

**Tech Stack:** Python 3.11, STOM CLI, existing `discovery research`, SQLite runtime DB, pytest.

---

## Full Flow

```text
[0. Wide v1 조건식]
   ResearchTest_Tick_B_090000_092800_Wide_20260419
   ResearchTest_Tick_S_090000_092800_Wide_20260419
        |
        v
[1. Wide v1 백테스트 CSV]
   40,937 executed trades
        |
        v
[2. Retention-Aware 후보 생성/선별]  <- this plan
        |
        v
[3. 후보 5개 백테스트]
        |
        v
[4. Retention-Penalized Ranking]
        |
        v
[5. best_candidate 분석]
        |
        v
[6. 다음 조건식 개선 방향]
```

## Scope Check

In scope:

- Verify the Wide v1 CSV and strategy names exist.
- Run `discovery research --run-candidates --candidate-count 5`.
- Capture JSON result summary.
- Verify candidate strategy cleanup.
- Record pilot log and update log.
- Run focused verification after documentation.

Out of scope:

- Code changes.
- WFO or `discovery promote`.
- Multi-round improvement loop v2.
- Creating a new Wide2 condition.
- Committing runtime DB, CSV, graph, or `_database` files.

## Input Contract

CSV:

```text
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

Strategies:

```text
buy:
ResearchTest_Tick_B_090000_092800_Wide_20260419

sell:
ResearchTest_Tick_S_090000_092800_Wide_20260419
```

Backtest context:

```text
start: 20250101
end: 20251231
timeframe: tick
avg_time: 30
start_time: 90000
end_time: 92800
engines: 32
```

---

### Task 1: Preflight Runtime Verification

**Files:**
- No tracked file changes.

- [ ] **Step 1: Confirm branch and clean state**

Run:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-dev
git status --short --branch
```

Expected:

```text
## STOM_Version_2U_C...origin/STOM_Version_2U_C
?? backtest/graph/
```

`backtest/graph/` is protected generated result data. Do not touch it.

- [ ] **Step 2: Confirm input CSV exists**

Run:

```powershell
Test-Path C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
Get-Item C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv | Select-Object FullName,Length,LastWriteTime
```

Expected:

```text
True
Length: 11137772
```

- [ ] **Step 3: Confirm strategies exist in runtime DB**

Run:

```powershell
@'
import sqlite3
from cli.paths import DB_STRATEGY

names = [
    ('stockbuy', 'ResearchTest_Tick_B_090000_092800_Wide_20260419'),
    ('stocksell', 'ResearchTest_Tick_S_090000_092800_Wide_20260419'),
]

print('DB_STRATEGY', DB_STRATEGY)
with sqlite3.connect(DB_STRATEGY) as con:
    for table, name in names:
        count = con.execute(f'SELECT COUNT(*) FROM {table} WHERE "index"=?', (name,)).fetchone()[0]
        print(table, name, count)
'@ | python -
```

Expected:

```text
stockbuy ResearchTest_Tick_B_090000_092800_Wide_20260419 1
stocksell ResearchTest_Tick_S_090000_092800_Wide_20260419 1
```

- [ ] **Step 4: Confirm no stale candidate strategies**

Run:

```powershell
@'
import sqlite3
from cli.paths import DB_STRATEGY

base = 'ResearchWideRetention_20260420'
with sqlite3.connect(DB_STRATEGY) as con:
    for idx in range(1, 6):
        name = f'{base}__cand{idx:03d}'
        count = con.execute('SELECT COUNT(*) FROM stockbuy WHERE "index"=?', (name,)).fetchone()[0]
        print(name, count)
'@ | python -
```

Expected:

```text
ResearchWideRetention_20260420__cand001 0
ResearchWideRetention_20260420__cand002 0
ResearchWideRetention_20260420__cand003 0
ResearchWideRetention_20260420__cand004 0
ResearchWideRetention_20260420__cand005 0
```

- [ ] **Step 5: Confirm no stale STOM candidate process**

Run:

```powershell
Get-CimInstance Win32_Process -Filter "name = 'python.exe' OR name = 'python32.exe'" |
  Where-Object { $_.CommandLine -match 'ResearchWideRetention_20260420|ResearchTest_Tick|stom_backtest' } |
  Select-Object ProcessId, Name, CommandLine
```

Expected:

```text
no output
```

If output appears, stop and inspect before running Task 2.

---

### Task 2: Run Wide v1 Retention-Aware Candidate Research

**Files:**
- Runtime generated CSV and DB side effects only.
- Do not commit runtime artifacts.

- [ ] **Step 1: Run candidate research**

Run:

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'

python stom_backtest.py discovery research ResearchWideRetention_20260420 `
  --input C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv `
  --base-buy-strategy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --min-samples 30 `
  --run-candidates `
  --candidate-count 5 `
  --min-estimated-retention 0.4 `
  --candidate-start 20250101 `
  --candidate-end 20251231 `
  --candidate-timeout 900 `
  --cleanup-best-candidate
```

- [ ] **Step 2: Record key output fields**

Capture from JSON output:

```text
status
phase
retention_selection
candidates count
candidate expression
candidate estimated_retention
candidate actual trade_count_retention
candidate adjusted_score
candidate promotion.passed
candidate promotion.reasons
best_candidate
cleanup_summary
```

- [ ] **Step 3: Verify cleanup**

Run:

```powershell
@'
import sqlite3
from cli.paths import DB_STRATEGY

base = 'ResearchWideRetention_20260420'
with sqlite3.connect(DB_STRATEGY) as con:
    for idx in range(1, 6):
        name = f'{base}__cand{idx:03d}'
        count = con.execute('SELECT COUNT(*) FROM stockbuy WHERE "index"=?', (name,)).fetchone()[0]
        print(name, count)
'@ | python -
```

Expected:

```text
all candidate counts are 0
```

- [ ] **Step 4: If command times out**

If the command does not return, stop the process tree for the specific `ResearchWideRetention_20260420` command only, then clean `backdata_*` shared memory.

Use:

```powershell
Get-CimInstance Win32_Process -Filter "name = 'python.exe' OR name = 'python32.exe'" |
  Where-Object { $_.CommandLine -match 'ResearchWideRetention_20260420' } |
  Select-Object ProcessId, Name, CommandLine
```

Then stop only those matching processes and their children.

Record timeout as a result. Do not mark the research run successful.

---

### Task 3: Record Pilot Log

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-20_wide_v1_retention_aware_candidates.md`
- Create: `docs/update_log/2026-04-20_wide_v1_retention_aware_candidate_research.md`

- [ ] **Step 1: Create pilot log**

Create `docs/research/condition_research/pilot_logs/2026-04-20_wide_v1_retention_aware_candidates.md`:

```markdown
# Wide v1 Retention-Aware Candidate Research

## 전체 플로우

```text
[Wide v1 CSV]
        |
        v
[Retention-Aware candidate selection]
        |
        v
[candidate backtests]
        |
        v
[Retention-Penalized Ranking]
        |
        v
[best_candidate analysis]
```

## 입력

- input_csv: `C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv`
- base_buy_strategy: `ResearchTest_Tick_B_090000_092800_Wide_20260419`
- sell_strategy: `ResearchTest_Tick_S_090000_092800_Wide_20260419`

## 실행 명령

Task 2에서 실행한 명령을 그대로 기록한다.

## 결과

실제 JSON 핵심 결과를 기록한다.

## 후보 분석

| rank | strategy | expression | estimated_retention | actual_retention | adjusted_score | passed | reasons |
| --- | --- | --- | --- | --- | --- | --- | --- |

## cleanup 확인

candidate strategy 잔여 여부를 기록한다.

## 다음 판단

promotion 통과 여부와 다음 단계 결정을 기록한다.
```

- [ ] **Step 2: Create update log**

Create `docs/update_log/2026-04-20_wide_v1_retention_aware_candidate_research.md`:

```markdown
# 2026-04-20 Wide v1 Retention-Aware Candidate Research

## 목적

Wide v1 백테스트 CSV를 Retention-Aware 후보 개선 루프에 넣고 후보 5개를 백테스트/랭킹한다.

## 전체 플로우

[Wide v1 CSV] -> [Retention-Aware 후보 선별] -> [후보 백테스트] -> [best_candidate 분석]

## 결과

실제 실행 결과를 기록한다.

## 다음 단계

실행 결과에 따라 promote/WFO, 후보 생성 조정, 또는 v2 반복 개선 설계로 이동한다.
```

- [ ] **Step 3: Run docs check**

Run:

```powershell
git diff --check
```

Expected:

```text
no output
```

- [ ] **Step 4: Commit logs**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-20_wide_v1_retention_aware_candidates.md docs/update_log/2026-04-20_wide_v1_retention_aware_candidate_research.md
git commit -m "와이드 기준 CSV 후보 개선 결과를 기록한다" -m "ResearchTest wide tick CSV를 Retention-Aware 후보 개선 루프에 입력한 결과와 후보별 ranking, cleanup, 다음 판단을 기록했다.

Constraint: 후보 전략과 백테스트 CSV는 런타임 산출물이므로 커밋하지 않음
Confidence: medium
Scope-risk: narrow
Tested: python stom_backtest.py discovery research ResearchWideRetention_20260420
Tested: git diff --check"
```

---

### Task 4: Final Verification

**Files:**
- Modify prior task docs only if verification exposes a documentation issue.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

- [ ] **Step 2: Run guardrail**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

- [ ] **Step 3: Verify worktree**

Run:

```powershell
git status --short --branch
git log --oneline --decorate --max-count=8
```

- [ ] **Step 4: Report next command**

Based on actual result:

```text
If candidate passes promotion:
  next command is discovery promote / WFO planning.

If best_candidate exists but fails promotion:
  next command is $brainstorming Wide v1 best_candidate failure analysis and v2 loop design.

If no candidates evaluated:
  next command is $brainstorming Wide v1 candidate generation/gate tuning.
```

## Final Verification Checklist

- [ ] Input CSV exists.
- [ ] Baseline strategies exist.
- [ ] `discovery research --run-candidates` attempted.
- [ ] Result recorded.
- [ ] Candidate cleanup verified.
- [ ] Focused tests pass.
- [ ] `verify_nonrelease_sync.py` passes.
- [ ] Runtime DB/CSV not committed.

## Plan Self-Review Notes

- Scope: this plan only executes and records one Wide v1 Retention-Aware candidate research round.
- Non-goals: no WFO, no promote, no automatic v2 loop, no code changes.
- Type consistency: command names and paths match the design document.
