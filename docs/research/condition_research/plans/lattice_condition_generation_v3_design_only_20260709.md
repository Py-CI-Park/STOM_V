# Lattice Condition Generation V3 Design Only Plan

## TL;DR
> **Summary**: Close the failed lattice v2 body branch and write a v3 condition-generation design specification before any new seed generation or replay. The executor must produce design documents, gates, and a bounded next command only.
> **Deliverables**:
> - v3 source read receipt
> - v2/v1 failure lesson matrix
> - v3 design specification
> - v3 evaluation protocol and gate table
> - v3 dry-run-only next command
> - handoff and ledger records
> **Effort**: Short, 1.5-3.0 hours
> **Parallel**: NO, evidence and design decisions are sequential
> **Critical Path**: T0 source receipt -> T1 failure matrix -> T2 v3 design principles -> T3 protocol/gates -> T4 final design/handoff

## Context

### Original Request

The requested command is:

```text
$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md
```

This is a planning command. It must not generate new strategy bodies, register DB rows, run replay, run OOS, execute Plan D, create a portfolio, or touch export/live/final promotion paths.

### Current Research State

| Page | Status | Result |
|---|---|---|
| Plan A provider stabilization | completed | Runtime/provider stability improved; not a strategy survivor result |
| Plan C CSS_V7 validation | completed | DB-listed candidate validation path established |
| Plan B tick 288 official warm64 | completed | 288/288 rows, 0 gate pass, no survivor |
| Plan B min 288 official warm64 | completed | 288/288 coverage, 0 gate pass, no survivor |
| P6 integrated 576 decision | completed | 576 no_go, 0 go, 0 hold |
| Repair composite | completed | Produced bounded OOS-style survivors; not promotion proof |
| Plan D rank01/rank02/rank03 | completed/paused | Produced seed evidence; not portfolio/export proof |
| Lattice v2 body branch | closed | 8 limited replay rows, 0 survivor, 0 hold, 8 no_go |

### Latest Closeout Decision

| Item | Value |
|---|---|
| Decision | `archive_v2_branch_and_stop` |
| Reason | 7 OK v2 body rows all had negative profit and MDD above cap; 1 row had no metrics |
| Corrected audit | Prior sell/risk threshold table was superseded; old `90/120` values were hold-time thresholds |
| Impact of corrected audit | no_go result unchanged |
| Plan D input | blocked, because v2 has no survivor or hold |

### Metis Review

No subagent was spawned because the active multi-agent tool policy says not to spawn subagents unless the user explicitly asks for delegation. Local gap review found these risks and the plan addresses them:

| Gap/Risk | Plan Response |
|---|---|
| Treating v2 failure as a gate-threshold problem | T1 requires separating gate strictness from actual profit/MDD failure |
| Mutating failed v2 bodies into v3 without design | T2 requires a design specification before generation |
| Running DB/replay/OOS too early | T3/T4 define dry-run-only next command and hard stop rules |
| Forgetting tick/min lane differences | T1/T2 require lane-specific design choices |
| Overfitting Plan D survivor seeds | T2/T3 require fully blind or walk-forward boundary before any future OOS claim |

## Work Objectives

### Core Objective

Produce a v3 design-only package that decides what a future condition-generation architecture must look like, based on the accumulated lattice/v2/Plan D evidence.

### Deliverables

| Deliverable | Path |
|---|---|
| Source read receipt | `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/source_read_receipt_v3_design_20260709.json` |
| Failure lesson matrix | `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_failure_lesson_matrix_20260709.md` |
| V3 design specification | `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_design_spec_20260709.md` |
| V3 evaluation protocol | `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_evaluation_protocol_20260709.md` |
| Next dry-run command | `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_next_command_20260709.md` |
| Handoff | `docs/update_log/2026-07-09_lattice_v3_design_only_handoff.md` |

### Definition Of Done

| Condition | Verification |
|---|---|
| All read-first files are read to EOF | source receipt has `read_scope=full_document`, line count, sha256 |
| v2 branch remains closed | decision text repeats `archive_v2_branch_and_stop`; no v2 continuation command |
| v3 design is written | design spec exists and includes objectives, allowed inputs, forbidden approaches, gates |
| next command is bounded | next command allows dry-run/spec/static only, not DB/replay/OOS |
| no research execution happened | verification confirms no DB write, no replay, no OOS, no Plan D, no portfolio |

### Must Have

- Preserve research-lane-only posture.
- Preserve INSERT-only rule for any future DB step, although this plan must not perform DB insert.
- Separate min-primary design from tick-diagnostic use.
- Treat repair composite/Plan D survivors as seed evidence, not promotion proof.
- Require fully blind or walk-forward split before any future OOS-style claim is upgraded.
- Record gates that prevent endless Plan D loops.

