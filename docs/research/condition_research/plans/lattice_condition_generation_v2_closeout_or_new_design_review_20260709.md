# Lattice Condition Generation V2 Closeout Or New Design Review Plan

## TL;DR

| Item | Decision |
|---|---|
| Plan type | Review-only execution plan |
| Primary goal | Decide whether to close the failed lattice v2 body branch or write a new condition-generation design brief |
| Current default posture | Do not continue v2 body replay/OOS/Plan D unless the review finds a concrete evidence contradiction |
| Required correction | Recompute sell/risk clause extraction because the prior threshold table likely captured time-stop values as stop/take-profit values |
| Forbidden during this plan | DB write, official replay, OOS, portfolio, Plan D/P7, export/live/final promotion |
| Expected time | 1.0-2.5 hours |
| Main output | Closeout-or-new-design decision, corrected risk/sell audit, final handoff, next command |

## Why This Plan Exists

The v2 body branch has already produced official min full-period warm64 limited replay evidence for 8 body candidates. The replay result did not produce a survivor or hold candidate:

| Metric | Value |
|---|---:|
| Replay rows | 8 |
| OK rows | 7 |
| Error/no-metrics rows | 1 |
| Survivor | 0 |
| Hold | 0 |
| no_go | 8 |
| Broad-based loss rows among parsed CSVs | 7 / 7 |
| Primary failures | loss_plus_mdd 7, no_metrics 1 |

However, the prior risk/sell review artifact contains a likely extraction bug in the sell/risk clause table. The high-level replay result is still usable because it comes from replay metrics and parsed CSVs, but the clause-level diagnosis must be recomputed before using it to justify either a closeout or a new design direction.

This plan therefore separates three questions:

| Question | Purpose |
|---|---|
| Was the v2 replay result valid? | Confirm the branch really failed under official full-period warm64 min replay |
| Was the sell/risk diagnosis accurate? | Correct the threshold extraction bug before making design claims |
| Should work stop or move to a new design? | Prevent endless Plan D/repair cycling without evidence |

## Read-First Source Package

Read each file fully to EOF before producing outputs. Record line count, sha256, and applied sections in the source receipt.

