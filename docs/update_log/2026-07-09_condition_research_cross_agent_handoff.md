# 2026-07-09 Condition Research Cross-Agent Handoff

## 0. Purpose

This document is the first-read handoff for Codex, Claude, GJC, or any other AI code agent resuming the condition-research workflow in `C:/System_Trading/STOM/STOM_V.wt-dev`.

| Item | Value |
|---|---|
| Primary purpose | Restore context without reading the whole conversation |
| Current branch | `loop/process-research-pipeline` |
| HEAD before this handoff commit | `9b20cfdf docs(research): 래티스 v2 조건부 Plan D 중단 기록` |
| Current research state | Lattice v2 body branch closed; v3 design-only plan prepared |
| Immediate safe next command | `$start-work docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` |
| Do not do next | Do not run DB apply, replay, OOS, Plan D, portfolio, export/live/final promotion |

## 1. Agent Start Order

Any next agent should follow this order exactly.

| Order | Action | Required File/Command | Expected Understanding |
|---:|---|---|---|
| 1 | Read this handoff first | `docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md` | Current state, stop rules, next command |
| 2 | Read v2 closeout report | `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md` | Why v2 body branch is closed |
| 3 | Read v2 closeout handoff | `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_handoff.md` | Safe next options and forbidden actions |
| 4 | Read machine decision | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_closeout_or_new_design_decision_20260709.json` | Decision is `archive_v2_branch_and_stop` |
| 5 | Read corrected sell/risk audit | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_corrected_sell_risk_clause_audit_20260709.md` | Previous risk table bug was corrected, but v2 still failed |
| 6 | Read v3 plan | `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` | Next work is design-only, not replay |
| 7 | Check dirty worktree | `git status --short` | Many unrelated dashboard/.gjc/.omo leftovers exist; stage explicitly |
| 8 | Execute only if instructed | `$start-work docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` | Create v3 design docs only |

## 2. Executive State

| Question | Answer |
|---|---|
| Are we still searching v2 body survivors? | No |
| Is Plan D currently open? | No |
| Did v2 fail because a report table had a bug? | No. The table bug was corrected, but replay metrics still failed |
| Did v2 fail because gates were too strict only? | No. Profit was negative and MDD was far above cap |
| Is the next step another backtest? | No |
| Is the next step candidate generation? | No |
| Is the next step v3 design planning/execution? | Yes, design-only |
| Can a future agent run DB INSERT apply? | Not from current scope. Only after a future explicit plan and user scope |
| Can a future agent run OOS/portfolio/export? | No |

## 3. Latest Work Completed In This Session

| Work | Plan/Command | Output | Result |
|---|---|---|---|
| V2 risk/sell repair review plan | `$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v2_risk_sell_repair_review_20260709.md` | Plan file created | Prepared analysis-only review |
| V2 risk/sell repair review execution | `$start-work ...v2_risk_sell_repair_review_20260709.md` style execution | `v2_risk_sell_failure_decomposition_20260709.*`, decision JSON, handoff | Initial decision: stop v2 body branch |
| V2 closeout/new-design plan | `$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v2_closeout_or_new_design_review_20260709.md` | Plan file created | Prepared final closeout review |
| V2 closeout/new-design execution | `$start-work docs/research/condition_research/plans/lattice_condition_generation_v2_closeout_or_new_design_review_20260709.md` | corrected audit, integrity check, context matrix, final report, handoff | Final decision: `archive_v2_branch_and_stop` |
| V3 design-only plan | `$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` | 467-line plan file | Next executable page is design-only |
| Cross-agent handoff | This document | `2026-07-09_condition_research_cross_agent_handoff.md` | Allows Codex/Claude/GJC to resume safely |

## 4. Current Research Progress

| Page/Phase | Status | Progress | Key Result | Next Action |
|---|---|---:|---|---|
| Plan A provider stabilization | Completed except A3 approval hold | 90% | Provider/failover and upper entrypoints stabilized; A3 promotion-review remains approval-blocked | Do not touch A3 unless explicitly approved |
| Plan C CSS_V7 validation | Completed | 100% | Static/pair/DB mirror/validation path established | No immediate action |
| Plan B official lattice tick 288 | Completed | 100% | 288/288 official warm64 tick rows, 0 gate pass | Use only as failure baseline |
| Plan B official lattice min 288 | Completed | 100% | 288/288 min coverage, 0 gate pass | Use only as failure baseline |
| P6 576 go/hold/no_go | Completed | 100% | 576 no_go, 0 go, 0 hold | Do not reopen old lattice |
| Repair composite | Completed | 100% | Produced bounded positive signals and selected OOS-style survivors | Use as design lesson, not promotion proof |
| Plan D rank01/rank02/rank03 | Bounded research completed/paused | 100% for bounded scope | Produced seed evidence, including rank03 R2-05 survivor-like result | Do not continue unlimited Plan D |
| Lattice v2 metadata/body dry-run | Completed | 100% | Static/registration discipline worked | Reusable as process pattern only |
| Lattice v2 body 8 limited replay | Completed and closed | 100% | 0 survivor, 0 hold, 8 no_go | Branch closed |
| V2 closeout review | Completed | 100% | `archive_v2_branch_and_stop` | Commit/handoff complete |
| V3 design-only page | Planned, not executed | 0% execution | Plan exists | Execute design-only next if user requests |

