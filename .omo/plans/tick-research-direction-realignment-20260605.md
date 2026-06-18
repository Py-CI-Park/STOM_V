# TICK Research Direction Realignment 20260605

## TL;DR
> **Summary**: Revise the TICK research plan so overfit-looking, human-like, and near-miss candidates are not killed too early. The pipeline now has three separate layers: Exploration Pool, Research Pool, and strict Promotion Gate.
> **Deliverables**:
> - Direction review update using `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
> - Three-tier candidate policy: `exploration_pool_v2`, `research_pool_v2`, `promotion_gate_v2`
> - Read-only PBO/CSCV, Deflated Sharpe, and slippage diagnostics
> - Human-reference morphology and recent-year improvement scoring for research ranking
> - gen6/gen7 near-miss retention and analysis, not early discard
> - `max_hold_count` reliability audit
> - 2023-2025 training run, research-pool analysis, and conditional fixed 2022/2026 OOS
> - Final decision card that separates "interesting research candidate" from "promotion-worthy proof"
> **Effort**: XL
> **Parallel**: YES - 4 waves
> **Critical Path**: P0 direction audit -> P1 three-tier policy -> P2 diagnostics + P3 pool selector -> P7 training/pools -> P8 conditional OOS -> P9 decision card

## Context
### Original Request
The user asked to revise the previous `$ulw-plan` because overly strict overfit rejection may prevent the system from discovering human-like condition expressions. The user also asked to review and incorporate:

- `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`

### Updated Direction From The 2026-06-05 Review
The review changes the planning stance:

- Current methodology is strong, but strict selectors do not improve the generator; they mostly reject earlier.
- The loop currently reinforces in-sample autopsy feedback, so train-good/OOS-bad behavior is expected.
- Human-made good conditions may look overfit because humans tune by reading charts/backtests over time.
- Therefore, exploration should be permissive enough to retain high-train, human-like, near-miss, and even overfit-looking candidates for analysis.
- Promotion claims must remain strict: fixed OOS, slippage, PBO/DSR, trade sufficiency, and forbidden-action checks.
- N1 is highest leverage: implement overfit diagnostics first, but use them as research labels in exploration and blockers only in promotion.
- N2/N3, regime experts and walk-forward refit, are strong future directions but should be recommended after evidence, not silently implemented in this plan.

### Plan Change
The prior plan used one strict `yearly_sparse_robust_v2` selector. This revision replaces that with a three-tier model:

| Layer | Purpose | Strictness | OOS Use |
|---|---|---|---|
| Exploration Pool | Keep broad, human-like, overfit-looking, and near-miss candidates for study | Loose | Never |
| Research Pool | Rank candidates worth deeper diagnosis and possible frozen OOS | Medium | Never for ranking |
| Promotion Gate | Decide whether any claim resembling human/seed superiority is allowed | Strict | Fixed OOS only after freeze |

### Guardrail
This plan does not weaken the final proof standard. It weakens early rejection only.

## Work Objectives
### Core Objective
Build a research process that can discover human-like TICK condition candidates without killing them too early, while preserving strict proof requirements before any seed/human-level claim.

### Deliverables
- `.omo/evidence/tick-research-direction-realignment-20260605/p0-direction-audit.md`
- `.omo/evidence/tick-research-direction-realignment-20260605/p1-three-tier-policy.md`
- `.omo/evidence/tick-research-direction-realignment-20260605/p2-promotion-diagnostics.json`
- `.omo/evidence/tick-research-direction-realignment-20260605/p3-pool-selector-tests.txt`
- `.omo/evidence/tick-research-direction-realignment-20260605/p4-max-hold-audit.md`
- `.omo/evidence/tick-research-direction-realignment-20260605/p5-research-diagnostics.json`
- `.omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-summary.md`
- `.omo/evidence/tick-research-direction-realignment-20260605/p7-candidate-pools.json`
- `.omo/evidence/tick-research-direction-realignment-20260605/p8-oos-comparison.json`
- `.omo/evidence/tick-research-direction-realignment-20260605/p9-decision-card.md`

### Definition Of Done
- Exploration Pool can retain candidates that fail Promotion Gate.
- Research Pool can explain why a candidate is promising or overfit-looking.
- Promotion Gate remains strict and cannot be bypassed by human-like morphology.
- If no promotion-eligible frozen candidate exists, fixed OOS is skipped or run only for explicitly marked research comparison, never for promotion.
- Final report states whether the next direction should be AI-alone replacement, seed+AI complement, regime-expert portfolio, or walk-forward refit.

### Must Have
- OOS-blind pool artifacts.
- Exact training/OOS periods and timeframe in every evidence file.
- PBO/DSR/slippage diagnostics implemented before final promotion reasoning.
- Human-reference morphology as research ranking aid only.
- No dashboard feature creep beyond evidence inspection.

### Must NOT Have
- No official engine edits: `backtest/backengine_*.py`, `backtest/back_static.py`.
- No hard-gate relaxation or edits to `compute_fitness` hard pass/fail semantics.
- No `backtest/graph/` edits.
- No protected path staging: `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `.omx/reports/`, `v3k_settings*.json`.
- No `final_approval`, `export_winner`, production strategy DB write, USER_ACK, KHOPENAPI login/connect, live broker wiring, V3K gate advancement, or blanket `taskkill`.
- No OOS-after-the-fact reselection.
- No claim that "overfit-looking is acceptable" at promotion stage.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.

