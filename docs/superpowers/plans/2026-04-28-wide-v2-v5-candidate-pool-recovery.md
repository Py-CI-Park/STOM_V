# Wide v2 v5 Candidate Pool Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `best_feature_mix_v5` recover from an empty v4 candidate pool so Wide v2 smoke can reach candidate backtests instead of stopping at `insufficient_candidates`.

**Architecture:** Add a small pure helper module for v5 recovery candidate generation, wire it into `cli.research_loop.run_research_iteration()` only when v5 needs it, and surface recovery metadata through optimizer JSON/Markdown reports. Keep retention and actual row-set gates strict; broaden candidate generation, not final approval.

**Tech Stack:** Python 3.11, pytest, existing STOM CLI research modules, dataclasses/dicts, JSON/Markdown runtime reporting.

---

## Scope Check

This plan implements one connected subsystem: Wide v2 v5 candidate-pool recovery. It does not introduce Wide v6/v7, does not run WFO inside the optimizer loop, does not alter the backtest engine, and does not do broad `cli/` refactoring.

The implementation must keep this MVP path intact:

```text
v5 recovery implementation
-> unit tests
-> candidate_count=2 smoke rerun
-> candidate_count=10 run only if smoke passes
-> WFO/OOS handoff only if final_best_candidate exists
```

Do not stage these paths:

- `utility/strategy.db`
- `backtest/graph/`
- `backtest/temp/`
- `backtest/csv/`

Use explicit staging only.

## File Structure

- Create: `cli/research_iteration_v5_recovery.py`
  - Pure helper for generating fallback v5 candidate pools from full `recommended_candidates`.
  - Owns recovery family construction, deduplication, and recovery metadata.
  - Does not execute backtests and does not read/write files.
- Create: `tests/unit/test_research_iteration_v5_recovery.py`
  - Unit tests for direct v4 passthrough, recovered trade feature, auto secondary, safe fallback, dedupe, and metadata.
- Modify: `cli/research_loop.py`
  - Imports the recovery helper.
  - Calls recovery only in `best_feature_mix_v5` after `build_v4_candidate_pool()`.
  - Adds v5 recovery metadata to runtime result payloads.
- Modify: `tests/unit/test_research_loop.py`
  - Integration-style unit tests showing v5 recovery candidates flow into row-set proxy selection and candidate execution.
  - Regression test for insufficient-candidate metadata at the top level.
- Modify: `cli/research_optimizer.py`
  - Preserves round-level v5 recovery and candidate-count metadata in optimizer-level failure metadata.
- Modify: `tests/unit/test_research_optimizer.py`
  - Regression test for optimizer summary preserving `requested_candidate_count`, `selected_candidate_count`, and v5 recovery metadata.
- Modify: `cli/research_optimizer_report.py`
  - Adds a `## V5 recovery` Markdown section.
- Modify: `tests/unit/test_research_optimizer_report.py`
  - Verifies recovery metadata appears in Markdown and pipe/newline escaping still applies.
- Create after implementation verification: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_recovery_smoke_review.md`
  - Korean smoke rerun review. Commit only if smoke is run and results are meaningful.

---

### Task 1: Pure v5 Recovery Helper

**Files:**
- Create: `tests/unit/test_research_iteration_v5_recovery.py`
- Create: `cli/research_iteration_v5_recovery.py`

- [ ] **Step 1: Write failing tests for the recovery helper**

Create `tests/unit/test_research_iteration_v5_recovery.py` with this content:

```python
from cli.research_iteration_v5_recovery import build_v5_recovery_candidate_pool


BEST_CONTEXT = {
    'strategy_name': 'WideV1Final_B_20260425',
    'expression': '66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
}


def _candidate(feature, operator='between', lower=1.0, upper=2.0, threshold=None, score=1.0, original_index=1):
    return {
        'feature': feature,
        'operator': operator,
        'lower_bound': lower,
        'upper_bound': upper,
        'threshold': threshold,
        'score': score,
        'combined_score': score,
        'source': 'quantile',
        'count': 100,
        'original_index': original_index,
    }


def test_v5_recovery_keeps_existing_v4_candidates_without_recovery():
    existing = [{
        'expression': '66.999 <= 시가총액 < 2_580 and 등락율 > 5',
        'v4_candidate_type': 'v4_repair_trade_amount',
        'v5_candidate_source': 'direct_v4',
    }]

    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[],
        existing_v4_result={'candidates': existing, 'candidate_count': 1},
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_등락율',
        secondary_features=[],
        candidate_count=2,
    )

    assert result['recovery_attempted'] is False
    assert result['recovery_reason'] == 'direct_v4_available'
    assert result['initial_v4_candidate_count'] == 1
    assert result['candidates'] == existing
    assert result['recovery_family_counts'] == {'direct_v4': 1}


def test_v5_recovery_builds_trade_feature_candidates_from_full_recommended_candidates():
    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[
            _candidate('B_체결강도', score=5.0, original_index=1),
            _candidate('B_등락율', operator='>', lower=None, upper=None, threshold=5.2, score=4.0, original_index=2),
        ],
        existing_v4_result={'candidates': [], 'candidate_count': 0},
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_등락율',
        secondary_features=[],
        candidate_count=2,
    )

    assert result['recovery_attempted'] is True
    assert result['recovery_reason'] == 'v4_candidate_pool_empty'
    assert result['initial_v4_candidate_count'] == 0
    assert result['recovery_family_counts']['recovered_trade_feature'] == 1
    assert any(candidate['v5_candidate_source'] == 'recovered_trade_feature' for candidate in result['candidates'])
    assert any('66.999 <= 시가총액 < 2_580' in candidate['expression'] for candidate in result['candidates'])
    assert any('등락율 > 5.2' in candidate['expression'] for candidate in result['candidates'])


def test_v5_recovery_builds_auto_secondary_candidates_when_secondary_features_are_empty():
    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[
            _candidate('B_체결강도', lower=70.0, upper=90.0, score=5.0, original_index=1),
            _candidate('B_현재가', lower=8000.0, upper=12000.0, score=3.0, original_index=2),
        ],
        existing_v4_result={'candidates': [], 'candidate_count': 0},
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_등락율',
        secondary_features=[],
        candidate_count=2,
    )

    auto_candidates = [
        candidate for candidate in result['candidates']
        if candidate['v5_candidate_source'] == 'auto_secondary_feature'
    ]
    assert result['recovery_family_counts']['auto_secondary_feature'] == 4
    assert len(auto_candidates) == 4
    assert any(candidate['secondary_feature'] == 'B_체결강도' for candidate in auto_candidates)
    assert any('체결강도' in candidate['expression'] for candidate in auto_candidates)


