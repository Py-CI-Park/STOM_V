# Backtest Iteration Research Loop v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a WFO-free `discovery research --run-candidates` mode that evaluates N independent candidate expressions in one round, ranks them, cleans temporary strategies, and reports the best candidate.

**Architecture:** Preserve `run_research_once()` for the existing single-candidate path. Add `run_research_iteration()` for one-round multi-candidate execution, with shared helpers for candidate specs, candidate execution, ranking, cleanup, and reporting.

**Tech Stack:** Python 3.11, existing STOM CLI modules, `cli.research_loop`, `cli.research_report`, `cli.subcommands`, `cli.ai_controller`, pytest.

---

## Scope Check

This plan implements only:

```text
baseline CSV analysis
-> candidate expression N generation
-> candidate-by-candidate backtest
-> candidate ranking
-> best_candidate selection
-> cleanup/reporting
```

Out of scope:

- WFO in `discovery research`.
- `discovery promote` changes.
- `auto_discovery` changes.
- AI/API condition regeneration.
- Multi-round iteration.
- Core backtest/runner/GUI changes.

## File Structure

- Modify `cli/research_loop.py`: config fields, validation, candidate spec helpers, shared candidate executor, ranking, cleanup summary, `run_research_iteration()`.
- Modify `cli/research_report.py`: iteration report fields and Markdown sections.
- Modify `cli/subcommands.py`: multi-candidate CLI options.
- Modify `cli/ai_controller.py`: route `run_candidates=True` to `run_research_iteration()`.
- Modify tests in `tests/unit/test_research_loop.py`, `tests/unit/test_research_report.py`, `tests/unit/test_subcommands.py`, `tests/unit/test_ai_controller.py`.
- Add `docs/update_log/2026-04-18_backtest_iteration_research_loop.md`.

---

### Task 1: Config, CLI, And Controller Routing

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `cli/subcommands.py`
- Modify: `cli/ai_controller.py`
- Test: `tests/unit/test_research_loop.py`
- Test: `tests/unit/test_subcommands.py`
- Test: `tests/unit/test_ai_controller.py`

- [ ] **Step 1: Write failing tests**

Add these tests:

```python
def test_research_loop_config_has_iteration_fields():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'run_candidates' in names
    assert 'candidate_count' in names
    assert 'candidate_name_prefix' in names
    assert 'cleanup_best_candidate' in names
    assert 'keep_loser_candidates' in names


def test_research_loop_rejects_iteration_mode_conflicts(tmp_path):
    conflict = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(name='Conflict', baseline_csv=str(tmp_path / 'b.csv'), run_candidate=True, run_candidates=True)
    )
    assert conflict['phase'] == 'run_candidate_and_run_candidates_conflict'

    plan_conflict = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(name='PlanConflict', baseline_csv=str(tmp_path / 'b.csv'), run_candidates=True, candidate_plan_only=True)
    )
    assert plan_conflict['phase'] == 'candidate_plan_only_iteration_conflict'

    invalid_count = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(name='InvalidCount', baseline_csv=str(tmp_path / 'b.csv'), run_candidates=True, candidate_count=0)
    )
    assert invalid_count['phase'] == 'invalid_candidate_count'
```

```python
def test_discovery_research_parser_accepts_iteration_options():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research', 'AutoResearchIteration',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--run-candidates',
        '--candidate-count', '5',
        '--candidate-name-prefix', 'ResearchBatch',
        '--cleanup-best-candidate',
        '--keep-loser-candidates',
    ])
    assert args.run_candidates is True
    assert args.candidate_count == 5
    assert args.candidate_name_prefix == 'ResearchBatch'
    assert args.cleanup_best_candidate is True
    assert args.keep_loser_candidates is True


def test_discovery_research_handler_passes_iteration_options():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'phase': 'candidates_evaluated'}
        exit_code = handle_subcommand([
            'discovery', 'research', 'AutoResearchIteration',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-candidates',
            '--candidate-count', '5',
            '--candidate-name-prefix', 'ResearchBatch',
            '--cleanup-best-candidate',
            '--keep-loser-candidates',
        ])
    payload = mock.call_args.args[0]
    assert exit_code == 0
    assert payload['run_candidates'] is True
    assert payload['candidate_count'] == 5
    assert payload['candidate_name_prefix'] == 'ResearchBatch'
    assert payload['cleanup_best_candidate'] is True
    assert payload['keep_loser_candidates'] is True
```

