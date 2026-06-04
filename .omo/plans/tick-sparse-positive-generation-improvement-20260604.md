# TICK Sparse-Positive Generation Improvement 20260604

## TL;DR
> **Summary**: Improve the TICK generation prompt/constraint path so a fresh 2023-2025 research run can produce at least one OOS-blind `sparse_positive_v1` eligible candidate before any 2022/2026 OOS is attempted. This plan targets candidate-generation quality, not gate relaxation or production promotion.
> **Deliverables**:
> - Safety snapshot and canonical reread
> - Failure taxonomy from the prior blocked P4 run
> - Predeclared sparse-positive generation policy
> - Default-OFF prompt/constraint toggle implementation plan for `sparse_positive_prompt_enabled`
> - Focused TDD coverage for OFF byte identity, ON prompt directives, config wiring, generator prompt logging, and selector freeze discipline
> - Short smoke A/B run evidence
> - Fresh 2023-2025 selector-frozen train run
> - Fixed 2022/2026 OOS only if a candidate is frozen first
> - Final decision card with slippage/PBO/DSR honesty
> **Effort**: XL
> **Parallel**: Limited - tests and static audits can run in parallel; official loop/backtest runs are serialized.
> **Critical Path**: P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7 -> Final Verification

## Context
### Original Request
The user asked to run the recommended `$ulw-plan` command directly:

```powershell
$ulw-plan TICK sparse-positive candidate generation prompt and constraint improvement plan. Use .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p6-decision-card.md, p4-selected-candidate.json, p4-selector-blocked.md, final-verification.txt as canonical evidence. Keep hard gates, official engines, and backtest/graph unchanged; keep new toggles default OFF; forbid OOS-after-the-fact reselection; require predeclared selector freeze before any OOS.
```

### Interview Summary
- No extra user questions are blocking because the user explicitly asked to proceed.
- The prior plan completed with verdict `NEEDS_MORE_EVIDENCE`.
- The previous selector rule prevented a training-negative candidate from reaching OOS.
- The current bottleneck is generation quality: fresh 2023-2025 P4 produced no candidate eligible under `sparse_positive_v1`.

### Metis Review
- Metis consultation was attempted twice:
  - `tick_sparse_positive_generation_gap_analysis`
  - `tick_sparse_positive_gap_analysis_small`
- Both timed out without substantive response after follow-up/closure.
- Gap controls applied directly in this plan:
  - Freeze all generation-policy thresholds before new OOS.
  - Keep implementation behind a new default-OFF toggle.
  - Preserve OFF byte identity with unit tests.
  - Run smoke A/B before the long train run.
  - Apply `sparse_positive_v1` to training rows only.
  - Skip OOS if no candidate is frozen.
  - Keep final verdict restricted to `PROMOTE_CANDIDATE`, `REJECT_CANDIDATE`, or `NEEDS_MORE_EVIDENCE`.

### Canonical Evidence
- `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p6-decision-card.md`
- `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-selected-candidate.json`
- `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-selector-blocked.md`
- `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/final-verification.txt`
- `docs/AGENT_HANDOFF.md`

### Ground Truth From Prior Run
- Run id: `tick_sel_sparse_p4_train_2023_2025_20260604`
- Period: 2023-01-01 through 2025-12-31
- Timeframe/window: tick, 09:00-09:30
- Selector: `sparse_positive_v1`
- Selected: `false`
- Blocked: `true`
- Eligible candidates: 0
- Rejections:
  - gen1: profit negative, MDD 167.56, trades 4212
  - gen2: profit negative, MDD 43.76, trades 688
  - gen4: profit negative, MDD 39.05, trades 687
  - gen5: profit negative, MDD 13.4, trades 111
- P5 OOS was correctly skipped because no candidate was frozen.

## Work Objectives
### Core Objective
Improve TICK condition generation so the system has a realistic chance to produce positive-profit, low-MDD, non-overtrading candidates eligible for `sparse_positive_v1`, while preserving all existing hard gates and OOS discipline.

