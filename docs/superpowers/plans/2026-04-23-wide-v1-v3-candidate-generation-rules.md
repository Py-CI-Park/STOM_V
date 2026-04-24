# Wide v1 v3 Candidate Generation Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `best_feature_mix_v3` candidate generation so Wide v1 can use `WideV1IterationV2_20260423__cand005` as the new reference best and run a candidate_count=10 v3 loop against the same wide score baseline.

**Architecture:** Keep the v3 candidate construction in a focused pure helper module and wire it through the existing discovery research loop. Reuse the existing `iteration_v2_*` CLI/config fields for the new `best_feature_mix_v3` mode to keep the PR narrow, but return/report the generated metadata under `iteration_v3` so v2 and v3 results remain distinguishable. Ranking continues to use `score_reference_csv` and the existing reference score path from PR #21.

**Tech Stack:** Python 3, pytest, existing STOM CLI modules under `cli/`, existing research loop/report/subcommand tests under `tests/unit/`.

---

## File Structure

- Create `cli/research_iteration_v3.py`
  - Pure helpers for parsing the two-condition cand005 best expression.
  - Builds v3 runnable candidates for `v3_tighten_secondary`, `v3_repair_trade_amount`, and `v3_replace_secondary`.
  - Carries `v3_control_keep_best` as report metadata without re-running the cand005 control.

- Create `tests/unit/test_research_iteration_v3.py`
  - Unit tests for expression parsing, candidate family generation, control metadata, low-retention filtering, and duplicate removal.

- Modify `cli/research_loop.py`
  - Import the v3 helper.
  - Allow `iteration_v2_mode='best_feature_mix_v3'`.
  - Invoke the v3 helper before retention annotation/selection.
  - Return `iteration_v3` metadata in results and errors that already include iteration metadata.

- Modify `tests/unit/test_research_loop.py`
  - Add config validation/plan assertions for `best_feature_mix_v3`.
  - Add a run test proving v3 generated expressions are used by `_execute_candidate_spec`.

- Modify `cli/subcommands.py`
  - Extend `--iteration-v2-mode` choices to include `best_feature_mix_v3`.

- Modify `tests/unit/test_subcommands.py`
  - Add parser and handler assertions for the new mode value.

- Modify `cli/research_report.py`
  - Include `iteration_v3` in the normalized report.
  - Render a `## Iteration Loop v3 Candidate Generation` section with type counts and control metadata.

- Modify `tests/unit/test_research_report.py`
  - Add report rendering assertions for v3 metadata.

- Create after verification: `docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md`
  - Implementation summary and verification evidence.

- Create after runtime execution: `docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v3.md`
  - Actual v3 candidate_count=10 execution result.

- Create after runtime execution: `docs/pr/2026-04-23_wide_v1_v3_candidate_generation_rules_pr.md`
  - PR report with summary, test plan, result, and remaining risk.

---

### Task 1: Pure v3 Candidate Helper

**Files:**
- Create: `cli/research_iteration_v3.py`
- Create: `tests/unit/test_research_iteration_v3.py`
- Reuse: `cli/research_iteration_v2.py`

- [ ] **Step 1: Write the failing helper tests**

Create `tests/unit/test_research_iteration_v3.py` with this content:

```python
from cli.research_iteration_v3 import (
    build_v3_candidate_pool,
    parse_best_expression_conditions,
)


BEST_EXPRESSION = '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4'
BEST_CONTEXT = {
    'strategy_name': 'WideV1IterationV2_20260423__cand005',
    'expression': BEST_EXPRESSION,
    'reference_adjusted_score': 13497.662902097409,
}


def _candidate(feature, lower, upper, score=1.0, retention=0.9):
    return {
        'feature': feature,
        'operator': 'between',
        'lower_bound': lower,
        'upper_bound': upper,
        'score': score,
        'combined_score': score,
        'source': 'quantile',
        'retention_estimate': {'estimated_retention': retention},
        'retention_filter_passed': True,
        'retention_fallback_used': False,
        'expression': f'{lower} <= {feature[2:]} < {upper}',
    }


def test_parse_best_expression_conditions_parses_primary_and_trade_amount():
    conditions = parse_best_expression_conditions(
        BEST_EXPRESSION,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
    )

    assert [item['feature'] for item in conditions] == ['B_시가총액', 'B_당일거래대금']
    assert conditions[0]['lower_bound'] == 66.999
    assert conditions[0]['upper_bound'] == 2580.0
    assert conditions[1]['lower_bound'] == 1805.7
    assert conditions[1]['upper_bound'] == 3654.4


def test_build_v3_candidate_pool_returns_control_metadata_without_running_control():
    result = build_v3_candidate_pool(
        [],
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도'],
    )

    assert result['status'] == 'ok'
    assert result['mode'] == 'best_feature_mix_v3'
    assert result['control_candidate']['v3_candidate_type'] == 'v3_control_keep_best'
    assert result['control_candidate']['strategy_name'] == 'WideV1IterationV2_20260423__cand005'
    assert result['control_candidate']['expression'] == BEST_EXPRESSION
    assert result['control_candidate']['skip_backtest'] is True
    assert result['type_counts']['v3_control_keep_best'] == 1
    assert result['candidates'] == []


def test_build_v3_candidate_pool_generates_tighten_repair_and_replace_families():
    analysis_candidates = [
        _candidate('B_체결강도', 0.039, 54.89, score=8.0),
        _candidate('B_등락율', 15.894, 25.0, score=7.0),
        _candidate('B_당일거래대금', 1500.0, 3654.4, score=6.0),
        _candidate('B_당일거래대금', 178.999, 1805.7, score=5.0),
    ]

    result = build_v3_candidate_pool(
        analysis_candidates,
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도', 'B_등락율', 'B_당일거래대금'],
    )

    expressions_by_type = {
        item['v3_candidate_type']: item['expression']
        for item in result['candidates']
    }
    assert 'v3_tighten_secondary' in result['type_counts']
    assert 'v3_repair_trade_amount' in result['type_counts']
    assert 'v3_replace_secondary' in result['type_counts']
    assert (
        '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4 and '
        in expressions_by_type['v3_tighten_secondary']
    )
    assert (
        '66.999 <= 시가총액 < 2_580 and 1500.0 <= 당일거래대금 < 3654.4'
        == expressions_by_type['v3_repair_trade_amount']
    )
    assert (
        '66.999 <= 시가총액 < 2_580 and 0.039 <= 체결강도 < 54.89'
        == expressions_by_type['v3_replace_secondary']
    )


def test_build_v3_candidate_pool_filters_low_retention_when_retention_is_known():
    analysis_candidates = [
        _candidate('B_체결강도', 0.039, 54.89, retention=0.2),
        _candidate('B_등락율', 15.894, 25.0, retention=0.8),
    ]

    result = build_v3_candidate_pool(
        analysis_candidates,
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도', 'B_등락율'],
        min_estimated_retention=0.4,
    )

    expressions = [item['expression'] for item in result['candidates']]
    assert all('체결강도' not in expression for expression in expressions)
    assert any('등락율' in expression for expression in expressions)


def test_build_v3_candidate_pool_removes_duplicate_expressions():
    analysis_candidates = [
        _candidate('B_체결강도', 0.039, 54.89, score=8.0, retention=0.90),
        _candidate('B_체결강도', 0.039, 54.89, score=9.0, retention=0.91),
    ]

    result = build_v3_candidate_pool(
        analysis_candidates,
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도'],
        retention_tolerance=0.02,
    )

    tighten = [
        item for item in result['candidates']
        if item['v3_candidate_type'] == 'v3_tighten_secondary'
    ]
    replace = [
        item for item in result['candidates']
        if item['v3_candidate_type'] == 'v3_replace_secondary'
    ]
    assert len(tighten) == 1
    assert len(replace) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v3.py -q
```