def test_v5_recovery_uses_safe_recommended_fallback_when_trade_and_secondary_are_missing():
    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[
            _candidate('B_시가총액', lower=3000.0, upper=5000.0, score=9.0, original_index=1),
            _candidate('B_회전율', operator='>', lower=None, upper=None, threshold=1.5, score=2.0, original_index=2),
        ],
        existing_v4_result={'candidates': [], 'candidate_count': 0},
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_등락율',
        secondary_features=['B_없는피처'],
        candidate_count=2,
    )

    fallback_candidates = [
        candidate for candidate in result['candidates']
        if candidate['v5_candidate_source'] == 'safe_recommended_fallback'
    ]
    assert result['recovery_family_counts']['safe_recommended_fallback'] == 1
    assert len(fallback_candidates) == 1
    assert '회전율 > 1.5' in fallback_candidates[0]['expression']
    assert '시가총액' in fallback_candidates[0]['expression']


def test_v5_recovery_dedupes_candidates_and_records_final_pool_count():
    duplicate_trade = _candidate('B_등락율', operator='>', lower=None, upper=None, threshold=5.2, score=4.0, original_index=2)
    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[duplicate_trade, dict(duplicate_trade)],
        existing_v4_result={'candidates': [], 'candidate_count': 0},
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_등락율',
        secondary_features=[],
        candidate_count=2,
    )

    expressions = [candidate['expression'] for candidate in result['candidates']]
    assert len(expressions) == len(set(expressions))
    assert result['final_candidate_pool_count'] == len(result['candidates'])
    assert result['candidate_count'] == len(result['candidates'])
```

- [ ] **Step 2: Run the failing helper tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v5_recovery.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'cli.research_iteration_v5_recovery'
```

- [ ] **Step 3: Implement `cli/research_iteration_v5_recovery.py`**

Create `cli/research_iteration_v5_recovery.py` with this content:

```python
"""Recovery candidate pool helpers for Wide v2 v5 runs."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, TypeAlias

from cli.condition_generator import candidate_to_expression
from cli.research_iteration_v2 import candidate_signature
from cli.research_iteration_v3 import parse_best_expression_conditions

JsonDict: TypeAlias = dict[str, Any]


def _score_value(candidate: JsonDict, key: str) -> float:
    try:
        return float(candidate.get(key, candidate.get('score', 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _candidate_expression(candidate: JsonDict) -> str:
    if candidate.get('source') != 'best_context' and candidate.get('expression'):
        return str(candidate['expression'])
    return candidate_to_expression(candidate, runtime_context=True)


def _with_original_indexes(candidates: list[JsonDict]) -> list[JsonDict]:
    indexed: list[JsonDict] = []
    for index, candidate in enumerate(candidates):
        item = deepcopy(candidate)
        item.setdefault('original_index', index)
        indexed.append(item)
    return indexed


def _combo_candidate(
    conditions: list[JsonDict],
    *,
    v4_candidate_type: str,
    v5_candidate_source: str,
    source_candidate: JsonDict,
    primary_feature: str,
    trade_amount_feature: str,
    secondary_feature: str | None = None,
) -> JsonDict:
    item: JsonDict = {
        'feature': source_candidate.get('feature'),
        'operator': source_candidate.get('operator'),
        'lower_bound': source_candidate.get('lower_bound'),
        'upper_bound': source_candidate.get('upper_bound'),
        'threshold': source_candidate.get('threshold'),
        'score': sum(_score_value(condition, 'score') for condition in conditions),
        'combined_score': sum(_score_value(condition, 'combined_score') for condition in conditions),
        'source': 'v5_recovery_pool',
        'primary_feature': primary_feature,
        'trade_amount_feature': trade_amount_feature,
        'secondary_feature': secondary_feature,
        'v4_candidate_type': v4_candidate_type,
        'v5_candidate_source': v5_candidate_source,
        'conditions': [deepcopy(condition) for condition in conditions],
        'retention_estimate': deepcopy(source_candidate.get('retention_estimate') or {}),
        'retention_filter_passed': source_candidate.get('retention_filter_passed'),
        'retention_fallback_used': source_candidate.get('retention_fallback_used', False),
    }
    if 'original_index' in source_candidate:
        item['original_index'] = source_candidate.get('original_index')
    item['expression'] = ' and '.join(_candidate_expression(condition) for condition in item['conditions'])
    return item


def _ranked_candidates(candidates: list[JsonDict]) -> list[JsonDict]:
    ranked = _with_original_indexes(candidates)
    ranked.sort(
        key=lambda candidate: (
            -_score_value(candidate, 'combined_score'),
            -_score_value(candidate, 'score'),
            int(candidate.get('original_index') or 0),
            str(candidate.get('feature') or ''),
        )
    )
    return ranked


def _dedupe_candidates(candidates: list[JsonDict]) -> list[JsonDict]:
    deduped: list[JsonDict] = []
    seen: set[tuple[object, object, object]] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            str(item.get('v5_candidate_source') or ''),
            -_score_value(item, 'combined_score'),
            str(item.get('expression') or ''),
        ),
    ):
        key = (
            candidate.get('v5_candidate_source'),
            candidate.get('expression'),
            candidate_signature(candidate),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _non_seed_candidates(
    candidates: list[JsonDict],
    *,
    primary_feature: str,
    trade_amount_feature: str,
) -> list[JsonDict]:
    return [
        candidate for candidate in candidates
        if candidate.get('feature') not in {primary_feature, trade_amount_feature}
    ]


def _secondary_candidates(
    candidates: list[JsonDict],
    *,
    primary_feature: str,
    trade_amount_feature: str,
    secondary_features: list[str] | None,
    candidate_count: int,
) -> list[JsonDict]:
    explicit = [
        candidate for candidate in candidates
        if candidate.get('feature') in set(secondary_features or [])
        and candidate.get('feature') not in {primary_feature, trade_amount_feature}
    ]
    if explicit:
        return explicit

    auto: list[JsonDict] = []
    seen_features: set[object] = set()
    for candidate in _non_seed_candidates(
        candidates,
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
    ):
        feature = candidate.get('feature')
        if feature in seen_features:
            continue
        seen_features.add(feature)
        auto.append(candidate)
        if len(auto) >= max(int(candidate_count), 1):
            break
    return auto


def _family_counts(candidates: list[JsonDict]) -> dict[str, int]:
    return dict(Counter(str(candidate.get('v5_candidate_source') or '') for candidate in candidates))


def build_v5_recovery_candidate_pool(
    *,
    full_recommended_candidates: list[JsonDict],
    existing_v4_result: JsonDict | None,
    best_context: JsonDict,
    primary_feature: str,
    trade_amount_feature: str,
    secondary_features: list[str] | None,
    candidate_count: int,
) -> JsonDict:
    existing_v4_result = existing_v4_result or {}
    existing_candidates = [dict(candidate) for candidate in existing_v4_result.get('candidates') or []]
    initial_v4_candidate_count = int(existing_v4_result.get('candidate_count') or len(existing_candidates))
    if existing_candidates:
        for candidate in existing_candidates:
            candidate.setdefault('v5_candidate_source', 'direct_v4')
        return {
            'status': 'ok',
            'mode': 'best_feature_mix_v5_recovery',
            'recovery_attempted': False,
            'recovery_reason': 'direct_v4_available',
            'initial_v4_candidate_count': initial_v4_candidate_count,
            'candidates': existing_candidates,
            'candidate_count': len(existing_candidates),
            'recovery_family_counts': {'direct_v4': len(existing_candidates)},
            'final_candidate_pool_count': len(existing_candidates),
        }

    best_primary, best_trade_amount = parse_best_expression_conditions(
        str(best_context.get('expression') or ''),
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
    )
    recommended = _ranked_candidates(full_recommended_candidates)
    candidates: list[JsonDict] = []

    for trade_candidate in recommended:
        if trade_candidate.get('feature') != trade_amount_feature:
            continue
        if candidate_signature(trade_candidate) == candidate_signature(best_trade_amount):
            continue
        candidates.append(_combo_candidate(
            [best_primary, trade_candidate],
            v4_candidate_type='v4_repair_trade_amount',
            v5_candidate_source='recovered_trade_feature',
            source_candidate=trade_candidate,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
        ))

    for secondary in _secondary_candidates(
        recommended,
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
        secondary_features=secondary_features,
        candidate_count=candidate_count,
    ):
        secondary_feature = str(secondary.get('feature') or '')
        candidates.append(_combo_candidate(
            [best_primary, best_trade_amount, secondary],
            v4_candidate_type='v4_tighten_secondary',
            v5_candidate_source='auto_secondary_feature',
            source_candidate=secondary,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
            secondary_feature=secondary_feature,
        ))
        candidates.append(_combo_candidate(
            [best_primary, secondary],
            v4_candidate_type='v4_replace_secondary',
            v5_candidate_source='auto_secondary_feature',
            source_candidate=secondary,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
            secondary_feature=secondary_feature,
        ))

    if len(candidates) < max(int(candidate_count), 1):
        for fallback in _non_seed_candidates(
            recommended,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
        ):
            candidates.append(_combo_candidate(
                [best_primary, fallback],
                v4_candidate_type='v4_replace_secondary',
                v5_candidate_source='safe_recommended_fallback',
                source_candidate=fallback,
                primary_feature=primary_feature,
                trade_amount_feature=trade_amount_feature,
                secondary_feature=str(fallback.get('feature') or ''),
            ))
            if len(candidates) >= max(int(candidate_count), 1):
                break

    candidates = _dedupe_candidates(candidates)
    return {
        'status': 'ok',
        'mode': 'best_feature_mix_v5_recovery',
        'recovery_attempted': True,
        'recovery_reason': 'v4_candidate_pool_empty',
        'initial_v4_candidate_count': initial_v4_candidate_count,
        'candidates': candidates,
        'candidate_count': len(candidates),
        'recovery_family_counts': _family_counts(candidates),
        'final_candidate_pool_count': len(candidates),
    }
```

