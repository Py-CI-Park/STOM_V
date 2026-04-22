# CLI BackTest Process Timeout Result Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CLI BackTest process timeouts explain where the child process stopped after `backtest_process_started`, without changing GUI backtest behavior.

**Architecture:** Use `windowQ` as the safe observation channel because it is already a status/log queue and is not part of the engine/Total result protocol. Add CLI-only diagnostic messages gated by an environment variable, let `QueueDrainer` capture them into memory, and attach a summarized diagnostic payload to timeout JSON.

**Tech Stack:** Python 3.11, multiprocessing Queue/Process, STOM BackTest/Total/BackSubTotal protocol, pytest, PowerShell, Markdown pilot logs.

---

## Scope

In scope:

- Add CLI-only protocol diagnostic capture to `cli/queue_drain.py`.
- Add BackTest/Total checkpoint emission in `backtest/backtest.py`.
- Enable diagnostic emission from `cli/runner.py` only during CLI backtests.
- Attach `backtest_process_diagnostics` to timeout/error JSON.
- Run smoke 4/32 and document the result.

Out of scope:

- Do not consume `totalQ`, `beq`, or `bstq` from the CLI parent while the backtest is running.
- Do not implement the final protocol fix yet unless the cause is trivially exposed by tests.
- Do not implement persistent CLI engine sessions.
- Do not run `candidate_count=5`.
- Do not run WFO/promote.
- Do not commit runtime DB/CSV/graph/temp JSON artifacts.

## File Structure

Modify:

- `cli/queue_drain.py`
  - Captures `[CLI_DIAG] {...}` messages into `QueueDrainer.protocol_diagnostics`.

- `tests/unit/test_queue_drain.py`
  - Adds tests for protocol diagnostic capture and malformed diagnostic handling.

- `backtest/backtest.py`
  - Adds `_emit_cli_protocol_checkpoint()`.
  - Emits CLI-only checkpoints from `BackTest.Start()`, `Total.MainLoop()`, and `Total.Report()`.

- `tests/unit/test_backtest_process_protocol_diagnostics.py`
  - Adds helper behavior tests and source-contract tests for key checkpoint names.

- `cli/runner.py`
  - Enables `STOM_CLI_BACKTEST_PROTOCOL_DIAG=1` during `run_backtest()`.
  - Summarizes `QueueDrainer.protocol_diagnostics` into timeout/error JSON.

- `tests/unit/test_runner_helpers.py`
  - Adds tests for diagnostic summary and timeout JSON source contract.

Create:

- `docs/research/condition_research/pilot_logs/2026-04-22_cli_backtest_process_timeout_protocol_smoke.md`
- `docs/update_log/2026-04-22_cli_backtest_process_timeout_protocol.md`

---

### Task 1: QueueDrainer Protocol Diagnostic Tests

**Files:**
- Modify: `tests/unit/test_queue_drain.py`

- [ ] **Step 1: Add failing diagnostic capture tests**

Append this test class to `tests/unit/test_queue_drain.py`:

```python
class TestProtocolDiagnostics:
    """CLI protocol diagnostics are captured without changing normal log behavior."""

    def test_cli_diag_message_is_recorded(self):
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put((
            'ui_001',
            '[CLI_DIAG] {"source":"BackTest","checkpoint":"backtest_child_started","detail":{"pid":123}}',
        ))
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message.startswith('[CLI_DIAG]')
        assert drainer.protocol_diagnostics == [
            {
                'source': 'BackTest',
                'checkpoint': 'backtest_child_started',
                'detail': {'pid': 123},
            }
        ]

    def test_malformed_cli_diag_message_is_ignored(self):
        q = Queue()
        drainer = _start_drainer(q, verbose=False)

        q.put(('ui_001', '[CLI_DIAG] not-json'))
        time.sleep(0.3)
        _stop_and_join(drainer)

        assert drainer.last_message == '[CLI_DIAG] not-json'
        assert drainer.protocol_diagnostics == []
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_queue_drain.py::TestProtocolDiagnostics -q
```

