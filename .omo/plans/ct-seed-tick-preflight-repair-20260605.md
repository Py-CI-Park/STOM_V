# C_T Seed Tick Preflight Repair 20260605

## TL;DR
> **Summary**: Repair the blocked `C_T_900_920_U2_B/S` tick preflight by proving exact per-day/per-window tick coverage, finding a fair same-window active control, and running only bounded warm/cold preflights until CSV+metrics appears or the blocker is reclassified.
> **Deliverables**:
> - Exact tick coverage/window scanner evidence.
> - Static seed/control time-filter and no-trade inspection.
> - Same-window active-control search and bounded C_T preflight results.
> - Decision card, full page progress table, and next command.
> **Effort**: Large
> **Parallel**: YES - 3 waves
> **Critical Path**: P0 -> P1/P2 -> P3 -> P4 -> P5/P6 -> Final

## Context

### Original Request
Run the recommended `$ulw-plan` command and continue completing the page:

```text
$ulw-plan C_T seed tick preflight repair plan: use .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p6-root-cause-decision-card.md, p3-window-coverage-audit.json, p4-cold-warm-compare.md, and p5-control-baseline.md as primary evidence. Build an exact per-day time-window coverage preflight for tick runs, find or construct a same-window active control without editing official engines or hard gates, inspect C_T_900_920_U2_B/S time filters and no-trade behavior, test the smallest corrected windows that can produce CSV/metrics, keep all new toggles default OFF, and keep 2023-2025 training plus 2022/2026 OOS blocked until a passing C_T preflight exists.
```

### Evidence Summary
- Previous page selected `INCONCLUSIVE_NEEDS_ENGINE_INTERNAL_EVIDENCE`, subtype `exact_window_no_metrics_after_data_load`.
- C_T W1R warm on `2025-01-03 09:00..09:01` loaded `back_count=41` but produced no CSV/metrics.
- Plan-bound C_T cold same-window run with `--timeout 120`, `wall_cap=240` also loaded data but produced no CSV/metrics.
- Same-window control `Tick_B_902_905_Update_2/S` also produced no CSV/metrics in `09:00..09:01`.
- Active-window control succeeded in `09:02..09:05`, proving the same-day stack can produce CSV/metrics.

### Metis Review Applied
- The plan avoids seed-only claims because the same-window control also failed.
- Runtime DB/CSV writes from owned diagnostic runs are allowed as evidence only and must not be staged.
- All runtime runs use unique IDs, owned PID capture, UTF-8/unbuffered output, inner timeouts, and outer wall caps.
- Static strategy facts are recorded as clues only, not proof of overfire or no-trade behavior.

## Work Objectives

### Core Objective
Find the smallest exact tick window where the same-day control path and C_T seed can be compared fairly, then decide whether C_T can produce CSV/metrics in bounded preflight. If no fair active same-window control exists, preserve the blocker and recommend the next narrower instrumentation page.

### Deliverables
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p0-safety-baseline.md`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p1-window-coverage-preflight.md`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p2-strategy-timefilter-inspect.md`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p3-same-window-active-control.md`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p4-ct-bounded-preflight.md`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p5-dashboard-ai-context-check.md`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p6-decision-card.md`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p7-next-command.md`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/final-verification.md`

### Definition Of Done
- No official engine, hard gate, `backtest/graph`, protected runtime path, export, live, V3K, long training, or OOS violation.
- Exact date/window coverage and strategy time-filter facts are recorded.
- At least one same-window control attempt is recorded, or a documented reason proves none can be selected within bounds.
- C_T bounded preflight is either `passing_preflight` (`status=success`, CSV path present, metrics present, no timeout) or explicitly blocked with evidence.
- Final page progress table and next command are written.

### Must Have
- Use existing `ai_strategy_loop/scripts/tick_seed_timeout_probe.py` where possible.
- If adding a helper, keep it additive under `ai_strategy_loop/scripts/`, test-first, and protected-output safe.
- Use read-only SQLite (`mode=ro`) for `_database/stock_tick_back.db`.
- Runtime evidence output must stay under `.omo/evidence/ct-seed-tick-preflight-repair-20260605/`.
- Passing preflight requires CSV+metrics; trade count is recorded but not the sole pass/fail condition.

### Must NOT Have
- No edits to `backtest/backengine_*.py`, `backtest/back_static.py`, `ai_strategy_loop/fitness/score.py`, or `backtest/graph`.
- No `final_approval`, `export_winner`, KHOPENAPI/live broker, V3K gate, blanket `taskkill`.
- No 2023-2025 training or 2022/2026 OOS in this page.
- No human-level, seed-superior, or OOS performance claim.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: TDD for any new helper/source change; otherwise evidence-only runtime QA.
- QA policy: each task has happy/failure scenarios and adversarial notes.
- Evidence root: `.omo/evidence/ct-seed-tick-preflight-repair-20260605/`.

Focused commands:

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py tests/unit/test_warm_session_window.py tests/unit/test_dashboard_engine_progress_contract.py -q
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_runner_helpers.py::test_runner_attaches_protocol_diagnostics_on_timeout tests/unit/test_runner_helpers.py::test_runner_records_timeout_checkpoint_fields -q
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json
```

