# 2026-07-06 Plan D Rank01 R2 Limited Replay Handoff

## 1. Scope

- plan: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`
- scope: `plan-d-rank01-rd-freeze-r2-limited-replay-no-portfolio-export`
- objective: freeze slot04, design slot04-based R2 candidates, apply INSERT-only registration for static-gate-passing candidates, and run only official min full-period warm64 limited replay up to 24 pairs.
- hard stops observed: no OOS, no portfolio, no export/live/final promotion, no DB UPDATE/DELETE, no run beyond 24 pairs.

## 2. Read-First Receipt

- receipt: `.omo/evidence/plan-d-rank01-rd-freeze-r2-limited-replay-no-portfolio-export-20260706/source_read_receipt.md`
- read_scope: full_document for plan, prior handoff, R-c replay result, R-c decision, Plan D document, strategy.txt, rules.txt.

## 3. Freeze And Watch

| role | label | profit | mdd | trades | daily | note |
|---|---|---:|---:|---:|---:|---|
| active_parent_for_r2 | plan_d_r1_rank01_04_repair_l14_liquidity_tight_default | 2,153,579 | 18.69 | 201 | 0.90 | frozen from R-c improved candidate |
| coverage_watch_only | plan_d_r1_rank01_06_discovery_adjacent_l13_l14_coverage | 1,059,257 | 18.49 | 448 | 2.10 | watch-only, not active R2 parent |

## 4. R2 Candidate And Registration

| item | result |
|---|---:|
| designed pairs | 24 |
| static gate passed | 24 |
| dry-run planned inserts | 48 |
| INSERT-only apply inserted rows | 48 |
| strategy DB backup | `ai_strategy_loop\state\loop_strategies.db.bak.lattice_20260706T075715Z` |

## 5. Limited Replay Result

| run_id | profile | rows | ok | gate_passed | improved | flat | no_go |
|---|---|---:|---:|---:|---:|---:|---:|
| lat_plan_d_rank01_r2_24_min_warm64_20260706 | official min full-period warm64 | 24 | 24 | 24 | 9 | 15 | 0 |

## 6. Recommended Next Freeze Candidates

| reason | label | profit | mdd | trades | daily |
|---|---|---:|---:|---:|---:|
| best_profit | plan_d_r1_rank01_r2_15_l14_amt14000_default_tp3_sl3_hold90 | 2,773,694 | 15.75 | 192 | 0.90 |
| lowest_mdd_among_improved | plan_d_r1_rank01_r2_21_l14_rate_floor85_default_tp3_sl3_hold90 | 2,515,910 | 15.57 | 188 | 0.90 |
| nearby_amount_axis_confirmation | plan_d_r1_rank01_r2_12_l14_amt13000_default_tp3_sl3_hold90 | 2,550,258 | 15.75 | 197 | 0.90 |

## 7. Decision

- decision: open a next bounded selected OOS/preregistration scope only.
- reason: 24/24 rows completed, 24/24 gates passed, and 9 rows improved over frozen slot04 while preserving or improving MDD.
- caveat: this replay is still in-sample/full-period replay, not blind OOS evidence. OOS must be preregistered and limited to selected frozen candidates.

## 8. Next Recommended Command

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

??? plan-d-rank01-r2-selected-oos-prereg-no-portfolio-export??? ????.
??? R2 limited replay improved ?? ? selected freeze ??? preregistration?? ????,
?? OOS? ?? ??? Plan D ?? ??? ?? ?? ??? ???? ???.

??:
- portfolio ?? ??
- export/live/final promotion ??
- preregistration ?? OOS ??
- selected freeze ?? ? OOS ?? ??
- DB UPDATE/DELETE ??
- git add -A ??
```