Expected:

```text
FAIL because QueueDrainer has no protocol_diagnostics attribute yet.
```

---

### Task 2: QueueDrainer Protocol Diagnostic Capture

**Files:**
- Modify: `cli/queue_drain.py`
- Test: `tests/unit/test_queue_drain.py`

- [ ] **Step 1: Implement capture in QueueDrainer**

Update `cli/queue_drain.py`:

```python
import json
import sys
from threading import Thread, Event


CLI_DIAG_PREFIX = '[CLI_DIAG] '
```

In `QueueDrainer.__init__`, add:

```python
        self.protocol_diagnostics = []
```

Add this method to `QueueDrainer`:

```python
    def _record_protocol_diagnostic(self, message):
        if not isinstance(message, str) or not message.startswith(CLI_DIAG_PREFIX):
            return
        payload = message[len(CLI_DIAG_PREFIX):]
        try:
            diagnostic = json.loads(payload)
        except json.JSONDecodeError:
            return
        if isinstance(diagnostic, dict):
            self.protocol_diagnostics.append(diagnostic)
```

In both tuple and string message branches, call it after `self.last_message = message` or `self.last_message = data`:

```python
                self._record_protocol_diagnostic(message)
```

```python
                self._record_protocol_diagnostic(data)
```

- [ ] **Step 2: Run QueueDrainer tests**

Run:

```powershell
python -m pytest tests/unit/test_queue_drain.py -q
```

Expected:

```text
All queue drainer tests pass.
```

- [ ] **Step 3: Commit Task 1-2**

Run:

```powershell
git add cli/queue_drain.py tests/unit/test_queue_drain.py
git commit -m "QueueDrainer가 CLI protocol 진단을 보존한다" -m "CLI BackTest timeout 원인 분석을 위해 windowQ의 [CLI_DIAG] JSON 메시지를 stderr 출력과 분리해 메모리 diagnostics로 보존한다.

Constraint: windowQ는 상태 메시지 채널이며 engine/Total 결과 protocol queue를 소비하지 않아야 함
Rejected: totalQ/beq/bstq parent drain | 실행 중 protocol 메시지를 빼앗아 백테스트를 깨뜨릴 수 있음
Confidence: high
Scope-risk: narrow
Tested: tests/unit/test_queue_drain.py
Not-tested: live BackTest smoke"
```

---

### Task 3: BackTest/Total Checkpoint Emission

**Files:**
- Create: `tests/unit/test_backtest_process_protocol_diagnostics.py`
- Modify: `backtest/backtest.py`

- [ ] **Step 1: Add failing helper and source-contract tests**

Create `tests/unit/test_backtest_process_protocol_diagnostics.py`:

```python
import json
import os
from multiprocessing import Queue
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_emit_cli_protocol_checkpoint_is_env_gated(monkeypatch):
    from backtest.backtest import _emit_cli_protocol_checkpoint

    q = Queue()
    monkeypatch.delenv('STOM_CLI_BACKTEST_PROTOCOL_DIAG', raising=False)

    _emit_cli_protocol_checkpoint(q, 'BackTest', 'backtest_child_started', {'pid': 123})

    assert q.empty()


def test_emit_cli_protocol_checkpoint_writes_json_message(monkeypatch):
    from backtest.backtest import _emit_cli_protocol_checkpoint

    q = Queue()
    monkeypatch.setenv('STOM_CLI_BACKTEST_PROTOCOL_DIAG', '1')

    _emit_cli_protocol_checkpoint(q, 'BackTest', 'backtest_child_started', {'pid': 123})

    ui_id, message = q.get(timeout=1)
    assert isinstance(ui_id, (int, float))
    assert message.startswith('[CLI_DIAG] ')
    payload = json.loads(message[len('[CLI_DIAG] '):])
    assert payload['source'] == 'BackTest'
    assert payload['checkpoint'] == 'backtest_child_started'
    assert payload['detail'] == {'pid': 123}


def test_backtest_start_emits_key_protocol_checkpoints():
    content = (ROOT / 'backtest' / 'backtest.py').read_text(encoding='utf-8')

    for checkpoint in [
        'backtest_child_started',
        'backtest_child_config_received',
        'backtest_child_moneytop_loaded',
        'backtest_child_total_process_started',
        'backtest_child_engine_start_sent',
        'backtest_child_waiting_mq_first',
        'backtest_child_mq_first_received',
        'backtest_child_waiting_mq_second',
        'backtest_child_completed',
    ]:
        assert checkpoint in content


def test_total_emits_key_protocol_checkpoints():
    content = (ROOT / 'backtest' / 'backtest.py').read_text(encoding='utf-8')

    for checkpoint in [
        'total_process_started',
        'total_info_received',
        'total_engine_done_count',
        'total_subtotal_collection_done_count',
        'total_result_received',
        'total_report_started',
        'total_report_no_trades',
        'total_report_db_written',
        'total_report_csv_written',
        'total_report_mq_sent',
    ]:
        assert checkpoint in content
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_backtest_process_protocol_diagnostics.py -q
```