## Execution Strategy

### Parallel Execution Waves
Wave 1: P0 safety, P1 coverage scanner, P2 static strategy inspection.
Wave 2: P3 same-window active control search, then P4 bounded C_T preflight.
Wave 3: P5 dashboard/context check, P6 decision, P7 next command, final verification.

### Dependency Matrix
| Task | Depends On | Blocks |
|---|---|---|
| P0 | none | P3, P4 |
| P1 | P0 | P3, P4, P6 |
| P2 | P0 | P3, P4, P6 |
| P3 | P1, P2 | P4, P6 |
| P4 | P3 | P6, P7 |
| P5 | P1, P2 | P6 |
| P6 | P3, P4, P5 | P7 |
| P7 | P6 | Final |

## TODOs

- [x] P0 - Safety Baseline And Resume Boundary

  **What to do**: Capture branch, HEAD, dirty status, protected path status, Boulder state, existing dashboard/listener state, and live AI loop/backtest processes. Do not kill anything.
  **Must NOT do**: Do not start runtime diagnostics or edit source in P0.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: P3/P4 | Blocked By: none

  **References**:
  - Policy: `AGENTS.md` - protected path and nonrelease rules.
  - Evidence: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/final-verification.md` - prior clean final state.

  **Acceptance Criteria**:
  - [ ] `p0-safety-baseline.md` records HEAD/branch/dirty/protected/process state.
  - [ ] Protected path status has no output.
  - [ ] Any unowned conflicting process blocks P3/P4 instead of being killed.

  **QA Scenarios**:
  ```text
  Scenario: Safety snapshot
    Tool: powershell
    Steps: Run git status, protected path status, boulder read, port/process queries.
    Expected: Evidence records state without mutation.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p0-safety-baseline.md

  Scenario: Existing unowned runtime
    Tool: powershell
    Steps: If process query finds non-owned loop/backtest, record PID and stop later runtime tasks.
    Expected: No kill command; later runtime tasks marked blocked.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p0-safety-baseline.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p0-safety-baseline.md`

- [x] P1 - Exact Tick Window Coverage Preflight

  **What to do**: Build a read-only coverage artifact for candidate windows around `2025-01-03`, starting from `09:00..09:05`, with 1-minute and 3-minute windows. Record moneytop rows, distinct code counts, per-window index counts, and first/last covered tick index. Prefer an evidence-only script invocation; if reusable helper code is added, add focused tests first.
  **Must NOT do**: Do not write `_database`; do not assume `moneytop` rows imply trades.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: P3/P4/P6 | Blocked By: P0

  **References**:
  - Pattern: `ai_strategy_loop/scripts/e2e_smoke.py:131` - tick day extraction and moneytop coverage.
  - Pattern: `ai_strategy_loop/scripts/build_subset_db.py:77` - read-only sqlite connection.
  - Evidence: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p3-window-coverage-audit.json`.

  **Acceptance Criteria**:
  - [ ] Raw JSON coverage artifact exists and uses read-only DB access.
  - [ ] Markdown summary identifies the smallest candidate active windows to try.
  - [ ] Empty windows are explicitly listed, not silently skipped.

  **QA Scenarios**:
  ```text
  Scenario: Covered active windows found
    Tool: powershell/python
    Steps: Scan `20250103` windows from `090000` through `090500`.
    Expected: JSON lists row/code/count facts for each window.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p1-window-coverage-preflight.json

  Scenario: Empty window remains explicit
    Tool: powershell/python
    Steps: Include prior empty `20250102 09:00..09:05`.
    Expected: Artifact records zero coverage and does not propose it for runtime.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p1-window-coverage-preflight.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p1-*`; optional helper/test only if needed