Expected:

```text
ERROR tests/unit/test_research_iteration_v3.py
ModuleNotFoundError: No module named 'cli.research_iteration_v3'
```

- [ ] **Step 3: Add the pure helper implementation**

Create `cli/research_iteration_v3.py` with this content:

```python
"""Pure helpers for Wide v1 iteration loop v3 candidate generation."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re

from cli.condition_generator import candidate_to_expression
from cli.research_iteration_v2 import (
    candidate_from_expression,
    candidate_signature,
    filter_duplicate_v2_candidates,
)


def _score_value(candidate: dict, key: str) -> float:
    return float(candidate.get(key, candidate.get('score', 0.0)) or 0.0)


def _retention_value(candidate: dict) -> float | None:
    estimate = candidate.get('retention_estimate') or {}
    value = estimate.get('estimated_retention')
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _passes_min_retention(candidate: dict, min_estimated_retention: float) -> bool:
    retention = _retention_value(candidate)
    return retention is None or retention >= min_estimated_retention


def _condition_expression(condition: dict) -> str:
    return condition.get('expression') or candidate_to_expression(condition, runtime_context=True)


def parse_best_expression_conditions(
    expression: str,
    *,
    primary_feature: str,
    trade_amount_feature: str,
) -> list[dict]:
    parts = [part.strip() for part in re.split(r'\s+and\s+', expression) if part.strip()]
    if len(parts) != 2:
        raise ValueError(f'best_feature_mix_v3 requires exactly two best-expression conditions: {expression}')
    return [
        candidate_from_expression(parts[0], feature=primary_feature),
        candidate_from_expression(parts[1], feature=trade_amount_feature),
    ]


def _combo_candidate(
    conditions: list[dict],
    *,
    candidate_type: str,
    source: str,
    primary_feature: str,
    secondary_feature: str | None = None,
) -> dict:
    item = {
        'feature': conditions[0].get('feature'),
        'operator': conditions[0].get('operator'),
        'lower_bound': conditions[0].get('lower_bound'),
        'upper_bound': conditions[0].get('upper_bound'),
        'threshold': conditions[0].get('threshold'),
        'score': sum(_score_value(condition, 'score') for condition in conditions),
        'combined_score': sum(_score_value(condition, 'combined_score') for condition in conditions),
        'source': source,
        'primary_feature': primary_feature,
        'secondary_feature': secondary_feature,
        'v3_candidate_type': candidate_type,
        'conditions': [deepcopy(condition) for condition in conditions],
    }
    item['expression'] = ' and '.join(_condition_expression(condition) for condition in item['conditions'])
    return item


def _control_candidate(best_context: dict, best_conditions: list[dict]) -> dict:
    return {
        'strategy_name': best_context.get('strategy_name'),
        'expression': best_context.get('expression'),
        'reference_adjusted_score': best_context.get('reference_adjusted_score'),
        'v3_candidate_type': 'v3_control_keep_best',
        'skip_backtest': True,
        'conditions': [deepcopy(condition) for condition in best_conditions],
    }


def _same_condition(first: dict, second: dict) -> bool:
    return candidate_signature(first) == candidate_signature(second)


def build_v3_candidate_pool(
    analysis_candidates: list[dict],
    *,
    best_context: dict | None = None,
    primary_feature: str = 'B_시가총액',
    trade_amount_feature: str = 'B_당일거래대금',
    secondary_features: list[str] | None = None,
    min_estimated_retention: float = 0.4,
    retention_tolerance: float = 0.02,
) -> dict:
    if not best_context:
        return {
            'status': 'disabled',
            'mode': 'best_feature_mix_v3',
            'candidates': [],
            'candidate_count': 0,
            'type_counts': {},
            'reason': 'best_context is required',
        }

    best_conditions = parse_best_expression_conditions(
        best_context.get('expression') or '',
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
    )
    primary_condition, trade_amount_condition = best_conditions
    secondary_feature_set = set(secondary_features or [])
    candidates = []

    secondary_candidates = [
        item for item in analysis_candidates
        if item.get('feature') in secondary_feature_set
        and item.get('feature') not in {primary_feature, trade_amount_feature}
        and _passes_min_retention(item, min_estimated_retention)
    ]
    for secondary in secondary_candidates:
        candidates.append(_combo_candidate(
            [primary_condition, trade_amount_condition, secondary],
            candidate_type='v3_tighten_secondary',
            source='v3_tighten_secondary',
            primary_feature=primary_feature,
            secondary_feature=secondary.get('feature'),
        ))
        candidates.append(_combo_candidate(
            [primary_condition, secondary],
            candidate_type='v3_replace_secondary',
            source='v3_replace_secondary',
            primary_feature=primary_feature,
            secondary_feature=secondary.get('feature'),
        ))

    trade_amount_candidates = [
        item for item in analysis_candidates
        if item.get('feature') == trade_amount_feature
        and not _same_condition(item, trade_amount_condition)
        and _passes_min_retention(item, min_estimated_retention)
    ]
    for trade_amount in trade_amount_candidates:
        candidates.append(_combo_candidate(
            [primary_condition, trade_amount],
            candidate_type='v3_repair_trade_amount',
            source='v3_repair_trade_amount',
            primary_feature=primary_feature,
            secondary_feature=trade_amount_feature,
        ))

    candidates = filter_duplicate_v2_candidates(candidates, retention_tolerance=retention_tolerance)
    control = _control_candidate(best_context, best_conditions)
    type_counts = Counter(item.get('v3_candidate_type') for item in candidates)
    type_counts[control['v3_candidate_type']] += 1

    return {
        'status': 'ok',
        'mode': 'best_feature_mix_v3',
        'primary_feature': primary_feature,
        'trade_amount_feature': trade_amount_feature,
        'secondary_features': list(secondary_features or []),
        'control_candidate': control,
        'candidates': candidates,
        'candidate_count': len(candidates),
        'type_counts': dict(type_counts),
    }
```

