# Wide v1 v4 Row-Set Diversity Candidate Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `best_feature_mix_v4` candidate generation that selects candidates by family quota and pre-execution row-set proxy diversity, then prepares actual row-set verification after execution.

**Architecture:** Add a focused pure helper module for v4 candidate pool/proxy selection, wire it through the existing discovery research loop and CLI parser, then expose report and analysis-script surfaces. Keep existing v3 behavior unchanged and do not run new backtests, promote, WFO, or mutate `strategy.db` in this implementation plan.

**Tech Stack:** Python 3, pandas, pytest, Ruff, basedpyright, existing STOM CLI research modules under `cli/`, markdown docs under `docs/`.

---

## File Structure

- Create `cli/research_iteration_v4.py`
  - Builds v4 candidate pool from the v3 best context and analysis candidates.
  - Adds `v4_*` family metadata.
  - Computes pre-execution row-set proxy signatures from baseline CSV rows.
  - Selects candidates using proxy row-set diversity and family quota.

- Create `tests/unit/test_research_iteration_v4.py`
  - Unit tests for v4 family generation, proxy signature grouping, quota selection, shortfall summaries, and duplicate proxy rejection.

- Modify `cli/research_loop.py`
  - Add `best_feature_mix_v4` validation.
  - Build `iteration_v4` metadata.
  - Use v4 proxy-diverse selection only in v4 mode.
  - Preserve v2/v3 selection behavior outside v4 mode.

- Modify `tests/unit/test_research_loop.py`
  - Add v4 validation and loop wiring tests.
  - Add regression that v3 path still uses existing retention-aware selection.

- Modify `cli/subcommands.py`
  - Add parser choice `best_feature_mix_v4`.

- Modify `tests/unit/test_subcommands.py`
  - Add parser and handler payload tests for v4 mode.

- Modify `cli/research_report.py`
  - Add an `Iteration Loop v4 Row-Set Diversity` markdown section.

- Modify `tests/unit/test_research_report.py`
  - Add v4 report rendering test.

- Create `scripts/analyze_wide_v1_v4_rowset_diversity.py`
  - Thin wrapper for actual v4 runtime row-set verification after a v4 run exists.
  - Requires explicit runtime path/root because no v4 artifact exists yet.

- Create `tests/unit/test_research_v3_tiebreak.py` additions
  - Test the v4 analysis script wrapper by monkeypatching the writer.

- Create final docs after implementation
  - `docs/pr/2026-04-24_wide_v1_v4_row_set_diversity_candidate_generation_pr.md`

---

## Task 1: Pure v4 Candidate and Proxy Selection Helper

**Files:**
- Create: `cli/research_iteration_v4.py`
- Create: `tests/unit/test_research_iteration_v4.py`
- Reuse: `cli/research_iteration_v2.py`
- Reuse: `cli/research_iteration_v3.py`
- Reuse: `cli/condition_generator.py`
- Reference existing retention behavior without importing private helpers from `cli/research_retention.py`

- [ ] **Step 1: Write failing tests for v4 family generation and proxy grouping**

Create `tests/unit/test_research_iteration_v4.py` with this initial content:

```python
from __future__ import annotations

from typing import Any, TypeAlias

import pandas as pd

from cli.research_iteration_v4 import (
    annotate_candidate_rowset_proxy,
    build_v4_candidate_pool,
    estimate_candidate_rowset_proxy,
    select_rowset_diverse_candidates,
)

JsonDict: TypeAlias = dict[str, Any]

BEST_EXPRESSION = (
    '66.999 <= 시가총액 < 2_580 and '
    '1805.7 <= 당일거래대금 < 3654.4'
)
BEST_CONTEXT = {
    'strategy_name': 'WideV1IterationV2_20260423__cand005',
    'expression': BEST_EXPRESSION,
    'reference_adjusted_score': 13497.662902097409,
}


def _candidate(
    feature: str,
    lower: float,
    upper: float,
    *,
    score: float = 1.0,
    retention: float = 0.9,
) -> JsonDict:
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


def _baseline_frame() -> pd.DataFrame:
    return pd.DataFrame({
        '시가총액': [100.0, 200.0, 300.0, 400.0],
        '당일거래대금': [1900.0, 2500.0, 4000.0, 1000.0],
        '체결강도': [10.0, 20.0, 30.0, 40.0],
        '등락율': [1.0, 2.0, 3.0, 4.0],
    })


def test_build_v4_candidate_pool_generates_v4_families():
    result = build_v4_candidate_pool(
        [
            _candidate('B_체결강도', 0.0, 25.0, score=8.0),
            _candidate('B_등락율', 0.0, 3.0, score=7.0),
            _candidate('B_당일거래대금', 1000.0, 5000.0, score=6.0),
            _candidate('B_당일거래대금', 1500.0, 3000.0, score=5.0),
        ],
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도', 'B_등락율', 'B_당일거래대금'],
    )

    assert result['status'] == 'ok'
    assert result['mode'] == 'best_feature_mix_v4'
    assert result['control_candidate']['v4_candidate_type'] == 'v4_control_keep_best'
    assert result['type_counts']['v4_tighten_secondary'] >= 1
    assert result['type_counts']['v4_replace_secondary'] >= 1
    assert result['type_counts']['v4_repair_trade_amount'] >= 1
    assert result['type_counts']['v4_relax_trade_amount'] >= 1


def test_estimate_candidate_rowset_proxy_groups_identical_masks():
    frame = _baseline_frame()

    first = estimate_candidate_rowset_proxy(frame, '체결강도 < 25')
    second = estimate_candidate_rowset_proxy(frame, '체결강도 <= 20')
    distinct = estimate_candidate_rowset_proxy(frame, '등락율 < 3')

    assert first['evaluation_error'] is None
    assert first['proxy_removed_count'] == 2
    assert first['proxy_kept_count'] == 2
    assert first['proxy_retention'] == 0.5
    assert first['proxy_signature'] == second['proxy_signature']
    assert first['proxy_signature'] != distinct['proxy_signature']


def test_annotate_candidate_rowset_proxy_records_hash_and_counts():
    annotated = annotate_candidate_rowset_proxy(
        [
            {'expression': '체결강도 < 25', 'v4_candidate_type': 'v4_tighten_secondary'},
            {'expression': '등락율 < 3', 'v4_candidate_type': 'v4_replace_secondary'},
        ],
        _baseline_frame(),
        min_retention=0.4,
    )

    assert annotated[0]['rowset_proxy']['proxy_retention'] == 0.5
    assert annotated[0]['rowset_proxy']['proxy_filter_passed'] is True
    assert isinstance(annotated[0]['rowset_proxy']['proxy_signature_hash'], str)
    assert 'proxy_signature' in annotated[0]['rowset_proxy']


def test_select_rowset_diverse_candidates_skips_duplicate_proxy_groups_and_honors_family_targets():
    candidates = [
        {
            'expression': 'tighten-a',
            'v4_candidate_type': 'v4_tighten_secondary',
            'combined_score': 100.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({1, 2}),
                'proxy_signature_hash': 'a',
                'proxy_retention': 0.90,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
        {
            'expression': 'tighten-duplicate',
            'v4_candidate_type': 'v4_tighten_secondary',
            'combined_score': 99.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({1, 2}),
                'proxy_signature_hash': 'a',
                'proxy_retention': 0.91,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
        {
            'expression': 'repair-a',
            'v4_candidate_type': 'v4_repair_trade_amount',
            'combined_score': 80.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({2, 3}),
                'proxy_signature_hash': 'b',
                'proxy_retention': 0.85,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
        {
            'expression': 'replace-a',
            'v4_candidate_type': 'v4_replace_secondary',
            'combined_score': 70.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({3, 4}),
                'proxy_signature_hash': 'c',
                'proxy_retention': 0.80,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
    ]

    selected, summary = select_rowset_diverse_candidates(
        candidates,
        candidate_count=3,
        min_retention=0.4,
        family_targets={
            'v4_repair_trade_amount': 1,
            'v4_replace_secondary': 1,
            'v4_tighten_secondary': 1,
            'v4_relax_trade_amount': 1,
        },
    )

    assert [item['expression'] for item in selected] == ['repair-a', 'replace-a', 'tighten-a']
    assert 'tighten-duplicate' not in [item['expression'] for item in selected]
    assert summary['status'] == 'ok'
    assert summary['phase'] == 'rowset_diverse_candidates_selected'
    assert summary['proxy_group_count'] == 3
    assert summary['skipped_duplicate_proxy_count'] == 1
    assert summary['quota_summary']['v4_relax_trade_amount']['shortfall'] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v4.py -q
```

