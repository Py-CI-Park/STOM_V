# CLI Runner Data Loading Timeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CLI backtests return a structured JSON success or failure instead of hanging indefinitely during engine data loading.

**Architecture:** Add a deadline-based timeout around the `backQ.get()` data-loading response loop in `cli.runner.run_backtest()`, record engine response checkpoints, and return a structured `engine_data_loading` error when not all engines respond. Validate the change with existing source-contract test style plus smoke runs, and document smoke/full baseline outcomes without committing runtime artifacts.

**Tech Stack:** Python 3.11, multiprocessing `Queue`, `queue.Empty`, STOM CLI runner, pytest, PowerShell, Markdown update and pilot logs.

---

## Scope

In scope:

- Add data-loading timeout handling to `cli/runner.py`.
- Add engine response checkpoints to `cli/runner.py`.
- Return structured JSON when engine data loading times out.
- Add source-contract tests in `tests/unit/test_runner_helpers.py`.
- Run focused tests.
- Run smoke CLI backtests:
  - 20250102~20250103, engines=32
  - 20250102~20250103, engines=4
  - 20250101~20251231, engines=32 if smoke evidence supports it
- Document smoke results and next decision.

Out of scope:

- Do not run `candidate_count=5`.
- Do not change strategy generation logic.
- Do not run WFO or promote.
- Do not modify GUI code.
- Do not rewrite the full CLI runner protocol.
- Do not commit runtime DB, CSV, graph, or temp JSON artifacts.

## File Structure

Modify:

- `cli/runner.py`
  - Adds `queue.Empty` handling, data-loading deadline, engine response checkpoints, structured timeout result.

- `tests/unit/test_runner_helpers.py`
  - Adds source-contract tests for data-loading timeout/checkpoint behavior.

Create:

- `docs/update_log/2026-04-22_cli_runner_data_loading_timeout.md`
  - Summarizes code change, tests, smoke results, and remaining risks.

- `docs/research/condition_research/pilot_logs/2026-04-22_cli_data_loading_timeout_smoke.md`
  - Records smoke command results and any 2025 full retry result.

Runtime-only generated files:

- `backtest/temp/wide_v1_cli_smoke_32_20260422.json`
- `backtest/temp/wide_v1_cli_smoke_4_20260422.json`
- `backtest/temp/wide_v1_cli_baseline_retry_20260422.json`
- Generated `backtest/csv/*.csv`
- `backtest/graph/`

Do not stage runtime-only files.

## Design Constraints

- Keep existing successful runner path behavior unchanged.
- Use `config.timeout` as the overall data-loading deadline.
- Start data-loading deadline after data-loading messages are sent to engines.
- Do not apply full integrity or heavy checks here; preflight already covers runtime DB usability.
- Cleanup must still run through the existing `finally` block.
- A data-loading timeout is a successful diagnostic outcome if it returns structured JSON.

---

### Task 1: Data Loading Timeout Source Contract Tests

**Files:**
- Modify: `tests/unit/test_runner_helpers.py`

- [ ] **Step 1: Add failing source-contract tests**

Append these tests to `tests/unit/test_runner_helpers.py`:

```python
def test_runner_data_loading_wait_uses_timeout_and_empty_exception():
    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'cli', 'runner.py',
    )
    with open(runner_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'from queue import Empty' in content
    assert 'backQ.get(timeout=' in content
    assert 'except Empty:' in content


def test_runner_records_engine_data_loading_checkpoints():
    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'cli', 'runner.py',
    )
    with open(runner_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "checkpoint.mark('engine_processes_started'" in content
    assert "checkpoint.mark('engine_data_load_requested'" in content
    assert "checkpoint.mark('engine_data_response_wait_started'" in content
    assert "checkpoint.mark('engine_data_response_received'" in content
    assert "checkpoint.mark('engine_data_response_timeout'" in content
    assert "checkpoint.mark('engine_data_load_completed'" in content


def test_runner_returns_structured_engine_data_loading_timeout_result():
    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'cli', 'runner.py',
    )
    with open(runner_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "'engine_data_loading'" in content
    assert "'expected_count'" in content
    assert "'received_count'" in content
    assert "'missing_count'" in content
    assert "'timeout_seconds'" in content
    assert "result['status'] = 'error'" in content
    assert "engine data loading timed out" in content
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py::test_runner_data_loading_wait_uses_timeout_and_empty_exception tests/unit/test_runner_helpers.py::test_runner_records_engine_data_loading_checkpoints tests/unit/test_runner_helpers.py::test_runner_returns_structured_engine_data_loading_timeout_result -q
```

