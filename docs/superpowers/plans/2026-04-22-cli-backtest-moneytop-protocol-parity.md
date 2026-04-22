# CLI BackTest Moneytop Protocol Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine why CLI BackTest child process cannot read `moneytop` while GUI/STOM can, then add the smallest safe instrumentation or runtime-path fix needed to make the difference explicit and reproducible.

**Architecture:** Start with evidence, not a workaround. First classify past CLI validation evidence, then document GUI/CLI protocol differences, then add child runtime-path and moneytop-query diagnostics to CLI output. Only after diagnostics identify the mismatch should a minimal runtime-context fix be implemented; do not create temporary `moneytop` tables in this plan.

**Tech Stack:** Python 3.11, SQLite, STOM GUI/CLI backtest code, pytest source/behavioral tests, Markdown research logs.

---

## Scope

In scope:

- Review past CLI validation claims and classify them as Level 0-3.
- Document GUI `backengine_start()` and BackTest execute protocol against CLI `run_backtest()`.
- Add diagnostics showing parent/child DB paths and BackTest child `moneytop` query failure context.
- Preserve structured JSON output for these diagnostics.
- Run smoke tests to verify the diagnostics identify the child/runtime path problem.
- Document findings and next decision.

Out of scope:

- Do not run `candidate_count=5`.
- Do not create temporary `moneytop` tables.
- Do not implement a persistent CLI engine session.
- Do not change GUI code.
- Do not run WFO or promote.
- Do not change strategy generation.

## File Structure

Create:

- `docs/research/condition_research/pilot_logs/2026-04-22_cli_historical_validation_review.md`
  - Past CLI validation evidence classified into Level 0-3.

- `docs/research/condition_research/pilot_logs/2026-04-22_gui_cli_backtest_protocol_diff.md`
  - GUI engine-start/backtest-execute protocol vs CLI run_backtest protocol.

- `docs/research/condition_research/pilot_logs/2026-04-22_cli_moneytop_protocol_smoke.md`
  - Smoke command results after diagnostics.

- `docs/update_log/2026-04-22_cli_backtest_moneytop_protocol_parity.md`
  - Summary of evidence, code changes, smoke result, remaining risk.

Modify if diagnostics are implemented:

- `backtest/backtest.py`
  - Record child DB paths and `moneytop` query status in a structured place or emit to queue before failure.

- `cli/runner.py`
  - Capture diagnostic messages from BackTest child if needed and include them in result JSON.

- `cli/output.py`
  - Preserve any new diagnostic fields in user-visible JSON.

- `tests/unit/test_runner_helpers.py`
  - Source/behavioral checks for diagnostic plumbing.

- `tests/unit/test_output.py`
  - JSON preservation checks for new diagnostic fields.

Do not commit:

- `_database/*.db`
- `backtest/temp/*.json`
- generated `backtest/csv/*.csv`
- `backtest/graph/`

## Validation Levels

Use these levels when reviewing historical CLI claims:

```text
Level 0: Parser / dry-run
Level 1: Mocked runner
Level 2: Actual CLI backtest execution with success/CSV
Level 3: GUI and CLI result parity with same strategy/date/time/timeframe/engine count and back_count/trade_count comparison
```

Current Wide v1 research requires Level 3.

---

### Task 1: Historical CLI Validation Review

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-22_cli_historical_validation_review.md`

- [ ] **Step 1: Search historical CLI validation references**

Run:

```powershell
rg -n "CLI|cli|stom_backtest|run_backtest|dry-run|CSV|trade_count|back_count|동일|same|success|timeout" docs\research docs\pr tests\unit -g "*.md" -g "*.py"
```

Expected:

```text
References in docs/research, docs/pr, and unit tests are printed.
```

- [ ] **Step 2: Review high-priority documents**

Read these files and note concrete evidence:

```powershell
Get-Content docs\research\2026-03-05_v251_cli_comprehensive_review_plan.md | Select-Object -First 260
Get-Content docs\research\2026-03-15_current_branch_actual_test_report.md | Select-Object -First 340
Get-Content docs\research\2026-03-17_auto_discovery_pipeline_roadmap.md | Select-Object -First 220
Get-Content docs\pr\2026-04-18_candidate_backtest_runtime_hardening_pr.md | Select-Object -First 180
Get-Content docs\pr\2026-04-18_backtest_iteration_research_loop_pr.md | Select-Object -First 220
Get-Content docs\pr\2026-04-21_cli_gui_tick_backtest_parity_preflight_pr.md | Select-Object -First 220
```

- [ ] **Step 3: Create historical validation review document**

Create `docs/research/condition_research/pilot_logs/2026-04-22_cli_historical_validation_review.md` with this structure and concrete entries:

```markdown
# CLI Historical Validation Review

