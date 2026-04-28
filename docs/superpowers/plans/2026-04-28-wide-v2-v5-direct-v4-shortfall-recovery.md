# Wide v2 v5 Direct V4 Shortfall Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Wide v2 v5 supplement a short direct-v4 candidate pool so `candidate_count=10` can enter candidate backtests instead of stopping with only 4 selected candidates.

**Architecture:** Keep existing v4 candidates as first-class candidates. When `0 < direct_v4_count < requested candidate_count`, reuse the existing v5 recovery families to add candidates, dedupe with `direct_v4` priority, then let the existing retention and row-set gates choose the execution pool.

**Tech Stack:** Python 3.11, pytest, existing STOM CLI research modules, dict-based JSON metadata, PowerShell verification commands.

---

## Scope Check

This plan implements one focused recovery lane:

```text
v4 pool count is greater than zero but less than requested candidate_count
-> keep direct_v4 candidates
-> generate v5 recovery candidates
-> combine and dedupe with direct_v4 priority
-> feed combined pool into existing retention and row-set selection
```

Included:

- v5 recovery helper behavior.
- direct-v4-first dedupe behavior.
- recovery metadata for `direct_v4_shortfall`.
- research-loop integration coverage.
- `candidate_count=10`, `max_rounds=1` rerun after tests pass.

Excluded:

- No Wide v6/v7.
- No WFO/OOS execution in this plan.
- No dynamic lowering of `candidate_count`.
- No ranking/scoring redesign.
- No broad `cli/` refactor.
- No PR creation or merge until implementation and runtime evidence pass.

Protected paths:

- Do not stage `utility/strategy.db`.
- Do not stage `backtest/graph/`.
- Do not stage `backtest/temp/`.
- Do not stage `backtest/csv/`.
- Use explicit `git add` paths only.

Remaining MVP flow:

```text
1. Implement direct_v4 shortfall recovery.
2. Run targeted and full unit tests.
3. Re-run candidate_count=10 max_rounds=1.
4. If final_best_candidate exists, plan WFO/OOS validation.
5. If recovery still cannot produce enough candidates, design recovery-family expansion.
6. Create Korean PR report and merge only after implementation plus runtime evidence are healthy.
```

## File Structure

- Modify: `tests/unit/test_research_iteration_v5_recovery.py`
  - Adjust the existing direct-v4 passthrough test.
  - Add direct-v4 shortfall supplement coverage.
  - Add direct-v4-first dedupe coverage.
- Modify: `cli/research_iteration_v5_recovery.py`
  - Extract recovery-family construction.
  - Add source priority for dedupe.
  - Change direct-v4 early return into a sufficient-pool check.
  - Add `requested_candidate_count` and `recovery_needed_count` metadata.
- Modify: `tests/unit/test_research_loop.py`
  - Add integration coverage proving a short direct-v4 pool triggers recovery and flows into candidate specs.
- Modify: `cli/research_loop.py`
  - Preserve `requested_candidate_count` and `recovery_needed_count` in `iteration_v5['recovery']`.
  - Preserve `recovery_needed_count` in top-level shortfall metadata.
- Create after runtime verification: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_review.md`
  - Korean evidence report for the implementation and rerun.

---

### Task 1: Recovery Helper Tests

**Files:**
- Modify: `tests/unit/test_research_iteration_v5_recovery.py`

- [ ] **Step 1: Update direct-v4 passthrough test**

Replace `test_v5_recovery_keeps_existing_v4_candidates_without_recovery()` with:

```python
def test_v5_recovery_keeps_existing_v4_candidates_without_recovery():
    existing = [{
        'expression': '66.999 <= PRIMARY < 2_580 and TRADE > 5',
        'v4_candidate_type': 'v4_repair_trade_amount',
        'v5_candidate_source': 'direct_v4',
    }]

    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[],
        existing_v4_result={'candidates': existing, 'candidate_count': 1},
        best_context=BEST_CONTEXT,
        primary_feature='B_PRIMARY',
        trade_amount_feature='B_TRADE',
        secondary_features=[],
        candidate_count=1,
    )

    assert result['recovery_attempted'] is False
    assert result['recovery_reason'] == 'direct_v4_available'
    assert result['initial_v4_candidate_count'] == 1
    assert result['requested_candidate_count'] == 1
    assert result['recovery_needed_count'] == 0
    assert result['candidates'] == existing
    assert result['recovery_family_counts'] == {'direct_v4': 1}