Expected:

```text
At least one assertion fails because runner does not yet use backQ.get(timeout=...) or engine_data_response_timeout.
```

- [ ] **Step 3: Commit failing tests only**

Do not commit failing tests by themselves. Continue to Task 2 before committing.

---

### Task 2: Runner Data Loading Deadline Implementation

**Files:**
- Modify: `cli/runner.py`
- Modify: `tests/unit/test_runner_helpers.py`

- [ ] **Step 1: Add import**

In `cli/runner.py`, add this import near the other standard library imports:

```python
from queue import Empty
```

- [ ] **Step 2: Mark engine process start completion**

After the loop that starts engine processes, add:

```python
        checkpoint.mark('engine_processes_started', detail={
            'engine_count': config.engine_count,
        })
```

This should be after all engine `proc.start()` calls and before stock DB loading starts.

- [ ] **Step 3: Mark data load request**

After `avg_list = _normalize_avg_list(config.avg_time)` and before sending `데이터로딩` messages, add:

```python
        checkpoint.mark('engine_data_load_requested', detail={
            'expected_count': multi,
            'data_list_count': len(data_list),
            'avg_list': avg_list,
        })
```

- [ ] **Step 4: Replace blocking backQ.get loop**

Replace the current block:

```python
        shared_info.clear()
        for i in range(multi):
            shared_info_ = backQ.get()
            shared_info += shared_info_
            windowQ.put((1.4, f'{log_gubun} 데이터 로딩 중... [{i+1}/{multi}]'))
```

with this structure, adapting only string literals if the file uses mojibake identifiers:

```python
        timeout = getattr(config, 'timeout', 3600) or 3600
        data_load_deadline = time.time() + timeout
        received_count = 0
        received_lengths = []
        checkpoint.mark('engine_data_response_wait_started', detail={
            'expected_count': multi,
            'timeout_seconds': timeout,
        })

        shared_info.clear()
        for i in range(multi):
            remaining = data_load_deadline - time.time()
            if remaining <= 0:
                checkpoint.mark('engine_data_response_timeout', detail={
                    'expected_count': multi,
                    'received_count': received_count,
                    'missing_count': multi - received_count,
                    'timeout_seconds': timeout,
                    'received_lengths': received_lengths,
                })
                result['status'] = 'error'
                result['message'] = 'engine data loading timed out'
                result['engine_data_loading'] = {
                    'expected_count': multi,
                    'received_count': received_count,
                    'missing_count': multi - received_count,
                    'timeout_seconds': timeout,
                    'received_lengths': received_lengths,
                }
                result.update(checkpoint.to_result_fields(status='error'))
                return result

            try:
                shared_info_ = backQ.get(timeout=remaining)
            except Empty:
                checkpoint.mark('engine_data_response_timeout', detail={
                    'expected_count': multi,
                    'received_count': received_count,
                    'missing_count': multi - received_count,
                    'timeout_seconds': timeout,
                    'received_lengths': received_lengths,
                })
                result['status'] = 'error'
                result['message'] = 'engine data loading timed out'
                result['engine_data_loading'] = {
                    'expected_count': multi,
                    'received_count': received_count,
                    'missing_count': multi - received_count,
                    'timeout_seconds': timeout,
                    'received_lengths': received_lengths,
                }
                result.update(checkpoint.to_result_fields(status='error'))
                return result

            received_count += 1
            received_lengths.append(len(shared_info_))
            checkpoint.mark('engine_data_response_received', detail={
                'expected_count': multi,
                'received_count': received_count,
                'response_index': i,
                'chunk_count': len(shared_info_),
            })
            shared_info += shared_info_
            windowQ.put((1.4, f'{log_gubun} 데이터 로딩 중... [{i+1}/{multi}]'))
```