### Must NOT Have

- No candidate body generation.
- No new STOM strategy syntax generation.
- No DB INSERT apply.
- No DB UPDATE/DELETE.
- No official replay or backtest.
- No OOS.
- No Plan D/P7 execution.
- No portfolio.
- No export/live/final promotion.
- No `git add -A`.
- No staging of dashboard 7 files, `.gjc`, unrelated `.omo` leftovers, or protected runtime paths.

## Read-First Source Package

Read each file fully to EOF before writing design outputs.

| Priority | Path | Use |
|---:|---|---|
| 1 | `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md` | v2 closeout rationale |
| 2 | `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_handoff.md` | current handoff and safe next options |
| 3 | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_closeout_or_new_design_decision_20260709.json` | machine-readable v2 decision |
| 4 | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_corrected_sell_risk_clause_audit_20260709.md` | corrected sell/risk lesson |
| 5 | `docs/update_log/2026-07-09_lattice_v2_closeout_context_matrix.md` | full page context |
| 6 | `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md` | full research analysis and old 576 summary |
| 7 | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_export_summary_20260705.json` | tick 288 evidence |
| 8 | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_export_summary_20260705.json` | min 288 evidence |
| 9 | `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_go_no_go_hold_20260705.json` | 576 go/hold/no_go evidence |
| 10 | `utility/ai_agent/strategy.txt` and `utility/ai_agent/rules.txt` | future STOM syntax constraints; read only, do not generate |

## Verification Strategy

> ZERO HUMAN INTERVENTION - all verification is agent-executed.

- Test decision: no unit tests required because this is documentation/design-only work.
- QA policy: each task writes machine-readable or human-readable evidence and runs parse/consistency checks.
- Evidence path: `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/`.

## Execution Strategy

### Parallel Execution Waves

No parallel execution. The work is a sequential design review:

| Wave | Tasks |
|---|---|
| Wave 1 | T0 source receipt |
| Wave 2 | T1 failure lesson matrix |
| Wave 3 | T2 v3 design specification |
| Wave 4 | T3 evaluation protocol and next command |
| Wave 5 | T4 handoff and verification |

### Dependency Matrix

| Task | Depends On | Blocks |
|---|---|---|
| T0 | none | T1, T2, T3, T4 |
| T1 | T0 | T2, T3 |
| T2 | T1 | T3 |
| T3 | T2 | T4 |
| T4 | T0-T3 | Final Verification |

## TODOs

- [ ] T0. Source Receipt And Scope Lock

  **What to do**:
  - Read every read-first file to EOF.
  - Record line count, sha256, read scope, applied sections.
  - Snapshot the current dirty worktree with explicit paths only.
  - Create the output directory `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/`.
  - Record that this is design-only and no DB/replay/OOS/Plan D work is allowed.

  **Must NOT do**:
  - Do not run backtests.
  - Do not generate strategy bodies.
  - Do not edit DB files.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: T1, T2, T3, T4 | Blocked By: none

  **References**:
  - `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md` - v2 stop rationale.
  - `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_handoff.md` - next-safe-options boundary.
  - `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_closeout_or_new_design_decision_20260709.json` - machine-readable decision.

  **Acceptance Criteria**:
  - [ ] `source_read_receipt_v3_design_20260709.json` exists.
  - [ ] Every source has `read_scope=full_document`, `line_count`, `sha256`.
  - [ ] Receipt includes `scope=design_only_no_generation_no_db_no_replay_no_oos_no_plan_d`.

  **QA Scenarios**:
  ```text
  Scenario: Source package complete
    Tool: powershell + python
    Steps: parse the receipt JSON and assert all required source paths exist, have line_count > 0, and have sha256 length 64
    Expected: all assertions pass
    Evidence: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/source_read_receipt_v3_design_20260709.json

  Scenario: Missing source guard
    Tool: python
    Steps: compare receipt paths against the required source list
    Expected: missing list is empty
    Evidence: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/source_receipt_validation_20260709.json
  ```

  **Commit**: NO | Message: none | Files: documentation/evidence only

