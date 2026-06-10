# TICK P7 Observability And Bounded Training 20260605

## TL;DR
> **Summary**: Before re-running the long 2023-2025 TICK P7 training job, strengthen honest runtime observability around warm backtests, timeouts, engine config, logs, and bounded execution. Then run a staged P7 training path that either produces frozen `exploration_pool_v2` / `research_pool_v2` / `promotion_gate_v2` artifacts or stops with a clear timeout blocker and no OOS.
> **Deliverables**:
> - Backtest progress and engine-log observability patch, reusing existing dashboard contracts.
> - Bounded preflight smoke config and evidence.
> - Bounded 2023-2025 P7 training config and run evidence.
> - Frozen candidate pools with explicit `promotion_gate_v2` section.
> - Conditional 2022/2026 OOS blocker or comparison.
> - Final decision card with progress table and next command.
> **Effort**: XL
> **Parallel**: YES - 4 waves
> **Critical Path**: P0 safety -> P1 observability contract -> P3 bounded preflight -> P4 P7 training -> P5 pool freeze -> P6 conditional OOS -> P7 decision card

## Context
### Original Request
The user asked to directly proceed with the recommended `$ulw-plan`:

> TICK P7 다년 run을 재시도하기 전에 백테스트 진행률/엔진 설정/엔진 로그/timeout 관측성을 보강하고, 2023~2025 bounded training run을 완료해 exploration_pool_v2/research_pool_v2/promotion_gate_v2 후보풀을 생성하는 계획을 만들어줘.

### Interview Summary
- No new user interview is required; the request names the source documents and guardrails.
- Default interpretation of `bounded`: exact config artifact, explicit per-run timeout, wall-clock cap, owned-process cleanup, and blocker evidence if the cap is exceeded.
- Terminal outcomes are deliberately two-path:
  - `completed_training_with_pools`
  - `blocked_with_timeout_evidence_no_oos`

### Metis Review (gaps addressed)
- Avoided the contradiction between "must complete P7" and "may timeout" by defining two valid terminal outcomes.
- Defined `bounded` as timeout + wall-clock + config identity + cleanup + blocker evidence.
- Avoided overclaiming engine-internal row/tick progress. The plan requires honest phase/generation/backtest-process observability and may add wrapper checkpoints outside official engines.
- Preserved existing `promotion_candidate` compatibility while adding an explicit artifact-level `promotion_gate_v2` section.
- Added no-OOS blocker path if no frozen promotion candidate exists.

## Work Objectives
### Core Objective
Make the next TICK P7 2023-2025 training attempt observable, bounded, restartable, and honest, then freeze research/promotion candidate pools before any fixed OOS.

### Deliverables
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p0-safety-snapshot.txt`
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p1-observability-contract.md`
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p2-dashboard-observability-smoke.md`
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p3-preflight-smoke-summary.md`
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p4-train-config.json`
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p4-train-log.txt`
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p5-candidate-pools.json`
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p6-oos-comparison.json` or `p6-oos-blocked.md`
- `.omo/evidence/tick-p7-observability-bounded-training-20260605/p7-decision-card.md`

### Definition of Done
- Existing progress/engine-state contracts remain backward compatible.
- `/status` and the dashboard show the active config, tick/min timeframe, engine mode/count, CPU count, current phase, elapsed time, ETA when derivable, timeout deadline, and recent loop/warm-backtest logs.
- A preflight smoke run proves observability works before the long P7 run starts, or writes a blocker.
- P7 either completes and writes candidate pools, or stops with explicit timeout/blocker evidence and no OOS.
- Candidate pool artifact is OOS-blind and includes `exploration_pool_v2`, `research_pool_v2`, `promotion_gate_v2`, and legacy `promotion_candidate`.
- Fixed 2022/2026 OOS is only run if a frozen promotion candidate exists.

### Must Have
- Exact period and timeframe in every evidence file.
- Bounded run IDs and config hashes.
- Owned-process cleanup only; no blanket process killing.
- Tests before or alongside implementation for every contract change.
- Final report separates research-readiness from human/seed-level proof.