Expected:

```text
ERROR tests/unit/test_research_iteration_v4.py
ModuleNotFoundError: No module named 'cli.research_iteration_v4'
```

- [ ] **Step 3: Add the v4 helper implementation**

Create `cli/research_iteration_v4.py` with this implementation:

```python
"""Pure helpers for Wide v1 iteration loop v4 row-set diversity."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from typing import Any, TypeAlias

import pandas as pd

from cli.condition_generator import candidate_to_expression
from cli.research_iteration_v2 import candidate_signature
from cli.research_iteration_v3 import parse_best_expression_conditions

JsonDict: TypeAlias = dict[str, Any]
ProxySignature: TypeAlias = frozenset[int]

DEFAULT_FAMILY_TARGETS = {
    'v4_repair_trade_amount': 2,
    'v4_replace_secondary': 2,
    'v4_tighten_secondary': 2,
    'v4_relax_trade_amount': 2,
}


def _score_value(candidate: JsonDict, key: str) -> float:
    try:
        return float(candidate.get(key, candidate.get('score', 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _candidate_expression(candidate: JsonDict) -> str:
    if candidate.get('source') != 'best_context' and candidate.get('expression'):
        return str(candidate['expression'])
    return candidate_to_expression(candidate, runtime_context=True)


def _combo_candidate(
    conditions: list[JsonDict],
    *,
    candidate_type: str,
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
        'source': 'v4_candidate_pool',
        'primary_feature': primary_feature,
        'trade_amount_feature': trade_amount_feature,
        'secondary_feature': secondary_feature,
        'retention_estimate': deepcopy(source_candidate.get('retention_estimate') or {}),
        'retention_filter_passed': source_candidate.get('retention_filter_passed'),
        'retention_fallback_used': source_candidate.get('retention_fallback_used', False),
        'v4_candidate_type': candidate_type,
        'conditions': [deepcopy(condition) for condition in conditions],
    }
    item['expression'] = ' and '.join(_candidate_expression(condition) for condition in item['conditions'])
    return item


def _control_candidate(best_context: JsonDict) -> JsonDict:
    return {
        'v4_candidate_type': 'v4_control_keep_best',
        'strategy_name': best_context.get('strategy_name'),
        'expression': best_context.get('expression'),
        'reference_adjusted_score': best_context.get('reference_adjusted_score'),
        'skip_backtest': True,
    }


def _is_trade_amount_relax(candidate: JsonDict, best_trade_amount: JsonDict) -> bool:
    lower = candidate.get('lower_bound')
    upper = candidate.get('upper_bound')
    best_lower = best_trade_amount.get('lower_bound')
    best_upper = best_trade_amount.get('upper_bound')
    if lower is None or upper is None or best_lower is None or best_upper is None:
        return False
    try:
        return float(lower) <= float(best_lower) and float(upper) >= float(best_upper)
    except (TypeError, ValueError):
        return False


def _dedupe_candidates(candidates: list[JsonDict]) -> list[JsonDict]:
    selected: list[JsonDict] = []
    seen: set[tuple[object, object, object]] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            str(item.get('v4_candidate_type') or ''),
            -_score_value(item, 'combined_score'),
            str(item.get('expression') or ''),
        ),
    ):
        key = (
            candidate.get('v4_candidate_type'),
            candidate.get('expression'),
            candidate_signature(candidate),
        )
        if key in seen:
            continue
        seen.add(key)
        selected.append(candidate)
    return selected


def build_v4_candidate_pool(
    analysis_candidates: list[JsonDict],
    *,
    best_context: JsonDict | None = None,
    primary_feature: str = 'B_시가총액',
    trade_amount_feature: str = 'B_당일거래대금',
    secondary_features: list[str] | None = None,
    min_estimated_retention: float | None = 0.4,
    retention_tolerance: float = 0.02,
) -> JsonDict:
    _ = min_estimated_retention
    _ = retention_tolerance
    if not best_context:
        return {
            'status': 'disabled',
            'mode': 'best_feature_mix_v4',
            'primary_feature': primary_feature,
            'trade_amount_feature': trade_amount_feature,
            'secondary_features': list(secondary_features or []),
            'control_candidate': None,
            'candidates': [],
            'candidate_count': 0,
            'type_counts': {},
            'reason': 'best_context is required',
        }

    best_primary, best_trade_amount = parse_best_expression_conditions(
        str(best_context.get('expression') or ''),
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
    )
    secondary_feature_set = set(secondary_features or []) - {primary_feature, trade_amount_feature}
    eligible_candidates = [deepcopy(candidate) for candidate in analysis_candidates]
    secondary_candidates = [
        candidate for candidate in eligible_candidates
        if candidate.get('feature') in secondary_feature_set
    ]
    trade_amount_candidates = [
        candidate for candidate in eligible_candidates
        if candidate.get('feature') == trade_amount_feature
        and candidate_signature(candidate) != candidate_signature(best_trade_amount)
    ]

    candidates: list[JsonDict] = []
    for secondary in secondary_candidates:
        candidates.append(_combo_candidate(
            [best_primary, best_trade_amount, secondary],
            candidate_type='v4_tighten_secondary',
            source_candidate=secondary,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
            secondary_feature=str(secondary.get('feature') or ''),
        ))
        candidates.append(_combo_candidate(
            [best_primary, secondary],
            candidate_type='v4_replace_secondary',
            source_candidate=secondary,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
            secondary_feature=str(secondary.get('feature') or ''),
        ))

    for trade_amount in trade_amount_candidates:
        candidate_type = (
            'v4_relax_trade_amount'
            if _is_trade_amount_relax(trade_amount, best_trade_amount)
            else 'v4_repair_trade_amount'
        )
        candidates.append(_combo_candidate(
            [best_primary, trade_amount],
            candidate_type=candidate_type,
            source_candidate=trade_amount,
            primary_feature=primary_feature,
            trade_amount_feature=trade_amount_feature,
        ))

    candidates = _dedupe_candidates(candidates)
    type_counts = Counter(str(item.get('v4_candidate_type')) for item in candidates)
    type_counts['v4_control_keep_best'] += 1
    return {
        'status': 'ok',
        'mode': 'best_feature_mix_v4',
        'primary_feature': primary_feature,
        'trade_amount_feature': trade_amount_feature,
        'secondary_features': list(secondary_features or []),
        'best_conditions': [best_primary, best_trade_amount],
        'control_candidate': _control_candidate(best_context),
        'candidates': candidates,
        'candidate_count': len(candidates),
        'type_counts': dict(type_counts),
    }


def _signature_hash(signature: ProxySignature) -> str:
    payload = json.dumps(sorted(signature), separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


def _evaluate_mask(frame: pd.DataFrame, expression: str) -> tuple[pd.Series, str | None]:
    try:
        mask = frame.eval(expression)
    except Exception as exc:
        return pd.Series(False, index=frame.index), f'{type(exc).__name__}: {exc}'
    if not pd.api.types.is_bool_dtype(mask):
        return pd.Series(False, index=frame.index), 'expression did not produce a boolean mask'
    return mask.fillna(False).astype(bool), None


def estimate_candidate_rowset_proxy(frame: pd.DataFrame, expression: str) -> JsonDict:
    baseline_trade_count = int(len(frame))
    if baseline_trade_count <= 0:
        signature: ProxySignature = frozenset()
        return {
            'baseline_trade_count': 0,
            'proxy_removed_count': 0,
            'proxy_kept_count': 0,
            'proxy_retention': 0.0,
            'proxy_signature': signature,
            'proxy_signature_hash': _signature_hash(signature),
            'evaluation_error': None,
        }

    mask, evaluation_error = _evaluate_mask(frame, expression)
    removed_indexes = set(int(index) for index in mask[mask].index)
    kept_signature = frozenset(
        int(index) for index in frame.index
        if int(index) not in removed_indexes
    )
    kept = len(kept_signature)
    return {
        'baseline_trade_count': baseline_trade_count,
        'proxy_removed_count': int(mask.sum()),
        'proxy_kept_count': kept,
        'proxy_retention': kept / baseline_trade_count,
        'proxy_signature': kept_signature,
        'proxy_signature_hash': _signature_hash(kept_signature),
        'evaluation_error': evaluation_error,
    }


def annotate_candidate_rowset_proxy(
    candidates: list[JsonDict],
    baseline_frame: pd.DataFrame,
    *,
    min_retention: float,
) -> list[JsonDict]:
    annotated: list[JsonDict] = []
    for candidate in candidates:
        item = dict(candidate)
        proxy = estimate_candidate_rowset_proxy(
            baseline_frame,
            str(item.get('expression') or ''),
        )
        proxy['proxy_filter_passed'] = (
            proxy['evaluation_error'] is None
            and float(proxy['proxy_retention']) >= float(min_retention)
        )
        item['rowset_proxy'] = proxy
        item['retention_estimate'] = {
            'estimated_retention': proxy['proxy_retention'],
            'evaluation_error': proxy['evaluation_error'],
        }
        item['retention_filter_passed'] = proxy['proxy_filter_passed']
        item['retention_fallback_used'] = False
        annotated.append(item)
    return annotated


def _quota_summary(
    selected: list[JsonDict],
    family_targets: dict[str, int],
) -> dict[str, JsonDict]:
    selected_counts = Counter(str(item.get('v4_candidate_type') or '') for item in selected)
    return {
        family: {
            'target': target,
            'selected': selected_counts.get(family, 0),
            'shortfall': max(target - selected_counts.get(family, 0), 0),
        }
        for family, target in family_targets.items()
    }


def _proxy_sort_key(candidate: JsonDict) -> tuple[float, float, int]:
    proxy = candidate.get('rowset_proxy') or {}
    proxy_retention = float(proxy.get('proxy_retention') or 0.0)
    target_distance = min(abs(proxy_retention - 0.80), abs(proxy_retention - 0.95))
    original_index = int(candidate.get('original_index') or 0)
    return (target_distance, -_score_value(candidate, 'combined_score'), original_index)


def select_rowset_diverse_candidates(
    candidates: list[JsonDict],
    *,
    candidate_count: int,
    min_retention: float,
    family_targets: dict[str, int] | None = None,
) -> tuple[list[JsonDict], JsonDict]:
    _ = min_retention
    requested_count = max(int(candidate_count), 0)
    targets = dict(DEFAULT_FAMILY_TARGETS if family_targets is None else family_targets)
    eligible = [
        dict(candidate) for candidate in candidates
        if (candidate.get('rowset_proxy') or {}).get('proxy_filter_passed') is True
        and not (candidate.get('rowset_proxy') or {}).get('evaluation_error')
    ]
    eligible.sort(key=_proxy_sort_key)

    selected: list[JsonDict] = []
    used_signatures: set[ProxySignature] = set()
    skipped_duplicate_proxy_count = 0

    def try_add(candidate: JsonDict) -> bool:
        nonlocal skipped_duplicate_proxy_count
        proxy = candidate.get('rowset_proxy') or {}
        signature = proxy.get('proxy_signature')
        if not isinstance(signature, frozenset):
            return False
        if signature in used_signatures:
            skipped_duplicate_proxy_count += 1
            return False
        selected.append(candidate)
        used_signatures.add(signature)
        return True

    for family, target in targets.items():
        family_selected = 0
        for candidate in eligible:
            if len(selected) >= requested_count or family_selected >= target:
                break
            if candidate in selected or candidate.get('v4_candidate_type') != family:
                continue
            if try_add(candidate):
                family_selected += 1

    for candidate in eligible:
        if len(selected) >= requested_count:
            break
        if candidate in selected:
            continue
        try_add(candidate)

    selected_proxy_groups = [
        (item.get('rowset_proxy') or {}).get('proxy_signature_hash')
        for item in selected
    ]
    summary: JsonDict = {
        'status': 'ok',
        'phase': 'rowset_diverse_candidates_selected',
        'pool_count': len(candidates),
        'passed_count': len(eligible),
        'fallback_count': 0,
        'selected_count': len(selected),
        'requested_count': requested_count,
        'min_estimated_retention': min_retention,
        'allow_retention_fallback': False,
        'proxy_group_count': len(used_signatures),
        'selected_proxy_groups': selected_proxy_groups,
        'skipped_duplicate_proxy_count': skipped_duplicate_proxy_count,
        'quota_summary': _quota_summary(selected, targets),
    }
    return selected, summary
```