- [ ] T1. Failure Lesson Matrix

  **What to do**:
  - Consolidate lessons from tick 288, min 288, P6 576, repair composite, Plan D seed research, and v2 body closeout.
  - Explicitly separate these failure classes:
    - engine/profile/process issue
    - gate-threshold issue
    - strategy structure issue
    - sell/risk reporting issue
    - overfitting or non-blind validation issue
  - Record why v2 failure is not solved by relaxing gates.
  - Record what remains useful from failed pages.

  **Must NOT do**:
  - Do not reinterpret no_go rows as survivors.
  - Do not promote repair composite or Plan D seed evidence to live/export readiness.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: T2, T3 | Blocked By: T0

  **References**:
  - `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md` - full research summary.
  - `docs/update_log/2026-07-09_lattice_v2_closeout_context_matrix.md` - current page matrix.
  - `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_corrected_sell_risk_clause_audit_20260709.md` - corrected sell/risk lesson.

  **Acceptance Criteria**:
  - [ ] `lattice_v3_failure_lesson_matrix_20260709.md` exists.
  - [ ] Matrix includes tick 288, min 288, 576 P6, repair composite, Plan D, v2 body.
  - [ ] Matrix states `gate_relaxation_is_not_sufficient`.
  - [ ] Matrix states `v2_sell_risk_table_superseded_but_decision_unchanged`.

  **QA Scenarios**:
  ```text
  Scenario: Matrix covers all prior pages
    Tool: python
    Steps: assert required page labels are present in the matrix markdown
    Expected: all required labels present
    Evidence: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/failure_lesson_matrix_validation_20260709.json

  Scenario: Gate-relaxation misconception blocked
    Tool: python
    Steps: assert matrix contains explicit text saying gate relaxation is not sufficient
    Expected: assertion passes
    Evidence: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/failure_lesson_matrix_validation_20260709.json
  ```

  **Commit**: NO | Message: none | Files: documentation/evidence only

- [ ] T2. V3 Design Specification

  **What to do**:
  - Write the design spec for a future v3 condition-generation architecture.
  - The design must choose these defaults:
    - min lane is primary for future candidate evaluation.
    - tick lane is diagnostic/stress-only unless explicitly reopened.
    - candidate generation must start from design requirements, not mutation of failed v2 bodies.
    - repair composite and Plan D seeds may inform feature families, but are not promotion proof.
    - buy edge quality must be tested separately from sell/risk clauses.
    - future candidates must include negative controls and holdout controls.
    - future OOS requires preregistration and a blind or walk-forward boundary.
  - Define what a v3 candidate class is allowed to use:
    - coverage composite
    - risk-balanced composite
    - seed-informed but not seed-copied families
    - anti-overtrade throttle
    - explicit MDD defense
    - explicit daily trade sufficiency target
  - Define what v3 must reject:
    - full-period replay result treated as blind OOS
    - unlimited Plan D loops
    - candidate families copied directly from failed v2 bodies
    - tick-first large lattice recreation

  **Must NOT do**:
  - Do not write actual STOM buy/sell condition bodies.
  - Do not create candidate JSON seed files.
  - Do not register anything in DB.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: T3 | Blocked By: T1

  **References**:
  - `utility/ai_agent/strategy.txt` - future syntax context only.
  - `utility/ai_agent/rules.txt` - future syntax/rule context only.
  - `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md` - v2 failure boundary.

  **Acceptance Criteria**:
  - [ ] `lattice_v3_design_spec_20260709.md` exists.
  - [ ] Spec includes sections: objectives, inputs, excluded inputs, candidate classes, risk design, lane design, validation boundaries.
  - [ ] Spec explicitly says no body generation in this page.
  - [ ] Spec includes a go/no-go table for future body generation.

  **QA Scenarios**:
  ```text
  Scenario: Design spec complete
    Tool: python
    Steps: assert required section headings exist in the spec markdown
    Expected: all headings present
    Evidence: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/v3_design_spec_validation_20260709.json

  Scenario: No accidental generation scope
    Tool: python
    Steps: assert the spec does not include generated buy_code/sell_code JSON arrays or DB apply instructions
    Expected: forbidden patterns absent
    Evidence: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/v3_design_spec_validation_20260709.json
  ```

  **Commit**: NO | Message: none | Files: documentation/evidence only

