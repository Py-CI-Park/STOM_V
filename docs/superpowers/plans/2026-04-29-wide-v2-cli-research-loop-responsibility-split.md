# Wide v2 CLI Research Loop Responsibility Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split low-risk ranking, cleanup, and timing-metadata helpers out of `cli/research_loop.py` without changing CLI behavior or research loop outputs.

**Architecture:** This is a behavior-preserving refactor. New focused modules own ranking, cleanup, and runtime timing helper logic, while `cli/research_loop.py` keeps public entrypoints such as `ResearchLoopConfig`, `run_research_once()`, and `run_research_iteration()`.

**Tech Stack:** Python, pytest, STOM CLI modules, PowerShell, Git.

---

## Current State

- Current branch: `feature/cli-research-refactor-plan`
- Base branch: `STOM_Version_2U_C`
- Current base commit: `e4981a14 Wide v2 개발 정리 및 CLI 리팩토링 준비`
- Design spec: `docs/superpowers/specs/2026-04-29-wide-v2-cli-research-loop-responsibility-split-design.md`
- Protected untracked data: `backtest/graph/`

## Scope

In scope:

- Create `cli/research_ranking.py`.
- Create `cli/research_cleanup.py`.
- Create `cli/research_runtime_metadata.py`.
- Move ranking helper logic out of `cli/research_loop.py`.
- Move cleanup helper logic out of `cli/research_loop.py`.
- Move runtime timing summary helper logic out of `cli/research_loop.py`.
- Keep public research loop behavior unchanged.
- Keep CLI command names and options unchanged.
- Run baseline and post-refactor tests.

Out of scope:

- Do not split `cli/subcommands.py`.
- Do not implement profit-objective scoring.
- Do not add v6/v7 candidate generation.
- Do not move `_finalize_research_runtime_result()` or `_flush_research_runtime_checkpoint()` in this first refactor.
- Do not rerun WFO/OOS.
- Do not rerun full backtests.
- Do not commit `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, or `utility/strategy.db`.

## File Structure

Create:

- `cli/research_ranking.py`
  - Owns `_numeric_value()`, `_rank_score()`, `_rank_key()`, `_rank_candidate_results()`.
  - Imports `apply_retention_penalty` from `cli.research_retention`.
  - Does not import `ResearchLoopConfig`.

- `cli/research_cleanup.py`
  - Owns `_cleanup_candidate_by_name()`, `_candidate_not_created_cleanup()`, `_cleanup_summary()`, `_apply_iteration_cleanup()`.
  - Imports `DB_STRATEGY` and `delete_strategy_from_db`.
  - Does not import `ResearchLoopConfig`.

- `cli/research_runtime_metadata.py`
  - Owns `_elapsed_value()`, `_candidate_field()`, `_candidate_expression()`, `_runtime_timing_summary()`.
  - Does not import `ResearchRuntimeRecorder`; uses duck typing for `.events`.

Modify:

- `cli/research_loop.py`
  - Remove moved helper definitions.
  - Import moved helpers from the new modules.
  - Keep call sites unchanged where possible.

Test:

- `tests/unit/test_research_loop.py`
- `tests/unit/test_research_optimizer.py`
- `tests/unit/test_research_optimizer_report.py`
- `tests/unit/test_research_optimizer_state.py`
- `tests/unit/test_subcommands.py`

---

### Task 1: Baseline Verification

**Files:**
- Read only.

- [ ] **Step 1: Confirm branch and protected untracked data**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## feature/cli-research-refactor-plan
?? backtest/graph/
```