```

- [ ] **Step 2: Add direct-v4 shortfall test**

Add this test after the passthrough test:

```python
def test_v5_recovery_supplements_direct_v4_shortfall():
    existing = [{
        'expression': '66.999 <= PRIMARY < 2_580 and TRADE > 5',
        'v4_candidate_type': 'v4_repair_trade_amount',
        'v5_candidate_source': 'direct_v4',
        'score': 20.0,
        'combined_score': 20.0,
        'conditions': [
            {'feature': 'B_PRIMARY', 'operator': 'between', 'lower_bound': 66.999, 'upper_bound': 2580.0, 'threshold': None},
            {'feature': 'B_TRADE', 'operator': '>', 'lower_bound': None, 'upper_bound': None, 'threshold': 5.0},
        ],
    }]

    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[
            _candidate('B_TRADE', operator='>', lower=None, upper=None, threshold=5.2, score=4.0, original_index=1),
            _candidate('B_STRENGTH', lower=70.0, upper=90.0, score=3.0, original_index=2),
            _candidate('B_PRICE', lower=8000.0, upper=12000.0, score=2.0, original_index=3),
        ],
        existing_v4_result={'candidates': existing, 'candidate_count': 1},
        best_context=BEST_CONTEXT,
        primary_feature='B_PRIMARY',
        trade_amount_feature='B_TRADE',
        secondary_features=[],
        candidate_count=3,
    )

    sources = [candidate['v5_candidate_source'] for candidate in result['candidates']]

    assert result['recovery_attempted'] is True
    assert result['recovery_reason'] == 'direct_v4_shortfall'
    assert result['initial_v4_candidate_count'] == 1
    assert result['requested_candidate_count'] == 3
    assert result['recovery_needed_count'] == 2
    assert result['recovery_family_counts']['direct_v4'] == 1
    assert result['final_candidate_pool_count'] >= 3
    assert result['candidate_count'] == len(result['candidates'])
    assert sources[0] == 'direct_v4'
    assert 'recovered_trade_feature' in sources
    assert 'auto_secondary_feature' in sources
```

- [ ] **Step 3: Add direct-v4 dedupe priority test**

Add this test after the shortfall test:

```python
def test_v5_recovery_dedupe_prefers_direct_v4_when_recovery_duplicates_it():
    direct = {
        'expression': '66.999 <= PRIMARY < 2_580 and TRADE > 5.2',
        'v4_candidate_type': 'v4_repair_trade_amount',
        'v5_candidate_source': 'direct_v4',
        'score': 1.0,
        'combined_score': 1.0,
        'conditions': [
            {'feature': 'B_PRIMARY', 'operator': 'between', 'lower_bound': 66.999, 'upper_bound': 2580.0, 'threshold': None},
            {'feature': 'B_TRADE', 'operator': '>', 'lower_bound': None, 'upper_bound': None, 'threshold': 5.2},
        ],
    }

    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[
            _candidate('B_TRADE', operator='>', lower=None, upper=None, threshold=5.2, score=10.0, original_index=1),
        ],
        existing_v4_result={'candidates': [direct], 'candidate_count': 1},
        best_context=BEST_CONTEXT,
        primary_feature='B_PRIMARY',
        trade_amount_feature='B_TRADE',
        secondary_features=[],
        candidate_count=2,
    )

    matching = [
        candidate for candidate in result['candidates']
        if candidate['expression'] == '66.999 <= PRIMARY < 2_580 and TRADE > 5.2'
    ]

    assert len(matching) == 1
    assert matching[0]['v5_candidate_source'] == 'direct_v4'
    assert result['recovery_family_counts']['direct_v4'] == 1
