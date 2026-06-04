# TICK OOS Dashboard Validation 20260604

## TL;DR
> **Summary**: Run the next TICK toggles-ON research/OOS validation loop using the upgraded research dashboard as the observation and evidence surface. This plan starts from the completed dashboard upgrade, treats the prior `tick-oos-validation-20260603` result as `REJECT_CANDIDATE`, and produces a new decision card without touching engines, hard gates, protected paths, live broker code, or export/approval boundaries.
> **Deliverables**:
> - Safety snapshot and current-code dashboard smoke evidence
> - TICK toggles-ON smoke config/run evidence
> - 2023~2025 training/research run evidence
> - Dashboard Research Lab analysis bundle: variable correlation, edge ratio, feature importance, strategy diff, prompts, AI context pack
> - Fixed 2022/2026 OOS seed-vs-AI comparison
> - Slippage/overfit/PBO-DSR status and final decision card
> - Final verification and scope-fidelity evidence
> **Effort**: XL
> **Parallel**: Limited. Safety/dashboard checks can run in parallel; official loop runs are serialized.

## Context
### Current State
- Existing plans are complete: `condition-research-rereview-20260603`, `tick-oos-validation-20260603`, and `tick-research-dashboard-upgrade-20260603`.
- Prior OOS verdict is `REJECT_CANDIDATE` in `.omo/evidence/tick-oos-validation-20260603/p5-decision-card.md`.
- Dashboard upgrade is complete. Final evidence says current code passed on owned port `8798`, but pre-existing `8770` was stale and must be restarted to expose new read-only APIs.
- Hand-off docs name the next objective: TICK toggles-ON multiyear research run and 2022/2026 OOS split validation.
- This plan is a fresh 2026-06-04 rerun/validation pass. Prior `tick-oos-validation-20260603` evidence is a baseline prior, not the final result for this plan.

### Ground Truth
- Seed reference: `Tick_B_902_905_Update_2` / `Tick_S_902_905_Update_2`.
- TICK data window: 09:00~09:30; seed OOS configs use 09:00~09:28 templates.
- `run_tickwide_config.json` is the short toggles-ON template.
- Human-level, seed-superior, or promotion claims require fresh OOS evidence and slippage-stressed support.

## Work Objectives
### Core Objective
Use the upgraded dashboard/research APIs to execute and audit a fresh TICK toggles-ON research/OOS validation sequence, then honestly classify the result as `PROMOTE_CANDIDATE`, `REJECT_CANDIDATE`, or `NEEDS_MORE_EVIDENCE`.

### Must Have
- Current-code dashboard verification before relying on new endpoints.
- Official loop/backtest execution only; no manual runtime DB edits.
- Evidence/runtime-only scope by default: do not patch dashboard/source code in this plan. If a code defect blocks execution, stop and document `NEEDS_CODE_FIX` instead of silently changing source.
- Fixed candidate selection before OOS.
- Separate 2022 and 2026 OOS; no OOS-informed reselection.
- Dashboard analysis evidence from `/variable_correlation`, `/edge_ratio`, `/feature_importance`, `/strategy_diff`, `/prompts`, `/research_docs`, and `/ai_context_pack`.
- Final verification: `git diff --check`, `python scripts/verify_nonrelease_sync.py`, protected-path git status, focused pytest suite.

### Must NOT Have
- No edits to `backtest/backengine_*.py`, `backtest/back_static.py`, `ai_strategy_loop/fitness/score.py` hard gates, or `backtest/graph/`.
- No `final_approval`, no `export_winner`, no production strategy DB writes.
- No V3K gate advancement, USER_ACK creation, KHOPENAPI login/connect, or live order wiring.
- No blanket `taskkill`; stop only owned PIDs/sessions.
- No claim of human-level or seed-superior performance unless the decision rule passes.

## Verification Strategy
- Evidence root: `.omo/evidence/tick-oos-dashboard-validation-20260604/`
- Use `PYTHONUTF8=1`.
- Prefer owned dashboard port `8799` if `8770` is stale or cannot be restarted safely. Stale detection must probe new routes, not only `/health`.
- For long loop runs, capture start/end timestamps, PID/session id, config, stdout/stderr, run_state, and cleanup receipt.
- Every task records applicable ultraqa classes in `.omo/start-work/ledger.jsonl`.
- Official runtime may update generated `ai_strategy_loop/state/*.db`; manual DB edits are forbidden. Protected-path git status must still be captured before and after.
- If P2/P3 cannot produce a pre-OOS candidate, skip P5 OOS execution and write `NEEDS_MORE_EVIDENCE` or `REJECT_CANDIDATE` with exact blocker evidence.