- [ ] **Step 4: Run the helper tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v5_recovery.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add cli\research_iteration_v5_recovery.py tests\unit\test_research_iteration_v5_recovery.py
git commit -m "Wide v2 v5 후보 풀 복구 helper를 추가한다" -m @"
Wide v2 smoke 실패 원인인 v5 후보 풀 0개 상황을 복구하기 위해 백테스트를 실행하지 않는 순수 후보 생성 helper를 추가한다.

Constraint: Wide v6/v7 신규 단계 없이 Wide v2 v5 내부 복구로 제한한다
Rejected: top_n 증가만으로 복구 | 다음 seed에서 같은 후보 풀 shortfall이 반복될 수 있다
Confidence: high
Scope-risk: narrow
Directive: 이 helper는 후보 생성만 담당하며 retention, row-set, 백테스트 실행 책임을 갖지 않는다
Tested: python -m pytest tests/unit/test_research_iteration_v5_recovery.py -q
Not-tested: 실제 smoke runtime은 research_loop 연결 이후 검증한다
"@
```

---

### Task 2: Research Loop Recovery Integration

**Files:**
- Modify: `tests/unit/test_research_loop.py`
- Modify: `cli/research_loop.py`

- [ ] **Step 1: Add a failing research loop test for v5 recovery execution**

Append this test near the existing v5 tests in `tests/unit/test_research_loop.py`:

```python
def test_run_research_iteration_uses_v5_recovery_when_v4_pool_is_empty(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'keep_metric': -1, '종목명': 'A', '매수시간': 20250101090000, '매도시간': 20250101090100, '매수가': 100, '매도가': 101, '수익률': 1.0, '수익금': 1000},
        {'keep_metric': 10, '종목명': 'B', '매수시간': 20250101090200, '매도시간': 20250101090300, '매수가': 100, '매도가': 99, '수익률': -1.0, '수익금': -1000},
        {'keep_metric': 20, '종목명': 'C', '매수시간': 20250101090400, '매도시간': 20250101090500, '매수가': 100, '매도가': 102, '수익률': 2.0, '수익금': 2000},
    ]).to_csv(baseline, index=False, encoding='utf-8-sig')
    monkeypatch.setattr(research_loop, 'validate_research_iteration_config', lambda config: {'status': 'ok'})
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {
        'status': 'ok',
        'recommended_candidates': [
            {'feature': 'B_등락율', 'operator': '>', 'threshold': 5.2, 'score': 4.0, 'combined_score': 4.0, 'source': 'quantile'},
            {'feature': 'B_체결강도', 'operator': 'between', 'lower_bound': 70.0, 'upper_bound': 90.0, 'score': 3.0, 'combined_score': 3.0, 'source': 'quantile'},
        ],
    })
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['70 <= 체결강도 < 90', '8000 <= 현재가 < 12000'],
            'selected_candidates': [
                {'feature': 'B_체결강도', 'operator': 'between', 'lower_bound': 70.0, 'upper_bound': 90.0, 'score': 3.0, 'combined_score': 3.0},
                {'feature': 'B_현재가', 'operator': 'between', 'lower_bound': 8000.0, 'upper_bound': 12000.0, 'score': 2.0, 'combined_score': 2.0},
            ],
        },
    )
    monkeypatch.setattr(
        research_loop,
        'build_v4_candidate_pool',
        lambda *args, **kwargs: {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'candidates': [],
            'candidate_count': 0,
            'type_counts': {'v4_control_keep_best': 1},
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
            'comparison': {'trade_count_retention': 0.8},
            'promotion': {'status': 'ok', 'passed': True, 'score': float(spec['index'])},
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': float(spec['index']),
                'adjusted_score': float(spec['index']),
                'trade_count': 10,
                'trade_count_retention': 0.8,
                'date_concentration': 0.0,
                'symbol_concentration': 0.0,
            },
        },
    )
    monkeypatch.setattr(
        research_loop,
        'select_actual_rowset_representatives',
        lambda ranked, runtime_root, requested_count: (
            ranked[:requested_count],
            {
                'status': 'ok',
                'row_set_identity_status': 'all_distinct',
                'requested_count': requested_count,
                'executed_count': len(ranked),
                'actual_group_count': len(ranked),
                'selected_count': requested_count,
                'selected_strategy_names': [candidate['strategy_name'] for candidate in ranked[:requested_count]],
            },
        ),
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V5Recovery',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1Final_B_20260425',
            iteration_v2_best_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_trade_amount_feature='B_등락율',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert len(executed_specs) == 2
    assert result['iteration_v5']['recovery']['recovery_attempted'] is True
    assert result['iteration_v5']['recovery']['recovery_reason'] == 'v4_candidate_pool_empty'
    assert result['initial_v4_candidate_count'] == 0
    assert result['recovery_attempted'] is True
    assert result['final_candidate_pool_count'] >= 2
    assert result['retention_selection']['pool_count'] >= 2
    assert any(
        candidate['source_candidate']['v5_candidate_source'] in {'recovered_trade_feature', 'auto_secondary_feature'}
        for candidate in result['candidate_specs']
    )
```

- [ ] **Step 2: Add a failing metadata regression test**

Append this second test in `tests/unit/test_research_loop.py`:

```python
def test_run_research_iteration_reports_v5_recovery_metadata_on_shortfall(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'keep_metric': 1, '종목명': 'A', '매수시간': 20250101090000, '매도시간': 20250101090100, '매수가': 100, '매도가': 101, '수익률': 1.0, '수익금': 1000},
    ]).to_csv(baseline, index=False, encoding='utf-8-sig')
    monkeypatch.setattr(research_loop, 'validate_research_iteration_config', lambda config: {'status': 'ok'})
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {
        'status': 'ok',
        'recommended_candidates': [],
    })
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['keep_metric < 0', 'keep_metric > 100'],
            'selected_candidates': [
                {'feature': 'B_체결강도', 'operator': 'between', 'lower_bound': 70.0, 'upper_bound': 90.0, 'score': 1.0, 'combined_score': 1.0},
                {'feature': 'B_현재가', 'operator': 'between', 'lower_bound': 8000.0, 'upper_bound': 12000.0, 'score': 1.0, 'combined_score': 1.0},
            ],
        },
    )
    monkeypatch.setattr(
        research_loop,
        'build_v4_candidate_pool',
        lambda *args, **kwargs: {'status': 'ok', 'candidates': [], 'candidate_count': 0, 'type_counts': {'v4_control_keep_best': 1}},
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V5RecoveryShortfall',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1Final_B_20260425',
            iteration_v2_best_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_trade_amount_feature='B_등락율',
        ),
        controller=object(),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'insufficient_retention_candidates'
    assert result['requested_candidate_count'] == 2
    assert result['selected_candidate_count'] == 0
    assert result['initial_v4_candidate_count'] == 0
    assert result['recovery_attempted'] is True
    assert result['final_candidate_pool_count'] == 0
    assert result['eligible_count'] == 0
