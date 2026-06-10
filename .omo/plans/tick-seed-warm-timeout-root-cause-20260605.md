# TICK Seed Warm Timeout Root Cause 20260605

## TL;DR
> **Summary**: Diagnose why seed `C_T_900_920_U2_B/S` times out in warm TICK mode even on the tiny `2025-01-01..2025-01-03 09:00:00..09:05:00` window. This page must narrow the blocker with read-only seed/data audits, a bounded diagnostic harness, tiny warm variants, and a safe cold/warm comparison before any 2023-2025 training or OOS is allowed.
> **Deliverables**:
> - Evidence-backed root-cause category for the P5 seed warm timeout.
> - Optional additive diagnostic helper under `ai_strategy_loop/scripts/`, with focused tests.
> - Tiny warm ladder configs/results, cold/warm comparison evidence, and stop rules.
> - Final page progress table and next command.
> **Effort**: Large
> **Parallel**: YES - 3 waves
> **Critical Path**: P0 safety -> P1 seed/config/data audit -> P2 probe harness -> P3 warm ladder -> P4 cold/warm compare -> P6 decision

## Context

### Original Request
The user asked to run the recommended command:

```text
$ulw-plan tick seed warm timeout root-cause plan: use .omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p5-timeout-diagnostic-ladder.md as primary evidence. Diagnose why C_T_900_920_U2_B/S times out even on 2025-01-01..2025-01-03 tick 09:00-09:05 warm mode, compare smaller window and cold/warm behavior if safe, preserve official backtest engines and hard gates, and do not start 2023-2025 training or OOS until a passing preflight exists.
```

### Interview Summary
- No additional user decision is needed. Default decision: bounded diagnosis first, no long training, no OOS.
- Runtime loop DB writes under `ai_strategy_loop/state/*.db` are allowed only as diagnostic evidence from owned runs and must not be staged. Protected/runtime source paths remain no-edit/no-stage.
- A small additive helper is allowed only under `ai_strategy_loop/scripts/` if it avoids official engine internals and is covered by tests.

### Metis Review
Gaps addressed:
- Terminal root-cause categories are defined in this plan.
- Exact warm/cold diagnostic matrix and stop rules are fixed.
- `safe` cold comparison now means owned process, unique run ID, UTF-8/unbuffered output, inner timeout plus outer wall cap, and no blanket process kill.
- Passing preflight means `status=success`, `csv_path` present, metrics present, elapsed under configured timeout, and no timeout/recovery branch. Trade count is recorded but not used alone as pass/fail.
- Data availability and seed code existence must be proven before runtime claims.
- Runtime DB writes are evidence-only; protected path status must be checked before and after.

## Work Objectives

### Core Objective
Find the first evidence-backed root-cause category for the seed warm timeout without changing official backtest engines, scoring hard gates, or production export paths.

### Root-Cause Categories
The final decision card must choose exactly one:

| Category | Evidence Required |
|---|---|
| `DATA_WINDOW_EMPTY_OR_NONTRADING` | read-only data audit shows no usable moneytop/tick rows or no trading-day coverage for the requested window. |
| `SEED_CODE_MISSING_OR_STALE` | seed buy/sell code is missing, empty, malformed, or not the expected `C_T_900_920_U2_B/S` code. |
| `WARM_SESSION_PATH_REGRESSION` | cold same-window run succeeds but warm tiny run times out/fails on the same seed/window, with data and seed present. |
| `SEED_RUNTIME_OVERFIRE_OR_STRATEGY_WORKLOAD` | data/control path is usable, seed code exists, and both warm/cold or repeated tiny warm variants show timeout/no-metrics behavior tied to the seed workload. |
| `ENV_RESOURCE_OR_ORPHAN_PROCESS_PRESSURE` | process/RAM/orphan evidence shows environment pressure invalidates runtime comparison. |
| `INCONCLUSIVE_NEEDS_ENGINE_INTERNAL_EVIDENCE` | wrapper evidence points inside official engine internals, but engine edits are forbidden and evidence is insufficient to classify further. |

