# Candidate Quality Gate And Retention-Aware Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add retention-aware candidate selection and retention-penalized ranking so `discovery research --run-candidates` prefers candidates that preserve enough baseline trades instead of over-pruning.

**Architecture:** Add a focused `cli.research_retention` module for retention estimation, selection, fallback, and penalty math. Wire it into `cli.research_loop` before candidate spec creation and inside ranking, then expose the policy through CLI options and Markdown/JSON reports without changing core backtest, WFO, promote, or GUI paths.

**Tech Stack:** Python 3.11, pandas, existing STOM CLI modules, `cli.research_loop`, `cli.research_report`, `cli.subcommands`, pytest.

---

## Full Flow

```text
[0. 기준 전략]
        |
        v
[1. 기준 백테스트 결과 CSV]
        |
        v
[2. CSV 분석]
        |
        v
[3. 후보 expression pool 생성]
        |
        v
[4. Retention-Aware 후보 선별]  <- this plan
        |
        v
[5. 후보 N개 백테스트]
        |
        v
[6. Retention-Penalized Ranking] <- this plan
        |
        v
[7. best_candidate 선택]
        |
        v
[8. 반복 개선 루프 v2]
        |
        v
[9. 최종 promote/WFO 검증]
```

## Scope Check

This plan implements only:

```text
estimated_retention calculation
retention-aware candidate selection
fallback policy
retention penalty / adjusted_score ranking
JSON and Markdown reporting
tick quality pilot
```

Out of scope:

- WFO inside `discovery research`.
- Promotion gate relaxation.
- Multi-round automatic regeneration.
- Opportunity-universe logging.
- Core backtest/runner/GUI changes.

## File Structure

- Create `cli/research_retention.py`
  - Estimate retention from baseline trade frames.
  - Annotate candidate dictionaries.
  - Select retention-aware candidates with fallback.
  - Compute retention penalty and adjusted score.

- Create `tests/unit/test_research_retention.py`
  - Focused tests for retention math and selection policy.

- Modify `cli/research_loop.py`
  - Add config fields and validation.
  - Increase effective candidate pool size.
  - Annotate and select candidates before `_build_candidate_specs()`.
  - Add retention metadata to `iteration_plan`, `retention_selection`, `candidate` items, and `rank_score`.

- Modify `cli/subcommands.py`
  - Add CLI options and payload fields.

- Modify `cli/research_report.py`
  - Render retention-aware selection and retention-penalized ranking fields.

- Modify tests:
  - `tests/unit/test_research_loop.py`
  - `tests/unit/test_subcommands.py`
  - `tests/unit/test_research_report.py`

- Add update log:
  - `docs/update_log/2026-04-19_candidate_quality_gate_retention_aware.md`

---

### Task 1: Retention Estimation Module

**Files:**
- Create: `cli/research_retention.py`
- Create: `tests/unit/test_research_retention.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_research_retention.py`:

```python
import math

import pandas as pd

from cli.research_retention import (
    annotate_candidate_retention,
    estimate_candidate_retention,
    retention_penalty,
    apply_retention_penalty,
)


def _frame():
    return pd.DataFrame([
        {'시가총액': 1000, '회전율': 5.0, '등락율': 1.0},
        {'시가총액': 2000, '회전율': 12.0, '등락율': 3.0},
        {'시가총액': 3000, '회전율': 20.0, '등락율': 5.0},
        {'시가총액': 4000, '회전율': 30.0, '등락율': 7.0},
        {'시가총액': 5000, '회전율': 40.0, '등락율': 9.0},
    ])


def test_estimate_candidate_retention_counts_removed_and_kept_rows():
    result = estimate_candidate_retention(_frame(), '시가총액 <= 4000')

    assert result['baseline_trade_count'] == 5
    assert result['estimated_removed_count'] == 4
    assert result['estimated_kept_count'] == 1
    assert result['estimated_retention'] == 0.2


def test_estimate_candidate_retention_accepts_b_prefixed_csv_columns():
    frame = pd.DataFrame([
        {'B_회전율': 5.0},
        {'B_회전율': 12.0},
        {'B_회전율': 20.0},
    ])

    result = estimate_candidate_retention(frame, '회전율 > 10')

    assert result['baseline_trade_count'] == 3
    assert result['estimated_removed_count'] == 2
    assert result['estimated_kept_count'] == 1
    assert result['estimated_retention'] == 1 / 3


def test_estimate_candidate_retention_marks_eval_errors_as_low_retention():
    result = estimate_candidate_retention(_frame(), '없는컬럼 > 0')

    assert result['baseline_trade_count'] == 5
    assert result['estimated_removed_count'] == 5
    assert result['estimated_kept_count'] == 0
    assert result['estimated_retention'] == 0.0
    assert result['evaluation_error']


def test_annotate_candidate_retention_marks_pass_fail():
    candidates = [{'expression': '시가총액 <= 2000'}, {'expression': '회전율 > 30'}]

    annotated = annotate_candidate_retention(candidates, _frame(), min_retention=0.4)

    assert annotated[0]['retention_estimate']['estimated_retention'] == 0.6
    assert annotated[0]['retention_filter_passed'] is True
    assert annotated[1]['retention_estimate']['estimated_retention'] == 0.8
    assert annotated[1]['retention_filter_passed'] is True


def test_retention_penalty_scales_below_threshold():
    assert retention_penalty(0.4, 0.4) == 1.0
    assert retention_penalty(0.2, 0.4) == 0.5
    assert retention_penalty(-1.0, 0.4) == 0.0
    assert retention_penalty(float('nan'), 0.4) == 0.0


def test_apply_retention_penalty_adds_adjusted_score():
    result = apply_retention_penalty(
        {'promotion_score': 100.0, 'trade_count_retention': 0.2},
        min_retention=0.4,
    )

    assert result['retention_penalty'] == 0.5
    assert result['adjusted_score'] == 50.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_retention.py -q
```

