# Lattice Condition Generation V2 Risk/Sell Repair Review Plan

작성일: 2026-07-09

## TL;DR

> **Summary**: v2 body 8개 후보는 daily trade coverage는 확보했지만 전부 음수 손익과 MDD 초과로 실패했다. 다음 작업은 새 후보를 바로 만들지 말고, 기존 8개 결과의 손실/MDD 원인을 sell/risk/hold-time/time/family 축으로 분해해 재설계 가치가 있는지 결정하는 것이다.
> **Deliverables**:
> - v2 body 8개 row-level failure decomposition
> - sell/risk clause audit
> - repair 가능/불가 판단표
> - 다음 후보 생성 여부 결정
> - 다음 실행 명령어
> **Effort**: Short, 1~2시간
> **Parallel**: NO
> **Critical Path**: source read -> row/csv decomposition -> strategy body audit -> repair feasibility decision -> handoff

## Context

### Original Request

추천 명령어 실행:

```text
$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v2_risk_sell_repair_review_20260709.md
```

### Current State

Latest committed boundary:

- Commit: `9b20cfdf`
- Handoff: `docs/update_log/2026-07-08_lattice_v2_to_plan_d_conditional_overnight_handoff.md`
- Limited replay result: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_body8_min_warm64_limited_replay_result_20260708.json`
- Stop decision: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_to_plan_d_stop_decision_20260708.json`

### Key Evidence

| Metric | Value |
|---|---:|
| replay run_id | `lat_lattice_v2_body8_min_warm64_20260708` |
| official profile | min full-period warm64 |
| period | 2025-04-07 ~ 2026-02-27 |
| tested candidates | 8 |
| honest rows | 8/8 |
| ok rows | 7 |
| error rows | 1 |
| gate_passed | 0 |
| survivor | 0 |
| hold | 0 |
| no_go | 8 |
| profit range | -881,171,389 ~ -101,728,684 |
| MDD range | 89.63 ~ 441.67 |
| daily avg trades range | 20.5 ~ 143.9 |

Interpretation: daily trade scarcity was not the blocker. The blocker was negative profit plus MDD far above the official cap.

### Local Gap Audit

Subagent delegation was not used because the active multi-agent tool contract only allows spawning when the user explicitly asks for delegation/subagents. The same gap-audit function is handled locally here.

| Risk | Resolution in this plan |
|---|---|
| Accidentally continuing Plan D | Explicitly forbidden; no survivor exists. |
| Re-running backtests during analysis | Explicitly forbidden; only existing JSON/CSV is read. |
| Treating MDD gate as too strict without proof | Plan requires row/csv decomposition before any gate discussion. |
| Designing new seeds before understanding loss cause | New seed generation is out of scope. |
| Mutating DB or runtime state | DB INSERT/UPDATE/DELETE all forbidden. |

## Work Objectives

### Core Objective

Determine whether the v2 condition-generation approach has a repairable sell/risk defect or whether this branch should be stopped before more candidate generation.

### Deliverables

1. `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_failure_decomposition_20260709.json`
2. `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_failure_decomposition_20260709.md`
3. `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_repair_decision_20260709.json`
4. `docs/update_log/2026-07-09_lattice_v2_risk_sell_repair_review_handoff.md`
5. If repair is justified, a next plan command for a dry-run-only repair page.

### Definition of Done

- All three read-first source files are read to EOF and recorded with line_count and sha256.
- Each of the 8 candidates is classified by primary failure cause.
- Each OK candidate is decomposed by at least profit, MDD, trade_count, daily_avg_trades, payoff_ratio, and available CSV-derived loss concentration fields.
- The plan explicitly decides one of:
  - `continue_with_repair_dryrun`
  - `stop_v2_body_branch`
  - `needs_manual_review_before_more_research`
- No DB mutation, replay, OOS, Plan D, portfolio, or promotion path is executed.

### Must Have

- Existing evidence only.
- Row-level table for all 8 candidates.
- Clear distinction between:
  - gate too strict
  - strategy structurally losing
  - sell/risk control insufficient
  - profile/runtime issue
- A next command that cannot accidentally run Plan D or full replay.

### Must NOT Have

- No DB INSERT/UPDATE/DELETE.
- No replay/OOS/Plan D.
- No new condition body generation.
- No portfolio/export/live/final promotion.
- No `git add -A`.
- Do not stage dashboard 7 files, `.gjc`, unrelated `.omo` residues, runtime DBs, or backtest CSV files.