```

- [ ] **Step 3: Run the failing research loop tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_run_research_iteration_uses_v5_recovery_when_v4_pool_is_empty `
  tests/unit/test_research_loop.py::test_run_research_iteration_reports_v5_recovery_metadata_on_shortfall `
  -q
```

Expected:

```text
FAILED
```

The failure should mention `build_v5_recovery_candidate_pool` is not imported/used or missing metadata fields.

- [ ] **Step 4: Import the recovery helper in `cli/research_loop.py`**

In `cli/research_loop.py`, add this import after the `cli.research_iteration_v5` import block:

```python
from cli.research_iteration_v5_recovery import build_v5_recovery_candidate_pool
```

- [ ] **Step 5: Add metadata extraction helper in `cli/research_loop.py`**

Add this function after the `_iteration_generation_metadata` function:

```python
def _v5_candidate_pool_metadata(
    iteration_v5: dict[str, object] | None,
    retention_selection: dict | None = None,
) -> dict[str, object]:
    if not iteration_v5:
        return {}
    recovery = iteration_v5.get('recovery')
    if not isinstance(recovery, dict):
        recovery = {}
    selected_count = None
    eligible_count = iteration_v5.get('eligible_count')
    if isinstance(retention_selection, dict):
        selected_count = retention_selection.get('selected_count')
        eligible_count = retention_selection.get('eligible_count', eligible_count)
    return {
        'initial_v4_candidate_count': iteration_v5.get('initial_v4_candidate_count'),
        'recovery_attempted': recovery.get('recovery_attempted', False),
        'recovery_reason': recovery.get('recovery_reason'),
        'recovery_family_counts': recovery.get('recovery_family_counts') or {},
        'final_candidate_pool_count': recovery.get('final_candidate_pool_count'),
        'eligible_count': eligible_count,
        'execution_count': iteration_v5.get('execution_count'),
        'planned_execution_count': iteration_v5.get('planned_execution_count'),
        'selected_candidate_count': selected_count,
    }
```