Expected:

```text
FAILED because cli.research_retention does not exist
```

- [ ] **Step 3: Implement module**

Create `cli/research_retention.py`:

```python
"""Retention-aware candidate selection helpers for discovery research."""

from __future__ import annotations

import math

import pandas as pd


def _finite_float(value, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _prepare_retention_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    for column in list(prepared.columns):
        if isinstance(column, str) and column.startswith('B_'):
            runtime_name = column[2:]
            if runtime_name not in prepared.columns:
                prepared[runtime_name] = prepared[column]
    return prepared


def _safe_eval_mask(frame: pd.DataFrame, expression: str) -> tuple[pd.Series, str | None]:
    prepared = _prepare_retention_frame(frame)
    try:
        mask = prepared.eval(expression, engine='python')
    except Exception as e:
        return pd.Series([True] * len(prepared), index=prepared.index), str(e)
    if not isinstance(mask, pd.Series):
        return pd.Series([True] * len(prepared), index=prepared.index), 'expression did not return a row mask'
    return mask.fillna(False).astype(bool), None


def estimate_candidate_retention(frame: pd.DataFrame, expression: str) -> dict:
    baseline_trade_count = int(len(frame))
    if baseline_trade_count <= 0:
        return {
            'baseline_trade_count': 0,
            'estimated_removed_count': 0,
            'estimated_kept_count': 0,
            'estimated_retention': 0.0,
        }
    mask, evaluation_error = _safe_eval_mask(frame, expression)
    removed = int(mask.sum())
    kept = max(baseline_trade_count - removed, 0)
    return {
        'baseline_trade_count': baseline_trade_count,
        'estimated_removed_count': removed,
        'estimated_kept_count': kept,
        'estimated_retention': kept / baseline_trade_count,
        'evaluation_error': evaluation_error,
    }


def annotate_candidate_retention(candidates: list[dict], baseline_frame: pd.DataFrame, min_retention: float) -> list[dict]:
    annotated = []
    for candidate in candidates:
        item = dict(candidate)
        estimate = estimate_candidate_retention(baseline_frame, str(item.get('expression') or ''))
        item['retention_estimate'] = estimate
        item['retention_filter_passed'] = estimate['evaluation_error'] is None and estimate['estimated_retention'] >= min_retention
        item['retention_fallback_used'] = False
        annotated.append(item)
    return annotated


def retention_penalty(actual_retention: float, min_retention: float) -> float:
    retention = max(_finite_float(actual_retention), 0.0)
    threshold = _finite_float(min_retention, 0.0)
    if threshold <= 0:
        return 1.0
    if retention >= threshold:
        return 1.0
    return retention / threshold


def apply_retention_penalty(rank_score: dict, min_retention: float) -> dict:
    result = dict(rank_score)
    promotion_score = _finite_float(result.get('promotion_score'))
    trade_count_retention = _finite_float(result.get('trade_count_retention'))
    penalty = retention_penalty(trade_count_retention, min_retention)
    result['promotion_score'] = promotion_score
    result['trade_count_retention'] = trade_count_retention
    result['retention_penalty'] = penalty
    result['adjusted_score'] = promotion_score * penalty
    return result
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_retention.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_retention.py tests/unit/test_research_retention.py
git commit -m "후보 거래 유지율 계산 모듈을 추가한다" -m "baseline 거래 CSV 기준으로 후보 expression의 예상 거래 유지율을 계산하고 ranking penalty를 산출하는 helper를 추가했다.

Constraint: discovery research에서 WFO를 다시 호출하지 않고 실행 전 후보 품질만 보강해야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_retention.py -q"
```