## 목적

과거 CLI 백테스트 검증 기록을 Level 0~3으로 재분류해, 현재 Wide v1 tick baseline 문제에 적용 가능한 근거와 새로 필요한 검증을 분리한다.

## 검증 레벨

```text
Level 0: Parser / dry-run
Level 1: Mocked runner
Level 2: Actual CLI backtest execution with success/CSV
Level 3: GUI/CLI parity with back_count/trade_count comparison
```

## 검토 결과

| Source | Evidence | Level | Current Wide v1 applicability |
| --- | --- | --- | --- |
| docs/research/... | concrete summary | Level N | applies / partial / not enough |

## 결론

- 과거 검증 중 현재 Wide v1 Level 3 요구를 직접 만족하는 항목:
- 현재 새로 검증해야 하는 항목:
- moneytop/BackTest child 경로와 관련해 과거 기록에서 확인된 점:
```

- [ ] **Step 4: Ensure no placeholders remain**

Run:

```powershell
rg -n "concrete summary|Level N|새로 검증해야 하는 항목:$" docs\research\condition_research\pilot_logs\2026-04-22_cli_historical_validation_review.md
```

Expected:

```text
No output
```

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-22_cli_historical_validation_review.md
git commit -m "과거 CLI 검증 범위를 재분류한다" -m "과거 CLI 백테스트 검증 기록을 Level 0~3으로 재분류해 현재 Wide v1 tick baseline에 바로 적용 가능한 근거와 새로 필요한 검증을 분리했다.

Constraint: 이번 커밋은 문서 분석만 수행
Confidence: medium
Scope-risk: narrow
Tested: rg placeholder scan
Not-tested: code changes"
```

---

### Task 2: GUI/CLI Backtest Protocol Diff

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-22_gui_cli_backtest_protocol_diff.md`

- [ ] **Step 1: Extract GUI protocol evidence**

Run:

```powershell
rg -n "moneytop|GetMoneytopQuery|backengine_start|백테엔진 준비 완료|백테정보|shared_info|back_count|BackTest" ui\ui_backtest_engine.py backtest\backtest.py
```

Expected:

```text
Lines in ui_backtest_engine.py and backtest.py showing moneytop, shared_info, back_count, and BackTest execution are printed.
```

- [ ] **Step 2: Extract CLI protocol evidence**

Run:

```powershell
rg -n "moneytop|GetMoneytopQuery|shared_info|back_count|BackTest|backQ|get|stock_back_db_selected|csv_detected" cli\runner.py
```

Expected:

```text
Lines in cli/runner.py showing parent moneytop read, data loading, BackTest child launch, and result extraction are printed.
```

- [ ] **Step 3: Create protocol diff document**

Create `docs/research/condition_research/pilot_logs/2026-04-22_gui_cli_backtest_protocol_diff.md`:

```markdown
# GUI / CLI Backtest Protocol Diff

## 목적

GUI에서 성공한 백테스트 protocol과 CLI `run_backtest()`의 protocol을 비교해 `moneytop` 의존성 및 parent/child runtime DB 차이를 특정한다.

## GUI protocol

```text
[engine start]
moneytop read
day_list/code_set/day_codes/code_days
engine data loading
shared_info
back_count
백테엔진 준비 완료

[backtest execute]
백테정보 전달
strategy code 전달
Total process 생성
BackTest.Start()
```

## CLI protocol

```text
[run_backtest]
parent moneytop read
engine data loading
shared_info
back_count
BackTest child process 생성
BackTest.Start()
child moneytop read
```

## 차이 요약

| Item | GUI | CLI current | Risk |
| --- | --- | --- | --- |
| moneytop read | engine start and BackTest | parent and child | child DB path mismatch |
| engine state | prepared then reused | prepared and executed in one function | lifecycle mismatch |
| runtime DB context | single GUI context | parent/child process imports | path mismatch |

## 다음 확인 대상

