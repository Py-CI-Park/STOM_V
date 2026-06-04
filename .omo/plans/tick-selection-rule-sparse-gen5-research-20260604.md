# TICK Selection Rule Sparse Gen5 Research 20260604

## TL;DR
> **Summary**: Improve the TICK candidate-selection rule after the 2026-06-04 OOS rejection, then run a fresh selector-frozen 2023~2025 research pass and fixed 2022/2026 OOS comparison. The plan treats prior P3 gen5 as a hypothesis source only, not proof. No OOS-after-the-fact reselection, no hard-gate weakening, no official engine edits, no `backtest/graph/`, and no production export/approval actions are allowed.
> **Deliverables**:
> - Safety snapshot and canonical-evidence reread
> - Versioned predeclared selector spec: `sparse_positive_v1`
> - Optional pure selector helper/tests if source support is needed
> - Prior-run replay artifact proving selector mechanics only
> - Fresh 2023~2025 selector-frozen train/research run
> - Fixed selected-candidate artifact written before OOS
> - 2022/2026 seed-vs-AI OOS comparison
> - Slippage/PBO/DSR status and final decision card
> **Effort**: XL
> **Parallel**: Limited. Exploration, tests, and dashboard probes can run in parallel; official loop/backtest runs are serialized.

## Context
### Current State
- Canonical handoff: `docs/AGENT_HANDOFF.md`.
- Prior detailed handoff: `docs/update_log/2026-06-03_tick_program_complete_handoff.md`.
- Prior dashboard/OOS validation plan: `.omo/plans/tick-oos-dashboard-validation-20260604.md`.
- Prior final verdict: `.omo/evidence/tick-oos-dashboard-validation-20260604/p6-decision-card.md` says `REJECT_CANDIDATE`.
- Prior P3 selected candidate: gen4 from `tick_oos_dash_p3_train_2023_2025_20260604`, selected by highest pre-OOS graded score, but training profit was negative and `gate_passed=false`.
- Prior P3 gen5: sparse-positive training candidate with positive profit, low MDD, 99 trades, and `daily_avg_trades 0.1 < min_daily_trades 0.3`; it was not selected under the declared P3 graded-score rule.
- Prior P5 OOS result: selected AI gen4 failed superiority, with combined AI profit `-405,285` vs seed `+2,032,445` and AI max MDD `16.77` vs seed max MDD `15.63`.

### Ground Truth
- Prior-run replay can validate selector mechanics only. It cannot support efficacy, promotion, or human-superiority claims because it is being inspected after the prior P5 failure is known.
- Any new candidate must be selected and frozen before touching 2022/2026 OOS.
- The hard graduation gate remains `ai_strategy_loop/fitness/score.py::compute_fitness`. Sparse selection is a research candidate-selection rule, not a hard-gate pass, promotion, or winner export.
- Current loop best tracking in `ai_strategy_loop/controller/loop.py` uses `graded.graded`; dashboard/lineage views are reporting layers. Do not silently redefine existing `best`/`winner` labels.

## Work Objectives
### Core Objective
Create and execute a predeclared, OOS-blind TICK candidate-selection rule that avoids choosing training-negative candidates when a low-risk sparse-positive candidate exists, then evaluate the fixed selected candidate against the seed on 2022/2026 OOS without reselection.

