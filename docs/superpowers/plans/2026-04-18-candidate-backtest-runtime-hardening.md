# Candidate Backtest Runtime Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `discovery research --run-candidate` safe for repeated research by adding candidate-only planning, date/timeout controls, failed-candidate cleanup, and runtime reporting.

**Architecture:** Keep core backtest/runner behavior unchanged. Extend the existing research loop as a coordinator: build a candidate execution plan before saving, apply candidate-only run overrides to the candidate backtest config, clean failed candidates by default, and surface runtime/cleanup details through the research report and CLI.

**Tech Stack:** Python 3.11, existing STOM CLI modules, `cli.research_loop`, `cli.research_report`, `cli.subcommands`, pytest.

---

## Scope Check

This plan hardens a single candidate execution path. It does not implement multi-candidate iteration yet.

Out of scope:

- Batch candidate generation.
- Full backtest iteration loop.
- Opportunity-universe logging.
- AI/API candidate generation.
- Core `backtest/`, `trade/`, GUI, or `cli.runner.run_backtest()` changes.

## File Structure

- Modify `cli/research_loop.py`
  - Add candidate runtime config fields.
  - Build `candidate_plan`.
  - Apply candidate date/timeout overrides.
  - Clean failed candidate strategies by default.
  - Classify timeout phase.

- Modify `cli/research_report.py`
  - Add `candidate_plan` and `cleanup` fields.
  - Render `## Candidate Runtime`.

- Modify `cli/subcommands.py`
  - Add candidate runtime CLI options.
  - Pass them into `research_strategy_once()`.

- Modify tests:
  - `tests/unit/test_research_loop.py`
  - `tests/unit/test_research_report.py`
  - `tests/unit/test_subcommands.py`

- Add update log:
  - `docs/update_log/2026-04-18_candidate_backtest_runtime_hardening.md`

---

### Task 1: Candidate Runtime Config And Plan

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_research_loop.py`:

```python
def test_research_loop_config_has_candidate_runtime_fields():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'candidate_start_date' in names
    assert 'candidate_end_date' in names
    assert 'candidate_timeout' in names
    assert 'candidate_plan_only' in names
    assert 'keep_failed_candidate' in names