Focused verification commands:

```powershell
python -m pytest tests/unit/test_candidate_research_pool_v2.py tests/unit/test_promotion_diagnostics.py tests/unit/test_sparse_positive_prompt.py -q
python -m pytest tests/unit/test_variable_correlation.py tests/unit/test_feature_importance.py tests/unit/test_backfinder_principle.py tests/unit/test_dispersion.py -q
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## Execution Strategy
### Parallel Execution Waves
Wave 1: P0 direction audit and P1 policy freeze.
Wave 2: P2 promotion diagnostics, P3 pool selector, P4 max-hold audit, P5 research diagnostics.
Wave 3: P6 smoke and P7 2023-2025 training/pool generation.
Wave 4: P8 conditional OOS and P9 decision card.

### Dependency Matrix
| Task | Depends On | Blocks |
|---|---|---|
| P0 Direction audit | none | all |
| P1 Three-tier policy | P0 | P2, P3, P7, P8 |
| P2 PBO/DSR/slippage diagnostics | P1 | P8, P9 |
| P3 Pool selector implementation | P1 | P7 |
| P4 Max-hold audit | P0 | P7 ranking annotation |
| P5 Research diagnostics | P0 | P7, P9 |
| P6 Smoke run | P1, P3 | P7 |
| P7 Training and pools | P2, P3, P4, P5, P6 | P8 |
| P8 Conditional fixed OOS | P7, P2 | P9 |
| P9 Decision card | P7, P8 | Final |

## TODOs
- [x] 1. P0 - Direction audit through `84acb6cb` plus current dirty evidence

  **What to do**:
  Create `.omo/evidence/tick-research-direction-realignment-20260605/`. Read `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md` and summarize what changes in the plan: strict selectors are no longer the exploration filter; N1 overfit diagnostics are first-class; replacement vs complement remains an explicit decision.

  **Must NOT do**: Do not edit source code or runtime DBs in this task.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: all later tasks | Blocked By: none

  **References**:
  - Direction review: `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
  - Prior plan: `.omo/plans/tick-research-direction-realignment-20260605.md`
  - Evidence cards: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md`, `.omo/evidence/tick-sparse-positive-oos-robustness-20260604/p7-decision-card.md`

  **Acceptance Criteria**:
  - [ ] `p0-direction-audit.md` states why overfit-looking candidates must remain analyzable in exploration.
  - [ ] `p0-direction-audit.md` states that strict proof remains required for promotion.
  - [ ] `p0-safety-snapshot.txt` captures branch, HEAD, dirty status, and protected-path status.

  **QA Scenarios**:
  ```text
  Scenario: Direction review reflected
    Tool: powershell
    Steps:
      rg -n "strict selectors|N1|PBO|Deflated|Complement|single" docs/update_log/2026-06-05_direction_review_through_84acb6cb.md
      rg -n "Exploration Pool|Research Pool|Promotion Gate" .omo/evidence/tick-research-direction-realignment-20260605/p0-direction-audit.md
    Expected: Audit maps the document's conclusions to the revised plan.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p0-direction-audit.md

  Scenario: Protected path snapshot
    Tool: powershell
    Steps:
      git status --short --branch
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
    Expected: Snapshot exists; no protected path is staged by this plan.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p0-safety-snapshot.txt
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