Important:

- Keep the existing `shared_info[:] = sorted(...)` line after the loop.
- Keep the existing `shared_data_loaded` checkpoint after sorting.
- Do not change the BackTest process creation path.

- [ ] **Step 5: Add data load completed checkpoint**

After the existing `shared_data_loaded` checkpoint and before the existing `back_count_ready` checkpoint, add:

```python
        checkpoint.mark('engine_data_load_completed', detail={
            'back_count': len(shared_info),
            'expected_count': multi,
            'received_count': received_count,
            'received_lengths': received_lengths,
        })
```

- [ ] **Step 6: Add cleanup checkpoints**

In the `finally` block, add checkpoints around cleanup:

```python
        checkpoint.mark('shared_memory_cleanup_started', detail={
            'shared_info_count': len(shared_info or []),
        })
        _cleanup_shared_memory(shared_info)
        checkpoint.mark('shared_memory_cleanup_completed')
```

Keep the rest of the finally block after this.

- [ ] **Step 7: Run source-contract tests**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py::test_runner_data_loading_wait_uses_timeout_and_empty_exception tests/unit/test_runner_helpers.py::test_runner_records_engine_data_loading_checkpoints tests/unit/test_runner_helpers.py::test_runner_returns_structured_engine_data_loading_timeout_result -q
```

Expected:

```text
3 passed
```

- [ ] **Step 8: Run runner helper tests**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 9: Run related focused tests**

Run:

```powershell
python -m pytest tests/unit/test_backtest_checkpoints.py tests/unit/test_runner_helpers.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 10: Run syntax and diff checks**

Run:

```powershell
python -m compileall -q cli/runner.py tests/unit/test_runner_helpers.py
git diff --check -- cli/runner.py tests/unit/test_runner_helpers.py
```

Expected:

```text
No Python syntax errors.
No whitespace errors.
```

- [ ] **Step 11: Commit Task 1-2 changes**

Run:

```powershell
git add cli/runner.py tests/unit/test_runner_helpers.py
git commit -m "CLI 데이터 로딩 timeout을 추가한다" -m "CLI 백테스트가 BackTest 프로세스 시작 전 데이터 로딩 응답 수집 단계에서 무한 대기하지 않도록 backQ.get timeout과 engine 응답 checkpoint를 추가했다.

timeout 발생 시 engine_data_loading expected/received/missing 정보를 포함한 구조화된 error JSON을 반환하도록 했다.

Constraint: candidate_count=5 실행과 GUI 코드 변경은 범위 밖
Rejected: 외부 timeout에 의존 | JSON/checkpoint 없이 멈추면 자동 연구 루프가 원인을 판단할 수 없음
Confidence: medium
Scope-risk: moderate
Tested: runner helper tests, checkpoint tests, compileall, git diff --check
Not-tested: 실제 smoke 백테스트"
```

---

### Task 3: Focused Verification

**Files:**
- No new files.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py -q
python -m pytest tests/unit/test_backtest_checkpoints.py tests/unit/test_runner_helpers.py -q
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_runner_helpers.py -q
```

Expected:

```text
All focused tests pass.
```

- [ ] **Step 2: Run nonrelease sync guard**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

---

### Task 4: Smoke Backtest Runs

**Files:**
- Runtime only:
  - `backtest/temp/wide_v1_cli_smoke_32_20260422.json`
  - `backtest/temp/wide_v1_cli_smoke_4_20260422.json`
  - `backtest/temp/wide_v1_cli_baseline_retry_20260422.json`
- No tracked file changes in this task.

- [ ] **Step 1: Confirm runtime preflight still passes**

Run:

```powershell
python stom_backtest.py runtime-preflight `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250102 `
  --end 20250103 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 300
```

Expected:

```text
status=ok
failed_checks=[]
```

- [ ] **Step 2: Run smoke with engines=32**

Run:

```powershell
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
  -o backtest\temp\wide_v1_cli_smoke_32_20260422.json