```

- [ ] **Step 4: Run the new helper tests and confirm they fail before implementation**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_iteration_v5_recovery.py::test_v5_recovery_supplements_direct_v4_shortfall `
  tests/unit/test_research_iteration_v5_recovery.py::test_v5_recovery_dedupe_prefers_direct_v4_when_recovery_duplicates_it `
  -q
```

Expected before implementation:

```text
FAILED ... assert False is True
```

---

### Task 2: Recovery Helper Implementation

**Files:**
- Modify: `cli/research_iteration_v5_recovery.py`

- [ ] **Step 1: Add source priority helper**

Add this helper above `_dedupe_candidates()`:

```python
def _source_priority(candidate: JsonDict) -> int:
    source = str(candidate.get('v5_candidate_source') or '')
    priorities = {
        'direct_v4': 0,
        'recovered_trade_feature': 1,
        'auto_secondary_feature': 2,
        'safe_recommended_fallback': 3,
    }
    return priorities.get(source, 9)
```

- [ ] **Step 2: Replace `_dedupe_candidates()`**

Replace the whole `_dedupe_candidates()` function with:

```python
def _dedupe_candidates(candidates: list[JsonDict]) -> list[JsonDict]:
    deduped: list[JsonDict] = []
    seen: set[tuple[object, object]] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            _source_priority(item),
            -_score_value(item, 'combined_score'),
            -_score_value(item, 'score'),
            str(item.get('expression') or ''),
        ),
    ):
        key = (
            candidate.get('expression'),
            candidate_signature(candidate),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped
```

- [ ] **Step 3: Add `_build_recovery_candidates()`**

Add this helper below `_family_counts()`:

```python
def _build_recovery_candidates(
    *,
    full_recommended_candidates: list[JsonDict],
    best_context: JsonDict,
    primary_feature: str,
    trade_amount_feature: str,
    secondary_features: list[str] | None,
    candidate_count: int,
) -> list[JsonDict]:
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

    return _dedupe_candidates(candidates)
```

- [ ] **Step 4: Replace `build_v5_recovery_candidate_pool()`**

Replace the whole `build_v5_recovery_candidate_pool()` function with:

```python
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
    for candidate in existing_candidates:
        candidate.setdefault('v5_candidate_source', 'direct_v4')

    requested_count = max(int(candidate_count), 0)
    existing_count = len(existing_candidates)
    initial_v4_candidate_count = int(existing_v4_result.get('candidate_count') or existing_count)

    if existing_count and (requested_count <= 0 or existing_count >= requested_count):
        return {
            'status': 'ok',
            'mode': 'best_feature_mix_v5_recovery',
            'recovery_attempted': False,
            'recovery_reason': 'direct_v4_available',
            'initial_v4_candidate_count': initial_v4_candidate_count,
            'requested_candidate_count': requested_count,
            'recovery_needed_count': 0,
            'candidates': existing_candidates,
            'candidate_count': existing_count,
            'recovery_family_counts': {'direct_v4': existing_count},
            'final_candidate_pool_count': existing_count,
        }

    recovery_candidates = _build_recovery_candidates(
        full_recommended_candidates=full_recommended_candidates,
        best_context=best_context,
        primary_feature=primary_feature,
        trade_amount_feature=trade_amount_feature,
        secondary_features=secondary_features,
        candidate_count=max(requested_count, 1),
    )

    if existing_count:
        candidates = _dedupe_candidates(existing_candidates + recovery_candidates)
        return {
            'status': 'ok',
            'mode': 'best_feature_mix_v5_recovery',
            'recovery_attempted': True,
            'recovery_reason': 'direct_v4_shortfall',
            'initial_v4_candidate_count': initial_v4_candidate_count,
            'requested_candidate_count': requested_count,
            'recovery_needed_count': max(requested_count - existing_count, 0),
            'candidates': candidates,
            'candidate_count': len(candidates),
            'recovery_family_counts': _family_counts(candidates),
            'final_candidate_pool_count': len(candidates),
        }

    candidates = recovery_candidates
    return {
        'status': 'ok',
        'mode': 'best_feature_mix_v5_recovery',
        'recovery_attempted': True,
        'recovery_reason': 'v4_candidate_pool_empty',
        'initial_v4_candidate_count': initial_v4_candidate_count,
        'requested_candidate_count': requested_count,
        'recovery_needed_count': requested_count,
        'candidates': candidates,
        'candidate_count': len(candidates),
        'recovery_family_counts': _family_counts(candidates),
        'final_candidate_pool_count': len(candidates),
    }
```