- [x] 2. P1 - Predeclare three-tier policy: exploration, research, promotion

  **What to do**:
  Write `p1-three-tier-policy.md` and `p1-three-tier-policy.json` before implementation or new OOS. This policy replaces the old single strict `yearly_sparse_robust_v2` concept.

  **Exploration Pool v2, loose OOS-blind retention**:
  - Input uses 2023-2025 training data only.
  - Reject only structural failures: missing strategy identity, no CSV, malformed CSV with no parseable trades, OOS-year contamination, or total trade_count < 10.
  - Retain candidates even if they fail yearly positivity, MDD <= 10, PBO/DSR, or strict trade sufficiency.
  - Label candidates with reasons: `human_like`, `near_miss`, `overfit_risk`, `sparse`, `mdd_risk`, `recent_improving`, `max_hold_unknown`, `pbo_high`, `dsr_insufficient`.
  - Max retained candidates: 30, deterministic sort by training profit, then lower MDD, then higher trade_count, then lower gen_no.

  **Research Pool v2, medium OOS-blind ranking**:
  - Input is Exploration Pool only.
  - Keep top 10 by research score.
  - Research score components:
    - human morphology score: trade density, MDD corridor, payoff, uptrend R2, drawdown recovery proxy, late-period collapse proxy, time-window spread, and `max_hold_count` if reliable.
    - recent improvement score: `0.2*profit_2023 + 0.3*profit_2024 + 0.5*profit_2025` plus positive yearly slope annotation.
    - quant score: variable correlation/interaction and feature-importance support.
    - risk label: PBO/DSR/slippage are annotations here, not blockers.
  - Suggested minimum for research ranking, not hard reject: aggregate trade_count >= 50 and at least two training years with trades.

  **Promotion Gate v2, strict proof**:
  - Promotion candidate max: 1.
  - Must pass base sparse-positive quality.
  - Training aggregate trades >= 150.
  - Each training year trade_count >= 30.
  - Each training year profit > 0.
  - Aggregate MDD <= 10.0.
  - Fixed OOS positive in both 2022 and available 2026 window.
  - Combined AI OOS profit >= combined seed OOS profit.
  - AI max OOS MDD <= seed max OOS MDD.
  - Each AI OOS window trade_count >= 20 and combined AI OOS trades >= 50.
  - Slippage-stressed OOS stays positive at 0.1%, 0.2%, and 0.3%.
  - PBO < 0.20 and DSR > 0. Insufficient data blocks promotion.

  **Must NOT do**: Do not use OOS data for Exploration or Research Pool ranking. Do not tune thresholds after OOS.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: P2, P3, P7, P8 | Blocked By: P0

  **References**:
  - Direction review: `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md:171`
  - Existing selector: `ai_strategy_loop/controller/_candidate_selection_core.py:81`
  - Existing yearly strict selector: `ai_strategy_loop/controller/_yearly_sparse_robust_selection.py:80`
  - Variable diagnostics: `ai_strategy_loop/fitness/correlation.py:76`, `ai_strategy_loop/fitness/correlation_profile.py:38`

  **Acceptance Criteria**:
  - [ ] Policy JSON parses and includes `exploration_pool_v2`, `research_pool_v2`, and `promotion_gate_v2`.
  - [ ] Policy explicitly says PBO/DSR are labels in exploration/research, blockers only in promotion.
  - [ ] Policy explicitly says human-reference morphology is not promotion proof.

  **QA Scenarios**:
  ```text
  Scenario: Policy parse and labels
    Tool: powershell
    Steps:
      python -c "import json,pathlib; p=json.loads(pathlib.Path('.omo/evidence/tick-research-direction-realignment-20260605/p1-three-tier-policy.json').read_text(encoding='utf-8')); assert 'exploration_pool_v2' in p and 'research_pool_v2' in p and 'promotion_gate_v2' in p"
    Expected: Policy JSON parses and has all three layers.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p1-policy-verify.txt

  Scenario: Early overfit candidates are retained, not promoted
    Tool: powershell
    Steps:
      rg -n "overfit|PBO|DSR|blocker|promotion|human morphology" .omo/evidence/tick-research-direction-realignment-20260605/p1-three-tier-policy.md
    Expected: The policy keeps overfit-looking candidates in research while blocking unsupported promotion.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p1-policy-verify.txt
  ```

  **Commit**: NO | Message: n/a | Files: policy evidence only