- [ ] T3. Evaluation Protocol And Gate Design

  **What to do**:
  - Write the protocol that future v3 work must follow before any replay or OOS opens.
  - Define phases:
    1. design spec approval
    2. metadata dry-run
    3. body static dry-run
    4. DB registration dry-run
    5. INSERT-only apply only after explicit scope
    6. limited min replay only after preregistered quota
    7. OOS-style robustness only after survivor exists
    8. Plan D intake only after OOS survivor exists
  - Define future gates:
    - syntax/static gate
    - duplicate lineage gate
    - sell/risk separation gate
    - MDD-first rejection gate
    - daily trade sufficiency gate
    - overfit-risk gate
    - blind boundary gate
  - Write the next command as dry-run-only. It must not include DB apply or replay.

  **Must NOT do**:
  - Do not open candidate generation in this task.
  - Do not write a command that executes DB apply, replay, OOS, Plan D, or portfolio.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: T4 | Blocked By: T2

  **References**:
  - `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_handoff.md` - safe next command shape.
  - `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_closeout_or_new_design_decision_20260709.json` - forbidden next actions.

  **Acceptance Criteria**:
  - [ ] `lattice_v3_evaluation_protocol_20260709.md` exists.
  - [ ] Protocol includes all eight phases listed above.
  - [ ] Protocol includes a stop condition before DB apply.
  - [ ] `lattice_v3_next_command_20260709.md` exists and recommends `$ulw-plan` or `$start-work` for dry-run/spec only, not apply/replay.

  **QA Scenarios**:
  ```text
  Scenario: Protocol gates are present
    Tool: python
    Steps: assert all named gates exist in the protocol markdown
    Expected: all named gates present
    Evidence: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/v3_protocol_validation_20260709.json

  Scenario: Next command is non-mutating
    Tool: python
    Steps: assert next-command markdown does not contain DB apply, replay, OOS, Plan D execution, or portfolio execution wording
    Expected: forbidden execution words are absent or explicitly marked forbidden
    Evidence: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/v3_protocol_validation_20260709.json
  ```

  **Commit**: NO | Message: none | Files: documentation/evidence only

- [ ] T4. Handoff, Boulder/Ledger, And Final Verification

  **What to do**:
  - Write `docs/update_log/2026-07-09_lattice_v3_design_only_handoff.md`.
  - Include:
    - why v3 exists
    - why v2 is closed
    - what the next safe command is
    - what is still forbidden
    - what evidence must exist before future generation/replay opens
  - Update `.omo/boulder.json` and `.omo/start-work/ledger.jsonl` only for this design-only execution record if using `$start-work`.
  - Run final verification.

  **Must NOT do**:
  - Do not stage or commit unless the user explicitly asks.
  - Do not touch dashboard frontend files, `.gjc`, unrelated `.omo` leftovers, or protected runtime paths.

  **Parallelization**: Can Parallel: NO | Wave 5 | Blocks: Final Verification | Blocked By: T0-T3

  **References**:
  - `AGENTS.md` project rules - explicit staging, Korean commit messages if commit is requested.
  - `.omo/start-work/ledger.jsonl` - append-only timing/evidence ledger if executing with start-work.

  **Acceptance Criteria**:
  - [ ] Handoff exists.
  - [ ] Handoff gives only bounded dry-run/spec next command.
  - [ ] Final verification JSON exists.
  - [ ] Protected path status is clean.

  **QA Scenarios**:
  ```text
  Scenario: Handoff is safe
    Tool: python
    Steps: assert handoff mentions no DB/replay/OOS/Plan D in the current completed work and gives bounded next command only
    Expected: assertion passes
    Evidence: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/v3_final_verification_20260709.json

  Scenario: Protected paths clean
    Tool: powershell
    Steps: run `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`
    Expected: no output
    Evidence: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/v3_final_verification_20260709.json
  ```

  **Commit**: NO | Message: none | Files: documentation/evidence only

## Final Verification Wave

- [ ] F1. Plan Compliance Audit

  Confirm all deliverables exist, all scope boundaries are preserved, and no execution-only work happened.

- [ ] F2. JSON And Markdown Verification

  Parse all JSON receipts and run a simple markdown section-presence check for all required reports.

- [ ] F3. Nonrelease And Protected Path Check

  Run:

  ```powershell
  python scripts/verify_nonrelease_sync.py
  git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
  ```

- [ ] F4. Diff Hygiene Check

  Run `git diff --check -- <explicit changed files>` for the v3 design outputs and `.omo` ledger files touched by the execution.

## Commit Strategy

Do not commit during this plan unless the user explicitly asks. If committing later:

| Rule | Requirement |
|---|---|
| Staging | Explicit file paths only |
| Forbidden | `git add -A` |
| Message | Korean title and Korean markdown body |
| Exclude | dashboard 7 files, `.gjc`, unrelated `.omo` leftovers, protected runtime paths |

## Success Criteria

| Criterion | Required State |
|---|---|
| v3 design-only work is startable | `$start-work docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` can execute without ambiguity |
| v2 remains closed | no command continues v2 body branch |
| future generation is gated | next command is dry-run/spec only |
| no unsafe execution | no DB/replay/OOS/Plan D/portfolio/export work in this page |
| evidence is durable | source receipt, design spec, protocol, next command, handoff are written |

## Recommended Next Command After This Plan

```text
$start-work docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md
```

This next command should produce design documents only. It must not generate strategy bodies, register DB rows, or run backtests.