### Deliverables
- Evidence root: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/`
- Draft generation policy: `p1-generation-quality-policy.md`
- Source implementation behind default-OFF `sparse_positive_prompt_enabled`
- Focused tests and verification outputs
- Smoke A/B run artifacts
- Fresh selector-freeze artifact
- Conditional fixed OOS comparison or explicit OOS-blocked artifact
- Final decision card

### Definition of Done
- `git diff --check` exits 0.
- `python scripts/verify_nonrelease_sync.py` exits 0.
- Protected path status is empty:
  ```powershell
  git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
  ```
- Focused unit tests pass.
- `sparse_positive_prompt_enabled=False` preserves existing prompt/generator behavior.
- Any OOS run has a preceding selected-candidate artifact with `oos_excluded=true`.
- No final decision claims human superiority unless OOS, slippage, PBO/DSR, and evidence sufficiency all pass.

### Must Have
- Use `PYTHONUTF8=1`.
- New feature toggle default: `sparse_positive_prompt_enabled=False`.
- OFF path must be byte-identical or behavior-identical to current default behavior.
- ON prompt must explicitly target:
  - positive training profit
  - MDD target <= 10.0
  - trade_count corridor 20-250
  - daily_avg_trades >= 0.05
  - payoff_ratio >= 1.05
  - no high-frequency overtrading
  - sell-side MDD/giveback control
- `sparse_positive_v1` remains the selector; do not weaken selector thresholds after OOS.
- Candidate freeze must happen before any 2022/2026 OOS.
- If no candidate qualifies, skip OOS and write a blocker artifact.

### Must NOT Have
- No edits to `ai_strategy_loop/fitness/score.py` hard gates.
- No edits to `backtest/backengine_*.py`, `backtest/back_static.py`, or official backtest engine behavior.
- No edits to `backtest/graph/`.
- No `final_approval`, no `export_winner`, no production strategy DB writes.
- No V3K gate advancement, USER_ACK creation, KHOPENAPI login/connect, or live order wiring.
- No blanket `taskkill`; stop only owned PIDs/sessions.
- No OOS-after-the-fact candidate change.
- No OOS use in prompt tuning, selector tuning, or P5 candidate choice.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.

- Test decision: TDD using pytest.
- Manual QA: real commands, real dashboard GETs if dashboard is touched, real loop/backtest run artifacts.
- Evidence root: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/`
- Baseline before source changes:
  ```powershell
  $env:PYTHONUTF8='1'
  python -m pytest tests/unit/test_filter_gate.py tests/unit/test_few_shot.py tests/unit/test_segment_feedback.py tests/unit/test_candidate_selection.py -q
  ```
- Focused post-change tests:
  ```powershell
  $env:PYTHONUTF8='1'
  python -m pytest tests/unit/test_sparse_positive_prompt.py tests/unit/test_filter_gate.py tests/unit/test_few_shot.py tests/unit/test_segment_feedback.py tests/unit/test_prompt_logging.py tests/unit/test_candidate_selection.py -q
  ```
- Final safety:
  ```powershell
  git diff --check
  python scripts/verify_nonrelease_sync.py
  git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
  ```

## Execution Strategy
### Parallel Execution Waves
Wave 1: P0 and P1 are sequential foundations.
Wave 2: P2 source/TDD work and P3 config/evidence tooling can be partially parallel after P1.
Wave 3: P4 smoke A/B runs after P2/P3.
Wave 4: P5 fresh 2023-2025 train after P4.
Wave 5: P6 OOS only if P5 selects a candidate.
Wave 6: P7 decision card and final verification.

### Dependency Matrix
| Task | Depends On | Blocks |
|---|---|---|
| P0 | none | P1 |
| P1 | P0 | P2, P3 |
| P2 | P1 | P4 |
| P3 | P1 | P4 |
| P4 | P2, P3 | P5 |
| P5 | P4 | P6, P7 |
| P6 | P5 selected=true | P7 |
| P7 | P5 and conditional P6 | F1-F4 |
| F1-F4 | P0-P7 | completion |

## TODOs

