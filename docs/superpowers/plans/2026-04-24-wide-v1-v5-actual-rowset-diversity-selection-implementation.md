# Wide v1 v5 Actual Row-Set Diversity Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `best_feature_mix_v5` so Wide v1 can execute an oversampled v4-style candidate pool, then select final representatives by actual candidate CSV row-set diversity before promote/WFO planning.

**Architecture:** Keep existing v4 behavior unchanged. Add a focused `cli/research_iteration_v5.py` helper for execution-pool sizing and actual row-set representative selection, wire it into `cli/research_loop.py` only for `best_feature_mix_v5`, and expose the result through CLI validation plus markdown reports.

**Tech Stack:** Python 3.11, existing STOM CLI, pytest, Ruff, basedpyright, `cli.research_v4_rowset`, `cli.research_iteration_v4`, `cli.research_loop`, `cli.subcommands`, `cli.research_report`.

---

## File Structure

- Create: `cli/research_iteration_v5.py`
  - Owns v5 execution count sizing, actual row-set representative selection, and selected-best application.
- Create: `tests/unit/test_research_iteration_v5.py`
  - Unit tests for v5 helper behavior.
- Modify: `cli/research_loop.py`
  - Accept `best_feature_mix_v5`, reuse v4 generation/proxy selection, execute an oversampled pool, then apply actual row-set representative selection.
- Modify: `cli/subcommands.py`
  - Add `best_feature_mix_v5` to parser choices.
- Modify: `cli/research_report.py`
  - Render `iteration_v5` and `actual_rowset_selection` sections.
- Modify: `tests/unit/test_research_loop.py`
  - Add v5 integration behavior tests while preserving v4 path tests.
- Modify: `tests/unit/test_subcommands.py`
  - Add parser and handler tests for v5 mode.
- Modify: `tests/unit/test_research_report.py`
  - Add report rendering test for v5.
- Create: `docs/pr/2026-04-24_wide_v1_v5_actual_rowset_diversity_selection_pr.md`
  - Korean markdown PR report after implementation verification.

---

## Task 1: Add v5 Actual Row-Set Helper

**Files:**
- Create: `tests/unit/test_research_iteration_v5.py`
- Create: `cli/research_iteration_v5.py`

- [ ] **Step 1: Write failing tests for v5 helper**

Create `tests/unit/test_research_iteration_v5.py` with this content:

```python
from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportMissingTypeStubs=none, reportUnknownMemberType=none, reportUnusedCallResult=none

from pathlib import Path
from typing import Any, TypeAlias

import pandas as pd

from cli.research_compare import INSTRUMENT_COLUMNS, OPTIONAL_KEY_COLUMNS, REQUIRED_KEY_COLUMNS
from cli.research_iteration_v5 import (
    apply_actual_rowset_selection,
    planned_v5_execution_count,
    select_actual_rowset_representatives,
)
from cli.research_metrics import NUMERIC_COLUMNS

JsonDict: TypeAlias = dict[str, Any]

SYMBOL_COLUMN = INSTRUMENT_COLUMNS[1]
BUY_TIME_COLUMN = REQUIRED_KEY_COLUMNS[0]
BUY_PRICE_COLUMN = OPTIONAL_KEY_COLUMNS[0]
SELL_TIME_COLUMN = NUMERIC_COLUMNS[1]
SELL_PRICE_COLUMN = NUMERIC_COLUMNS[3]
RETURN_COLUMN = NUMERIC_COLUMNS[5]
PROFIT_COLUMN = NUMERIC_COLUMNS[6]


def _row(symbol: str, buy_time: int, buy_price: int) -> JsonDict:
    return {
        SYMBOL_COLUMN: symbol,
        BUY_TIME_COLUMN: buy_time,
        BUY_PRICE_COLUMN: buy_price,
        SELL_TIME_COLUMN: buy_time + 100,
        SELL_PRICE_COLUMN: buy_price + 1,
        RETURN_COLUMN: 1.0,
        PROFIT_COLUMN: 100,
        'R_MFE': 1.2,
        'R_MAE': -0.2,
    }


def _trade_csv(path: Path, rows: list[JsonDict]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False, encoding='utf-8')
    return path


def _candidate(name: str, csv_path: Path, *, rank: int) -> JsonDict:
    return {
        'strategy_name': name,
        'candidate_csv': str(csv_path),
        'status': 'ok',
        'rank': rank,
        'selected_as_best': rank == 1,
        'rank_score': {
            'adjusted_score': 100.0 - rank,
            'trade_count': 2.0,
            'trade_count_retention': 1.0,
            'date_concentration': 0.5,
            'symbol_concentration': 0.5,
        },
    }


def test_planned_v5_execution_count_oversamples_with_available_cap():
    assert planned_v5_execution_count(requested_count=10, eligible_count=17) == 17
    assert planned_v5_execution_count(requested_count=10, eligible_count=30) == 20
    assert planned_v5_execution_count(requested_count=1, eligible_count=10) == 3
    assert planned_v5_execution_count(requested_count=0, eligible_count=10) == 0


def test_select_actual_rowset_representatives_keeps_one_ranked_member_per_group(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_c = _trade_csv(tmp_path / 'cand003.csv', [_row('C', 3, 300), _row('D', 4, 400)])
    ranked = [
        _candidate('cand001', csv_a, rank=1),
        _candidate('cand002', csv_b, rank=2),
        _candidate('cand003', csv_c, rank=3),
    ]

    selected, summary = select_actual_rowset_representatives(
        ranked,
        runtime_root=tmp_path,
        requested_count=2,
    )

    assert [item['strategy_name'] for item in selected] == ['cand001', 'cand003']
    assert summary['status'] == 'ok'
    assert summary['row_set_identity_status'] == 'all_distinct'
    assert summary['executed_count'] == 3
    assert summary['actual_group_count'] == 2
    assert summary['selected_count'] == 2
    assert summary['duplicate_actual_rowset_count'] == 1
    assert summary['skipped_duplicate_actual_count'] == 1
    assert summary['duplicate_groups'][0]['members'] == ['cand001', 'cand002']


def test_select_actual_rowset_representatives_reports_shortfall(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100)])
    ranked = [
        _candidate('cand001', csv_a, rank=1),
        _candidate('cand002', csv_b, rank=2),
    ]

    selected, summary = select_actual_rowset_representatives(
        ranked,
        runtime_root=tmp_path,
        requested_count=2,
    )

    assert [item['strategy_name'] for item in selected] == ['cand001']
    assert summary['status'] == 'shortfall'
    assert summary['row_set_identity_status'] == 'partially_distinct'
    assert summary['selected_count'] == 1
    assert summary['requested_count'] == 2


def test_apply_actual_rowset_selection_moves_best_to_first_selected_representative(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('B', 2, 200)])
    ranked = [
        _candidate('cand001', csv_a, rank=1),
        _candidate('cand002', csv_b, rank=2),
    ]
    selection = {
        'selected_strategy_names': ['cand002'],
    }

    updated, best = apply_actual_rowset_selection(ranked, selection)

    assert best['strategy_name'] == 'cand002'
    assert [item['selected_as_best'] for item in updated] == [False, True]
    assert [item['actual_rowset_selected'] for item in updated] == [False, True]
```