- [ ] **Step 5: Run helper tests**

Run:

```powershell
python -m pytest tests/unit/test_research_iteration_v5_recovery.py -q
```

Expected:

```text
all tests in test_research_iteration_v5_recovery.py pass
```

- [ ] **Step 6: Commit helper implementation**

Run:

```powershell
git status --short
git add cli/research_iteration_v5_recovery.py tests/unit/test_research_iteration_v5_recovery.py
git commit -m "Wide v2 direct_v4 부족 후보를 복구한다" -m "v5 후보 풀이 direct_v4 후보를 일부 만들었지만 요청 수를 채우지 못하면 기존 후보를 보존하고 recovery 후보로 부족분을 보강한다. direct_v4 후보가 중복 제거에서 우선되도록 source priority를 명시했다." -m "Constraint: candidate_count=10 검증은 후보 수를 낮추지 않고 통과해야 한다`nRejected: direct_v4 존재 시 즉시 반환 유지 | 4개 후보 shortfall을 반복한다`nRejected: source를 dedupe key에 유지 | 같은 조건식이 family만 다르게 중복 실행될 수 있다`nConfidence: high`nScope-risk: narrow`nDirective: direct_v4_shortfall metadata 없이 같은 문제를 성공으로 간주하지 말 것`nTested: python -m pytest tests/unit/test_research_iteration_v5_recovery.py -q`nNot-tested: full optimizer runtime rerun은 loop metadata 테스트 후 실행"
```

Expected:

```text
commit created
```

---

### Task 3: Research Loop Metadata and Integration

**Files:**
- Modify: `tests/unit/test_research_loop.py`
- Modify: `cli/research_loop.py`

- [ ] **Step 1: Add direct-v4 shortfall integration test**

Add this test after `test_run_research_iteration_uses_v5_recovery_when_v4_pool_is_empty()`:

```python
def test_run_research_iteration_uses_v5_recovery_when_direct_v4_pool_is_short(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'B_PRIMARY': 50, 'B_TRADE': 4.0, 'B_STRENGTH': 80, INSTRUMENT_COLUMNS[1]: 'A', REQUIRED_KEY_COLUMNS[0]: 1, OPTIONAL_KEY_COLUMNS[0]: 100},
        {'B_PRIMARY': 60, 'B_TRADE': 5.0, 'B_STRENGTH': 85, INSTRUMENT_COLUMNS[1]: 'B', REQUIRED_KEY_COLUMNS[0]: 2, OPTIONAL_KEY_COLUMNS[0]: 200},
    ]).to_csv(baseline, index=False, encoding='utf-8')

    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {
        'status': 'ok',
        'recommended_candidates': [
            {'feature': 'B_TRADE', 'operator': '>', 'threshold': 5.2, 'score': 5.0, 'combined_score': 5.0, 'original_index': 1},
            {'feature': 'B_STRENGTH', 'operator': 'between', 'lower_bound': 70.0, 'upper_bound': 90.0, 'score': 4.0, 'combined_score': 4.0, 'original_index': 2},
        ],
    })
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['TRADE > 5.2', '70 <= STRENGTH < 90'],
            'candidate_count': 2,
            'selected_candidates': [
                {'feature': 'B_TRADE', 'operator': '>', 'threshold': 5.2, 'score': 5.0, 'combined_score': 5.0},
                {'feature': 'B_STRENGTH', 'operator': 'between', 'lower_bound': 70.0, 'upper_bound': 90.0, 'score': 4.0, 'combined_score': 4.0},
            ],
        },
    )
    monkeypatch.setattr(
        research_loop,
        'build_v4_candidate_pool',
        lambda *args, **kwargs: {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'candidates': [{
                'expression': '66.999 <= PRIMARY < 2_580 and TRADE > 5',
                'v4_candidate_type': 'v4_repair_trade_amount',
                'v5_candidate_source': 'direct_v4',
                'score': 10.0,
                'combined_score': 10.0,
                'conditions': [
                    {'feature': 'B_PRIMARY', 'operator': 'between', 'lower_bound': 66.999, 'upper_bound': 2580.0, 'threshold': None},
                    {'feature': 'B_TRADE', 'operator': '>', 'lower_bound': None, 'upper_bound': None, 'threshold': 5.0},
                ],
            }],
            'candidate_count': 1,
            'type_counts': {'v4_repair_trade_amount': 1},
        },
    )
    monkeypatch.setattr(
        research_loop,
        'annotate_candidate_rowset_proxy',
        lambda candidates, baseline_frame, min_retention: [
            dict(candidate, retention_filter_passed=True)
            for candidate in candidates
        ],
    )
    monkeypatch.setattr(
        research_loop,
        'select_rowset_diverse_candidates',
        lambda candidates, *, candidate_count, min_retention: (
            [dict(candidate) for candidate in candidates[:candidate_count]],
            {
                'status': 'ok',
                'phase': 'rowset_diverse_candidates_selected',
                'requested_count': candidate_count,
                'selected_count': min(candidate_count, len(candidates)),
                'eligible_count': len(candidates),
            },
        ),
    )

    executed_specs = []

    def fake_execute_candidate_spec(config, spec, controller, baseline_csv):
        executed_specs.append(spec)
        return {
            'status': 'ok',
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {
                'trade_count_retention': 0.8,
                'candidate_summary': {
                    'trade_count': 10,
                    'date_concentration': 0.0,
                    'symbol_concentration': 0.0,
                },
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': float(10 - spec['index'])},
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute_candidate_spec)
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
            name='V5DirectShortfallRecovery',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1Final_B_20260425',
            iteration_v2_best_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
        ),
        controller=object(),
    )

    sources = [spec['source_candidate']['v5_candidate_source'] for spec in result['candidate_specs']]

    assert result['status'] == 'ok'
    assert len(executed_specs) == 2
    assert result['iteration_v5']['recovery']['recovery_attempted'] is True
    assert result['iteration_v5']['recovery']['recovery_reason'] == 'direct_v4_shortfall'
    assert result['iteration_v5']['recovery']['recovery_family_counts']['direct_v4'] == 1
    assert result['iteration_v5']['recovery']['requested_candidate_count'] == 2
    assert result['iteration_v5']['recovery']['recovery_needed_count'] == 1
    assert result['iteration_v5']['initial_v4_candidate_count'] == 1
    assert result['initial_v4_candidate_count'] == 1
    assert result['recovery_attempted'] is True
    assert result['final_candidate_pool_count'] >= 2
    assert sources[0] == 'direct_v4'
    assert any(source != 'direct_v4' for source in sources)
