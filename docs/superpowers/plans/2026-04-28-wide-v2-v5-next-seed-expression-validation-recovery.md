# Wide v2 v5 Next Seed Expression Validation Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Wide v2 continue to the next round when the round best candidate is not a valid v5 seed but another ranked candidate is seed-compatible.

**Architecture:** Keep global best selection unchanged for WFO/OOS handoff, and add a separate next-seed selection path inside `cli.research_optimizer`. The optimizer will prefer the round best when it validates, otherwise it will scan ranked candidates for the first expression that matches the configured v5 `primary_feature + trade_amount_feature` shape and record the decision in JSON and Markdown reports.

**Tech Stack:** Python 3.11, pytest, existing STOM CLI optimizer modules, JSON-safe dict metadata, Markdown report rendering.

---

## Scope Check

This plan implements one focused subsystem: Wide v2 v5 next seed expression validation recovery. It does not add Wide v6/v7, does not change v5 candidate generation families, does not run WFO/OOS, and does not execute `candidate_count=10` full run until `candidate_count=2` smoke proves the round-two seed problem is fixed.

Current MVP position:

```text
v5 후보 풀 0개 문제
-> recovery 구현 완료
-> candidate_count=2 smoke 실행 완료
-> 후보 backtest 진입 성공
-> round002 seed 검증 실패 발견
-> next seed selection recovery 구현 필요
```

Remaining MVP flow after this implementation:

```text
1. candidate_count=2 smoke rerun
2. candidate_count=10 full run only if smoke no longer stops with invalid_seed_expression
3. WFO/OOS handoff plan for the winner
4. Korean PR report and merge decision after implementation verification
```

Do not stage these paths:

- `utility/strategy.db`
- `backtest/graph/`
- `backtest/temp/`
- `backtest/csv/`

Use explicit staging only.

## File Structure

- Modify: `cli/research_optimizer.py`
  - Adds next-seed selection helpers.
  - Separates global best from next-round seed.
  - Stores next-seed metadata in round states and top-level optimizer result.
- Modify: `tests/unit/test_research_optimizer.py`
  - Adds regression tests for round-best seed, compatible fallback seed, and no-compatible-seed failure.
- Modify: `cli/research_optimizer_report.py`
  - Adds a Markdown section for next-seed selection metadata.
- Modify: `tests/unit/test_research_optimizer_report.py`
  - Verifies next-seed metadata is visible and escaped.
- Create after smoke rerun if useful: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_next_seed_recovery_smoke_review.md`
  - Korean smoke review for the rerun. Commit only docs evidence; do not commit runtime artifacts.

---

### Task 1: Optimizer Next-Seed Selection

**Files:**
- Modify: `tests/unit/test_research_optimizer.py`
- Modify: `cli/research_optimizer.py`

- [ ] **Step 1: Add failing optimizer tests for seed-compatible selection**

In `tests/unit/test_research_optimizer.py`, add these helper and tests after `test_optimizer_prefers_no_improvement_stop_before_invalid_next_seed()`:

```python
def _ranked_candidate(name, expression, score, *, rank, selected=False):
    return {
        'index': rank,
        'strategy_name': name,
        'expression': expression,
        'status': 'ok',
        'selected_as_best': selected,
        'actual_rowset_selected': True,
        'rank': rank,
        'rank_score': {
            'promotion_passed': True,
            'promotion_score': score,
            'adjusted_score': score,
            'score_basis': 'reference',
            'trade_count': 100,
            'trade_count_retention': 0.8,
            'date_concentration': 0.1,
            'symbol_concentration': 0.1,
        },
    }