- [ ] **Step 4: Run helper tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v4.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Run helper lint/type checks**

Run:

```powershell
python -m ruff check cli/research_iteration_v4.py tests/unit/test_research_iteration_v4.py
basedpyright cli\research_iteration_v4.py tests\unit\test_research_iteration_v4.py
```

Expected:

```text
All checks passed!
0 errors, 0 warnings, 0 notes
```

- [ ] **Step 6: Commit Task 1**

Run:

```powershell
git add cli/research_iteration_v4.py tests/unit/test_research_iteration_v4.py
git commit -m "Wide v1 v4 행집합 다양성 helper를 추가한다" -m "v4 후보 family metadata와 실행 전 row-set proxy selection helper를 추가했다.

Constraint: 실제 v4 backtest 실행 없이 baseline frame 기반 proxy만 계산함
Rejected: estimated_retention 단일 정렬 유지 | v3에서 tighten-only row-set 중복을 반복함
Confidence: high
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_iteration_v4.py -q
Tested: python -m ruff check cli/research_iteration_v4.py tests/unit/test_research_iteration_v4.py
Tested: basedpyright cli\\research_iteration_v4.py tests\\unit\\test_research_iteration_v4.py
Not-tested: 실제 v4 runtime"
```

---

## Task 2: Research Loop and CLI Wiring

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `cli/subcommands.py`
- Modify: `tests/unit/test_research_loop.py`
- Modify: `tests/unit/test_subcommands.py`
- Reuse: `cli/research_iteration_v4.py`