- [ ] **Step 2: Run baseline research loop tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 3: Run baseline optimizer tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 4: Run baseline subcommand tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py -q
```

Expected:

```text
All tests pass.
```

### Task 2: Extract Ranking Helpers

**Files:**
- Create: `cli/research_ranking.py`
- Modify: `cli/research_loop.py`
- Test: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Create `cli/research_ranking.py`**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: cli/research_ranking.py
+"""Ranking helpers for research candidate results."""
+
+from __future__ import annotations
+
+import math
+from typing import Any
+
+from cli.research_retention import apply_retention_penalty
+
+
+def _numeric_value(value: Any, default: float = 0.0) -> float:
+    try:
+        if value is None:
+            return default
+        normalized = float(value)
+        if not math.isfinite(normalized):
+            return default
+        return normalized
+    except (TypeError, ValueError):
+        return default
+
+
+def _rank_score(candidate: dict) -> dict:
+    incremental_promotion = candidate.get('promotion') or {}
+    incremental_comparison = candidate.get('comparison') or {}
+    reference_promotion = candidate.get('reference_promotion') or {}
+    reference_comparison = candidate.get('reference_comparison') or {}
+    use_reference = bool(reference_promotion and reference_comparison)
+    promotion = reference_promotion if use_reference else incremental_promotion
+    comparison = reference_comparison if use_reference else incremental_comparison
+    candidate_summary = comparison.get('candidate_summary') or {}
+    score = {
+        'promotion_passed': promotion.get('passed') is True,
+        'promotion_score': _numeric_value(promotion.get('score')),
+        'trade_count': _numeric_value(candidate_summary.get('trade_count')),
+        'trade_count_retention': _numeric_value(comparison.get('trade_count_retention')),
+        'date_concentration': _numeric_value(
+            candidate_summary.get('date_concentration'),
+            default=float('inf'),
+        ),
+        'symbol_concentration': _numeric_value(
+            candidate_summary.get('symbol_concentration'),
+            default=float('inf'),
+        ),
+    }
+    if use_reference:
+        score['score_basis'] = 'reference'
+        score['incremental_promotion_score'] = _numeric_value(incremental_promotion.get('score'))
+        score['reference_promotion_score'] = _numeric_value(reference_promotion.get('score'))
+    return score
+
+
+def _rank_key(candidate: dict) -> tuple:
+    score = candidate.get('rank_score') or _rank_score(candidate)
+    passed_rank = 0 if score['promotion_passed'] else 1
+    score_value = score.get('adjusted_score', score['promotion_score'])
+    return (
+        passed_rank,
+        -score_value,
+        -score['trade_count'],
+        -score['trade_count_retention'],
+        score['date_concentration'],
+        score['symbol_concentration'],
+        int(candidate.get('index') or 0),
+    )
+
+
+def _rank_candidate_results(
+    candidates: list[dict],
+    config=None,
+) -> tuple[list[dict], dict | None]:
+    ranked_candidates = [dict(candidate) for candidate in candidates]
+    for candidate in ranked_candidates:
+        rank_score = _rank_score(candidate)
+        if config is not None and config.use_retention_penalty:
+            rank_score = apply_retention_penalty(
+                rank_score,
+                config.min_estimated_retention,
+            )
+        candidate['rank'] = None
+        candidate['rank_score'] = rank_score
+        candidate['selected_as_best'] = False
+
+    eligible_indexes = [
+        index
+        for index, candidate in enumerate(ranked_candidates)
+        if candidate.get('status') == 'ok'
+    ]
+    ordered_indexes = sorted(
+        eligible_indexes,
+        key=lambda index: _rank_key(ranked_candidates[index]),
+    )
+
+    best_candidate = None
+    for rank, candidate_index in enumerate(ordered_indexes, start=1):
+        candidate = ranked_candidates[candidate_index]
+        candidate['rank'] = rank
+        candidate['selected_as_best'] = rank == 1
+        if rank == 1:
+            best_candidate = candidate
+
+    return ranked_candidates, best_candidate
*** End Patch
```

- [ ] **Step 2: Import ranking helpers in `cli/research_loop.py`**

Use `apply_patch` to add this import near existing research imports:

```diff
*** Begin Patch
*** Update File: cli/research_loop.py
@@
 from cli.research_promotion import evaluate_research_candidate
+from cli.research_ranking import (
+    _numeric_value,
+    _rank_candidate_results,
+    _rank_key,
+    _rank_score,
+)
 from cli.research_report import build_research_report, save_research_report_json, save_research_report_markdown
*** End Patch
```

- [ ] **Step 3: Remove ranking helper definitions from `cli/research_loop.py`**

Use `apply_patch` to delete the block from `def _numeric_value` through the end of `def _rank_candidate_results`.

Expected removed functions:

```text
_numeric_value
_rank_score
_rank_key
_rank_candidate_results
```