- [x] P2 - C_T And Control Strategy Time-Filter Inspection

  **What to do**: Use the same loop seed-read path to capture C_T and control code hashes, line counts, first lines, `self.Buy`/`self.Sell`, and static time/filter tokens. Record inferred active windows as clues only.
  **Must NOT do**: Do not treat static code facts as proof of overfire or no-trade behavior.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: P3/P4/P6 | Blocked By: P0

  **References**:
  - API: `ai_strategy_loop/controller/loop.py:2118` `_read_strategy_code`.
  - Helper: `ai_strategy_loop/scripts/tick_seed_timeout_probe.py` inspect command.
  - Evidence: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p2-inspect-probe.json`.

  **Acceptance Criteria**:
  - [ ] `p2-strategy-timefilter-inspect.md` records static facts for C_T and control buy/sell.
  - [ ] Any inferred window is labeled `static_hint`, not proof.
  - [ ] Missing or malformed seed code stops runtime tasks and updates P6.

  **QA Scenarios**:
  ```text
  Scenario: Strategy code available
    Tool: powershell
    Steps: Run helper inspect for C_T and control names.
    Expected: Hashes and required call presence recorded.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p2-strategy-timefilter-inspect.md

  Scenario: Static hints are not overclaimed
    Tool: powershell/rg
    Steps: Search P2 for `proof`.
    Expected: No static fact is described as root-cause proof.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p2-strategy-timefilter-inspect.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p2-*`

- [x] P3 - Same-Window Active Control Search

  **What to do**: From P1/P2, select the smallest same-day window where a control seed is likely active and data is covered. Run a bounded control warm preflight first. If no such fair window exists, record `no_same_window_active_control` and skip P4 runtime expansion.
  **Must NOT do**: Do not use the prior `09:02..09:05` control success as same-window proof unless C_T is tested on that same window too.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: P4/P6 | Blocked By: P1/P2

  **References**:
  - Evidence: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-baseline.md`.
  - Helper: `ai_strategy_loop/scripts/tick_seed_timeout_probe.py` run-loop command.
  - Config: `ai_strategy_loop/config.py:111` and `ai_strategy_loop/config.py:128`.

  **Acceptance Criteria**:
  - [ ] Control runtime uses unique `ct_preflight_control_*_20260605` run ID.
  - [ ] Warm timeout and outer wall cap are recorded.
  - [ ] Passing control means status success, CSV present, metrics present, and no timeout.

  **QA Scenarios**:
  ```text
  Scenario: Same-window control passes
    Tool: powershell
    Steps: Run bounded control on selected candidate window.
    Expected: CSV+metrics present and run id recorded.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p3-same-window-active-control.md

  Scenario: No fair active control
    Tool: powershell/python
    Steps: If all candidate windows fail or are non-equivalent, record the reason.
    Expected: P4 is restricted to non-claiming C_T exploratory preflight or skipped.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p3-same-window-active-control.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p3-*`

- [x] P4 - Bounded C_T Warm/Cold Preflight On Corrected Windows

  **What to do**: Only after P3. Run C_T on the selected same-window active candidate in warm mode first, then cold mode only if needed for comparison. Use `max_generations=1`, tick timeframe, engine count 1, warm timeout no more than 120s, and outer wall cap no more than 240s.
  **Must NOT do**: Do not continue expanding windows after first timeout/error unless the plan evidence says the prior window was invalid.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: P6/P7 | Blocked By: P3

  **References**:
  - Runtime: `ai_strategy_loop/controller/loop.py:1033` warm prepare path.
  - Runtime: `ai_strategy_loop/controller/loop.py:1236` warm run timeout.
  - Cold helper: `ai_strategy_loop/scripts/tick_seed_timeout_probe.py` run-cold.

  **Acceptance Criteria**:
  - [ ] `p4-ct-bounded-preflight.md` records config, run id, pid, elapsed, CSV yes/no, metrics yes/no.
  - [ ] If C_T produces CSV+metrics, mark `passing_ct_preflight`.
  - [ ] If C_T fails while same-window control passes, classify as C_T seed/window issue without claiming performance quality.
  - [ ] If both fail, preserve `INCONCLUSIVE` and block larger runs.

  **QA Scenarios**:
  ```text
  Scenario: C_T passing preflight
    Tool: powershell
    Steps: Run bounded warm C_T on selected active window.
    Expected: status success, CSV path, metrics, no timeout.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p4-ct-bounded-preflight.md

  Scenario: C_T fails despite active control
    Tool: powershell
    Steps: Compare P3 control pass with P4 C_T failure on same window.
    Expected: Decision evidence records seed/window blocker and blocks training/OOS.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p4-ct-bounded-preflight.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p4-*`

- [x] P5 - Dashboard And AI Context Visibility Check

  **What to do**: Check whether dashboard/status or evidence pages can explain the current engine config, timeframe, start/end time, timeout, and latest diagnosis. This is read/route verification only unless a minimal additive status artifact is already present.
  **Must NOT do**: Do not start broad dashboard UX work.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: P6 | Blocked By: P1/P2

  **References**:
  - Backend: `ai_strategy_loop/controller/progress_contract.py:65`.
  - Tests: `tests/unit/test_dashboard_engine_progress_contract.py`.
  - Prior request context: dashboard should show engine status/config/logs honestly.

  **Acceptance Criteria**:
  - [ ] `p5-dashboard-ai-context-check.md` states whether existing dashboard/context is sufficient for this blocker.
  - [ ] Any missing visibility is proposed as next command, not implemented here.

  **QA Scenarios**:
  ```text
  Scenario: Config visible in contract tests
    Tool: pytest
    Steps: Run dashboard engine progress contract tests.
    Expected: timeframe, timeout, start/end time fields covered.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p5-dashboard-ai-context-check.md

  Scenario: Missing visibility
    Tool: powershell/rg
    Steps: If a required field is absent, record the missing field.
    Expected: P6/P7 recommend a small visibility plan, not broad UX work.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p5-dashboard-ai-context-check.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p5-*`