- [ ] **Step 1: Write failing loop and CLI tests**

Append these tests to `tests/unit/test_research_loop.py`:

```python
def test_validate_research_iteration_accepts_best_feature_mix_v4(tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text('x\n', encoding='utf-8')

    result = validate_research_iteration_config(
        ResearchLoopConfig(
            name='V4Valid',
            baseline_csv=str(baseline),
            run_candidates=True,
            iteration_v2_mode='best_feature_mix_v4',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
            iteration_v2_primary_feature='B_시가총액',
        )
    )

    assert result['status'] == 'ok'


def test_run_research_iteration_applies_v4_proxy_diverse_selection(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text(
        'B_시가총액,B_체결강도,B_당일거래대금,수익금,종목명,매수시간,매도시간,매수가,매도가\n'
        '100,10,2000,-1,A,20250101090000,20250101090100,100,99\n'
        '200,20,3000,1,B,20250101090200,20250101090300,100,101\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['0 <= 체결강도 < 25', '1000 <= 당일거래대금 < 5000'],
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
            name='V4Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v4',
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
    assert result['iteration_v4']['status'] == 'ok'
    assert result['retention_selection']['phase'] == 'rowset_diverse_candidates_selected'
    assert result['retention_selection']['proxy_group_count'] >= 1
    assert executed_specs
```

Add this regression near the existing v3 tests:

```python
def test_run_research_iteration_keeps_v3_retention_selection_path(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text(
        'B_시가총액,B_체결강도,B_당일거래대금,수익금,종목명,매수시간,매도시간,매수가,매도가\n'
        '100,10,2000,-1,A,20250101090000,20250101090100,100,99\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['0 <= 체결강도 < 25'],
            'selected_candidates': [{
                'feature': 'B_체결강도',
                'operator': 'between',
                'lower_bound': 0.0,
                'upper_bound': 25.0,
                'score': 8.0,
                'combined_score': 8.0,
                'expression': '0 <= 체결강도 < 25',
            }],
        },
    )
    calls = {'retention': 0, 'rowset': 0}
    monkeypatch.setattr(
        research_loop,
        'select_retention_aware_candidates',
        lambda candidates, candidate_count, allow_fallback, min_retention: (
            calls.__setitem__('retention', calls['retention'] + 1) or candidates[:candidate_count],
            {
                'status': 'ok',
                'phase': 'retention_candidates_selected',
                'pool_count': len(candidates),
                'passed_count': len(candidates),
                'fallback_count': 0,
                'selected_count': min(candidate_count, len(candidates)),
                'requested_count': candidate_count,
                'min_estimated_retention': min_retention,
                'allow_retention_fallback': allow_fallback,
            },
        ),
    )
    monkeypatch.setattr(
        research_loop,
        'select_rowset_diverse_candidates',
        lambda *args, **kwargs: calls.__setitem__('rowset', calls['rowset'] + 1) or ([], {}),
    )
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {'trade_count_retention': 0.9},
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': 1.0,
                'trade_count': 1.0,
                'trade_count_retention': 0.9,
                'date_concentration': 0.0,
                'symbol_concentration': 0.0,
            },
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V3StillRetention',
            baseline_csv=str(baseline),
            run_candidates=True,
            candidate_count=1,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert calls == {'retention': 1, 'rowset': 0}
```

Append these tests to `tests/unit/test_subcommands.py`:

```python
def test_discovery_research_parser_accepts_iteration_v2_mode_v4():
    parser = build_parser()

    args = parser.parse_args([
        'discovery',
        'research',
        '--name',
        'V4Run',
        '--input',
        'baseline.csv',
        '--sell',
        'SellStrategy',
        '--run-candidates',
        '--candidate-count',
        '10',
        '--iteration-v2-mode',
        'best_feature_mix_v4',
        '--iteration-v2-best-candidate',
        'WideV1IterationV2_20260423__cand005',
        '--iteration-v2-best-expression',
        '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
    ])

    assert args.iteration_v2_mode == 'best_feature_mix_v4'
    assert args.candidate_count == 10


def test_discovery_research_handler_passes_iteration_v2_mode_v4(monkeypatch):
    captured = {}

    class Controller:
        def research_strategy_once(self, payload):
            captured.update(payload)
            return {'status': 'ok'}

    monkeypatch.setattr('cli.subcommands.CliController', lambda: Controller())
    result = handle_cli([
        'discovery',
        'research',
        '--name',
        'V4Run',
        '--input',
        'baseline.csv',
        '--sell',
        'SellStrategy',
        '--run-candidates',
        '--candidate-count',
        '10',
        '--iteration-v2-mode',
        'best_feature_mix_v4',
        '--iteration-v2-best-candidate',
        'WideV1IterationV2_20260423__cand005',
        '--iteration-v2-best-expression',
        '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
    ])

    assert result == 0
    assert captured['iteration_v2_mode'] == 'best_feature_mix_v4'
    assert captured['candidate_count'] == 10
```

- [ ] **Step 2: Run focused tests to verify they fail**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_validate_research_iteration_accepts_best_feature_mix_v4 `
  tests/unit/test_research_loop.py::test_run_research_iteration_applies_v4_proxy_diverse_selection `
  tests/unit/test_research_loop.py::test_run_research_iteration_keeps_v3_retention_selection_path `
  tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_mode_v4 `
  tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_v2_mode_v4 `
  -q
```

Expected:

```text
Failures mention invalid_iteration_v2_mode or invalid argparse choice for best_feature_mix_v4.
```

- [ ] **Step 3: Wire v4 helper into `cli/research_loop.py`**

Modify imports near the existing v3 import:

```python
from cli.research_iteration_v4 import (
    annotate_candidate_rowset_proxy,
    build_v4_candidate_pool,
    select_rowset_diverse_candidates,
)
```

Modify validation:

```python
allowed_iteration_modes = {'best_feature_mix', 'best_feature_mix_v3', 'best_feature_mix_v4'}
if config.run_candidates and config.iteration_v2_mode and config.iteration_v2_mode not in allowed_iteration_modes:
    return _error(
        'invalid_iteration_v2_mode',
        'iteration_v2_mode must be empty, best_feature_mix, best_feature_mix_v3, or best_feature_mix_v4',
    )
```

Modify the malformed best expression validation condition:

```python
if config.run_candidates and config.iteration_v2_mode in {'best_feature_mix_v3', 'best_feature_mix_v4'}:
    try:
        parse_best_expression_conditions(
            config.iteration_v2_best_expression,
            primary_feature=config.iteration_v2_primary_feature,
            trade_amount_feature='B_당일거래대금',
        )
    except ValueError as exc:
        return _error(
            'invalid_iteration_v2_best_expression',
            f'{config.iteration_v2_mode} iteration_v2_best_expression must contain exactly two parseable conditions: {exc}',
        )
```

Add `iteration_v4 = None` beside the existing variables:

```python
iteration_v2 = None
iteration_v3 = None
iteration_v4 = None
```

Add a v4 branch after the v3 branch:

```python
elif config.iteration_v2_mode == 'best_feature_mix_v4':
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
    expression_result = {
        **expression_result,
        'selected_candidates': expression_candidates,
        'expressions': [candidate['expression'] for candidate in expression_candidates],
        'candidate_count': len(expression_candidates),
        'iteration_v4': iteration_v4,
    }
    expressions = expression_result['expressions']
```

Modify the retention selection block:

```python
baseline_frame = _trade_frame_for_compare(baseline_csv)
if config.iteration_v2_mode == 'best_feature_mix_v4':
    annotated_candidates = annotate_candidate_rowset_proxy(
        expression_candidates,
        baseline_frame,
        min_retention=config.min_estimated_retention,
    )
    selected_candidates, retention_selection = select_rowset_diverse_candidates(
        annotated_candidates,
        candidate_count=config.candidate_count,
        min_retention=config.min_estimated_retention,
    )
else:
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
```

Ensure `_iteration_generation_metadata` includes v4:

```python
def _iteration_generation_metadata(iteration_v2, iteration_v3=None, iteration_v4=None) -> dict:
    result = {}
    if iteration_v2 is not None:
        result['iteration_v2'] = iteration_v2
    if iteration_v3 is not None:
        result['iteration_v3'] = iteration_v3
    if iteration_v4 is not None:
        result['iteration_v4'] = iteration_v4
    return result
```

Update every call to `_iteration_generation_metadata(iteration_v2, iteration_v3)` in `run_research_iteration` to pass:

```python
**_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4)
```

- [ ] **Step 4: Wire `best_feature_mix_v4` into `cli/subcommands.py`**

Change:

```python
disc_research.add_argument('--iteration-v2-mode', choices=['best_feature_mix', 'best_feature_mix_v3'], default='')
```

to:

```python
disc_research.add_argument(
    '--iteration-v2-mode',
    choices=['best_feature_mix', 'best_feature_mix_v3', 'best_feature_mix_v4'],
    default='',
)
```

- [ ] **Step 5: Run Task 2 focused tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_validate_research_iteration_accepts_best_feature_mix_v4 `
  tests/unit/test_research_loop.py::test_run_research_iteration_applies_v4_proxy_diverse_selection `
  tests/unit/test_research_loop.py::test_run_research_iteration_keeps_v3_retention_selection_path `
  tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_mode_v4 `
  tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_v2_mode_v4 `
  -q
```

Expected:

```text
5 passed
```

- [ ] **Step 6: Run broader loop/subcommand tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v3.py tests/unit/test_research_iteration_v4.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 7: Commit Task 2**

Run:

```powershell
git add cli/research_loop.py cli/subcommands.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py
git commit -m "Wide v1 v4 후보 선택 경로를 CLI 연구 루프에 연결한다" -m "best_feature_mix_v4 mode를 discovery research CLI와 research loop에 연결했다. v4 mode에서만 proxy row-set diversity selection을 사용하고 기존 v3 mode는 retention-aware selection 경로를 유지한다.

Constraint: 기존 iteration_v2_* CLI 옵션명을 재사용해 인터페이스 확산을 줄임
Rejected: 기존 retention selection 전역 변경 | v2/v3 회귀 위험이 큼
Confidence: high
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v3.py tests/unit/test_research_iteration_v4.py -q
Not-tested: 실제 v4 backtest"
```

---

## Task 3: Report Rendering for v4 Metadata

**Files:**
- Modify: `cli/research_report.py`
- Modify: `tests/unit/test_research_report.py`

- [ ] **Step 1: Write failing report test**

Append to `tests/unit/test_research_report.py`:

```python
def test_render_research_report_markdown_contains_iteration_v4_section():
    markdown = render_research_report_markdown({
        'status': 'ok',
        'name': 'WideV1IterationV4_20260424',
        'baseline_csv': 'cand005.csv',
        'iteration_v4': {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'primary_feature': 'B_시가총액',
            'trade_amount_feature': 'B_당일거래대금',
            'secondary_features': ['B_체결강도', 'B_등락율'],
            'candidate_count': 10,
            'type_counts': {
                'v4_tighten_secondary': 3,
                'v4_repair_trade_amount': 2,
                'v4_replace_secondary': 3,
                'v4_relax_trade_amount': 2,
                'v4_control_keep_best': 1,
            },
            'control_candidate': {
                'strategy_name': 'WideV1IterationV2_20260423__cand005',
                'expression': '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
                'reference_adjusted_score': 13497.662902097409,
                'skip_backtest': True,
            },
        },
        'retention_selection': {
            'phase': 'rowset_diverse_candidates_selected',
            'proxy_group_count': 4,
            'skipped_duplicate_proxy_count': 6,
            'quota_summary': {
                'v4_repair_trade_amount': {'target': 2, 'selected': 2, 'shortfall': 0},
                'v4_replace_secondary': {'target': 2, 'selected': 2, 'shortfall': 0},
            },
        },
    })

    assert '## Iteration Loop v4 Row-Set Diversity' in markdown
    assert '- mode: best_feature_mix_v4' in markdown
    assert 'v4_repair_trade_amount: 2' in markdown
    assert '- proxy_group_count: 4' in markdown
    assert '- skipped_duplicate_proxy_count: 6' in markdown
    assert 'quota v4_repair_trade_amount: target=2, selected=2, shortfall=0' in markdown
    assert 'control_strategy_name: WideV1IterationV2_20260423__cand005' in markdown
```

- [ ] **Step 2: Run report test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py::test_render_research_report_markdown_contains_iteration_v4_section -q
```

Expected:

```text
FAILED because v4 section is missing.
```

- [ ] **Step 3: Add v4 report section**

In `cli/research_report.py`, add this helper near the existing iteration v2/v3 rendering helpers:

```python
def _append_iteration_v4_section(lines: list[str], report: dict) -> None:
    iteration_v4 = report.get('iteration_v4') or {}
    if not iteration_v4 or iteration_v4.get('status') == 'disabled':
        return

    lines.extend(['', '## Iteration Loop v4 Row-Set Diversity'])
    for key in (
        'status',
        'mode',
        'primary_feature',
        'trade_amount_feature',
        'candidate_count',
    ):
        if key in iteration_v4:
            lines.append(f"- {key}: {iteration_v4.get(key)}")

    secondary_features = iteration_v4.get('secondary_features') or []
    if secondary_features:
        lines.append(f"- secondary_features: {', '.join(str(item) for item in secondary_features)}")

    type_counts = iteration_v4.get('type_counts') or {}
    if type_counts:
        lines.append("- type_counts:")
        for family, count in sorted(type_counts.items()):
            lines.append(f"  - {family}: {count}")

    control = iteration_v4.get('control_candidate') or {}
    if control:
        lines.append(f"- control_strategy_name: {control.get('strategy_name')}")
        lines.append(f"- control_expression: `{control.get('expression')}`")
        lines.append(f"- control_reference_adjusted_score: {control.get('reference_adjusted_score')}")
        lines.append(f"- control_skip_backtest: {control.get('skip_backtest')}")

    retention_selection = report.get('retention_selection') or {}
    for key in ('proxy_group_count', 'skipped_duplicate_proxy_count'):
        if key in retention_selection:
            lines.append(f"- {key}: {retention_selection.get(key)}")

    quota_summary = retention_selection.get('quota_summary') or {}
    if quota_summary:
        lines.append("- quota_summary:")
        for family, item in sorted(quota_summary.items()):
            item = item or {}
            lines.append(
                f"  - quota {family}: "
                f"target={item.get('target')}, "
                f"selected={item.get('selected')}, "
                f"shortfall={item.get('shortfall')}"
            )
