# CLI Child Runtime DB Override Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make BackTest child processes inherit the same runtime DB paths as the CLI parent so they stop reading `./_database/stock_tick_back.db` when the parent is using `STOM_CLI_DATABASE_DIR`.

**Architecture:** Add environment-variable based DB path resolution to the legacy `utility.setting_base` module while preserving the default GUI path when no env vars are set. Then ensure `cli.runner` sets the relevant `STOM_CLI_DB_*` env vars before Windows child processes import legacy modules. Validate with unit tests and smoke runs, without creating temporary `moneytop` tables.

**Tech Stack:** Python 3.11, Windows process spawn environment inheritance, SQLite path constants, pytest, STOM CLI runner.

---

## Scope

In scope:

- Add env-aware DB path resolver to `utility/setting_base.py`.
- Preserve current default GUI behavior when no env vars are set.
- Ensure CLI parent exports DB path env vars before spawning child processes.
- Verify BackTest child diagnostic `stock_back_db_path` changes from `./_database/stock_tick_back.db` to the intended runtime DB path.
- Run smoke 4/32 and document result.

Out of scope:

- Do not create temporary `moneytop` tables.
- Do not modify GUI code.
- Do not run `candidate_count=5`.
- Do not run WFO or promote.
- Do not implement persistent CLI engine session.
- Do not commit runtime DB/CSV/graph/temp artifacts.

## File Structure

Modify:

- `utility/setting_base.py`
  - Adds env-aware DB path resolver and applies it to DB constants.

- `cli/runner.py`
  - Ensures `STOM_CLI_DB_*` env vars are populated from `cli.paths` before child processes spawn.

- `tests/unit/test_setting_base_cli_overrides.py`
  - New tests for default path and env override behavior.

- `tests/unit/test_runner_helpers.py`
  - Tests that runner propagates CLI DB env vars.

Create:

- `docs/research/condition_research/pilot_logs/2026-04-22_cli_child_runtime_db_override_smoke.md`
  - Smoke result showing child DB path after override.

- `docs/update_log/2026-04-22_cli_child_runtime_db_override.md`
  - Summary of change, tests, smoke result, next step.

Do not commit:

- `_database/*.db`
- `backtest/temp/*.json`
- generated `backtest/csv/*.csv`
- `backtest/graph/`

---

### Task 1: setting_base Env Override Tests

**Files:**
- Create: `tests/unit/test_setting_base_cli_overrides.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_setting_base_cli_overrides.py`:

```python
import importlib
import sys


def _reload_setting_base(monkeypatch, env=None):
    keys = [
        'STOM_CLI_DATABASE_DIR',
        'STOM_CLI_DB_SETTING',
        'STOM_CLI_DB_STRATEGY',
        'STOM_CLI_DB_BACKTEST',
        'STOM_CLI_DB_STOCK_BACK_TICK',
        'STOM_CLI_DB_STOCK_BACK_MIN',
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    for key, value in (env or {}).items():
        monkeypatch.setenv(key, value)
    sys.modules.pop('utility.setting_base', None)
    import utility.setting_base as setting_base
    return importlib.reload(setting_base)


def test_setting_base_uses_default_database_path_without_cli_env(monkeypatch):
    setting_base = _reload_setting_base(monkeypatch)

    assert setting_base.DB_PATH == './_database'
    assert setting_base.DB_SETTING == './_database/setting.db'
    assert setting_base.DB_BACKTEST == './_database/backtest.db'
    assert setting_base.DB_STRATEGY == './_database/strategy.db'
    assert setting_base.DB_STOCK_TICK_BACK == './_database/stock_tick_back.db'
    assert setting_base.DB_STOCK_BACK_TICK == setting_base.DB_STOCK_TICK_BACK


def test_setting_base_uses_stom_cli_database_dir(monkeypatch):
    setting_base = _reload_setting_base(
        monkeypatch,
        {'STOM_CLI_DATABASE_DIR': r'C:\System_Trading\STOM\STOM_V.wt-dev\_database'},
    )

    root = r'C:\System_Trading\STOM\STOM_V.wt-dev\_database'
    assert setting_base.DB_PATH == root
    assert setting_base.DB_SETTING == root + '/setting.db'
    assert setting_base.DB_BACKTEST == root + '/backtest.db'
    assert setting_base.DB_STRATEGY == root + '/strategy.db'
    assert setting_base.DB_STOCK_TICK_BACK == root + '/stock_tick_back.db'
    assert setting_base.DB_STOCK_BACK_TICK == setting_base.DB_STOCK_TICK_BACK


def test_setting_base_individual_db_override_wins(monkeypatch):
    setting_base = _reload_setting_base(
        monkeypatch,
        {
            'STOM_CLI_DATABASE_DIR': r'C:\runtime\_database',
            'STOM_CLI_DB_STOCK_BACK_TICK': r'D:\tick\stock_tick_back.db',
            'STOM_CLI_DB_BACKTEST': r'D:\result\backtest.db',
        },
    )

    assert setting_base.DB_PATH == r'C:\runtime\_database'
    assert setting_base.DB_STOCK_TICK_BACK == r'D:\tick\stock_tick_back.db'
    assert setting_base.DB_STOCK_BACK_TICK == r'D:\tick\stock_tick_back.db'
    assert setting_base.DB_BACKTEST == r'D:\result\backtest.db'
    assert setting_base.DB_SETTING == r'C:\runtime\_database/setting.db'
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_setting_base_cli_overrides.py -q
```