## Verification Strategy

> ZERO HUMAN INTERVENTION - all verification is agent-executed.

- Test decision: analysis-only; no unit test changes required.
- QA policy: each task writes JSON/Markdown evidence and validates JSON parse.
- Evidence root: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/`
- Required commands:

```powershell
python - <<'PY'  # use PowerShell-compatible here-string instead of this Bash form
PY
python scripts/verify_nonrelease_sync.py
git diff --check -- docs/research/condition_research/plans/lattice_condition_generation_v2_risk_sell_repair_review_20260709.md docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708 docs/update_log/2026-07-09_lattice_v2_risk_sell_repair_review_handoff.md
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json ai_strategy_loop/state/loop_strategies.db ai_strategy_loop/state/loop_runs.db
```

Use PowerShell here-string form for Python snippets:

```powershell
@'
print("ok")
'@ | python -
```

## Execution Strategy

### Parallel Execution Waves

Wave 1: source receipt and row inventory.
Wave 2: CSV/strategy-body failure decomposition.
Wave 3: repair decision and handoff.
Wave 4: final verification and scoped commit if requested.

### Dependency Matrix

| Task | Depends On | Blocks |
|---:|---|---|
| 1 | none | 2, 3 |
| 2 | 1 | 4 |
| 3 | 1 | 4 |
| 4 | 2, 3 | 5 |
| 5 | 4 | 6 |
| 6 | 5 | final verification |

## TODOs

- [x] 1. Read-First Receipt

  **What to do**:
  - Read these files to EOF:
    - `docs/update_log/2026-07-08_lattice_v2_to_plan_d_conditional_overnight_handoff.md`
    - `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_body8_min_warm64_limited_replay_result_20260708.json`
    - `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_to_plan_d_stop_decision_20260708.json`
    - `docs/research/condition_research/generated_conditions/lattice_v2_body_static_dryrun_20260708/lattice_v2_body_static_dryrun_seeds_20260708.json`
  - Write `source_read_receipt_risk_sell_review_20260709.json` with path, read_scope, line_count, sha256, applied_sections.

  **Must NOT do**:
  - Do not mutate DB.
  - Do not run replay.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2, 3 | Blocked By: none

  **References**:
  - Result: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_body8_min_warm64_limited_replay_result_20260708.json`
  - Stop decision: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_to_plan_d_stop_decision_20260708.json`

  **Acceptance Criteria**:
  - [ ] Receipt JSON parses.
  - [ ] Receipt contains exactly the four read-first source paths.
  - [ ] All sources have `read_scope=full_document`.

  **QA Scenarios**:
  ```text
  Scenario: Happy path
    Tool: PowerShell + python
    Steps: Parse receipt and assert source_count=4.
    Expected: exit 0.
    Evidence: source_read_receipt_risk_sell_review_20260709.json

  Scenario: Missing source guard
    Tool: PowerShell + python
    Steps: Assert every listed source exists before analysis.
    Expected: exit 0; if missing, stop with blocked receipt.
    Evidence: source_read_receipt_risk_sell_review_20260709.json
  ```

  **Commit**: YES, if this page is committed | Message: `docs(research): v2 손실 원인 재검토 계획 실행 기록`

- [x] 2. Row-Level Failure Inventory

  **What to do**:
  - Parse the limited replay result.
  - Emit one row per candidate with:
    - gen_no
    - label
    - lane_origin
    - status
    - profit
    - MDD
    - trade_count
    - daily_avg_trades
    - payoff_ratio
    - csv_path
    - engine_reason
    - initial decision
  - Classify primary failure:
    - `loss_plus_mdd`
    - `mdd_only`
    - `low_daily`
    - `no_metrics`
    - `profile_mismatch_control`

  **Must NOT do**:
  - Do not change classification rules retroactively to make a survivor.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 4 | Blocked By: 1

  **References**:
  - Result rows: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_body8_min_warm64_limited_replay_result_20260708.json`

  **Acceptance Criteria**:
  - [ ] Inventory includes 8 candidates.
  - [ ] `survivor_count=0` remains unchanged.
  - [ ] No candidate is upgraded to hold/survivor.

  **QA Scenarios**:
  ```text
  Scenario: Happy path
    Tool: PowerShell + python
    Steps: Parse decomposition JSON and assert row_count=8.
    Expected: exit 0.
    Evidence: v2_risk_sell_failure_decomposition_20260709.json

  Scenario: Guard against false survivor
    Tool: PowerShell + python
    Steps: Assert all classifications are no_go/failure-analysis only.
    Expected: exit 0.
    Evidence: v2_risk_sell_failure_decomposition_20260709.json
  ```

  **Commit**: YES, if page is committed