## TODOs

- [x] 1. P0 safety snapshot and plan activation

  **What to do**: Create the evidence root. Capture branch, HEAD, dirty state, protected-path status, Boulder state, completed prior-plan status, prior P5 verdict, and current dashboard status. Confirm this plan is the active Boulder work before execution proceeds.
  **Must NOT do**: Do not clean the dirty worktree. Do not stop any existing dashboard process.

  **Acceptance Criteria**:
  - [ ] `p0-safety-snapshot.txt` records branch, HEAD, dirty status, protected-path status, Boulder state, prior verdict, and 8770 health/new-API state.
  - [ ] `p0-plan-selection.txt` records that all older plans are complete and this plan was selected.
  - [ ] Protected-path git status is empty or explicitly pre-existing and unrelated.

  **QA Scenarios**:
  ```text
  Scenario: Safety snapshot
    Tool: powershell
    Steps:
      New-Item -ItemType Directory -Force .omo/evidence/tick-oos-dashboard-validation-20260604
      git status --short --branch
      git rev-parse HEAD
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      Get-Content .omo/boulder.json
      Get-Content .omo/evidence/tick-oos-validation-20260603/p5-decision-card.md
    Expected: Evidence files exist and no protected-path changes are introduced.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/p0-safety-snapshot.txt
  ```

  **Commit**: NO

- [x] 2. P1 current-code dashboard readiness

  **What to do**: Verify whether `http://127.0.0.1:8770` serves upgraded backend APIs. If stale, start an owned dashboard on `127.0.0.1:8799`, record PID, and use that base URL for this plan's dashboard QA. Do not stop the pre-existing 8770 process unless the user has explicitly provided its ownership and asked to restart it.
  **Must NOT do**: Do not use `taskkill`. Do not click approval/export controls.

  **Acceptance Criteria**:
  - [ ] `p1-dashboard-smoke.json` has HTTP 200/readable payloads for `/health`, `/ui/`, `/runs`, `/run_state`, `/variable_correlation`, `/edge_ratio`, `/feature_importance`, `/strategy_diff`, `/prompts`, `/research_docs`, and `/ai_context_pack` on the selected base URL.
  - [ ] `p1-dashboard-base.txt` records the selected base URL for later tasks.
  - [ ] If an owned server is spawned, `p1-dashboard-pid.txt` and cleanup receipt identify only that owned PID/session.
  - [ ] 8770 stale state, if present, is recorded honestly.

  **QA Scenarios**:
  ```text
  Scenario: Dashboard API smoke
    Tool: powershell + curl.exe
    Steps:
      curl.exe -sS http://127.0.0.1:8770/health
      curl.exe -sS http://127.0.0.1:8770/variable_correlation?run_id=<known_run>
      If 404/stale, start: python -m ai_strategy_loop --host 127.0.0.1 --port 8799
      curl.exe -sS http://127.0.0.1:8799/health
      curl.exe -sS "http://127.0.0.1:8799/ai_context_pack?run_id=<known_run>&gen_no=0"
    Expected: Selected base URL exposes upgraded APIs; no approval/export action invoked.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/p1-dashboard-smoke.json
  ```

  **Commit**: NO

- [x] 3. P2 short TICK toggles-ON reproduction run

  **What to do**: Build `p2-smoke-config.json` from `ai_strategy_loop/state/run_tickwide_config.json`, explicitly setting `segment_feedback_enabled=true`, `segment_feedback_min_count=8`, `prompt_logging_enabled=true`, `equity_points_enabled=true`, `max_generations=2`, `bt_full_start=20250408`, `bt_full_end=20250430`, `bt_timeframe="tick"`, and `bt_universe_start_time=90000`, `bt_universe_end_time=93000`. Run id: `tick_oos_dash_p2_smoke_20260604`.
  **Must NOT do**: Do not reduce gates or change engines to force success. Do not write outside evidence/config/runtime state produced by the official loop.

  **Acceptance Criteria**:
  - [ ] `p2-smoke-config.json` contains the exact toggles and dates above.
  - [ ] `p2-smoke-log.txt` records official loop execution and exit status.
  - [ ] `p2-smoke-api.json` captures `/run_state`, `/backtest_detail`, `/variable_correlation`, `/edge_ratio`, `/feature_importance`, `/strategy_diff`, `/prompts`, and `/ai_context_pack`.
  - [ ] Any failure is recorded with exact exit/log evidence, not softened.

  **QA Scenarios**:
  ```text
  Scenario: Short smoke run
    Tool: powershell
    Steps:
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-oos-dashboard-validation-20260604/p2-smoke-config.json --run-id tick_oos_dash_p2_smoke_20260604
      curl.exe -sS "<base>/run_state?run_id=tick_oos_dash_p2_smoke_20260604"
      curl.exe -sS "<base>/ai_context_pack?run_id=tick_oos_dash_p2_smoke_20260604&gen_no=0"
    Expected: Run exits or fails with captured evidence; dashboard can inspect it.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/p2-smoke-log.txt
  ```

  **Commit**: NO