```python
def test_research_strategy_once_routes_iteration(monkeypatch):
    from cli.ai_controller import AIBacktestController
    from cli.research_loop import ResearchLoopConfig

    calls = {}

    def fake_iteration(config, controller):
        calls['config'] = config
        calls['controller'] = controller
        return {'status': 'ok', 'phase': 'candidates_evaluated'}

    monkeypatch.setattr('cli.research_loop.run_research_iteration', fake_iteration)
    monkeypatch.setattr('cli.research_loop.run_research_once', lambda config, controller: {'status': 'error', 'phase': 'wrong_route'})

    controller = AIBacktestController()
    result = controller.research_strategy_once({'name': 'IterationRoute', 'run_candidates': True, 'candidate_count': 3})

    assert result['phase'] == 'candidates_evaluated'
    assert isinstance(calls['config'], ResearchLoopConfig)
    assert calls['config'].run_candidates is True
    assert calls['config'].candidate_count == 3
    assert calls['controller'] is controller
```

- [ ] **Step 2: Run failing tests**

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_config_has_iteration_fields tests/unit/test_research_loop.py::test_research_loop_rejects_iteration_mode_conflicts tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_options tests/unit/test_ai_controller.py::test_research_strategy_once_routes_iteration -q
```

Expected: failures because iteration config, CLI options, and routing are missing.

- [ ] **Step 3: Implement config and validation**

Add to `ResearchLoopConfig`:

```python
    run_candidates: bool = False
    candidate_count: int = 5
    candidate_name_prefix: str | None = None
    cleanup_best_candidate: bool = False
    keep_loser_candidates: bool = False
```

Add:

```python
def validate_research_iteration_config(config: ResearchLoopConfig) -> dict:
    if config.run_candidate and config.run_candidates:
        return _error('run_candidate_and_run_candidates_conflict', 'run_candidate and run_candidates cannot both be true')
    if config.candidate_plan_only and config.run_candidates:
        return _error('candidate_plan_only_iteration_conflict', 'candidate_plan_only cannot be used with run_candidates')
    if config.candidate_count < 1:
        return _error('invalid_candidate_count', 'candidate_count must be greater than or equal to 1')
    return {'status': 'ok'}
```

Call this at the start of `run_research_once()`. Add a temporary `run_research_iteration()` stub that validates and returns `phase='candidate_iteration'`.

- [ ] **Step 4: Implement CLI and routing**

In `cli/subcommands.py`, make `--run-candidate` and `--run-candidates` mutually exclusive, add `--candidate-count`, `--candidate-name-prefix`, `--cleanup-best-candidate`, `--keep-loser-candidates`, and pass them to `research_strategy_once()`.

In `cli/ai_controller.py`, import `run_research_iteration` and route:

```python
if config.run_candidates:
    return run_research_iteration(config, self)
return run_research_once(config, self)
```

- [ ] **Step 5: Verify and commit**

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_config_has_iteration_fields tests/unit/test_research_loop.py::test_research_loop_rejects_iteration_mode_conflicts tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_options tests/unit/test_ai_controller.py::test_research_strategy_once_routes_iteration -q
git add cli/research_loop.py cli/subcommands.py cli/ai_controller.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_ai_controller.py
git commit -m "다중 후보 연구 모드 진입점을 추가한다" -m "discovery research에 run-candidates 설정과 CLI 옵션, 컨트롤러 라우팅을 추가했다.

Constraint: 기존 단일 후보 --run-candidate 경로는 유지해야 함
Rejected: 별도 discovery subcommand 추가 | 기존 research 흐름의 자연스러운 확장이므로 CLI 표면을 늘리지 않음
Confidence: high
Scope-risk: moderate
Tested: focused iteration routing and CLI tests"
```