- [ ] **Step 6: Wire v5 recovery into the v4/v5 branch in `run_research_iteration()`**

In `cli/research_loop.py`, replace this block in the `elif config.iteration_v2_mode in {'best_feature_mix_v4', 'best_feature_mix_v5'}:` branch:

```python
        expression_candidates = iteration_v4.get('candidates') or []
        expression_result = {
            **expression_result,
            'selected_candidates': expression_candidates,
            'expressions': [candidate['expression'] for candidate in expression_candidates],
            'candidate_count': len(expression_candidates),
            'iteration_v4': iteration_v4,
        }
        if config.iteration_v2_mode == 'best_feature_mix_v5':
            iteration_v5 = {
                'status': 'pool_built',
                'mode': 'best_feature_mix_v5',
                'requested_count': config.candidate_count,
                'v4_candidate_count': len(expression_candidates),
            }
        expressions = expression_result['expressions']
```

with:

```python
        expression_candidates = iteration_v4.get('candidates') or []
        if config.iteration_v2_mode == 'best_feature_mix_v5':
            recovery_result = build_v5_recovery_candidate_pool(
                full_recommended_candidates=analysis_result.get('recommended_candidates') or [],
                existing_v4_result=iteration_v4,
                best_context=best_context,
                primary_feature=config.iteration_v2_primary_feature,
                trade_amount_feature=config.iteration_v2_trade_amount_feature,
                secondary_features=_split_csv_values(config.iteration_v2_secondary_features),
                candidate_count=config.candidate_count,
            )
            expression_candidates = recovery_result.get('candidates') or []
            iteration_v5 = {
                'status': 'pool_built',
                'mode': 'best_feature_mix_v5',
                'requested_count': config.candidate_count,
                'v4_candidate_count': len(iteration_v4.get('candidates') or []),
                'initial_v4_candidate_count': recovery_result.get('initial_v4_candidate_count'),
                'recovery': {
                    'recovery_attempted': recovery_result.get('recovery_attempted'),
                    'recovery_reason': recovery_result.get('recovery_reason'),
                    'recovery_family_counts': recovery_result.get('recovery_family_counts') or {},
                    'final_candidate_pool_count': recovery_result.get('final_candidate_pool_count'),
                },
            }
        expression_result = {
            **expression_result,
            'selected_candidates': expression_candidates,
            'expressions': [candidate['expression'] for candidate in expression_candidates],
            'candidate_count': len(expression_candidates),
            'iteration_v4': iteration_v4,
        }
        if config.iteration_v2_mode == 'best_feature_mix_v5':
            expression_result['iteration_v5_recovery'] = (iteration_v5 or {}).get('recovery')
        expressions = expression_result['expressions']
```

- [ ] **Step 7: Preserve recovery metadata after row-set selection**

In the `if config.iteration_v2_mode == 'best_feature_mix_v5':` block after the `select_rowset_diverse_candidates` call, replace the existing `iteration_v5` reassignment that sets `status`, `requested_count`, `eligible_count`, `execution_count`, and `planned_execution_count` with:

```python
            iteration_v5 = {
                **(iteration_v5 or {}),
                'status': 'execution_pool_selected',
                'requested_count': config.candidate_count,
                'eligible_count': eligible_count,
                'execution_count': len(selected_candidates),
                'planned_execution_count': rowset_selection_count,
            }
```

This preserves the existing `recovery` metadata instead of overwriting it.

- [ ] **Step 8: Add v5 metadata to insufficient-candidate error payload**

In the `if len(selected_candidates) < config.candidate_count:` error payload, add:

```python
                **_v5_candidate_pool_metadata(iteration_v5, retention_selection),
```

immediately after:

```python
                selected_candidate_count=len(selected_candidates),
```

- [ ] **Step 9: Add v5 metadata to final result payload**

In the final `result_payload` dictionary near the end of `run_research_iteration()`, add:

```python
        **_v5_candidate_pool_metadata(iteration_v5, retention_selection),
```

immediately after:

```python
        'actual_rowset_selection': actual_rowset_selection,
```

- [ ] **Step 10: Run the research loop tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_run_research_iteration_uses_v5_recovery_when_v4_pool_is_empty `
  tests/unit/test_research_loop.py::test_run_research_iteration_reports_v5_recovery_metadata_on_shortfall `
  -q
```

Expected:

```text
2 passed
```

- [ ] **Step 11: Run focused v5/research loop tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v5_recovery.py tests/unit/test_research_loop.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 12: Commit Task 2**

Run:

```powershell
git add cli\research_loop.py tests\unit\test_research_loop.py
git commit -m "Wide v2 research loop에 v5 후보 풀 복구를 연결한다" -m @"
best_feature_mix_v5에서 v4 후보 풀이 0개일 때 full recommended candidates 기반 recovery 후보를 만들고 기존 retention/row-set selection으로 넘긴다.

Constraint: 후보 생성은 넓히되 retention과 row-set 선별은 우회하지 않는다
Rejected: research_loop.py 대규모 분리 | MVP 종료 전 리팩토링은 지연 위험이 크다
Confidence: medium
Scope-risk: moderate
Directive: recovery 후보가 있어도 final_best_candidate는 WFO/OOS 승인 전까지 실전 후보가 아니다
Tested: python -m pytest tests/unit/test_research_iteration_v5_recovery.py tests/unit/test_research_loop.py -q
Not-tested: 실제 smoke runtime은 Task 5에서 별도 실행한다
"@
```

---

### Task 3: Optimizer Failure Metadata Propagation

**Files:**
- Modify: `tests/unit/test_research_optimizer.py`
- Modify: `cli/research_optimizer.py`

- [ ] **Step 1: Add failing optimizer metadata test**

Append this test near `test_optimizer_maps_insufficient_retention_candidates_to_insufficient_candidates()` in `tests/unit/test_research_optimizer.py`:

```python
def test_optimizer_preserves_v5_recovery_metadata_on_insufficient_candidates():
    def fake_runner(config, controller):
        return {
            'status': 'error',
            'phase': 'insufficient_retention_candidates',
            'message': 'candidate_count=2 requested but only 0 candidates selected after retention filtering',
            'requested_candidate_count': 2,
            'selected_candidate_count': 0,
            'initial_v4_candidate_count': 0,
            'recovery_attempted': True,
            'recovery_reason': 'v4_candidate_pool_empty',
            'recovery_family_counts': {'recovered_trade_feature': 1},
            'final_candidate_pool_count': 1,
            'eligible_count': 0,
            'execution_count': 0,
            'planned_execution_count': 0,
            'iteration_v5': {
                'recovery': {
                    'recovery_attempted': True,
                    'recovery_reason': 'v4_candidate_pool_empty',
                    'recovery_family_counts': {'recovered_trade_feature': 1},
                    'final_candidate_pool_count': 1,
                },
            },
        }

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2RecoveryMetadata',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=3,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert result['status'] == 'error'
    assert result['stop_reason'] == 'insufficient_candidates'
    assert result['requested_candidate_count'] == 2
    assert result['selected_candidate_count'] == 0
    assert result['initial_v4_candidate_count'] == 0
    assert result['recovery_attempted'] is True
    assert result['recovery_reason'] == 'v4_candidate_pool_empty'
    assert result['recovery_family_counts'] == {'recovered_trade_feature': 1}
    assert result['final_candidate_pool_count'] == 1
    assert result['eligible_count'] == 0