- [x] P6 - Decision Card And Page Progress

  **What to do**: Write a decision card with one verdict: `PASSING_CT_PREFLIGHT`, `CT_SEED_WINDOW_BLOCKER`, `NO_FAIR_ACTIVE_CONTROL`, or `INCONCLUSIVE_ENGINE_INTERNAL`. Include progress table, allowed/blocked next steps, and no performance overclaim.
  **Must NOT do**: Do not claim human-level, seed-superior, or OOS proof.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: P7 | Blocked By: P3/P4/P5

  **References**:
  - Evidence: P1-P5 artifacts in this plan.
  - Prior decision: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p6-root-cause-decision-card.md`.

  **Acceptance Criteria**:
  - [ ] Exactly one verdict is selected.
  - [ ] Full page progress table is present.
  - [ ] Larger training/OOS remains blocked unless P4 has `passing_ct_preflight`.

  **QA Scenarios**:
  ```text
  Scenario: Decision is claim-safe
    Tool: rg
    Steps: Search P6 for human-level/OOS/seed-superior claims.
    Expected: Such claims appear only in blocked-claims sections.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p6-decision-card.md

  Scenario: Verdict is one of allowed enums
    Tool: powershell
    Steps: Inspect P6 verdict line.
    Expected: Exactly one allowed verdict.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p6-decision-card.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p6-decision-card.md`

- [x] P7 - Next Command

  **What to do**: Write the next recommended command. If P4 passed, recommend a bounded January retry plan, not 2023-2025/OOS directly. If P4 did not pass, recommend the next narrower instrumentation or seed/window repair page.
  **Must NOT do**: Do not start the next plan's runtime work.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: Final | Blocked By: P6

  **References**:
  - Evidence: `p6-decision-card.md`.
  - Guardrail: `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`.

  **Acceptance Criteria**:
  - [ ] `p7-next-command.md` contains exactly one recommended command.
  - [ ] Command preserves official engine/hard-gate/protected path/export/live/V3K/OOS guards.

  **QA Scenarios**:
  ```text
  Scenario: Passing preflight next command
    Tool: powershell
    Steps: If P6 is PASSING_CT_PREFLIGHT, inspect P7.
    Expected: Next command is bounded January retry, still not OOS.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p7-next-command.md

  Scenario: Non-passing preflight next command
    Tool: powershell
    Steps: If P6 is not PASSING_CT_PREFLIGHT, inspect P7.
    Expected: Next command targets narrower repair/instrumentation.
    Evidence: .omo/evidence/ct-seed-tick-preflight-repair-20260605/p7-next-command.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p7-next-command.md`

## Final Verification Wave

- [x] F1. Plan Compliance Audit
  - Command: `rg -n "2023-2025|2022/2026|final_approval|export_winner|taskkill|KHOPENAPI|V3K" .omo/evidence/ct-seed-tick-preflight-repair-20260605`
  - Expected: hits only in blocked/guard/next-command text.

- [x] F2. Focused Tests
  - Command: `$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py tests/unit/test_warm_session_window.py tests/unit/test_dashboard_engine_progress_contract.py -q`
  - Expected: pass.

- [x] F3. Runner Timeout Guards
  - Command: `$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_runner_helpers.py::test_runner_attaches_protocol_diagnostics_on_timeout tests/unit/test_runner_helpers.py::test_runner_records_timeout_checkpoint_fields -q`
  - Expected: pass.

- [x] F4. Protected Path And Runtime Cleanup
  - Commands:
    ```powershell
    git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'ct_preflight|ai_strategy_loop.controller.loop|stom_backtest.py' -and $_.CommandLine -notmatch 'Get-CimInstance' } | Select-Object ProcessId,CommandLine
    ```
  - Expected: no protected path output; no live owned runtime process.

- [x] F5. Nonrelease And Diff Guard
  - Commands:
    ```powershell
    python scripts/verify_nonrelease_sync.py
    git diff --check
    ```
  - Expected: verifier passes; diff check has no whitespace errors.

## Commit Strategy
- No commit by default because the worktree is broadly dirty.
- If the user later asks for a commit, stage explicitly only this plan's helper/test/evidence files and use Korean commit title/body.

## Success Criteria
- The page either finds a passing C_T preflight or explains why exact same-window active comparison is still unavailable.
- Full page progress and next command are documented.
- No larger training/OOS/performance claim is made.