Expected:

```text
FAIL because _emit_cli_protocol_checkpoint and checkpoint strings do not exist yet.
```

- [ ] **Step 3: Add CLI-only checkpoint helper**

Modify the imports at the top of `backtest/backtest.py`:

```python
import json
import os
import re
import sys
import time
import sqlite3
```

Add this helper after `_read_moneytop_with_diagnostics()`:

```python
def _emit_cli_protocol_checkpoint(queue, source, checkpoint, detail=None):
    if os.environ.get('STOM_CLI_BACKTEST_PROTOCOL_DIAG') != '1':
        return
    payload = {
        'source': source,
        'checkpoint': checkpoint,
        'detail': detail or {},
        'time': str_ymdhms(),
    }
    queue.put((
        ui_num.get('시스템로그', 1),
        '[CLI_DIAG] ' + json.dumps(payload, ensure_ascii=False, default=str),
    ))
```

- [ ] **Step 4: Emit BackTest.Start checkpoints**

Add calls in `BackTest.Start()` at these locations:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_started')
        data = self.bq.get()
        _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_config_received', {
            'backname': self.backname,
            'ui_gubun': self.ui_gubun,
        })
```

After `df_mt` validation and before `day_count`:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_moneytop_loaded', {
            'rows': len(df_mt),
            'back_count': back_count,
        })
```

After strategy code is loaded:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_strategy_loaded', {
            'buy_strategy': buystg_name,
            'sell_strategy': sellstg_name,
        })
```

Replace the anonymous `Process(...).start()` for `Total` with a named process:

```python
        total_proc = Process(
            target=Total,
            args=(self.wq, self.sq, self.tq, self.teleQ, mq, self.lq, self.bstq_list, self.backname, self.ui_gubun,
                  self.gubun, market_text, self.dict_set)
        )
        total_proc.start()
        _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_total_process_started', {
            'pid': total_proc.pid,
        })
```

After `self.tq.put(('백테정보', ...))`:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_total_info_sent', {
            'day_count': day_count,
            'back_count': back_count,
        })
```

After the loop that sends `('백테시작', 2)`:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_engine_start_sent', {
            'engine_count': len(self.bstq_list),
        })
```

After the loop that sends `data` to `beq_list`:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_engine_data_sent', {
            'engine_count': len(self.beq_list),
        })
```

Around the first and second `mq.get()` calls:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_waiting_mq_first')
        data = mq.get()
        _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_mq_first_received', {'data': data})
        if data == f'{self.backname} 완료':
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 소요시간 {now() - start_time}'))
            if self.dict_set['스톰라이브']: self.lq.put(self.backname)
            _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_waiting_mq_second')
            _ = mq.get()
            _emit_cli_protocol_checkpoint(self.wq, 'BackTest', 'backtest_child_completed')
            self.SysExit(False)