```

- [ ] **Step 2: Run the failing optimizer metadata test**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py::test_optimizer_preserves_v5_recovery_metadata_on_insufficient_candidates -q
```

Expected:

```text
FAILED
```

The failure should show missing top-level recovery metadata.

- [ ] **Step 3: Extend optimizer failure metadata extraction**

In `cli/research_optimizer.py`, add this tuple after `_RUNTIME_FAILURE_PHASES`:

```python
_ROUND_FAILURE_METADATA_KEYS = (
    'requested_candidate_count',
    'selected_candidate_count',
    'initial_v4_candidate_count',
    'recovery_attempted',
    'recovery_reason',
    'recovery_family_counts',
    'final_candidate_pool_count',
    'eligible_count',
    'execution_count',
    'planned_execution_count',
)
```

- [ ] **Step 4: Replace the `_failure_metadata` function**

Replace the existing `_failure_metadata` function with:

```python
def _failure_metadata(
    *,
    failed_round: int | None = None,
    failure_phase: Any = None,
    failure_message: Any = None,
    actual_rowset_selection: dict[str, Any] | None = None,
    round_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actual_selection = actual_rowset_selection or {}
    round_payload = round_result or {}
    metadata = {
        'failed_round': failed_round,
        'failure_phase': failure_phase,
        'failure_message': failure_message,
        'requested_candidate_count': (
            actual_selection.get('requested_count')
            if actual_selection.get('requested_count') is not None
            else round_payload.get('requested_candidate_count')
        ),
        'selected_candidate_count': (
            _selected_candidate_count(actual_selection)
            if actual_selection
            else round_payload.get('selected_candidate_count')
        ),
    }
    for key in _ROUND_FAILURE_METADATA_KEYS:
        if key in {'requested_candidate_count', 'selected_candidate_count'}:
            continue
        if key in round_payload:
            metadata[key] = round_payload.get(key)
    return json_safe_value(metadata)
```

- [ ] **Step 5: Pass round_result into the `_failure_metadata` call**

In the `if round_result.get('status') != 'ok':` block, update the call to:

```python
                failure_metadata = _failure_metadata(
                    failed_round=round_index,
                    failure_phase=round_result.get('phase'),
                    failure_message=round_result.get('message'),
                    actual_rowset_selection=round_result.get('actual_rowset_selection'),
                    round_result=round_result,
                )
```

- [ ] **Step 6: Run optimizer tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py::test_optimizer_preserves_v5_recovery_metadata_on_insufficient_candidates tests/unit/test_research_optimizer.py::test_optimizer_maps_insufficient_retention_candidates_to_insufficient_candidates -q
```

Expected:

```text
2 passed
```

- [ ] **Step 7: Commit Task 3**

Run:

```powershell
git add cli\research_optimizer.py tests\unit\test_research_optimizer.py
git commit -m "Wide v2 optimizer 실패 메타데이터를 보존한다" -m @"
round-level v5 recovery와 후보 shortfall 메타데이터를 optimizer summary 최상위로 전달해 smoke 실패 원인을 round JSON 없이도 확인할 수 있게 한다.

Constraint: 실패는 traceback이 아니라 구조화된 stop_reason/failure metadata로 분석 가능해야 한다
Rejected: report에서 round JSON을 직접 읽어 보완 | summary payload 계약이 계속 불완전해진다
Confidence: high
Scope-risk: narrow
Directive: 신규 실패 phase를 추가할 때는 optimizer stop_reason과 summary metadata 전파를 함께 갱신한다
Tested: python -m pytest tests/unit/test_research_optimizer.py::test_optimizer_preserves_v5_recovery_metadata_on_insufficient_candidates tests/unit/test_research_optimizer.py::test_optimizer_maps_insufficient_retention_candidates_to_insufficient_candidates -q
Not-tested: 실제 smoke runtime은 Task 5에서 별도 실행한다
"@
```

---

### Task 4: Optimizer Report Recovery Visibility

**Files:**
- Modify: `tests/unit/test_research_optimizer_report.py`
- Modify: `cli/research_optimizer_report.py`

- [ ] **Step 1: Add failing report test**

Append this test to `tests/unit/test_research_optimizer_report.py`:

```python
def test_render_optimizer_summary_markdown_includes_v5_recovery_metadata():
    result = _result()
    result.update({
        'initial_v4_candidate_count': 0,
        'recovery_attempted': True,
        'recovery_reason': 'v4_candidate_pool_empty',
        'recovery_family_counts': {'recovered_trade_feature': 1, 'auto_secondary_feature': 2},
        'final_candidate_pool_count': 3,
        'eligible_count': 2,
        'execution_count': 2,
        'planned_execution_count': 4,
    })

    markdown = render_optimizer_summary_markdown(result)

    assert '## V5 recovery' in markdown
    assert '- initial_v4_candidate_count=0' in markdown
    assert '- recovery_attempted=True' in markdown
    assert '- recovery_reason=v4_candidate_pool_empty' in markdown
    assert 'recovered_trade_feature' in markdown
    assert '- final_candidate_pool_count=3' in markdown
    assert '- eligible_count=2' in markdown
    assert '- execution_count=2' in markdown
    assert '- planned_execution_count=4' in markdown