```

Expected:

```text
Command returns before external timeout.
Output JSON exists.
status is success or error.
If error, checkpoint_status and last_checkpoint exist.
If data loading timeout, engine_data_loading exists.
```

- [ ] **Step 3: Run smoke with engines=4**

Run:

```powershell
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
  -o backtest\temp\wide_v1_cli_smoke_4_20260422.json
```

Expected:

```text
Command returns before external timeout.
Output JSON exists.
status is success or error.
If error, checkpoint_status and last_checkpoint exist.
If data loading timeout, engine_data_loading exists.
```

- [ ] **Step 4: Decide whether to run 2025 full retry**

Use this rule:

```text
Run 2025 full retry if:
  smoke commands return structured JSON, even if status=error.

Do not run 2025 full retry if:
  smoke still hangs externally without JSON.
```

- [ ] **Step 5: Run 2025 full retry when allowed**

Run only if Step 4 allows it:

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
  -o backtest\temp\wide_v1_cli_baseline_retry_20260422.json
```

Expected:

```text
Command returns before external timeout.
Output JSON exists.
status is success or error.
```

- [ ] **Step 6: Extract smoke summaries**

Run:

```powershell
@'
import json
from pathlib import Path

files = [
    Path('backtest/temp/wide_v1_cli_smoke_32_20260422.json'),
    Path('backtest/temp/wide_v1_cli_smoke_4_20260422.json'),
    Path('backtest/temp/wide_v1_cli_baseline_retry_20260422.json'),
]
for path in files:
    print('file', path)
    if not path.exists():
        print('exists', False)
        continue
    payload = json.loads(path.read_text(encoding='utf-8'))
    print('exists', True)
    print('status', payload.get('status'))
    print('message', payload.get('message'))
    print('checkpoint_status', payload.get('checkpoint_status'))
    print('last_checkpoint', payload.get('last_checkpoint'))
    print('engine_data_loading', payload.get('engine_data_loading'))
    print('csv_path', payload.get('csv_path'))
    print('elapsed_seconds', payload.get('elapsed_seconds'))
    print()
'@ | python -
```

Expected:

```text
Each generated JSON file prints status/checkpoint summary.
Missing full retry file is acceptable only if Step 4 skipped it.
```

---

### Task 5: Pilot And Update Log Documentation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-22_cli_data_loading_timeout_smoke.md`
- Create: `docs/update_log/2026-04-22_cli_runner_data_loading_timeout.md`

- [ ] **Step 1: Generate smoke pilot log and update log from JSON outputs**

Run this script after Task 4. It reads the smoke JSON files that exist, derives a decision, and writes both Markdown documents without unresolved placeholders.