### Deliverables
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p0-safety-baseline.md`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p1-seed-config-data-audit.md`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p2-probe-harness-contract.md`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p3-warm-tiny-ladder.md`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p4-cold-warm-compare.md`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-baseline.md`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p6-root-cause-decision-card.md`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p7-training-gate.md`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/final-verification.md`

### Definition Of Done
- Every run uses a unique `tick_seed_timeout_*_20260605` run ID and owned PID capture.
- No 2023-2025 training and no 2022/2026 OOS run occur.
- One root-cause category is chosen or explicitly marked inconclusive.
- Final evidence includes whole-page progress and the next command.
- `python scripts/verify_nonrelease_sync.py`, `git diff --check`, focused tests, and protected-path status checks are recorded.

### Must Have
- `$env:PYTHONUTF8='1'` and `$env:PYTHONUNBUFFERED='1'` for all runtime captures.
- Inner timeout and outer wrapper cap for every runtime run.
- Seed code hash, first lines, `self.Buy`/`self.Sell` presence, and basic static facts captured without using them as overfire proof.
- Effective `BacktestConfig` captured for every variant.
- Data-window coverage checked read-only before blaming strategy logic.

### Must NOT Have
- No edits to `backtest/backengine_*.py`, `backtest/back_static.py`, or `ai_strategy_loop/fitness/score.py`.
- No hard-gate relaxation.
- No `final_approval`, `export_winner`, live broker/KHOPENAPI, V3K gate action, or blanket `taskkill`.
- No staging of runtime DBs or protected paths.
- No human-level or seed-superior performance claim.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.

- Test decision: TDD for any helper script, using pytest.
- QA policy: Every task has agent-executed scenarios.
- Evidence root: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/`.
- Runtime DB policy: owned loop runs may update `ai_strategy_loop/state/*.db` as evidence, but these files are generated state and must not be staged.

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
Wave 1: P0, P1, P2 test-first helper contract.
Wave 2: P3 warm tiny ladder, P4 cold/warm comparison, P5 control baseline.
Wave 3: P6 root-cause decision, P7 training gate, final verification.

### Dependency Matrix
| Task | Depends On | Blocks |
|---|---|---|
| P0 | none | P3, P4 |
| P1 | P0 | P3, P4, P5, P6 |
| P2 | P0 | P3, P4, P5 |
| P3 | P1, P2 | P4, P6, P7 |
| P4 | P1, P2, P3 | P6, P7 |
| P5 | P1, P2 | P6 |
| P6 | P3, P4, P5 | P7 |
| P7 | P6 | Final |

## TODOs

- [x] P0 - Safety Baseline And Process Boundary

  **What to do**: Capture branch, HEAD, dirty status, current active OMO state, protected-path status, any listener/process using dashboard ports, and any live `python` child process that looks like an AI loop/backtest. Do not kill anything in P0.
  **Must NOT do**: Do not start diagnostics, do not edit source, do not stage, do not kill processes.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: P3/P4 | Blocked By: none

  **References**:
  - Pattern: `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p5-timeout-diagnostic-ladder.md` - primary blocked evidence.
  - Pattern: `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p7-decision-card.md` - prior page terminal verdict and next command.
  - Policy: `AGENTS.md` - protected path and commit rules.
  - Policy: `ai_strategy_loop/AGENTS.md` - `state/` is generated runtime state.

  **Acceptance Criteria**:
  - [ ] `p0-safety-baseline.md` records HEAD, branch, dirty summary, protected-path status, and existing process/listener state.
  - [ ] No protected path status output is introduced by P0.
  - [ ] If a conflicting live process exists, later runtime tasks are marked blocked until a non-destructive owned-process path is possible.

  **QA Scenarios**:
  ```text
  Scenario: Clean safety snapshot
    Tool: powershell
    Steps: Run git status, protected path status, Get-NetTCPConnection for known ports, and process listing filters.
    Expected: Evidence file records state without mutation.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p0-safety-baseline.md

  Scenario: Existing process conflict
    Tool: powershell
    Steps: If an unrelated live loop/backtest process is found, record PID/command and do not kill it.
    Expected: P3/P4 are blocked with reason `existing_unowned_process`.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p0-safety-baseline.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p0-safety-baseline.md`

