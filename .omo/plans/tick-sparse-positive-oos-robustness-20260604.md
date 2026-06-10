# TICK Sparse-Positive OOS Robustness Improvement 20260604

## TL;DR
> **Summary**: Convert the prior sparse-positive training success into a stricter OOS-robust research workflow by adding a predeclared training-only yearly robustness selector, then run a fresh 2023-2025 train pass and fixed 2022/2026 OOS only after a candidate is frozen.
> **Deliverables**:
> - Safety snapshot and canonical reread
> - `yearly_sparse_robust_v1` policy and artifact schema
> - Read-only training-year breakdown tooling and tests
> - Fresh TICK train config using existing `sparse_positive_prompt_enabled=true`, `winner_objective=multiyear`, and holdout diagnostics
> - Fresh selector-frozen train run
> - Conditional fixed 2022/2026 OOS seed-vs-AI comparison
> - Slippage/PBO/DSR honest decision card
> **Effort**: XL
> **Parallel**: Limited - audits/tests can parallelize; official TICK loop runs must be serialized.
> **Critical Path**: P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7 -> Final Verification

## Context
### Original Request
The user asked to execute the recommended command:

```powershell
$ulw-plan TICK sparse-positive OOS robustness improvement. Use .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p5-selected-candidate.json, p6-oos-comparison.json, p7-decision-card.md, final-verification.txt as canonical evidence. Keep hard gates, official engines, backtest/graph, protected paths unchanged; keep sparse_positive_prompt_enabled default OFF; forbid OOS-after-the-fact reselection and production export.
```

### Interview Summary
- No user questions are blocking because the user explicitly asked to proceed.
- The prior plan successfully produced a sparse-positive training candidate, then honestly rejected it on fixed OOS.
- The new bottleneck is not training-candidate existence; it is 2022 regime transfer and OOS trade sufficiency.

### Metis Review
Metis found gaps and this plan resolves them as follows:
- Do not mutate `sparse_positive_v1`; add a new versioned selector `yearly_sparse_robust_v1`.
- Define exact training-only yearly thresholds before any new OOS.
- Add a machine-readable policy artifact and selection artifact schema.
- Use result CSV/generation `csv_path` as the source for yearly metrics; missing/malformed/insufficient CSV rejects a candidate.
- Keep PBO/DSR advisory unless implemented tooling exists; do not make promotion possible without them.
- Avoid adding another prompt toggle. Use existing `sparse_positive_prompt_enabled`, which remains default OFF.

### Canonical Evidence
- `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p5-selected-candidate.json`
- `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p6-oos-comparison.json`
- `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md`
- `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/final-verification.txt`
- `docs/AGENT_HANDOFF.md`

### Ground Truth From Prior Run
- P5 selected gen4 before OOS: profit `+1,155,715`, MDD `9.12`, trades `124`, payoff `1.55`, bucket `sparse_positive`.
- P6 fixed OOS rejected the candidate:
  - seed_2022: `+2,223,554`, MDD `13.02`, trades `58`
  - seed_2026: `-191,109`, MDD `15.63`, trades `10`
  - ai_2022: `-222,400`, MDD `9.0`, trades `24`
  - ai_2026: `+356,664`, MDD `1.36`, trades `7`
- OOS pass failed because AI was not positive in both years, combined AI profit `134,264` was below seed `2,032,445`, and AI total OOS trades `31` was below the predeclared `50` minimum.

## Work Objectives
### Core Objective
Improve OOS robustness by requiring a fresh candidate to prove training-only yearly transfer and trade sufficiency before it is allowed into fixed 2022/2026 OOS.

### Deliverables
- Evidence root: `.omo/evidence/tick-sparse-positive-oos-robustness-20260604/`
- Policy files: `p1-yearly-sparse-robust-policy.md`, `p1-yearly-sparse-robust-policy.json`
- Source support for `yearly_sparse_robust_v1` selector and yearly breakdown artifact, if not already available
- Focused unit tests
- Predeclared run configs and hashes
- Fresh 2023-2025 train run and selector-freeze artifact
- Conditional fixed OOS comparison or explicit blocker
- Final decision card and handoff

### Definition of Done
- `git diff --check` exits 0.
- `python scripts/verify_nonrelease_sync.py` exits 0.
- Protected path status is empty:
  ```powershell
  git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
  ```