```

Call it from `render_research_report_markdown()` after the existing v3 section call:

```python
_append_iteration_v4_section(lines, report)
```

- [ ] **Step 4: Run report tests**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py -q
```

Expected:

```text
All report tests pass.
```

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git add cli/research_report.py tests/unit/test_research_report.py
git commit -m "Wide v1 v4 행집합 다양성 리포트 섹션을 추가한다" -m "discovery research markdown report에 iteration_v4 proxy row-set diversity metadata를 출력하도록 보강했다.

Constraint: report rendering만 변경하고 후보 생성/선택 동작은 변경하지 않음
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_report.py -q"
```

---

## Task 4: v4 Actual Row-Set Analysis Script

**Files:**
- Create: `scripts/analyze_wide_v1_v4_rowset_diversity.py`
- Modify: `tests/unit/test_research_v3_tiebreak.py`
- Reuse: `cli/research_v3_tiebreak.py`

- [ ] **Step 1: Add failing script wrapper test**

Append to `tests/unit/test_research_v3_tiebreak.py`:

```python
def test_analyze_wide_v1_v4_rowset_diversity_requires_runtime_and_prints_summary(
    monkeypatch,
    capsys,
    tmp_path: Path,
):
    import runpy
    import sys

    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / 'scripts' / 'analyze_wide_v1_v4_rowset_diversity.py'
    runtime_path = tmp_path / 'runtime.json'
    runtime_root = tmp_path / 'runtime_root'
    output_path = tmp_path / 'v4_report.md'
    runtime_root.mkdir()
    captured: JsonDict = {}

    def fake_write_v3_tie_break_report(**kwargs: Any) -> JsonDict:
        captured.update(kwargs)
        Path(kwargs['output_path']).write_text('# generated\n', encoding='utf-8')
        return {
            'decision': HOLD_ROW_SET_EQUIVALENCE,
            'next_command': '$brainstorming next',
            'row_set_gate': {'status': 'all_identical', 'group_count': 1},
        }

    monkeypatch.setattr('cli.research_v3_tiebreak.write_v3_tie_break_report', fake_write_v3_tie_break_report)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            str(script_path),
            '--runtime-path',
            str(runtime_path),
            '--runtime-root',
            str(runtime_root),
            '--output',
            str(output_path),
            '--top-n',
            '5',
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(script_path), run_name='__main__')
    stdout = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert captured == {
        'runtime_path': runtime_path,
        'runtime_root': runtime_root,
        'output_path': output_path,
        'top_n': 5,
    }
    assert 'decision=HOLD_ROW_SET_EQUIVALENCE' in stdout
    assert 'row_set_identity_status=all_identical' in stdout
    assert 'group_count=1' in stdout
    assert f'wrote={output_path}' in stdout
```

- [ ] **Step 2: Run script test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_tiebreak.py::test_analyze_wide_v1_v4_rowset_diversity_requires_runtime_and_prints_summary -q
```

Expected:

```text
FAILED with FileNotFoundError for scripts/analyze_wide_v1_v4_rowset_diversity.py.
```

- [ ] **Step 3: Add v4 analysis script**

Create `scripts/analyze_wide_v1_v4_rowset_diversity.py`:

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