- [ ] **Step 4: Run research loop tests after ranking extraction**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
All tests pass.
```

### Task 3: Extract Cleanup Helpers

**Files:**
- Create: `cli/research_cleanup.py`
- Modify: `cli/research_loop.py`
- Test: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Create `cli/research_cleanup.py`**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: cli/research_cleanup.py
+"""Cleanup helpers for research candidate strategies."""
+
+from __future__ import annotations
+
+from cli.paths import DB_STRATEGY
+from cli.strategy_generator import delete_strategy_from_db
+
+_CLEANUP_SAFE_FAILURE_PHASES = {
+    'candidate_strategy',
+    'candidate_not_created',
+}
+
+
+def _cleanup_candidate_by_name(strategy_name: str, reason: str) -> dict:
+    try:
+        result = delete_strategy_from_db(DB_STRATEGY, strategy_name, 'buy')
+    except Exception as e:
+        return {
+            'attempted': True,
+            'reason': reason,
+            'strategy_name': strategy_name,
+            'status': 'error',
+            'message': str(e),
+        }
+    return {
+        'attempted': True,
+        'reason': reason,
+        'strategy_name': strategy_name,
+        'status': result.get('status'),
+        'message': result.get('message'),
+        'action': result.get('action'),
+    }
+
+
+def _candidate_not_created_cleanup(strategy_name: str, reason: str = 'candidate_not_created') -> dict:
+    return {
+        'attempted': False,
+        'reason': reason,
+        'strategy_name': strategy_name,
+    }
+
+
+def _cleanup_summary(candidates: list[dict]) -> dict:
+    summary = {
+        'attempted_count': 0,
+        'deleted_count': 0,
+        'kept_count': 0,
+        'failed_count': 0,
+        'items': [],
+    }
+    for candidate in candidates:
+        cleanup = candidate.get('cleanup') or {}
+        summary['items'].append(cleanup)
+        if cleanup.get('attempted') is True:
+            summary['attempted_count'] += 1
+            if cleanup.get('status') == 'error':
+                summary['failed_count'] += 1
+            elif cleanup.get('action') == 'deleted' or str(cleanup.get('reason', '')).endswith('_deleted'):
+                summary['deleted_count'] += 1
+        elif cleanup:
+            summary['kept_count'] += 1
+    return summary
+
+
+def _apply_iteration_cleanup(config, candidates: list[dict]) -> tuple[list[dict], dict]:
+    updated_candidates = []
+    for candidate in candidates:
+        updated = dict(candidate)
+        existing_cleanup = updated.get('cleanup')
+        if existing_cleanup is not None:
+            preserved = dict(existing_cleanup)
+            preserved['existing'] = True
+            updated['cleanup'] = preserved
+            updated_candidates.append(updated)
+            continue
+
+        strategy_name = updated.get('strategy_name')
+        is_best = updated.get('selected_as_best') is True
+        is_failed = updated.get('status') != 'ok'
+
+        if is_best and not config.cleanup_best_candidate:
+            updated['cleanup'] = {
+                'attempted': False,
+                'reason': 'best_candidate_kept',
+                'strategy_name': strategy_name,
+            }
+        elif is_best:
+            updated['cleanup'] = _cleanup_candidate_by_name(
+                strategy_name,
+                'best_candidate_deleted',
+            )
+        elif is_failed and (
+            updated.get('phase') in _CLEANUP_SAFE_FAILURE_PHASES
+            or updated.get('cleanup_safe') is True
+        ):
+            updated['cleanup'] = _cleanup_candidate_by_name(
+                strategy_name,
+                'failed_candidate_deleted',
+            )
+        elif is_failed:
+            updated['cleanup'] = _candidate_not_created_cleanup(strategy_name)
+        elif config.keep_loser_candidates:
+            updated['cleanup'] = {
+                'attempted': False,
+                'reason': 'loser_candidate_kept',
+                'strategy_name': strategy_name,
+            }
+        else:
+            updated['cleanup'] = _cleanup_candidate_by_name(
+                strategy_name,
+                'loser_candidate_deleted',
+            )
+        updated_candidates.append(updated)
+
+    return updated_candidates, _cleanup_summary(updated_candidates)
*** End Patch
```

- [ ] **Step 2: Import cleanup helpers in `cli/research_loop.py`**

Use `apply_patch` to add this import near existing research imports:

```diff
*** Begin Patch
*** Update File: cli/research_loop.py
@@
 from cli.research_compare import compare_trade_sets
+from cli.research_cleanup import (
+    _apply_iteration_cleanup,
+    _candidate_not_created_cleanup,
+    _cleanup_candidate_by_name,
+    _cleanup_summary,
+)
 from cli.research_iteration_v2 import build_iteration_v2_candidate_plan
*** End Patch
```