Expected:

```text
At least the env override tests fail because utility.setting_base ignores STOM_CLI_DATABASE_DIR.
```

---

### Task 2: setting_base Env-Aware Resolver

**Files:**
- Modify: `utility/setting_base.py`
- Test: `tests/unit/test_setting_base_cli_overrides.py`

- [ ] **Step 1: Add import and resolver**

At the top of `utility/setting_base.py`, add:

```python
import os


def _resolve_db(filename, env_name):
    override = os.environ.get(env_name)
    if override:
        return override
    return f'{DB_PATH}/{filename}'
```

- [ ] **Step 2: Replace DB_PATH and DB constants**

Replace the DB path section with:

```python
DB_PATH             = os.environ.get('STOM_CLI_DATABASE_DIR', './_database')
DB_SETTING          = _resolve_db('setting.db', 'STOM_CLI_DB_SETTING')
DB_BACKTEST         = _resolve_db('backtest.db', 'STOM_CLI_DB_BACKTEST')
DB_TRADELIST        = _resolve_db('tradelist.db', 'STOM_CLI_DB_TRADELIST')
DB_STRATEGY         = _resolve_db('strategy.db', 'STOM_CLI_DB_STRATEGY')
DB_OPTUNA           = f"sqlite:///{_resolve_db('optuna.db', 'STOM_CLI_DB_OPTUNA')}"
DB_CODE_INFO        = _resolve_db('code_info.db', 'STOM_CLI_DB_CODE_INFO')
DB_STOCK_TICK       = _resolve_db('stock_tick.db', 'STOM_CLI_DB_STOCK_TICK')
DB_STOCK_MIN        = _resolve_db('stock_min.db', 'STOM_CLI_DB_STOCK_MIN')
DB_STOCK_TICK_BACK  = _resolve_db('stock_tick_back.db', 'STOM_CLI_DB_STOCK_BACK_TICK')
DB_STOCK_MIN_BACK   = _resolve_db('stock_min_back.db', 'STOM_CLI_DB_STOCK_BACK_MIN')
DB_COIN_TICK        = _resolve_db('coin_tick.db', 'STOM_CLI_DB_COIN_TICK')
DB_COIN_MIN         = _resolve_db('coin_min.db', 'STOM_CLI_DB_COIN_MIN')
DB_COIN_TICK_BACK   = _resolve_db('coin_tick_back.db', 'STOM_CLI_DB_COIN_BACK_TICK')
DB_COIN_MIN_BACK    = _resolve_db('coin_min_back.db', 'STOM_CLI_DB_COIN_BACK_MIN')
DB_FUTURE_TICK      = _resolve_db('future_tick.db', 'STOM_CLI_DB_FUTURE_TICK')
DB_FUTURE_MIN       = _resolve_db('future_min.db', 'STOM_CLI_DB_FUTURE_MIN')
DB_FUTURE_TICK_BACK = _resolve_db('future_tick_back.db', 'STOM_CLI_DB_FUTURE_BACK_TICK')
DB_FUTURE_MIN_BACK  = _resolve_db('future_min_back.db', 'STOM_CLI_DB_FUTURE_BACK_MIN')
DB_STOCK_USA_TICK   = _resolve_db('stock_usa_tick.db', 'STOM_CLI_DB_STOCK_USA_TICK')
DB_STOCK_USA_MIN    = _resolve_db('stock_usa_min.db', 'STOM_CLI_DB_STOCK_USA_MIN')
DB_STOCK_USA_TICK_BACK = _resolve_db('stock_usa_tick_back.db', 'STOM_CLI_DB_STOCK_USA_BACK_TICK')
DB_STOCK_USA_MIN_BACK  = _resolve_db('stock_usa_min_back.db', 'STOM_CLI_DB_STOCK_USA_BACK_MIN')
```