- [x] P1 - Seed Code, Effective Config, And Data Coverage Audit

  **What to do**: Verify `C_T_900_920_U2_B` and `C_T_900_920_U2_S` exist in `ai_strategy_loop/state/loop_strategies.db` through the same code-read path used by the loop. Capture code hashes, line counts, first 12 lines, `self.Buy`/`self.Sell` presence, static `매수=True` count, and time-window tokens. Build the effective warm `BacktestConfig` from the failed P5 config and record start/end dates, start/end times, timeframe, engine count, timeout, and `divid_mode`. Read `_database/stock_tick_back.db` read-only to record moneytop rows and distinct days/codes for the requested date/time window.
  **Must NOT do**: Do not write `_database`; do not label static code facts as overfire proof.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: P3/P4/P5/P6 | Blocked By: P0

  **References**:
  - API: `ai_strategy_loop/controller/loop.py:2118` `_read_strategy_code` - seed code read contract.
  - API: `ai_strategy_loop/controller/loop.py:374` `_build_warm_btconfig` - effective warm config mapping.
  - Config: `ai_strategy_loop/config.py:86` and `ai_strategy_loop/config.py:111` - timeframe and warm timeout fields.
  - Data pattern: `ai_strategy_loop/scripts/e2e_smoke.py:131` - tick date extraction and moneytop coverage logic.
  - Evidence: `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p5-seed-diag-5m-config.json`.

  **Acceptance Criteria**:
  - [ ] `p1-seed-config-data-audit.md` includes seed existence, code hashes, effective config, and read-only data coverage.
  - [ ] If seed code is missing or data coverage is empty, P3/P4 are skipped and P6 chooses `SEED_CODE_MISSING_OR_STALE` or `DATA_WINDOW_EMPTY_OR_NONTRADING`.
  - [ ] Read-only DB access uses `mode=ro` or equivalent non-mutating access.

  **QA Scenarios**:
  ```text
  Scenario: Seed and data present
    Tool: powershell/python
    Steps: Read seed code with `_read_strategy_code`, build warm config, query tick DB read-only for 20250101..20250103 090000..090500.
    Expected: Evidence records non-empty seed code and data coverage summary.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p1-seed-config-data-audit.md

  Scenario: Missing seed or empty data
    Tool: powershell/python
    Steps: If either read fails or row counts are zero, do not run runtime diagnostics.
    Expected: P1 records blocker and P6 can classify without runtime run.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p1-seed-config-data-audit.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p1-seed-config-data-audit.md`

- [x] P2 - Add Diagnostic Probe Harness With Tests

  **What to do**: Add an additive helper `ai_strategy_loop/scripts/tick_seed_timeout_probe.py` plus `tests/unit/test_tick_seed_timeout_probe.py`. The helper must support dry inspect and bounded runtime commands:
  - `inspect --config-json <path> --buy <name> --sell <name> --out <json>`
  - `run-loop --config-json <path> --run-id <id> --wall-cap <sec> --out <json>`
  - `run-cold --config-json <path> --buy <name> --sell <name> --wall-cap <sec> --out <json>`
  The helper must set UTF-8/unbuffered env vars, capture PID/command/elapsed/stdout/stderr paths, never call export/final approval, and classify raw outcomes into the root-cause category inputs without editing official engines.
  **Must NOT do**: Do not import or modify `backtest/backengine_*`; do not hide timeout as success; do not use blanket `taskkill`.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: P3/P4/P5 | Blocked By: P0

  **References**:
  - Pattern: `ai_strategy_loop/scripts/r4_tick_smalluniverse_poc.py` - AI loop helper script structure and bootstrap import.
  - Pattern: `ai_strategy_loop/scripts/e2e_smoke.py:120` - subprocess use instead of unsafe in-process backtest.
  - API: `ai_strategy_loop/controller/loop.py:239` `run_backtest_for` - cold subprocess path and command shape.
  - API: `cli/config.py:95` - `stom_backtest.py` CLI arguments.
  - Tests: `tests/AGENTS.md` - test fixture and runtime DB conventions.

  **Acceptance Criteria**:
  - [ ] Unit tests fail before implementation and pass after implementation.
  - [ ] Helper command construction includes `PYTHONUTF8=1`, `PYTHONUNBUFFERED=1`, unique evidence output paths, and no forbidden route/function strings.
  - [ ] Helper can run `inspect` without runtime DB writes.
  - [ ] Helper returns explicit JSON status: `ok`, `timeout`, `error`, `blocked`, or `skipped`.

  **QA Scenarios**:
  ```text
  Scenario: Dry inspect command
    Tool: pytest
    Steps: Run helper inspect against a temp config and monkeypatched seed reader.
    Expected: JSON includes config, code hash placeholders, and no runtime process.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p2-probe-harness-contract.md

  Scenario: Runtime command is safe
    Tool: pytest
    Steps: Monkeypatch subprocess start and assert env, wall cap, output paths, and forbidden strings.
    Expected: No `final_approval`, `export_winner`, live broker, V3K, or blanket kill appears.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p2-probe-harness-contract.md
  ```

  **Commit**: NO | Files: `ai_strategy_loop/scripts/_tick_seed_probe_safety.py`, `ai_strategy_loop/scripts/tick_seed_timeout_probe.py`, `tests/unit/test_tick_seed_timeout_probe.py`, `.omo/evidence/.../p2-probe-harness-contract.md`