- [ ] **Step 4: Run the helper tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v3.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add cli/research_iteration_v3.py tests/unit/test_research_iteration_v3.py
git commit -m "Wide v1 v3 후보 생성 helper를 추가한다" -m "cand005 best expression을 기준으로 tighten, repair, replace 후보군과 control metadata를 생성하는 순수 helper를 추가했다.

Constraint: cand005 control은 기존 CSV/reference score를 쓰는 메타데이터로만 보존하고 재실행 후보에는 넣지 않음
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_iteration_v3.py -q
Not-tested: discovery research loop wiring, runtime candidate_count=10"
```

---

### Task 2: Research Loop Wiring

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing research loop tests**

Append these tests near the existing iteration v2 tests in `tests/unit/test_research_loop.py`:

```python
def test_validate_research_iteration_accepts_best_feature_mix_v3(tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)

    result = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='V3Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
        )
    )

    assert result['status'] == 'ok'


def test_build_iteration_plan_includes_best_feature_mix_v3():
    plan = research_loop._build_iteration_plan(
        ResearchLoopConfig(
            name='V3Run',
            run_candidate=False,
            run_candidates=True,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도,B_등락율,B_당일거래대금',
        )
    )

    assert plan['iteration_v2_mode'] == 'best_feature_mix_v3'
    assert plan['iteration_v2_best_candidate'] == 'WideV1IterationV2_20260423__cand005'
    assert plan['iteration_v2_secondary_features'] == ['B_체결강도', 'B_등락율', 'B_당일거래대금']