- [ ] 1. P0 safety snapshot and canonical reread

  **What to do**: Create the evidence root. Capture branch, HEAD, dirty worktree, protected-path status, Boulder state, dashboard status if any, and canonical evidence summaries.
  **Must NOT do**: Do not clean the dirty worktree. Do not stop existing dashboard processes. Do not run long backtests.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: P1 | Blocked By: none

  **References**:
  - Pattern: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/final-scope-fidelity.txt` - prior final handoff shape.
  - Canonical: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p6-decision-card.md` - final prior verdict.
  - Canonical: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-selected-candidate.json` - selector artifact with selected=false.
  - Project rules: `AGENTS.md` - protected paths and verification commands.

  **Acceptance Criteria**:
  - [ ] `p0-safety-snapshot.txt` records branch, HEAD, dirty state, protected path status, Boulder state, and date/time.
  - [ ] `p0-canonical-reread.txt` records the exact canonical files read and the prior `NEEDS_MORE_EVIDENCE` facts.
  - [ ] Protected-path status is empty or explicitly pre-existing/unrelated.

  **QA Scenarios**:
  ```text
  Scenario: Safety snapshot
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      New-Item -ItemType Directory -Force .omo/evidence/tick-sparse-positive-generation-improvement-20260604
      git status --short --branch
      git rev-parse HEAD
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      Get-Content .omo/boulder.json
      Get-Content .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p6-decision-card.md
    Expected: Evidence root exists and no protected path is modified.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p0-safety-snapshot.txt

  Scenario: Canonical fact check
    Tool: powershell + rg
    Steps:
      rg -n "NEEDS_MORE_EVIDENCE|selected: false|eligible_candidates|profit negative|MDD|OOS" .omo/evidence/tick-selection-rule-sparse-gen5-research-20260604
    Expected: Prior blocked state and no-OOS fact are visible.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p0-canonical-reread.txt
  ```

  **Commit**: NO

- [ ] 2. P1 failure taxonomy and predeclared generation policy

  **What to do**: Convert the prior P4 rejection facts into a predeclared generation-quality policy before source changes or new OOS. Define the exact prompt targets and explicitly state that the policy is advisory generation guidance, not a hard-gate or selector relaxation.
  **Must NOT do**: Do not tune thresholds from any future OOS. Do not weaken `sparse_positive_v1`.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: P2, P3 | Blocked By: P0

  **References**:
  - Evidence: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-selector-blocked.md` - generation failure taxonomy.
  - Selector: `ai_strategy_loop/controller/_candidate_selection_core.py:19` - `SelectorThresholds`.
  - Selector: `ai_strategy_loop/controller/_candidate_selection_core.py:80` - `select_sparse_positive_v1`.
  - Tests: `tests/unit/test_candidate_selection.py:1` - selector contract.

  **Acceptance Criteria**:
  - [ ] `p1-failure-taxonomy.md` classifies prior failures into negative-profit, high-MDD, overtrade, timeout/missing-CSV, and sparse-but-still-negative.
  - [ ] `p1-generation-quality-policy.md` predeclares ON prompt targets: profit > 0, MDD <= 10, trade_count 20-250, daily_avg_trades >= 0.05, payoff_ratio >= 1.05.
  - [ ] `p1-generation-quality-policy.json` records the same targets machine-readably.
  - [ ] The policy states it is generation guidance only and cannot override hard gates or selector rules.

  **QA Scenarios**:
  ```text
  Scenario: Policy completeness
    Tool: powershell + rg
    Steps:
      rg -n "profit > 0|MDD <= 10|20-250|daily_avg_trades >= 0.05|payoff_ratio >= 1.05|hard gate|selector" .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p1-generation-quality-policy.md
    Expected: All targets and non-relaxation guardrails are explicit before implementation.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p1-generation-quality-policy.md

  Scenario: Machine-readable policy
    Tool: powershell
    Steps:
      Get-Content .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p1-generation-quality-policy.json | ConvertFrom-Json
    Expected: JSON parses and contains selector_version=sparse_positive_v1.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p1-generation-quality-policy.json
  ```

  **Commit**: NO