Keep the compatibility alias block below it:

```python
DB_STOCK_BACK_TICK = DB_STOCK_TICK_BACK
DB_STOCK_BACK_MIN = DB_STOCK_MIN_BACK
...
```

- [ ] **Step 3: Run setting_base tests**

Run:

```powershell
python -m pytest tests/unit/test_setting_base_cli_overrides.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 4: Run related sync tests**

Run:

```powershell
python -m pytest tests/unit/test_verify_nonrelease_sync.py tests/unit/test_setting_schema_contract.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 5: Commit Task 1-2**

Run:

```powershell
git add utility/setting_base.py tests/unit/test_setting_base_cli_overrides.py
git commit -m "setting_base가 CLI DB override를 읽도록 한다" -m "BackTest child가 legacy utility.setting_base를 import할 때도 STOM_CLI_DATABASE_DIR와 개별 STOM_CLI_DB_* 값을 읽도록 DB 경로 resolver를 추가했다.

Constraint: 환경변수가 없으면 기존 ./_database 경로를 유지해야 함
Rejected: worktree DB 복사/링크 | runtime artifact 오염과 자동화 반복성 문제가 큼
Confidence: high
Scope-risk: moderate
Tested: test_setting_base_cli_overrides.py, setting schema/nonrelease sync related tests
Not-tested: live BackTest child smoke"
```

---

### Task 3: Runner Env Propagation

**Files:**
- Modify: `cli/runner.py`
- Modify: `tests/unit/test_runner_helpers.py`

- [ ] **Step 1: Add failing source/behavior test**

Append to `tests/unit/test_runner_helpers.py`:

```python
def test_runner_exports_cli_db_paths_for_legacy_children():
    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'cli', 'runner.py',
    )
    with open(runner_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'STOM_CLI_DB_STOCK_BACK_TICK' in content
    assert 'STOM_CLI_DB_BACKTEST' in content
    assert 'STOM_CLI_DB_SETTING' in content
    assert 'STOM_CLI_DB_STRATEGY' in content
    assert '_ensure_cli_db_env' in content
```

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py::test_runner_exports_cli_db_paths_for_legacy_children -q
```

Expected:

```text
Test fails because runner does not yet ensure DB env vars.
```

- [ ] **Step 2: Implement `_ensure_cli_db_env`**

In `cli/runner.py`, update the `cli.paths` import:

```python
from cli.paths import (
    DB_SETTING,
    DB_STRATEGY,
    DB_STOCK_BACK_TICK,
    DB_STOCK_BACK_MIN,
    DB_BACKTEST,
)
```

Add helper near `_sync_dict_set`:

```python
def _ensure_cli_db_env():
    defaults = {
        'STOM_CLI_DB_SETTING': DB_SETTING,
        'STOM_CLI_DB_STRATEGY': DB_STRATEGY,
        'STOM_CLI_DB_BACKTEST': DB_BACKTEST,
        'STOM_CLI_DB_STOCK_BACK_TICK': DB_STOCK_BACK_TICK,
        'STOM_CLI_DB_STOCK_BACK_MIN': DB_STOCK_BACK_MIN,
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, str(value))
```

Call it in `run_backtest()` before `_sync_dict_set(config)`:

```python
    _ensure_cli_db_env()
    dict_set = _sync_dict_set(config)