---

### Task 2: Iteration Plan And Candidate Specs

**Files:**
- Modify: `cli/research_loop.py`
- Test: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing tests**

Add tests for `_build_iteration_plan()` and `_build_candidate_specs()`:

```python
def test_iteration_plan_uses_effective_top_n_and_candidate_prefix(tmp_path):
    plan = research_loop._build_iteration_plan(
        ResearchLoopConfig(
            name='BatchName',
            baseline_csv=str(tmp_path / 'baseline.csv'),
            candidate_count=3,
            candidate_name_prefix='PrefixName',
            top_n=1,
            candidate_start_date=20250102,
            candidate_end_date=20250103,
            candidate_timeout=120,
            run_candidates=True,
        )
    )
    assert plan['candidate_count'] == 3
    assert plan['candidate_name_prefix'] == 'PrefixName'
    assert plan['effective_top_n'] == 3
    assert plan['candidate_start_date'] == 20250102
    assert plan['candidate_end_date'] == 20250103
    assert plan['candidate_timeout'] == 120


def test_build_candidate_specs_uses_one_expression_per_candidate():
    config = ResearchLoopConfig(name='BatchName', run_candidates=True, candidate_count=2)
    result = {
        'expressions': ['체결강도 < 90', '시가총액 <= 3000'],
        'selected_candidates': [
            {'source': 'ttest', 'feature': 'B_체결강도', 'count': 50},
            {'source': 'quantile', 'feature': 'B_시가총액', 'count': 70},
        ],
    }
    specs = research_loop._build_candidate_specs(config, result)
    assert [spec['strategy_name'] for spec in specs] == ['BatchName__cand001', 'BatchName__cand002']
    assert specs[0]['expressions'] == ['체결강도 < 90']
    assert specs[1]['expressions'] == ['시가총액 <= 3000']
    assert specs[0]['source_candidate']['feature'] == 'B_체결강도'
```

- [ ] **Step 2: Implement helpers**

Add:

```python
def _candidate_name_prefix(config: ResearchLoopConfig) -> str:
    return config.candidate_name_prefix or config.name


def _effective_top_n(config: ResearchLoopConfig) -> int:
    return max(config.top_n, config.candidate_count) if config.run_candidates else config.top_n


def _build_iteration_plan(config: ResearchLoopConfig) -> dict:
    return {
        'candidate_count': config.candidate_count,
        'candidate_name_prefix': _candidate_name_prefix(config),
        'effective_top_n': _effective_top_n(config),
        'candidate_start_date': _candidate_start_date(config),
        'candidate_end_date': _candidate_end_date(config),
        'candidate_timeout': config.candidate_timeout,
        'cleanup_best_candidate': config.cleanup_best_candidate,
        'keep_loser_candidates': config.keep_loser_candidates,
        'keep_failed_candidate': config.keep_failed_candidate,
    }


def _build_candidate_specs(config: ResearchLoopConfig, expression_result: dict) -> list[dict]:
    specs = []
    expressions = expression_result.get('expressions') or []
    selected = expression_result.get('selected_candidates') or []
    for index, expression in enumerate(expressions[:config.candidate_count], start=1):
        specs.append({
            'index': index,
            'strategy_name': f'{_candidate_name_prefix(config)}__cand{index:03d}',
            'expression': expression,
            'expressions': [expression],
            'source_candidate': selected[index - 1] if index - 1 < len(selected) else None,
        })
    return specs
```

- [ ] **Step 3: Verify and commit**