```powershell
@'
import json
from pathlib import Path

SMOKE_32 = Path('backtest/temp/wide_v1_cli_smoke_32_20260422.json')
SMOKE_4 = Path('backtest/temp/wide_v1_cli_smoke_4_20260422.json')
FULL = Path('backtest/temp/wide_v1_cli_baseline_retry_20260422.json')

pilot_path = Path('docs/research/condition_research/pilot_logs/2026-04-22_cli_data_loading_timeout_smoke.md')
update_path = Path('docs/update_log/2026-04-22_cli_runner_data_loading_timeout.md')
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
            'path': str(path),
            'json_exists': False,
            'status': 'not_executed_or_no_json',
            'message': 'not_executed_or_no_json',
            'checkpoint_status': 'not_present',
            'last_checkpoint': 'not_present',
            'engine_data_loading': 'not_present',
            'csv_path': 'not_present',
            'elapsed_seconds': 'not_present',
        }
    return {
        'path': str(path),
        'json_exists': True,
        'status': payload.get('status'),
        'message': payload.get('message'),
        'checkpoint_status': payload.get('checkpoint_status'),
        'last_checkpoint': payload.get('last_checkpoint'),
        'engine_data_loading': payload.get('engine_data_loading', 'not_present'),
        'csv_path': payload.get('csv_path'),
        'elapsed_seconds': payload.get('elapsed_seconds'),
    }

smoke32 = summarize(SMOKE_32)
smoke4 = summarize(SMOKE_4)
full = summarize(FULL)

def structured(summary):
    return bool(summary['json_exists']) and summary['status'] in ('success', 'error')

if structured(smoke32) and structured(smoke4):
    if full['json_exists']:
        decision = 'PASS'
        reason = 'Smoke runs returned structured JSON and the full retry also produced JSON.'
        next_command = '$brainstorming Wide v1 CLI baseline GUI 비교 재시도 설계'
    else:
        decision = 'HOLD'
        reason = 'Smoke runs returned structured JSON, but full retry was skipped or did not produce JSON.'
        next_command = '$brainstorming CLI engine data response 누락 원인 분석 설계'
elif structured(smoke32) or structured(smoke4):
    decision = 'HOLD'
    reason = 'At least one smoke run returned structured JSON, but not all smoke paths are structured.'
    next_command = '$brainstorming CLI engine data response 누락 원인 분석 설계'
else:
    decision = 'FAIL'
    reason = 'Smoke runs did not produce structured JSON.'
    next_command = '$brainstorming CLI runner process lifecycle hang 분석 설계'

def block(summary):
    return '\n'.join([
        f"json_exists={summary['json_exists']}",
        f"status={summary['status']}",
        f"message={summary['message']}",
        f"checkpoint_status={summary['checkpoint_status']}",
        f"last_checkpoint={summary['last_checkpoint']}",
        f"engine_data_loading={summary['engine_data_loading']}",
        f"csv_path={summary['csv_path']}",
        f"elapsed_seconds={summary['elapsed_seconds']}",
    ])

pilot_lines = [
    '# CLI Data Loading Timeout Smoke Pilot',
    '',
    '## 목적',
    '',
    'CLI baseline이 data loading 단계에서 외부 timeout까지 멈추는 문제를 구조화된 success/error JSON으로 전환할 수 있는지 확인했다.',
    '',
    '## 이전 실패 증거',
    '',
    '~~~text',
    'CLI baseline command=FAIL',
    'external_timeout_ms=964079',
    'result_json_created=False',
    'new_csv_created=False',
    'shared_memory_remaining=backdata_0..31',
    '~~~',
    '',
    '## smoke 32엔진 결과',
    '',
    '~~~text',
    'command=20250102~20250103 tick avg_time=30 engines=32 timeout=300',
    block(smoke32),
    '~~~',
    '',
    '## smoke 4엔진 결과',
    '',
    '~~~text',
    'command=20250102~20250103 tick avg_time=30 engines=4 timeout=300',
    block(smoke4),
    '~~~',
    '',
    '## 2025 전체 재시도 결과',
    '',
    '~~~text',
    'command=20250101~20251231 tick avg_time=30 engines=32 timeout=900',
    block(full),
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
    '# 2026-04-22 CLI Runner Data Loading Timeout',
    '',
    '## 목적',
    '',
    'CLI baseline 백테스트가 data loading 단계에서 JSON 없이 멈추는 문제를 막기 위해, data loading 응답 수집 구간에 timeout과 checkpoint를 추가했다.',
    '',
    '## 변경 사항',
    '',
    '- `backQ.get(timeout=remaining)` 적용',
    '- `queue.Empty` 처리',
    '- `engine_data_response_*` checkpoint 추가',
    '- `engine_data_loading` structured error field 추가',
    '- shared memory cleanup checkpoint 추가',
    '',
    '## 검증',
    '',
    '~~~text',
    'runner_helper_tests=see command output in implementation session',
    'focused_tests=see command output in implementation session',
    'verify_nonrelease_sync=see command output in implementation session',
    f"smoke_32={smoke32['status']}",
    f"smoke_4={smoke4['status']}",
    f"full_retry={full['status']}",
    '~~~',
    '',
    '## 판정',
    '',
    '~~~text',
    f'decision={decision}',
    f'reason={reason}',
    '~~~',
    '',
    '## 남은 리스크',
    '',
    '- candidate_count=5는 아직 실행하지 않았다.',
    '- smoke가 structured error라면 GUI/CLI 결과 비교가 아니라 engine 응답 누락 원인 분석이 필요하다.',
    '- full retry가 success면 별도 baseline gate 재비교가 필요하다.',
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
docs\research\condition_research\pilot_logs\2026-04-22_cli_data_loading_timeout_smoke.md
docs\update_log\2026-04-22_cli_runner_data_loading_timeout.md
decision PASS
```