```

This ensures Windows spawn children inherit the same CLI DB paths.

- [ ] **Step 3: Run runner helper tests**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 4: Commit Task 3**

Run:

```powershell
git add cli/runner.py tests/unit/test_runner_helpers.py
git commit -m "runner가 child DB override 환경을 보장한다" -m "Windows spawn child가 legacy setting_base를 import하기 전에 parent CLI DB 경로가 STOM_CLI_DB_* 환경변수로 상속되도록 보장했다.

Constraint: 사용자 지정 환경변수는 setdefault로 덮어쓰지 않음
Confidence: high
Scope-risk: moderate
Tested: runner helper tests
Not-tested: live child smoke"
```

---

### Task 4: Smoke Validation

**Files:**
- Runtime only:
  - `backtest/temp/wide_v1_cli_child_db_override_smoke_4_20260422.json`
  - `backtest/temp/wide_v1_cli_child_db_override_smoke_32_20260422.json`
- No tracked changes in this task.

- [ ] **Step 1: Run smoke 4**

Run from the feature worktree:

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
  -o backtest\temp\wide_v1_cli_child_db_override_smoke_4_20260422.json
```

Expected:

```text
Command exits before external timeout.
If moneytop still fails, backtest_child_diagnostics.stock_back_db_path should be C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db.
If moneytop succeeds, command may progress to metrics/CSV or another structured error.
```

- [ ] **Step 2: Run smoke 32**

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
  -o backtest\temp\wide_v1_cli_child_db_override_smoke_32_20260422.json