- Unit tests for the new selector/yearly breakdown pass.
- Existing sparse-positive prompt and selector tests still pass.
- `sparse_positive_prompt_enabled` remains default OFF.
- No OOS run exists without a preceding `yearly_sparse_robust_v1` selected-candidate artifact with `oos_excluded=true`.
- Final verdict is one of `PROMOTE_CANDIDATE`, `REJECT_CANDIDATE`, or `NEEDS_MORE_EVIDENCE`; no unsupported human-superiority claim appears.

### Must Have
- `PYTHONUTF8=1` for all Python commands.
- Preserve `sparse_positive_v1` behavior and artifacts.
- Add `yearly_sparse_robust_v1` as a separate versioned selector.
- The new selector uses training rows and training CSVs only.
- Training years are exactly 2023, 2024, and 2025 for the fresh run.
- A candidate must satisfy all aggregate `sparse_positive_v1` checks plus stricter yearly robustness checks before OOS.
- If no candidate qualifies, skip 2022/2026 OOS and write a blocker artifact.

### Must NOT Have
- No edits to `ai_strategy_loop/fitness/score.py` hard gates.
- No edits to `backtest/backengine_*.py`, `backtest/back_static.py`, or official backtest engine behavior.
- No edits to `backtest/graph/`.
- No production strategy DB writes, `final_approval`, or `export_winner`.
- No V3K gate advancement, USER_ACK creation, KHOPENAPI login/connect, or live order wiring.
- No blanket `taskkill`; clean up only owned sessions/PIDs.
- No OOS-after-the-fact candidate change.
- No new prompt toggle unless a later explicit plan expands scope; use existing `sparse_positive_prompt_enabled`.

## Predeclared Selector: `yearly_sparse_robust_v1`
This selector is stricter than `sparse_positive_v1` and does not replace it.

Aggregate checks:
- Candidate must pass `sparse_positive_v1` aggregate checks.
- Total training `trade_count` must be between `150` and `250`.
- Total training `daily_avg_trades` must be at least `0.15`.
- Total training MDD must be `<= 10.0`.
- Total training profit must be `> 0`.
- Total payoff ratio must be `>= 1.05`.

Yearly checks, computed from the candidate's 2023-2025 result CSV by sell-date year:
- All required training years `2023`, `2024`, and `2025` must be present.
- Each required year must have at least `30` trades.
- Each required year must have positive profit.
- Full-period training uptrend R2 from the same CSV must be `>= 0.50`.
- Missing CSV, malformed CSV, missing date/profit columns, or insufficient yearly rows reject the candidate.

Ranking:
- Bucket A `hard_gate_yearly_robust`: aggregate hard gate passed plus yearly checks pass.
- Bucket B `sparse_yearly_robust`: aggregate sparse-positive bucket plus yearly checks pass.
- Rank key: bucket priority, descending minimum yearly profit, descending full profit per MDD, ascending MDD, descending capped total trades, descending payoff, ascending generation.

Forbidden selector fields:
- Any 2022/2026 OOS metrics.
- Slippage-stress results.
- Final decision-card verdicts.
- Any post-OOS analysis.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.

- Test decision: TDD for selector/yearly breakdown; focused pytest after implementation.
- Evidence root: `.omo/evidence/tick-sparse-positive-oos-robustness-20260604/`
- Required test commands:
  ```powershell
  $env:PYTHONUTF8='1'
  python -m pytest tests/unit/test_yearly_sparse_robust_selection.py tests/unit/test_candidate_selection.py tests/unit/test_sparse_positive_prompt.py -q
  python -m pytest tests/unit/test_filter_gate.py tests/unit/test_few_shot.py tests/unit/test_segment_feedback.py tests/unit/test_prompt_logging.py -q
  git diff --check
  python scripts/verify_nonrelease_sync.py
  ```

## Execution Strategy
### Parallel Execution Waves
Wave 1: P0 and P1 are sequential foundations.
Wave 2: P2 selector/tooling implementation and P3 config predeclaration.
Wave 3: P4 smoke and P5 fresh train.
Wave 4: P6 conditional fixed OOS.
Wave 5: P7 decision card and final verification.

### Dependency Matrix
| Task | Depends On | Blocks |
|---|---|---|
| P0 | none | P1 |
| P1 | P0 | P2, P3 |
| P2 | P1 | P4, P5 |
| P3 | P1 | P4, P5 |
| P4 | P2, P3 | P5 |
| P5 | P2, P3, P4 | P6, P7 |
| P6 | P5 selected=true | P7 |
| P7 | P5 and conditional P6 | F1-F4 |