- [ ] **Step 2: Run helper tests and verify RED**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v5.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'cli.research_iteration_v5'
```

- [ ] **Step 3: Implement v5 helper**

Create `cli/research_iteration_v5.py` with this content:

```python
"""Wide v1 v5 actual row-set representative selection."""

from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportUnknownArgumentType=none, reportUnknownMemberType=none, reportUnknownVariableType=none, reportUnusedCallResult=none

from pathlib import Path
from typing import Any, TypeAlias, cast

from cli.research_v4_rowset import analyze_v4_candidate_row_sets

JsonDict: TypeAlias = dict[str, Any]
JsonList: TypeAlias = list[JsonDict]


def planned_v5_execution_count(*, requested_count: int, eligible_count: int) -> int:
    requested = max(int(requested_count), 0)
    eligible = max(int(eligible_count), 0)
    if requested <= 0 or eligible <= 0:
        return 0
    target = max(requested + 2, requested * 2)
    return min(eligible, target)


def _safe_int(value: object, default: int = 999999) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _ranked_by_existing_order(candidates: JsonList) -> JsonList:
    return sorted(
        [dict(candidate) for candidate in candidates],
        key=lambda candidate: (
            _safe_int(candidate.get('rank')),
            str(candidate.get('strategy_name') or ''),
        ),
    )


def _candidate_by_name(candidates: JsonList) -> dict[str, JsonDict]:
    return {
        str(candidate.get('strategy_name')): dict(candidate)
        for candidate in candidates
        if candidate.get('strategy_name') is not None
    }


def _selected_status(*, requested_count: int, selected_count: int, actual_group_count: int) -> tuple[str, str]:
    if selected_count >= requested_count:
        return 'ok', 'all_distinct'
    if actual_group_count <= 1:
        return 'shortfall', 'all_identical'
    return 'shortfall', 'partially_distinct'


def select_actual_rowset_representatives(
    ranked_candidates: JsonList,
    *,
    runtime_root: str | Path,
    requested_count: int,
    candidate_specs: JsonList | None = None,
) -> tuple[JsonList, JsonDict]:
    requested = max(int(requested_count), 0)
    ranked = _ranked_by_existing_order(ranked_candidates)
    runtime = {
        'candidates': ranked,
        'candidate_specs': list(candidate_specs or []),
    }
    row_set_gate = analyze_v4_candidate_row_sets(
        cast(JsonDict, runtime),
        runtime_root=runtime_root,
        top_n=len(ranked),
    )
    by_name = _candidate_by_name(ranked)
    representatives = [
        by_name[str(group.get('representative'))]
        for group in row_set_gate.get('groups') or []
        if group.get('representative') in by_name
    ]
    representatives = _ranked_by_existing_order(representatives)
    selected = representatives[:requested]
    selected_names = [str(item.get('strategy_name')) for item in selected]
    duplicate_groups = [
        group
        for group in row_set_gate.get('groups') or []
        if len(group.get('members') or []) > 1
    ]
    skipped_duplicate_count = sum(
        max(len(group.get('members') or []) - 1, 0)
        for group in duplicate_groups
    )
    status, identity_status = _selected_status(
        requested_count=requested,
        selected_count=len(selected),
        actual_group_count=int(row_set_gate.get('group_count') or 0),
    )
    summary = {
        'status': status,
        'phase': 'actual_rowset_representatives_selected',
        'requested_count': requested,
        'executed_count': len(ranked),
        'actual_group_count': int(row_set_gate.get('group_count') or 0),
        'selected_count': len(selected),
        'duplicate_actual_rowset_count': skipped_duplicate_count,
        'skipped_duplicate_actual_count': skipped_duplicate_count,
        'selected_strategy_names': selected_names,
        'duplicate_groups': duplicate_groups,
        'row_set_identity_status': identity_status,
        'row_set_gate': row_set_gate,
    }
    return selected, summary