## 5. Why V2 Is Closed

| Evidence | Value | Interpretation |
|---|---:|---|
| V2 body replay rows | 8 | Exact bounded replay scope was honored |
| OK rows | 7 | Engine produced metrics for 7 rows |
| Error/no-metrics rows | 1 | One tick-origin negative-control row produced no metrics |
| Survivors | 0 | No candidate qualifies for OOS/Plan D |
| Holds | 0 | No borderline candidate preserved |
| no_go | 8 | All candidates rejected |
| OK-row profit | 7/7 negative | Failure is not just MDD gate strictness |
| OK-row MDD | 7/7 above cap 35 | Failure is materially outside risk cap |
| Parsed CSV loss shape | 7/7 broad-based loss | Failure is not one outlier trade |
| Corrected sell/risk audit | no_go unchanged | Prior table bug did not rescue v2 |

### Important Correction

The earlier risk/sell table incorrectly displayed values like `90` and `120` as stop/take-profit thresholds. These were hold-time thresholds. The corrected audit separates:

| Clause Type | Correct Interpretation |
|---|---|
| stop loss | negative return thresholds such as `-2` or `-3` |
| take profit | small positive thresholds such as `1`, `2`, `3`, or `4` |
| hold-time stop | minute thresholds such as `30`, `60`, `90`, `120` |
| late-session exit | time thresholds such as `145000`, `145500`, `91500` |

This correction changes the clause-level diagnosis but does not change the replay result.

## 6. What Was Learned From The Whole Research

| Research Area | What It Proved | What It Did Not Prove |
|---|---|---|
| Provider stabilization | Runtime failures can be separated from strategy failures | Strategy quality |
| Official tick 288 | Tick lattice was broadly loss-making under official warm64/full-period profile | Tick candidates are not reusable as survivors |
| Official min 288 | Min lane had better sparse signal than tick but still no go/hold | Original lattice is not sufficient |
| 576 P6 analysis | Failure map is useful: MDD, profit, daily trades, family/time/size patterns | It does not produce promotion candidates |
| Repair composite | Composite/coverage can find bounded signals | It is not final portfolio/export evidence |
| Plan D | Seed research can improve bounded candidates | Unlimited looping risks overfit and should stop |
| V2 body generation | Syntax/registration hygiene improved | Strategy quality still failed |
| V2 closeout | V2 branch should stop | It does not automatically authorize v3 generation |

## 7. Current Artifact Map

### 7.1 Latest Plans

| Purpose | Path | Status |
|---|---|---|
| V2 risk/sell review plan | `docs/research/condition_research/plans/lattice_condition_generation_v2_risk_sell_repair_review_20260709.md` | Created |
| V2 closeout/new-design review plan | `docs/research/condition_research/plans/lattice_condition_generation_v2_closeout_or_new_design_review_20260709.md` | Created and executed |
| V3 design-only plan | `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` | Created, not executed |

### 7.2 Latest V2 Evidence