If the printed decision is `HOLD` or `FAIL`, keep that decision. Do not manually rewrite it to PASS.

- [ ] **Step 2: Remove unresolved markers**

Run:

```powershell
rg -n "<" docs\research\condition_research\pilot_logs\2026-04-22_cli_data_loading_timeout_smoke.md docs\update_log\2026-04-22_cli_runner_data_loading_timeout.md
```

Expected:

```text
No output
```

---

### Task 6: Final Verification And Commit

**Files:**
- Commit:
  - `cli/runner.py`
  - `tests/unit/test_runner_helpers.py`
  - `docs/update_log/2026-04-22_cli_runner_data_loading_timeout.md`
  - `docs/research/condition_research/pilot_logs/2026-04-22_cli_data_loading_timeout_smoke.md`
- Do not commit:
  - `backtest/temp/*.json`
  - `backtest/csv/*.csv`
  - `backtest/graph/`
  - `_database/*.db`

- [ ] **Step 1: Run final focused tests**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py -q
python -m pytest tests/unit/test_backtest_checkpoints.py tests/unit/test_runner_helpers.py -q
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_runner_helpers.py -q
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
git diff --check -- cli/runner.py tests/unit/test_runner_helpers.py docs/update_log/2026-04-22_cli_runner_data_loading_timeout.md docs/research/condition_research/pilot_logs/2026-04-22_cli_data_loading_timeout_smoke.md
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

Expected tracked/untracked shape:

```text
 M cli/runner.py
 M tests/unit/test_runner_helpers.py
?? docs/research/condition_research/pilot_logs/2026-04-22_cli_data_loading_timeout_smoke.md
?? docs/update_log/2026-04-22_cli_runner_data_loading_timeout.md
?? backtest/graph/...
```

If `backtest/temp/*.json`, `_database/*.db`, or generated CSV files appear as staged changes, stop and unstage them.

- [ ] **Step 4: Commit**

Run:

```powershell
git add cli/runner.py tests/unit/test_runner_helpers.py docs/update_log/2026-04-22_cli_runner_data_loading_timeout.md docs/research/condition_research/pilot_logs/2026-04-22_cli_data_loading_timeout_smoke.md
git commit -m "CLI 데이터 로딩 timeout과 smoke 결과를 기록한다" -m "CLI 백테스트가 data loading 단계에서 무한 대기하지 않도록 engine 응답 수집 timeout과 checkpoint를 추가하고 smoke 실행 결과를 문서화했다.

Constraint: candidate_count=5 실행은 이번 범위가 아님
Confidence: medium
Scope-risk: moderate
Tested: runner helper tests, focused unit tests, verify_nonrelease_sync.py, smoke CLI backtests
Not-tested: WFO, promote, candidate_count=5"
```

---

## Decision Routing

Use the documented smoke decision:

```text
If smoke/full retry succeeds:
  $brainstorming Wide v1 CLI baseline GUI 비교 재시도 설계

If structured data-loading timeout remains:
  $brainstorming CLI engine data response 누락 원인 분석 설계

If external timeout still occurs without JSON:
  $brainstorming CLI runner process lifecycle hang 분석 설계
```

Do not run `candidate_count=5` until the CLI baseline gate is restored and GUI comparison is possible.

## Self-Review Checklist

Spec coverage:

```text
backQ.get timeout: Task 2
engine response checkpoints: Task 2
structured engine_data_loading error: Task 2
cleanup checkpoints: Task 2
source contract tests: Task 1
smoke 32/4/full retry: Task 4
pilot/update logs: Task 5
runtime artifact exclusion: Task 6
```

No GUI changes, candidate execution, WFO, or strategy-generation changes are included.