---

### Task 2: Retention-Aware Candidate Selection

**Files:**
- Modify: `cli/research_retention.py`
- Modify: `tests/unit/test_research_retention.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_research_retention.py`:

```python
from cli.research_retention import select_retention_aware_candidates


def test_select_retention_aware_candidates_prefers_passed_candidates():
    candidates = [
        {'expression': 'A', 'combined_score': 100, 'retention_estimate': {'estimated_retention': 0.2}, 'retention_filter_passed': False},
        {'expression': 'B', 'combined_score': 10, 'retention_estimate': {'estimated_retention': 0.7}, 'retention_filter_passed': True},
        {'expression': 'C', 'combined_score': 20, 'retention_estimate': {'estimated_retention': 0.6}, 'retention_filter_passed': True},
    ]

    selected, summary = select_retention_aware_candidates(candidates, candidate_count=2, allow_fallback=True, min_retention=0.4)

    assert [item['expression'] for item in selected] == ['B', 'C']
    assert summary['pool_count'] == 3
    assert summary['passed_count'] == 2
    assert summary['fallback_count'] == 0


def test_select_retention_aware_candidates_uses_fallback_when_needed():
    candidates = [
        {'expression': 'A', 'combined_score': 100, 'retention_estimate': {'estimated_retention': 0.2}, 'retention_filter_passed': False},
        {'expression': 'B', 'combined_score': 10, 'retention_estimate': {'estimated_retention': 0.7}, 'retention_filter_passed': True},
        {'expression': 'C', 'combined_score': 20, 'retention_estimate': {'estimated_retention': 0.3}, 'retention_filter_passed': False},
    ]

    selected, summary = select_retention_aware_candidates(candidates, candidate_count=3, allow_fallback=True, min_retention=0.4)

    assert [item['expression'] for item in selected] == ['B', 'C', 'A']
    assert selected[0]['retention_fallback_used'] is False
    assert selected[1]['retention_fallback_used'] is True
    assert selected[2]['retention_fallback_used'] is True
    assert summary['fallback_count'] == 2


def test_select_retention_aware_candidates_blocks_when_fallback_disabled():
    candidates = [
        {'expression': 'A', 'retention_estimate': {'estimated_retention': 0.2}, 'retention_filter_passed': False},
        {'expression': 'B', 'retention_estimate': {'estimated_retention': 0.7}, 'retention_filter_passed': True},
    ]

    selected, summary = select_retention_aware_candidates(candidates, candidate_count=2, allow_fallback=False, min_retention=0.4)

    assert selected == []
    assert summary['status'] == 'error'
    assert summary['phase'] == 'insufficient_retention_candidates'
    assert summary['passed_count'] == 1


def test_select_retention_aware_candidates_does_not_fallback_eval_errors():
    candidates = [
        {'expression': 'A', 'retention_estimate': {'estimated_retention': 0.7, 'evaluation_error': None}, 'retention_filter_passed': True},
        {'expression': 'B', 'retention_estimate': {'estimated_retention': 0.0, 'evaluation_error': 'missing column'}, 'retention_filter_passed': False},
        {'expression': 'C', 'retention_estimate': {'estimated_retention': 0.3, 'evaluation_error': None}, 'retention_filter_passed': False},
    ]

    selected, summary = select_retention_aware_candidates(candidates, candidate_count=2, allow_fallback=True, min_retention=0.4)

    assert [item['expression'] for item in selected] == ['A', 'C']
    assert summary['fallback_count'] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_retention.py -q
```

Expected:

```text
FAILED because select_retention_aware_candidates is not implemented
```

- [ ] **Step 3: Implement selection**

Add to `cli/research_retention.py`:

```python
def _candidate_score(candidate: dict) -> float:
    for key in ('combined_score', 'score', 'base_score'):
        if key in candidate:
            return _finite_float(candidate.get(key))
    return 0.0


def _retention_value(candidate: dict) -> float:
    estimate = candidate.get('retention_estimate') or {}
    return _finite_float(estimate.get('estimated_retention'))


def select_retention_aware_candidates(
    candidates: list[dict],
    candidate_count: int,
    allow_fallback: bool,
    min_retention: float,
) -> tuple[list[dict], dict]:
    pool = [dict(candidate) for candidate in candidates]
    passed = [candidate for candidate in pool if candidate.get('retention_filter_passed')]
    failed = [
        candidate for candidate in pool
        if not candidate.get('retention_filter_passed')
        and not (candidate.get('retention_estimate') or {}).get('evaluation_error')
    ]
    passed.sort(key=lambda item: (-_retention_value(item), -_candidate_score(item)))
    failed.sort(key=lambda item: (-_retention_value(item), -_candidate_score(item)))

    if len(passed) < candidate_count and not allow_fallback:
        return [], {
            'status': 'error',
            'phase': 'insufficient_retention_candidates',
            'pool_count': len(pool),
            'passed_count': len(passed),
            'fallback_count': 0,
            'selected_count': 0,
            'min_estimated_retention': min_retention,
            'allow_retention_fallback': allow_fallback,
        }

    selected = []
    for item in passed[:candidate_count]:
        item['retention_fallback_used'] = False
        selected.append(item)
    fallback_needed = max(candidate_count - len(selected), 0)
    for item in failed[:fallback_needed]:
        item['retention_fallback_used'] = True
        selected.append(item)

    return selected, {
        'status': 'ok',
        'phase': 'retention_candidates_selected',
        'pool_count': len(pool),
        'passed_count': len(passed),
        'fallback_count': sum(1 for item in selected if item.get('retention_fallback_used')),
        'selected_count': len(selected),
        'min_estimated_retention': min_retention,
        'allow_retention_fallback': allow_fallback,
    }
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_retention.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_retention.py tests/unit/test_research_retention.py
git commit -m "거래 유지율 기반 후보 선별을 추가한다" -m "estimated_retention 기준을 통과한 후보를 우선 선택하고 후보 부족 시 fallback 포함 여부를 명시하는 선별 helper를 추가했다.

Constraint: promotion gate를 완화하지 않고 후보 생성 품질로 retention 문제를 완화해야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_retention.py -q"
```

---

### Task 3: Research Loop Integration

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_research_loop.py`:

```python
def test_iteration_plan_includes_retention_policy():
    plan = research_loop._build_iteration_plan(
        ResearchLoopConfig(
            name='RetentionPlan',
            run_candidates=True,
            candidate_count=5,
            top_n=5,
            min_estimated_retention=0.4,
            candidate_pool_multiplier=3,
            allow_retention_fallback=True,
            use_retention_penalty=True,
        )
    )

    assert plan['candidate_pool_size'] == 15
    assert plan['min_estimated_retention'] == 0.4
    assert plan['allow_retention_fallback'] is True
    assert plan['use_retention_penalty'] is True