```

- [ ] **Step 2: Extend loop recovery metadata**

In `cli/research_loop.py`, extend the recovery dict near the `build_v5_recovery_candidate_pool()` call:

```python
'recovery': {
    'recovery_attempted': recovery_result.get('recovery_attempted'),
    'recovery_reason': recovery_result.get('recovery_reason'),
    'recovery_family_counts': recovery_result.get('recovery_family_counts') or {},
    'final_candidate_pool_count': recovery_result.get('final_candidate_pool_count'),
    'requested_candidate_count': recovery_result.get('requested_candidate_count'),
    'recovery_needed_count': recovery_result.get('recovery_needed_count'),
},
```

In `_v5_candidate_pool_metadata()`, add `recovery_needed_count` to the returned dict:

```python
'recovery_needed_count': recovery.get('recovery_needed_count'),
```

Place it after `final_candidate_pool_count`.

- [ ] **Step 3: Run v5 loop tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_run_research_iteration_v5_executes_oversampled_pool_and_selects_actual_rowsets `
  tests/unit/test_research_loop.py::test_run_research_iteration_uses_v5_recovery_when_v4_pool_is_empty `
  tests/unit/test_research_loop.py::test_run_research_iteration_reports_v5_recovery_metadata_on_shortfall `
  tests/unit/test_research_loop.py::test_run_research_iteration_uses_v5_recovery_when_direct_v4_pool_is_short `
  -q
```