### Must NOT Have
- No official engine edits: `backtest/backengine_*.py`, `backtest/back_static.py`.
- No hard-gate relaxation or edits to `ai_strategy_loop/fitness/score.py::compute_fitness`.
- No `backtest/graph/` edits.
- No protected path staging: `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `.omx/reports/`, `v3k_settings*.json`.
- No `final_approval`, `export_winner`, production strategy DB write, USER_ACK, KHOPENAPI login/connect, live broker wiring, V3K gate advancement, or blanket `taskkill`.
- No OOS-after-the-fact reselection.
- No claim that P7 success means human-level performance without fixed OOS/PBO/DSR/slippage proof.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.

- Test decision: TDD for changed contracts, tests-after for evidence-only scripts/configs.
- Framework: `pytest`, existing FastAPI `TestClient`, static frontend text tests, bounded CLI smoke commands.
- Evidence root: `.omo/evidence/tick-p7-observability-bounded-training-20260605/`

Focused verification commands:

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_engine_progress_contract.py tests/unit/test_dashboard_chart_explanations.py tests/unit/test_process_timing.py tests/unit/test_dashboard_phase_mapping.py -q
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_loop_robustness.py tests/unit/test_warm_session_window.py tests/unit/test_candidate_research_pool_v2.py tests/unit/test_promotion_diagnostics.py -q
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## Execution Strategy
### Parallel Execution Waves
Wave 1: P0 safety and P1 backend observability contract.
Wave 2: P2 dashboard surface and P3 bounded preflight smoke.
Wave 3: P4 P7 training and P5 pool freeze/diagnostics.
Wave 4: P6 conditional OOS and P7 decision card.

### Dependency Matrix
| Task | Depends On | Blocks |
|---|---|---|
| P0 Safety snapshot | none | all |
| P1 Observability contract | P0 | P2, P3, P4 |
| P2 Dashboard observability smoke | P1 | P3 |
| P3 Bounded preflight smoke | P1, P2 | P4 |
| P4 Bounded 2023-2025 training | P3 | P5 |
| P5 Candidate pool freeze | P4 | P6, P7 |
| P6 Conditional OOS | P5 | P7 |
| P7 Decision card | P5, P6 | Final |

## TODOs
- [x] 1. P0 - Safety Snapshot And Baseline Classification

  **What to do**: Create the evidence directory, capture branch/HEAD/dirty status, current boulder state, protected-path status, current dashboard listener status, and the exact source documents used for the plan. Classify existing dirty files as baseline inputs, not files to revert.

  **Must NOT do**: Do not edit source code, runtime DBs, protected paths, or run long backtests.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: all | Blocked By: none

  **References**:
  - Handoff: `docs/AGENT_HANDOFF.md`
  - Direction review: `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
  - P6 blocker: `.omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-summary.md`
  - P7 blocker: `.omo/evidence/tick-research-direction-realignment-20260605/p7-train-log.txt`
  - P9 decision: `.omo/evidence/tick-research-direction-realignment-20260605/p9-decision-card.md`

  **Acceptance Criteria**:
  - [ ] `p0-safety-snapshot.txt` contains branch, HEAD, dirty files, protected-path status, and active listeners.
  - [ ] `p0-source-index.md` lists the exact source documents and their role.
  - [ ] No protected path is modified or staged.

  **QA Scenarios**:
  ```text
  Scenario: Safety snapshot exists
    Tool: powershell
    Steps:
      git status --short --branch
      git rev-parse HEAD
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
    Expected: Commands are captured; protected-path status is empty or explicitly explained.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p0-safety-snapshot.txt

  Scenario: No source mutation in P0
    Tool: powershell
    Steps:
      git diff --name-only
    Expected: P0 adds evidence only.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p0-source-index.md
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

- [x] 2. P1 - Strengthen Backend Progress, Timeout, And Engine-State Contract

  **What to do**: Extend the existing observability contract without duplicating it. Add or update tests first so `latest.backtest_progress` and `latest.engine_state` can expose:
  - `timeout_sec`, `timeout_deadline_epoch`, `elapsed_sec`, `eta_sec`, `progress_source`
  - `bt_timeframe`, `bt_engine_mode`, `bt_full_start`, `bt_full_end`, `bt_universe_start_time`, `bt_universe_end_time`
  - `cpu_count`, `effective_engine_count`, `warm_prepared`, `back_count`
  - recent warm/backtest logs, including timeout/cancel/reset checkpoints.

  If child-process row/tick counters are unavailable without official engine edits, label progress as `phase_level` or `generation_level`, not `engine_internal`.

  **Must NOT do**: Do not edit `backtest/backengine_*.py`, `backtest/back_static.py`, or `compute_fitness`.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: P2, P3, P4 | Blocked By: P0

  **References**:
  - Contract builder: `ai_strategy_loop/controller/progress_contract.py:65`
  - Engine state builder: `ai_strategy_loop/controller/progress_contract.py:122`
  - Live publisher: `ai_strategy_loop/controller/loop.py:784`
  - Warm timeout pass-through: `ai_strategy_loop/controller/loop.py:1238`
  - GA warm timeout mirror: `ai_strategy_loop/controller/ga.py:261`
  - Warm session timeout/recovery: `cli/warm_session.py:352`
  - Existing tests: `tests/unit/test_dashboard_engine_progress_contract.py:27`, `tests/unit/test_process_timing.py`

  **Acceptance Criteria**:
  - [ ] Contract tests cover explicit timeout fields and phase-level progress labels.
  - [ ] `/status` normalization preserves legacy payloads and fills missing observability fields without rewriting runtime state.
  - [ ] Timeout/cancel/reset logs appear in recent logs when simulated.
  - [ ] Existing backward-compatible defaults still pass.

  **QA Scenarios**:
  ```text
  Scenario: Status payload reports timeout deadline
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_dashboard_engine_progress_contract.py -q
    Expected: Payload includes timeout fields, engine settings, CPU/engine count, and bounded progress source.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p1-progress-contract-tests.txt

  Scenario: Legacy current_state still works
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_dashboard_engine_progress_contract.py::test_status_route_normalizes_legacy_current_state_observability_fields -q
    Expected: Legacy state returns status 200 and computed observability defaults.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p1-legacy-status-tests.txt
  ```

  **Commit**: YES | Message: `조건연구 P7 백테스트 관측성 계약 보강` | Files: `ai_strategy_loop/controller/progress_contract.py`, `ai_strategy_loop/controller/contract.py`, `ai_strategy_loop/controller/state.py`, `ai_strategy_loop/controller/loop.py`, `ai_strategy_loop/controller/ga.py`, `cli/warm_session.py`, focused tests

- [x] 3. P2 - Update Dashboard Engine Panel And Phase Detail For Honest Runtime Visibility

  **What to do**: Update the dashboard frontend to show the strengthened fields from P1. The UI must clearly show:
  - overall progress, current phase, elapsed time, ETA/remaining when derivable
  - configured timeout and timeout deadline
  - engine mode, tick/min timeframe, date period, time window, CPU count, effective engine count
  - recent logs with timeout/reset/cancel messages
  - progress-source label: `generation_level`, `phase_level`, or `engine_internal` if ever available.

  Use the existing dashboard style; do not create a marketing page or nested cards.

  **Must NOT do**: Do not add unsupported claims such as "live engine-internal progress" unless the backend really supplies it.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: P3 | Blocked By: P1

  **References**:
  - Engine panel: `ai_strategy_loop/dashboard/frontend/engine.jsx:14`
  - Phase detail: `ai_strategy_loop/dashboard/frontend/phase-detail.jsx`
  - Status route: `ai_strategy_loop/dashboard/app.py:1447`
  - Existing frontend tests: `tests/unit/test_dashboard_chart_explanations.py`, `tests/unit/test_dashboard_phase_mapping.py`
  - Prior evidence: `.omo/evidence/tick-dashboard-observability-research-ux-20260604/p2-frontend-ux-repair.md`

  **Acceptance Criteria**:
  - [ ] Frontend tests assert visible labels for timeout, progress source, period, timeframe, engine count, and logs.
  - [ ] `engine.jsx` consumes `latest.backtest_progress` and `latest.engine_state` only; no duplicate fetching.
  - [ ] Long labels fit on desktop and mobile without overlap.

  **QA Scenarios**:
  ```text
  Scenario: Engine panel static contract
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_dashboard_chart_explanations.py tests/unit/test_dashboard_phase_mapping.py -q
    Expected: Frontend contains required labels and consumes backend fields.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p2-frontend-tests.txt

  Scenario: Live dashboard route smoke
    Tool: powershell + browser or curl
    Steps:
      python -m ai_strategy_loop --host 127.0.0.1 --port 8794
      curl.exe -sS --max-time 8 http://127.0.0.1:8794/status
    Expected: `/status` returns progress and engine state fields; owned server is stopped afterwards.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p2-dashboard-observability-smoke.md
  ```

  **Commit**: YES | Message: `조건연구 P7 대시보드 엔진 상태 표시 보강` | Files: `ai_strategy_loop/dashboard/frontend/engine.jsx`, `ai_strategy_loop/dashboard/frontend/phase-detail.jsx`, frontend tests

- [x] 4. P3 - Run Bounded Preflight Smoke Before Long P7

  **What to do**: Create `p3-preflight-config.json` and run a bounded smoke that is short enough to finish before the long P7 attempt. Use:
  - run ID: `tick_p7_preflight_observable_20260605`
  - timeframe: `tick`
  - period: `2025-01-01..2025-01-31`
  - time window: `09:00:00..09:30:00`
  - `max_generations=1`
  - `bt_engine_mode=warm`
  - `bt_warm_engine_count=8`
  - `bt_warm_run_timeout=300`
  - `prompt_logging_enabled=true`
  - `equity_points_enabled=true`
  - same generation toggles used in P6: classification/filter/time-dispersion/few-shot/sparse-positive/segment-feedback.

  If preflight times out or cannot produce status/log evidence, stop and write `p3-preflight-blocked.md`; do not start P4.

  **Must NOT do**: Do not treat smoke as OOS proof or promotion proof.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: P4 | Blocked By: P1, P2

  **References**:
  - P6 prior config: `.omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-config.json`
  - P6 timeout: `.omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-summary.md`
  - Loop CLI: `ai_strategy_loop/controller/loop.py:2264`

  **Acceptance Criteria**:
  - [ ] Preflight config exists and parses.
  - [ ] Preflight log captures run start, warm prepare, backtest phase, timeout fields, and final status.
  - [ ] `/status` captured during or after the run contains `latest.backtest_progress` and `latest.engine_state`.
  - [ ] If blocked, blocker explains whether the issue is auth, data, warm prepare, per-run timeout, or dashboard status.

  **QA Scenarios**:
  ```text
  Scenario: Preflight smoke
    Tool: powershell
    Steps:
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-p7-observability-bounded-training-20260605/p3-preflight-config.json --run-id tick_p7_preflight_observable_20260605
    Expected: Exits normally or writes exact blocker; no unsupported success claim.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p3-preflight-smoke-summary.md

  Scenario: Preflight status visibility
    Tool: powershell
    Steps:
      Query `/status` on the dashboard while or after preflight.
    Expected: Status includes active config, timeframe, engine mode/count, timeout fields, progress source, and recent logs.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p3-status-snapshot.json
  ```

  **Commit**: NO | Message: n/a | Files: evidence/config only

- [x] 5. P4 - Execute Bounded 2023-2025 P7 Training Or Stop With Timeout Evidence

  **What to do**: Create `p4-train-config.json` from the preflight config. Use:
  - run ID: `tick_p7_train_2023_2025_observable_20260605`
  - period: `2023-01-01..2025-12-31`
  - timeframe: `tick`
  - time window: `09:00:00..09:30:00`
  - `max_generations=10`
  - `bt_warm_run_timeout=900`
  - `bt_timeout=1800`
  - wall-clock cap: `6h`
  - same generation toggles as P3.

  During execution, poll status at a fixed interval and append snapshots to `p4-status-snapshots.jsonl`. If the wall-clock cap is reached, stop only the owned process/session, write `p4-train-blocked.md`, and do not run OOS.

  **Must NOT do**: Do not tune thresholds after seeing 2022/2026 OOS. Do not use OOS in this task.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: P5 | Blocked By: P3

  **References**:
  - Existing blocker: `.omo/evidence/tick-research-direction-realignment-20260605/p7-train-log.txt`
  - Loop runner: `ai_strategy_loop/controller/loop.py:901`
  - Warm timeout path: `cli/warm_session.py:352`
  - Config schema: `ai_strategy_loop/config.py:126`, `ai_strategy_loop/config.py:170`

  **Acceptance Criteria**:
  - [ ] `p4-train-config.json` records exact dates, timeframe, time window, timeout, and max generations.
  - [ ] `p4-train-log.txt` records loop output.
  - [ ] `p4-status-snapshots.jsonl` records progress/status snapshots.
  - [ ] Terminal state is exactly one of `completed_training_with_pools_ready` or `blocked_with_timeout_evidence_no_oos`.
  - [ ] If blocked, no P6 OOS files are created except blocker artifacts.

  **QA Scenarios**:
  ```text
  Scenario: P7 training completes
    Tool: powershell
    Steps:
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-p7-observability-bounded-training-20260605/p4-train-config.json --run-id tick_p7_train_2023_2025_observable_20260605
    Expected: Run exits normally; DB has generation rows for the run.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p4-train-log.txt

  Scenario: P7 training exceeds cap
    Tool: powershell
    Steps:
      Enforce 6h wall-clock cap on the owned process/session.
    Expected: Owned process is stopped, blocker is written, no OOS is run.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p4-train-blocked.md
  ```

  **Commit**: NO | Message: n/a | Files: evidence/config only

- [x] 6. P5 - Freeze Candidate Pools And Attach Research Diagnostics

  **What to do**: If P4 completed with generation rows, read only the P4 run rows and apply `select_candidate_research_pool_v2`. Write `p5-candidate-pools.json` with:
  - `selector_version`
  - `config_hash`
  - `policy_hash`
  - `oos_excluded=true`
  - `exploration_pool_v2`
  - `research_pool_v2`
  - `promotion_gate_v2`
  - legacy `promotion_candidate`
  - structural rejections
  - diagnostics labels and insufficiency reasons.

  `promotion_gate_v2` is a named report section. It must not change the existing selector semantics unless tests explicitly cover the schema addition.

  **Must NOT do**: Do not include 2022/2026 OOS fields in candidate ranking. Do not select after OOS.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: P6, P7 | Blocked By: P4

  **References**:
  - Selector: `ai_strategy_loop/controller/_candidate_research_pool_v2.py:52`
  - Artifact writer: `ai_strategy_loop/controller/_candidate_research_pool_artifact.py:20`
  - Diagnostics: `ai_strategy_loop/fitness/promotion_diagnostics.py`
  - Tests: `tests/unit/test_candidate_research_pool_v2.py:61`
  - Previous blocked artifact: `.omo/evidence/tick-research-direction-realignment-20260605/p7-candidate-pools.json`

  **Acceptance Criteria**:
  - [ ] If P4 blocked, `p5-candidate-pools.json` has `status=blocked_not_run` and no OOS fields.
  - [ ] If P4 completed, `p5-candidate-pools.json` includes non-OOS candidate pools and explicit `promotion_gate_v2`.
  - [ ] Any candidate CSV with 2022 or 2026 rows is structurally rejected.
  - [ ] Research Pool can be non-empty even when Promotion Gate is empty.

  **QA Scenarios**:
  ```text
  Scenario: Candidate pool artifact is OOS-blind
    Tool: powershell
    Steps:
      rg -n "oos_2022|oos_2026|seed_2022|seed_2026|ai_2022|ai_2026|post_oos" .omo/evidence/tick-p7-observability-bounded-training-20260605/p5-candidate-pools.json
    Expected: No matches.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p5-oos-blindness-check.txt

  Scenario: Selector tests still pass
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_candidate_research_pool_v2.py tests/unit/test_promotion_diagnostics.py -q
    Expected: Tests pass; schema addition is covered if implemented.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p5-pool-tests.txt
  ```

  **Commit**: YES | Message: `조건연구 P7 후보풀 산출물 확장` | Files: candidate-pool artifact code/tests if schema changes; otherwise evidence only

- [x] 7. P6 - Conditional Fixed 2022/2026 OOS Or Honest Blocker

  **What to do**: Read `p5-candidate-pools.json`.
  - If `promotion_gate_v2.promotion_allowed=true` and frozen identity exists, run fixed seed/AI OOS for 2022 and the available 2026 window.
  - If no promotion candidate exists, write `p6-oos-blocked.md` and `p6-oos-comparison.json` with null OOS rows.

  OOS configs must use frozen buy/sell names, `max_generations=1`, no generation/refinement/reselection, and exact date windows.

  **Must NOT do**: Do not run OOS on multiple Research Pool candidates in this plan. Do not tune after OOS.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: P7 | Blocked By: P5

  **References**:
  - Prior OOS blocker: `.omo/evidence/tick-research-direction-realignment-20260605/p8-oos-blocked.md`
  - Prior OOS comparison pattern: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p6-oos-comparison.md`
  - P9 honesty guard: `.omo/evidence/tick-research-direction-realignment-20260605/p9-decision-card.md`

  **Acceptance Criteria**:
  - [ ] If no promotion candidate exists, no AI OOS run is executed and blocker exists.
  - [ ] If OOS runs, candidate identity before and after OOS is byte-identical.
  - [ ] OOS comparison includes seed/AI 2022 and seed/AI 2026 rows or exact blockers.
  - [ ] Slippage/PBO/DSR promotion status is included.

  **QA Scenarios**:
  ```text
  Scenario: No promotion candidate
    Tool: powershell
    Steps:
      Read p5-candidate-pools.json; verify promotion_gate_v2 denies promotion.
    Expected: p6-oos-blocked.md exists and no fixed AI OOS run rows are created.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p6-oos-blocked.md

  Scenario: Frozen promotion OOS
    Tool: powershell
    Steps:
      Run fixed seed/AI OOS configs only for the frozen candidate.
    Expected: Four rows or blockers; no reselection.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p6-oos-comparison.json
  ```

  **Commit**: NO | Message: n/a | Files: evidence/config only