- child stock back DB path
- child backtest DB path
- child moneytop query target
- child moneytop error context
```

- [ ] **Step 4: Run placeholder scan**

Run:

```powershell
rg -n "Risk \\||child stock back DB path$" docs\research\condition_research\pilot_logs\2026-04-22_gui_cli_backtest_protocol_diff.md
```

Expected:

```text
No output, except the final checklist can remain if it is written as concrete next targets.
```

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-22_gui_cli_backtest_protocol_diff.md
git commit -m "GUI CLI 백테스트 프로토콜 차이를 문서화한다" -m "GUI backengine_start와 CLI run_backtest의 moneytop 조회, shared_info 준비, BackTest 실행 흐름을 비교해 child DB path mismatch 가능성을 문서화했다.

Constraint: 코드 변경 없이 protocol diff만 작성
Confidence: medium
Scope-risk: narrow
Tested: rg evidence search and placeholder scan
Not-tested: runtime behavior"
```

---

### Task 3: Child Runtime Path And Moneytop Diagnostics

**Files:**
- Modify: `backtest/backtest.py`
- Modify: `cli/runner.py`
- Modify: `cli/output.py`
- Modify: `tests/unit/test_runner_helpers.py`
- Modify: `tests/unit/test_output.py`

- [ ] **Step 1: Add failing output preservation test**

Append to `tests/unit/test_output.py`:

```python
def test_error_json_preserves_backtest_child_diagnostics():
    result = {
        'status': 'error',
        'message': 'backtest completed without metrics',
        'backtest_child_diagnostics': {
            'stock_back_db_path': 'stock_tick_back.db',
            'moneytop_query_status': 'error',
            'moneytop_error': 'no such table: moneytop',
        },
    }

    parsed = json.loads(format_json(result))

    assert parsed['status'] == 'error'
    assert parsed['backtest_child_diagnostics']['moneytop_query_status'] == 'error'
    assert 'moneytop' in parsed['backtest_child_diagnostics']['moneytop_error']
```

Run:

```powershell
python -m pytest tests/unit/test_output.py::test_error_json_preserves_backtest_child_diagnostics -q
```

Expected:

```text
Test fails because format_json does not yet preserve backtest_child_diagnostics.
```

- [ ] **Step 2: Add source contract tests for diagnostics**

Append to `tests/unit/test_runner_helpers.py`:

```python
def test_runner_collects_backtest_child_diagnostics():
    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'cli', 'runner.py',
    )
    with open(runner_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'backtest_child_diagnostics' in content
    assert 'child_moneytop_error' in content or 'moneytop_error' in content
    assert 'moneytop_query_status' in content


def test_backtest_emits_child_moneytop_diagnostics():
    backtest_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'backtest', 'backtest.py',
    )
    with open(backtest_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'backtest_child_diagnostics' in content
    assert 'moneytop_query_status' in content
    assert 'moneytop_error' in content
```

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py::test_runner_collects_backtest_child_diagnostics tests/unit/test_runner_helpers.py::test_backtest_emits_child_moneytop_diagnostics -q
```

Expected:

```text
Tests fail before implementation.
```

- [ ] **Step 3: Preserve diagnostics in output**

In `cli/output.py`, add `backtest_child_diagnostics` to the list of diagnostic fields preserved for error JSON.

If there is already a diagnostic preservation list from the previous data-loading work, add:

```python
'backtest_child_diagnostics'
```

- [ ] **Step 4: Emit diagnostics from BackTest child**

In `backtest/backtest.py`, around the `moneytop` query in `BackTest.Start()`, catch the query exception and emit a structured diagnostic before re-raising or exiting through the existing error path.

Required diagnostic shape:

```python
diagnostic = {
    'stock_back_db_path': db,
    'moneytop_query_status': 'error',
    'moneytop_error': str(e),
    'startday': startday,
    'endday': endday,
    'starttime': starttime,
    'endtime': endtime,
    'ui_gubun': self.ui_gubun,
}
```

Send it through an existing queue that the parent can observe. Prefer the existing `backQ` or `windowQ` only if the parent already drains it. If there is no safe parent channel, store enough information in the error message and document that Task 4 will use the existing traceback. Do not create a new IPC mechanism without evidence.

Preferred queue message if feasible:

```python
self.backQ.put(('backtest_child_diagnostics', diagnostic))
```

If `self.backQ` is not available in `BackTest`, inspect constructor fields and use the queue actually available.

- [ ] **Step 5: Capture diagnostics in runner**

In `cli/runner.py`, after BackTest process finishes and before metrics extraction, drain available queue messages or inspect the message source used in Step 4. If a `backtest_child_diagnostics` message is found, attach it to `result['backtest_child_diagnostics']`.

Minimum output requirement:

```python
result['backtest_child_diagnostics'] = diagnostic
```

If diagnostics are not available because BackTest child cannot send them safely, add a source-level note in the pilot log and keep this task as a HOLD for implementation. Do not invent unsafe IPC.

- [ ] **Step 6: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_output.py::test_error_json_preserves_backtest_child_diagnostics tests/unit/test_runner_helpers.py::test_runner_collects_backtest_child_diagnostics tests/unit/test_runner_helpers.py::test_backtest_emits_child_moneytop_diagnostics -q
python -m pytest tests/unit/test_output.py tests/unit/test_runner_helpers.py -q
```