def test_run_research_iteration_adds_retention_metadata(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'종목명': 'A', '매수시간': 1, '매수가': 1000, '수익률': -1.0, '수익금': -1000, '시가총액': 1000},
        {'종목명': 'B', '매수시간': 2, '매수가': 1000, '수익률': 1.0, '수익금': 1000, '시가총액': 5000},
    ]).to_csv(baseline, index=False, encoding='utf-8-sig')
    _patch_analysis_success(monkeypatch, expressions=['시가총액 <= 2000', '시가총액 > 2000'])
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'retention_estimate': spec['retention_estimate'],
            'retention_filter_passed': spec['retention_filter_passed'],
            'retention_fallback_used': spec['retention_fallback_used'],
            'status': 'error',
            'phase': 'candidate_backtest',
            'cleanup': {'attempted': True, 'reason': 'candidate_backtest', 'strategy_name': spec['strategy_name']},
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(name='RetentionBatch', baseline_csv=str(baseline), run_candidate=False, run_candidates=True, candidate_count=2),
        DummyController(None),
    )

    assert result['retention_selection']['selected_count'] == 2
    assert 'retention_estimate' in result['candidates'][0]
    assert 'retention_filter_passed' in result['candidates'][0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_iteration_plan_includes_retention_policy tests/unit/test_research_loop.py::test_run_research_iteration_adds_retention_metadata -q
```

Expected:

```text
FAILED because config fields and retention integration are missing
```

- [ ] **Step 3: Implement config and validation**

In `cli/research_loop.py`, import:

```python
from cli.research_retention import (
    annotate_candidate_retention,
    apply_retention_penalty,
    select_retention_aware_candidates,
)
```

Add to `ResearchLoopConfig`:

```python
    min_estimated_retention: float = 0.40
    allow_retention_fallback: bool = True
    use_retention_penalty: bool = True
    candidate_pool_multiplier: int = 3
```

In `validate_research_iteration_config()`:

```python
    if config.run_candidates and not 0 <= config.min_estimated_retention <= 1:
        return _error('invalid_min_estimated_retention', 'min_estimated_retention must be between 0 and 1')
    if config.run_candidates and config.candidate_pool_multiplier < 1:
        return _error('invalid_candidate_pool_multiplier', 'candidate_pool_multiplier must be greater than or equal to 1')
```

- [ ] **Step 4: Extend iteration plan and effective top_n**

Modify `_effective_top_n()`:

```python
def _candidate_pool_size(config: ResearchLoopConfig) -> int:
    return max(config.top_n, config.candidate_count * config.candidate_pool_multiplier)


def _effective_top_n(config: ResearchLoopConfig) -> int:
    return _candidate_pool_size(config) if config.run_candidates else config.top_n
```

Extend `_build_iteration_plan()`:

```python
        'candidate_pool_multiplier': config.candidate_pool_multiplier,
        'candidate_pool_size': _candidate_pool_size(config),
        'min_estimated_retention': config.min_estimated_retention,
        'allow_retention_fallback': config.allow_retention_fallback,
        'use_retention_penalty': config.use_retention_penalty,
```

- [ ] **Step 5: Integrate retention selection before specs**

In `run_research_iteration()`, after expression generation and before `_build_candidate_specs()`:

```python
    baseline_frame = _trade_frame_for_compare(baseline_csv)
    expression_candidates = []
    selected_candidates = expression_result.get('selected_candidates') or []
    for index, expression in enumerate(expressions, start=1):
        source_candidate = selected_candidates[index - 1] if index - 1 < len(selected_candidates) else None
        item = dict(source_candidate or {})
        item['expression'] = expression
        item['original_index'] = index
        expression_candidates.append(item)
    annotated_candidates = annotate_candidate_retention(
        expression_candidates,
        baseline_frame,
        min_retention=config.min_estimated_retention,
    )
    selected_candidates, retention_selection = select_retention_aware_candidates(
        annotated_candidates,
        candidate_count=config.candidate_count,
        allow_fallback=config.allow_retention_fallback,
        min_retention=config.min_estimated_retention,
    )
    if retention_selection.get('status') != 'ok':
        return _build_result(config, _error(
            retention_selection['phase'],
            f"candidate_count={config.candidate_count} requested but only {retention_selection.get('passed_count')} candidates passed min_estimated_retention={config.min_estimated_retention}",
            strategy_name=config.name,
            config=asdict(config),
            baseline_csv=baseline_csv,
            baseline_result=baseline_result,
            analysis_result=analysis_result,
            expression_result=expression_result,
            iteration_plan=iteration_plan,
            retention_selection=retention_selection,
        ))
    expression_result = {
        **expression_result,
        'expressions': [candidate['expression'] for candidate in selected_candidates],
        'selected_candidates': selected_candidates,
        'retention_selection': retention_selection,
    }
```

Include in result dict:

```python
        'retention_selection': retention_selection,
```

Because `_build_candidate_specs()` already copies `source_candidate`, add these fields to each spec from `source_candidate` if present:

```python
for key in ('retention_estimate', 'retention_filter_passed', 'retention_fallback_used'):
    if source_candidate and key in source_candidate:
        spec[key] = source_candidate[key]
```

Ensure `_execute_candidate_spec()` copies those fields from spec into candidate item.

- [ ] **Step 6: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py::test_iteration_plan_includes_retention_policy tests/unit/test_research_loop.py::test_run_research_iteration_adds_retention_metadata -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 7: Commit**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "연구 루프에 거래 유지율 후보 선별을 연결한다" -m "다중 후보 실행 전에 baseline CSV 기준 estimated_retention을 계산하고 retention-aware selection 결과를 candidate spec과 iteration result에 포함했다.

Constraint: promotion gate는 완화하지 않고 후보 pool 품질을 개선해야 함
Confidence: medium
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py::test_iteration_plan_includes_retention_policy tests/unit/test_research_loop.py::test_run_research_iteration_adds_retention_metadata -q"
```

---

### Task 4: Retention-Penalized Ranking

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_research_loop.py`:

```python
def test_rank_candidate_results_uses_adjusted_score_when_retention_penalty_enabled():
    config = ResearchLoopConfig(run_candidate=False, run_candidates=True, min_estimated_retention=0.4, use_retention_penalty=True)
    candidates = [
        {
            'index': 1,
            'status': 'ok',
            'strategy_name': 'LowRetentionHighScore',
            'expression': 'A',
            'promotion': {'passed': False, 'score': 100.0},
            'comparison': {'candidate_summary': {'trade_count': 10, 'date_concentration': 0.1, 'symbol_concentration': 0.1}, 'trade_count_retention': 0.1},
        },
        {
            'index': 2,
            'status': 'ok',
            'strategy_name': 'HighRetentionLowerScore',
            'expression': 'B',
            'promotion': {'passed': False, 'score': 40.0},
            'comparison': {'candidate_summary': {'trade_count': 100, 'date_concentration': 0.1, 'symbol_concentration': 0.1}, 'trade_count_retention': 0.4},
        },
    ]

    ranked, best = research_loop._rank_candidate_results(candidates, config)

    assert best['strategy_name'] == 'HighRetentionLowerScore'
    assert ranked[0]['rank_score']['retention_penalty'] == 0.25
    assert ranked[0]['rank_score']['adjusted_score'] == 25.0
    assert ranked[1]['rank_score']['adjusted_score'] == 40.0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_rank_candidate_results_uses_adjusted_score_when_retention_penalty_enabled -q
```

Expected:

```text
FAILED because _rank_candidate_results does not accept config or use adjusted_score
```

- [ ] **Step 3: Update ranking**

Modify `_rank_candidate_results()` to accept optional config:

```python
def _rank_candidate_results(candidates: list[dict], config: ResearchLoopConfig | None = None) -> tuple[list[dict], dict | None]:
```

After `_rank_score(candidate)`, apply:

```python
if config is not None and config.use_retention_penalty:
    candidate['rank_score'] = apply_retention_penalty(candidate['rank_score'], config.min_estimated_retention)
```

Update `_rank_key()` to use:

```python
score_value = score.get('adjusted_score', score['promotion_score'])
```

Call site:

```python
ranked_candidates, best_candidate = _rank_candidate_results(candidates, config)
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_rank_candidate_results_uses_adjusted_score_when_retention_penalty_enabled tests/unit/test_research_loop.py::test_rank_candidate_results_prefers_promotion_pass_then_score -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "거래 유지율 패널티를 후보 순위에 반영한다" -m "후보 ranking에서 실제 trade_count_retention이 낮은 후보의 promotion score를 adjusted_score로 감점하도록 연결했다.

Constraint: best_candidate가 raw score만 보고 과도한 필터 후보에 쏠리면 안 됨
Confidence: medium
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_loop.py::test_rank_candidate_results_uses_adjusted_score_when_retention_penalty_enabled tests/unit/test_research_loop.py::test_rank_candidate_results_prefers_promotion_pass_then_score -q"
```

---

### Task 5: CLI Options

**Files:**
- Modify: `cli/subcommands.py`
- Modify: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_subcommands.py`:

```python
def test_discovery_research_parser_accepts_retention_options():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'RetentionResearch',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--run-candidates',
        '--min-estimated-retention', '0.5',
        '--no-retention-fallback',
        '--no-retention-penalty',
        '--candidate-pool-multiplier', '4',
    ])

    assert args.min_estimated_retention == 0.5
    assert args.allow_retention_fallback is False
    assert args.use_retention_penalty is False
    assert args.candidate_pool_multiplier == 4


def test_discovery_research_handler_passes_retention_options():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok'}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'RetentionResearch',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-candidates',
            '--min-estimated-retention', '0.5',
            '--no-retention-fallback',
            '--no-retention-penalty',
            '--candidate-pool-multiplier', '4',
        ])
    payload = mock.call_args.args[0]
    assert exit_code == 0
    assert payload['min_estimated_retention'] == 0.5
    assert payload['allow_retention_fallback'] is False
    assert payload['use_retention_penalty'] is False
    assert payload['candidate_pool_multiplier'] == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_retention_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_retention_options -q
```

Expected:

```text
FAILED because CLI options are missing
```

- [ ] **Step 3: Implement CLI options**

In `cli/subcommands.py`, add:

```python
    disc_research.add_argument('--min-estimated-retention', type=float, default=0.4)
    disc_research.add_argument('--no-retention-fallback', dest='allow_retention_fallback', action='store_false', default=True)
    disc_research.add_argument('--no-retention-penalty', dest='use_retention_penalty', action='store_false', default=True)
    disc_research.add_argument('--candidate-pool-multiplier', type=int, default=3)
```

Add to handler payload:

```python
            'min_estimated_retention': parsed.min_estimated_retention,
            'allow_retention_fallback': parsed.allow_retention_fallback,
            'use_retention_penalty': parsed.use_retention_penalty,
            'candidate_pool_multiplier': parsed.candidate_pool_multiplier,
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_retention_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_retention_options -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/subcommands.py tests/unit/test_subcommands.py
git commit -m "거래 유지율 후보 정책 옵션을 CLI에 연결한다" -m "discovery research에서 min_estimated_retention, retention fallback, retention penalty, candidate pool multiplier를 설정할 수 있게 했다.

Constraint: 기본값은 retention-aware selection과 penalty가 켜진 상태여야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_retention_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_retention_options -q"
```

---

### Task 6: Report Retention Metadata

**Files:**
- Modify: `cli/research_report.py`
- Modify: `tests/unit/test_research_report.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_research_report.py`:

```python
def test_build_research_report_includes_retention_selection():
    result = _result()
    result['retention_selection'] = {'selected_count': 5, 'fallback_count': 2}

    report = build_research_report(result, strategy_name='RetentionResearch')

    assert report['retention_selection']['selected_count'] == 5
    assert report['retention_selection']['fallback_count'] == 2


def test_render_research_report_markdown_contains_retention_sections():
    report = build_research_report({
        'status': 'ok',
        'phase': 'candidates_evaluated',
        'strategy_name': 'RetentionResearch',
        'baseline_csv': 'baseline.csv',
        'iteration_plan': {'candidate_count': 1},
        'retention_selection': {'pool_count': 3, 'selected_count': 1, 'passed_count': 1, 'fallback_count': 0, 'min_estimated_retention': 0.4},
        'candidates': [{
            'rank': 1,
            'strategy_name': 'RetentionResearch__cand001',
            'expression': '시가총액 <= 2000',
            'status': 'ok',
            'retention_estimate': {'estimated_retention': 0.6},
            'retention_filter_passed': True,
            'retention_fallback_used': False,
            'promotion': {'passed': False, 'score': 100.0},
            'comparison': {'candidate_summary': {'trade_count': 10}, 'trade_count_retention': 0.3},
            'rank_score': {'promotion_score': 100.0, 'retention_penalty': 0.75, 'adjusted_score': 75.0, 'trade_count_retention': 0.3},
            'cleanup': {'reason': 'best_candidate_deleted'},
        }],
        'best_candidate': {'strategy_name': 'RetentionResearch__cand001', 'expression': '시가총액 <= 2000', 'promotion': {'passed': False}},
        'cleanup_summary': {'deleted_count': 1, 'kept_count': 0, 'failed_count': 0},
    }, strategy_name='RetentionResearch')

    markdown = render_research_report_markdown(report)

    assert '## Retention-Aware Candidate Selection' in markdown
    assert '## Retention-Penalized Ranking' in markdown
    assert 'estimated_retention' in markdown
    assert 'adjusted_score' in markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py::test_build_research_report_includes_retention_selection tests/unit/test_research_report.py::test_render_research_report_markdown_contains_retention_sections -q
```

Expected:

```text
FAILED because report lacks retention fields and sections
```

- [ ] **Step 3: Implement report fields and Markdown**

In `build_research_report()`, add:

```python
        'retention_selection': result.get('retention_selection'),
```

In `render_research_report_markdown()`, add sections near Candidate Iteration:

```text
## Retention-Aware Candidate Selection
## Retention-Penalized Ranking
```

Render candidate expression, `retention_estimate.estimated_retention`, `retention_filter_passed`, `retention_fallback_used`, `rank_score.retention_penalty`, and `rank_score.adjusted_score`.

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py::test_build_research_report_includes_retention_selection tests/unit/test_research_report.py::test_render_research_report_markdown_contains_retention_sections -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_report.py tests/unit/test_research_report.py
git commit -m "거래 유지율 후보 정보를 리포트에 표시한다" -m "retention_selection과 후보별 estimated_retention, retention penalty, adjusted_score를 연구 리포트에 렌더링하게 했다.

Constraint: 기존 Candidate Iteration 리포트와 단일 후보 리포트는 유지해야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_report.py::test_build_research_report_includes_retention_selection tests/unit/test_research_report.py::test_render_research_report_markdown_contains_retention_sections -q"
```

---

### Task 7: Verification, Update Log, And Pilot

**Files:**
- Create: `docs/update_log/2026-04-19_candidate_quality_gate_retention_aware.md`
- Modify prior task files only if verification exposes defects.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

- [ ] **Step 2: Run full unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q
```

- [ ] **Step 3: Run non-release sync verification**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

- [ ] **Step 4: Run tick retention pilot**

Run:

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py discovery research TickResearchRetentionPilot_20260419 `
  --input backtest/csv/stock_bt_Tick_B_902_905_Update_2_20260419092230.csv `
  --base-buy-strategy Tick_B_902_905_Update_2 `
  --sell Tick_S_902_905_Update_2 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --run-candidates `
  --candidate-count 5 `
  --min-estimated-retention 0.4 `
  --candidate-start 20250101 `
  --candidate-end 20251231 `
  --candidate-timeout 900 `
  --cleanup-best-candidate
```

Record:

```text
status
phase
retention_selection
candidate estimated_retention values
best_candidate
best_candidate.promotion.passed
best_candidate.rank_score.adjusted_score
cleanup_summary
strategy.db leftover check
```

- [ ] **Step 5: Create update log**

Create `docs/update_log/2026-04-19_candidate_quality_gate_retention_aware.md` with:

```markdown
# 2026-04-19 Candidate Quality Gate And Retention-Aware Selection

## 목적

후보 N개 파일럿에서 모든 후보가 `trade_count_retention<0.4`로 탈락한 문제를 완화하기 위해, 후보 실행 전 estimated_retention 선별과 실행 후 retention penalty ranking을 추가했다.

## 전체 플로우

[0. 기준 전략] -> [1. 기준 CSV] -> [2. CSV 분석] -> [3. 후보 pool] -> [4. Retention-Aware 선별] -> [5. 후보 백테스트] -> [6. Retention-Penalized Ranking] -> [7. best_candidate]

## 변경 사항

- `cli/research_retention.py` 추가
- estimated_retention 계산
- retention-aware selection
- fallback 정책
- retention penalty / adjusted_score
- CLI 옵션 추가
- 리포트 섹션 추가

## 검증

실제 명령과 결과를 기록한다.

## 파일럿

tick retention pilot 결과를 기록한다.

## 남은 리스크

- estimated_retention은 baseline executed trade 기준 추정치다.
- 신규 거래 생성 가능성은 사전 추정하지 못한다.
- promotion gate는 여전히 엄격하므로 후보가 계속 탈락할 수 있다.
- 최종 채택 전 WFO/promote 검증은 필요하다.
```

- [ ] **Step 6: Commit update log**

Run:

```powershell
git diff --check
git add docs/update_log/2026-04-19_candidate_quality_gate_retention_aware.md
git commit -m "거래 유지율 후보 품질 개선 기록을 남긴다" -m "Retention-Aware 후보 선별과 retention penalty ranking 변경 사항, 검증 결과, tick 파일럿 결과를 업데이트 로그로 기록했다.

Constraint: best_candidate는 promotion 통과를 의미하지 않음
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
Tested: python -m pytest tests/unit/ -q
Tested: python scripts/verify_nonrelease_sync.py"
```

---

## Final Verification Checklist

- [ ] `python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q` passes.
- [ ] `python -m pytest tests/unit/ -q` passes.
- [ ] `python scripts/verify_nonrelease_sync.py` passes.
- [ ] tick retention pilot was attempted and recorded.
- [ ] candidate strategies are cleaned when `--cleanup-best-candidate` is used.
- [ ] WFO remains absent from `discovery research`.
- [ ] Promotion gate `min_trade_count_retention=0.4` is not relaxed.

## Plan Self-Review Notes

- Spec coverage: retention estimation, selection, fallback, ranking penalty, CLI, report, validation, and pilot are covered.
- Scope: this plan does not implement multi-round regeneration, WFO, promotion gate relaxation, or core engine changes.
- Type consistency: `min_estimated_retention`, `allow_retention_fallback`, `use_retention_penalty`, `candidate_pool_multiplier`, `retention_selection`, `retention_estimate`, `retention_filter_passed`, `retention_fallback_used`, `retention_penalty`, and `adjusted_score` match the spec.