def apply_actual_rowset_selection(
    ranked_candidates: JsonList,
    selection_summary: JsonDict,
) -> tuple[JsonList, JsonDict | None]:
    selected_names = [
        str(name)
        for name in selection_summary.get('selected_strategy_names') or []
    ]
    selected_set = set(selected_names)
    best_name = selected_names[0] if selected_names else ''
    updated: JsonList = []
    best_candidate: JsonDict | None = None
    for candidate in ranked_candidates:
        item = dict(candidate)
        name = str(item.get('strategy_name') or '')
        item['actual_rowset_selected'] = name in selected_set
        item['selected_as_best'] = bool(name and name == best_name)
        if item['selected_as_best']:
            best_candidate = item
        updated.append(item)
    return updated, best_candidate
```

- [ ] **Step 4: Run helper tests and verify GREEN**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v5.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit helper**

Run:

```powershell
git add cli/research_iteration_v5.py tests/unit/test_research_iteration_v5.py
git commit -m "Wide v1 v5 실제 행집합 대표 선택기를 추가한다" -m "## 배경

v4는 proxy row-set 기준으로 후보를 분산했지만 actual candidate CSV 기준으로는 중복 row-set이 남았다. v5는 실행된 후보를 실제 행집합 기준으로 다시 대표 선택해야 한다.

## 변경

- v5 실행 후보 수 산정 helper를 추가했다.
- actual row-set 대표 선택 helper를 추가했다.
- duplicate actual row-set shortfall과 selected_as_best 재지정 테스트를 추가했다.