Expected:

```text
All tests pass after implementation.
```

- [ ] **Step 7: Compile and diff check**

Run:

```powershell
python -m compileall -q backtest/backtest.py cli/runner.py cli/output.py tests/unit/test_runner_helpers.py tests/unit/test_output.py
git diff --check -- backtest/backtest.py cli/runner.py cli/output.py tests/unit/test_runner_helpers.py tests/unit/test_output.py
```

Expected:

```text
No syntax or whitespace errors.
```

- [ ] **Step 8: Commit Task 3**

Run:

```powershell
git add backtest/backtest.py cli/runner.py cli/output.py tests/unit/test_runner_helpers.py tests/unit/test_output.py
git commit -m "BackTest moneytop 진단 정보를 JSON에 연결한다" -m "BackTest child의 moneytop 조회 실패를 parent CLI 결과 JSON에서 확인할 수 있도록 child diagnostic 전달과 output 보존을 추가했다.

Constraint: 임시 moneytop 테이블 생성은 하지 않음
Confidence: medium
Scope-risk: moderate
Tested: output and runner helper focused tests, compileall, git diff --check
Not-tested: live smoke backtest"
```

---

### Task 4: Smoke Re-run With Diagnostics

**Files:**
- Runtime only:
  - `backtest/temp/wide_v1_cli_moneytop_smoke_4_20260422.json`
  - `backtest/temp/wide_v1_cli_moneytop_smoke_32_20260422.json`
- No tracked changes unless diagnostics show the need to update docs in Task 5.

- [ ] **Step 1: Prepare runtime DB for worktree**

If running from a feature worktree without `_database`, copy small DBs from `wt-dev`:

```powershell
New-Item -ItemType Directory -Force _database | Out-Null
Copy-Item -LiteralPath C:\System_Trading\STOM\STOM_V.wt-dev\_database\strategy.db -Destination _database\strategy.db -Force
Copy-Item -LiteralPath C:\System_Trading\STOM\STOM_V.wt-dev\_database\setting.db -Destination _database\setting.db -Force
Copy-Item -LiteralPath C:\System_Trading\STOM\STOM_V.wt-dev\_database\backtest.db -Destination _database\backtest.db -Force
```

Do not stage these files.

- [ ] **Step 2: Run smoke engines=4**

Run:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250102 `
  --end 20250103 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 4 `
  --timeout 300 `
  --format json `
  -o backtest\temp\wide_v1_cli_moneytop_smoke_4_20260422.json
```

Expected:

```text
Command exits non-zero or zero before external timeout.
JSON file exists.
If moneytop fails, JSON includes backtest_child_diagnostics.
```

- [ ] **Step 3: Run smoke engines=32**

Run:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250102 `
  --end 20250103 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 300 `
  --format json `
  -o backtest\temp\wide_v1_cli_moneytop_smoke_32_20260422.json
```

Expected:

```text
Command exits before external timeout.
JSON file exists.
If moneytop fails, JSON includes backtest_child_diagnostics.
```

- [ ] **Step 4: Summarize smoke JSON**

Run:

```powershell
@'
import json
from pathlib import Path
for path in [
    Path('backtest/temp/wide_v1_cli_moneytop_smoke_4_20260422.json'),
    Path('backtest/temp/wide_v1_cli_moneytop_smoke_32_20260422.json'),
]:
    print('file', path)
    if not path.exists():
        print('exists', False)
        continue
    payload = json.loads(path.read_text(encoding='utf-8'))
    print('exists', True)
    print('status', payload.get('status'))
    print('message', payload.get('message'))
    print('last_checkpoint', payload.get('last_checkpoint'))
    print('backtest_child_diagnostics', payload.get('backtest_child_diagnostics'))
    print()