- [x] 3. P2 - Implement read-only overfit diagnostics: slippage, CSCV/PBO, Deflated Sharpe

  **What to do**:
  Add diagnostics first, because N1 is the highest-leverage gap. These diagnostics must label exploration/research candidates but block only Promotion Gate.

  **Owned files**:
  - `ai_strategy_loop/fitness/promotion_diagnostics.py`
  - `tests/unit/test_promotion_diagnostics.py`

  **Method**:
  - Slippage: 0.1%, 0.2%, 0.3% round-trip haircuts. Use trade notional columns if present; otherwise use `5_000_000 KRW * trade_count * haircut`.
  - CSCV/PBO: use monthly folds from 2023-2025 candidate CSVs. If fewer than 8 folds or fewer than 2 candidates, return `INSUFFICIENT_DATA`.
  - Deflated Sharpe: compute from monthly returns. If fewer than 12 monthly observations, return `INSUFFICIENT_DATA`.
  - Return JSON-safe labels: `pbo_status`, `pbo_value`, `dsr_status`, `dsr_value`, `slippage_status`, `promotion_blocker`.

  **Must NOT do**: Do not change `compute_fitness`. Do not mark insufficient PBO/DSR as pass.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: P7, P8, P9 | Blocked By: P1

  **References**:
  - Direction review N1: `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md:229`
  - Analysis audit gap: `docs/update_log/2026-06-02_analysis_capability_audit.md`
  - Prior advisory blocker: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md`

  **Acceptance Criteria**:
  - [ ] Tests cover notional slippage, proxy slippage, insufficient PBO, valid PBO, insufficient DSR, valid DSR.
  - [ ] Diagnostic output can be attached to Exploration Pool and Research Pool without rejecting them.
  - [ ] Promotion Gate blocks if PBO/DSR are insufficient or fail thresholds.

  **QA Scenarios**:
  ```text
  Scenario: Diagnostics tests
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_promotion_diagnostics.py -q
    Expected: All diagnostics tests pass.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p2-diagnostics-tests.txt

  Scenario: Insufficient data labels but does not erase research candidate
    Tool: pytest
    Steps:
      Run fixture with one candidate and short monthly history.
    Expected: Candidate has `dsr_insufficient`/`pbo_insufficient` labels and `promotion_allowed=false`, but remains eligible for research-pool annotation.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p2-promotion-diagnostics.json
  ```

  **Commit**: YES | Message: `조건식연구: 과적합 승격 진단 추가` | Files: owned files only

- [x] 4. P3 - Implement dual-track candidate pools and tests

  **What to do**:
  Implement `exploration_pool_v2`, `research_pool_v2`, and `promotion_gate_v2` as read-only selection/ranking helpers. Keep existing `sparse_positive_v1` and `yearly_sparse_robust_v1` unchanged.

  **Owned files**:
  - `ai_strategy_loop/controller/_candidate_research_pool_v2.py`
  - `ai_strategy_loop/controller/_candidate_research_pool_artifact.py`
  - `ai_strategy_loop/controller/candidate_selection.py`
  - `tests/unit/test_candidate_research_pool_v2.py`

  **Artifact schema**:
  - `selector_version`
  - `policy_hash`
  - `config_hash`
  - `oos_excluded=true`
  - `exploration_pool`
  - `research_pool`
  - `promotion_candidate`
  - `rejected_structural`
  - `labels`
  - `diagnostics`
  - `forbidden_oos_fields_detected`

  **Must NOT do**: Do not reuse strict v1 as the exploration filter. Do not select after OOS.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: P7 | Blocked By: P1

  **References**:
  - Existing candidate parser: `ai_strategy_loop/controller/_candidate_selection_artifact.py`
  - Existing strict selector: `ai_strategy_loop/controller/_yearly_sparse_robust_selection.py`
  - Public exports: `ai_strategy_loop/controller/candidate_selection.py`
  - Test style: `tests/unit/test_yearly_sparse_robust_selection.py`

  **Acceptance Criteria**:
  - [ ] A candidate with positive train profit but MDD > 10 can remain in Exploration Pool with `mdd_risk` label.
  - [ ] A gen6-like candidate with trades < 150 can remain in Research Pool but fail Promotion Gate.
  - [ ] A gen7-like candidate with MDD 10.32 can remain in Research Pool but fail Promotion Gate.
  - [ ] Any CSV with 2022 or 2026 rows is structurally rejected for pool ranking.
  - [ ] Existing v1 tests still pass.

  **QA Scenarios**:
  ```text
  Scenario: Near misses retained
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_candidate_research_pool_v2.py -q
    Expected: gen6/gen7-style fixtures are retained for research and blocked only for promotion.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p3-pool-selector-tests.txt

  Scenario: Existing selectors unchanged
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_yearly_sparse_robust_selection.py tests/unit/test_sparse_positive_prompt.py -q
    Expected: Existing behavior is unchanged.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p3-pool-selector-tests.txt
  ```

  **Commit**: YES | Message: `조건식연구: 탐색 후보 풀 선택기 추가` | Files: owned files only

- [x] 5. P4 - Audit `max_hold_count` and sparse holding behavior

  **What to do**:
  Determine whether low `max_hold_count` values are real strategy behavior or a measurement/display artifact. Use it as a research ranking/annotation field unless the audit proves reliability.

  **Owned files, only if code is needed**:
  - `scripts/research/audit_tick_max_hold_count.py`
  - `tests/unit/test_tick_max_hold_count_audit.py`

  **Must NOT do**: Do not edit official engines. Do not treat missing CSV buy/sell time columns as zero holdings.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: P7 annotation | Blocked By: P0

  **References**:
  - Score metric: `ai_strategy_loop/fitness/score.py:444`
  - State persistence: `ai_strategy_loop/controller/state.py:190`
  - CSV holdings recomputation: `ai_strategy_loop/fitness/equity_series.py:73`
  - Dashboard route/display: `ai_strategy_loop/dashboard/app.py:1102`
  - Tests: `tests/unit/test_dispersion.py`, `tests/unit/test_dashboard_backtest_detail.py`, `tests/unit/test_dashboard_hall_of_fame.py`

  **Acceptance Criteria**:
  - [ ] `p4-max-hold-audit.md` classifies `max_hold_count` as `reliable`, `display_only`, or `unavailable`.
  - [ ] Research Pool uses max-hold as rank/annotation only unless reliability is proven.
  - [ ] Promotion Gate does not fail solely on max-hold.

  **QA Scenarios**:
  ```text
  Scenario: Existing max-hold tests still pass
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_dispersion.py tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_hall_of_fame.py -q
    Expected: Existing contracts pass.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p4-max-hold-tests.txt

  Scenario: Missing holdings data is not false zero
    Tool: powershell
    Steps:
      Run audit against fixture/CSV with missing buy/sell time columns.
    Expected: Audit reports `unavailable`, not `zero`.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p4-max-hold-audit.md
  ```

  **Commit**: YES | Message: `조건식연구: 동시보유 지표 감사 추가` | Files: audit script/tests only

- [x] 6. P5 - Build human-reference and quant research diagnostics

  **What to do**:
  Create a research diagnostics report that ranks candidates without using OOS. Include variable correlations, feature histograms/ranges, time/market-cap/year segments, interactions, feature importance, BackFinder hints, and human-reference morphology.

  **Human morphology fields**:
  - trade density
  - MDD corridor
  - payoff ratio
  - uptrend R2 / equity smoothness proxy
  - drawdown recovery proxy
  - late-period collapse proxy
  - time-window spread
  - max-hold annotation if reliable
  - similarity to `docs/reference/STOM_Good_Results/` as reference-only, not proof

  **Owned files, only if glue code is needed**:
  - `scripts/research/build_tick_realign_research_report.py`
  - `tests/unit/test_tick_realign_research_report.py`

  **Must NOT do**: Do not use human screenshot similarity as promotion proof. Do not generate buy conditions from result/leakage variables.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: P7, P9 | Blocked By: P0

  **References**:
  - Human reference review: `docs/research/2026-06-04_condition_research_rereview_human_reference_graphs.md`
  - Direction review morphology caveat: `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
  - Correlation: `ai_strategy_loop/fitness/correlation.py:76`
  - Profile: `ai_strategy_loop/fitness/correlation_profile.py:38`
  - Feature importance: `ai_strategy_loop/fitness/feature_importance.py`
  - BackFinder: `ai_strategy_loop/fitness/backfinder_principle.py`

  **Acceptance Criteria**:
  - [ ] `p5-research-diagnostics.json` contains quant diagnostics or exact insufficiency reasons.
  - [ ] `p5-human-morphology.md` states that human similarity is a research prior, not proof.
  - [ ] Diagnostics support Research Pool ranking but do not override Promotion Gate.

  **QA Scenarios**:
  ```text
  Scenario: Quant diagnostics tests
    Tool: pytest
    Steps:
      python -m pytest tests/unit/test_variable_correlation.py tests/unit/test_feature_importance.py tests/unit/test_backfinder_principle.py -q
    Expected: Existing quant diagnostics pass.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p5-research-tests.txt

  Scenario: Empty data reports insufficiency
    Tool: pytest or powershell
    Steps:
      Run report builder against empty/missing CSV list.
    Expected: Report says `insufficient`, not false signal.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p5-research-diagnostics.json
  ```

  **Commit**: YES | Message: `조건식연구: 인간형 후보 진단 리포트 추가` | Files: report script/tests only