def test_optimizer_records_round_best_next_seed_when_seed_compatible():
    calls = []
    results = [
        _round_result('R1__cand001', '66.999 <= PRIMARY < 2_580 and TRADE > 4.90', 1.0),
        _round_result('R2__cand001', '66.999 <= PRIMARY < 2_580 and TRADE > 5.10', 2.0),
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2SeedRoundBest',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=2,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 2
    assert calls[1].iteration_v2_best_candidate == 'R1__cand001'
    assert calls[1].iteration_v2_best_expression == '66.999 <= PRIMARY < 2_580 and TRADE > 4.90'
    assert result['rounds'][0]['next_seed_selection_status'] == 'round_best'
    assert result['rounds'][0]['next_seed_strategy_name'] == 'R1__cand001'
    assert result['next_seed_selection_status'] == 'round_best'
    assert result['next_seed_strategy_name'] == 'R1__cand001'


def test_optimizer_falls_back_to_seed_compatible_candidate_without_changing_global_best():
    calls = []
    incompatible_best = _ranked_candidate(
        'R1__cand003',
        '66.999 <= PRIMARY < 2_580 and OTHER > 1.50',
        10.0,
        rank=1,
        selected=True,
    )
    compatible_seed = _ranked_candidate(
        'R1__cand001',
        '66.999 <= PRIMARY < 2_580 and TRADE > 4.90',
        8.0,
        rank=2,
    )
    results = [
        {
            'status': 'ok',
            'phase': 'candidates_evaluated',
            'best_candidate': incompatible_best,
            'candidates': [incompatible_best, compatible_seed],
        },
        _round_result('R2__cand001', '66.999 <= PRIMARY < 2_580 and TRADE > 5.10', 2.0),
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2SeedFallback',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=2,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 2
    assert calls[1].iteration_v2_best_candidate == 'R1__cand001'
    assert calls[1].iteration_v2_best_expression == '66.999 <= PRIMARY < 2_580 and TRADE > 4.90'
    assert result['rounds'][0]['next_seed_selection_status'] == 'compatible_fallback'
    assert result['rounds'][0]['next_seed_strategy_name'] == 'R1__cand001'
    assert result['rounds'][0]['rejected_round_best_seed_strategy_name'] == 'R1__cand003'
    assert result['rounds'][0]['rejected_round_best_seed_reason'] == 'invalid_seed_expression'
    assert result['final_best_candidate']['strategy_name'] == 'R1__cand003'
    assert result['wfo_candidate']['strategy_name'] == 'R1__cand003'
    assert result['next_seed_selection_status'] == 'compatible_fallback'
    assert result['next_seed_strategy_name'] == 'R1__cand001'


def test_optimizer_reports_not_found_when_no_seed_compatible_candidate_exists():
    calls = []
    incompatible_best = _ranked_candidate(
        'R1__cand003',
        '66.999 <= PRIMARY < 2_580 and OTHER > 1.50',
        10.0,
        rank=1,
        selected=True,
    )
    incompatible_second = _ranked_candidate(
        'R1__cand004',
        '66.999 <= PRIMARY < 2_580 and STRENGTH > 20',
        8.0,
        rank=2,
    )

    def fake_runner(config, controller):
        calls.append(config)
        return {
            'status': 'ok',
            'phase': 'candidates_evaluated',
            'best_candidate': incompatible_best,
            'candidates': [incompatible_best, incompatible_second],
        }

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2SeedNotFound',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=2,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 1
    assert result['status'] == 'error'
    assert result['stop_reason'] == 'invalid_seed_expression'
    assert result['completed_round_count'] == 1
    assert result['failed_round'] == 2
    assert result['failure_phase'] == 'invalid_seed_expression'
    assert result['failure_message'] == 'next seed expression is invalid'
    assert result['next_seed_selection_status'] == 'not_found'
    assert result['rejected_round_best_seed_strategy_name'] == 'R1__cand003'
    assert result['rejected_round_best_seed_expression'] == '66.999 <= PRIMARY < 2_580 and OTHER > 1.50'
    assert result['rounds'][0]['next_seed_selection_status'] == 'not_found'
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_optimizer.py::test_optimizer_records_round_best_next_seed_when_seed_compatible `
  tests/unit/test_research_optimizer.py::test_optimizer_falls_back_to_seed_compatible_candidate_without_changing_global_best `
  tests/unit/test_research_optimizer.py::test_optimizer_reports_not_found_when_no_seed_compatible_candidate_exists `
  -q
```

Expected:

```text
FAILED
```

At least one failure should show missing `next_seed_selection_status` metadata or the fallback test should stop with `invalid_seed_expression`.

- [ ] **Step 3: Add next-seed helper functions in `cli/research_optimizer.py`**

In `cli/research_optimizer.py`, replace the existing `_seed_from_previous` function with this block:

```python
def _candidate_seed_tuple(candidate: Any, fallback_candidate: str) -> tuple[str, str] | None:
    if not isinstance(candidate, dict):
        return None
    strategy_name = str(candidate.get('strategy_name') or fallback_candidate or '').strip()
    expression = str(candidate.get('expression') or '').strip()
    if not strategy_name or not expression:
        return None
    return strategy_name, expression


def _seed_candidate_rank_key(candidate: dict[str, Any]) -> tuple[int, int, int]:
    rank = candidate.get('rank')
    try:
        rank_value = int(rank)
    except (TypeError, ValueError):
        rank_value = 999999
    index = candidate.get('index')
    try:
        index_value = int(index)
    except (TypeError, ValueError):
        index_value = 999999
    selected_penalty = 0 if candidate.get('selected_as_best') is True else 1
    return rank_value, selected_penalty, index_value
```

Then add this function immediately after the `_seed_candidate_rank_key` function:

```python
def _seed_from_ranked_candidates(
    config: WideV2OptimizerConfig,
    round_result: dict[str, Any],
    fallback_candidate: str,
) -> dict[str, Any]:
    best_candidate = round_result.get('best_candidate')
    rejected_strategy_name = None
    rejected_expression = None
    rejected_reason = None
    best_seed = _candidate_seed_tuple(best_candidate, fallback_candidate)
    if best_seed is not None:
        if _validate_seed_expression(config, best_seed[1]):
            return json_safe_value({
                'strategy_name': best_seed[0],
                'expression': best_seed[1],
                'selection_status': 'round_best',
                'rejected_round_best_seed_strategy_name': None,
                'rejected_round_best_seed_expression': None,
                'rejected_round_best_seed_reason': None,
            })
        rejected_strategy_name = best_seed[0]
        rejected_expression = best_seed[1]
        rejected_reason = 'invalid_seed_expression'

    candidates = [
        candidate for candidate in round_result.get('candidates') or []
        if isinstance(candidate, dict)
    ]
    candidates.sort(key=_seed_candidate_rank_key)
    seen: set[tuple[str, str]] = set()
    if best_seed is not None:
        seen.add(best_seed)
    for candidate in candidates:
        seed = _candidate_seed_tuple(candidate, fallback_candidate)
        if seed is None or seed in seen:
            continue
        seen.add(seed)
        if _validate_seed_expression(config, seed[1]):
            return json_safe_value({
                'strategy_name': seed[0],
                'expression': seed[1],
                'selection_status': 'compatible_fallback',
                'rejected_round_best_seed_strategy_name': rejected_strategy_name,
                'rejected_round_best_seed_expression': rejected_expression,
                'rejected_round_best_seed_reason': rejected_reason,
            })

    return json_safe_value({
        'strategy_name': None,
        'expression': None,
        'selection_status': 'not_found',
        'rejected_round_best_seed_strategy_name': rejected_strategy_name,
        'rejected_round_best_seed_expression': rejected_expression,
        'rejected_round_best_seed_reason': rejected_reason,
    })
```

- [ ] **Step 4: Add metadata copy helpers in `cli/research_optimizer.py`**

Add these functions after the `_seed_from_ranked_candidates` function:

```python
def _next_seed_round_metadata(seed_selection: dict[str, Any]) -> dict[str, Any]:
    return {
        'next_seed_selection_status': seed_selection.get('selection_status'),
        'next_seed_strategy_name': seed_selection.get('strategy_name'),
        'next_seed_expression': seed_selection.get('expression'),
        'rejected_round_best_seed_strategy_name': seed_selection.get(
            'rejected_round_best_seed_strategy_name'
        ),
        'rejected_round_best_seed_expression': seed_selection.get(
            'rejected_round_best_seed_expression'
        ),
        'rejected_round_best_seed_reason': seed_selection.get(
            'rejected_round_best_seed_reason'
        ),
    }


def _next_seed_result_metadata(seed_selection: dict[str, Any] | None) -> dict[str, Any]:
    if not seed_selection:
        return {
            'next_seed_selection_status': None,
            'next_seed_strategy_name': None,
            'next_seed_expression': None,
            'rejected_round_best_seed_strategy_name': None,
            'rejected_round_best_seed_expression': None,
            'rejected_round_best_seed_reason': None,
        }
    return _next_seed_round_metadata(seed_selection)
```

- [ ] **Step 5: Wire fallback seed selection into `run_wide_v2_optimizer()`**

Inside `run_wide_v2_optimizer()`, after:

```python
    failure_metadata = _failure_metadata()
```

add:

```python
    last_next_seed_selection: dict[str, Any] | None = None
```

Then replace this block:

```python
            next_seed = _seed_from_previous(round_result, current_candidate)
            if next_seed is None or not _validate_seed_expression(config, next_seed[1]):
                status = 'error'
                stop_reason = 'invalid_seed_expression'
                failure_metadata = _failure_metadata(
                    failed_round=round_index + 1,
                    failure_phase='invalid_seed_expression',
                    failure_message='next seed expression is invalid',
                )
                break

            current_candidate, current_expression = next_seed
```

with:

```python
            seed_selection = _seed_from_ranked_candidates(
                config,
                round_result,
                current_candidate,
            )
            round_state.update(_next_seed_round_metadata(seed_selection))
            if rounds:
                rounds[-1] = json_safe_value(round_state)
            last_next_seed_selection = seed_selection
            if seed_selection.get('selection_status') == 'not_found':
                status = 'error'
                stop_reason = 'invalid_seed_expression'
                failure_metadata = {
                    **_failure_metadata(
                        failed_round=round_index + 1,
                        failure_phase='invalid_seed_expression',
                        failure_message='next seed expression is invalid',
                    ),
                    **_next_seed_round_metadata(seed_selection),
                }
                break

            current_candidate = str(seed_selection.get('strategy_name') or '')
            current_expression = str(seed_selection.get('expression') or '')
```

Finally, in the result payload, add the next seed metadata after `**failure_metadata`:

```python
        **_next_seed_result_metadata(last_next_seed_selection),
```

The surrounding result block should include:

```python
        'stop_reason': stop_reason,
        **failure_metadata,
        **_next_seed_result_metadata(last_next_seed_selection),
        'completed_round_count': completed_round_count,
```

- [ ] **Step 6: Run optimizer tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_optimizer.py::test_optimizer_records_round_best_next_seed_when_seed_compatible `
  tests/unit/test_research_optimizer.py::test_optimizer_falls_back_to_seed_compatible_candidate_without_changing_global_best `
  tests/unit/test_research_optimizer.py::test_optimizer_reports_not_found_when_no_seed_compatible_candidate_exists `
  tests/unit/test_research_optimizer.py::test_optimizer_prefers_no_improvement_stop_before_invalid_next_seed `
  tests/unit/test_research_optimizer.py::test_optimizer_stops_before_next_round_when_seed_expression_is_invalid `
  -q
```

Expected:

```text
5 passed
```

- [ ] **Step 7: Run full optimizer unit file**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py -q
```

Expected:

```text
all tests in tests/unit/test_research_optimizer.py pass
```

- [ ] **Step 8: Commit Task 1**

Run:

```powershell
git add cli\research_optimizer.py tests\unit\test_research_optimizer.py
git commit -m "Wide v2 다음 seed 선택 복구를 구현한다" -m @"
Wide v2 optimizer에서 global best 후보와 다음 round seed를 분리했다.

round best가 현재 v5 seed shape을 통과하면 그대로 사용하고, 통과하지 못하면 ranked candidates에서 seed-compatible 후보를 찾아 다음 round를 이어간다. global best와 WFO candidate는 여전히 점수 기준 후보를 유지한다.

Constraint: v5 반복 루프는 configured primary/trade feature 축을 유지해야 한다
Rejected: trade_amount_feature 자동 변경 | round마다 비교 축이 바뀌어 개선 판단이 불안정해진다
Confidence: high
Scope-risk: moderate
Directive: global_best_candidate와 next_round_seed를 같은 개념으로 합치지 말 것
Tested: python -m pytest tests/unit/test_research_optimizer.py -q
Not-tested: smoke rerun은 Task 3에서 실행한다
"@
```

---

### Task 2: Optimizer Report Next-Seed Visibility

**Files:**
- Modify: `tests/unit/test_research_optimizer_report.py`
- Modify: `cli/research_optimizer_report.py`

- [ ] **Step 1: Add failing report test**

In `tests/unit/test_research_optimizer_report.py`, add this test after `test_render_optimizer_summary_markdown_includes_v5_recovery_metadata()`:

```python
def test_render_optimizer_summary_markdown_includes_next_seed_selection_metadata():
    result = _result()
    result.update({
        'next_seed_selection_status': 'compatible_fallback',
        'next_seed_strategy_name': 'R1__cand001',
        'next_seed_expression': '66.999 <= PRIMARY < 2_580 and TRADE > 4.90',
        'rejected_round_best_seed_strategy_name': 'R1__cand003',
        'rejected_round_best_seed_expression': '66.999 <= PRIMARY < 2_580 and OTHER > 1.50',
        'rejected_round_best_seed_reason': 'invalid_seed_expression',
    })

    markdown = render_optimizer_summary_markdown(result)

    assert '## Next seed selection' in markdown
    assert '- next_seed_selection_status=compatible_fallback' in markdown
    assert '- next_seed_strategy_name=R1__cand001' in markdown
    assert '- next_seed_expression=66.999 <= PRIMARY < 2_580 and TRADE > 4.90' in markdown
    assert '- rejected_round_best_seed_strategy_name=R1__cand003' in markdown
    assert '- rejected_round_best_seed_reason=invalid_seed_expression' in markdown
```

- [ ] **Step 2: Add escaping coverage to the existing escape test**

In `test_render_optimizer_summary_markdown_escapes_pipes_and_flattens_newlines()`, add these mutations before rendering:

```python
    result['next_seed_strategy_name'] = 'Seed|Next\nTwo'
    result['next_seed_expression'] = 'Next|Expr\nTwo'
    result['rejected_round_best_seed_expression'] = 'Rejected|Expr\nTwo'
```

Then add these assertions:

```python
    assert 'Seed\\|Next Two' in markdown
    assert 'Next\\|Expr Two' in markdown
    assert 'Rejected\\|Expr Two' in markdown
```

- [ ] **Step 3: Run report tests to verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer_report.py::test_render_optimizer_summary_markdown_includes_next_seed_selection_metadata -q
```

Expected:

```text
FAILED
```

The failure should show `## Next seed selection` is missing.

- [ ] **Step 4: Add next seed report helper**

In `cli/research_optimizer_report.py`, add this function after the `_recovery_lines` function:

```python
def _next_seed_lines(result: dict[str, Any]) -> list[str]:
    return [
        '## Next seed selection',
        '',
        _bullet('next_seed_selection_status', result.get('next_seed_selection_status')),
        _bullet('next_seed_strategy_name', result.get('next_seed_strategy_name')),
        _bullet('next_seed_expression', result.get('next_seed_expression')),
        _bullet(
            'rejected_round_best_seed_strategy_name',
            result.get('rejected_round_best_seed_strategy_name'),
        ),
        _bullet(
            'rejected_round_best_seed_expression',
            result.get('rejected_round_best_seed_expression'),
        ),
        _bullet(
            'rejected_round_best_seed_reason',
            result.get('rejected_round_best_seed_reason'),
        ),
        '',
    ]
```

- [ ] **Step 5: Render next seed section before Stop reason**

In the `render_optimizer_summary_markdown` function, after:

```python
        *_recovery_lines(result),
```

add:

```python
        *_next_seed_lines(result),
```

- [ ] **Step 6: Run report tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer_report.py -q
```

Expected:

```text
all tests in tests/unit/test_research_optimizer_report.py pass
```

- [ ] **Step 7: Commit Task 2**

Run:

```powershell
git add cli\research_optimizer_report.py tests\unit\test_research_optimizer_report.py
git commit -m "Wide v2 보고서에 다음 seed 선택을 표시한다" -m @"
optimizer Markdown report에 next seed selection 섹션을 추가했다.

round best가 다음 seed로 사용되지 않은 경우에도 어떤 후보가 다음 round seed가 되었는지, 왜 round best가 거부되었는지 report에서 바로 확인할 수 있다.

Constraint: smoke와 full run 분석은 summary JSON과 Markdown만으로 추적 가능해야 한다
Rejected: round JSON 수동 확인만 의존 | 반복 실행 시 원인 추적 비용이 커진다
Confidence: high
Scope-risk: narrow
Directive: next_seed metadata key는 optimizer summary JSON과 Markdown report에서 동일하게 유지할 것
Tested: python -m pytest tests/unit/test_research_optimizer_report.py -q
Not-tested: smoke report는 Task 3에서 생성한다
"@
```

---

### Task 3: Focused Verification and Smoke Rerun

**Files:**
- Create if smoke runs: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_next_seed_recovery_smoke_review.md`
- Read generated, do not stage: `backtest/temp/wide_v2_v5_next_seed_recovery_smoke_20260428*.json`
- Read generated, do not stage: `backtest/csv/*`

- [ ] **Step 1: Run focused unit tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_optimizer.py `
  tests/unit/test_research_optimizer_report.py `
  tests/unit/test_subcommands.py `
  -q
```

Expected:

```text
all selected tests pass
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

- [ ] **Step 4: Run candidate_count=2 next-seed recovery smoke**

Run:

```powershell
$env:PYTHONUTF8='1'
$smokeStart = Get-Date
$consolePath = 'backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_console.txt'
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2V5NextSeedRecoverySmoke_20260428 `
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
  --runtime-output backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428.json `
  --leaderboard-output backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_leaderboard.json `
  --summary-output backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_summary.json `
  --report-path docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_next_seed_recovery_smoke_summary.md *> $consolePath
$smokeExit = $LASTEXITCODE
$smokeEnd = Get-Date
$smokeElapsed = $smokeEnd - $smokeStart
[PSCustomObject]@{
  ExitCode = $smokeExit
  TotalMinutes = [Math]::Round($smokeElapsed.TotalMinutes, 2)
  ConsolePath = $consolePath
  SummaryExists = Test-Path 'backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_summary.json'
  LeaderboardExists = Test-Path 'backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_leaderboard.json'
  ReportExists = Test-Path 'docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_next_seed_recovery_smoke_summary.md'
}
```

Expected healthy condition:

```text
ExitCode = 0
summary JSON exists
leaderboard JSON exists
Markdown report exists
stop_reason is not invalid_seed_expression
```

Acceptable diagnostic condition:

```text
ExitCode = 1
stop_reason is runtime_failure, insufficient_candidates, duplicate_rowset_only, no_improvement_streak_reached, or max_rounds_reached
next_seed_selection_status is round_best or compatible_fallback when a next seed was needed
```

Failure condition:

```text
stop_reason = invalid_seed_expression
failure_phase = invalid_seed_expression
```

- [ ] **Step 5: Inspect smoke summary**

Run:

```powershell
$summary = Get-Content backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_summary.json -Raw -Encoding UTF8 | ConvertFrom-Json
$summary | Select-Object status, stop_reason, completed_round_count, failed_round, failure_phase, failure_message, next_seed_selection_status, next_seed_strategy_name, next_seed_expression, rejected_round_best_seed_strategy_name, rejected_round_best_seed_reason | Format-List
$summary.final_best_candidate | Select-Object round_index, candidate_index, strategy_name, adjusted_score, promotion_score, expression | Format-List
$summary.wfo_candidate | Select-Object strategy_name, source_round, source_candidate, next_command | Format-List
```

Expected:

```text
stop_reason is not invalid_seed_expression
completed_round_count is 1 or 2
next_seed_selection_status is round_best or compatible_fallback if round 2 was attempted
```

- [ ] **Step 6: Inspect leaderboard**

Run:

```powershell
$leaderboard = Get-Content backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_leaderboard.json -Raw -Encoding UTF8 | ConvertFrom-Json
[PSCustomObject]@{ LeaderboardCount = @($leaderboard).Count }
$leaderboard | Select-Object round_index, candidate_index, strategy_name, status, candidate_type, promotion_passed, adjusted_score, trade_count_retention | Format-Table -AutoSize
```

Expected:

```text
LeaderboardCount >= 4
```

- [ ] **Step 7: Write Korean smoke review**

If smoke was run and summary JSON exists, create `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_v5_next_seed_recovery_smoke_review.md` by running:

```powershell
$summaryPath = 'backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_summary.json'
$leaderboardPath = 'backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_leaderboard.json'
$reviewPath = 'docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_next_seed_recovery_smoke_review.md'
$summary = Get-Content $summaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$leaderboard = if (Test-Path $leaderboardPath) {
  @(Get-Content $leaderboardPath -Raw -Encoding UTF8 | ConvertFrom-Json)
} else {
  @()
}
$leaderboardCount = @($leaderboard).Count
$elapsedMinutes = if (Get-Variable -Name smokeElapsed -ErrorAction SilentlyContinue) {
  [Math]::Round($smokeElapsed.TotalMinutes, 2)
} else {
  ''
}
$exitCode = if (Get-Variable -Name smokeExit -ErrorAction SilentlyContinue) {
  $smokeExit
} else {
  ''
}
$conclusion = if ($summary.stop_reason -ne 'invalid_seed_expression') {
  'PASS: next seed recovery 이후 invalid_seed_expression 중단이 재현되지 않았다.'
} else {
  'FAIL: next seed recovery 이후에도 invalid_seed_expression 중단이 재현되었다.'
}
$nextStep = if ($summary.stop_reason -ne 'invalid_seed_expression') {
  '$writing-plans Wide v2 v5 next seed recovery 적용 후 candidate_count=10 full run 검증 계획 작성'
} else {
  '$brainstorming Wide v2 v5 next seed fallback residual invalid_seed_expression 분석'
}
$review = @"
# Wide v2 v5 next seed recovery smoke 리뷰

## 목적

Wide v2 v5 recovery 이후 남은 ``invalid_seed_expression`` 병목이 next seed fallback 구현으로 해소되었는지 확인했다.

## 실행 요약

| 항목 | 값 |
| --- | --- |
| run_id | WideV2V5NextSeedRecoverySmoke_20260428 |
| candidate_count | 2 |
| max_rounds | 2 |
| exit_code | $exitCode |
| elapsed_minutes | $elapsedMinutes |
| status | $($summary.status) |
| stop_reason | $($summary.stop_reason) |
| completed_round_count | $($summary.completed_round_count) |
| failed_round | $($summary.failed_round) |
| failure_phase | $($summary.failure_phase) |

## Next seed 판정

| 항목 | 값 |
| --- | --- |
| next_seed_selection_status | $($summary.next_seed_selection_status) |
| next_seed_strategy_name | $($summary.next_seed_strategy_name) |
| next_seed_expression | $($summary.next_seed_expression) |
| rejected_round_best_seed_strategy_name | $($summary.rejected_round_best_seed_strategy_name) |
| rejected_round_best_seed_reason | $($summary.rejected_round_best_seed_reason) |
| leaderboard_count | $leaderboardCount |

## 결론

$conclusion

## 다음 단계

````text
$nextStep
````
"@
Set-Content -Path $reviewPath -Value $review -Encoding UTF8
```

- [ ] **Step 8: Commit smoke evidence if created**

If both smoke summary and review docs exist, run:

```powershell
git add `
  docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_next_seed_recovery_smoke_summary.md `
  docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_next_seed_recovery_smoke_review.md
git commit -m "Wide v2 다음 seed 복구 smoke 결과를 기록한다" -m @"
next seed expression validation recovery 적용 후 candidate_count=2 smoke 결과를 기록했다.

Constraint: runtime artifacts under backtest/temp, backtest/csv, backtest/graph are not committed
Constraint: smoke pass is not WFO/OOS approval
Rejected: candidate_count=10 full run before this smoke | invalid_seed_expression 병목 제거 여부를 먼저 확인해야 한다
Confidence: medium
Scope-risk: narrow
Directive: stop_reason이 invalid_seed_expression이면 full run으로 넘어가지 말 것
Tested: candidate_count=2 Wide v2 v5 next seed recovery smoke
Not-tested: candidate_count=10 full run and WFO/OOS validation
"@
```

If smoke report files do not exist because the command failed before report write, do not commit generated `backtest/temp` artifacts. Record the failure in the final response.

---

### Task 4: Final Verification Before Full-Run Decision

**Files:**
- Verify only. Do not create PR or merge in this task.

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

- [ ] **Step 5: Decide next stage**

Use this decision table:

```text
If all tests pass and smoke stop_reason is not invalid_seed_expression:
  Do not PR yet. Proceed to candidate_count=10 full run planning.

If smoke stop_reason is invalid_seed_expression:
  Do not full run. Start brainstorming for next seed fallback bug.

If unit tests fail:
  Fix tests before any smoke or PR.

If protected artifacts are staged:
  Unstage them before any commit or PR.
```

---

## Self-Review

- Spec coverage: This plan covers seed-compatible fallback selection, separation of global best from next seed, summary metadata, Markdown visibility, focused tests, smoke rerun, protected artifact handling, and full-run gating.
- Placeholder scan: Red-flag placeholder scan is clean. Angle-bracket search matches comparison operators inside condition expressions only.
- Type consistency: The plan consistently uses `next_seed_selection_status`, `next_seed_strategy_name`, `next_seed_expression`, `rejected_round_best_seed_strategy_name`, `rejected_round_best_seed_expression`, and `rejected_round_best_seed_reason`.
- Scope check: The plan does not run WFO/OOS, does not add Wide v6/v7, does not change v5 candidate families, and does not run candidate_count=10 before smoke passes.