'@ | python -
```

Expected:

```text
Each JSON file prints status/message/last_checkpoint and diagnostics if present.
```

---

### Task 5: Documentation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-22_cli_moneytop_protocol_smoke.md`
- Create: `docs/update_log/2026-04-22_cli_backtest_moneytop_protocol_parity.md`

- [ ] **Step 1: Generate moneytop smoke pilot log and update log**

Run this script after Task 4 has produced the smoke JSON files.

```powershell
@'
import json
from pathlib import Path

SMOKE_4 = Path('backtest/temp/wide_v1_cli_moneytop_smoke_4_20260422.json')
SMOKE_32 = Path('backtest/temp/wide_v1_cli_moneytop_smoke_32_20260422.json')
pilot_path = Path('docs/research/condition_research/pilot_logs/2026-04-22_cli_moneytop_protocol_smoke.md')
update_path = Path('docs/update_log/2026-04-22_cli_backtest_moneytop_protocol_parity.md')
pilot_path.parent.mkdir(parents=True, exist_ok=True)
update_path.parent.mkdir(parents=True, exist_ok=True)

def load(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))

def summarize(path):
    payload = load(path)
    if payload is None:
        return {
            'json_exists': False,
            'status': 'not_executed_or_no_json',
            'message': 'not_executed_or_no_json',
            'last_checkpoint': 'not_present',
            'backtest_child_diagnostics': 'not_present',
        }
    return {
        'json_exists': True,
        'status': payload.get('status'),
        'message': payload.get('message'),
        'last_checkpoint': payload.get('last_checkpoint'),
        'backtest_child_diagnostics': payload.get('backtest_child_diagnostics', 'not_present'),
    }

smoke4 = summarize(SMOKE_4)
smoke32 = summarize(SMOKE_32)
has_diag = (
    smoke4['backtest_child_diagnostics'] != 'not_present'
    or smoke32['backtest_child_diagnostics'] != 'not_present'
)

if has_diag:
    decision = 'PASS_FOR_DIAGNOSTICS'
    reason = 'At least one smoke run exposed BackTest child moneytop diagnostics in JSON.'
    next_command = '$brainstorming CLI child runtime DB override 전달 설계'
else:
    decision = 'HOLD'
    reason = 'Smoke runs completed but BackTest child diagnostics were not exposed in JSON.'
    next_command = '$brainstorming BackTest moneytop diagnostic 전달 방식 재검토'

pilot_lines = [
    '# CLI Moneytop Protocol Smoke',
    '',
    '## 목적',
    '',
    'BackTest child의 moneytop 조회 실패가 어떤 DB/runtime context에서 발생하는지 구조화된 진단 정보로 확인한다.',
    '',
    '## smoke 4 결과',
    '',
    '~~~text',
    f"json_exists={smoke4['json_exists']}",
    f"status={smoke4['status']}",
    f"message={smoke4['message']}",
    f"last_checkpoint={smoke4['last_checkpoint']}",
    f"backtest_child_diagnostics={smoke4['backtest_child_diagnostics']}",
    '~~~',
    '',
    '## smoke 32 결과',
    '',
    '~~~text',
    f"json_exists={smoke32['json_exists']}",
    f"status={smoke32['status']}",
    f"message={smoke32['message']}",
    f"last_checkpoint={smoke32['last_checkpoint']}",
    f"backtest_child_diagnostics={smoke32['backtest_child_diagnostics']}",
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

update_lines = [
    '# 2026-04-22 CLI BackTest Moneytop Protocol Parity',
    '',
    '## 목적',
    '',
    'GUI와 CLI의 moneytop 사용 protocol 차이를 분석하고, BackTest child moneytop 실패 진단을 JSON으로 노출했다.',
    '',
    '## 변경 사항',
    '',
    '- 과거 CLI 검증 범위 재분류',
    '- GUI/CLI protocol diff 문서화',
    '- BackTest child moneytop diagnostic 추가',
    '- CLI JSON output diagnostic 보존',
    '',
    '## 검증',
    '',
    '~~~text',
    'focused_tests=see implementation command output',
    f"smoke_4={smoke4['status']}",
    f"smoke_32={smoke32['status']}",
    f"diagnostics_exposed={has_diag}",
    '~~~',
    '',
    '## 남은 리스크',
    '',
    '- candidate_count=5는 아직 실행하지 않았다.',
    '- moneytop 해결 후에도 CLI baseline GUI 비교가 필요하다.',
    '- shared memory cleanup 잔여 문제는 별도 추적이 필요하다.',
    '',
    '## 다음 단계',
    '',
    '~~~text',
    next_command,
    '~~~',
    '',
]

pilot_path.write_text('\n'.join(pilot_lines), encoding='utf-8')
update_path.write_text('\n'.join(update_lines), encoding='utf-8')
print(pilot_path)
print(update_path)
print('decision', decision)
print('reason', reason)
'@ | python -
```