- [ ] 3. P2 implement default-OFF sparse-positive prompt guidance with TDD

  **What to do**: Add the smallest source support for a new default-OFF toggle `sparse_positive_prompt_enabled`. Wire it through `LoopConfig`, `launch_config`, `controller/state` active config allow-lists if needed, `_generate_pair`, `generate_strategy`, and `build_messages`. The ON path must inject kind-specific guidance: buy prompts reduce overtrading and target sparse-positive entry; sell prompts protect MDD/giveback and payoff. OFF path must preserve current output/behavior.
  **Must NOT do**: Do not edit `ai_strategy_loop/fitness/score.py`, official backtest engines, `backtest/graph/`, or selector thresholds. Do not make the new guidance always-on.

  **Parallelization**: Can Parallel: PARTIAL | Wave 2 | Blocks: P4 | Blocked By: P1

  **References**:
  - Config: `ai_strategy_loop/config.py:17` - `LoopConfig`.
  - Existing toggles: `ai_strategy_loop/config.py:303` through `ai_strategy_loop/config.py:466` - default-OFF prompt/feedback toggles.
  - Prompt entry: `ai_strategy_loop/brain/prompt.py:156` - `build_messages`.
  - Existing prompt blocks: `ai_strategy_loop/brain/prompt.py:351`, `:369`, `:407`, `:536`.
  - Generator entry: `ai_strategy_loop/brain/generator.py:55` - `generate_strategy`.
  - Loop wiring: `ai_strategy_loop/controller/loop.py:525` - `_generate_pair`.
  - Loop config pass-through: `ai_strategy_loop/controller/loop.py:670` through `:710`.
  - State config patterns: `ai_strategy_loop/controller/state.py` config allow-list entries near existing prompt toggles.
  - Test patterns: `tests/unit/test_filter_gate.py:133`, `tests/unit/test_few_shot.py:276`, `tests/unit/test_segment_feedback.py:176`.

  **Acceptance Criteria**:
  - [ ] Add red tests first in `tests/unit/test_sparse_positive_prompt.py`.
  - [ ] `LoopConfig().sparse_positive_prompt_enabled is False`.
  - [ ] `LoopConfig.from_dict({"sparse_positive_prompt_enabled": True})` parses true.
  - [ ] `build_messages(..., sparse_positive_prompt_enabled=False)` is byte-identical to current default for buy and sell.
  - [ ] ON buy prompt includes sparse-positive targets and overtrade avoidance.
  - [ ] ON sell prompt includes MDD/giveback/payoff protection.
  - [ ] `generate_strategy` prompt logging `injected_features` includes `sparse_positive_prompt_enabled`.
  - [ ] `_generate_pair` passes the config flag to buy and sell generation.
  - [ ] `launch_config` exposes the toggle as default false if dashboard config spec tracks prompt toggles.

  **QA Scenarios**:
  ```text
  Scenario: Red then green unit tests
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m pytest tests/unit/test_sparse_positive_prompt.py -q
      # First run before implementation should fail because the toggle does not exist.
      # After implementation, rerun the same command.
    Expected: Red failure is captured first; green run passes after implementation.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p2-red-green-tests.txt

  Scenario: Existing prompt toggles unaffected
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m pytest tests/unit/test_filter_gate.py tests/unit/test_few_shot.py tests/unit/test_segment_feedback.py tests/unit/test_prompt_logging.py -q
    Expected: Existing prompt/generator contracts remain green.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p2-regression-tests.txt

  Scenario: No protected path mutation
    Tool: powershell
    Steps:
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
    Expected: Empty output.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p2-protected-path-status.txt
  ```

  **Commit**: NO