```

- [ ] **Step 2: Run the failing report test**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer_report.py::test_render_optimizer_summary_markdown_includes_v5_recovery_metadata -q
```

Expected:

```text
FAILED
```

The failure should show `## V5 recovery` is missing.

- [ ] **Step 3: Add a report helper for recovery metadata**

In `cli/research_optimizer_report.py`, add this function after the `_leaderboard_rows` function:

```python
def _recovery_lines(result: dict[str, Any]) -> list[str]:
    recovery_family_counts = result.get('recovery_family_counts') or {}
    return [
        '## V5 recovery',
        '',
        _bullet('initial_v4_candidate_count', result.get('initial_v4_candidate_count')),
        _bullet('recovery_attempted', result.get('recovery_attempted')),
        _bullet('recovery_reason', result.get('recovery_reason')),
        _bullet('recovery_family_counts', recovery_family_counts),
        _bullet('final_candidate_pool_count', result.get('final_candidate_pool_count')),
        _bullet('eligible_count', result.get('eligible_count')),
        _bullet('execution_count', result.get('execution_count')),
        _bullet('planned_execution_count', result.get('planned_execution_count')),
        '',
    ]
```

- [ ] **Step 4: Render recovery section before Stop reason**

In the `render_optimizer_summary_markdown` function, insert this block after the leaderboard table and before `'## Stop reason'`:

```python
        *_recovery_lines(result),
```

The surrounding list should become:

```python
        '## Global leaderboard top candidates',
        '',
        *_leaderboard_rows(result),
        '',
        *_recovery_lines(result),
        '## Stop reason',
```

- [ ] **Step 5: Run report tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer_report.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit Task 4**

Run:

```powershell
git add cli\research_optimizer_report.py tests\unit\test_research_optimizer_report.py
git commit -m "Wide v2 보고서에 v5 복구 상태를 표시한다" -m @"
optimizer Markdown report에 v5 candidate pool recovery 섹션을 추가해 후보 풀 shortfall과 recovery family별 후보 수를 바로 확인할 수 있게 한다.

Constraint: 사용자가 round JSON까지 파지 않아도 smoke 실패 원인을 확인할 수 있어야 한다
Rejected: report 문서에 수동 설명만 추가 | 다음 실행마다 자동 관찰성이 깨진다
Confidence: high
Scope-risk: narrow
Directive: recovery metadata 키 이름은 optimizer summary JSON과 Markdown report에서 동일하게 유지한다
Tested: python -m pytest tests/unit/test_research_optimizer_report.py -q
Not-tested: 실제 smoke report는 Task 5에서 생성한다
"@
```

---

### Task 5: Focused Verification and Smoke Rerun