- [x] P3 - Warm Tiny Diagnostic Ladder

  **What to do**: Run only after P1 and P2 pass. Generate configs under the evidence root and execute this exact stop-on-first-timeout ladder with `max_generations=1`, seed `C_T_900_920_U2_B/S`, `bt_engine_mode=warm`, `bt_timeframe=tick`, and `bt_betting=5`, `bt_avg_time=30`.

  | Variant | Run ID | Period | Window | Engines | Warm Timeout | Wall Cap | Start Rule |
  |---|---|---|---|---:|---:|---:|---|
  | W1 | `tick_seed_timeout_warm_1d_1m_e1_20260605` | `2025-01-02..2025-01-02` | `09:00:00..09:01:00` | 1 | 60s | 150s | start after P1/P2 |
  | W2 | `tick_seed_timeout_warm_1d_5m_e1_20260605` | `2025-01-02..2025-01-02` | `09:00:00..09:05:00` | 1 | 90s | 210s | only if W1 passes |
  | W3 | `tick_seed_timeout_warm_3d_1m_e1_20260605` | `2025-01-01..2025-01-03` | `09:00:00..09:01:00` | 1 | 90s | 210s | only if W2 passes |
  | W4 | `tick_seed_timeout_warm_3d_5m_e1_20260605` | `2025-01-01..2025-01-03` | `09:00:00..09:05:00` | 1 | 120s | 270s | only if W3 passes |
  | W5 | `tick_seed_timeout_warm_3d_5m_e8_retry_20260605` | `2025-01-01..2025-01-03` | `09:00:00..09:05:00` | 8 | 120s | 270s | only if W4 passes |

  Use `2025-01-02` for one-day variants because `2025-01-01` may be non-trading; P1 data audit must confirm the actual trading-day availability and may move the one-day variant to the first covered trading day while recording the reason.
  **Must NOT do**: Do not continue the ladder after a timeout, no CSV, missing metrics, process error, or unsafe process state.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: P4/P6/P7 | Blocked By: P1/P2

  **References**:
  - Runtime path: `ai_strategy_loop/controller/loop.py:1037` warm prepare.
  - Timeout path: `ai_strategy_loop/controller/loop.py:1236` and `cli/warm_session.py:348`.
  - Prior failure: `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p5-timeout-diagnostic-ladder.md`.
  - Progress tests: `tests/unit/test_dashboard_engine_progress_contract.py:119`.

  **Acceptance Criteria**:
  - [ ] `p3-warm-tiny-ladder.md` records each attempted variant, config path, run ID, PID, elapsed, warm prepare `back_count`, backtest status, CSV yes/no, metrics yes/no, and stop reason.
  - [ ] If W1 fails, P4 still may run cold W1 comparison only if P0/P1 say process state is safe.
  - [ ] No variant runs after first failed warm gate unless the plan explicitly allows P4 cold comparison.

  **QA Scenarios**:
  ```text
  Scenario: Warm W1 passes
    Tool: powershell
    Steps: Run helper `run-loop` for W1 with 150s wall cap.
    Expected: JSON status success, CSV yes, metrics yes, elapsed below timeout; proceed to W2.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p3-warm-tiny-ladder.md

  Scenario: Warm W1 times out
    Tool: powershell
    Steps: Run helper `run-loop` for W1 with 150s wall cap.
    Expected: JSON status timeout/error, no further warm variants; P3 records first failing gate.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p3-warm-tiny-ladder.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p3-*`