- [ ] 4. P3 predeclare run configs and selector-freeze tooling

  **What to do**: Create exact smoke and train configs under the evidence root. Base them on `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-train-config.json`, but add `sparse_positive_prompt_enabled` only for ON configs. Predeclare all run ids, windows, hashes, and selector application steps. Confirm existing candidate-selection helper can write artifacts; if a tiny evidence-only script is needed, add it with tests.
  **Must NOT do**: Do not start the long run in P3. Do not use any OOS metrics in selector config or prompt policy.

  **Parallelization**: Can Parallel: PARTIAL | Wave 2 | Blocks: P4 | Blocked By: P1

  **References**:
  - Prior train config: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-train-config.json`.
  - Selector public API: `ai_strategy_loop/controller/candidate_selection.py:1`.
  - Artifact parser/writer: `ai_strategy_loop/controller/_candidate_selection_artifact.py`.
  - Selector tests: `tests/unit/test_candidate_selection.py:1`.

  **Acceptance Criteria**:
  - [ ] `p3-config-manifest.json` records all config paths, run ids, periods, hashes, and toggle values.
  - [ ] Smoke OFF run id: `tick_spgen_p4_smoke_off_20260604`.
  - [ ] Smoke ON run id: `tick_spgen_p4_smoke_on_20260604`.
  - [ ] Fresh train run id: `tick_spgen_p5_train_2023_2025_20260604`.
  - [ ] Smoke configs use tick 09:00-09:30, 2025-01-01 through 2025-03-31, `max_generations=3`, prompt logging ON.
  - [ ] Fresh train config uses tick 09:00-09:30, 2023-01-01 through 2025-12-31, `max_generations=8`, prompt logging ON, `sparse_positive_prompt_enabled=true`.
  - [ ] JSON files are UTF-8 without BOM and parse with Python `json.load`.
  - [ ] `p3-selector-freeze-procedure.md` states selector input fields and OOS exclusions.

  **QA Scenarios**:
  ```text
  Scenario: Config JSON parse and hash
    Tool: powershell + python
    Steps:
      $env:PYTHONUTF8='1'
      python - <<'PY'
      import json, pathlib
      root = pathlib.Path('.omo/evidence/tick-sparse-positive-generation-improvement-20260604')
      for p in root.glob('p3-*.json'):
          data = p.read_bytes()
          assert not data.startswith(b'\xef\xbb\xbf'), p
          json.loads(data.decode('utf-8'))
      PY
    Expected: All P3 JSON config/manifest files parse and have no BOM.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p3-config-verification.txt

  Scenario: Selector freeze procedure is OOS-blind
    Tool: powershell + rg
    Steps:
      rg -n "oos_excluded|forbidden_oos_fields_present|sparse_positive_v1|training rows only" .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p3-selector-freeze-procedure.md
    Expected: Freeze procedure explicitly excludes OOS fields.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p3-selector-freeze-procedure.md
  ```

  **Commit**: NO

- [ ] 5. P4 short smoke A/B run, no OOS

  **What to do**: Run two short official loop smoke runs: OFF baseline and ON sparse-positive prompt. Compare generation failures, prompt records, trade/MDD/profit shape, and selector outcome. This is pipeline evidence only, not promotion evidence.
  **Must NOT do**: Do not run 2022/2026 OOS in P4. Do not tune thresholds after seeing smoke results. Do not treat smoke winner as production candidate.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: P5 | Blocked By: P2, P3

  **References**:
  - CLI entry: `python -m ai_strategy_loop.controller.loop --config-json <cfg> --run-id <id>`.
  - Prompt route: `ai_strategy_loop/dashboard/app.py:1491` - `/prompts` endpoint if dashboard QA is used.
  - Prior cleanup pattern: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-cleanup-check.txt`.

  **Acceptance Criteria**:
  - [ ] `p4-smoke-off-log.txt` records command, start/end time, PID/session if applicable, exit status, duration, and run id.
  - [ ] `p4-smoke-on-log.txt` records the same for the ON run.
  - [ ] `p4-smoke-comparison.json` compares gen_count, generation_error_count, best_graded, gate_passed_count, prompt_count, selected flag, rejection reasons.
  - [ ] ON prompt records include `sparse_positive_prompt_enabled=true` in injected features when prompt logging is enabled.
  - [ ] `p4-smoke-comparison.md` states that smoke is not OOS or promotion evidence.

  **QA Scenarios**:
  ```text
  Scenario: Smoke OFF and ON official loop runs
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p3-smoke-off-config.json --run-id tick_spgen_p4_smoke_off_20260604
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p3-smoke-on-config.json --run-id tick_spgen_p4_smoke_on_20260604
    Expected: Both runs exit cleanly or exact blockers are recorded; no OOS rows are created.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p4-smoke-comparison.md

  Scenario: Prompt logging check
    Tool: powershell + python
    Steps:
      Query `ai_strategy_loop/state/loop_runs.db` prompts table for both smoke run ids.
      Verify ON records include sparse_positive_prompt_enabled=true.
    Expected: Prompt logging proves the ON prompt path was active.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p4-prompt-logging-check.txt

  Scenario: Owned process cleanup
    Tool: powershell
    Steps:
      Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*tick_spgen_p4_smoke*' }
    Expected: No owned smoke loop process remains after completion.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p4-cleanup-check.txt
  ```

  **Commit**: NO