- [ ] **Step 3: Remove cleanup helper definitions from `cli/research_loop.py`**

Use `apply_patch` to delete the block from `def _cleanup_candidate_by_name` through the end of `def _apply_iteration_cleanup`.

Expected removed functions:

```text
_cleanup_candidate_by_name
_candidate_not_created_cleanup
_cleanup_summary
_apply_iteration_cleanup
```

- [ ] **Step 4: Remove now-unused cleanup imports or constants from `cli/research_loop.py`**

Inspect:

```powershell
rg -n "delete_strategy_from_db|_CLEANUP_SAFE_FAILURE_PHASES|DB_STRATEGY" cli/research_loop.py
```

If `delete_strategy_from_db` or `_CLEANUP_SAFE_FAILURE_PHASES` are no longer used, remove their import/definition from `cli/research_loop.py`.

Keep `DB_STRATEGY` in `cli/research_loop.py` only if other functions still use it.

- [ ] **Step 5: Run research loop tests after cleanup extraction**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
All tests pass.
```

### Task 4: Extract Runtime Timing Helpers

**Files:**
- Create: `cli/research_runtime_metadata.py`
- Modify: `cli/research_loop.py`
- Test: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Create `cli/research_runtime_metadata.py`**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: cli/research_runtime_metadata.py
+"""Runtime metadata helpers for research iterations."""
+
+from __future__ import annotations
+
+
+def _elapsed_value(event: dict) -> float | None:
+    value = event.get('elapsed_seconds')
+    if isinstance(value, (int, float)):
+        return float(value)
+    return None
+
+
+def _candidate_field(spec: dict, key: str):
+    if key in spec:
+        return spec.get(key)
+    source_candidate = spec.get('source_candidate')
+    if isinstance(source_candidate, dict):
+        return source_candidate.get(key)
+    return None
+
+
+def _candidate_expression(spec: dict) -> str | None:
+    expression = spec.get('expression')
+    if expression is not None:
+        return str(expression)
+    expressions = spec.get('expressions') or []
+    if expressions:
+        return str(expressions[0])
+    return None
+
+
+def _runtime_timing_summary(
+    recorder,
+    *,
+    candidate_specs: list[dict] | None = None,
+    candidates: list[dict] | None = None,
+) -> dict:
+    events = list(recorder.events)
+    checkpoint_durations = []
+    for previous, current in zip(events, events[1:]):
+        previous_elapsed = _elapsed_value(previous)
+        current_elapsed = _elapsed_value(current)
+        duration = (
+            round(current_elapsed - previous_elapsed, 3)
+            if previous_elapsed is not None and current_elapsed is not None
+            else None
+        )
+        checkpoint_durations.append({
+            'from': previous.get('name'),
+            'to': current.get('name'),
+            'phase': current.get('phase'),
+            'duration_seconds': duration,
+        })
+
+    specs_by_index = {
+        int(spec.get('index')): spec
+        for spec in (candidate_specs or [])
+        if spec.get('index') is not None
+    }
+    candidates_by_index = {
+        int(candidate.get('index')): candidate
+        for candidate in (candidates or [])
+        if candidate.get('index') is not None
+    }
+    starts = {
+        int(event.get('candidate_index')): event
+        for event in events
+        if event.get('name') == 'candidate_started' and event.get('candidate_index') is not None
+    }
+    completions = {
+        int(event.get('candidate_index')): event
+        for event in events
+        if event.get('name') in {'candidate_succeeded', 'candidate_failed'} and event.get('candidate_index') is not None
+    }
+    candidate_indexes = sorted(set(specs_by_index) | set(starts) | set(completions) | set(candidates_by_index))
+    candidate_durations = []
+    for index in candidate_indexes:
+        spec = specs_by_index.get(index, {})
+        candidate = candidates_by_index.get(index, {})
+        start = starts.get(index)
+        completion = completions.get(index)
+        start_elapsed = _elapsed_value(start or {})
+        completion_elapsed = _elapsed_value(completion or {})
+        duration = (
+            round(completion_elapsed - start_elapsed, 3)
+            if start_elapsed is not None and completion_elapsed is not None
+            else None
+        )
+        candidate_durations.append({
+            'index': index,
+            'strategy_name': (
+                candidate.get('strategy_name')
+                or spec.get('strategy_name')
+                or _candidate_field(spec, 'strategy_name')
+            ),
+            'expression': (
+                candidate.get('expression')
+                or _candidate_expression(spec)
+            ),
+            'source': (
+                candidate.get('source')
+                or spec.get('source')
+                or _candidate_field(spec, 'source')
+            ),
+            'status': candidate.get('status'),
+            'phase': candidate.get('phase'),
+            'started_at_seconds': start_elapsed,
+            'completed_at_seconds': completion_elapsed,
+            'duration_seconds': duration,
+        })
+
+    return {
+        'checkpoint_durations': checkpoint_durations,
+        'candidate_durations': candidate_durations,
+    }
*** End Patch
```