| Purpose | Path |
|---|---|
| Risk/sell source receipt | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/source_read_receipt_risk_sell_review_20260709.json` |
| Risk/sell failure decomposition | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_failure_decomposition_20260709.json` |
| Human risk/sell decomposition | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_failure_decomposition_20260709.md` |
| Risk/sell repair decision | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_risk_sell_repair_decision_20260709.json` |
| Closeout source receipt | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/source_read_receipt_closeout_or_new_design_20260709.json` |
| Corrected sell/risk audit JSON | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_corrected_sell_risk_clause_audit_20260709.json` |
| Corrected sell/risk audit MD | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_corrected_sell_risk_clause_audit_20260709.md` |
| Replay integrity check | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_replay_evidence_integrity_check_20260709.json` |
| Final closeout decision | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_closeout_or_new_design_decision_20260709.json` |

### 7.3 Latest Update Logs

| Purpose | Path |
|---|---|
| V2 risk/sell review handoff | `docs/update_log/2026-07-09_lattice_v2_risk_sell_repair_review_handoff.md` |
| V2 context matrix | `docs/update_log/2026-07-09_lattice_v2_closeout_context_matrix.md` |
| V2 closeout review | `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md` |
| V2 closeout handoff | `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_handoff.md` |
| Cross-agent handoff | `docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md` |

## 8. Next Recommended Work

### Recommended Command

Run this only if the user wants to continue the research workflow:

```text
$start-work docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md
```

### What That Command Should Do

| Step | Purpose | Output |
|---|---|---|
| T0 | Read source package and lock scope | v3 source receipt |
| T1 | Convert prior failures into design lessons | failure lesson matrix |
| T2 | Write v3 design specification | v3 design spec |
| T3 | Write evaluation protocol and gates | protocol + dry-run-only next command |
| T4 | Write handoff and final verification | v3 design-only handoff |

### What That Command Must Not Do

| Forbidden | Reason |
|---|---|
| Generate STOM buy/sell bodies | v3 design is not yet approved |
| DB INSERT apply | Current page is design-only |
| DB UPDATE/DELETE | Always forbidden in this research lane |
| Official replay/backtest | No v3 candidates exist yet |
| OOS | No preregistered survivor exists |
| Plan D/P7 | No OOS survivor seed input exists |
| Portfolio | No candidate is promotion-ready |
| export/live/final promotion | Research lane only |

## 9. Conditional Future Flow

The next agent should not jump to later pages. Use this decision tree.

| Condition After V3 Design-Only Execution | Next Step | Command Shape |
|---|---|---|
| V3 design spec says stop | Stop research and write closeout | No automatic command |
| V3 design spec says dry-run can open | Create a new dry-run-only plan | `$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v3_candidate_static_dryrun_YYYYMMDD.md` |
| V3 design has unresolved evidence contradiction | Manual reconciliation only | `$start-work <manual-review-plan>` |
| V3 dry-run later produces static candidates | Still no replay until DB dry-run and explicit scope | Future bounded plan only |
| Future bounded replay produces survivor | Only then preregister OOS-style robustness | Future bounded plan only |
| Future OOS-style survivor exists | Only then Plan D intake may be considered | Future bounded plan only |

## 10. Hard Guardrails

| Guardrail | Required Behavior |
|---|---|
| Research lane only | Do not touch live/export/final/promotion paths |
| DB safety | No DB UPDATE/DELETE; no INSERT apply unless a future explicit plan says so |
| Worktree discipline | Stage explicit files only; never use `git add -A` |
| Dirty workspace | Do not stage dashboard 7 files, `.gjc`, unrelated `.omo` leftovers |
| A3 approval | Do not modify A3 promotion-review code without explicit user approval |
| V2 branch | Do not continue v2 body branch |
| Plan D | Do not reopen Plan D automatically |
| Full 288 | Do not run full tick/min 288 again from current scope |
| OOS | Do not run OOS without preregistration and selected survivor |
| Portfolio | Do not generate portfolio without OOS survivor and explicit scope |

## 11. Dirty Worktree Notes

At handoff creation time, the worktree contains many unrelated or separately-owned dirty paths. Agents must not assume all dirty files belong to the current task.

| Dirty Group | Status | Handling |
|---|---|---|
| Dashboard frontend 7 files | Modified, separate worktree/topic | Do not stage for condition research |
| `.gjc/` | Untracked runtime/tool residue | Do not stage |
| `.omo/evidence/tmap-walkforward/*` and old `.omo` plans | Untracked historical leftovers | Do not stage unless user explicitly asks |
| `.omo/ulw-loop/20260707_plan_d_final_loop/ledger.jsonl` | Modified historical loop ledger | Do not stage for this handoff |
| Condition research 20260709 docs/artifacts | Relevant | Safe to stage explicitly for this commit |
| `.omo/boulder.json`, `.omo/start-work/ledger.jsonl` | Relevant recent start-work records | Safe to stage explicitly if committing current research record |

## 12. Suggested Commit Scope For This Handoff

Use explicit path staging only.

| Include | Reason |
|---|---|
| `docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md` | New cross-agent handoff |
| `docs/update_log/2026-07-09_lattice_v2_*` | Latest v2 closeout/update-log docs |
| `docs/research/condition_research/plans/lattice_condition_generation_v2_*_20260709.md` | Plans that explain v2 risk/closeout review |
| `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` | Next executable design-only plan |
| `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/*20260709*` | Machine-readable receipts and decisions |
| `.omo/boulder.json` and `.omo/start-work/ledger.jsonl` | Recent start-work bookkeeping, if included intentionally |

| Exclude | Reason |
|---|---|
| dashboard frontend files | Separate dashboard work |
| `.gjc/` | Tool residue |
| broad `.omo/evidence` leftovers | Historical/unrelated |
| artifacts `.err` and old scripts | Not part of this handoff |
| protected runtime paths | Never stage casually |

## 13. What To Tell The User Next

If asked for status, report this table.

| Topic | User-Facing Summary |
|---|---|
| Current state | V2 is closed; v3 design-only plan is ready |
| Main result | The branch failed on real profit/MDD evidence, not only on a reporting bug |
| Next best action | Execute v3 design-only plan, not replay/OOS |
| Expected next duration | About 1.5-3 hours for design docs; no backtest runtime |
| Risk | If agents skip design and generate candidates, they may repeat v2 failure |
| Recommended command | `$start-work docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` |

## 14. Final Recommendation

The next work should continue only at the v3 design-only layer. Do not search for more survivors inside the closed v2 branch, do not reopen unlimited Plan D, and do not run new backtests until a future design/spec/static-dry-run page produces a bounded and explicitly approved next step.