- [ ] 6. P5 fresh 2023-2025 selector-frozen train run

  **What to do**: Run the fresh 2023-2025 train config with `sparse_positive_prompt_enabled=true`. After completion, apply `sparse_positive_v1` to training rows only and write `p5-selected-candidate.json` before any OOS.
  **Must NOT do**: Do not use 2022/2026 OOS data in selection. Do not change the candidate after selection. Do not weaken hard gates, selector thresholds, or prompt policy from P1.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: P6, P7 | Blocked By: P4

  **References**:
  - Prior run blocker: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-selector-blocked.md`.
  - Selector helper: `ai_strategy_loop/controller/candidate_selection.py:1`.
  - Selector thresholds: `ai_strategy_loop/controller/_candidate_selection_core.py:19`.
  - Prior train log pattern: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-train-log.txt`.

  **Acceptance Criteria**:
  - [ ] `p5-train-log.txt` records command, timestamps, run id, exit code, timeout/OOM status, duration, and cleanup.
  - [ ] `p5-selected-candidate.json` exists and has `oos_excluded=true`, `diagnostic_only=false`, and `forbidden_oos_fields_present=false`.
  - [ ] If selected=false, `p5-selector-blocked.md` exists and P6 OOS is skipped.
  - [ ] If selected=true, selected buy/sell names, gen_no, bucket, and metrics are recorded before P6.
  - [ ] No protected path status output.

  **QA Scenarios**:
  ```text
  Scenario: Fresh selector-frozen train
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      python -m ai_strategy_loop.controller.loop --config-json .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p3-train-config.json --run-id tick_spgen_p5_train_2023_2025_20260604
      Apply sparse_positive_v1 to loop_runs.db rows for tick_spgen_p5_train_2023_2025_20260604.
    Expected: Candidate is frozen before OOS or OOS is honestly blocked.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p5-selected-candidate.json

  Scenario: OOS blindness
    Tool: powershell + rg
    Steps:
      rg -n "oos_2022|oos_2026|seed_2022|seed_2026|ai_2022|ai_2026" .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p5-selected-candidate.json
    Expected: No OOS fields are present.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p5-oos-blindness-check.txt
  ```

  **Commit**: NO

- [ ] 7. P6 fixed 2022/2026 OOS only if P5 selected a candidate

  **What to do**: If P5 selected a candidate, build fixed seed and AI OOS configs for 2022 and 2026. AI configs must use exact P5 buy/sell names, `bt_refine_from_best=false`, `max_generations=1`, TICK timeframe, and no candidate mutation. If P5 selected=false, write `p6-oos-blocked.md` and do not run OOS.
  **Must NOT do**: Do not reselect, tune, or edit candidate code after any OOS result appears.

  **Parallelization**: Can Parallel: NO | Wave 5 | Blocks: P7 | Blocked By: P5 selected=true

  **References**:
  - Prior OOS discipline: `.omo/plans/tick-selection-rule-sparse-gen5-research-20260604.md` P5.
  - Prior OOS rejection evidence: `.omo/evidence/tick-oos-dashboard-validation-20260604/p6-decision-card.md`.
  - Seed identity: `Tick_B_902_905_Update_2`, `Tick_S_902_905_Update_2`.

  **Acceptance Criteria**:
  - [ ] If P5 selected=false, `p6-oos-blocked.md` exists and all P6 OOS DB row counts are zero.
  - [ ] If P5 selected=true, `p6-config-manifest.json` records seed/AI configs, hashes, windows, selected strategy identity, and no-mutation flags.
  - [ ] `p6-oos-comparison.json` contains seed_2022, seed_2026, ai_2022, ai_2026 rows or exact blockers.
  - [ ] `p6-oos-comparison.md` applies the predeclared pass rule.
  - [ ] AI candidate identity before and after OOS is unchanged.

  **OOS Pass Rule**:
  - AI profit must be positive in both 2022 and 2026.
  - Combined AI profit must be greater than or equal to combined seed profit.
  - AI max MDD must be less than or equal to seed max MDD.
  - Each AI OOS year must have at least 20 trades or verdict becomes `NEEDS_MORE_EVIDENCE`.
  - Combined AI OOS must have at least 50 trades.
  - Slippage-stressed AI OOS must remain positive in both years for promotion.

  **QA Scenarios**:
  ```text
  Scenario: Conditional OOS guard
    Tool: powershell + python
    Steps:
      Read p5-selected-candidate.json.
      If selected=false, assert no P6 OOS run ids have rows in loop_runs.db.
      If selected=true, run fixed seed/AI OOS configs.
    Expected: OOS is either honestly skipped or executed with a frozen candidate only.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p6-oos-comparison.md

  Scenario: Candidate identity immutability
    Tool: powershell + python
    Steps:
      Compare P5 selected buy/sell names with AI OOS config buy/sell names and resulting strategy names.
    Expected: No candidate mutation or reselection occurs after OOS starts.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p6-identity-check.txt
  ```

  **Commit**: NO