- [x] P4 - Safe Cold Versus Warm Comparison

  **What to do**: Run a cold comparison only for the smallest warm variant that failed or for W1 if W1 passed but later warm failed. Use the same seed, dates, timeframe, start/end times, betting, avg time, and engine count where the cold CLI path can express them. Prefer raw `stom_backtest.py` subprocess through the helper rather than in-process runner. Use `--divid-mode 종목코드별 분류`, `--timeframe tick`, `--start-time`, `--end-time`, `--engines 1`, `--timeout 120`, `--format json`, `--quiet`, with outer wall cap `240s`.
  **Must NOT do**: Do not claim cold/warm equivalence if the cold path cannot load the same full-universe semantics; record such differences as limitations.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: P6/P7 | Blocked By: P1/P2/P3

  **References**:
  - CLI args: `cli/config.py:95` through `cli/config.py:144`.
  - Cold path pattern: `ai_strategy_loop/controller/loop.py:239` through `ai_strategy_loop/controller/loop.py:335`.
  - E2E subprocess rationale: `ai_strategy_loop/scripts/e2e_smoke.py:120`.

  **Acceptance Criteria**:
  - [ ] `p4-cold-warm-compare.md` records exact cold command, env, PID, elapsed, exit code, status, CSV, metrics, and semantic differences from warm.
  - [ ] If cold succeeds and matching warm fails, P6 can choose `WARM_SESSION_PATH_REGRESSION`.
  - [ ] If cold also times out/fails with seed and data present, P6 can choose `SEED_RUNTIME_OVERFIRE_OR_STRATEGY_WORKLOAD` unless process pressure evidence says otherwise.

  **QA Scenarios**:
  ```text
  Scenario: Cold succeeds while warm fails
    Tool: powershell
    Steps: Run helper `run-cold` for the first failed warm variant.
    Expected: Cold JSON success and warm JSON timeout/error; classify warm-path regression.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p4-cold-warm-compare.md

  Scenario: Cold comparison cannot be made equivalent
    Tool: powershell
    Steps: Helper detects unsupported full-universe equivalence or CLI limitation.
    Expected: P4 records limitation and P6 avoids overclaiming cold/warm root cause.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p4-cold-warm-compare.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p4-*`

- [x] P5 - Known-Fast Control Baseline

  **What to do**: If available in the loop DB, run a tiny warm control using canonical `Tick_B_902_905_Update_2` / `Tick_S_902_905_Update_2` on the same W1 date/window with engine count 1, warm timeout 60s, wall cap 150s. If those names are not present, record skip and cite prior `2026-05-28` evidence instead of fabricating a control.
  **Must NOT do**: Do not copy from production DB or export; only use loop DB names already present.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: P6 | Blocked By: P1/P2

  **References**:
  - Prior fast evidence: `docs/update_log/2026-05-28_ai_strategy_loop_R6_FULLUNIVERSE_HANDOFF.md:313`.
  - Prior seed baseline: `docs/update_log/2026-05-28_ai_strategy_loop_R6_FULLUNIVERSE_HANDOFF.md:64`.
  - Seed read helper: `ai_strategy_loop/controller/loop.py:2118`.

  **Acceptance Criteria**:
  - [ ] `p5-control-baseline.md` records control seed availability, config, run ID, status, elapsed, CSV, metrics, and whether it supports or refutes an environment-level explanation.
  - [ ] If unavailable, P5 is `skipped_control_not_present` and P6 records lower confidence.

  **QA Scenarios**:
  ```text
  Scenario: Control seed present
    Tool: powershell
    Steps: Run W1-equivalent warm control with `Tick_B_902_905_Update_2/S`.
    Expected: Success or failure recorded separately from C_T seed.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-baseline.md

  Scenario: Control seed absent
    Tool: powershell/python
    Steps: Check loop DB for both control names.
    Expected: No runtime control run; cite prior docs and classify as skipped.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-baseline.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p5-*`

