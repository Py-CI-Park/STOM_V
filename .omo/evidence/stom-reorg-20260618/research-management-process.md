# Research Management Operating Process - STOM Reorganization Page 8

Generated: 2026-06-18T22:45:47+09:00

## Purpose

This process makes research management improve research quality by forcing clear names, branch attribution, official OOS separation, evidence lineage, dashboard visibility, and next-action decisions.

## Lifecycle

| Step | Output | Required Fields | Stop Gate |
|---:|---|---|---|
| 1 | preregistration | hypothesis, machine name, display alias, evidence type, target period, expected stop conditions | no run without hypothesis and evidence type |
| 2 | run | command, config, source files, runtime notes, raw jsonl/log/official JSON | stop on timeout/hung command without cleanup receipt |
| 3 | record | raw evidence, summary, log, dashboard summary | stop on summary parse or jsonl parse error |
| 4 | classify evidence | official OOS / CSV reanalysis / portfolio rule / docs-only / blocked | stop if evidence type is ambiguous |
| 5 | update registry | machine name, display alias, OOS status, promotion status, next action | stop if registry does not cite raw source |
| 6 | expose dashboard | research card, alias, badge, detail link, error state | stop if card hides evidence type |
| 7 | decide next action | promote, reject, shadow, rerun, block, or design-only | stop if no decision owner/status |

## Page Templates

### Preregistration

```markdown
# <display_alias> Preregistration
- machine_name:
- display_alias:
- candidate_family:
- hypothesis:
- evidence_type:
- train/source period:
- official OOS period:
- inputs:
- branch attribution requirement:
- seed bank link:
- stop conditions:
- dashboard badge:
- next action if pass:
- next action if fail:
```

### Run Log

```markdown
# <campaign> Run Log
- command:
- config:
- start/end:
- generated files:
- cleanup receipt:
- malformed input handling:
- stale state check:
- dirty worktree check:
- warnings:
```

### Result Card

```markdown
# <display_alias> Result Card
- machine_name:
- badge:
- evidence_type:
- profit:
- MDD:
- trades:
- period:
- official OOS status:
- promotion_status:
- source files:
- dashboard record:
```

### OOS Decision

```markdown
# <candidate> OOS Decision
- decision: promote | reject | shadow | rerun | blocked
- official OOS result:
- MDD cap:
- trade count:
- branch attribution:
- drift check:
- reason:
- next action:
```

### Dashboard Card

```markdown
# Dashboard Card Spec
- campaign id:
- display title:
- machine name visible: yes
- badge:
- evidence source links:
- summary/detail availability:
- warning text:
- next-action queue link:
```

### Next-Action Queue

```markdown
# Next Action Queue
1. candidate:
   action:
   reason:
   estimated time:
   blocker:
   expected artifact:
```

## Stop Conditions

| Stop Condition | Meaning | Required Response |
|---|---|---|
| overfit risk | calendar/month/weekday exclusion wins only by score | shadow only; require causal rationale before promotion |
| official OOS fail | gate false, negative result, or MDD breach | reject or redesign; preserve evidence |
| MDD cap fail | drawdown exceeds candidate family cap | block promotion; compare defensive variants |
| summary drift | summary and raw jsonl/JSON disagree | repair summary before dashboard/registry update |
| insufficient trades | trade count too low for claim | rerun wider period or mark inconclusive |
| branch attribution missing | AND/OR branches not tied to P/L | require branch_id attribution before promotion |
| protected/live dependency | V3K gate/live/DB/write required | block unless separately approved |

## Feedback Loop

| Management Signal | Research Improvement |
|---|---|
| branch attribution | identifies which AND/OR branch adds or destroys lift |
| seed bank link | prevents repeated cold-start failures and focuses mutation |
| registry status | stops raw score winners from being mistaken for promotion candidates |
| evidence type badge | prevents CSV reanalysis from being called official OOS |
| dashboard gap | becomes the next dashboard task only after evidence taxonomy is stable |
| stop condition | prevents overfit and weak-trade candidates from consuming OOS time |

## Default Next Research Queue

| Priority | Action | Candidate | Evidence Output |
|---:|---|---|---|
| 1 | official OOS | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | official OOS JSON + dashboard card + promotion decision |
| 2 | shadow comparison | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | shadow OOS comparison card |
| 3 | portfolio report | `exit2_full_after_prior_r8r2_loss_else_off` | portfolio-rule report, not condition promotion |
| 4 | standalone filter OOS | `r8_exclude_cap_lt_1500` | isolation OOS report |
| 5 | branch attribution | top AND/OR candidates | branch_id profit/MDD/OOS lift table |

## Dashboard Feedback Rule

Every completed research campaign must produce or update:

1. registry entry,
2. Research Records card,
3. badge/evidence type,
4. next-action status,
5. dashboard gap if any required data cannot be displayed.

If the dashboard cannot show alias, evidence type, OOS status, and next action, the campaign is not considered management-complete even if the analysis itself is done.

Cleanup receipt:
- No new OOS run, PR, push, branch, protected path write, live/V3K action, or dashboard implementation was performed.