- [ ] 8. P7 slippage, PBO/DSR status, and decision card

  **What to do**: Produce a final decision card. Run slippage/PBO/DSR diagnostics if tooling exists. If tooling is missing or no candidate/OOS exists, record explicit advisory blockers. The final verdict must be one of `PROMOTE_CANDIDATE`, `REJECT_CANDIDATE`, or `NEEDS_MORE_EVIDENCE`.
  **Must NOT do**: Do not promote when P5 selected=false, P6 skipped, OOS trade count is too sparse, OOS fails, slippage fails/unavailable, or PBO/DSR is unresolved.

  **Parallelization**: Can Parallel: NO | Wave 6 | Blocks: Final Verification | Blocked By: P5 and conditional P6

  **References**:
  - Prior decision card: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p6-decision-card.md`.
  - Prior final verification: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/final-verification.txt`.
  - Slippage/PBO/DSR blocker policy: prior P6 card sections "Slippage Status" and "PBO/DSR Status".

  **Acceptance Criteria**:
  - [ ] `p7-decision-card.md` includes Executive Verdict, Generation Toggle, Candidate Identity, Training Evidence, OOS Evidence, Seed Comparison, Trade-Count Sufficiency, Slippage Status, PBO/DSR Status, Forbidden Actions Check, and Final Verdict.
  - [ ] `PROMOTE_CANDIDATE` appears only if P6 pass rule, slippage-stressed positive OOS, and evidence sufficiency all pass.
  - [ ] Otherwise verdict is `REJECT_CANDIDATE` or `NEEDS_MORE_EVIDENCE`.
  - [ ] No unsupported human-superiority claim appears.

  **QA Scenarios**:
  ```text
  Scenario: Decision honesty audit
    Tool: powershell + rg
    Steps:
      rg -n "PROMOTE_CANDIDATE|REJECT_CANDIDATE|NEEDS_MORE_EVIDENCE|human|superior|slippage|PBO|DSR|final_approval|export_winner|taskkill" .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md
    Expected: Verdict is evidence-bound and forbidden actions are stated as not invoked.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md

  Scenario: Promotion blocker audit
    Tool: powershell + rg
    Steps:
      rg -n "blocked|not run|unavailable|too sparse|failed|NEEDS_MORE_EVIDENCE|REJECT_CANDIDATE" .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md
    Expected: Any missing OOS/slippage/PBO/DSR evidence blocks promotion explicitly.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-verification.txt
  ```

  **Commit**: NO

## Final Verification Wave