## TODOs

- [x] 1. P0 safety snapshot and canonical reread

  **What to do**: Create the evidence root. Capture branch, HEAD, dirty worktree, protected-path status, Boulder state, prior final verdict, prior selected candidate, and prior OOS comparison.
  **Must NOT do**: Do not clean or stage the dirty worktree. Do not stop the user's dashboard on 8770.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: P1 | Blocked By: none

  **References**:
  - Canonical: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p5-selected-candidate.json` - prior training candidate.
  - Canonical: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p6-oos-comparison.json` - OOS failure facts.
  - Canonical: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md` - final rejection.
  - Project rules: `AGENTS.md` - protected paths and verification commands.

  **Acceptance Criteria**:
  - [ ] `p0-safety-snapshot.txt` records branch, HEAD, dirty state, protected path status, and Boulder state.
  - [ ] `p0-canonical-reread.txt` records P5/P6/P7 facts and the prior `REJECT_CANDIDATE` verdict.
  - [ ] Protected-path status is empty or explicitly pre-existing/unrelated.

  **QA Scenarios**:
  ```text
  Scenario: Safety snapshot
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      New-Item -ItemType Directory -Force .omo/evidence/tick-sparse-positive-oos-robustness-20260604
      git status --short --branch
      git rev-parse HEAD
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      Get-Content .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md
    Expected: Evidence root exists and prior rejection facts are visible.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p0-safety-snapshot.txt
  ```

  **Commit**: NO

- [x] 2. P1 predeclare `yearly_sparse_robust_v1` policy

  **What to do**: Write the selector policy and machine-readable thresholds before source changes or new OOS. Explicitly state that prior 2022/2026 OOS is used only as a rejected-candidate lesson, not as a future after-the-fact selector adjustment.
  **Must NOT do**: Do not tune thresholds after any new OOS result appears. Do not edit `sparse_positive_v1`.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: P2, P3 | Blocked By: P0

  **References**:
  - Existing selector: `ai_strategy_loop/controller/_candidate_selection_core.py:19` - aggregate thresholds.
  - Existing selector API: `ai_strategy_loop/controller/candidate_selection.py:1`.
  - Forbidden OOS fields: `ai_strategy_loop/controller/_candidate_selection_artifact.py:18`.
  - Existing tests: `tests/unit/test_candidate_selection.py:1`.

  **Acceptance Criteria**:
  - [ ] `p1-yearly-sparse-robust-policy.md` contains all aggregate/yearly thresholds, ranking, forbidden fields, and no-OOS-retuning rule.
  - [ ] `p1-yearly-sparse-robust-policy.json` parses and contains `selector_version=yearly_sparse_robust_v1`.
  - [ ] The policy states that if no candidate qualifies, P6 OOS is skipped.

  **QA Scenarios**:
  ```text
  Scenario: Policy completeness
    Tool: powershell + rg
    Steps:
      rg -n "yearly_sparse_robust_v1|150|250|0.15|2023|2024|2025|30 trades|OOS|forbidden" .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p1-yearly-sparse-robust-policy.md
      Get-Content .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p1-yearly-sparse-robust-policy.json | ConvertFrom-Json
    Expected: Selector version and exact thresholds are predeclared before implementation/OOS.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p1-policy-verification.txt
  ```

  **Commit**: NO

- [x] 3. P2 implement training-year breakdown and robust selector with TDD

  **What to do**: Add the smallest read-only selector support. Extend candidate-selection code with a separate `yearly_sparse_robust_v1` path. Parse per-year metrics from generation `csv_path` using the same CSV date/profit conventions as `fitness.holdout`/`fitness.multiyear`. Write artifacts that include aggregate metrics, yearly breakdown, eligible/rejected candidates, config hash, and OOS-blind flags.
  **Must NOT do**: Do not change `sparse_positive_v1`, hard gates, official engines, or `backtest/graph`.

  **Parallelization**: Can Parallel: PARTIAL | Wave 2 | Blocks: P4, P5 | Blocked By: P1

  **References**:
  - Existing selector core: `ai_strategy_loop/controller/_candidate_selection_core.py:80` - follow structure but keep new version separate.
  - Artifact writer: `ai_strategy_loop/controller/_candidate_selection_artifact.py:66`.
  - CSV reader pattern: `ai_strategy_loop/fitness/holdout.py:172` - `_read_holdout_rows`.
  - Multiyear reporting pattern: `ai_strategy_loop/fitness/multiyear.py:73` - `YearMetrics`.
  - Tests: `tests/unit/test_candidate_selection.py:54` - selector test style.

  **Acceptance Criteria**:
  - [ ] Add red tests first in `tests/unit/test_yearly_sparse_robust_selection.py`.
  - [ ] Tests cover: valid all-year candidate selection, total trade count below 150 rejection, one negative training year rejection, one year below 30 trades rejection, missing CSV rejection, OOS-field rejection, deterministic ranking, and `sparse_positive_v1` unchanged.
  - [ ] New artifact has `selector_version=yearly_sparse_robust_v1`, `oos_excluded=true`, `diagnostic_only=false` for fresh freeze, and `forbidden_oos_fields_present=false`.
  - [ ] Existing `tests/unit/test_candidate_selection.py` and `tests/unit/test_sparse_positive_prompt.py` still pass.

  **QA Scenarios**:
  ```text
  Scenario: Red/green selector tests
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m pytest tests/unit/test_yearly_sparse_robust_selection.py -q
      python -m pytest tests/unit/test_yearly_sparse_robust_selection.py tests/unit/test_candidate_selection.py tests/unit/test_sparse_positive_prompt.py -q
    Expected: First run before implementation fails; final run passes.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p2-red-green-tests.txt
  ```

  **Commit**: NO

- [x] 4. P3 predeclare smoke/train/OOS configs and selector-freeze procedure

  **What to do**: Build exact configs under the evidence root. Use existing `sparse_positive_prompt_enabled=true` only in run configs; leave its code default OFF. Train config must use 2023-2025, tick 09:00-09:30, `winner_objective=multiyear`, `graduation_holdout=true`, `holdout_recent_days=60`, prompt logging, equity points, segment feedback, and `max_generations=10`.
  **Must NOT do**: Do not start official loop runs in P3. Do not use 2022/2026 metrics in selector config.

  **Parallelization**: Can Parallel: PARTIAL | Wave 2 | Blocks: P4, P5 | Blocked By: P1

  **References**:
  - Prior train config: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p3-train-config.json`.
  - Sparse prompt config: `ai_strategy_loop/config.py:453` - default-OFF prompt guidance.
  - Multiyear config: `ai_strategy_loop/config.py:247` and `ai_strategy_loop/config.py:266`.
  - Holdout config: `ai_strategy_loop/config.py:67`.
  - OOS config pattern: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p6-config-manifest.json`.

  **Acceptance Criteria**:
  - [ ] `p3-config-manifest.json` records all config paths, run ids, periods, hashes, toggles, and selector version.
  - [ ] Smoke run id: `tick_oosrob_p4_smoke_20260604`, period 2025-01-01 through 2025-03-31, max_generations=3.
  - [ ] Train run id: `tick_oosrob_p5_train_2023_2025_20260604`, period 2023-01-01 through 2025-12-31, max_generations=10.
  - [ ] OOS run ids are predeclared but not executed: `tick_oosrob_p6_seed_2022_20260604`, `tick_oosrob_p6_seed_2026_20260604`, `tick_oosrob_p6_ai_2022_20260604`, `tick_oosrob_p6_ai_2026_20260604`.
  - [ ] JSON files parse as UTF-8 without BOM.

  **QA Scenarios**:
  ```text
  Scenario: Config parse/hash
    Tool: powershell + python
    Steps:
      $env:PYTHONUTF8='1'
      python -c "import json,pathlib; root=pathlib.Path('.omo/evidence/tick-sparse-positive-oos-robustness-20260604'); [json.loads(p.read_bytes().decode('utf-8')) for p in root.glob('p3-*.json')]"
      rg -n "yearly_sparse_robust_v1|tick_oosrob_p5_train|20230101|20251231|multiyear|graduation_holdout" .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p3-config-manifest.json
    Expected: All configs parse and manifest proves predeclared selector/config state.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p3-config-verification.txt
  ```

  **Commit**: NO

- [x] 5. P4 short smoke run and prompt/selector sanity

  **What to do**: Run one short 2025 Q1 smoke with the train-style toggles to prove the pipeline still generates/backtests and prompt logging records `sparse_positive_prompt_enabled=true`. Apply `yearly_sparse_robust_v1` diagnostically only if the smoke period is too short for 2023-2025 yearly checks; record that smoke is not promotion evidence.
  **Must NOT do**: Do not run 2022/2026 OOS. Do not relax thresholds from smoke results.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: P5 | Blocked By: P2, P3

  **References**:
  - CLI entry: `python -m ai_strategy_loop.controller.loop --config-json <cfg> --run-id <id>`.
  - Prompt logging endpoint/source: `ai_strategy_loop/dashboard/app.py:1491`.
  - Prior smoke evidence: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p4-smoke-comparison.md`.

  **Acceptance Criteria**:
  - [ ] `p4-smoke-log.txt` records command, timestamps, exit status, duration, and cleanup.
  - [ ] `p4-smoke-summary.json` records generation rows and prompt logging counts.
  - [ ] Prompt records include `sparse_positive_prompt_enabled=true`.
  - [ ] `p4-smoke-summary.md` states smoke is not OOS or promotion evidence.

  **QA Scenarios**:
  ```text
  Scenario: Official smoke run
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p3-smoke-config.json --run-id tick_oosrob_p4_smoke_20260604
      Query loop_runs.db prompts/generations for tick_oosrob_p4_smoke_20260604.
    Expected: Run exits cleanly or exact blocker is recorded; no OOS rows are created.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p4-smoke-summary.md
  ```

  **Commit**: NO