def test_research_preview_includes_candidate_plan(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(
            name='PlanPreview',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            sell_strategy='BaseSell',
            start_date=20250101,
            end_date=20250131,
            candidate_start_date=20250102,
            candidate_end_date=20250103,
            candidate_timeout=300,
            run_candidate=False,
        ),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    plan = result['candidate_plan']
    assert plan['strategy_name'] == 'PlanPreview'
    assert plan['base_buy_strategy'] == 'BaseBuy'
    assert plan['sell_strategy'] == 'BaseSell'
    assert plan['expression'] == '체결강도 < 90'
    assert plan['candidate_start_date'] == 20250102
    assert plan['candidate_end_date'] == 20250103
    assert plan['candidate_timeout'] == 300
    assert plan['will_save_strategy'] is False
    assert plan['will_run_backtest'] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_config_has_candidate_runtime_fields tests/unit/test_research_loop.py::test_research_preview_includes_candidate_plan -q
```

Expected:

```text
TypeError: ResearchLoopConfig.__init__() got an unexpected keyword argument 'candidate_start_date'
```

- [ ] **Step 3: Implement config fields and candidate plan helper**

In `cli/research_loop.py`, add fields to `ResearchLoopConfig`:

```python
    candidate_start_date: int | None = None
    candidate_end_date: int | None = None
    candidate_timeout: int | None = None
    candidate_plan_only: bool = False
    keep_failed_candidate: bool = False
```

Add helpers:

```python
def _candidate_start_date(config: ResearchLoopConfig) -> int:
    return config.candidate_start_date or config.start_date


def _candidate_end_date(config: ResearchLoopConfig) -> int:
    return config.candidate_end_date or config.end_date


def _build_candidate_plan(config: ResearchLoopConfig, candidate: dict) -> dict:
    """Build a stable plan describing candidate execution before side effects."""
    will_save = bool(config.run_candidate and not config.candidate_plan_only)
    return {
        'strategy_name': config.name,
        'base_buy_strategy': config.base_buy_strategy,
        'sell_strategy': config.sell_strategy,
        'expression': candidate.get('expression'),
        'expressions': candidate.get('expressions', []),
        'candidate_start_date': _candidate_start_date(config),
        'candidate_end_date': _candidate_end_date(config),
        'candidate_timeout': config.candidate_timeout,
        'will_save_strategy': will_save,
        'will_run_backtest': will_save,
        'keep_failed_candidate': config.keep_failed_candidate,
    }
```

After `candidate = {...}` in `run_research_once()`, add:

```python
    candidate_plan = _build_candidate_plan(config, candidate)
```

Include `candidate_plan` in the preview result:

```python
            'candidate_plan': candidate_plan,
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_config_has_candidate_runtime_fields tests/unit/test_research_loop.py::test_research_preview_includes_candidate_plan -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "후보 백테스트 실행 계획을 만든다" -m "research 루프가 후보 전략 저장 전에 실행 범위와 timeout, 실행 여부를 candidate_plan으로 반환하도록 했다.

Constraint: 후보 실행 계획은 strategy.db 쓰기 전에 생성되어야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_loop.py -q"
```

---

### Task 6: Candidate Runtime Report

**Files:**
- Modify: `cli/research_report.py`
- Modify: `tests/unit/test_research_report.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_research_report.py`:

```python
def test_build_research_report_includes_candidate_plan_and_cleanup():
    result = _result()
    result['candidate_plan'] = {'strategy_name': 'AutoResearch', 'candidate_timeout': 300}
    result['cleanup'] = {'attempted': True, 'status': 'ok', 'action': 'deleted'}

    report = build_research_report(result, strategy_name='AutoResearch')

    assert report['candidate_plan']['candidate_timeout'] == 300
    assert report['cleanup']['action'] == 'deleted'


def test_render_research_report_markdown_contains_candidate_runtime():
    result = _result()
    result['candidate_plan'] = {
        'strategy_name': 'AutoResearch',
        'candidate_start_date': 20250101,
        'candidate_end_date': 20250102,
        'candidate_timeout': 300,
        'will_save_strategy': True,
        'will_run_backtest': True,
    }
    result['cleanup'] = {'attempted': True, 'status': 'ok', 'action': 'deleted'}

    markdown = render_research_report_markdown(build_research_report(result, strategy_name='AutoResearch'))

    assert '## Candidate Runtime' in markdown
    assert '후보 백테스트 시작일' in markdown
    assert 'candidate_timeout' in markdown
    assert 'cleanup' in markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py::test_build_research_report_includes_candidate_plan_and_cleanup tests/unit/test_research_report.py::test_render_research_report_markdown_contains_candidate_runtime -q
```

Expected:

```text
FAILED because report lacks candidate_plan/cleanup/runtime section
```

- [ ] **Step 3: Add report fields and Markdown section**

In `build_research_report()`, add:

```python
        'candidate_plan': result.get('candidate_plan'),
        'cleanup': result.get('cleanup'),
```

In `render_research_report_markdown()`, add a section after Candidate:

```python
    lines.extend(['', '## Candidate Runtime'])
    candidate_plan = report.get('candidate_plan') or {}
    cleanup = report.get('cleanup') or {}
    if candidate_plan:
        lines.append(f"- 후보 백테스트 실행 여부: {candidate_plan.get('will_run_backtest')}")
        lines.append(f"- 후보 백테스트 시작일: {candidate_plan.get('candidate_start_date')}")
        lines.append(f"- 후보 백테스트 종료일: {candidate_plan.get('candidate_end_date')}")
        lines.append(f"- candidate_timeout: {candidate_plan.get('candidate_timeout')}")
        lines.append(f"- 후보 전략 저장 여부: {candidate_plan.get('will_save_strategy')}")
    else:
        lines.append("- none")
    if cleanup:
        lines.append(f"- cleanup attempted: {cleanup.get('attempted')}")
        lines.append(f"- cleanup status: {cleanup.get('status')}")
        lines.append(f"- cleanup action: {cleanup.get('action')}")
        if cleanup.get('message'):
            lines.append(f"- cleanup message: {cleanup.get('message')}")
```

- [ ] **Step 4: Run report tests**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py -q
```

Expected:

```text
all tests in test_research_report.py passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_report.py tests/unit/test_research_report.py
git commit -m "후보 실행 정보를 연구 리포트에 표시한다" -m "candidate_plan과 cleanup 결과를 연구 리포트에 포함해 후보 백테스트 실행 범위와 실패 정리 상태를 확인할 수 있게 했다.

Constraint: 반복 연구의 실패 원인을 리포트로 추적할 수 있어야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_report.py -q"
```

---

### Task 7: Candidate Runtime CLI Options

**Files:**
- Modify: `cli/subcommands.py`
- Modify: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_subcommands.py`:

```python
def test_discovery_research_parser_accepts_candidate_runtime_options():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'AutoResearchRuntime',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--run-candidate',
        '--candidate-start', '20250102',
        '--candidate-end', '20250103',
        '--candidate-timeout', '300',
        '--candidate-plan-only',
        '--keep-failed-candidate',
    ])

    assert args.candidate_start == 20250102
    assert args.candidate_end == 20250103
    assert args.candidate_timeout == 300
    assert args.candidate_plan_only is True
    assert args.keep_failed_candidate is True