Expected:

```text
4 passed
```

- [ ] **Step 4: Commit loop integration**

Run:

```powershell
git status --short
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "Wide v2 direct_v4 복구 경로를 루프에서 검증한다" -m "direct_v4 후보가 요청 수보다 부족할 때 v5 recovery가 실행되고 candidate specs로 direct 후보와 recovery 후보가 함께 전달되는지 검증했다. loop metadata가 direct_v4_shortfall 원인을 유지하도록 필요한 필드만 보강한다." -m "Constraint: optimizer full run 실패 원인을 loop result metadata로 추적할 수 있어야 한다`nRejected: report 계층 선수정 | 기존 report는 top-level recovery fields를 이미 출력한다`nConfidence: high`nScope-risk: narrow`nDirective: runtime rerun 전에 v5 loop targeted tests를 먼저 통과시킬 것`nTested: targeted v5 research_loop tests`nNot-tested: candidate_count=10 runtime rerun은 다음 task에서 실행"
```

Expected:

```text
commit created
```

---

### Task 4: Regression Verification

**Files:**
- Read only: `cli/research_iteration_v5_recovery.py`
- Read only: `cli/research_loop.py`
- Read only: `tests/unit/`

- [ ] **Step 1: Run focused regression tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_iteration_v5_recovery.py `
  tests/unit/test_research_loop.py `
  tests/unit/test_research_optimizer.py `
  tests/unit/test_research_optimizer_report.py `
  -q
```

Expected:

```text
all selected tests pass with zero failures
```

- [ ] **Step 2: Run full unit verification**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
all unit tests pass, one skipped is acceptable
```

- [ ] **Step 3: Run non-release sync verification**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
verification passes
```

- [ ] **Step 4: Run whitespace diff check**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
no output
```

---

### Task 5: Candidate Count 10 Runtime Rerun and Korean Review

**Files:**
- Generate, do not stage: `backtest/temp/wide_v2_v5_direct_v4_shortfall_recovery_20260428.json`
- Generate, do not stage: `backtest/temp/wide_v2_v5_direct_v4_shortfall_recovery_20260428_summary.json`
- Generate, do not stage: `backtest/temp/wide_v2_v5_direct_v4_shortfall_recovery_20260428_leaderboard.json`
- Generate, do not stage: `backtest/temp/wide_v2_v5_direct_v4_shortfall_recovery_20260428_console.txt`
- Generate, do not stage: `backtest/temp/wide_v2_v5_direct_v4_shortfall_recovery_20260428_run_meta.json`
- Create and commit: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_review.md`

- [ ] **Step 1: Prepare runtime paths**

Run:

```powershell
$env:PYTHONUTF8 = '1'
$RunId = 'wide_v2_v5_direct_v4_shortfall_recovery_20260428'
$RuntimePath = "backtest\temp\${RunId}.json"
$SummaryPath = "backtest\temp\${RunId}_summary.json"
$LeaderboardPath = "backtest\temp\${RunId}_leaderboard.json"
$ConsolePath = "backtest\temp\${RunId}_console.txt"
$MetaPath = "backtest\temp\${RunId}_run_meta.json"
$ReportPath = 'docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_summary.md'
$ReviewPath = 'docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_review.md'

