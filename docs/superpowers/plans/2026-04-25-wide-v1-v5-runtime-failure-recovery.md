# Wide v1 v5 Runtime Failure Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `discovery research` v5 runs recoverable by writing runtime JSON checkpoints, continuing after individual candidate failures, and aborting after three consecutive candidate failures.

**Architecture:** Add a small `cli.research_runtime_output` helper for JSON output and checkpoints, then wire it through `ResearchLoopConfig`, `run_research_iteration()`, and `discovery research` CLI arguments. Keep `cli.runner.py` unchanged except for preserving existing diagnostics already returned by candidate results.

**Tech Stack:** Python 3.11, argparse, dataclasses, pathlib, json, pytest, existing STOM CLI modules.

---

## File Structure

- Create: `cli\research_runtime_output.py`
  - Owns checkpoint event recording and atomic JSON writes for research runtime payloads.
- Modify: `cli\research_loop.py`
  - Adds config fields, checkpoint calls, consecutive candidate failure policy, runtime output writes, and v5 actual row-set gate.
- Modify: `cli\subcommands.py`
  - Adds `--runtime-output` and `--max-consecutive-candidate-failures` to `discovery research`.
  - Passes parsed values into `AIBacktestController.research_strategy_once()`.
- Modify: `tests\unit\test_research_loop.py`
  - Adds unit coverage for config fields, checkpoint persistence, failure continuation, failure abort, and v5 row-set gating.
- Modify: `tests\unit\test_subcommands.py`
  - Adds CLI parser and handler coverage for the new arguments.
- Create: `docs\pr\2026-04-25_wide_v1_v5_runtime_failure_recovery_pr.md`
  - Korean PR report with plan, current scope, result, verification, and next command.

Do not modify `cli\runner.py` in this plan. Do not stage `backtest\csv`, `backtest\graph`, or `backtest\temp` outputs.

---

## Task 1: CLI Contract and Config Surface Tests

**Files:**
- Modify: `tests\unit\test_research_loop.py`
- Modify: `tests\unit\test_subcommands.py`

- [ ] **Step 1: Add failing config field test**

Append this test near the existing `ResearchLoopConfig` field tests in `tests\unit\test_research_loop.py`:

```python
def test_research_loop_config_has_runtime_recovery_fields():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'runtime_output_path' in names
    assert 'max_consecutive_candidate_failures' in names

    config = ResearchLoopConfig()
    assert config.runtime_output_path is None
    assert config.max_consecutive_candidate_failures == 3
```

- [ ] **Step 2: Add failing parser test**

Append this test near other discovery research parser tests in `tests\unit\test_subcommands.py`:

```python
def test_discovery_research_parser_accepts_runtime_recovery_options():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'RuntimeRecovery',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--run-candidates',
        '--runtime-output', 'backtest/temp/runtime_recovery.json',
        '--max-consecutive-candidate-failures', '3',
    ])

    assert args.runtime_output == 'backtest/temp/runtime_recovery.json'
    assert args.max_consecutive_candidate_failures == 3
```

- [ ] **Step 3: Add failing handler passthrough test**

Append this test near `test_discovery_research_handler_calls_controller` in `tests\unit\test_subcommands.py`:

```python
def test_discovery_research_handler_passes_runtime_recovery_options(capsys):
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'phase': 'candidates_evaluated'}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'RuntimeRecovery',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-candidates',
            '--runtime-output', 'backtest/temp/runtime_recovery.json',
            '--max-consecutive-candidate-failures', '3',
        ])

    assert exit_code == 0
    _ = capsys.readouterr()
    kwargs = mock.call_args.args[0]
    assert kwargs['runtime_output_path'] == 'backtest/temp/runtime_recovery.json'
    assert kwargs['max_consecutive_candidate_failures'] == 3
```

- [ ] **Step 4: Run the focused failing tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_research_loop_config_has_runtime_recovery_fields `
  tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_runtime_recovery_options `
  tests/unit/test_subcommands.py::test_discovery_research_handler_passes_runtime_recovery_options `
  -q
```

Expected now:

```text
FAILED
```

Failure reasons should mention missing `runtime_output_path`, missing `max_consecutive_candidate_failures`, or unrecognized CLI arguments.

- [ ] **Step 5: Add config fields**

In `cli\research_loop.py`, extend `ResearchLoopConfig` after `keep_failed_candidate`:

```python
    runtime_output_path: str | None = None
    max_consecutive_candidate_failures: int = 3
```

- [ ] **Step 6: Add CLI arguments**

In `cli\subcommands.py`, add these lines after `--keep-failed-candidate`:

```python
    disc_research.add_argument('--runtime-output', dest='runtime_output_path')
    disc_research.add_argument('--max-consecutive-candidate-failures', type=int, default=3)
```

- [ ] **Step 7: Pass CLI values into controller**

In the `parsed.discovery_action == 'research'` config dict in `cli\subcommands.py`, add:

```python
            'runtime_output_path': parsed.runtime_output_path,
            'max_consecutive_candidate_failures': parsed.max_consecutive_candidate_failures,
```

Place these near existing candidate runtime options.

- [ ] **Step 8: Run the Task 1 tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_research_loop_config_has_runtime_recovery_fields `
  tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_runtime_recovery_options `
  tests/unit/test_subcommands.py::test_discovery_research_handler_passes_runtime_recovery_options `
  -q
```

Expected:

```text
3 passed
```

- [ ] **Step 9: Commit Task 1**

Run:

```powershell
git add cli/research_loop.py cli/subcommands.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py
git commit -m "Wide v1 v5 런타임 복구 CLI 계약을 추가한다" -m "research 실행에 runtime output 경로와 연속 후보 실패 허용값을 전달할 수 있게 한다. 아직 runtime 파일 쓰기와 checkpoint 정책은 다음 커밋에서 구현한다." -m "Constraint: discovery research 범위에만 새 옵션을 노출한다`nConfidence: high`nScope-risk: narrow`nTested: python -m pytest tests/unit/test_research_loop.py::test_research_loop_config_has_runtime_recovery_fields tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_runtime_recovery_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_runtime_recovery_options -q`nNot-tested: runtime output writing is implemented in a later task"
```

Expected: one commit is created with title `Wide v1 v5 런타임 복구 CLI 계약을 추가한다`.

---

## Task 2: Runtime Output Helper

**Files:**
- Create: `cli\research_runtime_output.py`
- Create: `tests\unit\test_research_runtime_output.py`

- [ ] **Step 1: Write failing helper tests**

Create `tests\unit\test_research_runtime_output.py`:

```python
import json

import pytest

from cli.research_runtime_output import (
    ResearchRuntimeRecorder,
    ResearchRuntimeWriteError,
)


def test_runtime_recorder_writes_json_atomically(tmp_path):
    output_path = tmp_path / 'nested' / 'runtime.json'
    recorder = ResearchRuntimeRecorder(str(output_path))
    recorder.mark('iteration_started', phase='candidate_iteration')

    payload = {'status': 'ok', 'phase': 'candidates_evaluated'}
    written = recorder.write(payload)

    assert written == str(output_path)
    data = json.loads(output_path.read_text(encoding='utf-8'))
    assert data['status'] == 'ok'
    assert data['phase'] == 'candidates_evaluated'
    assert data['checkpoints'][0]['name'] == 'iteration_started'
    assert data['checkpoint_summary']['event_count'] == 1
    assert data['checkpoint_summary']['last_checkpoint'] == 'iteration_started'


def test_runtime_recorder_noops_without_output_path():
    recorder = ResearchRuntimeRecorder(None)
    recorder.mark('iteration_started')

    assert recorder.write({'status': 'ok'}) is None
    assert recorder.summary()['event_count'] == 1


def test_runtime_recorder_raises_structured_write_error(tmp_path):
    output_dir = tmp_path / 'as_directory.json'
    output_dir.mkdir()
    recorder = ResearchRuntimeRecorder(str(output_dir))

    with pytest.raises(ResearchRuntimeWriteError) as excinfo:
        recorder.write({'status': 'ok'})

    assert excinfo.value.path == str(output_dir)
    assert 'runtime output write failed' in str(excinfo.value)
```

- [ ] **Step 2: Run helper tests to verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_runtime_output.py -q
```

Expected now:

```text
FAILED
```

Failure reason should mention `ModuleNotFoundError: No module named 'cli.research_runtime_output'`.

- [ ] **Step 3: Create helper module**

Create `cli\research_runtime_output.py`:

```python
"""Runtime JSON output support for discovery research loops."""

from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any