```powershell
python -m pytest tests/unit/test_research_loop.py::test_iteration_plan_uses_effective_top_n_and_candidate_prefix tests/unit/test_research_loop.py::test_build_candidate_specs_uses_one_expression_per_candidate -q
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "다중 후보 실행 계획을 만든다" -m "후보 N개 실행을 위해 iteration_plan과 후보별 단일 expression spec 생성 helper를 추가했다.

Constraint: 후보 N개는 같은 baseline 분석 결과에서 나온 expression을 하나씩 평가해야 함
Confidence: high
Scope-risk: narrow
Tested: iteration plan and candidate spec unit tests"
```

---

### Task 3: Shared Candidate Execution Helper

**Files:**
- Modify: `cli/research_loop.py`
- Test: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing tests**

Add tests that `_execute_candidate_spec()`:

```text
uses spec['strategy_name'] as buy_strategy
passes exactly spec['expressions'] to generate_buy_filter_strategy()
returns phase='candidate_evaluated' on success
returns candidate_backtest_timeout and cleanup on timeout
```

Use this core assertion pattern:

```python
assert generated == [('Batch__cand001', ['체결강도 < 90'])]
assert result['candidate_plan']['strategy_name'] == 'Batch__cand001'
assert result['promotion']['status'] == 'ok'
```

- [ ] **Step 2: Refactor helpers**

Update `_candidate_config_dict()`, `_build_candidate_plan()`, `_prepare_candidate_strategy()`, and `_cleanup_candidate_strategy()` to accept optional `strategy_name`. Existing call sites must still work with default `config.name`.

- [ ] **Step 3: Implement `_execute_candidate_spec()`**

Add helper:

```python
def _candidate_from_spec(spec: dict) -> dict:
    return {
        'expression': spec.get('expression'),
        'expressions': spec.get('expressions') or [],
        'reason': _format_candidate_reason(spec.get('source_candidate')) or f"analysis_candidate={spec.get('expression')}",
        'candidate_count': 1,
        'selected_candidates': [spec.get('source_candidate')] if spec.get('source_candidate') else [],
    }
```

`_execute_candidate_spec()` must perform:

```text
prepare candidate strategy
run candidate backtest with candidate date/timeout
validate csv_path
compare baseline/candidate
evaluate promotion
return one candidate item with status, phase, candidate_plan, comparison, promotion, cleanup
```

Reuse the existing single-candidate failure phases.

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest tests/unit/test_research_loop.py::test_execute_candidate_spec_uses_spec_strategy_name_and_single_expression tests/unit/test_research_loop.py::test_execute_candidate_spec_timeout_returns_candidate_item_and_cleanup tests/unit/test_research_loop.py::test_candidate_backtest_timeout_cleans_candidate_by_default tests/unit/test_research_loop.py::test_research_loop_returns_candidate_backtest_phase -q
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "후보 실행 helper를 공통화한다" -m "다중 후보 루프가 후보별 strategy name과 단일 expression을 사용하도록 candidate spec 실행 helper를 추가했다.