Constraint: 기존 v4 helper와 behavior를 변경하지 않음
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_iteration_v5.py -q
Not-tested: research_loop v5 wiring"
```

---

## Task 2: Wire `best_feature_mix_v5` into Research Loop

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing research loop v5 test**

Append this test to `tests/unit/test_research_loop.py`:

```python
def test_run_research_iteration_v5_executes_oversample_and_selects_actual_distinct(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text(
        'B_시가총액,B_체결강도,B_당일거래대금,수익률,종목명,매수시간,매도시간,매수가,매도가,수익금\n'
        '100,10,2000,-1,A,20250101090000,20250101090100,100,99,-1\n'
        '3000,20,3000,1,B,20250101090200,20250101090300,100,101,1\n'
        '100,30,4000,-1,C,20250101090400,20250101090500,100,99,-1\n'
        '3000,40,6000,1,D,20250101090600,20250101090700,100,101,1\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': [
                '0 <= 체결강도 < 25',
                '25 <= 체결강도 < 45',
                '1000 <= 당일거래대금 < 5000',
            ],
            'selected_candidates': [
                {
                    'feature': 'B_체결강도',
                    'operator': 'between',
                    'lower_bound': 0.0,
                    'upper_bound': 25.0,
                    'score': 8.0,
                    'combined_score': 8.0,
                    'expression': '0 <= 체결강도 < 25',
                },
                {
                    'feature': 'B_체결강도',
                    'operator': 'between',
                    'lower_bound': 25.0,
                    'upper_bound': 45.0,
                    'score': 7.0,
                    'combined_score': 7.0,
                    'expression': '25 <= 체결강도 < 45',
                },
                {
                    'feature': 'B_당일거래대금',
                    'operator': 'between',
                    'lower_bound': 1000.0,
                    'upper_bound': 5000.0,
                    'score': 6.0,
                    'combined_score': 6.0,
                    'expression': '1000 <= 당일거래대금 < 5000',
                },
            ],
        },
    )
    executed_specs = []

    def fake_execute(config, spec, controller, baseline_csv):
        index = len(executed_specs) + 1
        csv_path = tmp_path / f'{spec["strategy_name"]}.csv'
        name = 'DUP' if index in {1, 2} else f'U{index}'
        _write_trade_csv(csv_path, name=name, buy_time=202501010900 + index)
        executed_specs.append(spec)
        return {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'candidate_csv': str(csv_path),
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
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V5Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            candidate_pool_multiplier=3,
            iteration_v2_mode='best_feature_mix_v5',
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
    assert result['iteration_v5']['mode'] == 'best_feature_mix_v5'
    assert result['iteration_v5']['execution_candidate_count'] > 2
    assert len(executed_specs) == result['iteration_v5']['execution_candidate_count']
    assert result['actual_rowset_selection']['phase'] == 'actual_rowset_representatives_selected'
    assert result['actual_rowset_selection']['selected_count'] == 2
    assert result['best_candidate']['actual_rowset_selected'] is True
```

- [ ] **Step 2: Run v5 loop test and verify RED**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_v5_executes_oversample_and_selects_actual_distinct -q
```

Expected:

```text
AssertionError or invalid_iteration_v2_mode
```

- [ ] **Step 3: Import v5 helpers in `cli/research_loop.py`**

At the top of `cli/research_loop.py`, add:

```python
from cli.research_iteration_v5 import (
    apply_actual_rowset_selection,
    planned_v5_execution_count,
    select_actual_rowset_representatives,
)
```

- [ ] **Step 4: Extend metadata helper**

Change `_iteration_generation_metadata` in `cli/research_loop.py` to:

```python
def _iteration_generation_metadata(
    iteration_v2: dict[str, object] | None,
    iteration_v3: dict[str, object] | None,
    iteration_v4: dict[str, object] | None = None,
    iteration_v5: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata: dict[str, object] = {}
    if iteration_v2:
        metadata['iteration_v2'] = iteration_v2
    if iteration_v3:
        metadata['iteration_v3'] = iteration_v3
    if iteration_v4:
        metadata['iteration_v4'] = iteration_v4
    if iteration_v5:
        metadata['iteration_v5'] = iteration_v5
    return metadata
```

- [ ] **Step 5: Allow v5 in validation**

In `validate_research_iteration_config`, replace:

```python
allowed_iteration_modes = {'best_feature_mix', 'best_feature_mix_v3', 'best_feature_mix_v4'}
```

with:

```python
allowed_iteration_modes = {
    'best_feature_mix',
    'best_feature_mix_v3',
    'best_feature_mix_v4',
    'best_feature_mix_v5',
}
```

Replace the invalid mode message with:

```python
'iteration_v2_mode must be empty, best_feature_mix, best_feature_mix_v3, best_feature_mix_v4, or best_feature_mix_v5',
```

Replace:

```python
if config.run_candidates and config.iteration_v2_mode in {'best_feature_mix_v3', 'best_feature_mix_v4'}:
```

with:

```python
if config.run_candidates and config.iteration_v2_mode in {
    'best_feature_mix_v3',
    'best_feature_mix_v4',
    'best_feature_mix_v5',
}:
```

Inside that block, use v4 parsing for v5:

```python
candidate_pool_builder = (
    build_v4_candidate_pool
    if config.iteration_v2_mode in {'best_feature_mix_v4', 'best_feature_mix_v5'}
    else build_v3_candidate_pool
)
```

- [ ] **Step 6: Add v5 mode branch**

In `run_research_iteration`, after `iteration_v4 = None`, add:

```python
iteration_v5 = None
actual_rowset_selection: dict[str, object] | None = None
```

After the `best_feature_mix_v4` branch, add this `elif` branch:

```python
    elif config.iteration_v2_mode == 'best_feature_mix_v5':
        best_context = {
            'strategy_name': config.iteration_v2_best_candidate,
            'expression': config.iteration_v2_best_expression,
        }
        if _score_reference_csv(config):
            best_context['reference_adjusted_score'] = _safe_reference_promotion_score(config, baseline_csv)
        iteration_v4 = build_v4_candidate_pool(
            expression_candidates,
            best_context=best_context,
            primary_feature=config.iteration_v2_primary_feature,
            secondary_features=_split_csv_values(config.iteration_v2_secondary_features),
            min_estimated_retention=config.min_estimated_retention,
            retention_tolerance=config.iteration_v2_duplicate_retention_tolerance,
        )
        expression_candidates = iteration_v4.get('candidates') or []
        iteration_v5 = {
            'status': 'ok',
            'mode': 'best_feature_mix_v5',
            'source_mode': 'best_feature_mix_v4',
            'requested_candidate_count': config.candidate_count,
        }
        expression_result = {
            **expression_result,
            'selected_candidates': expression_candidates,
            'expressions': [candidate['expression'] for candidate in expression_candidates],
            'candidate_count': len(expression_candidates),
            'iteration_v4': iteration_v4,
            'iteration_v5': iteration_v5,
        }
        expressions = expression_result['expressions']
```

- [ ] **Step 7: Oversample v5 selected candidates**

In the v4 selection block, replace:

```python
    if config.iteration_v2_mode == 'best_feature_mix_v4':
```

with:

```python
    if config.iteration_v2_mode in {'best_feature_mix_v4', 'best_feature_mix_v5'}:
```

After `annotated_candidates = annotate_candidate_rowset_proxy(...)`, add:

```python
        rowset_candidate_count = config.candidate_count
        if config.iteration_v2_mode == 'best_feature_mix_v5':
            rowset_candidate_count = planned_v5_execution_count(
                requested_count=config.candidate_count,
                eligible_count=len(annotated_candidates),
            )
            iteration_v5 = {
                **(iteration_v5 or {}),
                'execution_candidate_count': rowset_candidate_count,
                'eligible_proxy_candidate_count': len(annotated_candidates),
            }
```

Then pass `rowset_candidate_count`:

```python
        selected_candidates, retention_selection = select_rowset_diverse_candidates(
            annotated_candidates,
            candidate_count=rowset_candidate_count,
            min_retention=config.min_estimated_retention,
        )
```

Update all `_iteration_generation_metadata(...)` calls in `run_research_iteration` to pass `iteration_v5`:

```python
**_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
```

- [ ] **Step 8: Apply actual row-set representative selection after ranking**

After:

```python
    ranked_candidates, cleanup_summary = _apply_iteration_cleanup(config, ranked_candidates)
```

add:

```python
    if config.iteration_v2_mode == 'best_feature_mix_v5':
        actual_selected, actual_rowset_selection = select_actual_rowset_representatives(
            ranked_candidates,
            runtime_root=Path('.'),
            requested_count=config.candidate_count,
            candidate_specs=specs,
        )
        ranked_candidates, best_candidate = apply_actual_rowset_selection(
            ranked_candidates,
            actual_rowset_selection,
        )
        iteration_v5 = {
            **(iteration_v5 or {}),
            'actual_selected_count': len(actual_selected),
            'actual_rowset_status': actual_rowset_selection.get('status'),
            'actual_rowset_identity_status': actual_rowset_selection.get('row_set_identity_status'),
            'actual_group_count': actual_rowset_selection.get('actual_group_count'),
        }
```

Keep the existing best candidate fallback block after this code so non-v5 behavior is preserved:

```python
    best_candidate = next(
        (
            candidate
            for candidate in ranked_candidates
            if candidate.get('selected_as_best') is True
        ),
        None,
    )
```

In the final result dict, add:

```python
'actual_rowset_selection': actual_rowset_selection,
```

- [ ] **Step 9: Run v5 loop test and verify GREEN**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_v5_executes_oversample_and_selects_actual_distinct -q
```

Expected:

```text
1 passed
```

- [ ] **Step 10: Run v4 loop regression test**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_applies_v4_proxy_diverse_selection tests/unit/test_research_loop.py::test_run_research_iteration_keeps_v3_retention_selection_path -q
```

Expected:

```text
2 passed
```

- [ ] **Step 11: Commit research loop wiring**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "Wide v1 v5 실제 행집합 선택을 연구 루프에 연결한다" -m "## 배경

v5는 proxy 기준 후보 선택 이후 실제 candidate CSV row-set 대표를 최종 후보군으로 다시 골라야 한다. 이를 위해 v5 mode는 v4 후보 생성과 proxy selection을 재사용하되 실행 후보 pool을 더 넓게 잡는다.

## 변경

- best_feature_mix_v5 validation과 runtime branch를 추가했다.
- v5 실행 후보 수를 candidate_count보다 크게 선택하도록 연결했다.
- 실행 후 actual row-set representative selection을 적용했다.
- v4와 v3 기존 연구 루프 회귀 테스트를 유지했다.

Constraint: best_feature_mix_v4 기존 behavior는 변경하지 않음
Confidence: medium
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_v5_executes_oversample_and_selects_actual_distinct -q
Tested: python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_applies_v4_proxy_diverse_selection tests/unit/test_research_loop.py::test_run_research_iteration_keeps_v3_retention_selection_path -q
Not-tested: 실제 v5 runtime 실행"
```

---

## Task 3: Add CLI Parser and Report Support

**Files:**
- Modify: `cli/subcommands.py`
- Modify: `cli/research_report.py`
- Modify: `tests/unit/test_subcommands.py`
- Modify: `tests/unit/test_research_report.py`

- [ ] **Step 1: Add failing parser test**

In `tests/unit/test_subcommands.py`, add a v5 case next to the v4 parser tests:

```python
def test_discovery_research_parser_accepts_iteration_v2_mode_v5():
    parser = build_parser()

    args = parser.parse_args([
        'discovery',
        'research',
        'WideV1IterationV5_20260424',
        '--input',
        'baseline.csv',
        '--run-candidates',
        '--iteration-v2-mode',
        'best_feature_mix_v5',
        '--iteration-v2-best-expression',
        '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
    ])

    assert args.iteration_v2_mode == 'best_feature_mix_v5'
```

- [ ] **Step 2: Run parser test and verify RED**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_mode_v5 -q
```

Expected:

```text
invalid choice: 'best_feature_mix_v5'
```

- [ ] **Step 3: Add v5 parser choice**

In `cli/subcommands.py`, change:

```python
choices=['best_feature_mix', 'best_feature_mix_v3', 'best_feature_mix_v4'],
```

to:

```python
choices=['best_feature_mix', 'best_feature_mix_v3', 'best_feature_mix_v4', 'best_feature_mix_v5'],
```

- [ ] **Step 4: Add failing report test**

In `tests/unit/test_research_report.py`, add:

```python
def test_render_research_report_markdown_contains_iteration_v5_section():
    markdown = render_research_report_markdown({
        'strategy_name': 'WideV1IterationV5_20260424',
        'status': 'ok',
        'iteration_v5': {
            'status': 'ok',
            'mode': 'best_feature_mix_v5',
            'requested_candidate_count': 10,
            'execution_candidate_count': 17,
            'actual_selected_count': 10,
            'actual_group_count': 10,
            'actual_rowset_identity_status': 'all_distinct',
        },
        'actual_rowset_selection': {
            'status': 'ok',
            'phase': 'actual_rowset_representatives_selected',
            'requested_count': 10,
            'executed_count': 17,
            'actual_group_count': 10,
            'selected_count': 10,
            'duplicate_actual_rowset_count': 7,
            'selected_strategy_names': ['cand001', 'cand002'],
        },
    })

    assert '## Iteration Loop v5 Actual Row-Set Selection' in markdown
    assert '- mode: best_feature_mix_v5' in markdown
    assert '- execution_candidate_count: 17' in markdown
    assert '- actual_group_count: 10' in markdown
    assert '- selected_strategy_names: cand001, cand002' in markdown
```

- [ ] **Step 5: Run report test and verify RED**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py::test_render_research_report_markdown_contains_iteration_v5_section -q
```

Expected:

```text
AssertionError: assert '## Iteration Loop v5 Actual Row-Set Selection' in markdown
```

- [ ] **Step 6: Implement v5 report section**

In `cli/research_report.py`, add this function after `_append_iteration_v4_section`:

```python
def _append_iteration_v5_section(lines: list[str], report: dict) -> None:
    iteration_v5 = report.get('iteration_v5') or {}
    actual_selection = report.get('actual_rowset_selection') or {}
    if not iteration_v5 and not actual_selection:
        return

    lines.extend(['', '## Iteration Loop v5 Actual Row-Set Selection'])
    for key in (
        'status',
        'mode',
        'source_mode',
        'requested_candidate_count',
        'execution_candidate_count',
        'eligible_proxy_candidate_count',
        'actual_selected_count',
        'actual_group_count',
        'actual_rowset_identity_status',
    ):
        if key in iteration_v5:
            lines.append(f"- {key}: {iteration_v5.get(key)}")

    for key in (
        'phase',
        'requested_count',
        'executed_count',
        'actual_group_count',
        'selected_count',
        'duplicate_actual_rowset_count',
        'skipped_duplicate_actual_count',
        'row_set_identity_status',
    ):
        if key in actual_selection:
            lines.append(f"- {key}: {actual_selection.get(key)}")

    selected_names = actual_selection.get('selected_strategy_names') or []
    if selected_names:
        lines.append(f"- selected_strategy_names: {', '.join(str(item) for item in selected_names)}")
```

In `render_research_report_markdown`, call it after `_append_iteration_v4_section(lines, report)`:

```python
    _append_iteration_v5_section(lines, report)
```

- [ ] **Step 7: Run parser and report tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_mode_v5 tests/unit/test_research_report.py::test_render_research_report_markdown_contains_iteration_v5_section -q
```

Expected:

```text
2 passed
```

- [ ] **Step 8: Commit CLI and report support**

Run:

```powershell
git add cli/subcommands.py cli/research_report.py tests/unit/test_subcommands.py tests/unit/test_research_report.py
git commit -m "Wide v1 v5 CLI와 보고서 표기를 추가한다" -m "## 배경

v5 runtime을 실행하고 검토하려면 CLI parser와 markdown report가 best_feature_mix_v5와 actual row-set selection 결과를 표현해야 한다.

## 변경

- best_feature_mix_v5 parser choice를 추가했다.
- 연구 보고서에 Iteration Loop v5 Actual Row-Set Selection 섹션을 추가했다.
- parser와 report 단위 테스트를 추가했다.

Constraint: 새 CLI option은 추가하지 않고 기존 iteration_v2_mode choice만 확장함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_mode_v5 tests/unit/test_research_report.py::test_render_research_report_markdown_contains_iteration_v5_section -q
Not-tested: 실제 v5 runtime 실행"
```

---

## Task 4: Add v5 Runtime Analysis Script

**Files:**
- Create: `scripts/analyze_wide_v1_v5_actual_rowset_selection.py`
- Modify: `tests/unit/test_research_iteration_v5.py`

- [ ] **Step 1: Add failing script test**

Append this test to `tests/unit/test_research_iteration_v5.py`:

```python
def test_analyze_wide_v1_v5_actual_rowset_selection_script_prints_decision(
    monkeypatch,
    capsys,
    tmp_path: Path,
):
    import runpy
    import sys

    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / 'scripts' / 'analyze_wide_v1_v5_actual_rowset_selection.py'
    runtime_path = tmp_path / 'runtime.json'
    output_path = tmp_path / 'decision.md'
    runtime_path.write_text(
        '{"status": "ok", "actual_rowset_selection": {"status": "ok", "selected_count": 10, "row_set_identity_status": "all_distinct"}, "iteration_v5": {"mode": "best_feature_mix_v5"}}',
        encoding='utf-8',
    )
    monkeypatch.setattr(
        sys,
        'argv',
        [
            str(script_path),
            '--runtime-path',
            str(runtime_path),
            '--output',
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(script_path), run_name='__main__')
    stdout = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert 'decision=PROCEED_TO_PROMOTE_WFO_PLAN' in stdout
    assert 'next_command=$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성' in stdout
    assert output_path.exists()
```

Add missing imports at the top of `tests/unit/test_research_iteration_v5.py`:

```python
import pytest
```

- [ ] **Step 2: Run script test and verify RED**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v5.py::test_analyze_wide_v1_v5_actual_rowset_selection_script_prints_decision -q
```

Expected:

```text
FileNotFoundError or No such file
```

- [ ] **Step 3: Implement script**

Create `scripts/analyze_wide_v1_v5_actual_rowset_selection.py`:

```python
#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Analyze Wide v1 v5 actual row-set representative selection from a runtime artifact.',
    )
    _ = parser.add_argument('--runtime-path', type=Path, required=True)
    _ = parser.add_argument('--output', type=Path, required=True)
    return parser


