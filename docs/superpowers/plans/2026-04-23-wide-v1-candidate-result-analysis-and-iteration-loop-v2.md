# Wide v1 Candidate Result Analysis And Iteration Loop v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a v2 candidate generation mode that uses the Wide v1 candidate_count=5 result to build cand003-centered and feature-diverse candidate expressions, then execute and document the next v2 candidate run.

**Architecture:** Extend the existing research loop instead of creating a separate engine. Add a small v2 candidate helper module for primary-feature variants, secondary-feature combinations, and duplicate filtering; wire it into `ResearchLoopConfig` and the `discovery research` CLI; keep runtime DB path verification and candidate execution on the existing `--run-candidates` path.

**Tech Stack:** Python 3.11, pandas-style candidate metadata dictionaries, STOM CLI `discovery research`, pytest, Markdown evidence logs.

---

## Scope

In scope:

- Add a v2 candidate generation helper that can bias candidate expressions around the current best candidate.
- Support three v2 modes:
  - primary range variants
  - primary + one secondary feature combinations
  - limited secondary-only diversity candidates
- Add duplicate filtering based on feature/operator/bounds and estimated retention proximity.
- Add CLI/config options to enable v2 mode in `discovery research`.
- Execute v2 `candidate_count=5` after implementation.
- Document v2 result and PASS/HOLD/FAIL.

Out of scope:

- Do not execute candidate_count=10 in this plan.
- Do not run WFO or `discovery promote`.
- Do not mark cand003 or v2 best candidate as final live strategy.
- Do not commit runtime DB/CSV/graph/temp JSON artifacts.

## File Structure

Create:

- `cli/research_iteration_v2.py`
  - Pure helpers for building v2 candidate dictionaries from analysis candidates and a best-candidate context.
  - No DB, CLI, or subprocess side effects.

- `tests/unit/test_research_iteration_v2.py`
  - Unit tests for v2 candidate generation and duplicate filtering.

Create after execution:

- `docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v2.md`
  - Runtime evidence, candidate results, PASS/HOLD/FAIL.

- `docs/update_log/2026-04-23_wide_v1_iteration_loop_v2.md`
  - Short project update and next command.

Modify:

- `cli/research_loop.py`
  - Add config fields.
  - Apply v2 candidate generation before retention annotation when enabled.
  - Add v2 metadata to `iteration_plan` and result payload.

- `cli/subcommands.py`
  - Add v2 CLI flags and pass them into `research_strategy_once()`.

- `cli/research_report.py`
  - Add v2 candidate generation summary to Markdown.

- `tests/unit/test_research_loop.py`
  - Validate v2 mode wiring and result payload.

- `tests/unit/test_subcommands.py`
  - Validate parser and payload.

- `tests/unit/test_research_report.py`
  - Validate v2 report section.

Runtime-only files:

- `backtest/temp/wide_v1_iteration_loop_v2_preflight_20260423.json`
- `backtest/temp/wide_v1_iteration_loop_v2_result_20260423.json`
- generated `backtest/csv/*.csv`
- strategy DB temporary candidate rows

## Baseline Constants

Current best candidate from PR #18:

```text
strategy_name=WideV1RetentionCand5_20260422__cand003
primary_feature=시가총액
primary_expression=66.999 <= 시가총액 < 2_580
baseline_adjusted_score=10943.034141541459
baseline_trade_count=36918
baseline_trade_count_retention=0.9018247551115128
baseline_promotion_passed=True
```

Feature preferences:

```text
primary_feature=B_시가총액
secondary_features=B_체결강도,B_등락율,B_당일거래대금,B_시분초
```

Candidate generation policy:

```text
v2_candidate_mode=best_feature_mix
v2_primary_feature=B_시가총액
v2_secondary_features=B_체결강도,B_등락율,B_당일거래대금,B_시분초
v2_include_secondary_only=True
v2_max_secondary_only=1
v2_duplicate_retention_tolerance=0.02
```

---

### Task 1: v2 Candidate Helper

**Files:**
- Create: `cli/research_iteration_v2.py`
- Create: `tests/unit/test_research_iteration_v2.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_research_iteration_v2.py`:

```python
from cli.research_iteration_v2 import (
    build_v2_candidate_pool,
    candidate_signature,
    filter_duplicate_v2_candidates,
)


BEST_CONTEXT = {
    'strategy_name': 'WideV1RetentionCand5_20260422__cand003',
    'expression': '66.999 <= 시가총액 < 2_580',
    'source_candidate': {
        'feature': 'B_시가총액',
        'operator': 'between',
        'lower_bound': 66.999,
        'upper_bound': 2580.0,
        'score': 0.2237,
        'source': 'quantile',
    },
    'rank_score': {
        'adjusted_score': 10943.034141541459,
        'trade_count_retention': 0.9018247551115128,
    },
}


def _candidate(feature, lower, upper, score=1.0, retention=0.9, source='quantile'):
    return {
        'feature': feature,
        'operator': 'between',
        'lower_bound': lower,
        'upper_bound': upper,
        'score': score,
        'combined_score': score,
        'source': source,
        'retention_estimate': {'estimated_retention': retention},
        'retention_filter_passed': True,
        'retention_fallback_used': False,
        'expression': f'{lower} <= {feature[2:]} < {upper}',
    }


def test_candidate_signature_uses_feature_operator_and_bounds():
    candidate = _candidate('B_시가총액', 66.999, 2580.0)

    assert candidate_signature(candidate) == ('B_시가총액', 'between', 66.999, 2580.0)


def test_filter_duplicate_v2_candidates_drops_near_duplicate_retention():
    candidates = [
        _candidate('B_시가총액', 66.999, 2580.0, score=1.0, retention=0.900),
        _candidate('B_시가총액', 66.999, 2580.0, score=2.0, retention=0.905),
        _candidate('B_체결강도', 0.009, 55.94, score=3.0, retention=0.900),
    ]

    result = filter_duplicate_v2_candidates(candidates, retention_tolerance=0.02)

    assert [item['feature'] for item in result] == ['B_시가총액', 'B_체결강도']
    assert result[0]['score'] == 1.0


def test_build_v2_candidate_pool_prefers_primary_variants_and_combinations():
    analysis_candidates = [
        _candidate('B_시가총액', 50.0, 2580.0, score=10.0, retention=0.88),
        _candidate('B_시가총액', 66.999, 3000.0, score=9.0, retention=0.87),
        _candidate('B_체결강도', 0.009, 55.94, score=8.0, retention=0.90),
        _candidate('B_등락율', 15.894, 25.0, score=7.0, retention=0.91),
        _candidate('B_당일거래대금', 1800.0, 3586.0, score=6.0, retention=0.92),
        _candidate('B_시분초', 90029.999, 90055.0, score=5.0, retention=0.98),
    ]

    result = build_v2_candidate_pool(
        analysis_candidates,
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        secondary_features=['B_체결강도', 'B_등락율', 'B_당일거래대금', 'B_시분초'],
        include_secondary_only=True,
        max_secondary_only=1,
        retention_tolerance=0.02,
    )

    expressions = [item['expression'] for item in result['candidates']]
    assert result['status'] == 'ok'
    assert result['primary_feature'] == 'B_시가총액'
    assert any('시가총액' in expression for expression in expressions)
    assert any(' and ' in expression for expression in expressions)
    assert result['mode'] == 'best_feature_mix'
    assert result['candidate_count'] == len(result['candidates'])
    assert result['type_counts']['primary_variant'] >= 1
    assert result['type_counts']['primary_secondary_combo'] >= 1
    assert result['type_counts']['secondary_only'] == 1


def test_build_v2_candidate_pool_returns_disabled_when_no_context():
    result = build_v2_candidate_pool([], best_context=None)

    assert result['status'] == 'disabled'
    assert result['candidates'] == []
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v2.py -q
```

Expected:

```text
FAIL because cli.research_iteration_v2 does not exist.
```

- [ ] **Step 3: Implement helper module**

Create `cli/research_iteration_v2.py`:

```python
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from cli.condition_generator import candidate_to_expression


def _retention_value(candidate: dict) -> float | None:
    estimate = candidate.get('retention_estimate') or {}
    value = estimate.get('estimated_retention')
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def candidate_signature(candidate: dict) -> tuple:
    return (
        candidate.get('feature'),
        candidate.get('operator'),
        candidate.get('lower_bound'),
        candidate.get('upper_bound'),
        candidate.get('threshold'),
    )


def filter_duplicate_v2_candidates(candidates: list[dict], retention_tolerance: float = 0.02) -> list[dict]:
    selected = []
    for candidate in candidates:
        signature = candidate_signature(candidate)
        retention = _retention_value(candidate)
        duplicate = False
        for existing in selected:
            if candidate_signature(existing) != signature:
                continue
            existing_retention = _retention_value(existing)
            if retention is None or existing_retention is None:
                duplicate = True
                break
            if abs(retention - existing_retention) < retention_tolerance:
                duplicate = True
                break
        if not duplicate:
            selected.append(candidate)
    return selected


def _copy_with_type(candidate: dict, candidate_type: str) -> dict:
    item = deepcopy(candidate)
    item['v2_candidate_type'] = candidate_type
    item['expression'] = candidate_to_expression(item, runtime_context=True)
    item['conditions'] = [deepcopy(item)]
    return item


def _combo_candidate(primary: dict, secondary: dict) -> dict:
    item = {
        'feature': primary.get('feature'),
        'operator': primary.get('operator'),
        'lower_bound': primary.get('lower_bound'),
        'upper_bound': primary.get('upper_bound'),
        'threshold': primary.get('threshold'),
        'score': float(primary.get('score', 0.0) or 0.0) + float(secondary.get('score', 0.0) or 0.0),
        'combined_score': float(primary.get('combined_score', primary.get('score', 0.0)) or 0.0)
        + float(secondary.get('combined_score', secondary.get('score', 0.0)) or 0.0),
        'source': 'v2_combo',
        'primary_feature': primary.get('feature'),
        'secondary_feature': secondary.get('feature'),
        'retention_estimate': primary.get('retention_estimate') or {},
        'retention_filter_passed': primary.get('retention_filter_passed'),
        'retention_fallback_used': primary.get('retention_fallback_used', False),
        'v2_candidate_type': 'primary_secondary_combo',
        'conditions': [deepcopy(primary), deepcopy(secondary)],
    }
    item['expression'] = ' and '.join(
        candidate_to_expression(condition, runtime_context=True)
        for condition in item['conditions']
    )
    return item


def build_v2_candidate_pool(
    analysis_candidates: list[dict],
    *,
    best_context: dict | None = None,
    primary_feature: str = 'B_시가총액',
    secondary_features: list[str] | None = None,
    include_secondary_only: bool = True,
    max_secondary_only: int = 1,
    retention_tolerance: float = 0.02,
) -> dict:
    if not best_context:
        return {
            'status': 'disabled',
            'mode': 'best_feature_mix',
            'candidates': [],
            'candidate_count': 0,
            'type_counts': {},
            'reason': 'best_context is required',
        }

    secondary_features = secondary_features or []
    primary_candidates = [
        item for item in analysis_candidates
        if item.get('feature') == primary_feature
    ]
    secondary_candidates = [
        item for item in analysis_candidates
        if item.get('feature') in set(secondary_features)
    ]

    result = []
    for candidate in primary_candidates:
        result.append(_copy_with_type(candidate, 'primary_variant'))

    primary_seed = primary_candidates[0] if primary_candidates else (best_context.get('source_candidate') or {})
    for secondary in secondary_candidates:
        if primary_seed:
            result.append(_combo_candidate(primary_seed, secondary))

    if include_secondary_only and max_secondary_only > 0:
        for candidate in secondary_candidates[:max_secondary_only]:
            result.append(_copy_with_type(candidate, 'secondary_only'))

    result = filter_duplicate_v2_candidates(result, retention_tolerance=retention_tolerance)
    type_counts = Counter(item.get('v2_candidate_type') for item in result)

    return {
        'status': 'ok',
        'mode': 'best_feature_mix',
        'primary_feature': primary_feature,
        'secondary_features': secondary_features,
        'candidates': result,
        'candidate_count': len(result),
        'type_counts': dict(type_counts),
    }
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v2.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit helper**

Run:

```powershell
git add cli/research_iteration_v2.py tests/unit/test_research_iteration_v2.py
git commit -m "Wide v1 v2 후보 생성 helper를 추가한다" -m "cand003 중심 primary feature 변형과 보조 feature 조합 후보를 만들기 위한 side-effect 없는 v2 candidate helper를 추가했다.

Constraint: DB/CLI/runtime side effect 없이 순수 후보 metadata만 생성
Confidence: high
Scope-risk: narrow
Tested: tests/unit/test_research_iteration_v2.py
Not-tested: research_loop integration"
```

---

### Task 2: Research Loop v2 Wiring

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Add failing config and integration tests**

Append to `tests/unit/test_research_loop.py`:

```python
def test_research_loop_config_has_iteration_v2_fields():
    names = set(ResearchLoopConfig.__dataclass_fields__)

    assert 'iteration_v2_mode' in names
    assert 'iteration_v2_best_candidate' in names
    assert 'iteration_v2_primary_feature' in names
    assert 'iteration_v2_secondary_features' in names
    assert 'iteration_v2_include_secondary_only' in names
    assert 'iteration_v2_max_secondary_only' in names
    assert 'iteration_v2_duplicate_retention_tolerance' in names


def test_iteration_plan_includes_v2_settings():
    plan = research_loop._build_iteration_plan(
        ResearchLoopConfig(
            run_candidates=True,
            iteration_v2_mode='best_feature_mix',
            iteration_v2_best_candidate='cand003',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도,B_등락율',
        )
    )

    assert plan['iteration_v2_mode'] == 'best_feature_mix'
    assert plan['iteration_v2_best_candidate'] == 'cand003'
    assert plan['iteration_v2_primary_feature'] == 'B_시가총액'
    assert plan['iteration_v2_secondary_features'] == ['B_체결강도', 'B_등락율']