| Priority | Path | Why it is required |
|---:|---|---|
| 1 | `docs/update_log/2026-07-09_lattice_v2_risk_sell_repair_review_handoff.md` | Latest handoff and current stop recommendation |
| 2 | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_failure_decomposition_20260709.json` | Machine-readable row and failure decomposition |
| 3 | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_failure_decomposition_20260709.md` | Human-readable report containing the suspected threshold extraction bug |
| 4 | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_repair_decision_20260709.json` | Current stop-v2-body-branch decision |
| 5 | `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md` | Whole-study result context: Plan A/B/C/D, 576 lattice, repair composite, Plan D |
| 6 | `docs/update_log/2026-07-08_lattice_condition_generation_v2_redesign_plan_handoff.md` | Why v2 redesign was opened |
| 7 | `docs/update_log/2026-07-08_lattice_condition_generation_v2_candidate_dryrun_handoff.md` | v2 metadata candidate dry-run context |
| 8 | `docs/update_log/2026-07-08_lattice_condition_generation_v2_body_static_dryrun_handoff.md` | v2 body static dry-run context |
| 9 | `docs/research/condition_research/generated_conditions/lattice_v2_body_static_dryrun_20260708/lattice_v2_body_static_dryrun_seeds_20260708.json` | Body candidate definitions, if available |
| 10 | `utility/ai_agent/strategy.txt` and `utility/ai_agent/rules.txt` | Only for interpreting STOM syntax; do not generate new bodies in this plan |

## Scope

| In Scope | Out Of Scope |
|---|---|
| Source receipt and evidence inventory | New condition generation |
| Corrected sell/risk clause extraction audit | DB INSERT apply |
| Validation that replay/result files match the handoff | Official replay |
| Closeout vs new-design decision matrix | OOS or portfolio |
| Final closeout report or design-review recommendation | Plan D/P7 execution |
| Handoff and next command | Export/live/final promotion |

## Decision Gates

The executor must produce exactly one final decision.

| Decision | Required evidence |
|---|---|
| `archive_v2_branch_and_stop` | Replay evidence remains valid, 0 survivor/hold, broad-based losses are confirmed, corrected sell/risk audit does not reveal a profile or parser contradiction |
| `new_design_spec_only` | Replay failure is valid, but corrected audit identifies a specific design-level flaw that justifies writing a new design brief; no seed generation or DB apply is allowed |
| `manual_review_needed` | Corrected audit contradicts prior evidence, source files are missing, replay row counts disagree, or the result depends on an unresolved parsing/profile issue |

Do not choose `continue_v2_body_branch`. The current branch has already failed the bounded evidence threshold unless the review finds a concrete contradiction.

## Task Breakdown

### T0. Preflight And Source Receipt

| Step | Action | Output |
|---:|---|---|
| T0.1 | Check git status with explicit paths only | Status snapshot |
| T0.2 | Read all read-first files to EOF | `source_read_receipt_closeout_or_new_design_20260709.json` |
| T0.3 | Verify replay/result/handoff files exist and parse | Preflight receipt |

Acceptance:

| Check | Required result |
|---|---|
| Source files readable | pass |
| JSON artifacts parse | pass |
| No DB write attempted | pass |

### T1. Correct Sell/Risk Extraction Audit

Recompute sell/risk clause extraction from the source seed/body files, not from the prior Markdown table.

| Problem To Guard Against | Required Correction |
|---|---|
| Stop loss values displayed as `90.0`, `120.0`, etc. | Extract stop loss/take profit from the exact STOM sell clauses, not from the last number in a segment |
| Time-stop or late-exit values captured as risk thresholds | Keep time cutoffs separate from stop/take-profit thresholds |
| Clause presence interpreted as effectiveness | Compare clause presence with replay metrics and CSV-level losses |

Outputs:

| Path | Purpose |
|---|---|
| `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_corrected_sell_risk_clause_audit_20260709.json` | Corrected machine-readable clause audit |
| `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_corrected_sell_risk_clause_audit_20260709.md` | Corrected human-readable clause audit |

Acceptance:

| Check | Required result |
|---|---|
| Threshold extraction explicitly separates stop/take-profit/time-stop/late-exit | pass |
| Prior flawed table is marked as superseded | pass |
| No replay/OOS required | pass |

### T2. Replay Evidence Integrity Check

Validate that the branch-level conclusion does not rely on the flawed threshold table.

| Evidence | Required Check |
|---|---|
| 8-row replay result | Row count and candidate IDs match |
| 7 OK rows | Metrics exist and parse |
| 1 error row | Classified as no_metrics, not hidden survivor |
| 7 broad-based loss rows | CSV-derived loss conclusion reproducible |
| 0 survivor/hold | Classification matches the documented gate rules |

Output:

| Path | Purpose |
|---|---|
| `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_replay_evidence_integrity_check_20260709.json` | Evidence integrity receipt |

### T3. Whole-Research Context Matrix

Build a concise table that places this v2 branch inside the full research history.

| Research Page | Result To Capture |
|---|---|
| Plan A provider stabilization | Completed; infrastructure improvement, not a strategy survivor |
| Plan C CSS_V7 validation | Completed; DB-listed candidate validation context |
| Plan B tick 288 official warm64 | 0 gate_passed, no survivor |
| Plan B min 288 official warm64 | 0 gate_passed, no survivor |
| P6 576 integrated decision | 576 no_go |
| Repair composite | Produced OOS-style survivors, but not promotion proof |
| Plan D rank01/rank02/rank03 | Seed research produced bounded signals, not portfolio/export readiness |
| v2 body branch | 8 limited replay candidates, 0 survivor/hold |

Output:

| Path | Purpose |
|---|---|
| `docs/update_log/2026-07-09_lattice_v2_closeout_context_matrix.md` | Human-readable context table |

### T4. Closeout Or New-Design Decision

Apply the decision gates and write one decision JSON.

| Candidate Decision | When To Choose |
|---|---|
| `archive_v2_branch_and_stop` | The v2 body branch failure is confirmed and there is no actionable contradiction |
| `new_design_spec_only` | There is a concrete design lesson, but not enough evidence to generate/apply new seeds |
| `manual_review_needed` | Evidence is inconsistent or cannot be verified |

Output:

| Path | Purpose |
|---|---|
| `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_closeout_or_new_design_decision_20260709.json` | Final decision receipt |

### T5. Final Report

Write one report. The report must not open a new experiment by itself.

| If Decision | Required Report Content |
|---|---|
| `archive_v2_branch_and_stop` | Why v2 should stop, what evidence remains reusable, what should not be repeated |
| `new_design_spec_only` | New-design requirements, prohibited shortcuts, and what evidence would be required before generation |
| `manual_review_needed` | Exact blockers and what manual inspection is required |

Output:

| Path | Purpose |
|---|---|
| `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md` | Final review report |

### T6. Handoff And Next Command

Write a handoff that gives the next safe command.

| Final Decision | Next Command Shape |
|---|---|
| `archive_v2_branch_and_stop` | No automatic research command; recommend PR/commit/review or user decision |
| `new_design_spec_only` | `$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_YYYYMMDD.md` |
| `manual_review_needed` | `$start-work ...` for manual evidence reconciliation only |

Output:

| Path | Purpose |
|---|---|
| `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_handoff.md` | Handoff and next command |

## Verification

Run only non-mutating checks.

| Check | Command |
|---|---|
| JSON parse and decision assertions | `python - <<'PY' ... PY` or equivalent local script |
| Nonrelease sync | `python scripts/verify_nonrelease_sync.py` |
| Whitespace | `git diff --check -- <explicit changed files>` |
| Protected paths clean | `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json` |

## Commit Guidance

Commit only if the executor's scope explicitly includes committing. If committing:

| Rule | Requirement |
|---|---|
| Staging | Explicit file paths only |
| Forbidden | `git add -A` |
| Message | Korean title and Korean markdown body |
| Do not stage | dashboard 7 files, `.gjc`, unrelated `.omo` leftovers, protected runtime paths |

## Stop Conditions

Stop and write `manual_review_needed` if any of these occur:

| Stop Condition | Reason |
|---|---|
| Corrected sell/risk audit cannot be computed | Clause-level conclusion would be unreliable |
| Replay rows do not match 8 candidates | Branch result integrity uncertain |
| Result JSON/CSV evidence contradicts handoff | Manual reconciliation required |
| Any command would require DB UPDATE/DELETE | Violates research-lane append-only contract |

## Expected Result

The expected result is not another replay. The expected result is one of:

| Outcome | Meaning |
|---|---|
| Archive v2 | Current v2 branch is closed; future work must start from a new design brief |
| New design spec only | A design document is created, but no generation/replay is run |
| Manual review needed | Evidence has a concrete inconsistency that must be resolved before more research |