**Files:**
- Create if smoke runs: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_recovery_smoke_review.md`
- Read generated, do not stage: `backtest/temp/wide_v2_v5_recovery_smoke_20260428*.json`
- Read generated, do not stage: `backtest/csv/*`

- [ ] **Step 1: Run focused unit tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_iteration_v5_recovery.py `
  tests/unit/test_research_loop.py `
  tests/unit/test_research_optimizer.py `
  tests/unit/test_research_optimizer_report.py `
  tests/unit/test_subcommands.py `
  -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 2: Run non-release sync guard**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 3: Run whitespace check**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
no output
```

- [ ] **Step 4: Run candidate_count=2 recovery smoke**

Run:

```powershell
$env:PYTHONUTF8='1'
$smokeStart = Get-Date
$consolePath = 'backtest\temp\wide_v2_v5_recovery_smoke_20260428_console.txt'
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2V5RecoverySmoke_20260428 `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --seed-candidate WideV1Final_B_20260425 `
  --seed-expression "66.999 <= 시가총액 < 2_580 and 등락율 > 4.83" `
  --iteration-v2-trade-amount-feature "B_등락율" `
  --start 20250101 `
  --end 20251231 `
  --candidate-count 2 `
  --max-rounds 2 `
  --candidate-timeout 900 `
  --runtime-output backtest\temp\wide_v2_v5_recovery_smoke_20260428.json `
  --leaderboard-output backtest\temp\wide_v2_v5_recovery_smoke_20260428_leaderboard.json `
  --summary-output backtest\temp\wide_v2_v5_recovery_smoke_20260428_summary.json `
  --report-path docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_recovery_smoke_summary.md *> $consolePath
$smokeExit = $LASTEXITCODE
$smokeEnd = Get-Date
$smokeElapsed = $smokeEnd - $smokeStart
[PSCustomObject]@{
  ExitCode = $smokeExit
  TotalMinutes = [Math]::Round($smokeElapsed.TotalMinutes, 2)
  ConsolePath = $consolePath
}
```

Expected healthy condition:

```text
ExitCode = 0
summary JSON exists
leaderboard JSON exists
Markdown report exists
```

Acceptable diagnostic condition:

```text
ExitCode = 1
status = error
failure_phase is candidate runtime related, not v4_candidate_count=0
recovery_attempted = True
final_candidate_pool_count > 0
```

Failure condition:

```text
status = error
failure_phase = insufficient_retention_candidates
initial_v4_candidate_count = 0
final_candidate_pool_count = 0
```

- [ ] **Step 5: Inspect smoke summary**

Run:

```powershell
$summary = Get-Content backtest\temp\wide_v2_v5_recovery_smoke_20260428_summary.json -Raw -Encoding UTF8 | ConvertFrom-Json
$summary | Select-Object status, stop_reason, completed_round_count, failed_round, failure_phase, failure_message, requested_candidate_count, selected_candidate_count, initial_v4_candidate_count, recovery_attempted, recovery_reason, final_candidate_pool_count, eligible_count, execution_count, planned_execution_count
$summary.recovery_family_counts
$summary.final_best_candidate | Select-Object round_index, candidate_index, strategy_name, adjusted_score, promotion_score
$summary.wfo_candidate | Select-Object strategy_name, source_round, source_candidate, next_command
```

Expected for MVP progress:

```text
recovery_attempted = True or False
final_candidate_pool_count > 0 when initial_v4_candidate_count = 0
execution_count > 0
```

- [ ] **Step 6: Inspect leaderboard**

Run:

```powershell
$leaderboard = Get-Content backtest\temp\wide_v2_v5_recovery_smoke_20260428_leaderboard.json -Raw -Encoding UTF8 | ConvertFrom-Json
[PSCustomObject]@{ LeaderboardCount = @($leaderboard).Count }
$leaderboard | Select-Object round_index, candidate_index, strategy_name, status, candidate_type, promotion_passed, adjusted_score, trade_count_retention
```

Expected if smoke reaches candidate evaluation:

```text
LeaderboardCount >= 1
```

- [ ] **Step 7: Write Korean smoke review**

If smoke was run, create `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_recovery_smoke_review.md` with concrete values by running:

```powershell
$summary = Get-Content backtest\temp\wide_v2_v5_recovery_smoke_20260428_summary.json -Raw -Encoding UTF8 | ConvertFrom-Json
$leaderboardPath = 'backtest\temp\wide_v2_v5_recovery_smoke_20260428_leaderboard.json'
$leaderboard = if (Test-Path $leaderboardPath) {
  @(Get-Content $leaderboardPath -Raw -Encoding UTF8 | ConvertFrom-Json)
} else {
  @()
}
$leaderboardCount = @($leaderboard).Count
$elapsedMinutes = [Math]::Round($smokeElapsed.TotalMinutes, 2)
$conclusion = if ($leaderboardCount -ge 1) {
  'PASS: 후보 백테스트 단계에 진입했고 leaderboard가 생성되었다.'
} elseif (($summary.final_candidate_pool_count -as [int]) -gt 0) {
  'PARTIAL: recovery 후보 풀은 생성되었지만 후보 런타임 또는 row-set selection에서 중단되었다.'
} else {
  'FAIL: recovery 후에도 final_candidate_pool_count가 0이다.'
}
$nextStep = if ($leaderboardCount -ge 1) {
  'candidate_count=10 full run 검증 계획으로 넘어간다.'
} elseif (($summary.final_candidate_pool_count -as [int]) -gt 0) {
  '새 failure_phase를 기준으로 recovery 설계를 좁힌다.'
} else {
  'v5 recovery 후보 family 생성 규칙을 다시 설계한다.'
}
$review = @"
# Wide v2 v5 recovery smoke 리뷰

## 목적

Wide v2 v5 recovery 구현 후 candidate_count=2 smoke가 후보 풀 0개 실패를 벗어나 후보 백테스트 단계까지 진입하는지 확인한다.

## 실행 요약

| 항목 | 값 |
| --- | --- |
| run_id | WideV2V5RecoverySmoke_20260428 |
| candidate_count | 2 |
| max_rounds | 2 |
| status | $($summary.status) |
| stop_reason | $($summary.stop_reason) |
| completed_round_count | $($summary.completed_round_count) |
| elapsed_minutes | $elapsedMinutes |

## Recovery 판정

| 항목 | 값 |
| --- | --- |
| initial_v4_candidate_count | $($summary.initial_v4_candidate_count) |
| recovery_attempted | $($summary.recovery_attempted) |
| recovery_reason | $($summary.recovery_reason) |
| final_candidate_pool_count | $($summary.final_candidate_pool_count) |
| eligible_count | $($summary.eligible_count) |
| execution_count | $($summary.execution_count) |
| planned_execution_count | $($summary.planned_execution_count) |
| leaderboard_count | $leaderboardCount |

## 결론

$conclusion

## 다음 단계

$nextStep
"@
Set-Content -Path docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_recovery_smoke_review.md -Value $review -Encoding UTF8
```

- [ ] **Step 8: Commit Task 5 smoke evidence if created**

If `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_recovery_smoke_summary.md` and the review document exist, run:

```powershell
git add `
  docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_recovery_smoke_summary.md `
  docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_recovery_smoke_review.md

git commit -m "Wide v2 v5 복구 smoke 결과를 기록한다" -m @"
v5 candidate pool recovery 구현 후 candidate_count=2 smoke 결과를 기록하고 full run 또는 추가 복구 여부를 판단한다.

Constraint: backtest/temp, backtest/csv, backtest/graph는 커밋하지 않는다
Constraint: smoke 통과는 WFO/OOS 승인과 다르다
Rejected: smoke 결과 없이 candidate_count=10 실행 | 후보 풀 복구 여부를 먼저 확인해야 한다
Confidence: medium
Scope-risk: narrow
Directive: final_best_candidate가 있을 때만 WFO/OOS 계획으로 넘어간다
Tested: candidate_count=2 Wide v2 v5 recovery smoke
Not-tested: candidate_count=10 full run and WFO/OOS validation
"@
```

If smoke report files do not exist because the run failed before report write, do not commit generated `backtest/temp` artifacts. Record the failure in the final response instead.

---

### Task 6: Final Verification Before PR Decision

**Files:**
- Verify only; do not create PR in this task.

- [ ] **Step 1: Run all unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
all unit tests pass
```

- [ ] **Step 2: Run sync guard**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 3: Run whitespace check**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
no output
```

- [ ] **Step 4: Check protected artifacts**

Run:

```powershell
git status --short --branch
```

Expected:

```text
Only code/tests/docs changes are tracked or committed.
backtest/graph/ remains untracked.
backtest/temp/ and backtest/csv/ generated artifacts are not staged.
utility/strategy.db is not staged.
```

- [ ] **Step 5: Decide PR readiness**

Use this decision table:

```text
If unit tests pass and smoke reaches candidate backtests:
  Prepare Korean PR report and create PR only after user asks or confirms.

If unit tests pass but smoke is PARTIAL:
  Do not PR yet. Start a new brainstorming step for the observed failure_phase.

If unit tests fail:
  Fix tests before any PR.

If protected artifacts are staged:
  Unstage them before any PR.
```

---

## Self-Review

- Spec coverage: This plan covers the helper module, research loop integration, optimizer metadata propagation, report rendering, smoke rerun, final verification, and no-PR-before-validation policy.
- Placeholder scan: Red-flag placeholder scan is clean. The smoke-review step generates concrete values from the summary JSON before committing the review document.
- Type consistency: The helper name is consistently `build_v5_recovery_candidate_pool`; metadata keys are consistently `initial_v4_candidate_count`, `recovery_attempted`, `recovery_reason`, `recovery_family_counts`, `final_candidate_pool_count`, `eligible_count`, `execution_count`, and `planned_execution_count`.
- Scope check: The plan does not add Wide v6/v7, does not alter WFO, does not refactor the whole CLI, and does not touch protected runtime/result paths.