def test_run_research_iteration_applies_v2_candidate_pool(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text(
        'B_시가총액,B_체결강도,B_등락율,수익률,종목명,매수시간,매도시간,매수가,매도가,수익금\\n'
        '100,10,1,-1,A,20250101090000,20250101090100,100,99,-1\\n'
        '200,20,2,1,B,20250101090200,20250101090300,100,101,1\\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': [
                '50 <= 시가총액 < 2580',
                '0 <= 체결강도 < 55',
                '0 <= 등락율 < 25',
            ],
            'selected_candidates': [
                {
                    'feature': 'B_시가총액',
                    'operator': 'between',
                    'lower_bound': 50.0,
                    'upper_bound': 2580.0,
                    'score': 10.0,
                    'combined_score': 10.0,
                    'retention_estimate': {'estimated_retention': 0.9},
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'feature': 'B_체결강도',
                    'operator': 'between',
                    'lower_bound': 0.0,
                    'upper_bound': 55.0,
                    'score': 9.0,
                    'combined_score': 9.0,
                    'retention_estimate': {'estimated_retention': 0.9},
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'feature': 'B_등락율',
                    'operator': 'between',
                    'lower_bound': 0.0,
                    'upper_bound': 25.0,
                    'score': 8.0,
                    'combined_score': 8.0,
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
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V2Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix',
            iteration_v2_best_candidate='cand003',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도,B_등락율',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert result['iteration_v2']['status'] == 'ok'
    assert executed_specs
    assert any(' and ' in spec['expression'] for spec in executed_specs)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_config_has_iteration_v2_fields tests/unit/test_research_loop.py::test_iteration_plan_includes_v2_settings tests/unit/test_research_loop.py::test_run_research_iteration_applies_v2_candidate_pool -q
```

Expected:

```text
FAIL because ResearchLoopConfig has no v2 fields and research_loop does not apply v2 candidate pool.
```

- [ ] **Step 3: Add config fields and helpers**

In `cli/research_loop.py`, add import:

```python
from cli.research_iteration_v2 import build_v2_candidate_pool
```

Add fields to `ResearchLoopConfig`:

```python
    iteration_v2_mode: str = ''
    iteration_v2_best_candidate: str = ''
    iteration_v2_primary_feature: str = 'B_시가총액'
    iteration_v2_secondary_features: str = ''
    iteration_v2_include_secondary_only: bool = True
    iteration_v2_max_secondary_only: int = 1
    iteration_v2_duplicate_retention_tolerance: float = 0.02
```

Add helper near `_candidate_pool_size`:

```python
def _split_csv_values(value: str | None) -> list[str]:
    return [item.strip() for item in (value or '').split(',') if item.strip()]
```

Update `_build_iteration_plan()` with:

```python
        'iteration_v2_mode': config.iteration_v2_mode,
        'iteration_v2_best_candidate': config.iteration_v2_best_candidate,
        'iteration_v2_primary_feature': config.iteration_v2_primary_feature,
        'iteration_v2_secondary_features': _split_csv_values(config.iteration_v2_secondary_features),
        'iteration_v2_include_secondary_only': config.iteration_v2_include_secondary_only,
        'iteration_v2_max_secondary_only': config.iteration_v2_max_secondary_only,
        'iteration_v2_duplicate_retention_tolerance': config.iteration_v2_duplicate_retention_tolerance,
```

Add validation to `validate_research_iteration_config()`:

```python
    if config.run_candidates and config.iteration_v2_mode and config.iteration_v2_mode != 'best_feature_mix':
        return _error(
            'invalid_iteration_v2_mode',
            'iteration_v2_mode must be empty or best_feature_mix',
        )
    if config.run_candidates and config.iteration_v2_max_secondary_only < 0:
        return _error(
            'invalid_iteration_v2_max_secondary_only',
            'iteration_v2_max_secondary_only must be greater than or equal to 0',
        )
```

- [ ] **Step 4: Apply v2 candidate pool in run_research_iteration**

In `run_research_iteration()`, after `expression_candidates` is built and before `baseline_frame = _trade_frame_for_compare(baseline_csv)`, add:

```python
    iteration_v2 = {'status': 'disabled', 'mode': config.iteration_v2_mode}
    if config.iteration_v2_mode == 'best_feature_mix':
        iteration_v2 = build_v2_candidate_pool(
            expression_candidates,
            best_context={'strategy_name': config.iteration_v2_best_candidate},
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
```

Include `iteration_v2=iteration_v2` in all downstream result/error payloads after this point where `expression_result` is returned. At minimum, include it in the final success payload:

```python
        'iteration_v2': iteration_v2,
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v2.py tests/unit/test_research_loop.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 6: Commit Task 1-2**

Run:

```powershell
git add cli/research_iteration_v2.py cli/research_loop.py tests/unit/test_research_iteration_v2.py tests/unit/test_research_loop.py
git commit -m "Wide v1 v2 후보 생성 경로를 research loop에 연결한다" -m "cand003 중심 primary feature 변형과 보조 feature 조합 후보를 생성하는 v2 mode를 research loop에 연결했다.

Constraint: 기존 discovery research 기본 동작은 iteration_v2_mode가 비어 있으면 유지
Confidence: medium
Scope-risk: moderate
Tested: tests/unit/test_research_iteration_v2.py tests/unit/test_research_loop.py
Not-tested: live v2 candidate execution"
```

---

### Task 3: CLI Options And Report

**Files:**
- Modify: `cli/subcommands.py`
- Modify: `cli/research_report.py`
- Modify: `tests/unit/test_subcommands.py`
- Modify: `tests/unit/test_research_report.py`

- [ ] **Step 1: Add failing CLI parser tests**

Append to `tests/unit/test_subcommands.py`:

```python
def test_discovery_research_parser_accepts_iteration_v2_options():
    parser = build_parser()

    args = parser.parse_args([
        'discovery', 'research', 'V2Run',
        '--input', 'baseline.csv',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20251231',
        '--run-candidates',
        '--iteration-v2-mode', 'best_feature_mix',
        '--iteration-v2-best-candidate', 'WideV1RetentionCand5_20260422__cand003',
        '--iteration-v2-primary-feature', 'B_시가총액',
        '--iteration-v2-secondary-features', 'B_체결강도,B_등락율',
        '--no-iteration-v2-secondary-only',
        '--iteration-v2-max-secondary-only', '0',
        '--iteration-v2-duplicate-retention-tolerance', '0.03',
    ])

    assert args.iteration_v2_mode == 'best_feature_mix'
    assert args.iteration_v2_best_candidate == 'WideV1RetentionCand5_20260422__cand003'
    assert args.iteration_v2_primary_feature == 'B_시가총액'
    assert args.iteration_v2_secondary_features == 'B_체결강도,B_등락율'
    assert args.iteration_v2_include_secondary_only is False
    assert args.iteration_v2_max_secondary_only == 0
    assert args.iteration_v2_duplicate_retention_tolerance == 0.03
```

Append handler payload test:

```python
def test_discovery_research_handler_passes_iteration_v2_options(monkeypatch):
    captured = {}

    class FakeController:
        def research_strategy_once(self, payload):
            captured.update(payload)
            return {'status': 'ok'}

    monkeypatch.setattr('cli.subcommands.AIBacktestController', lambda: FakeController())

    result = handle_subcommand([
        'discovery', 'research', 'V2Run',
        '--input', 'baseline.csv',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20251231',
        '--run-candidates',
        '--iteration-v2-mode', 'best_feature_mix',
        '--iteration-v2-best-candidate', 'cand003',
        '--iteration-v2-primary-feature', 'B_시가총액',
        '--iteration-v2-secondary-features', 'B_체결강도,B_등락율',
    ])

    assert result == 0
    assert captured['iteration_v2_mode'] == 'best_feature_mix'
    assert captured['iteration_v2_best_candidate'] == 'cand003'
    assert captured['iteration_v2_primary_feature'] == 'B_시가총액'
    assert captured['iteration_v2_secondary_features'] == 'B_체결강도,B_등락율'
```

- [ ] **Step 2: Add failing report test**

Append to `tests/unit/test_research_report.py`:

```python
def test_render_research_report_markdown_contains_iteration_v2_section():
    report = build_research_report({
        'status': 'ok',
        'strategy_name': 'V2Run',
        'iteration_v2': {
            'status': 'ok',
            'mode': 'best_feature_mix',
            'primary_feature': 'B_시가총액',
            'secondary_features': ['B_체결강도', 'B_등락율'],
            'candidate_count': 3,
            'type_counts': {
                'primary_variant': 1,
                'primary_secondary_combo': 1,
                'secondary_only': 1,
            },
        },
    }, strategy_name='V2Run')

    markdown = render_research_report_markdown(report)

    assert '## Iteration Loop v2 Candidate Generation' in markdown
    assert 'best_feature_mix' in markdown
    assert 'B_시가총액' in markdown
    assert 'primary_secondary_combo' in markdown
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_v2_options tests/unit/test_research_report.py::test_render_research_report_markdown_contains_iteration_v2_section -q
```

Expected:

```text
FAIL because CLI options and report section do not exist.
```

- [ ] **Step 4: Add CLI options**

In `cli/subcommands.py`, add to `disc_research` parser:

```python
    disc_research.add_argument('--iteration-v2-mode', choices=['best_feature_mix'], default='')
    disc_research.add_argument('--iteration-v2-best-candidate', default='')
    disc_research.add_argument('--iteration-v2-best-expression', default='')
    disc_research.add_argument('--iteration-v2-primary-feature', default='B_시가총액')
    disc_research.add_argument('--iteration-v2-secondary-features', default='')
    disc_research.add_argument('--no-iteration-v2-secondary-only', dest='iteration_v2_include_secondary_only', action='store_false', default=True)
    disc_research.add_argument('--iteration-v2-max-secondary-only', type=int, default=1)
    disc_research.add_argument('--iteration-v2-duplicate-retention-tolerance', type=float, default=0.02)
```

In the `research_strategy_once` payload, add:

```python
            'iteration_v2_mode': parsed.iteration_v2_mode,
            'iteration_v2_best_candidate': parsed.iteration_v2_best_candidate,
            'iteration_v2_best_expression': parsed.iteration_v2_best_expression,
            'iteration_v2_primary_feature': parsed.iteration_v2_primary_feature,
            'iteration_v2_secondary_features': parsed.iteration_v2_secondary_features,
            'iteration_v2_include_secondary_only': parsed.iteration_v2_include_secondary_only,
            'iteration_v2_max_secondary_only': parsed.iteration_v2_max_secondary_only,
            'iteration_v2_duplicate_retention_tolerance': parsed.iteration_v2_duplicate_retention_tolerance,
```

- [ ] **Step 5: Add report section**

In `cli/research_report.py`, extend `build_research_report()` to include:

```python
        'iteration_v2': result.get('iteration_v2'),
```

In `render_research_report_markdown()`, add section after iteration plan or retention selection:

```python
    iteration_v2 = report.get('iteration_v2') or {}
    if iteration_v2:
        lines.extend(['', '## Iteration Loop v2 Candidate Generation'])
        for key in (
            'status',
            'mode',
            'primary_feature',
            'secondary_features',
            'candidate_count',
        ):
            lines.append(f"- {key}: {iteration_v2.get(key)}")
        type_counts = iteration_v2.get('type_counts') or {}
        if type_counts:
            lines.append('- type_counts:')
            for key, value in type_counts.items():
                lines.append(f"  - {key}: {value}")
```

- [ ] **Step 6: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_report.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 7: Commit Task 3**

Run:

```powershell
git add cli/subcommands.py cli/research_report.py tests/unit/test_subcommands.py tests/unit/test_research_report.py
git commit -m "Wide v1 v2 CLI 옵션과 리포트를 추가한다" -m "discovery research에서 iteration loop v2 후보 생성 모드를 사용할 수 있도록 CLI 옵션과 리포트 섹션을 추가했다.

Constraint: v2 옵션은 명시적으로 켠 경우에만 동작해야 함
Confidence: medium
Scope-risk: moderate
Tested: tests/unit/test_subcommands.py tests/unit/test_research_report.py
Not-tested: live v2 candidate execution"
```

---

### Task 4: v2 Candidate Count 5 Execution

**Files:**
- Runtime only:
  - `backtest/temp/wide_v1_iteration_loop_v2_preflight_20260423.json`
  - `backtest/temp/wide_v1_iteration_loop_v2_result_20260423.json`
  - generated `backtest/csv/*.csv`
  - strategy DB candidate rows

- No tracked file changes in this task.

- [ ] **Step 1: Run runtime-preflight**

Run:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
$out = python stom_backtest.py runtime-preflight `
  --buy WideV1RetentionCand5_20260422__cand003 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --betting 20 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900
$out | Set-Content -LiteralPath backtest\temp\wide_v1_iteration_loop_v2_preflight_20260423.json -Encoding UTF8
$out
```

Expected:

```text
status=ok
buy.status=ok
sell.status=ok
stock_back_db_usable=True
```

- [ ] **Step 2: Run v2 candidate_count=5**

Run:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
python stom_backtest.py discovery research WideV1IterationV2_20260423 `
  --input backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv `
  --base-buy-strategy WideV1RetentionCand5_20260422__cand003 `
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
  --candidate-count 5 `
  --candidate-timeout 900 `
  --min-estimated-retention 0.4 `
  --candidate-pool-multiplier 3 `
  --iteration-v2-mode best_feature_mix `
  --iteration-v2-best-candidate WideV1RetentionCand5_20260422__cand003 `
  --iteration-v2-best-expression "66.999 <= 시가총액 < 2_580" `
  --iteration-v2-primary-feature B_시가총액 `
  --iteration-v2-secondary-features B_체결강도,B_등락율,B_당일거래대금,B_시분초 `
  | Set-Content -LiteralPath backtest\temp\wide_v1_iteration_loop_v2_result_20260423.json -Encoding UTF8
```

Expected:

```text
Command exits 0.
result JSON exists.
result contains iteration_v2 section.
candidate_count_observed >= 5 or structured HOLD/FAIL reason.
```

- [ ] **Step 3: Compute v2 decision**

Run:

```powershell
@'
import json
from pathlib import Path

BASE_ADJUSTED_SCORE = 10943.034141541459
path = Path('backtest/temp/wide_v1_iteration_loop_v2_result_20260423.json')
payload = json.loads(path.read_text(encoding='utf-8-sig'))
candidates = payload.get('candidates') or []
best = payload.get('best_candidate') or {}
rank_score = best.get('rank_score') or {}
promotion = best.get('promotion') or {}

best_score = rank_score.get('adjusted_score')
best_retention = rank_score.get('trade_count_retention')
promotion_passed = promotion.get('passed')
cleanup = payload.get('cleanup_summary') or {}

if (
    payload.get('status') == 'ok'
    and len(candidates) >= 5
    and best
    and best_score is not None
    and best_score > BASE_ADJUSTED_SCORE
    and best_retention is not None
    and best_retention >= 0.4
    and promotion_passed is True
    and cleanup.get('failed_count', 0) == 0
):
    decision = 'PASS'
    reason = 'v2 best candidate improved adjusted_score over cand003 baseline.'
elif payload.get('status') == 'ok' and len(candidates) > 0:
    decision = 'HOLD'
    reason = 'v2 executed but did not improve over cand003 baseline or needs row-level analysis.'
else:
    decision = 'FAIL'
    reason = f"v2 execution failed: status={payload.get('status')}, phase={payload.get('phase')}, message={payload.get('message')}"

print('status', payload.get('status'))
print('candidate_count_observed', len(candidates))
print('best_candidate', best.get('strategy_name'))
print('best_adjusted_score', best_score)
print('best_trade_count_retention', best_retention)
print('promotion_passed', promotion_passed)
print('cleanup_failed_count', cleanup.get('failed_count'))
print('decision', decision)
print('reason', reason)
'@ | python -
```

Expected:

```text
decision PASS
or
decision HOLD with clear reason.
```

---

### Task 5: v2 Documentation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v2.md`
- Create: `docs/update_log/2026-04-23_wide_v1_iteration_loop_v2.md`

- [ ] **Step 1: Generate pilot log**

Run:

```powershell
@'
import json
from pathlib import Path

BASE_ADJUSTED_SCORE = 10943.034141541459
result_path = Path('backtest/temp/wide_v1_iteration_loop_v2_result_20260423.json')
preflight_path = Path('backtest/temp/wide_v1_iteration_loop_v2_preflight_20260423.json')
out_path = Path('docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v2.md')
out_path.parent.mkdir(parents=True, exist_ok=True)

payload = json.loads(result_path.read_text(encoding='utf-8-sig'))
preflight = json.loads(preflight_path.read_text(encoding='utf-8-sig'))
candidates = payload.get('candidates') or []
best = payload.get('best_candidate') or {}
best_rank_score = best.get('rank_score') or {}
best_promotion = best.get('promotion') or {}
cleanup = payload.get('cleanup_summary') or {}

best_score = best_rank_score.get('adjusted_score')
best_retention = best_rank_score.get('trade_count_retention')
promotion_passed = best_promotion.get('passed')

if (
    payload.get('status') == 'ok'
    and len(candidates) >= 5
    and best
    and best_score is not None
    and best_score > BASE_ADJUSTED_SCORE
    and best_retention is not None
    and best_retention >= 0.4
    and promotion_passed is True
    and cleanup.get('failed_count', 0) == 0
):
    decision = 'PASS'
    reason = 'v2 best candidate improved adjusted_score over cand003 baseline.'
    next_command = '$brainstorming Wide v1 candidate_count=10 확장 실행 설계'
elif payload.get('status') == 'ok' and candidates:
    decision = 'HOLD'
    reason = 'v2 executed but did not improve over cand003 baseline or needs row-level analysis.'
    next_command = '$brainstorming Wide v1 row-level 후보 차이 분석 설계'
else:
    decision = 'FAIL'
    reason = f"v2 execution failed: status={payload.get('status')}, phase={payload.get('phase')}, message={payload.get('message')}"
    next_command = '$brainstorming Wide v1 v2 실행 실패 checkpoint 분석 설계'

candidate_lines = []
for candidate in candidates:
    rank_score = candidate.get('rank_score') or {}
    promotion = candidate.get('promotion') or {}
    metrics = (candidate.get('candidate_result') or {}).get('metrics') or {}
    candidate_lines.extend([
        f"rank={candidate.get('rank')}",
        f"strategy_name={candidate.get('strategy_name')}",
        f"expression={candidate.get('expression')}",
        f"candidate_status={(candidate.get('candidate_result') or {}).get('status')}",
        f"trade_count={metrics.get('trade_count')}",
        f"trade_count_retention={rank_score.get('trade_count_retention')}",
        f"promotion_passed={promotion.get('passed')}",
        f"adjusted_score={rank_score.get('adjusted_score')}",
        '',
    ])

lines = [
    '# Wide v1 Iteration Loop v2 Pilot',
    '',
    '## 목적',
    '',
    'cand003 중심 v2 후보 생성 규칙이 기존 best candidate보다 더 나은 후보를 만들 수 있는지 확인한다.',
    '',
    '## preflight',
    '',
    '```text',
    f"status={preflight.get('status')}",
    f"setting_db_path={preflight.get('runtime_profile', {}).get('setting_db_path')}",
    f"strategy_db_path={preflight.get('runtime_profile', {}).get('strategy_db_path')}",
    f"stock_back_db_path={preflight.get('runtime_profile', {}).get('stock_back_db_path')}",
    '```',
    '',
    '## 실행 결과',
    '',
    '```text',
    f"status={payload.get('status')}",
    f"phase={payload.get('phase')}",
    f"candidate_count_observed={len(candidates)}",
    f"iteration_v2={payload.get('iteration_v2')}",
    f"best_candidate={best.get('strategy_name')}",
    f"best_adjusted_score={best_score}",
    f"baseline_adjusted_score={BASE_ADJUSTED_SCORE}",
    f"cleanup_failed_count={cleanup.get('failed_count')}",
    '```',
    '',
    '## 후보별 결과',
    '',
    '```text',
    *(candidate_lines or ['candidate_results=not_present']),
    '```',
    '',
    '## 판정',
    '',
    '```text',
    f"decision={decision}",
    f"reason={reason}",
    f"next_command={next_command}",
    '```',
    '',
]
out_path.write_text('\n'.join(lines), encoding='utf-8')
print(out_path)
print('decision', decision)
'@ | python -
```

Expected:

```text
docs\research\condition_research\pilot_logs\2026-04-23_wide_v1_iteration_loop_v2.md
decision PASS
or
decision HOLD
```

- [ ] **Step 2: Generate update log**

Run:

```powershell
@'
from pathlib import Path
import re

pilot_path = Path('docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v2.md')
out_path = Path('docs/update_log/2026-04-23_wide_v1_iteration_loop_v2.md')
text = pilot_path.read_text(encoding='utf-8')

def extract(name):
    match = re.search(rf'^{re.escape(name)}=(.*)$', text, flags=re.MULTILINE)
    return match.group(1).strip() if match else 'not_present'

decision = extract('decision')
next_command = extract('next_command')

lines = [
    '# 2026-04-23 Wide v1 Iteration Loop v2',
    '',
    '## 목적',
    '',
    'cand003 중심 후보 분석과 후보 5개 공통/차이 패턴을 반영한 v2 후보 생성/실행 결과를 기록했다.',
    '',
    '## 결과 요약',
    '',
    '```text',
    f"status={extract('status')}",
    f"candidate_count_observed={extract('candidate_count_observed')}",
    f"best_candidate={extract('best_candidate')}",
    f"best_adjusted_score={extract('best_adjusted_score')}",
    f"decision={decision}",
    '```',
    '',
    '## 판정',
    '',
    '```text',
    f"decision={decision}",
    f"reason={extract('reason')}",
    f"next_command={next_command}",
    '```',
    '',
    '## 다음 단계',
    '',
    '```text',
    next_command,
    '```',
    '',
]
out_path.write_text('\n'.join(lines), encoding='utf-8')
print(out_path)
print('decision', decision)
'@ | python -
```

Expected:

```text
docs\update_log\2026-04-23_wide_v1_iteration_loop_v2.md
decision PASS
or
decision HOLD
```

- [ ] **Step 3: Verify docs**

Run:

```powershell
$patterns = @('T' + 'BD', 'TO' + 'DO', 'FIX' + 'ME', 'actual' + '_', 'observ' + 'ed') -join '|'
rg -n $patterns docs\research\condition_research\pilot_logs\2026-04-23_wide_v1_iteration_loop_v2.md docs\update_log\2026-04-23_wide_v1_iteration_loop_v2.md
```

Expected:

```text
No output.
```

---

### Task 6: Verification And Commit

**Files:**
- Commit all code/test/doc changes from Tasks 1-5.

Do not commit:

```text
backtest/temp/*.json
backtest/csv/*.csv
backtest/graph/
_database/*.db
```

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v2.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py -q
python scripts/verify_nonrelease_sync.py
git diff --check
```

Expected:

```text
All selected tests pass.
verify_nonrelease_sync.py passes.
git diff --check has no output.
```

- [ ] **Step 2: Confirm runtime artifacts are not staged**

Run:

```powershell
git status --short --untracked-files=all
```

Expected tracked changes include:

```text
cli/research_iteration_v2.py
cli/research_loop.py
cli/subcommands.py
cli/research_report.py
tests/unit/test_research_iteration_v2.py
tests/unit/test_research_loop.py
tests/unit/test_subcommands.py
tests/unit/test_research_report.py
docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v2.md
docs/update_log/2026-04-23_wide_v1_iteration_loop_v2.md
```

Runtime files may exist, but they must not be staged.

- [ ] **Step 3: Commit final work**

Run:

```powershell
git add cli/research_iteration_v2.py cli/research_loop.py cli/subcommands.py cli/research_report.py tests/unit/test_research_iteration_v2.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v2.md docs/update_log/2026-04-23_wide_v1_iteration_loop_v2.md
git commit -m "Wide v1 반복 개선 루프 v2 결과를 기록한다" -m "cand003 중심 후보 생성 규칙과 후보 5개 공통/차이 feature를 반영한 iteration loop v2 실행 결과를 문서화했다.

Constraint: runtime DB, CSV, graph, temp JSON 산출물은 커밋하지 않음
Confidence: medium
Scope-risk: moderate
Tested: focused unit tests, runtime-preflight, v2 candidate execution, verify_nonrelease_sync.py
Not-tested: candidate_count=10, WFO, promote"
```

---

## Final Decision Routing

Use the documented v2 decision:

```text
PASS:
  $brainstorming Wide v1 candidate_count=10 확장 실행 설계

HOLD:
  $brainstorming Wide v1 row-level 후보 차이 분석 설계

FAIL:
  $brainstorming Wide v1 v2 실행 실패 checkpoint 분석 설계
```

## Self-Review Checklist

Spec coverage:

```text
cand003 중심 후보 generation: Task 1-2
후보 5개 공통/차이 feature 조합: Task 1-2
candidate_count=5 v2 실행: Task 4
candidate_count=10 조건부 확장: Final Decision Routing
runtime DB path policy: Task 4
WFO/promote 제외: Scope and final routing
```

If implementation reveals that v2 candidate generation needs broader architecture changes, stop and write a smaller follow-up design rather than expanding this plan silently.