- [x] 7. P6 - Short smoke run with permissive exploration settings

  **What to do**:
  Create `.omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-config.json`. Use tick 09:00-09:30, 2025-01-01 through 2025-03-31, `max_generations=2`, and the same generation aids as before:

  - `provider="gpt_auth"`
  - `bt_timeframe="tick"`
  - `bt_universe_start_time=90000`
  - `bt_universe_end_time=93000`
  - `classification_generation_enabled=true`
  - `require_filter_gates=true`
  - `encourage_time_dispersion=true`
  - `few_shot_enabled=true`
  - `few_shot_source="seed_db"`
  - `segment_feedback_enabled=true`
  - `sparse_positive_prompt_enabled=true`
  - `dispersion_prompt_enabled=true`

  Run ID: `tick_realign_p6_smoke_20260605`.

  **Must NOT do**: Do not use smoke as OOS proof. Do not require Promotion Gate pass for smoke success.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: P7 | Blocked By: P1, P3

  **References**:
  - Loop CLI: `ai_strategy_loop/controller/loop.py:2272`
  - Config: `ai_strategy_loop/config.py`
  - Prior note: `.omo/plans/tick-oos-validation-20260603.md:31`

  **Acceptance Criteria**:
  - [ ] Smoke exits cleanly or records blocker.
  - [ ] At least one candidate is classifiable into Exploration Pool or structural blocker is recorded.
  - [ ] Smoke summary says no human/seed-level claim is allowed.

  **QA Scenarios**:
  ```text
  Scenario: Smoke run
    Tool: powershell
    Steps:
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-config.json --run-id tick_realign_p6_smoke_20260605
    Expected: Run exits 0 or blocker is recorded.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-log.txt

  Scenario: Smoke pool classification
    Tool: powershell
    Steps:
      Apply exploration_pool_v2 to smoke generations.
    Expected: Candidates are retained/labeled or structurally rejected with exact reasons.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-summary.md
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

- [x] 8. P7 - 2023-2025 training run and candidate pools

  **What to do**:
  Create `.omo/evidence/tick-research-direction-realignment-20260605/p7-train-config.json` from P6. Set:

  - `bt_full_start=20230101`
  - `bt_full_end=20251231`
  - `max_generations=10`

  Run ID: `tick_realign_p7_train_2023_2025_20260605`.

  After training, write `p7-candidate-pools.json`:
  - all structurally valid candidates in Exploration Pool
  - top 10 Research Pool candidates
  - zero or one Promotion Gate candidate
  - labels for near-miss/overfit/human-like/recent-improving
  - gen6/gen7-style near-miss handling if present

  **Must NOT do**: Do not use 2022/2026 OOS in pool ranking. Do not require strict Promotion Gate for research-pool evidence.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: P8 | Blocked By: P2, P3, P4, P5, P6

  **References**:
  - Current loop run path: `ai_strategy_loop/controller/loop.py`
  - Candidate pool selector from P3
  - Diagnostics from P2/P5

  **Acceptance Criteria**:
  - [ ] `p7-train-log.txt` records official loop execution or exact blocker.
  - [ ] `p7-candidate-pools.json` has `oos_excluded=true`.
  - [ ] Research Pool can be non-empty even if Promotion Gate has no candidate.
  - [ ] `p7-near-miss-analysis.md` explains any high-train/strict-fail candidates.

  **QA Scenarios**:
  ```text
  Scenario: Training run and pools
    Tool: powershell
    Steps:
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-research-direction-realignment-20260605/p7-train-config.json --run-id tick_realign_p7_train_2023_2025_20260605
      Apply exploration_pool_v2, research_pool_v2, and promotion_gate_v2.
    Expected: Candidate pools are written before any OOS.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p7-candidate-pools.json

  Scenario: OOS blindness
    Tool: powershell
    Steps:
      rg -n "oos_2022|oos_2026|seed_2022|seed_2026|ai_2022|ai_2026|post_oos" .omo/evidence/tick-research-direction-realignment-20260605/p7-candidate-pools.json
    Expected: No OOS fields are present.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p7-oos-blindness-check.txt
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