- [x] 3. Strategy Body And Sell/Risk Clause Audit

  **What to do**:
  - Parse the original 8 seed bodies from `lattice_v2_body_static_dryrun_seeds_20260708.json`.
  - For each seed, extract sell-side and risk-relevant clauses from `sell_code` and any risk gates in `buy_code`.
  - Record whether the body contains:
    - hard stop-loss condition
    - time stop
    - take-profit condition
    - volatility/range cap
    - late-session exit rule
    - position/hold duration limiter
    - overtrading throttle
  - Compare those fields against observed MDD/profit.

  **Must NOT do**:
  - Do not generate replacement STOM syntax.
  - Do not edit `utility/ai_agent/strategy.txt` or `rules.txt`.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 4 | Blocked By: 1

  **References**:
  - Seed body source: `docs/research/condition_research/generated_conditions/lattice_v2_body_static_dryrun_20260708/lattice_v2_body_static_dryrun_seeds_20260708.json`
  - Prior handoff: `docs/update_log/2026-07-08_lattice_v2_to_plan_d_conditional_overnight_handoff.md`

  **Acceptance Criteria**:
  - [ ] All 8 seeds have a sell/risk audit row.
  - [ ] Audit flags are boolean or explicit `unknown`.
  - [ ] Any `unknown` is explained from source limitations.

  **QA Scenarios**:
  ```text
  Scenario: Happy path
    Tool: PowerShell + python
    Steps: Parse audit JSON and assert audited_seed_count=8.
    Expected: exit 0.
    Evidence: v2_risk_sell_failure_decomposition_20260709.json

  Scenario: Missing clause handling
    Tool: PowerShell + python
    Steps: Assert missing clauses are recorded as false/unknown, not omitted.
    Expected: exit 0.
    Evidence: v2_risk_sell_failure_decomposition_20260709.json
  ```

  **Commit**: YES, if page is committed

- [x] 4. CSV-Derived Loss Concentration Review

  **What to do**:
  - For OK rows with existing `csv_path`, read backtest CSVs in read-only mode.
  - Extract available columns only; do not assume schema.
  - If columns permit, compute:
    - largest losing trade
    - bottom 10 loss sum
    - loss/win count
    - average win
    - average loss
    - loss concentration ratio
    - time bucket loss concentration
    - hold-time loss concentration
  - If CSV schema lacks needed columns, record `unavailable_columns` and continue.

  **Must NOT do**:
  - Do not create, move, delete, or stage backtest CSV files.
  - Do not rerun backtest to fill missing CSVs.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 5 | Blocked By: 2, 3

  **References**:
  - CSV paths are embedded in `lattice_v2_body8_min_warm64_limited_replay_result_20260708.json`.

  **Acceptance Criteria**:
  - [ ] CSV review covers all available OK-row CSVs.
  - [ ] Missing/error row is explicitly marked no metrics.
  - [ ] The analysis states whether losses are broad-based or concentrated.

  **QA Scenarios**:
  ```text
  Scenario: Happy path
    Tool: PowerShell + python
    Steps: Read each available csv_path and record schema plus row count.
    Expected: exit 0.
    Evidence: v2_risk_sell_failure_decomposition_20260709.json

  Scenario: Missing CSV
    Tool: PowerShell + python
    Steps: If a csv_path is absent, record missing_csv and continue.
    Expected: no crash; missing file does not trigger rerun.
    Evidence: v2_risk_sell_failure_decomposition_20260709.json
  ```

  **Commit**: YES, if page is committed

- [x] 5. Repair Feasibility Decision

  **What to do**:
  - Decide one of:
    - `continue_with_repair_dryrun`
    - `stop_v2_body_branch`
    - `needs_manual_review_before_more_research`
  - Use this decision table:

| Evidence | Decision |
|---|---|
| Losses are concentrated and sell/risk clauses are weak/missing | `continue_with_repair_dryrun` |
| Losses are broad-based across entries despite risk clauses | `stop_v2_body_branch` |
| CSV schema prevents determining loss concentration | `needs_manual_review_before_more_research` |
| Any result suggests engine/profile mismatch | `needs_manual_review_before_more_research` |

  **Must NOT do**:
  - Do not decide to run OOS or Plan D directly.
  - Do not allow full 288 replay as next step.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: 6 | Blocked By: 4

  **References**:
  - Stop decision: `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/lattice_v2_to_plan_d_stop_decision_20260708.json`

  **Acceptance Criteria**:
  - [ ] Decision JSON exists.
  - [ ] Decision is one of the three allowed values.
  - [ ] Decision rationale cites concrete row/csv/strategy-body evidence.

  **QA Scenarios**:
  ```text
  Scenario: Happy path
    Tool: PowerShell + python
    Steps: Parse decision JSON and assert decision enum is valid.
    Expected: exit 0.
    Evidence: v2_risk_sell_repair_decision_20260709.json

  Scenario: Unsafe next step guard
    Tool: rg
    Steps: Search decision/handoff for forbidden next commands: Plan D, OOS, full min 288, full tick 288.
    Expected: no next command contains forbidden execution.
    Evidence: final verification receipt
  ```

  **Commit**: YES, if page is committed

- [x] 6. Handoff And Next Command

  **What to do**:
  - Write `docs/update_log/2026-07-09_lattice_v2_risk_sell_repair_review_handoff.md`.
  - Include:
    - overall page status
    - row-level findings table
    - sell/risk audit summary
    - CSV loss concentration summary
    - repair decision
    - next command
  - If decision is `continue_with_repair_dryrun`, next command must be dry-run only:

```text
$ulw-loop docs/research/condition_research/plans/lattice_condition_generation_v2_risk_sell_repair_dryrun_20260709.md
```

  - If decision is `stop_v2_body_branch`, next command should be a closeout/report command, not generation.

  **Must NOT do**:
  - Do not write a next command that performs DB apply, replay, OOS, or Plan D in the same page.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: final verification | Blocked By: 5

  **References**:
  - This plan file.
  - All deliverables from tasks 1~5.

  **Acceptance Criteria**:
  - [ ] Handoff exists.
  - [ ] Handoff includes a table with all 8 candidates.
  - [ ] Handoff includes a next command matching the decision.

  **QA Scenarios**:
  ```text
  Scenario: Happy path
    Tool: rg
    Steps: Confirm handoff contains "repair decision", "next command", and all 8 body labels.
    Expected: exit 0.
    Evidence: docs/update_log/2026-07-09_lattice_v2_risk_sell_repair_review_handoff.md

  Scenario: Forbidden next command
    Tool: rg
    Steps: Confirm next command does not include OOS/Plan D/full 288.
    Expected: exit 0.
    Evidence: final verification receipt
  ```

  **Commit**: YES, if page is committed

## Final Verification Wave

- [x] F1. Plan Compliance Audit
  - Confirm no DB INSERT/UPDATE/DELETE was run.
  - Confirm no replay/OOS/Plan D was run.
  - Confirm all deliverables exist.

- [x] F2. Evidence Parse
  - Parse all new JSON and JSONL files.
  - Confirm 8 candidate rows are preserved.

- [x] F3. Nonrelease Guard
  - Run `python scripts/verify_nonrelease_sync.py`.

- [x] F4. Scoped Diff Check
  - Run scoped `git diff --check`.
  - Run protected-path `git status --short`.

## Commit Strategy

If the user asks to commit this page, stage explicitly:

```powershell
git add docs/research/condition_research/plans/lattice_condition_generation_v2_risk_sell_repair_review_20260709.md
git add docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_failure_decomposition_20260709.json
git add docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_failure_decomposition_20260709.md
git add docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_repair_decision_20260709.json
git add docs/update_log/2026-07-09_lattice_v2_risk_sell_repair_review_handoff.md
```

Do not stage runtime DBs, backtest CSVs, dashboard files, `.gjc`, or unrelated `.omo` files.

Commit message:

```text
docs(research): v2 손실 원인 재검토 계획 수립
```

## Success Criteria

This review page is successful if it prevents blind continuation and produces one evidence-backed decision:

| Decision | Meaning |
|---|---|
| `continue_with_repair_dryrun` | Repair is plausible, but only static/dry-run next. |
| `stop_v2_body_branch` | v2 body branch should stop; no more candidate generation from this structure. |
| `needs_manual_review_before_more_research` | Evidence is insufficient or contradictory; do not automate more research. |