```

Expected:

```text
Command exits before external timeout.
Diagnostics show child DB path is no longer ./_database/stock_tick_back.db.
```

- [ ] **Step 3: Summarize smoke JSON**

Run:

```powershell
@'
import json
from pathlib import Path
for path in [
    Path('backtest/temp/wide_v1_cli_child_db_override_smoke_4_20260422.json'),
    Path('backtest/temp/wide_v1_cli_child_db_override_smoke_32_20260422.json'),
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
    print('csv_path', payload.get('csv_path'))
    print()
'@ | python -
```

Expected:

```text
Each JSON summary is printed.
```

---

### Task 5: Documentation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-22_cli_child_runtime_db_override_smoke.md`
- Create: `docs/update_log/2026-04-22_cli_child_runtime_db_override.md`

- [ ] **Step 1: Create pilot log**

Create `docs/research/condition_research/pilot_logs/2026-04-22_cli_child_runtime_db_override_smoke.md` with concrete smoke results:

```markdown
# CLI Child Runtime DB Override Smoke

## 목적

BackTest child가 parent와 같은 runtime DB 경로를 보도록 `utility.setting_base`와 runner env propagation을 보강한 결과를 확인한다.

## smoke 4 결과

```text
status=value_from_smoke_json
message=value_from_smoke_json
child_stock_back_db_path=value_from_backtest_child_diagnostics_or_not_present
moneytop_query_status=value_from_backtest_child_diagnostics_or_not_present
csv_path=value_from_smoke_json_or_None
```

## smoke 32 결과

```text
status=value_from_smoke_json
message=value_from_smoke_json
child_stock_back_db_path=value_from_backtest_child_diagnostics_or_not_present
moneytop_query_status=value_from_backtest_child_diagnostics_or_not_present
csv_path=value_from_smoke_json_or_None
```

## 판정

```text
decision=value_from_PASS_HOLD_FAIL_decision_logic
reason=value_from_smoke_result_interpretation
```

## 다음 단계

```text
next_brainstorming_command_from_decision_routing
```
```

- [ ] **Step 2: Create update log**

Create `docs/update_log/2026-04-22_cli_child_runtime_db_override.md`:

```markdown
# 2026-04-22 CLI Child Runtime DB Override

## 목적

BackTest child process가 parent CLI와 같은 runtime DB 경로를 보도록 legacy `utility.setting_base`에 CLI DB override를 적용했다.

## 변경 사항

- `utility.setting_base` env-aware DB resolver 추가
- `cli.runner` child DB env propagation 추가
- setting_base override tests 추가
- smoke 4/32 실행

## 검증

```text
setting_base_tests=value_from_test_command_output
runner_helper_tests=value_from_test_command_output
focused_tests=value_from_test_command_output
smoke_4=value_from_smoke_json
smoke_32=value_from_smoke_json
```

## 다음 단계

```text
next_brainstorming_command_from_decision_routing
```
```

- [ ] **Step 3: Placeholder scan**

Run:

```powershell
rg -n "<" docs\research\condition_research\pilot_logs\2026-04-22_cli_child_runtime_db_override_smoke.md docs\update_log\2026-04-22_cli_child_runtime_db_override.md
```

Expected:

```text
No output
```

---

### Task 6: Final Verification And Commit

**Files:**
- Commit:
  - `utility/setting_base.py`
  - `cli/runner.py`
  - `tests/unit/test_setting_base_cli_overrides.py`
  - `tests/unit/test_runner_helpers.py`
  - `docs/research/condition_research/pilot_logs/2026-04-22_cli_child_runtime_db_override_smoke.md`
  - `docs/update_log/2026-04-22_cli_child_runtime_db_override.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_setting_base_cli_overrides.py tests/unit/test_runner_helpers.py -q
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_runner_helpers.py tests/unit/test_output.py tests/unit/test_exit_codes.py tests/unit/test_setting_base_cli_overrides.py -q
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
All tests pass.
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

- [ ] **Step 3: Confirm runtime artifacts are not staged**

Run:

```powershell
git status --short --untracked-files=all
```

Expected:

```text
Only code/test/doc changes are staged or unstaged.
Runtime DB/CSV/graph/temp JSON are not staged.
```

- [ ] **Step 4: Commit**

Run:

```powershell
git add utility/setting_base.py cli/runner.py tests/unit/test_setting_base_cli_overrides.py tests/unit/test_runner_helpers.py docs/research/condition_research/pilot_logs/2026-04-22_cli_child_runtime_db_override_smoke.md docs/update_log/2026-04-22_cli_child_runtime_db_override.md
git commit -m "CLI child runtime DB override를 전달한다" -m "BackTest child가 legacy utility.setting_base를 import할 때도 parent CLI와 같은 runtime DB 경로를 보도록 환경변수 기반 resolver와 runner env propagation을 추가했다.

Constraint: 환경변수가 없을 때 GUI 기본 ./_database 경로는 유지
Confidence: medium
Scope-risk: moderate
Tested: setting_base override tests, runner helper tests, focused tests, verify_nonrelease_sync.py, smoke 4/32
Not-tested: candidate_count=5, WFO, promote"
```

---

## Decision Routing

Use the smoke result:

```text
If child path changes and moneytop succeeds:
  $brainstorming Wide v1 CLI baseline GUI 비교 재시도 설계

If child path changes but another BackTest/Total error appears:
  $brainstorming CLI BackTest 다음 실패 단계 분석 설계

If child still sees ./_database:
  $brainstorming CLI child env propagation 실패 분석 설계
```

Do not run `candidate_count=5` until CLI baseline can produce metrics/CSV and GUI parity can be compared.

## Self-Review Checklist

Spec coverage:

```text
setting_base env override: Task 1-2
runner env propagation: Task 3
smoke validation: Task 4
docs: Task 5
final verification: Task 6
candidate_count=5 blocked: Decision Routing
```

No temporary moneytop table creation, GUI code changes, WFO, promote, or candidate execution are included.