- [ ] **Step 2: Verify copied function body against `cli/research_loop.py`**

Before removing old functions, compare the current body around `_runtime_timing_summary`:

```powershell
Get-Content -LiteralPath cli\research_loop.py -TotalCount 510 | Select-Object -Skip 400 -First 110
```

If current `candidate_durations` fields differ from the plan snippet, update `cli/research_runtime_metadata.py` to match the current implementation exactly before continuing.

- [ ] **Step 3: Import runtime metadata helpers in `cli/research_loop.py`**

Use `apply_patch` to add this import near existing runtime output imports:

```diff
*** Begin Patch
*** Update File: cli/research_loop.py
@@
 from cli.research_runtime_output import ResearchRuntimeRecorder
+from cli.research_runtime_metadata import (
+    _candidate_expression,
+    _candidate_field,
+    _elapsed_value,
+    _runtime_timing_summary,
+)
 from cli.research_segments import build_research_segment_conditions
*** End Patch
```

- [ ] **Step 4: Remove runtime timing helper definitions from `cli/research_loop.py`**

Use `apply_patch` to delete these function definitions from `cli/research_loop.py`:

```text
_elapsed_value
_candidate_field
_candidate_expression
_runtime_timing_summary
```

Do not remove:

```text
_runtime_write_failure
_finalize_research_runtime_result
_flush_research_runtime_checkpoint
```

- [ ] **Step 5: Run research loop tests after runtime metadata extraction**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
All tests pass.
```

### Task 5: Update Imports And Static Checks

**Files:**
- Modify: `cli/research_loop.py`
- Read: new modules.

- [ ] **Step 1: Check for unused direct imports in `cli/research_loop.py`**

Run:

```powershell
rg -n "import math|delete_strategy_from_db|apply_retention_penalty|_CLEANUP_SAFE_FAILURE_PHASES|ResearchRuntimeRecorder" cli/research_loop.py
```

Expected:

- `import math` should be absent from `cli/research_loop.py`.
- `delete_strategy_from_db` should be absent from `cli/research_loop.py`.
- `apply_retention_penalty` should be absent from `cli/research_loop.py`.
- `_CLEANUP_SAFE_FAILURE_PHASES` should be absent from `cli/research_loop.py`.
- `ResearchRuntimeRecorder` should remain in `cli/research_loop.py`.

- [ ] **Step 2: Check new modules do not import `cli.research_loop`**

Run:

```powershell
rg -n "research_loop" cli/research_ranking.py cli/research_cleanup.py cli/research_runtime_metadata.py
```

Expected:

```text
No output.
```

- [ ] **Step 3: Run compile check for touched modules**

Run:

```powershell
python -m py_compile cli/research_loop.py cli/research_ranking.py cli/research_cleanup.py cli/research_runtime_metadata.py
```

Expected:

```text
No output and exit code 0.
```

### Task 6: Full Focused Verification

**Files:**
- No file edits.

- [ ] **Step 1: Run research loop tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 2: Run optimizer tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 3: Run subcommand tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 4: Run non-release sync guard**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
Exit code 0.
```