```

- [ ] **Step 5: Emit Total checkpoints**

In `Total.__init__`, before `self.MainLoop()`:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'Total', 'total_process_started', {
            'backname': self.backname,
            'ui_gubun': self.ui_gubun,
        })
```

In `Total.MainLoop()`, after `bc += 1`:

```python
                _emit_cli_protocol_checkpoint(self.wq, 'Total', 'total_engine_done_count', {
                    'count': bc,
                    'back_count': self.back_count,
                })
```

After `sc += 1`:

```python
                _emit_cli_protocol_checkpoint(self.wq, 'Total', 'total_subtotal_collection_done_count', {
                    'count': sc,
                })
```

At the start of `elif data[0] == '백테결과':`

```python
                _emit_cli_protocol_checkpoint(self.wq, 'Total', 'total_result_received', {
                    'trade_count': 0 if data[1] is None else len(data[1]),
                })
```

At the end of `elif data[0] == '백테정보':`

```python
                _emit_cli_protocol_checkpoint(self.wq, 'Total', 'total_info_received', {
                    'back_count': self.back_count,
                    'day_count': self.day_count,
                })
```

At the start of `Report()`:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'Total', 'total_report_started', {
            'trade_count': 0 if list_tsg is None else len(list_tsg),
        })
```

Before the `sys.exit()` in the no-trades branch:

```python
            _emit_cli_protocol_checkpoint(self.wq, 'Total', 'total_report_no_trades')
```

After `df.to_sql(...)` / `self.df_tsg.to_sql(...)` / `con.close()`:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'Total', 'total_report_db_written', {
            'table': self.savename,
            'save_file_name': save_file_name,
        })
```

After `self.df_tsg.to_csv(...)`:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'Total', 'total_report_csv_written', {
            'save_file_name': save_file_name,
        })
```

After each `self.mq.put(f'{self.backname} 완료')`, add:

```python
        _emit_cli_protocol_checkpoint(self.wq, 'Total', 'total_report_mq_sent', {
            'message': f'{self.backname} 완료',
        })
```

- [ ] **Step 6: Run BackTest diagnostic tests**

Run:

```powershell
python -m pytest tests/unit/test_backtest_process_protocol_diagnostics.py -q
```

Expected:

```text
4 passed.
```

- [ ] **Step 7: Commit Task 3**

Run:

```powershell
git add backtest/backtest.py tests/unit/test_backtest_process_protocol_diagnostics.py
git commit -m "BackTest process 내부 protocol checkpoint를 추가한다" -m "CLI timeout이 BackTest.Start 내부 어느 단계에서 발생하는지 확인할 수 있도록 BackTest와 Total에 CLI 전용 windowQ checkpoint를 추가했다.

Constraint: GUI 실행에서는 STOM_CLI_BACKTEST_PROTOCOL_DIAG가 없으므로 추가 로그가 발생하지 않아야 함
Rejected: Total queue parent drain | 실행 중 결과 protocol을 방해할 수 있음
Confidence: medium
Scope-risk: moderate
Tested: tests/unit/test_backtest_process_protocol_diagnostics.py
Not-tested: live BackTest smoke"
```

---

### Task 4: Runner Timeout JSON Diagnostic Summary

**Files:**
- Modify: `cli/runner.py`
- Modify: `tests/unit/test_runner_helpers.py`

- [ ] **Step 1: Add failing summary tests**

Append to `tests/unit/test_runner_helpers.py`:

```python
def test_runner_summarizes_protocol_diagnostics_by_source():
    from cli.runner import _summarize_protocol_diagnostics

    events = [
        {'source': 'BackTest', 'checkpoint': 'backtest_child_started', 'detail': {}},
        {'source': 'Total', 'checkpoint': 'total_info_received', 'detail': {'back_count': 4}},
        {'source': 'BackTest', 'checkpoint': 'backtest_child_waiting_mq_first', 'detail': {}},
    ]

    summary = _summarize_protocol_diagnostics(events)

    assert summary['event_count'] == 3
    assert summary['last_checkpoint'] == 'backtest_child_waiting_mq_first'
    assert summary['last_by_source']['BackTest'] == 'backtest_child_waiting_mq_first'
    assert summary['last_by_source']['Total'] == 'total_info_received'
    assert summary['events'] == events