Expected:

```text
docs\research\condition_research\pilot_logs\2026-04-22_cli_moneytop_protocol_smoke.md
docs\update_log\2026-04-22_cli_backtest_moneytop_protocol_parity.md
decision PASS_FOR_DIAGNOSTICS
```

If the decision is `HOLD`, keep it. Do not rewrite it manually.

- [ ] **Step 2: Placeholder scan**

Run:

```powershell
rg -n "<" docs\research\condition_research\pilot_logs\2026-04-22_cli_moneytop_protocol_smoke.md docs\update_log\2026-04-22_cli_backtest_moneytop_protocol_parity.md
```

Expected:

```text
No output
```

---

### Task 6: Final Verification And Commit

**Files:**
- Commit all tracked code/test/doc files changed by this plan.
- Do not commit runtime DB, CSV, graph, or temp JSON.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_output.py tests/unit/test_runner_helpers.py -q
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_runner_helpers.py tests/unit/test_output.py tests/unit/test_exit_codes.py -q
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
All focused tests pass.
verify_nonrelease_sync.py passes.
```

- [ ] **Step 2: Run diff check**

Run:

```powershell
git diff --check
```

Expected:

```text
No whitespace errors.
```

- [ ] **Step 3: Check status**

Run:

```powershell
git status --short --untracked-files=all
```

Expected:

```text
Tracked changes include code/test/docs only.
Runtime artifacts are untracked or ignored and not staged.
```

- [ ] **Step 4: Commit**

Run:

```powershell
git add backtest/backtest.py cli/runner.py cli/output.py tests/unit/test_runner_helpers.py tests/unit/test_output.py docs/research/condition_research/pilot_logs/2026-04-22_cli_historical_validation_review.md docs/research/condition_research/pilot_logs/2026-04-22_gui_cli_backtest_protocol_diff.md docs/research/condition_research/pilot_logs/2026-04-22_cli_moneytop_protocol_smoke.md docs/update_log/2026-04-22_cli_backtest_moneytop_protocol_parity.md
git commit -m "CLI moneytop 프로토콜 진단을 추가한다" -m "GUI/CLI 백테스트 protocol 차이를 문서화하고 BackTest child moneytop 조회 실패를 CLI JSON에서 확인할 수 있도록 진단 정보를 추가했다.

Constraint: 임시 moneytop table 생성과 candidate_count=5 실행은 범위 밖
Confidence: medium
Scope-risk: moderate
Tested: focused tests, verify_nonrelease_sync.py, moneytop smoke runs
Not-tested: candidate_count=5, WFO, promote"
```

---

## Decision Routing

Use the smoke result:

```text
If child DB path mismatch is confirmed:
  $brainstorming CLI child runtime DB override 전달 설계

If child DB path is same but moneytop is missing:
  $brainstorming BackTest moneytop source 전달/우회 설계

If moneytop succeeds and metrics are produced:
  $brainstorming Wide v1 CLI baseline GUI 비교 재시도 설계
```

Do not run `candidate_count=5` yet.

## Self-Review Checklist

Spec coverage:

```text
Historical validation review: Task 1
GUI/CLI protocol diff: Task 2
Child runtime/moneytop diagnostics: Task 3
Smoke runs: Task 4
Docs: Task 5
Final verification/commit: Task 6
```

No temporary moneytop table creation, GUI code changes, WFO, promote, or candidate execution are included.