def test_discovery_research_handler_passes_candidate_runtime_options():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'report': {'strategy_name': 'AutoResearchRuntime'}}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'AutoResearchRuntime',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--candidate-start', '20250102',
            '--candidate-end', '20250103',
            '--candidate-timeout', '300',
            '--candidate-plan-only',
            '--keep-failed-candidate',
        ])

    assert exit_code == 0
    payload = mock.call_args.args[0]
    assert payload['candidate_start_date'] == 20250102
    assert payload['candidate_end_date'] == 20250103
    assert payload['candidate_timeout'] == 300
    assert payload['candidate_plan_only'] is True
    assert payload['keep_failed_candidate'] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_candidate_runtime_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_candidate_runtime_options -q
```

Expected:

```text
SystemExit: 2
```

- [ ] **Step 3: Add CLI args and handler payload**

In `cli/subcommands.py`, add to `disc_research`:

```python
    disc_research.add_argument('--candidate-start', type=int)
    disc_research.add_argument('--candidate-end', type=int)
    disc_research.add_argument('--candidate-timeout', type=int)
    disc_research.add_argument('--candidate-plan-only', action='store_true', default=False)
    disc_research.add_argument('--keep-failed-candidate', action='store_true', default=False)
```

Add to research handler payload:

```python
            'candidate_start_date': parsed.candidate_start,
            'candidate_end_date': parsed.candidate_end,
            'candidate_timeout': parsed.candidate_timeout,
            'candidate_plan_only': parsed.candidate_plan_only,
            'keep_failed_candidate': parsed.keep_failed_candidate,
```

- [ ] **Step 4: Run subcommand tests and help**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py -q
python stom_backtest.py discovery research --help
```

Expected:

```text
tests pass
help shows --candidate-start, --candidate-end, --candidate-timeout, --candidate-plan-only, --keep-failed-candidate
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/subcommands.py tests/unit/test_subcommands.py
git commit -m "후보 백테스트 실행 옵션을 CLI에 추가한다" -m "discovery research에서 후보 전용 기간, timeout, 계획 전용 모드, 실패 후보 보존 옵션을 전달하게 했다.

Constraint: 후보 백테스트 실행 제어는 research 명령의 책임이어야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_subcommands.py -q"
```

---

### Task 8: Integration Verification And Update Log