def test_runner_attaches_protocol_diagnostics_on_timeout():
    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'cli', 'runner.py',
    )
    with open(runner_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "os.environ['STOM_CLI_BACKTEST_PROTOCOL_DIAG'] = '1'" in content
    assert "'backtest_process_diagnostics'" in content
    assert '_summarize_protocol_diagnostics(drainer.protocol_diagnostics)' in content
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py::test_runner_summarizes_protocol_diagnostics_by_source tests/unit/test_runner_helpers.py::test_runner_attaches_protocol_diagnostics_on_timeout -q
```

Expected:

```text
FAIL because _summarize_protocol_diagnostics and runner timeout attachment do not exist yet.
```

- [ ] **Step 3: Implement summary helper**

Add this helper in `cli/runner.py` near `_collect_backtest_child_diagnostics()`:

```python
def _summarize_protocol_diagnostics(events):
    events = list(events or [])
    last_by_source = {}
    for event in events:
        source = event.get('source')
        checkpoint = event.get('checkpoint')
        if source and checkpoint:
            last_by_source[source] = checkpoint
    return {
        'event_count': len(events),
        'last_checkpoint': events[-1].get('checkpoint') if events else None,
        'last_by_source': last_by_source,
        'events': events,
    }
```

- [ ] **Step 4: Enable CLI protocol diagnostics during run_backtest**

In `run_backtest(config)`, before child processes are created:

```python
    previous_protocol_diag = os.environ.get('STOM_CLI_BACKTEST_PROTOCOL_DIAG')
    os.environ['STOM_CLI_BACKTEST_PROTOCOL_DIAG'] = '1'
```

In the timeout branch, before `return result`:

```python
            result['backtest_process_diagnostics'] = _summarize_protocol_diagnostics(
                drainer.protocol_diagnostics
            )
```

In the non-zero exit branch and missing metrics branch, also attach the summary:

```python
            result['backtest_process_diagnostics'] = _summarize_protocol_diagnostics(
                drainer.protocol_diagnostics
            )
```

In the `except Exception as e:` block, attach the summary:

```python
        result['backtest_process_diagnostics'] = _summarize_protocol_diagnostics(
            getattr(drainer, 'protocol_diagnostics', [])
        )
```

In `finally`, restore the env value before returning:

```python
        if previous_protocol_diag is None:
            os.environ.pop('STOM_CLI_BACKTEST_PROTOCOL_DIAG', None)
        else:
            os.environ['STOM_CLI_BACKTEST_PROTOCOL_DIAG'] = previous_protocol_diag
```

Keep this restore after process cleanup so child processes inherit the value while running.

- [ ] **Step 5: Run focused runner tests**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py::test_runner_summarizes_protocol_diagnostics_by_source tests/unit/test_runner_helpers.py::test_runner_attaches_protocol_diagnostics_on_timeout -q
```

Expected:

```text
2 passed.
```

- [ ] **Step 6: Run related tests**

Run:

```powershell
python -m pytest tests/unit/test_queue_drain.py tests/unit/test_backtest_process_protocol_diagnostics.py tests/unit/test_runner_helpers.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 7: Commit Task 4**

Run:

```powershell
git add cli/runner.py tests/unit/test_runner_helpers.py
git commit -m "CLI timeout JSON에 BackTest protocol 진단을 포함한다" -m "CLI run_backtest가 BackTest child에서 발생한 windowQ protocol checkpoint를 timeout/error JSON에 포함하도록 diagnostic summary를 추가했다.

Constraint: 실행 중 engine/Total protocol queue를 parent가 소비하지 않아야 함
Confidence: medium
Scope-risk: moderate
Tested: queue_drain, BackTest protocol diagnostic, runner helper tests
Not-tested: live BackTest smoke"
```

---

### Task 5: Smoke Validation And Documentation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-22_cli_backtest_process_timeout_protocol_smoke.md`
- Create: `docs/update_log/2026-04-22_cli_backtest_process_timeout_protocol.md`

- [ ] **Step 1: Ensure GUI/STOM processes are not holding the same run**

Run:

```powershell
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
  $_.Path -like '*python*'
} | Select-Object Id,ProcessName,Path
```

Expected:

```text
No obvious stale STOM GUI/BackTest process for the same ResearchTest run.
If unrelated Python processes exist, do not kill them without confirming their command line.
```

- [ ] **Step 2: Run smoke 4**

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
  -o backtest\temp\wide_v1_cli_process_timeout_protocol_smoke_4_20260422.json
```

Expected:

```text
Command returns before any external shell timeout.
If still status=error timeout, JSON contains backtest_process_diagnostics.
```

- [ ] **Step 3: Run smoke 32**

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
  -o backtest\temp\wide_v1_cli_process_timeout_protocol_smoke_32_20260422.json
```

Expected:

```text
Command returns before any external shell timeout.
If still status=error timeout, JSON contains backtest_process_diagnostics.
```

- [ ] **Step 4: Summarize smoke JSON**

Run:

```powershell
@'
import json
from pathlib import Path

for path in [
    Path('backtest/temp/wide_v1_cli_process_timeout_protocol_smoke_4_20260422.json'),
    Path('backtest/temp/wide_v1_cli_process_timeout_protocol_smoke_32_20260422.json'),
]:
    print('file', path)
    if not path.exists():
        print('exists', False)
        continue
    payload = json.loads(path.read_text(encoding='utf-8'))
    diag = payload.get('backtest_process_diagnostics') or {}
    print('exists', True)
    print('status', payload.get('status'))
    print('message', payload.get('message'))
    print('last_checkpoint', payload.get('last_checkpoint'))
    print('csv_path', payload.get('csv_path'))
    print('diagnostic_event_count', diag.get('event_count'))
    print('diagnostic_last_checkpoint', diag.get('last_checkpoint'))
    print('diagnostic_last_by_source', diag.get('last_by_source'))
    print()
'@ | python -
```

Expected:

```text
Each JSON summary is printed. diagnostic_event_count is non-zero if BackTest child reached checkpoint emission.
```

- [ ] **Step 5: Draft pilot log from smoke JSON**

Run this script to print a pilot log draft using the actual smoke JSON values:

```powershell
@'
import json
from pathlib import Path

paths = {
    "smoke 4": Path("backtest/temp/wide_v1_cli_process_timeout_protocol_smoke_4_20260422.json"),
    "smoke 32": Path("backtest/temp/wide_v1_cli_process_timeout_protocol_smoke_32_20260422.json"),
}

def row(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    diag = payload.get("backtest_process_diagnostics") or {}
    return {
        "status": payload.get("status"),
        "message": payload.get("message"),
        "last_checkpoint": payload.get("last_checkpoint"),
        "diagnostic_event_count": diag.get("event_count"),
        "diagnostic_last_checkpoint": diag.get("last_checkpoint"),
        "diagnostic_last_by_source": diag.get("last_by_source"),
        "csv_path": payload.get("csv_path"),
    }

rows = {name: row(path) for name, path in paths.items()}
diagnostic_ok = all((item["diagnostic_event_count"] or 0) > 0 for item in rows.values())
decision = "PASS_FOR_DIAGNOSTIC" if diagnostic_ok else "FAIL_FOR_DIAGNOSTIC"
reason = (
    "smoke 4/32 모두 timeout이어도 backtest_process_diagnostics가 남아 다음 원인 위치를 판단할 수 있다."
    if diagnostic_ok else
    "smoke JSON에 protocol diagnostic event가 남지 않아 child checkpoint 전달 경로를 다시 확인해야 한다."
)
next_command = (
    "$brainstorming CLI BackTest Total/BackSubTotal 완료 신호 protocol 수정 설계"
    if diagnostic_ok else
    "$brainstorming CLI BackTest child checkpoint 전달 실패 분석 설계"
)

lines = [
    "# CLI BackTest Process Timeout Protocol Smoke",
    "",
    "## 목적",
    "",
    "BackTest process가 `backtest_process_started` 이후 timeout될 때 child/Total protocol checkpoint가 CLI JSON에 남는지 확인한다.",
    "",
    "## 실행 조건",
    "",
    "```text",
    "buy=ResearchTest_Tick_B_090000_092800_Wide_20260419",
    "sell=ResearchTest_Tick_S_090000_092800_Wide_20260419",
    "period=20250102~20250103",
    "time=090000~092800",
    "timeframe=tick",
    "avg_time=30",
    r"runtime_db=C:\System_Trading\STOM\STOM_V.wt-dev\_database",
    "```",
    "",
]
for name, item in rows.items():
    lines += [
        f"## {name} 결과",
        "",
        "```text",
        f"status={item['status']}",
        f"message={item['message']}",
        f"last_checkpoint={item['last_checkpoint']}",
        f"diagnostic_event_count={item['diagnostic_event_count']}",
        f"diagnostic_last_checkpoint={item['diagnostic_last_checkpoint']}",
        f"diagnostic_last_by_source={item['diagnostic_last_by_source']}",
        f"csv_path={item['csv_path']}",
        "```",
        "",
    ]