- [x] 6. P5 fresh 2023-2025 train and `yearly_sparse_robust_v1` freeze

  **What to do**: Run the fresh train config. After completion, apply `yearly_sparse_robust_v1` to training rows only. Write `p5-selected-candidate.json` before any OOS. If no candidate qualifies, write `p5-selector-blocked.md` and skip P6.
  **Must NOT do**: Do not use 2022/2026 OOS data in selection. Do not modify the selected candidate after freeze.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: P6, P7 | Blocked By: P4

  **References**:
  - Fresh run pattern: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p5-train-log.txt`.
  - Selector artifact pattern: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p5-selected-candidate.json`.
  - CSV path field: `ai_strategy_loop/controller/state.py` generations persistence and dashboard run compare.

  **Acceptance Criteria**:
  - [ ] `p5-train-log.txt` records command, timestamps, exit code, duration, timeout/OOM status, and cleanup.
  - [ ] `p5-selected-candidate.json` exists with `selector_version=yearly_sparse_robust_v1`, `oos_excluded=true`, `diagnostic_only=false`, and yearly breakdown.
  - [ ] If selected=false, `p5-selector-blocked.md` exists and P6 OOS is skipped.
  - [ ] If selected=true, selected buy/sell names, gen_no, aggregate metrics, yearly metrics, and config hash are recorded before P6.

  **QA Scenarios**:
  ```text
  Scenario: Fresh robust train
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p3-train-config.json --run-id tick_oosrob_p5_train_2023_2025_20260604
      Apply yearly_sparse_robust_v1 to training rows only.
    Expected: Candidate is frozen before OOS or OOS is honestly blocked.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p5-selected-candidate.json

  Scenario: OOS blindness
    Tool: powershell + rg
    Steps:
      rg -n "oos_2022|oos_2026|seed_2022|seed_2026|ai_2022|ai_2026|post_oos" .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p5-selected-candidate.json
    Expected: No OOS fields are present.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p5-oos-blindness-check.txt
  ```

  **Commit**: NO