**Files:**
- Create: `docs/update_log/2026-04-18_candidate_backtest_runtime_hardening.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 2: Run broader research tests**

Run:

```powershell
python -m pytest tests/unit/test_research_metrics.py tests/unit/test_research_segments.py tests/unit/test_research_candidates.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py tests/unit/test_research_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 3: Run full unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
all unit tests passed
```

- [ ] **Step 4: Run non-release sync verification**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 5: Create update log**

Create `docs/update_log/2026-04-18_candidate_backtest_runtime_hardening.md`:

```markdown
# 2026-04-18 후보 백테스트 런타임 안정화

## 개요

`discovery research --run-candidate` 후보 백테스트가 timeout되거나 실패해도 연구 루프가 안전하게 복구되도록 실행 계획, 후보 전용 기간/timeout, 실패 후보 cleanup을 추가했다.

## 변경 사항

- 후보 실행 계획 `candidate_plan` 추가
- `--candidate-start`, `--candidate-end` 추가
- `--candidate-timeout` 추가
- `--candidate-plan-only` 추가
- `--keep-failed-candidate` 추가
- 실패/timeout 후보 전략 기본 삭제
- cleanup 결과를 JSON/Markdown 리포트에 포함

## 검증

- `python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q`
- `python -m pytest tests/unit/ -q`
- `python scripts/verify_nonrelease_sync.py`

## 남은 리스크

- 후보 백테스트 자체가 여전히 느릴 수 있다.
- 너무 짧은 candidate 기간은 통계적으로 의미가 약할 수 있다.
- 다음 단계는 후보 N개 반복 실행과 최고 후보 선택이다.
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add docs/update_log/2026-04-18_candidate_backtest_runtime_hardening.md
git commit -m "후보 백테스트 런타임 안정화 기록을 남긴다" -m "후보 백테스트 실행 제어와 실패 후보 cleanup의 변경 사항, 검증 결과, 남은 리스크를 업데이트 로그로 기록했다.

Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/ -q; python scripts/verify_nonrelease_sync.py"
```

---

## Self-Review

Spec coverage:

- Candidate runtime config: Task 1.
- Plan-only behavior: Task 2.
- Candidate date/timeout overrides: Task 3.
- Failed/timed-out cleanup: Task 4.
- Missing CSV and comparison cleanup: Task 5.
- Report runtime section: Task 6.
- CLI options: Task 7.
- Verification and update log: Task 8.

Known boundaries:

- This plan does not implement multi-candidate iteration.
- This plan does not change `cli.runner.run_backtest()`.
- This plan does not alter WFO or promote flows.

Completion scan:

- Every code task includes concrete tests, code changes, commands, expected results, and commit commands.


---

### Task 4: Failed Candidate Cleanup

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_research_loop.py`:

```python
def test_candidate_backtest_timeout_cleans_candidate_by_default(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append((db_path, name, strategy_type)) or {'status': 'ok', 'name': name, 'action': 'deleted'},
    )

    result = run_research_once(
        ResearchLoopConfig(name='TimeoutCandidate', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(baseline), status='error', message='백테스트 시간 초과 (300초)'),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_backtest_timeout'
    assert result['cleanup']['attempted'] is True
    assert result['cleanup']['status'] == 'ok'
    assert cleanup_calls[0][1] == 'TimeoutCandidate'


def test_keep_failed_candidate_skips_cleanup(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *args, **kwargs: cleanup_calls.append(args) or {'status': 'ok'},
    )

    result = run_research_once(
        ResearchLoopConfig(
            name='KeepFailed',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            keep_failed_candidate=True,
        ),
        DummyController(str(baseline), status='error'),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_backtest'
    assert result['cleanup']['attempted'] is False
    assert result['cleanup']['reason'] == 'keep_failed_candidate'
    assert cleanup_calls == []
```

Update `DummyController` so it accepts a custom message:

```python
class DummyController:
    def __init__(self, candidate_csv, status='success', message='candidate failed'):
        self.candidate_csv = candidate_csv
        self.status = status
        self.message = message
        self.runs = []
```