lines += [
    "## 판정",
    "",
    "```text",
    f"decision={decision}",
    f"reason={reason}",
    "```",
    "",
    "## 다음 단계",
    "",
    "```text",
    next_command,
    "```",
]
print("\n".join(lines))
'@ | python -
```

Use `apply_patch` to create `docs/research/condition_research/pilot_logs/2026-04-22_cli_backtest_process_timeout_protocol_smoke.md` with exactly the printed draft after checking it matches the smoke output.

- [ ] **Step 6: Draft update log from verification output**

After verification commands in Task 6 have been run, create `docs/update_log/2026-04-22_cli_backtest_process_timeout_protocol.md` with the concrete command results from the terminal. The committed file must use exact values such as `queue_drain_tests=37 passed` or `verify_nonrelease_sync=PASS`; generic labels are not acceptable.

```markdown
# 2026-04-22 CLI BackTest Process Timeout Protocol

## 목적

CLI 백테스트가 BackTest process 시작 후 timeout될 때 내부 protocol 진행 지점을 JSON으로 확인할 수 있게 했다.

## 변경 사항

- QueueDrainer protocol diagnostic capture 추가
- BackTest/Total CLI-only checkpoint 추가
- runner timeout/error JSON diagnostic summary 추가
- smoke 4/32 실행 결과 기록