- [x] 9. P8 - Conditional fixed 2022/2026 OOS

  **What to do**:
  There are two possible paths:

  1. **Promotion path**: If `promotion_candidate` exists, run fixed seed/AI OOS:
     - `tick_realign_p8_seed_2022_20260605`
     - `tick_realign_p8_seed_2026_20260605`
     - `tick_realign_p8_ai_2022_20260605`
     - `tick_realign_p8_ai_2026_20260605`
  2. **Research-only path**: If no promotion candidate exists but Research Pool has candidates, do not run promotion OOS by default. Optionally write `p8-oos-blocked.md` and recommend a separate future plan for controlled research OOS comparison.

  OOS rules for Promotion path:
  - 2022: `20220101..20221231`.
  - 2026: exact available seed config window; record exact dates.
  - AI configs use frozen promotion candidate buy/sell names.
  - `max_generations=1`, `bt_refine_from_best=false`, tick 09:00-09:30.
  - No generation/refinement/reselection.

  **Must NOT do**: Do not run OOS on multiple Research Pool candidates in this plan; that would become OOS-driven selection. Do not tune after OOS.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: P9 | Blocked By: P7, P2

  **References**:
  - Prior OOS plan: `.omo/plans/tick-oos-validation-20260603.md`
  - Prior OOS blocker: `.omo/evidence/tick-sparse-positive-oos-robustness-20260604/p6-oos-blocked.md`

  **Acceptance Criteria**:
  - [ ] If no promotion candidate exists, `p8-oos-blocked.md` exists and explains why Research Pool still matters.
  - [ ] If promotion candidate exists, `p8-oos-comparison.json` has seed/AI 2022/2026 rows or exact blockers.
  - [ ] Candidate identity before and after OOS is identical.
  - [ ] `p8-promotion-diagnostics.json` contains slippage/PBO/DSR and `promotion_allowed`.

  **QA Scenarios**:
  ```text
  Scenario: No promotion candidate
    Tool: powershell
    Steps:
      Read p7-candidate-pools.json; if promotion_candidate is null, verify no P8 AI OOS run rows are created.
    Expected: OOS blocked; research pool is preserved for analysis.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p8-oos-blocked.md

  Scenario: Frozen promotion OOS
    Tool: powershell
    Steps:
      If promotion_candidate exists, run fixed seed/AI OOS configs.
    Expected: Four OOS rows exist or exact blockers; identity unchanged.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p8-oos-comparison.json
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

- [x] 10. P9 - Decision card and direction choice

  **What to do**:
  Write `p9-decision-card.md` with these sections:

  - Executive Verdict
  - Direction Review Incorporated
  - Exploration Pool Summary
  - Research Pool Summary
  - Promotion Gate Summary
  - Near-Miss and Overfit-Looking Candidates
  - Human Morphology Evidence
  - PBO/DSR/Slippage Status
  - Max-Hold Audit
  - OOS Evidence or OOS Blocker
  - Seed Comparison, if OOS ran
  - Replacement vs Complement Recommendation
  - N2 Regime-Expert Feasibility
  - N3 Walk-Forward Feasibility
  - Forbidden Actions Check
  - Final Verdict
  - Next Recommended Command

  **Verdict enum**:
  - `PROMOTE_RESEARCH_CANDIDATE`
  - `RESEARCH_POOL_READY`
  - `REJECT_CANDIDATE`
  - `NEEDS_MORE_EVIDENCE`

  **Must NOT do**: Do not claim human-level or seed-superior from Exploration/Research Pool alone. Do not hide OOS blockers.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: Final | Blocked By: P7, P8

  **References**:
  - Direction review: `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
  - Decision card pattern: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md`
  - Needs-more-evidence pattern: `.omo/evidence/tick-sparse-positive-oos-robustness-20260604/p7-decision-card.md`

  **Acceptance Criteria**:
  - [ ] Final verdict uses the enum above.
  - [ ] If verdict is `RESEARCH_POOL_READY`, it clearly says this is not promotion proof.
  - [ ] Recommendation explicitly chooses or defers among AI-alone replacement, seed+AI complement, N2 regime experts, and N3 walk-forward.
  - [ ] Forbidden action section confirms no `final_approval`, `export_winner`, live broker, V3K, or blanket taskkill.

  **QA Scenarios**:
  ```text
  Scenario: Decision honesty scan
    Tool: powershell
    Steps:
      rg -n "PROMOTE_RESEARCH_CANDIDATE|RESEARCH_POOL_READY|REJECT_CANDIDATE|NEEDS_MORE_EVIDENCE|human|seed|PBO|DSR|slippage|final_approval|export_winner|KHOPENAPI|taskkill" .omo/evidence/tick-research-direction-realignment-20260605/p9-decision-card.md
    Expected: Required verdict and guardrail statements are present.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p9-honesty-audit.txt

  Scenario: No unsupported promotion
    Tool: powershell
    Steps:
      If verdict is PROMOTE_RESEARCH_CANDIDATE, verify p8-promotion-diagnostics.json has promotion_allowed=true.
    Expected: Promotion verdict cannot appear without strict diagnostics pass.
    Evidence: .omo/evidence/tick-research-direction-realignment-20260605/p9-honesty-audit.txt
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