- [x] 7. P6 fixed 2022/2026 OOS only if P5 selected a candidate

  **What to do**: If P5 selected a candidate, build fixed seed and AI OOS configs. AI configs must use exact P5 buy/sell names, `bt_refine_from_best=false`, `max_generations=1`, TICK timeframe, and no candidate mutation. If P5 selected=false, write `p6-oos-blocked.md` and do not run OOS.
  **Must NOT do**: Do not reselect, tune, or edit candidate code after any OOS result appears.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: P7 | Blocked By: P5 selected=true

  **References**:
  - Prior fixed OOS manifest: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p6-config-manifest.json`.
  - Seed identity: `Tick_B_902_905_Update_2`, `Tick_S_902_905_Update_2`.
  - OOS pass rule: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p6-oos-comparison.json`.

  **Acceptance Criteria**:
  - [ ] If P5 selected=false, `p6-oos-blocked.md` exists and P6 OOS DB row counts are zero.
  - [ ] If P5 selected=true, `p6-config-manifest.json` records seed/AI configs, hashes, windows, selected strategy identity, and no-mutation flags.
  - [ ] `p6-oos-comparison.json` contains seed_2022, seed_2026, ai_2022, ai_2026 rows or exact blockers.
  - [ ] Candidate identity before and after OOS is unchanged.

  **OOS Pass Rule**:
  - AI profit must be positive in both 2022 and 2026.
  - Combined AI profit must be greater than or equal to combined seed profit.
  - AI max MDD must be less than or equal to seed max MDD.
  - Each AI OOS year must have at least 20 trades.
  - Combined AI OOS must have at least 50 trades.
  - Slippage-stressed AI OOS must remain positive in both years for promotion.

  **QA Scenarios**:
  ```text
  Scenario: Conditional fixed OOS
    Tool: powershell + python
    Steps:
      Read p5-selected-candidate.json.
      If selected=false, assert no P6 run ids exist in generations table.
      If selected=true, run fixed seed/AI OOS configs.
    Expected: OOS is skipped or executed only with a frozen candidate.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p6-oos-comparison.md
  ```

  **Commit**: NO