## 검증

검증 결과는 아래 키를 유지하고, 값은 터미널 출력과 smoke JSON에서 확인한 구체 값으로 기록한다.

```text
queue_drain_tests=37 passed
backtest_protocol_tests=4 passed
runner_helper_tests=49 passed
focused_tests=selected CLI/backtest unit tests passed
verify_nonrelease_sync=PASS
smoke_4=status=error,last_checkpoint=backtest_process_started,diagnostic_event_count=nonzero
smoke_32=status=error,last_checkpoint=backtest_process_started,diagnostic_event_count=nonzero
```

## 판정

```text
decision=PASS_FOR_DIAGNOSTIC
reason=smoke 4/32 모두 timeout이어도 protocol diagnostic이 남아 다음 수정 지점을 판단할 수 있다.
```

## 남은 리스크

- 이번 단계는 원인 위치 계측이며 CLI metrics/CSV 생성을 보장하지 않는다.
- GUI/CLI 결과 비교는 metrics/CSV 생성 후 별도 gate에서 수행해야 한다.
- 원인이 Total/BackSubTotal protocol이면 다음 PR에서 최소 수정이 필요하다.
```

- [ ] **Step 7: Placeholder scan**

Run:

```powershell
rg -n "generic labels|nonzero|selected CLI|concrete value" docs\research\condition_research\pilot_logs\2026-04-22_cli_backtest_process_timeout_protocol_smoke.md docs\update_log\2026-04-22_cli_backtest_process_timeout_protocol.md
```

Expected:

```text
No output.
```

---

### Task 6: Final Verification And Commit

**Files:**
- Commit:
  - `cli/queue_drain.py`
  - `tests/unit/test_queue_drain.py`
  - `backtest/backtest.py`
  - `tests/unit/test_backtest_process_protocol_diagnostics.py`
  - `cli/runner.py`
  - `tests/unit/test_runner_helpers.py`
  - `docs/research/condition_research/pilot_logs/2026-04-22_cli_backtest_process_timeout_protocol_smoke.md`
  - `docs/update_log/2026-04-22_cli_backtest_process_timeout_protocol.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_queue_drain.py tests/unit/test_backtest_process_protocol_diagnostics.py tests/unit/test_runner_helpers.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run broader CLI unit tests**