- [ ] **Step 5: Run whitespace check**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
No output.
```

### Task 7: Create PR Documentation

**Files:**
- Create: `docs/pr/2026-04-29_wide_v2_cli_research_loop_responsibility_split_pr.md`

- [ ] **Step 1: Create Korean PR body**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/pr/2026-04-29_wide_v2_cli_research_loop_responsibility_split_pr.md
+# Wide v2 CLI research_loop 책임 분리 1차 리팩토링
+
+## 목적
+
+이번 PR은 동작 변경이 아니라 구조 정리입니다.
+
+`cli/research_loop.py`에 섞여 있던 ranking, cleanup, runtime timing metadata 책임을 별도 모듈로 분리해 이후 조건식 개선 개발과 업스트림 업데이트 대응을 더 안전하게 만듭니다.
+
+## 변경 사항
+
+- `cli/research_ranking.py` 추가
+  - 후보 ranking score 계산
+  - retention penalty 적용
+  - best candidate 선택
+- `cli/research_cleanup.py` 추가
+  - 후보 전략 cleanup 결정
+  - cleanup summary 생성
+- `cli/research_runtime_metadata.py` 추가
+  - runtime checkpoint duration 계산
+  - candidate duration summary 생성
+- `cli/research_loop.py`에서 위 helper들을 import하도록 정리
+
+## 변경하지 않은 것
+
+- CLI 명령 이름과 옵션
+- `run_research_once()` 외부 동작
+- `run_research_iteration()` 외부 동작
+- 수익률 목적함수
+- v6/v7 후보 생성
+- WFO/OOS 실행
+- full backtest 실행
+
+## 검증
+
+```powershell
+python -m py_compile cli/research_loop.py cli/research_ranking.py cli/research_cleanup.py cli/research_runtime_metadata.py
+python -m pytest tests/unit/test_research_loop.py -q
+python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
+python -m pytest tests/unit/test_subcommands.py -q
+python scripts/verify_nonrelease_sync.py
+git diff --check --ignore-cr-at-eol HEAD
+```
+
+## 다음 단계
+
+다음 리팩토링 후보는 `cli/subcommands.py` command family 분리입니다. 다만 이 PR의 merge 이후 테스트 안정성을 먼저 확인한 뒤 별도 설계/계획/PR로 진행합니다.
*** End Patch
```

- [ ] **Step 2: Verify PR body content**

Run:

```powershell
Select-String -Path docs\pr\2026-04-29_wide_v2_cli_research_loop_responsibility_split_pr.md -Pattern "동작 변경이 아니라 구조 정리|cli/research_ranking.py|cli/research_cleanup.py|cli/research_runtime_metadata.py|test_research_loop.py"
```

Expected output contains all five patterns.

### Task 8: Commit Refactor

**Files:**
- Stage only files listed below.

- [ ] **Step 1: Review changed files**

Run:

```powershell
git status --short
```

Expected includes:

```text
?? backtest/graph/
?? cli/research_cleanup.py
?? cli/research_ranking.py
?? cli/research_runtime_metadata.py
 M cli/research_loop.py
?? docs/pr/2026-04-29_wide_v2_cli_research_loop_responsibility_split_pr.md
```

- [ ] **Step 2: Stage explicit files only**

Run:

```powershell
git add cli/research_loop.py
git add cli/research_ranking.py
git add cli/research_cleanup.py
git add cli/research_runtime_metadata.py
git add docs/pr/2026-04-29_wide_v2_cli_research_loop_responsibility_split_pr.md
git add docs/superpowers/plans/2026-04-29-wide-v2-cli-research-loop-responsibility-split.md
git add docs/superpowers/specs/2026-04-29-wide-v2-cli-research-loop-responsibility-split-design.md
```

- [ ] **Step 3: Confirm staged files**

Run:

```powershell
git diff --cached --name-only
```

Expected exactly:

```text
cli/research_cleanup.py
cli/research_loop.py
cli/research_ranking.py
cli/research_runtime_metadata.py
docs/pr/2026-04-29_wide_v2_cli_research_loop_responsibility_split_pr.md
docs/superpowers/plans/2026-04-29-wide-v2-cli-research-loop-responsibility-split.md
docs/superpowers/specs/2026-04-29-wide-v2-cli-research-loop-responsibility-split-design.md
```

- [ ] **Step 4: Commit with Lore protocol**

Run:

```powershell
git commit -m "Wide v2 research_loop 책임을 분리한다" -m "조건식 개선 CLI 커스텀을 업스트림 업데이트에 견디기 쉽게 만들기 위해 research_loop.py에 섞여 있던 ranking, cleanup, runtime timing metadata helper를 별도 모듈로 이동한다. CLI command contract와 research loop entrypoint는 유지하고, 동작 변경 없이 구조 경계만 정리한다.

Constraint: 이번 PR은 동작 변경 없는 구조 정리다
Constraint: subcommands.py 분리, 수익률 목적함수, v6/v7 후보 생성은 범위 밖이다
Rejected: finalize/checkpoint helper까지 이동 | runtime recorder와 error handling 결합이 깊어 첫 PR risk가 크다
Rejected: subcommands.py를 먼저 분리 | CLI surface 전체를 건드려 회귀 위험이 크다
Confidence: high
Scope-risk: moderate
Directive: 다음 리팩토링은 이 PR의 테스트 안정성을 확인한 뒤 subcommands.py command family 분리를 별도 PR로 진행할 것
Tested: py_compile, research_loop pytest, optimizer pytest, subcommands pytest, verify_nonrelease_sync, git diff check
Not-tested: full backtest, WFO/OOS rerun, live trading"
```