Constraint: 단일 후보와 다중 후보의 timeout, CSV 누락, 비교 실패 처리 규칙이 갈라지면 안 됨
Confidence: medium
Scope-risk: moderate
Tested: shared candidate execution and single-candidate regression tests"
```

---

### Task 4: Iteration Core, Ranking, And Cleanup

**Files:**
- Modify: `cli/research_loop.py`
- Test: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing tests**

Add tests for:

```text
run_research_iteration analyzes baseline CSV once
run_research_iteration runs each candidate exactly once
_rank_candidate_results prefers promotion.passed before score
_apply_iteration_cleanup keeps best by default
_apply_iteration_cleanup deletes losers by default
cleanup_best_candidate deletes best
keep_loser_candidates keeps losers
all candidates failing returns status='error' and best_candidate=None
```

Concrete ranking test:

```python
def test_rank_candidate_results_prefers_promotion_pass_then_score():
    candidates = [
        {
            'index': 1,
            'status': 'ok',
            'strategy_name': 'Batch__cand001',
            'expression': 'A',
            'promotion': {'passed': False, 'score': 100.0},
            'comparison': {'candidate_summary': {'trade_count': 100, 'date_concentration': 0.1, 'symbol_concentration': 0.1}, 'trade_count_retention': 0.8},
        },
        {
            'index': 2,
            'status': 'ok',
            'strategy_name': 'Batch__cand002',
            'expression': 'B',
            'promotion': {'passed': True, 'score': 10.0},
            'comparison': {'candidate_summary': {'trade_count': 20, 'date_concentration': 0.3, 'symbol_concentration': 0.2}, 'trade_count_retention': 0.4},
        },
    ]
    ranked, best = research_loop._rank_candidate_results(candidates)
    assert best['strategy_name'] == 'Batch__cand002'
    assert ranked[1]['rank'] == 1
    assert ranked[1]['selected_as_best'] is True