New-Item -ItemType Directory -Force -Path 'backtest\temp' | Out-Null
New-Item -ItemType Directory -Force -Path 'docs\research\condition_research\pilot_logs' | Out-Null

foreach ($Path in @($RuntimePath, $SummaryPath, $LeaderboardPath, $ConsolePath, $MetaPath, $ReportPath, $ReviewPath)) {
  if (Test-Path -LiteralPath $Path) {
    Remove-Item -LiteralPath $Path -Force
  }
}
```

Expected:

```text
No PowerShell error.
```

- [ ] **Step 2: Re-run the previous failing full candidate-count condition**

Run:

```powershell
$RunStart = Get-Date
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2V5DirectV4ShortfallRecovery_20260428 `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --seed-candidate WideV1Final_B_20260425 `
  --seed-expression "66.999 <= 시가총액 < 2_580 and 등락율 > 4.83" `
  --iteration-v2-trade-amount-feature "B_등락율" `
  --start 20250101 `
  --end 20251231 `
  --candidate-count 10 `
  --max-rounds 1 `
  --candidate-timeout 900 `
  --runtime-output $RuntimePath `
  --leaderboard-output $LeaderboardPath `
  --summary-output $SummaryPath `
  --report-path $ReportPath *> $ConsolePath
$RunExit = $LASTEXITCODE
$RunEnd = Get-Date
$RunElapsed = $RunEnd - $RunStart
[PSCustomObject]@{
  run_id = 'WideV2V5DirectV4ShortfallRecovery_20260428'
  started_at = $RunStart.ToString('o')
  ended_at = $RunEnd.ToString('o')
  elapsed = $RunElapsed.ToString()
  exit_code = $RunExit
  runtime_path = $RuntimePath
  summary_path = $SummaryPath
  leaderboard_path = $LeaderboardPath
  console_path = $ConsolePath
  report_path = $ReportPath
  candidate_count = 10
  max_rounds = 1
} | ConvertTo-Json | Set-Content -Encoding UTF8 $MetaPath
$RunElapsed
$RunExit
```

Expected acceptable outcomes:

```text
Preferred: status=ok, leaderboard_count > 0, final_best_candidate exists
Acceptable recovery proof: recovery_attempted=True, recovery_reason=direct_v4_shortfall, final_candidate_pool_count > initial_v4_candidate_count
Rejected: recovery_attempted=False, recovery_reason=direct_v4_available, selected_candidate_count=4
```

- [ ] **Step 3: Generate the Korean review from actual JSON**

Run:

```powershell
$Summary = Get-Content -Raw $SummaryPath | ConvertFrom-Json
$Meta = Get-Content -Raw $MetaPath | ConvertFrom-Json
$FinalBest = 'none'
if ($Summary.final_best_candidate -and $Summary.final_best_candidate.strategy_name) {
  $FinalBest = $Summary.final_best_candidate.strategy_name
}
$WfoCandidate = 'none'
if ($Summary.wfo_candidate -and $Summary.wfo_candidate.strategy_name) {
  $WfoCandidate = $Summary.wfo_candidate.strategy_name
}
$Decision = if ($Summary.status -eq 'ok' -and $FinalBest -ne 'none') {
  'final_best_candidate가 존재하므로 다음 단계는 WFO/OOS 검증 실행 계획이다.'
} elseif ($Summary.recovery_attempted -eq $true -and $Summary.recovery_reason -eq 'direct_v4_shortfall') {
  'direct_v4_shortfall recovery는 실행되었다. 후보 수가 여전히 부족하면 다음 문제는 recovery family 확장 또는 retention gate 조정으로 분리한다.'
} else {
  'direct_v4_shortfall recovery가 실행되지 않았다. helper 조건 분기와 loop metadata 전파를 다시 점검해야 한다.'
}
$NextCommand = if ($Summary.status -eq 'ok' -and $FinalBest -ne 'none') {
  '$writing-plans Wide v2 WFO/OOS 검증 실행 계획 작성'
} elseif ($Summary.recovery_attempted -eq $true -and $Summary.recovery_reason -eq 'direct_v4_shortfall') {
  '$brainstorming Wide v2 v5 recovery family expansion 설계'
} else {
  '$brainstorming Wide v2 v5 direct_v4 shortfall recovery 재점검 설계'
}