Expected:

```text
Git exits 0 and prints a commit summary for "Wide v2 research_loop 책임을 분리한다".
```

### Task 9: Push And Create PR

**Files:**
- Read: `docs/pr/2026-04-29_wide_v2_cli_research_loop_responsibility_split_pr.md`

- [ ] **Step 1: Confirm GitHub CLI auth**

Run:

```powershell
gh auth status
```

Expected:

```text
Logged in to github.com
```

- [ ] **Step 2: Push branch**

Run:

```powershell
git push -u origin feature/cli-research-refactor-plan
```

Expected:

```text
branch 'feature/cli-research-refactor-plan' set up to track 'origin/feature/cli-research-refactor-plan'
```

- [ ] **Step 3: Create PR**

Run:

```powershell
gh pr create --base STOM_Version_2U_C --head feature/cli-research-refactor-plan --title "Wide v2 CLI research_loop 책임 분리 1차 리팩토링" --body-file docs/pr/2026-04-29_wide_v2_cli_research_loop_responsibility_split_pr.md
```

Expected:

```text
https://github.com/Py-CI-Park/STOM_V/pull/<number>
```

### Task 10: Merge PR And Prepare Next Step

**Files:**
- No file edits.

- [ ] **Step 1: Merge PR through GitHub if merge state is clean**

Run:

```powershell
$pr = gh pr view --json number,url,state,mergeStateStatus,reviewDecision,baseRefName,headRefName | ConvertFrom-Json
"PR #$($pr.number) $($pr.url) state=$($pr.state) mergeState=$($pr.mergeStateStatus)"
if ($pr.mergeStateStatus -ne "CLEAN") { throw "PR is not clean: $($pr.mergeStateStatus)" }
gh pr merge --merge --delete-branch=false --subject "Wide v2 CLI research_loop 책임 분리 1차 리팩토링" --body "ranking, cleanup, runtime timing metadata helper를 별도 모듈로 분리해 research_loop.py의 책임을 줄인다."
```

Expected:

```text
PR state is CLEAN and merge exits 0.
```

- [ ] **Step 2: Fast-forward local base**

Run:

```powershell
git switch STOM_Version_2U_C
git pull --ff-only origin STOM_Version_2U_C
```

Expected:

```text
Fast-forward
```

- [ ] **Step 3: Run post-merge guard**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
No whitespace errors and verify_nonrelease_sync exits 0.
```

- [ ] **Step 4: Create next branch**

Run:

```powershell
git switch -c feature/cli-subcommands-refactor-plan
```

Expected:

```text
Switched to a new branch 'feature/cli-subcommands-refactor-plan'
```

- [ ] **Step 5: Report next recommended command**

Report:

```text
$brainstorming Wide v2 CLI subcommands command family 분리 설계
```

---

## Self-Review

Spec coverage:

- Ranking helper split: Task 2.
- Cleanup helper split: Task 3.
- Runtime timing metadata split: Task 4.
- No `subcommands.py` split: explicitly out of scope.
- No profit objective or v6/v7 work: explicitly out of scope.
- Verification before/after: Tasks 1, 5, and 6.
- PR body and merge routine: Tasks 7, 9, and 10.

Placeholder scan:

- No placeholder markers or incomplete file paths are intentionally left.
- Every created file path is exact.
- Every command includes an expected result.

Risk controls:

- The plan keeps `run_research_once()` and `run_research_iteration()` in `cli/research_loop.py`.
- The plan avoids moving `_finalize_research_runtime_result()` and `_flush_research_runtime_checkpoint()`.
- New modules do not import `cli.research_loop`, reducing circular import risk.
- Tests run after each extraction stage.

## Execution Recommendation

Recommended execution mode: Inline Execution using `superpowers:executing-plans`.

Reason:

- The refactor is sequential and shared-file heavy.
- Staging and PR creation should stay in one session for traceability.
- Subagents are not necessary unless a separate review lane is explicitly requested.