DEFAULT_OUTPUT = PROJECT_ROOT / 'docs' / 'research' / 'condition_research' / 'pilot_logs' / (
    '2026-04-24_wide_v1_v4_rowset_diversity.md'
)


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('--top-n must be a positive integer') from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError('--top-n must be a positive integer')
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Analyze Wide v1 v4 actual candidate row-set diversity from a runtime artifact.',
    )
    _ = parser.add_argument('--runtime-path', type=Path, required=True)
    _ = parser.add_argument('--runtime-root', type=Path, required=True)
    _ = parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    _ = parser.add_argument('--top-n', type=positive_int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    from cli.research_v3_tiebreak import write_v3_tie_break_report

    args = build_parser().parse_args(argv)
    runtime_path = cast(Path, args.runtime_path)
    runtime_root = cast(Path, args.runtime_root)
    output_path = cast(Path, args.output)
    top_n = cast(int, args.top_n)
    analysis = write_v3_tie_break_report(
        runtime_path=runtime_path,
        runtime_root=runtime_root,
        output_path=output_path,
        top_n=top_n,
    )
    row_set_gate = analysis.get('row_set_gate') or {}
    print(f"decision={analysis['decision']}")
    print(f"next_command={analysis['next_command']}")
    print(f"row_set_identity_status={row_set_gate.get('status')}")
    print(f"group_count={row_set_gate.get('group_count')}")
    print(f'wrote={output_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run script wrapper tests**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_tiebreak.py::test_analyze_wide_v1_v4_rowset_diversity_requires_runtime_and_prints_summary -q
python -m pytest tests/unit/test_research_v3_tiebreak.py -q
```

Expected:

```text
The focused test passes.
All v3 tiebreak tests pass.
```

- [ ] **Step 5: Commit Task 4**

Run:

```powershell
git add scripts/analyze_wide_v1_v4_rowset_diversity.py tests/unit/test_research_v3_tiebreak.py
git commit -m "Wide v1 v4 실제 행집합 검증 스크립트를 추가한다" -m "v4 runtime artifact가 생성된 뒤 actual candidate CSV row-set diversity를 분석할 수 있는 wrapper를 추가했다.

Constraint: 아직 v4 runtime artifact가 없으므로 기본 runtime path를 두지 않고 명시 입력만 허용함
Rejected: v3 artifact를 v4 기본값으로 재사용 | 잘못된 분석 대상으로 오해될 수 있음
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_v3_tiebreak.py -q
Not-tested: 실제 v4 runtime artifact 분석"
```

---

## Task 5: Final Verification and PR Report

**Files:**
- Create: `docs/pr/2026-04-24_wide_v1_v4_row_set_diversity_candidate_generation_pr.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_iteration_v4.py `
  tests/unit/test_research_loop.py `
  tests/unit/test_subcommands.py `
  tests/unit/test_research_report.py `
  tests/unit/test_research_v3_tiebreak.py `
  -q
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
All unit tests pass. Existing warning count may remain.
```

- [ ] **Step 3: Run lint and type diagnostics**

Run:

```powershell
python -m ruff check `
  cli/research_iteration_v4.py `
  cli/research_loop.py `
  cli/subcommands.py `
  cli/research_report.py `
  scripts/analyze_wide_v1_v4_rowset_diversity.py `
  tests/unit/test_research_iteration_v4.py `
  tests/unit/test_research_loop.py `
  tests/unit/test_subcommands.py `
  tests/unit/test_research_report.py `
  tests/unit/test_research_v3_tiebreak.py

basedpyright `
  cli\research_iteration_v4.py `
  scripts\analyze_wide_v1_v4_rowset_diversity.py `
  tests\unit\test_research_iteration_v4.py
```

Expected:

```text
Ruff reports All checks passed.
basedpyright reports 0 errors.
```

- [ ] **Step 4: Run sync and whitespace checks**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
git diff --check
```

Expected:

```text
verify_nonrelease_sync.py reports PASS.
git diff --check prints no errors.
```

- [ ] **Step 5: Confirm known v3 artifact remains unchanged**

Run:

```powershell
python scripts/analyze_wide_v1_v3_tie_break.py
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_tie_break_ranking.md -Pattern 'decision=|row_set_identity_status|group_count'
```

Expected:

```text
decision=HOLD_ROW_SET_EQUIVALENCE
row_set_identity_status=all_identical
group_count=1
```

- [ ] **Step 6: Add PR report**

Create `docs/pr/2026-04-24_wide_v1_v4_row_set_diversity_candidate_generation_pr.md`:

```markdown
# Wide v1 v4 row-set diversity 후보 생성 PR 보고서

## 1. 이번 PR의 목적

이번 PR은 v3 top 후보가 모두 같은 실행 row-set으로 수렴한 문제를 반복하지 않도록 `best_feature_mix_v4` 후보 생성과 proxy row-set diversity selection을 추가한다.

## 2. 전체 플로우와 현재 위치

```text
[v3 row-set tie 확인]
        |
        v
[이번 PR: v4 proxy row-set diversity 후보 생성]
        |
        v
[다음: v4 candidate_count=10 실행]
        |
        v
[v4 actual row-set diversity 분석]
        |
        v
[promote/WFO 여부 판단]
```

## 3. 변경 사항

```text
- cli/research_iteration_v4.py 추가
- best_feature_mix_v4 CLI mode 추가
- research_loop v4 proxy-diverse selection 연결
- markdown report v4 section 추가
- v4 actual row-set analysis script 추가
```

## 4. 검증 결과

```text
Record one line per verification command using the observed output from Task 5 Steps 1-5.
Do not mark a verification command as passing unless it was executed in the implementation session.
v3 tie-break regression=HOLD_ROW_SET_EQUIVALENCE 유지
```

## 5. 남은 리스크

```text
- 이번 PR은 v4 후보 생성/선택 구현이며 실제 v4 backtest 실행은 포함하지 않는다.
- proxy row-set diversity는 baseline CSV 기반 예상치이며 actual row-set diversity는 실행 후 별도 검증해야 한다.
- promote/WFO는 actual row-set diversity가 확인된 뒤에만 판단한다.
```

## 6. 다음 단계

```text
$writing-plans Wide v1 v4 candidate_count=10 실행 및 actual row-set diversity 분석 계획 작성
```
```

Before committing the PR report, scan the document and verify that the verification section contains only observed command summaries from this implementation session.

- [ ] **Step 7: Commit final docs**

Run:

```powershell
git add docs/pr/2026-04-24_wide_v1_v4_row_set_diversity_candidate_generation_pr.md
git commit -m "Wide v1 v4 행집합 다양성 후보 생성 PR 보고서를 추가한다" -m "best_feature_mix_v4 구현 결과와 검증 결과를 PR 보고서로 문서화했다.

Constraint: 실제 v4 candidate_count=10 runtime은 다음 계획으로 분리함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/ -q
Tested: python -m ruff check touched files
Tested: basedpyright touched files
Tested: python scripts/verify_nonrelease_sync.py
Tested: git diff --check
Not-tested: 실제 v4 runtime execution"
```

---

## Final Verification

- [ ] **Step 1: Check status**

Run:

```powershell
git status --short --branch --untracked-files=all
```

Expected:

```text
No tracked changes remain.
Pre-existing protected backtest/graph/*.png files may remain untracked.
```

- [ ] **Step 2: Read next command from PR report**

Run:

```powershell
Select-String -Path docs\pr\2026-04-24_wide_v1_v4_row_set_diversity_candidate_generation_pr.md -Pattern '\$writing-plans|다음 단계'
```

Expected next command:

```text
$writing-plans Wide v1 v4 candidate_count=10 실행 및 actual row-set diversity 분석 계획 작성
```

## Self-Review Checklist

Spec coverage:

```text
v4 candidate family metadata: Task 1
proxy row-set signature: Task 1
proxy row-set diversity selection: Task 1 and Task 2
CLI best_feature_mix_v4: Task 2
research loop metadata: Task 2
report v4 section: Task 3
actual row-set verification script: Task 4
PR documentation and next command: Task 5
no promote/WFO/strategy.db mutation: all tasks preserve this boundary
```

Placeholder scan:

```text
Committed plan sections are fully specified. The PR report task requires observed command summaries before commit.
```

Type consistency:

```text
Main helper module: cli.research_iteration_v4
Main mode: best_feature_mix_v4
Result metadata: iteration_v4
Selection phase: rowset_diverse_candidates_selected
Actual verification script: scripts/analyze_wide_v1_v4_rowset_diversity.py
Next branch: v4 candidate_count=10 execution and actual row-set diversity analysis
```