def test_run_research_iteration_applies_v3_candidate_pool(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text(
        'B_시가총액,B_체결강도,B_당일거래대금,수익률,종목명,매수시간,매도시간,매수가,매도가,수익금\n'
        '100,10,2000,-1,A,20250101090000,20250101090100,100,99,-1\n'
        '200,20,3000,1,B,20250101090200,20250101090300,100,101,1\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': [
                '0.039 <= 체결강도 < 54.89',
                '1500 <= 당일거래대금 < 3654.4',
            ],
            'selected_candidates': [
                {
                    'feature': 'B_체결강도',
                    'operator': 'between',
                    'lower_bound': 0.039,
                    'upper_bound': 54.89,
                    'score': 8.0,
                    'combined_score': 8.0,
                    'retention_estimate': {'estimated_retention': 0.9},
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'feature': 'B_당일거래대금',
                    'operator': 'between',
                    'lower_bound': 1500.0,
                    'upper_bound': 3654.4,
                    'score': 6.0,
                    'combined_score': 6.0,
                    'retention_estimate': {'estimated_retention': 0.9},
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
            ],
        },
    )
    executed_specs = []
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: executed_specs.append(spec) or {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {'trade_count_retention': 0.9},
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': 1.0,
                'trade_count': 2.0,
                'trade_count_retention': 0.9,
                'date_concentration': 0.0,
                'symbol_concentration': 0.0,
            },
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V3Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도,B_당일거래대금',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert result['iteration_v3']['status'] == 'ok'
    assert result['iteration_v3']['type_counts']['v3_control_keep_best'] == 1
    assert executed_specs
    assert any('1805.7 <= 당일거래대금 < 3654.4 and' in spec['expression'] for spec in executed_specs)
    assert all(spec['expression'] != result['iteration_v3']['control_candidate']['expression'] for spec in executed_specs)
```

- [ ] **Step 2: Run the targeted failing tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_validate_research_iteration_accepts_best_feature_mix_v3 tests/unit/test_research_loop.py::test_build_iteration_plan_includes_best_feature_mix_v3 tests/unit/test_research_loop.py::test_run_research_iteration_applies_v3_candidate_pool -q
```

Expected:

```text
At least test_validate_research_iteration_accepts_best_feature_mix_v3 fails with invalid_iteration_v2_mode.
```

- [ ] **Step 3: Modify `cli/research_loop.py` imports**

Change the imports at the top from:

```python
from cli.research_iteration_v2 import build_v2_candidate_pool, candidate_from_expression
```

to:

```python
from cli.research_iteration_v2 import build_v2_candidate_pool, candidate_from_expression
from cli.research_iteration_v3 import build_v3_candidate_pool
```

- [ ] **Step 4: Allow the new mode in validation**

In `validate_research_iteration_config()`, replace:

```python
    if config.run_candidates and config.iteration_v2_mode and config.iteration_v2_mode != 'best_feature_mix':
        return _error(
            'invalid_iteration_v2_mode',
            'iteration_v2_mode must be empty or best_feature_mix',
        )
```

with:

```python
    allowed_iteration_modes = {'best_feature_mix', 'best_feature_mix_v3'}
    if config.run_candidates and config.iteration_v2_mode and config.iteration_v2_mode not in allowed_iteration_modes:
        return _error(
            'invalid_iteration_v2_mode',
            'iteration_v2_mode must be empty, best_feature_mix, or best_feature_mix_v3',
        )
```

- [ ] **Step 5: Add a metadata helper**

Add this helper near `_build_iteration_plan()`:

```python
def _iteration_generation_metadata(iteration_v2: dict | None, iteration_v3: dict | None) -> dict:
    metadata = {}
    if iteration_v2:
        metadata['iteration_v2'] = iteration_v2
    if iteration_v3:
        metadata['iteration_v3'] = iteration_v3
    return metadata
```

- [ ] **Step 6: Wire v3 generation into `run_research_iteration()`**

In `run_research_iteration()`, replace the block that initializes and handles `iteration_v2` with this block:

```python
    iteration_v2 = None
    iteration_v3 = None
    if config.iteration_v2_mode == 'best_feature_mix':
        best_context = {
            'strategy_name': config.iteration_v2_best_candidate,
            'expression': config.iteration_v2_best_expression,
            'source_candidate': candidate_from_expression(
                config.iteration_v2_best_expression,
                feature=config.iteration_v2_primary_feature,
            ),
        }
        iteration_v2 = build_v2_candidate_pool(
            expression_candidates,
            best_context=best_context,
            primary_feature=config.iteration_v2_primary_feature,
            secondary_features=_split_csv_values(config.iteration_v2_secondary_features),
            include_secondary_only=config.iteration_v2_include_secondary_only,
            max_secondary_only=config.iteration_v2_max_secondary_only,
            retention_tolerance=config.iteration_v2_duplicate_retention_tolerance,
        )
        expression_candidates = iteration_v2.get('candidates') or []
        expression_result = {
            **expression_result,
            'selected_candidates': expression_candidates,
            'expressions': [candidate['expression'] for candidate in expression_candidates],
            'candidate_count': len(expression_candidates),
            'iteration_v2': iteration_v2,
        }
        expressions = expression_result['expressions']
    elif config.iteration_v2_mode == 'best_feature_mix_v3':
        best_context = {
            'strategy_name': config.iteration_v2_best_candidate,
            'expression': config.iteration_v2_best_expression,
        }
        iteration_v3 = build_v3_candidate_pool(
            expression_candidates,
            best_context=best_context,
            primary_feature=config.iteration_v2_primary_feature,
            secondary_features=_split_csv_values(config.iteration_v2_secondary_features),
            min_estimated_retention=config.min_estimated_retention,
            retention_tolerance=config.iteration_v2_duplicate_retention_tolerance,
        )
        expression_candidates = iteration_v3.get('candidates') or []
        expression_result = {
            **expression_result,
            'selected_candidates': expression_candidates,
            'expressions': [candidate['expression'] for candidate in expression_candidates],
            'candidate_count': len(expression_candidates),
            'iteration_v3': iteration_v3,
        }
        expressions = expression_result['expressions']
```

- [ ] **Step 7: Include v3 metadata in existing returns**

In `run_research_iteration()`, replace each occurrence of:

```python
            **({'iteration_v2': iteration_v2} if iteration_v2 else {}),
```

and:

```python
        **({'iteration_v2': iteration_v2} if iteration_v2 else {}),
```

with:

```python
            **_iteration_generation_metadata(iteration_v2, iteration_v3),
```

or:

```python
        **_iteration_generation_metadata(iteration_v2, iteration_v3),
```

using the indentation required by the surrounding return dictionary.

- [ ] **Step 8: Run research loop tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_validate_research_iteration_accepts_best_feature_mix_v3 tests/unit/test_research_loop.py::test_build_iteration_plan_includes_best_feature_mix_v3 tests/unit/test_research_loop.py::test_run_research_iteration_applies_v3_candidate_pool tests/unit/test_research_loop.py::test_run_research_iteration_applies_v2_candidate_pool -q
```

Expected:

```text
4 passed
```

- [ ] **Step 9: Commit Task 2**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "Wide v1 v3 후보 생성을 research loop에 연결한다" -m "기존 iteration_v2 옵션 표면에 best_feature_mix_v3 mode를 추가하고, cand005 기준 v3 후보 pool을 retention-aware 후보 실행 경로에 연결했다.

Constraint: CLI 옵션 이름은 이번 PR에서 일반화하지 않고 기존 iteration_v2_* 계약을 재사용함
Rejected: iteration_mode 전체 리네이밍 | 기존 CLI/report/test 변경 범위가 커져 v3 후보 생성 목적을 벗어남
Confidence: high
Scope-risk: moderate
Tested: targeted research_loop v2/v3 unit tests
Not-tested: full discovery research runtime"
```

---

### Task 3: CLI Mode Parsing

**Files:**
- Modify: `cli/subcommands.py`
- Modify: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Write failing CLI tests**

Add these tests near the existing iteration v2 parser/handler tests in `tests/unit/test_subcommands.py`:

```python
def test_discovery_research_parser_accepts_iteration_v2_mode_v3():
    parser = build_parser()

    args = parser.parse_args([
        'discovery',
        'research',
        'WideV1IterationV3_20260423',
        '--input',
        'cand005.csv',
        '--score-reference-csv',
        'wide.csv',
        '--base-buy-strategy',
        'WideV1IterationV2_20260423__cand005',
        '--sell',
        'ResearchTest_Tick_S_090000_092800_Wide_20260419',
        '--start',
        '20250101',
        '--end',
        '20251231',
        '--run-candidates',
        '--candidate-count',
        '10',
        '--iteration-v2-mode',
        'best_feature_mix_v3',
        '--iteration-v2-best-candidate',
        'WideV1IterationV2_20260423__cand005',
        '--iteration-v2-best-expression',
        '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
    ])

    assert args.iteration_v2_mode == 'best_feature_mix_v3'
    assert args.candidate_count == 10
    assert args.score_reference_csv == 'wide.csv'


def test_discovery_research_handler_passes_iteration_v2_mode_v3(monkeypatch):
    payloads = []

    class Controller:
        def run_research_iteration(self, **payload):
            payloads.append(payload)
            return {'status': 'ok'}

    monkeypatch.setattr('cli.subcommands.get_controller', lambda: Controller())

    code = handle_subcommand([
        'discovery',
        'research',
        'WideV1IterationV3_20260423',
        '--input',
        'cand005.csv',
        '--score-reference-csv',
        'wide.csv',
        '--base-buy-strategy',
        'WideV1IterationV2_20260423__cand005',
        '--sell',
        'ResearchTest_Tick_S_090000_092800_Wide_20260419',
        '--start',
        '20250101',
        '--end',
        '20251231',
        '--run-candidates',
        '--candidate-count',
        '10',
        '--iteration-v2-mode',
        'best_feature_mix_v3',
        '--iteration-v2-best-candidate',
        'WideV1IterationV2_20260423__cand005',
        '--iteration-v2-best-expression',
        '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
        '--iteration-v2-secondary-features',
        'B_체결강도,B_등락율,B_당일거래대금',
    ])

    assert code == 0
    assert payloads[0]['iteration_v2_mode'] == 'best_feature_mix_v3'
    assert payloads[0]['candidate_count'] == 10
    assert payloads[0]['score_reference_csv'] == 'wide.csv'
```

- [ ] **Step 2: Run tests to verify parser failure**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_mode_v3 tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_v2_mode_v3 -q
```

Expected:

```text
ArgumentParser exits because best_feature_mix_v3 is not in the choices list.
```

- [ ] **Step 3: Extend parser choices**

In `cli/subcommands.py`, replace:

```python
    disc_research.add_argument('--iteration-v2-mode', choices=['best_feature_mix'], default='')
```

with:

```python
    disc_research.add_argument('--iteration-v2-mode', choices=['best_feature_mix', 'best_feature_mix_v3'], default='')
```

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_mode_v3 tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_v2_mode_v3 tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_v2_options -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git add cli/subcommands.py tests/unit/test_subcommands.py
git commit -m "Wide v1 v3 CLI mode 값을 허용한다" -m "discovery research의 기존 iteration-v2-mode 옵션에서 best_feature_mix_v3 값을 받을 수 있게 해 v3 후보 생성 경로를 CLI에서 실행 가능하게 했다.

Constraint: 옵션 이름은 기존 실행 스크립트와 계획 문서 호환성을 위해 유지함
Confidence: high
Scope-risk: narrow
Tested: targeted subcommands parser and handler tests
Not-tested: live CLI runtime"
```

---

### Task 4: Report Rendering

**Files:**
- Modify: `cli/research_report.py`
- Modify: `tests/unit/test_research_report.py`

- [ ] **Step 1: Write failing report test**

Add this test near the existing iteration v2 report tests in `tests/unit/test_research_report.py`:

```python
def test_render_research_report_markdown_contains_iteration_v3_section():
    markdown = render_research_report_markdown({
        'status': 'ok',
        'name': 'WideV1IterationV3_20260423',
        'baseline_csv': 'cand005.csv',
        'score_reference_csv': 'wide.csv',
        'trade_counts': {'baseline': 36096, 'candidate': 35000, 'common': 34000},
        'iteration_v3': {
            'status': 'ok',
            'mode': 'best_feature_mix_v3',
            'primary_feature': 'B_시가총액',
            'trade_amount_feature': 'B_당일거래대금',
            'secondary_features': ['B_체결강도', 'B_등락율', 'B_당일거래대금'],
            'candidate_count': 10,
            'type_counts': {
                'v3_tighten_secondary': 4,
                'v3_repair_trade_amount': 3,
                'v3_replace_secondary': 3,
                'v3_control_keep_best': 1,
            },
            'control_candidate': {
                'strategy_name': 'WideV1IterationV2_20260423__cand005',
                'expression': (
                    '66.999 <= 시가총액 < 2_580 and '
                    '1805.7 <= 당일거래대금 < 3654.4'
                ),
                'reference_adjusted_score': 13497.662902097409,
                'skip_backtest': True,
            },
        },
    })

    assert '## Iteration Loop v3 Candidate Generation' in markdown
    assert '- mode: best_feature_mix_v3' in markdown
    assert 'v3_tighten_secondary: 4' in markdown
    assert 'v3_control_keep_best: 1' in markdown
    assert 'control_strategy_name: WideV1IterationV2_20260423__cand005' in markdown
    assert 'control_skip_backtest: True' in markdown
```

- [ ] **Step 2: Run the failing test**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py::test_render_research_report_markdown_contains_iteration_v3_section -q
```

Expected:

```text
FAIL because the markdown does not contain the Iteration Loop v3 section.
```

- [ ] **Step 3: Normalize `iteration_v3` in report data**

In `cli/research_report.py`, find the dictionary returned by the report normalization helper that currently includes:

```python
        'iteration_v2': result.get('iteration_v2'),
```

Add the next line:

```python
        'iteration_v3': result.get('iteration_v3'),
```

- [ ] **Step 4: Add the v3 report section**

Add this function after `_append_iteration_v2_section()`:

```python
def _append_iteration_v3_section(lines: list[str], report: dict) -> None:
    iteration_v3 = report.get('iteration_v3') or {}
    if not iteration_v3 or iteration_v3.get('status') == 'disabled':
        return

    lines.extend(['', '## Iteration Loop v3 Candidate Generation'])
    for key in (
        'status',
        'mode',
        'primary_feature',
        'trade_amount_feature',
        'secondary_features',
        'candidate_count',
    ):
        lines.append(f"- {key}: {iteration_v3.get(key)}")
    type_counts = iteration_v3.get('type_counts') or {}
    if type_counts:
        lines.append('- type_counts:')
        for key, value in type_counts.items():
            lines.append(f"  - {key}: {value}")
    control = iteration_v3.get('control_candidate') or {}
    if control:
        lines.append(f"- control_strategy_name: {control.get('strategy_name')}")
        lines.append(f"- control_expression: {control.get('expression')}")
        lines.append(f"- control_reference_adjusted_score: {control.get('reference_adjusted_score')}")
        lines.append(f"- control_skip_backtest: {control.get('skip_backtest')}")
```

- [ ] **Step 5: Call the v3 report section**

In `render_research_report_markdown()`, replace:

```python
    _append_iteration_v2_section(lines, report)
```

with:

```python
    _append_iteration_v2_section(lines, report)
    _append_iteration_v3_section(lines, report)
```

- [ ] **Step 6: Run report tests**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py::test_render_research_report_markdown_contains_iteration_v3_section tests/unit/test_research_report.py::test_render_research_report_markdown_contains_iteration_v2_section tests/unit/test_research_report.py::test_render_research_report_markdown_omits_disabled_iteration_v2_section -q
```

Expected:

```text
3 passed
```

- [ ] **Step 7: Commit Task 4**

Run:

```powershell
git add cli/research_report.py tests/unit/test_research_report.py
git commit -m "Wide v1 v3 후보 생성 리포트를 표시한다" -m "research report가 best_feature_mix_v3 후보 family 분포와 cand005 control metadata를 별도 섹션으로 표시하게 했다.

Constraint: v2 report section은 기존 이름과 동작을 유지해야 한다
Confidence: high
Scope-risk: narrow
Tested: targeted research_report v2/v3 unit tests
Not-tested: runtime-generated markdown report"
```

---

### Task 5: Focused Verification and Implementation Docs

**Files:**
- Create: `docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md`

- [ ] **Step 1: Run focused unit tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py -q | Tee-Object -FilePath backtest\temp\wide_v1_v3_focused_tests.txt
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run lint and sync guard**

Run:

```powershell
python -m ruff check cli/research_iteration_v3.py cli/research_loop.py cli/subcommands.py cli/research_report.py tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py | Tee-Object -FilePath backtest\temp\wide_v1_v3_ruff.txt
python scripts/verify_nonrelease_sync.py | Tee-Object -FilePath backtest\temp\wide_v1_v3_sync_guard.txt
git diff --check | Tee-Object -FilePath backtest\temp\wide_v1_v3_diff_check.txt
```

Expected:

```text
ruff reports All checks passed.
verify_nonrelease_sync.py reports PASS.
git diff --check prints no errors.
```

- [ ] **Step 3: Run full unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q | Tee-Object -FilePath backtest\temp\wide_v1_v3_full_unit_tests.txt
```

Expected:

```text
All unit tests pass. Existing warnings may match the current scipy/binance/websockets warning set.
```

- [ ] **Step 4: Generate implementation update log from captured verification output**

Run:

```powershell
@'
from __future__ import annotations

from pathlib import Path

def read_log(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise SystemExit(f'missing verification log: {path}')
    return file_path.read_text(encoding='utf-8').strip()

focused = read_log('backtest/temp/wide_v1_v3_focused_tests.txt')
ruff = read_log('backtest/temp/wide_v1_v3_ruff.txt')
sync_guard = read_log('backtest/temp/wide_v1_v3_sync_guard.txt')
diff_check = read_log('backtest/temp/wide_v1_v3_diff_check.txt')
full = read_log('backtest/temp/wide_v1_v3_full_unit_tests.txt')

content = f"""# Wide v1 v3 후보 생성 규칙 구현

## 목적

PR #21 이후 `WideV1IterationV2_20260423__cand005`가 같은 wide baseline 기준에서 `cand003`보다 높은 reference score를 기록했으므로, cand005를 새 reference best로 삼는 v3 후보 생성 경로를 추가했다.

## 변경 사항

- `best_feature_mix_v3` 후보 생성 helper를 추가했다.
- v3 후보군을 `v3_tighten_secondary`, `v3_repair_trade_amount`, `v3_replace_secondary`로 나눴다.
- `v3_control_keep_best`는 cand005 기존 결과를 report metadata로 보존하고 재실행 후보에서는 제외했다.
- 기존 `iteration_v2_*` CLI/config 옵션 표면에서 `best_feature_mix_v3` mode를 허용했다.
- research report에 v3 후보 family 분포와 control metadata를 표시했다.

## 검증

```text
focused tests:
  python -m pytest tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py -q
  output:
{focused}

ruff:
  python -m ruff check cli/research_iteration_v3.py cli/research_loop.py cli/subcommands.py cli/research_report.py tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py
  output:
{ruff}

sync guard:
  python scripts/verify_nonrelease_sync.py
  output:
{sync_guard}

diff check:
  git diff --check
  output:
{diff_check or 'no output'}

full unit tests:
  python -m pytest tests/unit/ -q
  output:
{full}
```

## 남은 리스크

- v3 candidate_count=10 full-year runtime은 별도 실행 결과 문서에서 기록한다.
- cand005 control은 재실행하지 않으므로 동일 조건 재현성 검증은 이번 구현 단계에서 생략한다.
- v3 best도 최종 채택이 아니며 promote/WFO 검증이 필요하다.
"""

Path('docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md').write_text(content, encoding='utf-8')
print('wrote docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md')
'@ | python -
```

Expected:

```text
wrote docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md
```

- [ ] **Step 5: Commit Task 5**

Run:

```powershell
git add docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md
git commit -m "Wide v1 v3 후보 생성 구현 기록을 남긴다" -m "best_feature_mix_v3 helper, loop wiring, CLI mode, report 표시 변경과 검증 결과를 update log에 기록했다.

Constraint: v3 full-year runtime 실행 결과는 별도 pilot log로 분리함
Confidence: high
Scope-risk: narrow
Tested: focused unit tests, ruff, verify_nonrelease_sync.py, full unit tests, git diff --check
Not-tested: v3 candidate_count=10 runtime, promote, WFO"
```

---

### Task 6: Runtime v3 Execution and PR Docs

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v3.md`
- Create: `docs/pr/2026-04-23_wide_v1_v3_candidate_generation_rules_pr.md`
- Modify: `docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md`

- [ ] **Step 1: Confirm required runtime CSVs exist**

Run:

```powershell
Test-Path C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv
Test-Path C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
Test-Path C:\System_Trading\STOM\STOM_V.wt-dev\_database\strategy.db
```

Expected:

```text
True
True
True
```

- [ ] **Step 2: Run v3 candidate_count=10**

Run from `C:\System_Trading\STOM\STOM_V.wt-wide-v3`:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
python -m cli.main discovery research WideV1IterationV3_20260423 `
  --input C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv `
  --score-reference-csv C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv `
  --base-buy-strategy WideV1IterationV2_20260423__cand005 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --betting 20 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --run-candidates `
  --candidate-count 10 `
  --candidate-timeout 900 `
  --iteration-v2-mode best_feature_mix_v3 `
  --iteration-v2-best-candidate WideV1IterationV2_20260423__cand005 `
  --iteration-v2-best-expression "66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4" `
  --iteration-v2-primary-feature B_시가총액 `
  --iteration-v2-secondary-features B_체결강도,B_등락율,B_당일거래대금,B_시분초,B_회전율,B_전일동시간비 `
  | Tee-Object -FilePath backtest\temp\wide_v1_iteration_v3_20260423.json
```

Expected:

```text
JSON output is written to backtest\temp\wide_v1_iteration_v3_20260423.json.
The JSON status is either ok or an explicit error phase with diagnostics.
```

- [ ] **Step 3: Generate runtime pilot log and PR report from observed JSON**

Run:

```powershell
@'
from __future__ import annotations

import json
from pathlib import Path

result_path = Path('backtest/temp/wide_v1_iteration_v3_20260423.json')
result = json.loads(result_path.read_text(encoding='utf-8'))
pilot_path = Path('docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v3.md')
pr_path = Path('docs/pr/2026-04-23_wide_v1_v3_candidate_generation_rules_pr.md')
update_path = Path('docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md')

iteration_v3 = result.get('iteration_v3') or {}
best = result.get('best_candidate') or {}
best_rank = best.get('rank_score') or {}
candidates = result.get('candidates') or []
type_counts = iteration_v3.get('type_counts') or {}
control = iteration_v3.get('control_candidate') or {}
decision = 'PASS_TO_V3_EXECUTION_RESULT_ANALYSIS'
control_score = control.get('reference_adjusted_score')
best_score = best_rank.get('adjusted_score')
if result.get('status') != 'ok':
    decision = 'FAIL_RUNTIME_DIAGNOSTICS'
elif control_score is not None and best_score is not None and best_score <= control_score:
    decision = 'HOLD_FOR_CANDIDATE_RULE_REVIEW'

top_lines = []
for candidate in candidates[:10]:
    rank_score = candidate.get('rank_score') or {}
    top_lines.append(
        f"- rank={candidate.get('rank')} strategy={candidate.get('strategy_name')} "
        f"score={rank_score.get('adjusted_score')} "
        f"retention={rank_score.get('trade_count_retention')} "
        f"expression={candidate.get('expression')}"
    )

pilot = f"""# Wide v1 Iteration Loop v3 Pilot

## 실행 조건

```text
name=WideV1IterationV3_20260423
input=C:\\System_Trading\\STOM\\STOM_V.wt-wide-v2\\backtest\\csv\\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv
score_reference_csv=C:\\System_Trading\\STOM\\STOM_V.wt-wide-cli-compare\\backtest\\csv\\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
base_buy_strategy=WideV1IterationV2_20260423__cand005
sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
period=20250101~20251231
time=090000~092800
avg_time=30
engines=32
candidate_count=10
mode=best_feature_mix_v3
```

## 실행 결과

```text
status={result.get('status')}
phase={result.get('phase')}
candidate_count_observed={len(candidates)}
best_candidate={best.get('strategy_name')}
best_reference_adjusted_score={best_score}
control_candidate={control.get('strategy_name')}
control_reference_adjusted_score={control_score}
decision={decision}
```

## v3 후보 family 분포

```text
{json.dumps(type_counts, ensure_ascii=False, indent=2)}
```

## 상위 후보

{chr(10).join(top_lines) if top_lines else '- runtime candidates were not produced.'}

## 남은 리스크

- v3 best는 최종 채택이 아니며 promote/WFO 검증이 필요하다.
- cand005 control은 기존 결과를 기준으로 비교했으며 동일 조건 재실행은 생략했다.
- reference score가 더 높아도 전략 자체가 손실 전략이라는 기존 리스크는 유지된다.
"""

pr = f"""# Wide v1 v3 후보 생성 규칙 PR 보고서

## Summary

- `best_feature_mix_v3` 후보 생성 helper를 추가했다.
- cand005 기준으로 tighten, repair, replace 후보군을 만들고 cand005 control metadata를 report에 표시했다.
- v3 candidate_count=10 runtime 결과를 기록했다.

## Result

```text
status={result.get('status')}
phase={result.get('phase')}
best_candidate={best.get('strategy_name')}
best_reference_adjusted_score={best_score}
control_reference_adjusted_score={control_score}
decision={decision}
```

## Test Plan

- python -m pytest tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py -q
- python -m ruff check cli/research_iteration_v3.py cli/research_loop.py cli/subcommands.py cli/research_report.py tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py
- python scripts/verify_nonrelease_sync.py
- git diff --check
- python -m pytest tests/unit/ -q
- discovery research WideV1IterationV3_20260423 candidate_count=10

## Remaining Risk

- v3 best는 최종 채택이 아니다.
- promote/WFO 검증은 아직 실행하지 않았다.
- cand005 control은 재실행하지 않고 기존 reference score를 사용했다.
"""

pilot_path.write_text(pilot, encoding='utf-8')
pr_path.write_text(pr, encoding='utf-8')

update = update_path.read_text(encoding='utf-8')
if '## Runtime v3 실행' not in update:
    update += f"""

## Runtime v3 실행

```text
status={result.get('status')}
phase={result.get('phase')}
candidate_count_observed={len(candidates)}
best_candidate={best.get('strategy_name')}
best_reference_adjusted_score={best_score}
control_reference_adjusted_score={control_score}
decision={decision}
```
"""
    update_path.write_text(update, encoding='utf-8')

print(f'wrote {pilot_path}')
print(f'wrote {pr_path}')
print(f'updated {update_path}')
'@ | python -
```

Expected:

```text
wrote docs\research\condition_research\pilot_logs\2026-04-23_wide_v1_iteration_loop_v3.md
wrote docs\pr\2026-04-23_wide_v1_v3_candidate_generation_rules_pr.md
updated docs\update_log\2026-04-23_wide_v1_v3_candidate_generation_rules.md
```

- [ ] **Step 4: Verify docs and runtime artifacts are scoped**

Run:

```powershell
git status --short --untracked-files=all
git diff --check
```

Expected tracked docs:

```text
docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v3.md
docs/pr/2026-04-23_wide_v1_v3_candidate_generation_rules_pr.md
docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md
```

Expected runtime artifacts not staged:

```text
backtest/temp/wide_v1_iteration_v3_20260423.json
backtest/csv/*
backtest/graph/*
```

- [ ] **Step 5: Commit Task 6**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v3.md docs/pr/2026-04-23_wide_v1_v3_candidate_generation_rules_pr.md docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md
git commit -m "Wide v1 v3 후보 생성 실행 결과를 기록한다" -m "best_feature_mix_v3 candidate_count=10 실행 결과와 PR 보고서를 문서화했다.

Constraint: runtime JSON/CSV/graph 산출물은 커밋하지 않음
Confidence: medium
Scope-risk: moderate
Tested: v3 candidate_count=10 runtime, git diff --check
Not-tested: promote, WFO"
```

---

## Final Verification

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run full unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
All unit tests pass. Existing warnings may match the current warning set.
```

- [ ] **Step 3: Run lint, sync guard, and diff check**

Run:

```powershell
python -m ruff check cli/research_iteration_v3.py cli/research_loop.py cli/subcommands.py cli/research_report.py tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py
python scripts/verify_nonrelease_sync.py
git diff --check
```

Expected:

```text
ruff reports All checks passed.
verify_nonrelease_sync.py reports PASS.
git diff --check prints no errors.
```

- [ ] **Step 4: Confirm branch status**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## feature/wide-v1-v3-candidate-generation-rules
```

Tracked changes should be committed. Runtime artifacts under `backtest/temp`, `backtest/csv`, and `backtest/graph` should not be staged.

## Final Routing

Use the documented v3 decision:

```text
PASS_TO_V3_EXECUTION_RESULT_ANALYSIS:
  $brainstorming Wide v1 v3 결과 분석 및 v4 여부 판단 설계

HOLD_FOR_CANDIDATE_RULE_REVIEW:
  $brainstorming Wide v1 v3 후보 생성 규칙 재검토 설계

FAIL_RUNTIME_DIAGNOSTICS:
  $brainstorming Wide v1 v3 runtime 실패 원인 분석 설계
```

## Self-Review Checklist

Spec coverage:

```text
cand005 reference best: Task 1-2
Dual-track candidate pool: Task 1
v3_tighten_secondary: Task 1
v3_repair_trade_amount: Task 1
v3_replace_secondary: Task 1
v3_control_keep_best without rerun: Task 1 and Task 4
score_reference_csv ranking continuity: Task 2 and Task 6
best_feature_mix_v3 CLI mode: Task 3
report v3 type counts: Task 4
candidate_count=10 runtime: Task 6
promote/WFO exclusion: Task 6 and Final Routing
```

Placeholder scan:

```text
The plan writes verification and runtime values through scripts that read captured command output.
```

Type consistency:

```text
Helper function names are build_v3_candidate_pool and parse_best_expression_conditions.
Result metadata key is iteration_v3.
Candidate family metadata key is v3_candidate_type.
CLI mode value is best_feature_mix_v3.
Existing CLI option names remain iteration_v2_* for compatibility.
```