- [x] P6 - Root-Cause Decision Card

  **What to do**: Write `p6-root-cause-decision-card.md` with a concise decision tree, evidence table, chosen category, confidence level, unresolved risks, and explicit allowed/blocked next steps. It must separate dashboard/process success from trading-performance proof.
  **Must NOT do**: Do not claim human-level or seed-superior performance.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: P7 | Blocked By: P3/P4/P5

  **References**:
  - Terminal categories: this plan's `Root-Cause Categories`.
  - Evidence: P1 through P5 artifacts.
  - Direction guard: `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`.

  **Acceptance Criteria**:
  - [ ] Exactly one root-cause category is selected.
  - [ ] If category is `INCONCLUSIVE_NEEDS_ENGINE_INTERNAL_EVIDENCE`, the decision card names the missing evidence and why official engine edits remain forbidden.
  - [ ] The card includes a page progress table and no performance/OOS overclaim.

  **QA Scenarios**:
  ```text
  Scenario: Classifiable root cause
    Tool: powershell/rg
    Steps: Inspect P1-P5 artifacts and write category evidence.
    Expected: One category selected with supporting rows.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p6-root-cause-decision-card.md

  Scenario: Inconclusive
    Tool: powershell/rg
    Steps: If evidence conflicts or points inside forbidden engine internals, mark inconclusive.
    Expected: No training/OOS; next command targets narrower instrumentation or safe reproduction.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p6-root-cause-decision-card.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p6-root-cause-decision-card.md`

- [x] P7 - Training Gate And Next Command

  **What to do**: Write `p7-training-gate.md`. If P3 produced a passing tiny warm preflight and P6 category is not environment/process pressure, recommend the next bounded January retry plan. Otherwise recommend the next narrower root-cause or instrumentation plan. Do not start any long training from this page.
  **Must NOT do**: Do not run January retry, 2023-2025 training, or 2022/2026 OOS in P7.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: Final | Blocked By: P6

  **References**:
  - Previous gate: `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p6-training-retry-gate.md`.
  - Current decision: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p6-root-cause-decision-card.md`.

  **Acceptance Criteria**:
  - [ ] `p7-training-gate.md` states allowed/not allowed for 10m diagnostic, January retry, 2023-2025 training, and OOS.
  - [ ] Exactly one next recommended command is provided.
  - [ ] No long runtime process is spawned.

  **QA Scenarios**:
  ```text
  Scenario: Tiny preflight passes
    Tool: powershell
    Steps: P3/P6 show pass and non-environment category.
    Expected: Next command is a bounded January retry plan, still not OOS.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p7-training-gate.md

  Scenario: Root cause remains blocked
    Tool: powershell
    Steps: P3/P6 show timeout, environment pressure, or inconclusive category.
    Expected: Next command targets narrower instrumentation; training/OOS blocked.
    Evidence: .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p7-training-gate.md
  ```

  **Commit**: NO | Files: `.omo/evidence/.../p7-training-gate.md`

## Final Verification Wave
> ALL must be agent-executed. Present consolidated results before marking the page complete.

- [x] F1. Plan Compliance Audit
  - Command: `rg -n "2023-2025|2022/2026|final_approval|export_winner|taskkill" .omo/evidence/tick-seed-warm-timeout-root-cause-20260605`
  - Expected: Mentions are only in forbidden-action or blocked sections; no invocation evidence.

- [x] F2. Focused Tests
  - Command: `$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py tests/unit/test_warm_session_window.py tests/unit/test_dashboard_engine_progress_contract.py -q`
  - Expected: pass.

- [x] F3. Runtime Cleanup And Protected Paths
  - Command: `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json`
  - Expected: no output.

- [x] F4. Nonrelease And Diff Guard
  - Commands:
    ```powershell
    python scripts/verify_nonrelease_sync.py
    git diff --check
    ```
  - Expected: verifier passes; diff check has no whitespace errors.

## Commit Strategy
- No commit by default. The worktree is already broadly dirty.
- If the user later requests a commit, stage files explicitly only:
  - `ai_strategy_loop/scripts/tick_seed_timeout_probe.py`
  - `ai_strategy_loop/scripts/_tick_seed_probe_safety.py`
  - `tests/unit/test_tick_seed_timeout_probe.py`
  - `.omo/plans/tick-seed-warm-timeout-root-cause-20260605.md`
  - `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/*`
- Commit title/body must be Korean per repo rule.

## Success Criteria
- Root cause is narrowed enough to decide whether the next page should be:
  - bounded January retry;
  - smaller/runtime instrumentation;
  - environment cleanup;
  - or an inconclusive engine-internal blocker.
- Full page progress is documented.
- Next command is explicit.
- No training/OOS/export/live/protected-path violation occurred.