### Must Have
- Evidence root: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/`.
- Use `PYTHONUTF8=1`.
- Selector rule version fixed as `sparse_positive_v1` before fresh OOS.
- Selector freeze artifact before OOS with all inputs, rejections, config hash, selected gen, buy/sell, timestamp, and `oos_excluded=true`.
- Prior-run replay labeled `diagnostic_only`.
- Fresh 2023~2025 train/research candidate selected before OOS.
- OOS pass rule includes both return quality and evidence sufficiency; sparse two-trade OOS profit is not enough for promotion.
- Final verdict is exactly one of `PROMOTE_CANDIDATE`, `REJECT_CANDIDATE`, or `NEEDS_MORE_EVIDENCE`.

### Must NOT Have
- No edits to `backtest/backengine_*.py`, `backtest/back_static.py`, `ai_strategy_loop/fitness/score.py` hard gates, or `backtest/graph/`.
- No `final_approval`, no `export_winner`, no production strategy DB writes.
- No V3K gate advancement, USER_ACK creation, KHOPENAPI login/connect, or live order wiring.
- No blanket `taskkill`; stop only owned PIDs/sessions.
- No OOS-after-the-fact candidate change.
- No human-level, seed-superior, or promotion claim unless all declared OOS, slippage, and evidence-sufficiency rules pass.

## Predeclared Selector: `sparse_positive_v1`
### Inputs
- Training generations only from one declared run id.
- Fields allowed: `gen_no`, `status`, `score`/`graded_score`, `gate_passed`, `gate_reason`, `profit`, `total_profit_pct`, `mdd`, `trade_count`, `daily_avg_trades`, `payoff_ratio`, `max_hold_count`, `buy_name`, `sell_name`.
- Fields forbidden: any 2022/2026 OOS metrics, slippage-stress outputs, final decision-card verdicts, or post-OOS analysis.

### Eligibility
- Candidate must have `status == "ok"`.
- Candidate must have non-empty `buy_name` and `sell_name`.
- Reject if `profit <= 0`.
- Reject if `mdd > 10.0`.
- Reject if `trade_count < 20` or `trade_count > 250`.
- Reject if `daily_avg_trades < 0.05`.
- Reject if `payoff_ratio < 1.05`, unless payoff is missing/unavailable and the missingness is recorded.
- Reject if the only available metrics are incomplete enough to hide profit, MDD, trade count, or strategy identity.

### Buckets and Ranking
- Bucket A, `hard_gate_positive`: `gate_passed=true`, `profit>0`, and all eligibility checks pass.
- Bucket B, `sparse_positive`: `gate_passed=false`, all eligibility checks pass, and `gate_reason` is exactly a daily-frequency failure such as `daily_avg_trades < min_daily_trades`. Mixed failures involving profit, MDD, TPI, timeout, missing CSV, or validation errors do not qualify.
- Bucket A outranks Bucket B.
- Within a bucket, rank by:
  1. Higher `profit / max(mdd, 1.0)`
  2. Lower `mdd`
  3. Higher `trade_count`, capped at 150 for tie scoring
  4. Higher `payoff_ratio`
  5. Lower `gen_no` for deterministic tie-break
- If no candidate qualifies, write a blocked selector artifact and skip OOS.

### Selector Artifact Schema
Write `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/<phase>-selected-candidate.json` with:
- `selector_version`
- `run_id`
- `config_path`
- `config_hash`
- `selected`
- `blocked`
- `blocker`
- `selected_bucket`
- `gen_no`
- `buy_name`
- `sell_name`
- all selected metrics listed above
- `selection_timestamp`
- `oos_excluded: true`
- `diagnostic_only` when replaying prior P3
- `eligible_candidates`
- `rejected_candidates` with machine-checkable reasons
- `forbidden_oos_fields_present: false`

## TODOs

- [x] 1. P0 safety snapshot and canonical reread

  **What to do**: Create the evidence root. Capture branch, HEAD, dirty worktree, protected-path status, Boulder state, active dashboard status, and the prior `REJECT_CANDIDATE` evidence. Reread the canonical docs/evidence named above.
  **Must NOT do**: Do not clean the dirty worktree. Do not stop existing dashboard processes.

  **Acceptance Criteria**:
  - [ ] `p0-safety-snapshot.txt` records branch, HEAD, dirty state, protected paths, Boulder state, dashboard base status, and current date/time.
  - [ ] `p0-canonical-inputs.txt` records the exact canonical files read and the prior verdict facts.
  - [ ] Protected-path status is empty or explicitly pre-existing/unrelated.

  **QA Scenarios**:
  ```text
  Scenario: Safety snapshot
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      New-Item -ItemType Directory -Force .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604
      git status --short --branch
      git rev-parse HEAD
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      Get-Content .omo/boulder.json
      Get-Content docs/AGENT_HANDOFF.md
      Get-Content .omo/evidence/tick-oos-dashboard-validation-20260604/p6-decision-card.md
    Expected: Evidence root exists and no protected path is modified.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p0-safety-snapshot.txt
  ```

  **Commit**: NO

- [x] 2. P1 predeclare `sparse_positive_v1`

  **What to do**: Write the selector spec as executable research policy before any fresh OOS. Include exact thresholds, bucket/ranking logic, OOS field exclusion, artifact schema, and final promotion blockers.
  **Must NOT do**: Do not use any new OOS results to tune thresholds after this step.

  **Acceptance Criteria**:
  - [ ] `p1-selector-spec.md` contains the same rule as this plan or a stricter version, with no OOS-informed edits.
  - [ ] `p1-selector-spec.json` contains machine-readable thresholds and ranking keys.
  - [ ] `p1-oos-blindness-check.txt` records that 2022/2026 candidate metrics are excluded from selector inputs.

  **QA Scenarios**:
  ```text
  Scenario: Selector predeclaration
    Tool: powershell + rg
    Steps:
      rg -n "sparse_positive_v1|oos_excluded|daily_avg_trades|mdd|trade_count" .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p1-selector-spec.md
    Expected: Selector thresholds and forbidden OOS fields are explicit before P4/P5.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p1-selector-spec.md
  ```

  **Commit**: NO

- [x] 3. P2 implement or script pure selector support

  **What to do**: If existing tooling cannot produce the selector artifact exactly, add the smallest read-only selector support. Preferred source boundary is a pure helper such as `ai_strategy_loop/controller/candidate_selection.py` plus a small evidence script, without changing hard gates or engine code. Keep existing `best`/`winner` dashboard labels unchanged unless a new explicit `selected_candidate` view is added.
  **Must NOT do**: Do not edit `compute_fitness` to relax the hard gate. Do not mutate runtime DB rows manually.

  **Acceptance Criteria**:
  - [ ] If code changes are made, `tests/unit/test_candidate_selection.py` covers gen4 training-negative rejection, gen5 sparse-positive eligibility, mixed-failure rejection, gate-passed-positive priority, OOS-field rejection, and deterministic ties.
  - [ ] If a dashboard/read-only endpoint is added, a focused dashboard contract test covers it.
  - [ ] Existing selection semantics remain documented: `best` is graded-best, `winner` is existing gate/objective winner, and `selected_candidate` is the new pre-OOS research selector.
  - [ ] If no source change is needed, `p2-selector-tooling.txt` explains the existing command/script path used to produce the artifact.

  **QA Scenarios**:
  ```text
  Scenario: Selector unit coverage
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m pytest tests/unit/test_candidate_selection.py -q
      python -m pytest tests/unit/test_research_v3_tiebreak.py tests/unit/test_research_v4_rowset.py tests/unit/test_research_candidates.py -q
    Expected: Selector behavior is locked without hard-gate or engine edits.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p2-selector-tests.txt
  ```

  **Commit**: NO

- [x] 4. P3 prior-run selector replay, diagnostic only

  **What to do**: Apply `sparse_positive_v1` to prior run `tick_oos_dash_p3_train_2023_2025_20260604` using only `.omo/evidence/tick-oos-dashboard-validation-20260604/p3-selected-candidate.json` or the equivalent pre-OOS training rows. This is a mechanics check only.
  **Must NOT do**: Do not claim this proves gen5 effectiveness. Do not use replay output as a promotion candidate.

  **Acceptance Criteria**:
  - [ ] `p3-prior-replay-selected-candidate.json` has `diagnostic_only=true` and `oos_excluded=true`.
  - [ ] Replay rejects prior gen4 because `profit <= 0`.
  - [ ] Replay classifies prior gen5 as `sparse_positive` only if it satisfies the exact P1 thresholds and has only a daily-frequency gate failure.
  - [ ] `p3-prior-replay.md` states that replay is not efficacy evidence due data-snooping risk.

  **QA Scenarios**:
  ```text
  Scenario: Prior replay mechanics
    Tool: powershell
    Steps:
      Run the selector against .omo/evidence/tick-oos-dashboard-validation-20260604/p3-selected-candidate.json
      Verify gen4 rejection and gen5 bucket classification.
    Expected: Replay demonstrates rule mechanics only and stays OOS-blind.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p3-prior-replay-selected-candidate.json
  ```

  **Commit**: NO

- [x] 5. P4 fresh 2023~2025 selector-frozen research run

  **What to do**: Build a fresh train config from `.omo/evidence/tick-oos-dashboard-validation-20260604/p3-train-config.json`, retaining TICK 09:00~09:30, 2023-01-01 through 2025-12-31, prompt logging, equity points, segment feedback, few-shot seed source, official warm engine, and hard gates. Run id: `tick_sel_sparse_p4_train_2023_2025_20260604`. After completion, apply `sparse_positive_v1` and freeze the candidate before any OOS.
  **Must NOT do**: Do not use 2022/2026 results while choosing or editing the candidate. Do not weaken `min_daily_trades`, MDD, TPI, or profit hard gates.

  **Recommended config**:
  ```json
  {
    "run_id": "tick_sel_sparse_p4_train_2023_2025_20260604",
    "bt_full_start": 20230101,
    "bt_full_end": 20251231,
    "bt_timeframe": "tick",
    "bt_universe_start_time": 90000,
    "bt_universe_end_time": 93000,
    "max_generations": 6,
    "bt_timeout": 900,
    "bt_warm_run_timeout": 300,
    "min_daily_trades": 0.3,
    "mdd_cap": 35,
    "prompt_logging_enabled": true,
    "equity_points_enabled": true,
    "segment_feedback_enabled": true,
    "segment_feedback_min_count": 8,
    "bt_refine_from_best": true,
    "winner_objective": "uptrend"
  }
  ```

  **Acceptance Criteria**:
  - [ ] `p4-train-config.json` records exact config and hash.
  - [ ] `p4-train-log.txt` records start/end timestamps, command, PID/session if applicable, exit status, timeout/OOM status, and duration.
  - [ ] `p4-selected-candidate.json` is written before P5 and has `oos_excluded=true`.
  - [ ] If no candidate qualifies, P5 is skipped and `p4-selector-blocked.md` explains why.
  - [ ] Any prior gen5 strategy seeding/refinement is allowed only if documented as a training hypothesis and still followed by fresh selector freeze before OOS.

  **QA Scenarios**:
  ```text
  Scenario: Fresh selector-frozen train
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-train-config.json --run-id tick_sel_sparse_p4_train_2023_2025_20260604
      Apply sparse_positive_v1 to training generations only.
    Expected: Candidate is frozen before OOS or P5 is blocked honestly.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-selected-candidate.json
  ```

  **Commit**: NO

- [x] 6. P5 fixed 2022/2026 OOS seed-vs-AI comparison

  **What to do**: If P4 selected a candidate, build fixed OOS configs for seed and AI. AI configs must use exact P4 buy/sell names, `bt_refine_from_best=false`, `max_generations=1`, TICK timeframe, and no candidate mutation. Predeclare the comparison windows before execution. Prefer identical 09:00~09:30 AI/seed windows if configs support it; if seed templates require 09:00~09:28, document the mismatch and run an additional matched-window sensitivity if feasible.
  **Must NOT do**: Do not reselect, tune, or edit candidate code after any OOS result appears.

  **OOS pass rule**:
  - AI profit must be positive in both 2022 and 2026.
  - Combined AI profit must be greater than or equal to combined seed profit.
  - AI max MDD must be less than or equal to seed max MDD.
  - Each AI OOS year must have at least 20 trades or be classified `NEEDS_MORE_EVIDENCE`, even if profitable.
  - Combined AI OOS must have at least 50 trades.
  - OOS holding/trade profile must be within a documented human-reference corridor or have a written risk explanation.

  **Acceptance Criteria**:
  - [ ] `p5-config-manifest.json` records all seed/AI configs, windows, hashes, and selected strategy identity.
  - [ ] `p5-oos-comparison.json` has seed_2022, seed_2026, ai_2022, ai_2026 rows or exact blockers.
  - [ ] `p5-oos-comparison.md` states pass/fail against the exact rule above.
  - [ ] If P4 did not select a candidate, `p5-oos-blocked.md` exists and no OOS rows are fabricated.

  **QA Scenarios**:
  ```text
  Scenario: Fixed OOS execution
    Tool: powershell
    Steps:
      Run fixed seed and AI 2022/2026 configs.
      Compare AI buy/sell names with p4-selected-candidate.json before and after OOS.
    Expected: Candidate identity is unchanged; OOS pass/fail is rule-bound.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p5-oos-comparison.md
  ```

  **Commit**: NO

- [x] 7. P6 slippage, PBO/DSR status, and decision card

  **What to do**: Produce a final decision card. If slippage/PBO/DSR tooling exists, run read-only diagnostics with tests/evidence. If PBO/DSR tooling does not exist, mark it as an explicit advisory blocker; do not fake the metric. Slippage-stressed OOS must remain positive in both years for promotion.
  **Must NOT do**: Do not promote when OOS trade count is too sparse, P5 fails, slippage fails/unavailable, or PBO/DSR is an unresolved blocker.

  **Acceptance Criteria**:
  - [ ] `p6-decision-card.md` includes Executive Verdict, Selector Version, Candidate Identity, Training Evidence, Replay Caveat, OOS Evidence, Seed Comparison, Trade-Count Sufficiency, Slippage Status, PBO/DSR Status, Forbidden Actions Check, and Final Verdict.
  - [ ] `PROMOTE_CANDIDATE` appears only if P5 pass rule, slippage-stressed positive OOS, and evidence sufficiency all pass.
  - [ ] Otherwise verdict is `REJECT_CANDIDATE` or `NEEDS_MORE_EVIDENCE`.

  **QA Scenarios**:
  ```text
  Scenario: Decision honesty audit
    Tool: powershell + rg
    Steps:
      rg -n "PROMOTE_CANDIDATE|REJECT_CANDIDATE|NEEDS_MORE_EVIDENCE|human|superior|slippage|PBO|DSR" .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p6-decision-card.md
      Verify every positive claim cites P5/P6 evidence.
    Expected: Verdict is evidence-bound and no unsupported promotion language exists.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p6-decision-card.md
  ```

  **Commit**: NO

## Final Verification Wave

- [x] F1. Plan compliance audit

  **What to do**: Map every checklist item to evidence and record forbidden-action absence.

  **Acceptance Criteria**:
  - [ ] `final-plan-compliance.txt` maps P0-P6 and F1-F4 to artifacts.
  - [ ] It records whether `final_approval`, `export_winner`, `USER_ACK`, `KHOPENAPI`, `taskkill`, hard-gate edits, engine edits, or `backtest/graph` edits occurred.

  **QA Scenarios**:
  ```text
  Scenario: Compliance audit
    Tool: powershell + rg
    Steps:
      rg -n "^- \\[ \\]" .omo/plans/tick-selection-rule-sparse-gen5-research-20260604.md
      Get-ChildItem .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604
      rg -n "final_approval|export_winner|USER_ACK|KHOPENAPI|taskkill" .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604
    Expected: Open/completed tasks and forbidden-action evidence are explicit.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/final-plan-compliance.txt
  ```

- [x] F2. Code and branch safety verification

  **What to do**: Run final verification commands, preserving unrelated dirty changes.

  **Acceptance Criteria**:
  - [ ] `final-verification.txt` includes `git diff --check`, `python scripts/verify_nonrelease_sync.py`, protected-path status, and focused pytest output.
  - [ ] If source changed, focused selector/dashboard tests pass or exact blocker evidence is recorded.

  **QA Scenarios**:
  ```text
  Scenario: Final verification
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      git diff --check
      python scripts/verify_nonrelease_sync.py
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      python -m pytest tests/unit/test_candidate_selection.py tests/unit/test_research_v3_tiebreak.py tests/unit/test_research_v4_rowset.py tests/unit/test_research_candidates.py -q
      python -m pytest tests/unit/test_dashboard_current_gen_detail.py tests/unit/test_dashboard_run_compare_frontend.py tests/unit/test_dashboard_backtest_detail.py tests/unit/test_variable_correlation.py tests/unit/test_prompt_logging.py -q
    Expected: Verification passes or exact unrelated/pre-existing failures are recorded.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/final-verification.txt
  ```

- [x] F3. Dashboard/read-only QA if dashboard surface is used

  **What to do**: If any dashboard endpoint or current-code UI is used, capture selected base URL, statuses, and cleanup receipt for owned server only.

  **Acceptance Criteria**:
  - [ ] `final-dashboard-qa.txt` records exact URLs/statuses and selected base URL.
  - [ ] No approval/export action is invoked.

  **QA Scenarios**:
  ```text
  Scenario: Dashboard QA
    Tool: curl.exe
    Steps:
      curl.exe -sS "<base>/health"
      curl.exe -sS "<base>/runs"
      curl.exe -sS "<base>/runs/compare?ids=<seed_or_train_ids>"
    Expected: Read-only routes work or unavailability is explicit.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/final-dashboard-qa.txt
  ```

- [x] F4. Final handoff

  **What to do**: Record final git status, protected-path status, final verdict, and recommended next command.

  **Acceptance Criteria**:
  - [ ] `final-scope-fidelity.txt` includes branch status, protected-path status, final verdict from P6, selected candidate identity if any, and statement that this is research validation, not production promotion.
  - [ ] `.omo/boulder.json` is marked completed only after all required evidence exists.

  **QA Scenarios**:
  ```text
  Scenario: Final handoff
    Tool: powershell + rg
    Steps:
      git status --short --branch
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      rg -n "Final Verdict|PROMOTE_CANDIDATE|REJECT_CANDIDATE|NEEDS_MORE_EVIDENCE" .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p6-decision-card.md
    Expected: Final state and next command are explicit.
    Evidence: .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/final-scope-fidelity.txt
  ```

## Commit Strategy
- Commit: NO by default during `$start-work`; user can request a commit after review.
- If committing later, stage files explicitly and use Korean commit title/body.

## Success Criteria
- `sparse_positive_v1` is predeclared before OOS and produces auditable candidate-selection artifacts.
- Prior gen5 replay is clearly separated from fresh evidence and cannot be used as efficacy proof.
- A fresh 2023~2025 candidate is either frozen before OOS or honestly blocked.
- Fixed 2022/2026 OOS comparison either rejects, blocks, or promotes the candidate using the exact declared rules.
- Engines, hard gates, `backtest/graph/`, protected paths, live broker boundaries, and export/approval boundaries remain untouched.

## Recommended Commands
```powershell
$start-work tick-selection-rule-sparse-gen5-research-20260604
```

Optional high-accuracy planning review before execution:
```powershell
high accuracy review .omo/plans/tick-selection-rule-sparse-gen5-research-20260604.md
```