Run:

```powershell
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_queue_drain.py tests/unit/test_runner_helpers.py tests/unit/test_output.py tests/unit/test_exit_codes.py tests/unit/test_setting_base_cli_overrides.py tests/unit/test_backtest_process_protocol_diagnostics.py -q
```

Expected:

```text
All selected CLI/backtest unit tests pass.
```

- [ ] **Step 3: Run full unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
All unit tests pass.
```

- [ ] **Step 4: Run nonrelease sync guard**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
PASS.
```

- [ ] **Step 5: Run diff check**

Run:

```powershell
git diff --check
```

Expected:

```text
No whitespace errors.
```

- [ ] **Step 6: Confirm runtime artifacts are not staged**

Run:

```powershell
git status --short --untracked-files=all
```

Expected:

```text
Only code/test/doc changes are tracked or staged.
Runtime DB/CSV/graph/temp JSON files are not staged.
```

- [ ] **Step 7: Commit final docs if not already committed**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-22_cli_backtest_process_timeout_protocol_smoke.md docs/update_log/2026-04-22_cli_backtest_process_timeout_protocol.md
git commit -m "CLI BackTest timeout protocol smoke 결과를 기록한다" -m "BackTest process timeout 계측 결과를 pilot log와 update log에 기록해 다음 수정 단계의 원인 위치를 명확히 남겼다.

Constraint: runtime JSON/CSV/graph artifact는 커밋하지 않음
Confidence: medium
Scope-risk: narrow
Tested: focused tests, full unit tests, verify_nonrelease_sync.py, smoke 4/32
Not-tested: full-year GUI/CLI parity, candidate_count=5"
```

---

## Decision Routing

Use the smoke result:

```text
If diagnostic_last_checkpoint is backtest_child_waiting_mq_first:
  $brainstorming CLI BackTest Total/BackSubTotal 완료 신호 protocol 수정 설계

If diagnostic_last_checkpoint is total_report_csv_written or total_report_mq_sent but process still times out:
  $brainstorming CLI BackTest mq second completion wait 수정 설계

If smoke creates metrics/CSV:
  $brainstorming Wide v1 CLI Baseline Backtest Gate 및 GUI 결과 비교 설계

If diagnostic_event_count is zero:
  $brainstorming CLI BackTest child checkpoint 전달 실패 분석 설계
```

Do not run `candidate_count=5` until CLI baseline can produce metrics/CSV and GUI parity can be compared.

## Self-Review Checklist

Spec coverage:

```text
Queue-safe observation channel: Task 1-2
BackTest/Total checkpoints: Task 3
Timeout JSON diagnostics: Task 4
Smoke 4/32: Task 5
Focused/full verification: Task 6
Decision routing: Decision Routing
```

No implementation step consumes `totalQ`, `beq`, or `bstq` from the parent while the backtest is running. The plan uses `windowQ` only and gates extra messages behind `STOM_CLI_BACKTEST_PROTOCOL_DIAG`.
