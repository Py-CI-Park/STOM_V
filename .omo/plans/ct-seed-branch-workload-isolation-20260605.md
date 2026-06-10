# C_T Seed Branch Workload Isolation 20260605

## TL;DR
> **Summary**: Isolate whether the `C_T_900_920_U2_B/S` timeout on `2025-01-03 09:02..09:05` is driven by the buy code, sell code, or their combination by using temporary diagnostic strategy copies and bounded warm/cold preflights.
> **Deliverables**:
> - Safety/Boulder baseline.
> - C_T/control buy-sell branch and DB-copy map.
> - Namespaced diagnostic strategy copy archive and cleanup receipt.
> - Mixed-pair bounded preflight evidence.
> - Decision card, full page progress table, and next command.
> **Effort**: Medium-large
> **Parallel**: YES - static/evidence tasks can run in parallel; runtime probes are sequential.
> **Critical Path**: P0 -> P1/P2 -> P3 -> P4 -> P5/P6 -> P7 -> Final

## Context

### Original Request
Run the recommended next command:

```text
$ulw-plan C_T seed branch workload isolation plan: use .omo/evidence/ct-seed-tick-preflight-repair-20260605/p6-decision-card.md, p4-ct-bounded-preflight.md, p3-same-window-active-control.md, and p2-strategy-timefilter-inspect.md as primary evidence. Isolate which C_T buy/sell branch or condition family causes the 2025-01-03 09:02..09:05 tick timeout by using diagnostic strategy copies and bounded warm/cold preflights only, without editing official backtest engines, hard gates, protected paths, backtest_graph, final_approval/export_winner/live/V3K paths. Keep new toggles default OFF, require CSV+metrics before any January retry, and keep 2023-2025 training plus 2022/2026 OOS blocked until a repaired C_T preflight passes.
```

### Evidence Summary
- Previous page verdict: `CT_SEED_WINDOW_BLOCKER`.
- Same-window active control `Tick_B_902_905_Update_2/S` passed on `2025-01-03 09:02..09:05`.
- C_T warm and cold runs on the same window loaded covered data but timed out or returned no CSV/metrics.
- The current page must not expand to January retry, 2023-2025 training, or 2022/2026 OOS until a repaired C_T preflight passes.

## Work Objectives

### Core Objective
Create temporary diagnostic copies of the C_T and control buy/sell strategies, run bounded mixed-pair preflights on `2025-01-03 09:02..09:05`, and decide whether the timeout is isolated to C_T buy, C_T sell, both, or an unresolved engine/runtime interaction.

### Deliverables
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p0-safety-baseline.md`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p1-branch-static-map.md`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p2-diagnostic-copy-map.md`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p3-mixed-pair-preflights.md`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p4-runtime-log-review.md`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p5-decision-card.md`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p6-next-command.md`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/final-verification.md`

### Definition Of Done
- No official engine, hard gate, `backtest/graph`, protected runtime path, export, live, V3K, long training, or OOS violation.
- Diagnostic strategy rows are namespaced, archived, and cleaned from the loop strategy DB after runtime evidence is captured.
- At least two mixed-pair preflights are attempted or explicitly blocked:
  - C_T buy + control sell.
  - control buy + C_T sell.
- Each runtime attempt records run id, buy/sell names, config, timeout fields, stdout/stderr paths, status, CSV/metrics availability, and cleanup status.
- Decision uses one of:
  - `CT_BUY_BRANCH_WORKLOAD`
  - `CT_SELL_BRANCH_WORKLOAD`
  - `CT_BUY_AND_SELL_WORKLOAD`
  - `DIAGNOSTIC_COPY_UNSAFE`
  - `INCONCLUSIVE_ENGINE_INTERACTION`

### Must Have
- Use existing `ai_strategy_loop/scripts/tick_seed_timeout_probe.py` where possible.
- Runtime evidence output must stay under `.omo/evidence/ct-seed-branch-workload-isolation-20260605/`.
- Passing preflight requires `status=success` or equivalent ok result plus CSV path and metrics present.
- Static line/branch facts are clues only; runtime mixed-pair evidence decides the axis.