class ResearchRuntimeWriteError(RuntimeError):
    """Raised when a research runtime payload cannot be written."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        super().__init__(f'runtime output write failed for {path}: {message}')


class ResearchRuntimeRecorder:
    """Record research checkpoints and optionally persist runtime JSON."""

    def __init__(self, output_path: str | None = None) -> None:
        self.output_path = output_path
        self.started_at = time.monotonic()
        self.events: list[dict[str, Any]] = []

    def mark(
        self,
        name: str,
        *,
        phase: str | None = None,
        message: str | None = None,
        candidate_index: int | None = None,
        strategy_name: str | None = None,
        consecutive_failure_count: int | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            'name': name,
            'elapsed_seconds': self._elapsed_seconds(),
        }
        if phase is not None:
            event['phase'] = phase
        if message is not None:
            event['message'] = message
        if candidate_index is not None:
            event['candidate_index'] = candidate_index
        if strategy_name is not None:
            event['strategy_name'] = strategy_name
        if consecutive_failure_count is not None:
            event['consecutive_failure_count'] = consecutive_failure_count
        if detail is not None:
            event['detail'] = _json_safe(detail)
        self.events.append(event)
        return event

    def summary(self) -> dict[str, Any]:
        return {
            'event_count': len(self.events),
            'last_checkpoint': self.events[-1]['name'] if self.events else None,
            'elapsed_seconds': self._elapsed_seconds(),
        }

    def decorate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            **payload,
            'checkpoints': list(self.events),
            'checkpoint_summary': self.summary(),
        }

    def write(self, payload: dict[str, Any]) -> str | None:
        if not self.output_path:
            return None
        path = Path(self.output_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(self.decorate(payload), ensure_ascii=False, indent=2, default=str)
            temp_path = path.with_name(f'.{path.name}.tmp')
            temp_path.write_text(text, encoding='utf-8')
            os.replace(temp_path, path)
        except Exception as exc:
            raise ResearchRuntimeWriteError(str(path), str(exc)) from exc
        return str(path)

    def _elapsed_seconds(self) -> float:
        return round(time.monotonic() - self.started_at, 3)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return repr(value)
```

- [ ] **Step 4: Run helper tests**

Run:

```powershell
python -m pytest tests/unit/test_research_runtime_output.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add cli/research_runtime_output.py tests/unit/test_research_runtime_output.py
git commit -m "Wide v1 v5 연구 런타임 출력 도우미를 추가한다" -m "research loop가 stdout과 무관하게 checkpoint가 포함된 runtime JSON을 저장할 수 있도록 작은 helper를 분리한다." -m "Constraint: 새 dependency 없이 pathlib/json/os.replace만 사용한다`nConfidence: high`nScope-risk: narrow`nTested: python -m pytest tests/unit/test_research_runtime_output.py -q`nNot-tested: research_loop integration is implemented in later tasks"
```

Expected: one commit is created with title `Wide v1 v5 연구 런타임 출력 도우미를 추가한다`.

---

## Task 3: Runtime Output Integration for Successful Iterations

**Files:**
- Modify: `tests\unit\test_research_loop.py`
- Modify: `cli\research_loop.py`

- [ ] **Step 1: Add failing success runtime output test**

Append this test near `test_run_research_iteration_analyzes_once_and_runs_each_candidate` in `tests\unit\test_research_loop.py`:

```python
def test_run_research_iteration_writes_runtime_output_on_success(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate_1 = tmp_path / 'candidate_1.csv'
    candidate_2 = tmp_path / 'candidate_2.csv'
    runtime_output = tmp_path / 'runtime' / 'research.json'
    _write_trade_csv(baseline, name='BASE')
    _write_trade_csv(candidate_1, name='C1')
    _write_trade_csv(candidate_2, name='C2')
    _patch_analysis_success(monkeypatch, expressions=['R_MFE < 0', 'R_MFE > 1'])

    def fake_execute(config, spec, controller, baseline_csv):
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'ok',
            'phase': 'candidate_evaluated',
            'candidate_csv': str(candidate_1 if spec['index'] == 1 else candidate_2),
            'comparison': {
                'candidate_summary': {
                    'trade_count': 10 + spec['index'],
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.5,
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': float(spec['index'])},
            'cleanup': None,
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *args, **kwargs: {'status': 'ok', 'action': 'deleted'},
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='RuntimeSuccess',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            runtime_output_path=str(runtime_output),
        ),
        DummyController(None),
    )

    data = json.loads(runtime_output.read_text(encoding='utf-8'))
    assert result['status'] == 'ok'
    assert data['status'] == 'ok'
    assert data['phase'] == 'candidates_evaluated'
    assert data['failure_policy']['max_consecutive_candidate_failures'] == 3
    assert data['failure_policy']['total_candidate_failures'] == 0
    assert data['checkpoint_summary']['last_checkpoint'] == 'iteration_completed'
    assert [event['name'] for event in data['checkpoints']] == [
        'iteration_started',
        'analysis_completed',
        'candidate_pool_selected',
        'candidate_started',
        'candidate_succeeded',
        'candidate_started',
        'candidate_succeeded',
        'iteration_completed',
    ]
```

Also add `import json` at the top of `tests\unit\test_research_loop.py` if it is not present.

- [ ] **Step 2: Run the test to verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_success -q
```

Expected now:

```text
FAILED
```

Failure reason should be that the runtime output file does not exist or `ResearchLoopConfig` lacks runtime fields if Task 1 was not completed.

- [ ] **Step 3: Import runtime recorder**

In `cli\research_loop.py`, add near imports:

```python
from cli.research_runtime_output import ResearchRuntimeRecorder, ResearchRuntimeWriteError
```

- [ ] **Step 4: Add failure policy helpers**

Add these helpers above `run_research_iteration()` in `cli\research_loop.py`:

```python
def _initial_failure_policy(config: ResearchLoopConfig) -> dict:
    return {
        'max_consecutive_candidate_failures': config.max_consecutive_candidate_failures,
        'consecutive_candidate_failures': 0,
        'total_candidate_failures': 0,
        'aborted': False,
        'abort_reason': None,
    }


def _runtime_write_failure(path: str | None, exc: Exception, **extra) -> dict:
    return _error(
        'runtime_output_write_failure',
        str(exc),
        runtime_output_path=path,
        **extra,
    )
```

- [ ] **Step 5: Initialize recorder in `run_research_iteration()`**

At the start of `run_research_iteration()` after validation and after `config = replace(...)`, add:

```python
    recorder = ResearchRuntimeRecorder(config.runtime_output_path)
    failure_policy = _initial_failure_policy(config)
    recorder.mark('iteration_started', phase='candidate_iteration')
```

- [ ] **Step 6: Mark analysis and candidate pool checkpoints**

After successful `analyze_result_csv(...)`, add:

```python
    recorder.mark('analysis_completed', phase='analysis')
```

After `specs = _build_candidate_specs(...)`, add:

```python
    recorder.mark(
        'candidate_pool_selected',
        phase='candidate_pool',
        detail={
            'candidate_spec_count': len(specs),
            'requested_count': config.candidate_count,
            'execution_count': candidate_execution_count,
        },
    )
```

- [ ] **Step 7: Replace candidate list comprehension with checkpointed loop**

Replace:

```python
    candidates = [
        _execute_candidate_spec(config, spec, controller, baseline_csv)
        for spec in specs
    ]
```

with:

```python
    candidates = []
    for spec in specs:
        recorder.mark(
            'candidate_started',
            phase='candidate_execution',
            candidate_index=spec.get('index'),
            strategy_name=spec.get('strategy_name'),
        )
        candidate = _execute_candidate_spec(config, spec, controller, baseline_csv)
        candidates.append(candidate)
        if candidate.get('status') == 'ok':
            failure_policy['consecutive_candidate_failures'] = 0
            recorder.mark(
                'candidate_succeeded',
                phase=candidate.get('phase'),
                candidate_index=candidate.get('index'),
                strategy_name=candidate.get('strategy_name'),
            )
        else:
            failure_policy['consecutive_candidate_failures'] += 1
            failure_policy['total_candidate_failures'] += 1
            candidate['consecutive_failure_count'] = failure_policy['consecutive_candidate_failures']
            recorder.mark(
                'candidate_failed',
                phase=candidate.get('phase'),
                message=candidate.get('message'),
                candidate_index=candidate.get('index'),
                strategy_name=candidate.get('strategy_name'),
                consecutive_failure_count=failure_policy['consecutive_candidate_failures'],
            )
            if failure_policy['consecutive_candidate_failures'] == max(
                config.max_consecutive_candidate_failures - 1,
                1,
            ):
                recorder.mark(
                    'candidate_failure_warning',
                    phase='candidate_iteration',
                    message='consecutive candidate failures are approaching the abort threshold',
                    consecutive_failure_count=failure_policy['consecutive_candidate_failures'],
                )
```

- [ ] **Step 8: Add final runtime write for success path**

Before the final `return _build_result(config, {...})`, assign the dict to `result_payload`, then decorate and write:

```python
    result_payload = {
        'status': 'ok' if has_best_candidate else 'error',
        'phase': 'candidates_evaluated' if has_best_candidate else 'candidate_iteration',
        'message': None if has_best_candidate else 'no candidate evaluated successfully',
        'strategy_name': config.name,
        'config': asdict(config),
        'baseline_csv': baseline_csv,
        'baseline_result': baseline_result,
        'analysis_result': analysis_result,
        'expression_result': expression_result,
        'iteration_plan': iteration_plan,
        **_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
        'retention_selection': retention_selection,
        'retention_candidates': retention_candidates,
        'candidate_specs': specs,
        'candidates': ranked_candidates,
        'best_candidate': best_candidate,
        'actual_rowset_selection': actual_rowset_selection,
        'cleanup_summary': cleanup_summary,
        'failure_policy': failure_policy,
    }
    recorder.mark(
        'iteration_completed' if has_best_candidate else 'iteration_aborted',
        phase=result_payload['phase'],
        message=result_payload['message'],
    )
    result_payload = recorder.decorate(result_payload)
    try:
        recorder.write(result_payload)
    except ResearchRuntimeWriteError as exc:
        return _build_result(config, _runtime_write_failure(
            config.runtime_output_path,
            exc,
            strategy_name=config.name,
            config=asdict(config),
            failure_policy=failure_policy,
            candidates=ranked_candidates,
        ))
    return _build_result(config, result_payload)
```

Keep all fields from the existing final return.

- [ ] **Step 9: Run success runtime output test**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_success -q
```

Expected:

```text
1 passed
```

- [ ] **Step 10: Run existing research loop candidate test**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_analyzes_once_and_runs_each_candidate -q
```

Expected:

```text
1 passed
```

- [ ] **Step 11: Commit Task 3**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "Wide v1 v5 연구 루프 성공 체크포인트를 저장한다" -m "candidate 실행 성공 경로에서 runtime output JSON과 checkpoint summary를 저장해 stdout capture 없이도 완료 상태를 복구할 수 있게 한다." -m "Constraint: candidate failure continuation and abort policy are completed in the next task`nConfidence: medium`nScope-risk: moderate`nTested: python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_success tests/unit/test_research_loop.py::test_run_research_iteration_analyzes_once_and_runs_each_candidate -q`nNot-tested: consecutive failure abort policy is implemented in a later task"
```

Expected: one commit is created with title `Wide v1 v5 연구 루프 성공 체크포인트를 저장한다`.

---

## Task 4: Candidate Failure Continuation and Abort Policy

**Files:**
- Modify: `tests\unit\test_research_loop.py`
- Modify: `cli\research_loop.py`

- [ ] **Step 1: Add failing single-failure continuation test**

Append this test in `tests\unit\test_research_loop.py`:

```python
def test_run_research_iteration_continues_after_single_candidate_failure(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate_2 = tmp_path / 'candidate_2.csv'
    runtime_output = tmp_path / 'runtime.json'
    _write_trade_csv(baseline, name='BASE')
    _write_trade_csv(candidate_2, name='C2')
    _patch_analysis_success(monkeypatch, expressions=['R_MFE < 0', 'R_MFE > 1'])
    executed = []

    def fake_execute(config, spec, controller, baseline_csv):
        executed.append(spec['strategy_name'])
        if spec['index'] == 1:
            return {
                'index': spec['index'],
                'strategy_name': spec['strategy_name'],
                'expression': spec['expression'],
                'status': 'error',
                'phase': 'candidate_backtest_timeout',
                'message': 'timeout',
                'cleanup': {'attempted': True, 'reason': 'candidate_backtest_timeout', 'strategy_name': spec['strategy_name']},
                'rank': None,
                'rank_score': None,
                'selected_as_best': False,
            }
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'ok',
            'phase': 'candidate_evaluated',
            'candidate_csv': str(candidate_2),
            'comparison': {
                'candidate_summary': {'trade_count': 11, 'date_concentration': 0.1, 'symbol_concentration': 0.1},
                'trade_count_retention': 0.5,
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': 2.0},
            'cleanup': None,
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *args, **kwargs: {'status': 'ok', 'action': 'deleted'},
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='FailureContinue',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            runtime_output_path=str(runtime_output),
        ),
        DummyController(None),
    )

    assert executed == ['FailureContinue__cand001', 'FailureContinue__cand002']
    assert result['status'] == 'ok'
    assert result['failure_policy']['total_candidate_failures'] == 1
    assert result['failure_policy']['consecutive_candidate_failures'] == 0
    assert result['candidates'][0]['consecutive_failure_count'] == 1
    data = json.loads(runtime_output.read_text(encoding='utf-8'))
    assert data['candidates'][0]['status'] == 'error'
    assert data['candidates'][1]['status'] == 'ok'
```

- [ ] **Step 2: Add failing consecutive abort test**

Append this test:

```python
def test_run_research_iteration_aborts_after_three_consecutive_candidate_failures(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    runtime_output = tmp_path / 'runtime.json'
    _write_trade_csv(baseline, name='BASE')
    _patch_analysis_success(
        monkeypatch,
        expressions=['R_MFE < 0', 'R_MFE > 1', 'R_MAE < -1', 'R_MAE > -2'],
    )
    executed = []

    def fake_execute(config, spec, controller, baseline_csv):
        executed.append(spec['strategy_name'])
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'error',
            'phase': 'candidate_backtest_timeout',
            'message': 'timeout',
            'cleanup': {'attempted': True, 'reason': 'candidate_backtest_timeout', 'strategy_name': spec['strategy_name']},
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='FailureAbort',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=4,
            runtime_output_path=str(runtime_output),
            max_consecutive_candidate_failures=3,
        ),
        DummyController(None),
    )

    assert executed == ['FailureAbort__cand001', 'FailureAbort__cand002', 'FailureAbort__cand003']
    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_iteration_runtime_failure'
    assert result['failure_policy']['aborted'] is True
    assert result['failure_policy']['abort_reason'] == 'max_consecutive_candidate_failures'
    assert result['failure_policy']['consecutive_candidate_failures'] == 3
    data = json.loads(runtime_output.read_text(encoding='utf-8'))
    assert data['phase'] == 'candidate_iteration_runtime_failure'
    assert data['checkpoint_summary']['last_checkpoint'] == 'iteration_aborted'
    assert [candidate['strategy_name'] for candidate in data['candidates']] == executed
```

- [ ] **Step 3: Run failure policy tests to verify failure**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_run_research_iteration_continues_after_single_candidate_failure `
  tests/unit/test_research_loop.py::test_run_research_iteration_aborts_after_three_consecutive_candidate_failures `
  -q
```

Expected now:

```text
FAILED
```

At least the abort test should fail because the loop still executes all specs.

- [ ] **Step 4: Add abort check inside candidate loop**

In the loop added in Task 3, after `candidate_failure_warning` handling, add:

```python
            if (
                config.max_consecutive_candidate_failures > 0
                and failure_policy['consecutive_candidate_failures'] >= config.max_consecutive_candidate_failures
            ):
                failure_policy['aborted'] = True
                failure_policy['abort_reason'] = 'max_consecutive_candidate_failures'
                recorder.mark(
                    'iteration_aborted',
                    phase='candidate_iteration_runtime_failure',
                    message='maximum consecutive candidate failures reached',
                    consecutive_failure_count=failure_policy['consecutive_candidate_failures'],
                )
                break
```

- [ ] **Step 5: Return structured abort before ranking**

Immediately after the candidate loop, add:

```python
    if failure_policy['aborted']:
        cleanup_candidates, cleanup_summary = _apply_iteration_cleanup(config, candidates)
        result_payload = {
            'status': 'error',
            'phase': 'candidate_iteration_runtime_failure',
            'message': 'maximum consecutive candidate failures reached',
            'strategy_name': config.name,
            'config': asdict(config),
            'baseline_csv': baseline_csv,
            'baseline_result': baseline_result,
            'analysis_result': analysis_result,
            'expression_result': expression_result,
            'iteration_plan': iteration_plan,
            **_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
            'retention_selection': retention_selection,
            'retention_candidates': retention_candidates,
            'candidate_specs': specs,
            'candidates': cleanup_candidates,
            'best_candidate': None,
            'actual_rowset_selection': {
                'status': 'not_run',
                'reason': 'candidate_iteration_runtime_failure',
                'requested_count': config.candidate_count,
                'successful_candidate_count': 0,
            },
            'cleanup_summary': cleanup_summary,
            'failure_policy': failure_policy,
        }
        result_payload = recorder.decorate(result_payload)
        try:
            recorder.write(result_payload)
        except ResearchRuntimeWriteError as exc:
            return _build_result(config, _runtime_write_failure(
                config.runtime_output_path,
                exc,
                strategy_name=config.name,
                config=asdict(config),
                failure_policy=failure_policy,
                candidates=cleanup_candidates,
            ))
        return _build_result(config, result_payload)
```

- [ ] **Step 6: Run failure policy tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_run_research_iteration_continues_after_single_candidate_failure `
  tests/unit/test_research_loop.py::test_run_research_iteration_aborts_after_three_consecutive_candidate_failures `
  -q
```

Expected:

```text
2 passed
```

- [ ] **Step 7: Run all research loop tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
passed
```

The exact count may differ from the current branch, but there must be zero failures.

- [ ] **Step 8: Commit Task 4**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "Wide v1 v5 후보 실패 복구 정책을 적용한다" -m "개별 candidate 실패를 결과 item으로 남기고 다음 후보를 계속 실행한다. 연속 실패가 3회에 도달하면 구조화된 runtime JSON을 저장하고 연구 루프를 중단한다." -m "Constraint: runner process cleanup은 이번 범위에서 깊게 변경하지 않는다`nConfidence: medium`nScope-risk: moderate`nTested: python -m pytest tests/unit/test_research_loop.py -q`nNot-tested: actual long v5 backtest rerun is deferred until recovery instrumentation is complete"
```

Expected: one commit is created with title `Wide v1 v5 후보 실패 복구 정책을 적용한다`.

---

## Task 5: v5 Actual Row-Set Gate for Partial Success

**Files:**
- Modify: `tests\unit\test_research_loop.py`
- Modify: `cli\research_loop.py`

- [ ] **Step 1: Add failing v5 insufficient success test**

Append this test near `test_run_research_iteration_v5_executes_oversampled_pool_and_selects_actual_rowsets`:

```python
def test_run_research_iteration_v5_skips_actual_rowset_when_success_count_is_short(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate_csv = tmp_path / 'candidate_1.csv'
    _write_identity_trade_csv(baseline, symbol='BASE')
    _write_identity_trade_csv(candidate_csv, symbol='C1')
    _patch_analysis_success(
        monkeypatch,
        expressions=[
            '66.999 <= 시가총액 < 2580',
            '1805.7 <= 당일거래대금 < 3654.4',
            '체결강도 < 90',
            '등락율 > 1',
        ],
    )
    monkeypatch.setattr(
        research_loop,
        '_safe_reference_promotion_score',
        lambda config, candidate_csv: 1.0,
    )

    def fake_execute(config, spec, controller, baseline_csv):
        if spec['index'] == 1:
            return {
                'index': spec['index'],
                'strategy_name': spec['strategy_name'],
                'expression': spec['expression'],
                'status': 'ok',
                'phase': 'candidate_evaluated',
                'candidate_csv': str(candidate_csv),
                'comparison': {
                    'candidate_summary': {'trade_count': 10, 'date_concentration': 0.1, 'symbol_concentration': 0.1},
                    'trade_count_retention': 0.5,
                },
                'promotion': {'status': 'ok', 'passed': True, 'score': 2.0},
                'cleanup': None,
                'rank': None,
                'rank_score': None,
                'selected_as_best': False,
            }
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'error',
            'phase': 'candidate_backtest_timeout',
            'message': 'timeout',
            'cleanup': {'attempted': True, 'reason': 'candidate_backtest_timeout', 'strategy_name': spec['strategy_name']},
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V5Short',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression='66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도,B_등락율,B_당일거래대금',
            max_consecutive_candidate_failures=3,
        ),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    assert result['actual_rowset_selection']['status'] == 'not_run'
    assert result['actual_rowset_selection']['reason'] == 'insufficient_successful_candidates'
    assert result['actual_rowset_selection']['requested_count'] == 2
    assert result['actual_rowset_selection']['successful_candidate_count'] == 1
    assert result['iteration_v5']['status'] == 'not_run'
    assert result['iteration_v5']['actual_selected_count'] == 0
```

- [ ] **Step 2: Run the v5 gate test to verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_v5_skips_actual_rowset_when_success_count_is_short -q
```

Expected now:

```text
FAILED
```

Failure should show that actual row-set selection was attempted or `actual_rowset_selection` is not the expected `not_run` payload.

- [ ] **Step 3: Gate v5 actual row-set selection**

In `cli\research_loop.py`, replace the current v5 block:

```python
    if config.iteration_v2_mode == 'best_feature_mix_v5':
        _, actual_rowset_selection = select_actual_rowset_representatives(
            ranked_candidates,
            runtime_root=Path.cwd(),
            requested_count=config.candidate_count,
        )
```

with:

```python
    if config.iteration_v2_mode == 'best_feature_mix_v5':
        successful_candidates = [
            candidate
            for candidate in ranked_candidates
            if candidate.get('status') == 'ok'
        ]
        if len(successful_candidates) < config.candidate_count:
            actual_rowset_selection = {
                'status': 'not_run',
                'reason': 'insufficient_successful_candidates',
                'requested_count': config.candidate_count,
                'successful_candidate_count': len(successful_candidates),
            }
            iteration_v5 = {
                **(iteration_v5 or {}),
                'status': 'not_run',
                'requested_count': config.candidate_count,
                'execution_count': len(specs),
                'actual_selected_count': 0,
                'row_set_identity_status': 'not_evaluated',
            }
        else:
            recorder.mark(
                'actual_rowset_selection_started',
                phase='actual_rowset_selection',
            )
            _, actual_rowset_selection = select_actual_rowset_representatives(
                ranked_candidates,
                runtime_root=Path.cwd(),
                requested_count=config.candidate_count,
            )
            ranked_candidates, best_candidate = apply_actual_rowset_selection(
                ranked_candidates,
                actual_rowset_selection,
            )
            iteration_v5 = {
                **(iteration_v5 or {}),
                'status': actual_rowset_selection.get('status'),
                'requested_count': config.candidate_count,
                'execution_count': len(specs),
                'actual_selected_count': actual_rowset_selection.get('selected_count'),
                'row_set_identity_status': actual_rowset_selection.get('row_set_identity_status'),
            }
            recorder.mark(
                'actual_rowset_selection_completed',
                phase='actual_rowset_selection',
                detail={
                    'status': actual_rowset_selection.get('status'),
                    'selected_count': actual_rowset_selection.get('selected_count'),
                    'row_set_identity_status': actual_rowset_selection.get('row_set_identity_status'),
                },
            )
```

Remove the old duplicate `apply_actual_rowset_selection(...)` and `iteration_v5 = {...}` block so it does not run twice.

- [ ] **Step 4: Run v5 gate tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_run_research_iteration_v5_skips_actual_rowset_when_success_count_is_short `
  tests/unit/test_research_loop.py::test_run_research_iteration_v5_executes_oversampled_pool_and_selects_actual_rowsets `
  -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit Task 5**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "Wide v1 v5 실제 행집합 선택 실행 조건을 고정한다" -m "성공 후보 수가 requested candidate_count보다 부족하면 actual row-set 선택을 실행하지 않고 not_run payload로 기록한다. partial run을 유효한 v5 선택 결과로 해석하지 않게 한다." -m "Constraint: v5 actual row-set selection requires enough successful candidate CSVs`nConfidence: high`nScope-risk: narrow`nTested: python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_v5_skips_actual_rowset_when_success_count_is_short tests/unit/test_research_loop.py::test_run_research_iteration_v5_executes_oversampled_pool_and_selects_actual_rowsets -q`nNot-tested: full v5 runtime rerun is a later validation task"
```

Expected: one commit is created with title `Wide v1 v5 실제 행집합 선택 실행 조건을 고정한다`.

---

## Task 6: Runtime Output Write Failure Handling

**Files:**
- Modify: `tests\unit\test_research_loop.py`
- Modify: `cli\research_loop.py`

- [ ] **Step 1: Add failing runtime write failure test**

Append this test in `tests\unit\test_research_loop.py`:

```python
def test_run_research_iteration_returns_runtime_output_write_failure(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    blocked_output = tmp_path / 'blocked.json'
    blocked_output.mkdir()
    _write_trade_csv(baseline, name='BASE')
    _patch_analysis_success(monkeypatch, expressions=['R_MFE < 0'])

    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'error',
            'phase': 'candidate_backtest_timeout',
            'message': 'timeout',
            'cleanup': {'attempted': True, 'reason': 'candidate_backtest_timeout', 'strategy_name': spec['strategy_name']},
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='WriteFail',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
            runtime_output_path=str(blocked_output),
        ),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'runtime_output_write_failure'
    assert result['runtime_output_path'] == str(blocked_output)
    assert 'runtime output write failed' in result['message']
```

- [ ] **Step 2: Run write failure test**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_returns_runtime_output_write_failure -q
```

Expected:

```text
1 passed
```

If this fails, wrap every `recorder.write(...)` call in `try/except ResearchRuntimeWriteError` and return `_runtime_write_failure(...)` with current context.

- [ ] **Step 3: Run runtime recovery tests together**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_runtime_output.py `
  tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_success `
  tests/unit/test_research_loop.py::test_run_research_iteration_continues_after_single_candidate_failure `
  tests/unit/test_research_loop.py::test_run_research_iteration_aborts_after_three_consecutive_candidate_failures `
  tests/unit/test_research_loop.py::test_run_research_iteration_v5_skips_actual_rowset_when_success_count_is_short `
  tests/unit/test_research_loop.py::test_run_research_iteration_returns_runtime_output_write_failure `
  -q
```

Expected:

```text
passed
```

- [ ] **Step 4: Commit Task 6**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "Wide v1 v5 런타임 출력 실패를 구조화한다" -m "runtime output 경로에 쓸 수 없으면 복구성 보장이 깨지므로 runtime_output_write_failure payload를 반환한다." -m "Constraint: runtime output write failure is fatal for recovery mode`nConfidence: high`nScope-risk: narrow`nTested: python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_success tests/unit/test_research_loop.py::test_run_research_iteration_continues_after_single_candidate_failure tests/unit/test_research_loop.py::test_run_research_iteration_aborts_after_three_consecutive_candidate_failures tests/unit/test_research_loop.py::test_run_research_iteration_v5_skips_actual_rowset_when_success_count_is_short tests/unit/test_research_loop.py::test_run_research_iteration_returns_runtime_output_write_failure -q`nNot-tested: real filesystem permission failure outside tmp_path"
```

Expected: one commit is created with title `Wide v1 v5 런타임 출력 실패를 구조화한다`.

---

## Task 7: Pre-Candidate Failure Runtime Output

**Files:**
- Modify: `tests\unit\test_research_loop.py`
- Modify: `cli\research_loop.py`

- [ ] **Step 1: Add failing analysis failure runtime output test**

Append this test in `tests\unit\test_research_loop.py`:

```python
def test_run_research_iteration_writes_runtime_output_on_analysis_failure(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    runtime_output = tmp_path / 'runtime.json'
    _write_trade_csv(baseline, name='BASE')
    monkeypatch.setattr(
        research_loop,
        'analyze_result_csv',
        lambda *args, **kwargs: {'status': 'error', 'message': 'analysis failed'},
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='AnalysisRuntimeFail',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
            runtime_output_path=str(runtime_output),
        ),
        DummyController(None),
    )

    data = json.loads(runtime_output.read_text(encoding='utf-8'))
    assert result['status'] == 'error'
    assert result['phase'] == 'analysis'
    assert data['status'] == 'error'
    assert data['phase'] == 'analysis'
    assert data['analysis_result']['message'] == 'analysis failed'
    assert data['checkpoint_summary']['last_checkpoint'] == 'iteration_aborted'
    assert data['failure_policy']['total_candidate_failures'] == 0
```

- [ ] **Step 2: Add failing baseline failure runtime output test**

Append this test in `tests\unit\test_research_loop.py`:

```python
def test_run_research_iteration_writes_runtime_output_on_baseline_failure(tmp_path):
    runtime_output = tmp_path / 'runtime.json'
    controller = DummyController(None, status='error', message='baseline failed')

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='BaselineRuntimeFail',
            baseline_csv=None,
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
            runtime_output_path=str(runtime_output),
        ),
        controller,
    )

    data = json.loads(runtime_output.read_text(encoding='utf-8'))
    assert result['status'] == 'error'
    assert result['phase'] == 'baseline_run'
    assert data['status'] == 'error'
    assert data['phase'] == 'baseline_run'
    assert data['run_result']['message'] == 'baseline failed'
    assert data['checkpoint_summary']['last_checkpoint'] == 'iteration_aborted'
    assert data['failure_policy']['total_candidate_failures'] == 0
```

- [ ] **Step 3: Run pre-candidate tests to verify failure**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_analysis_failure `
  tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_baseline_failure `
  -q
```

Expected now:

```text
FAILED
```

The failure should show that `runtime.json` does not exist.

- [ ] **Step 4: Add a runtime finalize helper**

Add this helper above `run_research_iteration()` in `cli\research_loop.py`:

```python
def _finalize_research_runtime_result(
    config: ResearchLoopConfig,
    recorder: ResearchRuntimeRecorder,
    result_payload: dict,
    failure_policy: dict,
) -> dict:
    result_payload = {
        **result_payload,
        'failure_policy': failure_policy,
    }
    result_payload = recorder.decorate(result_payload)
    try:
        recorder.write(result_payload)
    except ResearchRuntimeWriteError as exc:
        return _build_result(config, _runtime_write_failure(
            config.runtime_output_path,
            exc,
            strategy_name=result_payload.get('strategy_name', config.name),
            config=result_payload.get('config', asdict(config)),
            failure_policy=failure_policy,
            candidates=result_payload.get('candidates', []),
        ))
    return _build_result(config, result_payload)
```

- [ ] **Step 5: Use helper for baseline failure**

Replace the first `baseline_result.get('status') not in ('ok', 'success')` return in `run_research_iteration()` with:

```python
            recorder.mark(
                'iteration_aborted',
                phase='baseline_run',
                message=baseline_result.get('message', 'baseline run failed'),
            )
            return _finalize_research_runtime_result(
                config,
                recorder,
                _error(
                    'baseline_run',
                    baseline_result.get('message', 'baseline run failed'),
                    strategy_name=config.name,
                    config=asdict(config),
                    run_result=baseline_result,
                    candidate_specs=[],
                    candidates=[],
                    best_candidate=None,
                    actual_rowset_selection=None,
                    cleanup_summary={'attempted_count': 0, 'deleted_count': 0, 'kept_count': 0, 'failed_count': 0, 'items': []},
                ),
                failure_policy,
            )
```

Replace the next baseline CSV missing return with the same pattern, using:

```python
                    'baseline_run',
                    'baseline run did not return csv_path',
                    strategy_name=config.name,
                    config=asdict(config),
                    run_result=baseline_result,
                    candidate_specs=[],
                    candidates=[],
                    best_candidate=None,
                    actual_rowset_selection=None,
                    cleanup_summary={'attempted_count': 0, 'deleted_count': 0, 'kept_count': 0, 'failed_count': 0, 'items': []},
```

- [ ] **Step 6: Use helper for analysis failure**

Replace the `analysis_result.get('status') != 'ok'` return in `run_research_iteration()` with:

```python
    if analysis_result.get('status') != 'ok':
        recorder.mark(
            'iteration_aborted',
            phase='analysis',
            message=analysis_result.get('message', 'analysis failed'),
        )
        return _finalize_research_runtime_result(
            config,
            recorder,
            _error(
                'analysis',
                analysis_result.get('message', 'analysis failed'),
                strategy_name=config.name,
                config=asdict(config),
                baseline_csv=baseline_csv,
                baseline_result=baseline_result,
                analysis_result=analysis_result,
                iteration_plan=iteration_plan,
                candidate_specs=[],
                candidates=[],
                best_candidate=None,
                actual_rowset_selection=None,
                cleanup_summary={'attempted_count': 0, 'deleted_count': 0, 'kept_count': 0, 'failed_count': 0, 'items': []},
            ),
            failure_policy,
        )
```

Keep the existing `analysis_result` call unchanged.

- [ ] **Step 7: Use helper for retention and expression pre-candidate failures**

For these pre-candidate returns in `run_research_iteration()`, mark `iteration_aborted` and return through `_finalize_research_runtime_result(...)` with existing payload fields preserved:

- `no_expressions`
- `insufficient_expressions`
- `retention_selection.get('status') != 'ok'`
- `len(selected_candidates) < config.candidate_count`

Use these exact phase and message rules:

- `no_expressions`
  - phase: `no_expressions`
  - message: `expression_result.get('message', 'no candidate expressions generated')`
  - preserve: `baseline_csv`, `baseline_result`, `analysis_result`, `expression_result`, `iteration_plan`
- `insufficient_expressions`
  - phase: `insufficient_expressions`
  - message: `f"candidate_count={config.candidate_count} requested but only {len(expressions)} expressions generated"`
  - preserve: `requested_candidate_count=config.candidate_count`, `expression_count=len(expressions)`
- retention selection error
  - phase: `retention_selection.get('phase', 'insufficient_retention_candidates')`
  - message: `retention_selection.get('message', 'insufficient retention-aware candidates')`
  - preserve: `retention_selection`, `retention_candidates`, and iteration metadata
- selected candidate shortfall
  - phase: `insufficient_retention_candidates`
  - message: `f"candidate_count={config.candidate_count} requested but only {len(selected_candidates)} candidates selected after retention filtering"`
  - preserve: `requested_candidate_count=config.candidate_count`, `selected_candidate_count=len(selected_candidates)`

For the `no_expressions` branch, the replacement body is:

```python
        recorder.mark(
            'iteration_aborted',
            phase='no_expressions',
            message=expression_result.get('message', 'no candidate expressions generated'),
        )
        return _finalize_research_runtime_result(
            config,
            recorder,
            _error(
                'no_expressions',
                expression_result.get('message', 'no candidate expressions generated'),
                strategy_name=config.name,
                config=asdict(config),
                baseline_csv=baseline_csv,
                baseline_result=baseline_result,
                analysis_result=analysis_result,
                expression_result=expression_result,
                iteration_plan=iteration_plan,
                candidate_specs=[],
                candidates=[],
                best_candidate=None,
                actual_rowset_selection=None,
                cleanup_summary={'attempted_count': 0, 'deleted_count': 0, 'kept_count': 0, 'failed_count': 0, 'items': []},
            ),
            failure_policy,
        )
```

For the other three branches, use the same wrapper and the exact phase, message, and preserved diagnostic fields listed above. Do not remove existing diagnostic keys from those error payloads.

- [ ] **Step 8: Use helper for existing final writes**

Replace direct final `recorder.write(...)` blocks from Tasks 3 and 4 with calls to `_finalize_research_runtime_result(...)` so success, candidate abort, and write failure paths use one implementation.

For the normal final return, use:

```python
    return _finalize_research_runtime_result(
        config,
        recorder,
        result_payload,
        failure_policy,
    )
```

For the consecutive failure abort return, use:

```python
        return _finalize_research_runtime_result(
            config,
            recorder,
            result_payload,
            failure_policy,
        )
```

- [ ] **Step 9: Run pre-candidate failure tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_analysis_failure `
  tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_baseline_failure `
  tests/unit/test_research_loop.py::test_run_research_iteration_rejects_insufficient_expressions `
  tests/unit/test_research_loop.py::test_run_research_iteration_returns_insufficient_retention_when_fallback_disabled `
  tests/unit/test_research_loop.py::test_run_research_iteration_rejects_retention_selection_shortfall `
  -q
```

Expected:

```text
5 passed
```

- [ ] **Step 10: Commit Task 7**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "Wide v1 v5 후보 전 실패 런타임을 저장한다" -m "baseline, analysis, expression, retention 단계에서 candidate 실행 전 실패가 발생해도 runtime output JSON에 중단 사유와 checkpoint를 남긴다." -m "Constraint: pre-candidate failure branches must preserve existing diagnostic fields`nConfidence: medium`nScope-risk: moderate`nTested: python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_analysis_failure tests/unit/test_research_loop.py::test_run_research_iteration_writes_runtime_output_on_baseline_failure tests/unit/test_research_loop.py::test_run_research_iteration_rejects_insufficient_expressions tests/unit/test_research_loop.py::test_run_research_iteration_returns_insufficient_retention_when_fallback_disabled tests/unit/test_research_loop.py::test_run_research_iteration_rejects_retention_selection_shortfall -q`nNot-tested: actual long v5 runtime failure is validated in the next rerun branch"
```

Expected: one commit is created with title `Wide v1 v5 후보 전 실패 런타임을 저장한다`.

---

## Task 8: PR Report and Verification

**Files:**
- Create: `docs\pr\2026-04-25_wide_v1_v5_runtime_failure_recovery_pr.md`
- Test: `tests\unit\test_research_runtime_output.py`
- Test: `tests\unit\test_research_loop.py`
- Test: `tests\unit\test_subcommands.py`
- Test: `tests\unit\test_research_iteration_v5.py`
- Test: `tests\unit\test_wide_v1_v5_analysis.py`

- [ ] **Step 1: Write Korean PR report**

Create `docs\pr\2026-04-25_wide_v1_v5_runtime_failure_recovery_pr.md`:

```markdown
# PR 보고서: Wide v1 v5 runtime failure recovery

## 1. 목적

Wide v1 v5 `candidate_count=10` 실제 실행이 runtime JSON 없이 정지한 문제를 해결하기 위해, `discovery research` 연구 루프에 복구 가능한 runtime output과 candidate checkpoint 정책을 추가한다.

## 2. 전체 방향

이번 작업은 v6 조건식 확장이 아니라 v5 실행 안정성 보강이다.

```text
v4 proxy row-set diversity
  -> v5 actual row-set validation
  -> runtime failure 확인
  -> runtime recovery 보강
  -> v5 재실행
  -> promote/WFO 판단
```

## 3. 현재 구현 범위

- `discovery research --runtime-output` 추가
- `--max-consecutive-candidate-failures` 추가
- candidate checkpoint 저장
- 개별 candidate 실패 후 다음 후보 계속 실행
- 연속 실패 3회 시 구조화된 중단
- 성공 후보 부족 시 actual row-set 선택 미실행
- runtime output write failure 구조화

## 4. 제외 범위

- `cli/runner.py` 대규모 multiprocessing cleanup 리팩토링
- GUI 변경
- v6 조건식 확장
- promote/WFO 실행
- 실제 v5 full rerun

## 5. 퀀트 트레이더 관점 검토

partial candidate CSV는 성과 검증 근거가 아니다. 이번 변경은 성공/실패 후보와 actual row-set 미실행 사유를 JSON으로 남겨, 불완전한 실험 결과가 promote/WFO 판단으로 넘어가지 않게 한다.

## 6. CLI 개발 전문가 관점 검토

stdout capture 의존을 줄이고 runtime output file을 명시적으로 저장한다. candidate 실패를 exception 흐름이 아니라 data item으로 보존해 장시간 실행을 진단 가능하게 만든다.

## 7. 전체 프로그램 관점 검토

STOM 백테스트 runner의 핵심 multiprocessing 구조를 이번 PR에서 크게 바꾸지 않는다. 연구 루프 레벨에 복구 계층을 추가해 회귀 위험을 제한한다.

## 8. 검증

```powershell
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
```

## 9. 다음 단계

다음 추천 명령:

```text
$writing-plans Wide v1 v5 runtime recovery 적용 후 candidate_count=10 재실행 검증 계획 작성
```
```

- [ ] **Step 2: Run focused unit tests**

Run:

```powershell
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
```

Expected:

```text
passed
```

There must be zero failures.

- [ ] **Step 3: Run whitespace check**

Run:

```powershell
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
```

Expected:

```text
No output.
```

- [ ] **Step 4: Check staged scope before commit**

Run:

```powershell
git status --short --untracked-files=all
```

Expected tracked or untracked implementation files:

```text
cli/research_runtime_output.py
cli/research_loop.py
cli/subcommands.py
tests/unit/test_research_runtime_output.py
tests/unit/test_research_loop.py
tests/unit/test_subcommands.py
docs/pr/2026-04-25_wide_v1_v5_runtime_failure_recovery_pr.md
```

Existing untracked `backtest/graph/*.png` files may remain. Do not stage them.

- [ ] **Step 5: Commit PR report if not already committed**

If the PR report was not included in an earlier task commit, run:

```powershell
git add docs/pr/2026-04-25_wide_v1_v5_runtime_failure_recovery_pr.md
git commit -m "Wide v1 v5 런타임 복구 PR 보고서를 작성한다" -m "runtime output, checkpoint, 연속 실패 중단 정책의 구현 범위와 검증 결과를 한글 PR 보고서로 기록한다." -m "Confidence: high`nScope-risk: narrow`nTested: python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q`nTested: git diff --check --ignore-cr-at-eol`nNot-tested: 실제 v5 재실행은 다음 계획에서 수행한다"
```

Expected: one commit is created with title `Wide v1 v5 런타임 복구 PR 보고서를 작성한다`.

---

## Task 9: Merge Handoff

**Files:**
- No new file changes.

- [ ] **Step 1: Verify branch status**

Run:

```powershell
git status --short --branch --untracked-files=no
git log -1 --format="%h %s"
```

Expected:

```text
## feature/wide-v1-v5-runtime-failure-recovery
latest commit title starts with `Wide v1 v5`
```

No tracked modified files.

- [ ] **Step 2: Merge to `STOM_Version_2U_C` with a merge point**

Run:

```powershell
git checkout STOM_Version_2U_C
git merge --no-ff feature/wide-v1-v5-runtime-failure-recovery -m "Wide v1 v5 런타임 실패 복구를 병합한다" -m "research loop checkpoint와 runtime output을 2U_C 기준선에 merge point로 남긴다. v5 actual row-set 재실행 전 후보 실패를 복구 가능한 JSON으로 기록할 수 있게 한다." -m "Constraint: 2U_C 기준선은 feature branch merge point로 연구 진행 내역을 추적해야 한다`nRejected: runner 대규모 cleanup을 같은 PR에 포함 | 영향 범위가 넓고 이번 목표는 연구 루프 복구성이다`nConfidence: high`nScope-risk: moderate`nTested: python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q`nTested: git diff --check --ignore-cr-at-eol`nNot-tested: 실제 v5 candidate_count=10 재실행은 다음 브랜치에서 수행한다"
```

Expected:

```text
Merge made by the 'ort' strategy.
```

- [ ] **Step 3: Verify merged baseline**

Run:

```powershell
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
git status --short --branch --untracked-files=no
```

Expected:

```text
passed
No diff-check output.
## STOM_Version_2U_C...
```

No tracked modified files.

- [ ] **Step 4: Create next validation branch**

Run:

```powershell
git checkout -b feature/wide-v1-v5-runtime-recovery-rerun-validation
```

Expected:

```text
Switched to a new branch 'feature/wide-v1-v5-runtime-recovery-rerun-validation'
```

- [ ] **Step 5: Report next command**

Report this next command:

```text
$writing-plans Wide v1 v5 runtime recovery 적용 후 candidate_count=10 재실행 검증 계획 작성
```

---

## Self-Review Checklist

- Spec coverage: Tasks cover runtime output, checkpoints, individual failure continuation, consecutive failure abort at 3, v5 actual row-set gate, write failure handling, pre-candidate analysis failure output, tests, PR report, and merge handoff.
- Scope: Plan stays in `discovery research`, `research_loop`, and unit tests. `cli/runner.py` is intentionally excluded.
- Placeholder scan: The plan contains no undefined future implementation placeholders.
- Type consistency: Config fields are `runtime_output_path` and `max_consecutive_candidate_failures`; CLI parsed fields use the same names; runtime JSON uses `failure_policy`, `checkpoints`, and `checkpoint_summary`.
- Staging policy: All git commands stage explicit files only. No `git add -A` is used.