```

Concrete cleanup test:

```python
def test_iteration_cleanup_deletes_losers_and_keeps_best(monkeypatch):
    cleanup_calls = []
    monkeypatch.setattr(research_loop, 'delete_strategy_from_db', lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'})
    config = ResearchLoopConfig(name='Batch', run_candidates=True)
    candidates = [
        {'strategy_name': 'Batch__cand001', 'status': 'ok', 'selected_as_best': True, 'cleanup': None},
        {'strategy_name': 'Batch__cand002', 'status': 'ok', 'selected_as_best': False, 'cleanup': None},
    ]
    updated, summary = research_loop._apply_iteration_cleanup(config, candidates)
    assert cleanup_calls == ['Batch__cand002']
    assert updated[0]['cleanup']['reason'] == 'best_candidate_kept'
    assert updated[1]['cleanup']['reason'] == 'loser_candidate_deleted'
    assert summary['deleted_count'] == 1
    assert summary['kept_count'] == 1
```

- [ ] **Step 2: Implement ranking helpers**

Add `_rank_score()`, `_rank_key()`, and `_rank_candidate_results()` using this sort priority:

```text
promotion.passed True first
promotion.score descending
candidate_summary.trade_count descending
trade_count_retention descending
date_concentration ascending
symbol_concentration ascending
index ascending
```

Return `(ranked_candidates, best_candidate)`.

- [ ] **Step 3: Implement cleanup helpers**

Add `_cleanup_candidate_by_name()`, `_cleanup_summary()`, and `_apply_iteration_cleanup()`.

Required behavior:

```text
existing failed candidate cleanup stays unchanged
best + cleanup_best_candidate=False -> reason best_candidate_kept
best + cleanup_best_candidate=True -> reason best_candidate_deleted
loser + keep_loser_candidates=False -> reason loser_candidate_deleted
loser + keep_loser_candidates=True -> reason loser_candidate_kept
```

- [ ] **Step 4: Implement `run_research_iteration()`**

The function must:

```text
validate config
resolve baseline CSV
run analyze_result_csv() once
build iteration_plan
run generate_condition_expressions_from_analysis(..., top_n=iteration_plan['effective_top_n'])
build candidate specs
execute each spec with _execute_candidate_spec()
rank candidate results
apply cleanup
return _build_result(config, result)
```

Top-level result must include:

```python
'phase': 'candidates_evaluated' if best_candidate else 'candidate_iteration'
'iteration_plan': iteration_plan
'candidates': ranked_candidates
'best_candidate': best_candidate
'cleanup_summary': cleanup_summary
```

- [ ] **Step 5: Verify and commit**

```powershell
python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_analyzes_once_and_runs_each_candidate tests/unit/test_research_loop.py::test_rank_candidate_results_prefers_promotion_pass_then_score tests/unit/test_research_loop.py::test_iteration_cleanup_deletes_losers_and_keeps_best tests/unit/test_research_loop.py::test_iteration_cleanup_can_delete_best tests/unit/test_research_loop.py::test_iteration_cleanup_can_keep_losers -q
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "다중 후보 평가와 정리를 실행한다" -m "baseline 분석 1회에서 생성된 후보 expression을 후보별 전략으로 실행하고, promotion ranking과 cleanup 정책으로 best_candidate를 선택하게 했다.

Constraint: best_candidate는 promotion 통과 후보가 아니라 후보 묶음 내 최고 rank 후보임
Rejected: 후보마다 run_research_once 재호출 | baseline 분석이 후보 수만큼 반복되고 후보 출처 추적이 흐려짐
Confidence: medium
Scope-risk: moderate
Tested: multi-candidate iteration, ranking, cleanup focused tests"
```

---

### Task 5: Iteration Report

**Files:**
- Modify: `cli/research_report.py`
- Test: `tests/unit/test_research_report.py`

- [ ] **Step 1: Write failing tests**

Add tests that:

```text
build_research_report includes phase, iteration_plan, candidates, best_candidate, cleanup_summary
render_research_report_markdown includes ## Candidate Iteration
render_research_report_markdown includes ## Candidate Ranking
render_research_report_markdown includes ## Cleanup Summary
```

Concrete assertions:

```python
assert report['phase'] == 'candidates_evaluated'
assert report['iteration_plan']['candidate_count'] == 2
assert report['best_candidate']['strategy_name'] == 'Batch__cand001'
assert report['cleanup_summary']['deleted_count'] == 1
assert '## Candidate Iteration' in markdown
assert '## Candidate Ranking' in markdown
assert '## Cleanup Summary' in markdown
```

- [ ] **Step 2: Implement report fields**

In `build_research_report()`, add:

```python
'phase': result.get('phase'),
'iteration_plan': result.get('iteration_plan'),
'candidates': result.get('candidates'),
'best_candidate': result.get('best_candidate'),
'cleanup_summary': result.get('cleanup_summary'),
```

- [ ] **Step 3: Implement Markdown sections**

In `render_research_report_markdown()`, after Candidate Runtime and before Trade Set Comparison, render:

```text
## Candidate Iteration
## Candidate Ranking
## Cleanup Summary
```

The ranking table columns must be:

```text
rank | strategy | expression | status | passed | score | trade_count | retention | cleanup
```

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest tests/unit/test_research_report.py::test_build_research_report_includes_iteration_fields tests/unit/test_research_report.py::test_render_research_report_markdown_contains_iteration_sections -q
git add cli/research_report.py tests/unit/test_research_report.py
git commit -m "다중 후보 연구 리포트를 추가한다" -m "iteration_plan, candidates, best_candidate, cleanup_summary를 연구 리포트에 포함하고 Markdown 순위/정리 섹션을 렌더링하게 했다.

Constraint: 기존 단일 후보 리포트 섹션은 유지해야 함
Confidence: high
Scope-risk: narrow
Tested: iteration report focused tests"
```

---

### Task 6: Verification, Update Log, And Pilot

**Files:**
- Create: `docs/update_log/2026-04-18_backtest_iteration_research_loop.md`
- Modify: prior task files only if verification exposes a defect.

- [ ] **Step 1: Run focused tests**

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py tests/unit/test_ai_controller.py -q
```

- [ ] **Step 2: Run full unit tests**

```powershell
python -m pytest tests/unit/ -q
```

- [ ] **Step 3: Run non-release sync verification**

```powershell
python scripts/verify_nonrelease_sync.py
```

- [ ] **Step 4: Run short real pilot**

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py discovery research AutoResearchIterationPilot `
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidates `
  --candidate-count 3 `
  --candidate-start 20250407 `
  --candidate-end 20250407 `
  --candidate-timeout 120 `
  --cleanup-best-candidate
```

Expected:

```text
status is ok if at least one candidate evaluates
phase is candidates_evaluated
candidates has up to 3 items
cleanup_summary is present
test candidate strategies are not left in strategy.db because cleanup_best_candidate is set
```

- [ ] **Step 5: Create update log**

Create `docs/update_log/2026-04-18_backtest_iteration_research_loop.md` with:

```markdown
# 2026-04-18 Backtest Iteration Research Loop v1

## 목적

`discovery research`에서 후보 N개를 한 라운드로 실행하고, 후보별 백테스트/비교/승격 평가를 수집한 뒤 `best_candidate`를 선택하는 빠른 연구 루프를 추가했다.

## 변경 사항

- `--run-candidates` 다중 후보 실행 모드 추가
- 후보별 전략명 `{name}__candNNN` 생성
- 후보별 expression 1개만 필터로 적용
- baseline CSV 분석 1회 후 후보 N개 실행
- 후보별 comparison/promotion 평가 수집
- promotion score 기반 deterministic ranking
- best 후보 기본 보존
- loser/failed 후보 기본 삭제
- `--cleanup-best-candidate`, `--keep-loser-candidates` 추가
- iteration_plan, candidates, best_candidate, cleanup_summary 리포트 추가

## 검증

실제 명령과 결과를 기록한다.

## 파일럿

실제 `--run-candidates` 파일럿 명령과 결과를 기록한다.

## 남은 리스크

- 짧은 후보 구간은 런타임 검증용이며 전략 품질 검증으로 충분하지 않다.
- `best_candidate`는 promotion 통과 후보가 아닐 수 있다.
- 다중 라운드 자동 재생성은 아직 구현되지 않았다.
- 최종 채택 전에는 `discovery promote` 또는 별도 WFO 검증이 필요하다.
- 결과 CSV 누적 관리 정책은 후속 작업이 필요하다.
```

Before committing, record the exact verification and pilot command outputs in the verification and pilot sections.

- [ ] **Step 6: Commit update log**

```powershell
git diff --check
git add docs/update_log/2026-04-18_backtest_iteration_research_loop.md
git commit -m "다중 후보 연구 루프 기록을 남긴다" -m "후보 N개 실행, 랭킹, cleanup, best_candidate 선택 변경 사항과 검증 결과를 업데이트 로그로 기록했다.

Constraint: 파일럿은 cleanup_best_candidate로 strategy.db 잔여 후보를 남기지 않아야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py tests/unit/test_ai_controller.py -q
Tested: python -m pytest tests/unit/ -q
Tested: python scripts/verify_nonrelease_sync.py
Not-tested: 장기간 후보 N개 운영 파일럿"
```

---

## Final Verification Checklist

- [ ] `git status --short --branch` shows only intentional tracked changes and existing untracked `backtest/graph/`.
- [ ] `python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py tests/unit/test_ai_controller.py -q` passes.
- [ ] `python -m pytest tests/unit/ -q` passes.
- [ ] `python scripts/verify_nonrelease_sync.py` passes.
- [ ] A short `--run-candidates` pilot was attempted and recorded.
- [ ] Test candidate strategies are not left in `strategy.db` after the pilot when `--cleanup-best-candidate` is used.
- [ ] WFO remains absent from `discovery research`.
- [ ] Existing `--run-candidate` single-candidate tests still pass.

## Plan Self-Review Notes

- Spec coverage: config, CLI, candidate spec, execution, ranking, cleanup, report, and verification requirements are mapped to tasks.
- Scope: this plan implements one-round multi-candidate evaluation only; multi-round regeneration remains a later phase.
- Type consistency: `run_candidates`, `candidate_count`, `candidate_name_prefix`, `cleanup_best_candidate`, `keep_loser_candidates`, `iteration_plan`, `candidates`, `best_candidate`, and `cleanup_summary` names match the design document.