and uses `self.message`.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_candidate_backtest_timeout_cleans_candidate_by_default tests/unit/test_research_loop.py::test_keep_failed_candidate_skips_cleanup -q
```

Expected:

```text
FAILED because cleanup is not implemented and timeout phase is not split
```

- [ ] **Step 3: Implement cleanup helpers**

In `cli/research_loop.py`, import:

```python
from cli.strategy_generator import delete_strategy_from_db, generate_buy_filter_strategy, save_strategy_to_db
```

Add helpers:

```python
def _candidate_failure_phase(candidate_result: dict) -> str:
    message = str(candidate_result.get('message') or '')
    if '시간 초과' in message or 'timeout' in message.lower():
        return 'candidate_backtest_timeout'
    return 'candidate_backtest'


def _cleanup_candidate_strategy(config: ResearchLoopConfig, reason: str) -> dict:
    """Delete failed candidate strategy unless the user requested preservation."""
    if config.keep_failed_candidate:
        return {
            'attempted': False,
            'reason': 'keep_failed_candidate',
            'strategy_name': config.name,
        }
    result = delete_strategy_from_db(DB_STRATEGY, config.name, 'buy')
    return {
        'attempted': True,
        'reason': reason,
        'strategy_name': config.name,
        'status': result.get('status'),
        'message': result.get('message'),
        'action': result.get('action'),
    }
```

When candidate backtest returns non-ok, use:

```python
        phase = _candidate_failure_phase(candidate_result)
        cleanup = _cleanup_candidate_strategy(config, phase)
        return _error(
            phase,
            candidate_result.get('message', 'candidate run failed'),
            baseline_csv=baseline_csv,
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            run_result=candidate_result,
        )
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_candidate_backtest_timeout_cleans_candidate_by_default tests/unit/test_research_loop.py::test_keep_failed_candidate_skips_cleanup tests/unit/test_research_loop.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "실패 후보 전략을 기본 정리한다" -m "후보 백테스트 실패나 timeout 시 후보 전략을 기본 삭제하고 cleanup 결과를 구조화해 반환하게 했다.

Constraint: 반복 연구에서 실패 후보가 strategy.db에 누적되면 안 됨
Confidence: high
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_loop.py -q"
```

---

### Task 5: Cleanup For Missing CSV And Comparison Failure

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_research_loop.py`:

```python
def test_candidate_csv_missing_cleans_candidate(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'},
    )

    result = run_research_once(
        ResearchLoopConfig(name='MissingCsvCleanup', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_csv_missing'
    assert result['cleanup']['attempted'] is True
    assert cleanup_calls == ['MissingCsvCleanup']


def test_comparison_failure_cleans_candidate(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'compare_trade_sets',
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('compare failed')),
    )
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'},
    )

    result = run_research_once(
        ResearchLoopConfig(name='CompareCleanup', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(candidate)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'comparison'
    assert result['cleanup']['attempted'] is True
    assert cleanup_calls == ['CompareCleanup']
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_candidate_csv_missing_cleans_candidate tests/unit/test_research_loop.py::test_comparison_failure_cleans_candidate -q
```

Expected:

```text
FAILED because cleanup is not included for these failure paths
```

- [ ] **Step 3: Add cleanup to missing CSV and comparison failure paths**

When candidate CSV is missing or path does not exist, add:

```python
cleanup = _cleanup_candidate_strategy(config, 'candidate_csv_missing')
```

and include `cleanup=cleanup` in `_error(...)`.

When comparison fails, add:

```python
cleanup = _cleanup_candidate_strategy(config, 'comparison')
```

and include it in the error payload.

Successful comparison should still not cleanup.

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_candidate_csv_missing_cleans_candidate tests/unit/test_research_loop.py::test_comparison_failure_cleans_candidate tests/unit/test_research_loop.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "후보 CSV와 비교 실패도 정리한다" -m "후보 백테스트 이후 CSV 누락이나 비교 실패가 발생해도 실패 후보 전략을 기본 삭제하도록 cleanup 경로를 확장했다.