- [x] 4. P3 2023~2025 toggles-ON multiyear training run

  **What to do**: Build `p3-train-config.json` from P2 config with `bt_full_start=20230101`, `bt_full_end=20251231`, `max_generations=6`, `bt_timeout=900`, `bt_warm_run_timeout=300`, `prompt_logging_enabled=true`, `equity_points_enabled=true`, and the same TICK 09:00~09:30 toggles. Run id: `tick_oos_dash_p3_train_2023_2025_20260604`.
  **Must NOT do**: Do not use OOS years to tune. Do not change the candidate after P4 OOS. Do not weaken hard gates.

  **Acceptance Criteria**:
  - [ ] `p3-train-log.txt` records run execution, duration, and exit status.
  - [ ] `p3-selected-candidate.json` selects the highest completed pre-OOS generation by graded score, with buy/sell names, gen_no, gate status, profit, MDD, trades, and selection timestamp.
  - [ ] Candidate selection rule explicitly excludes OOS results and uses only `tick_oos_dash_p3_train_2023_2025_20260604`.
  - [ ] If the run fails due OOM/timeout, `p3-resource-blocker.md` records the blocker and selected-candidate is either absent or marked unavailable.

  **QA Scenarios**:
  ```text
  Scenario: Multiyear training run
    Tool: powershell
    Steps:
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-oos-dashboard-validation-20260604/p3-train-config.json --run-id tick_oos_dash_p3_train_2023_2025_20260604
      curl.exe -sS "<base>/run_state?run_id=tick_oos_dash_p3_train_2023_2025_20260604"
    Expected: Completed generations or exact blocker evidence; candidate selected before OOS only.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/p3-selected-candidate.json
  ```

  **Commit**: NO

- [x] 5. P4 dashboard research analysis and feedback audit

  **What to do**: Use the upgraded dashboard APIs on the P3 run to capture variable correlation, edge ratio, feature importance, strategy diff, prompts, research docs, and AI context pack. Produce `p4-analysis.md` summarizing losing segments, variable signals, prompt/segment-feedback evidence, and whether another training run is justified. Do not start another training run unless this plan is updated first.
  **Must NOT do**: Do not make promotion claims from P3 training. Do not execute AI/network calls from the dashboard.

  **Acceptance Criteria**:
  - [ ] `p4-analysis.json` captures API payloads or exact unavailable reasons.
  - [ ] `p4-analysis.md` names top losing/winning segments, top correlations/features, prompt count/status, current strategy diff availability, and AI context summary.
  - [ ] Segment-feedback injection is classified as `observed`, `not_observed`, or `unavailable` with evidence.

  **QA Scenarios**:
  ```text
  Scenario: Research Lab API bundle
    Tool: curl.exe
    Steps:
      curl.exe -sS "<base>/variable_correlation?run_id=tick_oos_dash_p3_train_2023_2025_20260604&method=spearman"
      curl.exe -sS "<base>/edge_ratio?run_id=tick_oos_dash_p3_train_2023_2025_20260604&fine_time=true"
      curl.exe -sS "<base>/feature_importance?run_id=tick_oos_dash_p3_train_2023_2025_20260604&axis=change&fine_time=true"
      curl.exe -sS "<base>/prompts?run_id=tick_oos_dash_p3_train_2023_2025_20260604"
      curl.exe -sS "<base>/ai_context_pack?run_id=tick_oos_dash_p3_train_2023_2025_20260604&gen_no=<selected_gen>"
    Expected: Payloads captured; unavailable data is explicit.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/p4-analysis.json
  ```

  **Commit**: NO