## Final Verification Wave
> ALL must APPROVE. Present consolidated results to user before marking the work done.

- [x] F1. Plan Compliance Audit
  ```powershell
  rg -n "^- \[ \]" .omo/plans/tick-research-direction-realignment-20260605.md
  Get-ChildItem .omo/evidence/tick-research-direction-realignment-20260605
  ```

- [x] F2. Focused Tests
  ```powershell
  python -m pytest tests/unit/test_candidate_research_pool_v2.py tests/unit/test_promotion_diagnostics.py tests/unit/test_sparse_positive_prompt.py -q
  python -m pytest tests/unit/test_variable_correlation.py tests/unit/test_feature_importance.py tests/unit/test_backfinder_principle.py tests/unit/test_dispersion.py -q
  ```

- [x] F3. Guardrail Verification
  ```powershell
  git diff --check
  python scripts/verify_nonrelease_sync.py
  git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
  ```

- [x] F4. Scope Fidelity
  - Verify no source edits outside owned files.
  - Verify no engine/hard-gate/backtest_graph/protected path edits.
  - Verify no production export/live/V3K action.
  - Verify final answer separates research discovery from promotion proof.

## Commit Strategy
- Stage files explicitly; do not use `git add -A`.
- Suggested commits:
  - `조건식연구: 과적합 승격 진단 추가`
  - `조건식연구: 탐색 후보 풀 선택기 추가`
  - `조건식연구: 동시보유 지표 감사 추가`
  - `조건식연구: 인간형 후보 진단 리포트 추가`
- Korean markdown commit bodies must mention that engines, hard gates, protected paths, `final_approval`, and `export_winner` were not touched.

## Success Criteria
- The system no longer treats every overfit-looking candidate as immediate failure.
- gen6/gen7-style near misses can become research evidence without becoming promotion claims.
- Strict OOS/slippage/PBO/DSR standards remain intact for promotion.
- Final decision tells the user whether the next best direction is:
  - continue AI-alone replacement,
  - switch to seed+AI complement,
  - build regime-expert portfolio,
  - or build walk-forward refit workflow.

## Recommended Next Command
```text
$start-work tick-research-direction-realignment-20260605
```

Optional high-accuracy review before execution:

```text
high accuracy review .omo/plans/tick-research-direction-realignment-20260605.md
```