Constraint: 후보 저장 이후 어떤 실패 경로에서도 strategy.db 잔여물이 남지 않아야 함
Confidence: high
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_loop.py -q"
```


---

### Task 2: Candidate Plan Only Mode

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing test**

Add to `tests/unit/test_research_loop.py`:

```python
def test_candidate_plan_only_does_not_save_or_run(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    def fail_save(*args, **kwargs):
        raise AssertionError('save should not be attempted')

    monkeypatch.setattr(research_loop, 'save_strategy_to_db', fail_save)

    result = run_research_once(
        ResearchLoopConfig(
            name='PlanOnly',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=True,
            candidate_plan_only=True,
        ),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    assert result['phase'] == 'candidate_plan'
    assert result['candidate_plan']['will_save_strategy'] is False
    assert result['candidate_plan']['will_run_backtest'] is False
    assert result['candidate_csv'] is None
    assert result['comparison'] is None
    assert result['promotion'] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_candidate_plan_only_does_not_save_or_run -q
```

Expected:

```text
FAILED because candidate save/backtest is still attempted or phase is missing
```

- [ ] **Step 3: Implement plan-only branch**

In `run_research_once()`, after `candidate_plan = ...`, add before the existing `if not config.run_candidate` block:

```python
    if config.candidate_plan_only:
        return _build_result(config, {
            'status': 'ok',
            'phase': 'candidate_plan',
            'strategy_name': config.name,
            'config': asdict(config),
            'baseline_csv': baseline_csv,
            'candidate_csv': None,
            'baseline_result': baseline_result,
            'analysis_result': analysis_result,
            'expression_result': expression_result,
            'candidate': candidate,
            'candidate_plan': candidate_plan,
            'comparison': None,
            'promotion': None,
        })
```

Also ensure the regular `not config.run_candidate` preview result includes `candidate_plan`.

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_candidate_plan_only_does_not_save_or_run tests/unit/test_research_loop.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "후보 백테스트 계획 전용 모드를 추가한다" -m "candidate_plan_only 설정으로 후보 전략 저장과 백테스트 없이 후보 실행 계획만 반환하게 했다.

Constraint: 실제 후보 백테스트 전에 실행 범위와 조건식을 확인할 수 있어야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_loop.py -q"
```

---

### Task 3: Candidate Backtest Overrides

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing test**

Add to `tests/unit/test_research_loop.py`:

```python
def test_candidate_runtime_overrides_candidate_backtest_config(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    controller = DummyController(str(candidate))
    result = run_research_once(
        ResearchLoopConfig(
            name='RuntimeOverride',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            sell_strategy='BaseSell',
            start_date=20250101,
            end_date=20250131,
            candidate_start_date=20250102,
            candidate_end_date=20250103,
            candidate_timeout=300,
            run_candidate=True,
        ),
        controller,
    )

    assert result['status'] == 'ok'
    candidate_config = controller.runs[0]
    assert candidate_config['buy_strategy'] == 'RuntimeOverride'
    assert candidate_config['start_date'] == 20250102
    assert candidate_config['end_date'] == 20250103
    assert candidate_config['timeout'] == 300
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_candidate_runtime_overrides_candidate_backtest_config -q
```

Expected:

```text
FAILED because candidate config still uses base start/end and lacks timeout
```

- [ ] **Step 3: Apply overrides in `_candidate_config_dict()`**

Modify `_candidate_config_dict(config)`:

```python
def _candidate_config_dict(config: ResearchLoopConfig) -> dict:
    candidate = _base_config_dict(config)
    candidate['buy_strategy'] = config.name
    candidate['start_date'] = _candidate_start_date(config)
    candidate['end_date'] = _candidate_end_date(config)
    if config.candidate_timeout is not None:
        candidate['timeout'] = config.candidate_timeout
    return candidate
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_candidate_runtime_overrides_candidate_backtest_config tests/unit/test_research_loop.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "후보 백테스트 실행 범위를 분리한다" -m "후보 백테스트에 candidate_start/end와 candidate_timeout을 반영해 분석 범위와 검증 범위를 분리할 수 있게 했다.

Constraint: baseline CSV 분석 기간과 후보 검증 기간은 독립적으로 제어되어야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_loop.py -q"
```