@"
# Wide v2 v5 direct_v4 shortfall recovery 검증

## 실행 목적

직전 candidate_count=10 full run은 v4 후보가 4개 존재한다는 이유로 recovery가 생략되어 selected_candidate_count=4에서 중단되었다. 이번 실행은 direct_v4 후보가 요청 수보다 부족할 때 direct_v4_shortfall recovery가 실행되는지 검증한다.

## 실행 조건

- run_id: `WideV2V5DirectV4ShortfallRecovery_20260428`
- candidate_count: `10`
- max_rounds: `1`
- start/end: `20250101-20251231`
- seed_candidate: `WideV1Final_B_20260425`
- seed_expression: `66.999 <= 시가총액 < 2_580 and 등락율 > 4.83`
- trade_amount_feature: `B_등락율`
- elapsed: `$($Meta.elapsed)`
- exit_code: `$($Meta.exit_code)`

## 결과 요약

- status: `$($Summary.status)`
- stop_reason: `$($Summary.stop_reason)`
- failure_phase: `$($Summary.failure_phase)`
- requested_candidate_count: `$($Summary.requested_candidate_count)`
- selected_candidate_count: `$($Summary.selected_candidate_count)`
- leaderboard_count: `$($Summary.leaderboard_count)`
- final_best_candidate: `$FinalBest`
- wfo_candidate: `$WfoCandidate`

## recovery 상태

- initial_v4_candidate_count: `$($Summary.initial_v4_candidate_count)`
- recovery_attempted: `$($Summary.recovery_attempted)`
- recovery_reason: `$($Summary.recovery_reason)`
- final_candidate_pool_count: `$($Summary.final_candidate_pool_count)`
- eligible_count: `$($Summary.eligible_count)`
- execution_count: `$($Summary.execution_count)`
- planned_execution_count: `$($Summary.planned_execution_count)`

## 판단

$Decision

## 다음 단계

`$NextCommand`
"@ | Set-Content -Encoding UTF8 $ReviewPath
```

Expected:

```text
The review file exists and contains concrete values from the summary JSON.
```

- [ ] **Step 4: Stage and commit curated docs**

Run:

```powershell
git status --short
git add docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_review.md
if (Test-Path -LiteralPath $ReportPath) {
  git add docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_direct_v4_shortfall_recovery_summary.md
}
git commit -m "Wide v2 direct_v4 복구 검증 결과를 기록한다" -m "candidate_count=10 재실행 결과를 한국어 리뷰로 정리했다. direct_v4_shortfall recovery가 실제 full candidate-count 검증에서 작동했는지와 다음 MVP 분기를 기록한다." -m "Constraint: raw backtest artifacts are protected and must stay unstaged`nConfidence: medium`nScope-risk: narrow`nDirective: WFO/OOS 단계는 final_best_candidate가 존재할 때만 진행할 것`nTested: candidate_count=10 max_rounds=1 runtime rerun`nNot-tested: WFO/OOS validation"
```

Expected:

```text
commit created
```

---

## Final Verification Checklist

Before claiming implementation complete, verify:

```powershell
python -m pytest tests/unit/test_research_iteration_v5_recovery.py tests/unit/test_research_loop.py tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py -q
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol HEAD
git status --short --branch
```

Expected final status:

```text
tracked files clean
only protected runtime artifacts may remain untracked
```

## Handoff Command

Implement this plan with:

```text
$executing-plans docs/superpowers/plans/2026-04-28-wide-v2-v5-direct-v4-shortfall-recovery.md
```