### Must NOT Have
- No edits to `backtest/backengine_*.py`, `backtest/back_static.py`, `ai_strategy_loop/fitness/score.py`, or `backtest/graph`.
- No `final_approval`, `export_winner`, KHOPENAPI/live broker, V3K gate, blanket `taskkill`.
- No 2023-2025 training or 2022/2026 OOS in this page.
- No human-level, seed-superior, or OOS performance claim.
- Do not stage or commit runtime DB/CSV/log artifacts.

## Verification Strategy
Focused commands:

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py tests/unit/test_warm_session_window.py tests/unit/test_dashboard_engine_progress_contract.py -q
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_runner_helpers.py::test_runner_attaches_protocol_diagnostics_on_timeout tests/unit/test_runner_helpers.py::test_runner_records_timeout_checkpoint_fields -q
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json
```

## TODOs

- [x] P0 - Safety Baseline And Resume Boundary

  **What to do**: Capture branch, HEAD, dirty status, protected path status, Boulder state, current diagnostic process state, and previous page evidence links.

  **Acceptance Criteria**:
  - [x] `p0-safety-baseline.md` records HEAD/branch/dirty/protected/process state.
  - [x] Boulder active work is set to this plan before runtime probes.
  - [x] Unowned conflicting runtime process blocks P3 instead of being killed.

- [x] P1 - Branch Static Map

  **What to do**: Inspect C_T/control buy/sell code from the loop DB via the same strategy-read path. Record code hashes, line counts, `self.Buy`/`self.Sell`, and C_T time branch ranges. Label static facts as `static_hint`.

  **Acceptance Criteria**:
  - [x] `p1-branch-static-map.md` records C_T and control code facts.
  - [x] The `09:02..09:05` active C_T buy branch is identified as a static hint, not runtime proof.

- [x] P2 - Diagnostic Copy Map

  **What to do**: Create namespaced temporary strategy rows copied from original C_T/control rows:
  - `CT_DIAG_CTB_902905_20260605`
  - `CT_DIAG_CTS_902905_20260605`
  - `CT_DIAG_CTLB_902905_20260605`
  - `CT_DIAG_CTLS_902905_20260605`
  Archive copied code hashes and row presence under evidence, then clean the rows after runtime probes.

  **Acceptance Criteria**:
  - [x] Copy archive JSON records original and diagnostic names, tables, hashes, and line counts.
  - [x] No official/protected source file is edited.

- [x] P3 - Mixed-Pair Bounded Preflights

  **What to do**: Run bounded warm preflights on `2025-01-03 09:02..09:05`:
  - `CT_DIAG_CTB_902905_20260605` + `CT_DIAG_CTLS_902905_20260605`
  - `CT_DIAG_CTLB_902905_20260605` + `CT_DIAG_CTS_902905_20260605`
  Optionally run cold comparison only if warm evidence is contradictory or ambiguous.

  **Acceptance Criteria**:
  - [x] Runtime evidence records status, timeout, elapsed, stdout/stderr, CSV/metrics availability, and cleanup.
  - [x] No January retry, long training, or OOS is started.

- [x] P4 - Runtime Log Review

  **What to do**: Review stdout/stderr and probe JSON to extract the first meaningful checkpoint: data load, backtest process start, CSV/metrics path, timeout, cleanup, or return code.

  **Acceptance Criteria**:
  - [x] `p4-runtime-log-review.md` summarizes checkpoints without overclaiming.
  - [x] If a mixed pair passes, its CSV+metrics are explicitly cited.

- [x] P5 - Decision Card

  **What to do**: Decide which workload axis is implicated and record blocked/unblocked next steps.

  **Acceptance Criteria**:
  - [x] `p5-decision-card.md` contains verdict, evidence table, full page progress, and blocked claims.

- [x] P6 - Next Command

  **What to do**: Write the exact next recommended `$ulw-plan` or `$start-work` command based on P5.

  **Acceptance Criteria**:
  - [x] `p6-next-command.md` contains one actionable command and explains why it is next.

- [x] Final - Verification And Cleanup

  **What to do**: Run focused tests and nonrelease/protected checks. Confirm diagnostic rows were cleaned or explicitly documented if intentionally retained.

  **Acceptance Criteria**:
  - [x] Final verification evidence exists.
  - [x] Boulder work status is completed.
  - [x] Final answer includes page progress and next command.