- [x] 8. P7 slippage, PBO/DSR status, and decision card

  **What to do**: Produce a final decision card. Apply simple advisory slippage haircuts if trade-level cost tooling is unavailable: 0.1%, 0.2%, and 0.3% round-trip approximations documented as advisory. Search for PBO/DSR tooling; run it only if it already exists and is read-only. Otherwise mark it as an advisory blocker.
  **Must NOT do**: Do not promote if OOS fails, slippage-stressed OOS is unavailable/negative, trade count is insufficient, or PBO/DSR is unresolved.

  **Parallelization**: Can Parallel: NO | Wave 5 | Blocks: Final Verification | Blocked By: P5 and conditional P6

  **References**:
  - Prior decision card: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md`.
  - PBO/DSR docs: `docs/research/condition_research/wiki/metrics_glossary.md`.
  - Slippage/PBO guardrails: `.omo/plans/tick-oos-validation-20260603.md` P5.

  **Acceptance Criteria**:
  - [ ] `p7-decision-card.md` includes Executive Verdict, Selector Version, Candidate Identity, Training Yearly Evidence, OOS Evidence, Seed Comparison, Trade Sufficiency, Slippage Status, PBO/DSR Status, Forbidden Actions Check, and Final Verdict.
  - [ ] `PROMOTE_CANDIDATE` appears only if the OOS pass rule, slippage stress, and evidence sufficiency all pass.
  - [ ] Otherwise verdict is `REJECT_CANDIDATE` or `NEEDS_MORE_EVIDENCE`.
  - [ ] No unsupported human-level or seed-superior claim appears.

  **QA Scenarios**:
  ```text
  Scenario: Decision honesty audit
    Tool: powershell + rg
    Steps:
      rg -n "PROMOTE_CANDIDATE|REJECT_CANDIDATE|NEEDS_MORE_EVIDENCE|human|superior|slippage|PBO|DSR|final_approval|export_winner|taskkill" .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p7-decision-card.md
    Expected: Verdict is evidence-bound and forbidden actions are stated as not invoked.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p7-honesty-audit.txt
  ```

  **Commit**: NO

## Final Verification Wave

- [x] F1. Plan compliance audit

  **What to do**: Map every task to evidence and record forbidden-action absence.

  **Acceptance Criteria**:
  - [ ] `final-plan-compliance.txt` maps P0-P7 and F1-F4 to artifacts.
  - [ ] It records whether `final_approval`, `export_winner`, `USER_ACK`, `KHOPENAPI`, `taskkill`, hard-gate edits, engine edits, or `backtest/graph` edits occurred.

  **QA Scenarios**:
  ```text
  Scenario: Compliance audit
    Tool: powershell + rg
    Steps:
      rg -n "^- \[ \]" .omo/plans/tick-sparse-positive-oos-robustness-20260604.md
      Get-ChildItem .omo/evidence/tick-sparse-positive-oos-robustness-20260604
      rg -n "final_approval|export_winner|USER_ACK|KHOPENAPI|taskkill" .omo/evidence/tick-sparse-positive-oos-robustness-20260604
    Expected: Open/completed tasks and forbidden-action evidence are explicit.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/final-plan-compliance.txt
  ```

- [x] F2. Code and branch safety verification

  **What to do**: Run final verification commands while preserving unrelated dirty changes.

  **Acceptance Criteria**:
  - [ ] `final-verification.txt` includes `git diff --check`, `python scripts/verify_nonrelease_sync.py`, protected-path status, and focused pytest output.
  - [ ] Focused selector/prompt/dashboard tests pass or exact blockers are recorded.

  **QA Scenarios**:
  ```text
  Scenario: Final verification
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      git diff --check
      python scripts/verify_nonrelease_sync.py
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      python -m pytest tests/unit/test_yearly_sparse_robust_selection.py tests/unit/test_candidate_selection.py tests/unit/test_sparse_positive_prompt.py tests/unit/test_filter_gate.py tests/unit/test_few_shot.py tests/unit/test_segment_feedback.py tests/unit/test_prompt_logging.py -q
      python -m pytest tests/unit/test_dashboard_prompts.py tests/unit/test_dashboard_research_docs.py tests/unit/test_dashboard_index_compare.py tests/unit/test_variable_correlation.py -q
    Expected: Verification passes or exact unrelated/pre-existing failures are recorded.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/final-verification.txt
  ```

- [x] F3. Dashboard/read-only QA

  **What to do**: If dashboard-visible config/selector artifacts are touched, start an owned alternate-port dashboard, capture read-only route statuses, and clean it up. Leave pre-existing 8770 untouched.

  **Acceptance Criteria**:
  - [ ] `final-dashboard-qa.txt` records exact URLs/statuses and selected base URL.
  - [ ] `final-dashboard-cleanup.txt` records owned server cleanup.
  - [ ] No approval/export action is invoked.

  **QA Scenarios**:
  ```text
  Scenario: Dashboard QA
    Tool: curl.exe
    Steps:
      curl.exe -sS "<owned-base>/health"
      curl.exe -sS "<owned-base>/config/spec"
      curl.exe -sS "<owned-base>/prompts?run_id=tick_oosrob_p5_train_2023_2025_20260604"
      curl.exe -sS "<owned-base>/runs/compare?ids=tick_oosrob_p6_seed_2022_20260604,tick_oosrob_p6_seed_2026_20260604,tick_oosrob_p6_ai_2022_20260604,tick_oosrob_p6_ai_2026_20260604"
    Expected: Read-only routes work or unavailability is explicit.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/final-dashboard-qa.txt
  ```

- [x] F4. Final handoff

  **What to do**: Record final git status, protected-path status, final verdict, selected candidate identity if any, and recommended next command.

  **Acceptance Criteria**:
  - [ ] `final-scope-fidelity.txt` includes branch status, protected-path status, final verdict from P7, selected candidate identity if any, and statement that this is research validation, not production promotion.
  - [ ] `.omo/boulder.json` is marked completed only after all required evidence exists.

  **QA Scenarios**:
  ```text
  Scenario: Final handoff
    Tool: powershell + rg
    Steps:
      git status --short --branch
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      rg -n "Final Verdict|PROMOTE_CANDIDATE|REJECT_CANDIDATE|NEEDS_MORE_EVIDENCE" .omo/evidence/tick-sparse-positive-oos-robustness-20260604/p7-decision-card.md
    Expected: Final state and next command are explicit.
    Evidence: .omo/evidence/tick-sparse-positive-oos-robustness-20260604/final-scope-fidelity.txt
  ```

## Commit Strategy
- Commit: NO by default during `$start-work`; user can request commit after review.
- If committing later, stage files explicitly and use Korean commit title/body per project rules.

## Success Criteria
- `yearly_sparse_robust_v1` is predeclared, tested, and separate from `sparse_positive_v1`.
- A fresh candidate must prove aggregate sparse-positive quality plus 2023/2024/2025 yearly robustness before OOS.
- Fixed 2022/2026 OOS is run only for a frozen candidate.
- Final verdict is evidence-bound and does not overclaim human-level performance.

## Recommended Commands
```powershell
$start-work tick-sparse-positive-oos-robustness-20260604
```

Optional high-accuracy review:
```powershell
high accuracy review .omo/plans/tick-sparse-positive-oos-robustness-20260604.md
```