- [x] 6. P5 fixed 2022/2026 OOS seed-vs-AI comparison

  **What to do**: Build fixed OOS configs for seed and selected AI candidate. Seed configs derive from `run_ens_seed_2022full_config.json` and `run_ens_seed_2026full_config.json`. AI configs use the exact P3 selected buy/sell names, `bt_refine_from_best=false`, `max_generations=1`, TICK timeframe, 09:00~09:30, and OOS dates 2022 plus available 2026 window. Produce `p5-oos-comparison.json` and `p5-oos-comparison.md`.
  **Must NOT do**: Do not reselect after OOS. Do not tune on 2022/2026. Do not call export/final approval.

  **Acceptance Criteria**:
  - [ ] If `p3-selected-candidate.json` is unavailable or marked blocked, P5 writes `p5-oos-blocked.md` and does not fabricate OOS rows.
  - [ ] Four OOS rows exist or each missing row has exact blocker reason: seed_2022, seed_2026, ai_2022, ai_2026.
  - [ ] Candidate identity in P5 matches `p3-selected-candidate.json`.
  - [ ] Superiority rule is predeclared: AI must be positive in both OOS years, combined AI profit >= combined seed profit, combined AI MDD <= combined seed MDD, and trade/holding profile must be within or justified against human-reference corridor.
  - [ ] `p5-oos-comparison.md` states whether the rule passed.

  **QA Scenarios**:
  ```text
  Scenario: Fixed OOS execution/capture
    Tool: powershell
    Steps:
      Run or capture fixed OOS runs:
        tick_oos_dash_p5_seed_2022_20260604
        tick_oos_dash_p5_seed_2026_20260604
        tick_oos_dash_p5_ai_2022_20260604
        tick_oos_dash_p5_ai_2026_20260604
      Compare selected buy/sell before and after OOS.
    Expected: OOS evidence exists and candidate was not changed post-OOS.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/p5-oos-comparison.json
  ```

  **Commit**: NO

- [x] 7. P6 slippage, overfit, and final decision card

  **What to do**: Create `p6-decision-card.md` with Executive Verdict, Candidate Identity, Training Evidence, Dashboard Analysis, OOS Evidence, Seed Comparison, Human Reference Corridor, Overfit Risk, PBO/DSR Status, Slippage/Execution Stress, Forbidden Actions Check, and Final Verdict.
  **Must NOT do**: Do not promote if P5 superiority rule fails or slippage-stressed OOS is not positive in both OOS years.

  **Acceptance Criteria**:
  - [ ] Final verdict is one of `PROMOTE_CANDIDATE`, `REJECT_CANDIDATE`, or `NEEDS_MORE_EVIDENCE`.
  - [ ] If `PROMOTE_CANDIDATE`, it cites P5 rule pass and slippage-stressed positive OOS in both 2022 and 2026.
  - [ ] If PBO/DSR is unavailable, it is an explicit advisory blocker or `NEEDS_MORE_EVIDENCE` factor.
  - [ ] No human-level/superior claim appears without OOS and slippage support.

  **QA Scenarios**:
  ```text
  Scenario: Decision card honesty audit
    Tool: rg + powershell
    Steps:
      rg -n "PROMOTE_CANDIDATE|REJECT_CANDIDATE|NEEDS_MORE_EVIDENCE|human-level|초월|능가" .omo/evidence/tick-oos-dashboard-validation-20260604/p6-decision-card.md
      Verify any positive claim cites P5 and slippage sections.
    Expected: Verdict is evidence-bound; no unsupported promotion language.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/p6-decision-card.md
  ```

  **Commit**: NO

## Final Verification Wave

- [x] F1. Plan compliance audit

  **What to do**: Re-read this plan and every artifact under `.omo/evidence/tick-oos-dashboard-validation-20260604/`. Confirm every top-level task has evidence and forbidden actions are absent.

  **Acceptance Criteria**:
  - [ ] `final-plan-compliance.txt` maps tasks 1-7 and F1-F4 to evidence artifacts.
  - [ ] It records whether `final_approval`, `export_winner`, `USER_ACK`, `KHOPENAPI`, or `taskkill` occurred.

  **QA Scenarios**:
  ```text
  Scenario: Compliance audit
    Tool: powershell + rg
    Steps:
      rg -n "^- \\[ \\]" .omo/plans/tick-oos-dashboard-validation-20260604.md
      Get-ChildItem .omo/evidence/tick-oos-dashboard-validation-20260604
      rg -n "final_approval|export_winner|USER_ACK|KHOPENAPI|taskkill" .omo/evidence/tick-oos-dashboard-validation-20260604
    Expected: Only current final-wave unchecked items before completion; forbidden terms appear only as guardrail/negative evidence.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/final-plan-compliance.txt
  ```