- [ ] F1. Plan compliance audit

  **What to do**: Map every task to evidence and record forbidden-action absence.

  **Acceptance Criteria**:
  - [ ] `final-plan-compliance.txt` maps P0-P7 and F1-F4 to artifacts.
  - [ ] It records whether `final_approval`, `export_winner`, `USER_ACK`, `KHOPENAPI`, `taskkill`, hard-gate edits, engine edits, or `backtest/graph` edits occurred.

  **QA Scenarios**:
  ```text
  Scenario: Compliance audit
    Tool: powershell + rg
    Steps:
      rg -n "^- \[ \]" .omo/plans/tick-sparse-positive-generation-improvement-20260604.md
      Get-ChildItem .omo/evidence/tick-sparse-positive-generation-improvement-20260604
      rg -n "final_approval|export_winner|USER_ACK|KHOPENAPI|taskkill" .omo/evidence/tick-sparse-positive-generation-improvement-20260604
    Expected: Open/completed tasks and forbidden-action evidence are explicit.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/final-plan-compliance.txt
  ```

- [ ] F2. Code and branch safety verification

  **What to do**: Run final verification commands, preserving unrelated dirty changes.

  **Acceptance Criteria**:
  - [ ] `final-verification.txt` includes `git diff --check`, `python scripts/verify_nonrelease_sync.py`, protected-path status, and focused pytest output.
  - [ ] Focused prompt/generator/selector/dashboard tests pass or exact blockers are recorded.

  **QA Scenarios**:
  ```text
  Scenario: Final verification
    Tool: powershell
    Steps:
      $env:PYTHONUTF8='1'
      git diff --check
      python scripts/verify_nonrelease_sync.py
      git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
      python -m pytest tests/unit/test_sparse_positive_prompt.py tests/unit/test_filter_gate.py tests/unit/test_few_shot.py tests/unit/test_segment_feedback.py tests/unit/test_prompt_logging.py tests/unit/test_candidate_selection.py -q
      python -m pytest tests/unit/test_dashboard_prompts.py tests/unit/test_dashboard_research_docs.py tests/unit/test_dashboard_index_compare.py tests/unit/test_variable_correlation.py -q
    Expected: Verification passes or exact unrelated/pre-existing failures are recorded.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/final-verification.txt
  ```

- [ ] F3. Dashboard/read-only QA if dashboard surface is touched

  **What to do**: If launch config, prompt route, run comparison, or dashboard-visible config is touched, capture read-only statuses and cleanup receipt for owned server only.

  **Acceptance Criteria**:
  - [ ] `final-dashboard-qa.txt` records exact URLs/statuses and selected base URL.
  - [ ] No approval/export action is invoked.

  **QA Scenarios**:
  ```text
  Scenario: Dashboard QA
    Tool: curl.exe
    Steps:
      curl.exe -sS "<base>/health"
      curl.exe -sS "<base>/config/spec"
      curl.exe -sS "<base>/prompts?run_id=tick_spgen_p4_smoke_on_20260604"
      curl.exe -sS "<base>/runs/compare?ids=tick_spgen_p4_smoke_off_20260604,tick_spgen_p4_smoke_on_20260604"
    Expected: Read-only routes work or unavailability is explicit.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/final-dashboard-qa.txt
  ```

- [ ] F4. Final handoff

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
      rg -n "Final Verdict|PROMOTE_CANDIDATE|REJECT_CANDIDATE|NEEDS_MORE_EVIDENCE" .omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md
    Expected: Final state and next command are explicit.
    Evidence: .omo/evidence/tick-sparse-positive-generation-improvement-20260604/final-scope-fidelity.txt
  ```

## Commit Strategy
- Commit: NO by default during `$start-work`; user can request a commit after review.
- If committing later, stage files explicitly and use Korean commit title/body per project rules.

## Success Criteria
- The sparse-positive generation improvement is behind a default-OFF toggle.
- OFF path preserves current behavior.
- ON path is visible in prompt logging and pushes generation away from negative-profit/high-MDD/overtrade patterns.
- Smoke evidence proves the new path runs without breaking generation.
- Fresh 2023-2025 training either freezes a candidate before OOS or blocks honestly.
- 2022/2026 OOS is run only for a frozen candidate.
- Final verdict is evidence-bound and does not overclaim human-level performance.

## Recommended Commands
```powershell
$start-work tick-sparse-positive-generation-improvement-20260604
```

Optional high-accuracy review before execution:
```powershell
high accuracy review .omo/plans/tick-sparse-positive-generation-improvement-20260604.md
```