def _decision(runtime: dict) -> tuple[str, str]:
    actual = runtime.get('actual_rowset_selection') or {}
    status = actual.get('status')
    selected_count = int(actual.get('selected_count') or 0)
    requested_count = int(actual.get('requested_count') or selected_count)
    identity = actual.get('row_set_identity_status')
    if status == 'ok' and selected_count >= requested_count and identity == 'all_distinct':
        return (
            'PROCEED_TO_PROMOTE_WFO_PLAN',
            '$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성',
        )
    if runtime.get('status') not in {'ok', 'success'}:
        return (
            'HOLD_V5_RUNTIME_FAILURE',
            '$brainstorming Wide v1 v5 runtime failure recovery 설계',
        )
    return (
        'HOLD_V5_ACTUAL_ROW_SET_SHORTFALL',
        '$brainstorming Wide v1 v6 actual row-set generation expansion 설계',
    )


def main(argv: list[str] | None = None) -> int:
    from cli.research_v3_decision import read_runtime_json

    args = build_parser().parse_args(argv)
    runtime_path = cast(Path, args.runtime_path)
    output_path = cast(Path, args.output)
    runtime = read_runtime_json(runtime_path)
    actual = runtime.get('actual_rowset_selection') or {}
    decision, next_command = _decision(runtime)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"""# Wide v1 v5 actual row-set selection decision

## Decision

```text
decision={decision}
next_command={next_command}
```

## Actual Row-Set Selection

```text
status={actual.get('status')}
requested_count={actual.get('requested_count')}
executed_count={actual.get('executed_count')}
selected_count={actual.get('selected_count')}
actual_group_count={actual.get('actual_group_count')}
row_set_identity_status={actual.get('row_set_identity_status')}
```
""",
        encoding='utf-8',
    )
    print(f'decision={decision}')
    print(f'next_command={next_command}')
    print(f'wrote={output_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run script test and verify GREEN**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v5.py::test_analyze_wide_v1_v5_actual_rowset_selection_script_prints_decision -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit script**

Run:

```powershell
git add scripts/analyze_wide_v1_v5_actual_rowset_selection.py tests/unit/test_research_iteration_v5.py
git commit -m "Wide v1 v5 실제 행집합 판단 스크립트를 추가한다" -m "## 배경

v5 runtime 이후 promote/WFO 또는 추가 보강 설계를 결정하려면 actual_rowset_selection 결과를 독립적으로 요약하는 스크립트가 필요하다.

## 변경

- v5 runtime decision script를 추가했다.
- all_distinct selected representative 상태에서 promote/WFO 계획으로 연결한다.
- shortfall과 runtime failure hold 경로를 명시했다.

Constraint: script는 runtime JSON을 읽고 markdown decision만 생성함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_iteration_v5.py::test_analyze_wide_v1_v5_actual_rowset_selection_script_prints_decision -q
Not-tested: 실제 v5 runtime artifact"
```

---

## Task 5: Full Verification and PR Report

**Files:**
- Create: `docs/pr/2026-04-24_wide_v1_v5_actual_rowset_diversity_selection_pr.md`

- [ ] **Step 1: Run focused verification**

Run:

```powershell
$VerificationLog = 'backtest\temp\wide_v1_v5_verification.txt'
"# Wide v1 v5 verification" | Set-Content -Path $VerificationLog -Encoding utf8

"`n## pytest" | Tee-Object -FilePath $VerificationLog -Append
python -m pytest tests/unit/test_research_iteration_v5.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py tests/unit/test_research_v4_rowset.py -q 2>&1 | Tee-Object -FilePath $VerificationLog -Append
if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

"`n## ruff" | Tee-Object -FilePath $VerificationLog -Append
python -m ruff check cli/research_iteration_v5.py cli/research_loop.py cli/research_report.py cli/subcommands.py scripts/analyze_wide_v1_v5_actual_rowset_selection.py tests/unit/test_research_iteration_v5.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py 2>&1 | Tee-Object -FilePath $VerificationLog -Append
if ($LASTEXITCODE -ne 0) { throw "ruff failed" }

"`n## basedpyright" | Tee-Object -FilePath $VerificationLog -Append
basedpyright cli\research_iteration_v5.py cli\research_loop.py scripts\analyze_wide_v1_v5_actual_rowset_selection.py tests\unit\test_research_iteration_v5.py 2>&1 | Tee-Object -FilePath $VerificationLog -Append
if ($LASTEXITCODE -ne 0) { throw "basedpyright failed" }

"`n## verify_nonrelease_sync" | Tee-Object -FilePath $VerificationLog -Append
python scripts\verify_nonrelease_sync.py 2>&1 | Tee-Object -FilePath $VerificationLog -Append
if ($LASTEXITCODE -ne 0) { throw "verify_nonrelease_sync failed" }

"`n## git diff --check --ignore-cr-at-eol" | Tee-Object -FilePath $VerificationLog -Append
cmd /c "git diff --check --ignore-cr-at-eol 2>&1" | Tee-Object -FilePath $VerificationLog -Append
if ($LASTEXITCODE -ne 0) { throw "git diff --check failed" }
```

Expected:

```text
pytest exits 0.
ruff exits 0.
basedpyright exits 0.
verify_nonrelease_sync exits 0.
git diff --check exits 0.
```

- [ ] **Step 2: Create Korean PR report**

Create `docs/pr/2026-04-24_wide_v1_v5_actual_rowset_diversity_selection_pr.md`:

```markdown
# Wide v1 v5 actual row-set diversity selection PR 보고서

## 1. 목적

v4에서 확인된 actual row-set partially_distinct 문제를 해결하기 위해 `best_feature_mix_v5` mode를 추가했다. v5는 v4 후보 생성과 proxy selection을 재사용하되, `candidate_count`보다 더 많은 후보를 실행하고 actual candidate CSV row-set 대표만 최종 후보군으로 선택한다.

## 2. 변경 요약

- `cli/research_iteration_v5.py`를 추가했다.
- `best_feature_mix_v5` mode를 research loop와 CLI parser에 연결했다.
- 실행 후 actual row-set representative selection을 적용했다.
- report와 decision script에 v5 actual row-set selection 결과를 추가했다.

## 3. 퀀트 판단

v5는 proxy 다양성만으로 promote/WFO를 허용하지 않는다. 실제 후보 CSV의 체결 row-set 대표를 기준으로 최종 후보군을 구성하므로 v4의 `cand004`, `cand005` 같은 actual duplicate collapse를 다음 runtime에서 걸러낼 수 있다.

## 4. CLI 판단

기존 `best_feature_mix_v4` behavior를 변경하지 않고 `best_feature_mix_v5` 별도 mode를 추가했다. 새 필수 CLI option은 추가하지 않았고, 기존 `candidate_pool_multiplier`로 넓어진 pool 안에서 oversample 실행을 수행한다.

## 5. 검증

```text
See backtest\temp\wide_v1_v5_verification.txt
```

## 6. 남은 리스크

```text
- 실제 v5 runtime은 아직 실행하지 않았다.
- execution_candidate_count가 candidate_count보다 커져 runtime 비용이 증가한다.
- v5에서도 actual distinct 대표가 candidate_count만큼 확보되지 않으면 v6 generation expansion 설계가 필요하다.
```

## 7. 다음 단계

```text
$writing-plans Wide v1 v5 candidate_count=10 실제 실행 및 actual row-set 검증 계획 작성
```
```

- [ ] **Step 3: Verify PR report has no placeholder markers**

Run:

```powershell
$patterns = @(
  ('TB' + 'D'),
  ('TO' + 'DO'),
  ('Copy the ' + 'observed'),
  ('Record only ' + 'commands'),
  ('replace ' + 'with'),
  ('<' + 'observed'),
  ('<' + 'copy')
)
Select-String -Path docs\pr\2026-04-24_wide_v1_v5_actual_rowset_diversity_selection_pr.md -Pattern $patterns
```

Expected:

```text
No matches.
```

- [ ] **Step 4: Stage only source, tests, and markdown report**

Run:

```powershell
git add cli\research_iteration_v5.py `
        cli\research_loop.py `
        cli\subcommands.py `
        cli\research_report.py `
        scripts\analyze_wide_v1_v5_actual_rowset_selection.py `
        tests\unit\test_research_iteration_v5.py `
        tests\unit\test_research_loop.py `
        tests\unit\test_subcommands.py `
        tests\unit\test_research_report.py `
        docs\pr\2026-04-24_wide_v1_v5_actual_rowset_diversity_selection_pr.md
git diff --cached --check --ignore-cr-at-eol
git diff --cached --stat
```

Expected:

```text
Only the listed source, test, script, and PR markdown files are staged.
No backtest csv, graph, or temp output is staged.
```

- [ ] **Step 5: Final commit**

Run:

```powershell
git commit -m "Wide v1 v5 실제 행집합 대표 선택을 구현한다" -m "## 배경

v4 실행은 proxy row-set diversity를 확보했지만 actual row-set 기준으로 일부 후보가 같은 체결 집합으로 collapse 됐다. v5는 실행 후보를 더 넓게 실행한 뒤 실제 row-set 대표만 최종 후보로 남긴다.

## 변경

- best_feature_mix_v5 mode를 추가했다.
- v5 actual row-set representative selection helper를 추가했다.
- research loop, CLI parser, report, decision script를 v5에 연결했다.
- focused tests와 PR 보고서를 추가했다.

Constraint: best_feature_mix_v4 behavior는 변경하지 않음
Rejected: candidate_count만 확대 | actual row-set duplicate를 직접 제거하지 못함
Confidence: high
Scope-risk: moderate
Directive: v5 runtime 실행 전에는 promote/WFO 계획으로 이동하지 말 것
Tested: python -m pytest tests/unit/test_research_iteration_v5.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py tests/unit/test_research_v4_rowset.py -q
Tested: python -m ruff check v5 touched files
Tested: basedpyright cli\research_iteration_v5.py cli\research_loop.py scripts\analyze_wide_v1_v5_actual_rowset_selection.py tests\unit\test_research_iteration_v5.py
Tested: python scripts\verify_nonrelease_sync.py
Tested: git diff --cached --check --ignore-cr-at-eol
Not-tested: actual v5 candidate_count=10 runtime execution"
```

---

## Self-Review Checklist

Spec coverage:

```text
best_feature_mix_v5 mode: Tasks 2 and 3
oversample execution pool: Task 2
actual row-set representative selection: Task 1
final selected best from representatives: Task 1 and Task 2
duplicate group diagnostics: Task 1 and Task 4
reporting: Task 3 and Task 5
decision handoff: Task 4 and Task 5
no promote/WFO in implementation: Task 5 PR report
```

Placeholder scan command:

```powershell
$patterns = @(
  ('TB' + 'D'),
  ('TO' + 'DO'),
  ('<' + 'observed'),
  ('<' + 'copy'),
  ('replace ' + 'with'),
  ('Copy the ' + 'observed'),
  ('Record only ' + 'commands'),
  ('implement ' + 'later'),
  ('fill in ' + 'details'),
  ('Similar to ' + 'Task')
)
Select-String -Path docs\superpowers\plans\2026-04-24-wide-v1-v5-actual-rowset-diversity-selection-implementation.md -Pattern $patterns
```

Expected:

```text
No matches.
```

Type consistency:

```text
Mode name: best_feature_mix_v5
New helper module: cli.research_iteration_v5
Main helper: select_actual_rowset_representatives
Summary field: actual_rowset_selection
Report field: iteration_v5
Next runtime plan command: $writing-plans Wide v1 v5 candidate_count=10 실제 실행 및 actual row-set 검증 계획 작성
```