- [x] F2. Code and branch safety verification

  **What to do**: Run final verification commands without modifying source files.

  **Acceptance Criteria**:
  - [ ] `final-verification.txt` contains `git diff --check`, `python scripts/verify_nonrelease_sync.py`, protected-path status, and focused pytest output.
  - [ ] Protected path status is empty or explicitly pre-existing and unrelated.

  **QA Scenarios**:
  ```text
  Scenario: Final verification
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      git diff --check
      python scripts/verify_nonrelease_sync.py
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      python -m pytest tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_equity_curves.py tests/unit/test_dashboard_profit_codeview.py tests/unit/test_dashboard_run_state.py tests/unit/test_prompt_logging.py tests/unit/test_edge_ratio.py tests/unit/test_feature_importance.py tests/unit/test_adaptive_timing.py tests/unit/test_dashboard_hall_of_fame.py tests/unit/test_variable_correlation.py tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_research_docs.py tests/unit/test_dashboard_ai_context_pack.py tests/unit/test_dashboard_research_lab_frontend.py tests/unit/test_dashboard_strategy_prompt_frontend.py tests/unit/test_dashboard_run_compare_frontend.py tests/unit/test_dashboard_chart_explanations.py tests/unit/test_dashboard_wiki_frontend.py tests/unit/test_dashboard_integrated_layout.py tests/unit/test_dashboard_table_sorting.py tests/unit/test_dashboard_runs_enriched.py tests/unit/test_dashboard_current_gen_detail.py -q
    Expected: Commands pass or exact unrelated/pre-existing failures are recorded.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/final-verification.txt
  ```

- [x] F3. Real dashboard QA

  **What to do**: Exercise the selected current-code dashboard base URL from P1. Capture `/ui/`, `/runs`, `/run_state`, `/variable_correlation`, `/edge_ratio`, `/feature_importance`, `/strategy_diff`, `/prompts`, `/research_docs`, `/ai_context_pack`, and if possible `/runs/compare` for OOS rows.

  **Acceptance Criteria**:
  - [ ] `final-dashboard-qa.txt` records exact URLs, statuses, selected base URL, and cleanup receipt for any owned server.
  - [ ] No approval/export action is invoked.

  **QA Scenarios**:
  ```text
  Scenario: Real dashboard QA
    Tool: curl.exe
    Steps:
      curl.exe -sS "<base>/ui/"
      curl.exe -sS "<base>/runs"
      curl.exe -sS "<base>/ai_context_pack?run_id=tick_oos_dash_p3_train_2023_2025_20260604&gen_no=<selected_gen>"
    Expected: Current-code dashboard is usable for the final evidence set.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/final-dashboard-qa.txt
  ```

- [x] F4. Scope fidelity and final handoff

  **What to do**: Record final git status, protected-path status, final verdict, dashboard base URL caveat, and recommended next command.

  **Acceptance Criteria**:
  - [ ] `final-scope-fidelity.txt` includes final `git status --short --branch`, protected-path status, final verdict from P6, and statement that this is research validation, not production promotion.
  - [ ] `.omo/boulder.json` is marked completed when all checkboxes are done.

  **QA Scenarios**:
  ```text
  Scenario: Scope fidelity
    Tool: powershell + rg
    Steps:
      git status --short --branch
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      rg -n "Final Verdict|PROMOTE_CANDIDATE|REJECT_CANDIDATE|NEEDS_MORE_EVIDENCE" .omo/evidence/tick-oos-dashboard-validation-20260604/p6-decision-card.md
    Expected: Final state and verdict are explicit; protected paths untouched.
    Evidence: .omo/evidence/tick-oos-dashboard-validation-20260604/final-scope-fidelity.txt
  ```

## Commit Strategy
- Commit: NO by default during `$start-work`; user can request a commit after review.
- If committing later, stage files explicitly and use Korean commit title/body.

## Success Criteria
- The fresh run sequence either produces an honestly superior candidate or rejects/blocks it with concrete evidence.
- Dashboard research APIs are used as first-class evidence, not just visual decoration.
- The result is safe to hand off: no source-engine changes, no protected-path source edits, no live/export actions, and all owned QA resources cleaned up.