- [x] 8. P7 - Final Decision Card, Page Progress Table, And Next Command

  **What to do**: Write `p7-decision-card.md` with:
  - Executive verdict
  - Source documents used
  - Observability changes summary
  - Preflight result
  - P7 training result or blocker
  - Candidate pool table
  - Promotion Gate summary
  - OOS result or blocker
  - PBO/DSR/slippage status
  - Human/seed-level claim status
  - Full page progress table
  - Remaining stages and next recommended command

  Verdict enum:
  - `COMPLETED_TRAINING_WITH_POOLS`
  - `BLOCKED_WITH_TIMEOUT_EVIDENCE_NO_OOS`
  - `PROMOTION_CANDIDATE_READY_FOR_OOS`
  - `NEEDS_MORE_EVIDENCE`

  **Must NOT do**: Do not claim human-level, seed-superior, or promotion-ready unless fixed OOS and diagnostics support it.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: Final | Blocked By: P5, P6

  **References**:
  - Current decision pattern: `.omo/evidence/tick-research-direction-realignment-20260605/p9-decision-card.md`
  - Final verification pattern: `.omo/evidence/tick-research-direction-realignment-20260605/final-verification.md`
  - Dashboard final pattern: `.omo/evidence/tick-dashboard-observability-research-ux-20260604/final-verification.md`

  **Acceptance Criteria**:
  - [ ] Decision card includes one verdict enum.
  - [ ] Full progress table covers P0-P7 and Final Verification.
  - [ ] If blocked, the next command targets the exact blocker rather than OOS.
  - [ ] Forbidden action section confirms no `final_approval`, `export_winner`, live broker, V3K, or blanket taskkill.

  **QA Scenarios**:
  ```text
  Scenario: Decision honesty scan
    Tool: powershell
    Steps:
      rg -n "COMPLETED_TRAINING_WITH_POOLS|BLOCKED_WITH_TIMEOUT_EVIDENCE_NO_OOS|PROMOTION_CANDIDATE_READY_FOR_OOS|NEEDS_MORE_EVIDENCE|final_approval|export_winner|KHOPENAPI|taskkill|human-level|seed" .omo/evidence/tick-p7-observability-bounded-training-20260605/p7-decision-card.md
    Expected: Required verdict and guardrails are present.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p7-honesty-audit.txt

  Scenario: Progress table complete
    Tool: powershell
    Steps:
      rg -n "P0|P1|P2|P3|P4|P5|P6|P7|Final" .omo/evidence/tick-p7-observability-bounded-training-20260605/p7-decision-card.md
    Expected: All stages are listed with status and evidence.
    Evidence: .omo/evidence/tick-p7-observability-bounded-training-20260605/p7-progress-table-audit.txt
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

## Final Verification Wave
> ALL must APPROVE. Present consolidated results to user before marking the work done.

- [x] F1. Plan Compliance Audit
  ```powershell
  rg -n "^- \[ \]" .omo/plans/tick-p7-observability-bounded-training-20260605.md
  Get-ChildItem .omo/evidence/tick-p7-observability-bounded-training-20260605
  ```

- [x] F2. Focused Tests
  ```powershell
  $env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_engine_progress_contract.py tests/unit/test_dashboard_chart_explanations.py tests/unit/test_process_timing.py tests/unit/test_dashboard_phase_mapping.py -q
  $env:PYTHONUTF8='1'; python -m pytest tests/unit/test_loop_robustness.py tests/unit/test_warm_session_window.py tests/unit/test_candidate_research_pool_v2.py tests/unit/test_promotion_diagnostics.py -q
  ```

- [x] F3. Guardrail Verification
  ```powershell
  git diff --check
  python scripts/verify_nonrelease_sync.py
  git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
  ```

- [x] F4. Scope Fidelity Check
  - Verify no official engine/hard-gate/backtest_graph/protected path edits.
  - Verify no production export/live/V3K action.
  - Verify P7/P6 artifacts separate research discovery from promotion proof.

## Commit Strategy
- Stage files explicitly; do not use `git add -A`.
- Keep commits small:
  - `조건연구 P7 백테스트 관측성 계약 보강`
  - `조건연구 P7 대시보드 엔진 상태 표시 보강`
  - `조건연구 P7 후보풀 산출물 확장`
- Korean markdown commit bodies must state that official engines, hard gates, protected paths, `final_approval`, and `export_winner` were not touched.

## Success Criteria
- The system can show why a long P7 run is still active, timed out, or blocked.
- The user can see engine settings, timeout, logs, elapsed/remaining/ETA, tick/min, and date/year window before trusting a long run.
- P7 either produces OOS-blind candidate pools or records a blocker with enough detail to fix the next bottleneck.
- No fixed OOS is run unless a frozen promotion candidate exists.
- No human-level or seed-superior claim is made without strict proof.

## Recommended Next Command
```text
$start-work tick-p7-observability-bounded-training-20260605
```

Optional review:

```text
high accuracy review .omo/plans/tick-p7-observability-bounded-training-20260605.md
```
