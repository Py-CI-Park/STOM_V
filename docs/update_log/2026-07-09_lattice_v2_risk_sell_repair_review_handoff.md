# Lattice V2 Risk/Sell Repair Review Handoff

Date: 2026-07-09T13:20:00+09:00

## Scope

Executed analysis-only review from `docs/research/condition_research/plans/lattice_condition_generation_v2_risk_sell_repair_review_20260709.md`.
No DB mutation, replay, OOS, Plan D, portfolio, or promotion path was executed.

## Result

| Item | Value |
|---|---:|
| candidates reviewed | 8 |
| OK rows | 7 |
| error rows | 1 |
| survivor | 0 |
| hold | 0 |
| no_go | 8 |
| parsed CSVs | 7 |
| broad-based loss rows | 7 |
| repair decision | `stop_v2_body_branch` |

## Interpretation

Losses are broad-based across the available OK-row CSVs despite uniform stop-loss, take-profit, and time-stop sell clauses; the branch appears structurally losing rather than missing a simple sell/risk clause.

The current v2 body branch should not continue into more automatic candidate generation from the same structure. The OK rows already contain stop-loss, take-profit, time-stop, late-exit, and range-cap clauses, yet losses remain broad-based and MDD exceeds the cap across every OK row.

## Candidate Table

| gen | label | status | profit | MDD | trades | daily | primary failure |
|---:|---|---|---:|---:|---:|---:|---|
| 0 | body_01_lattice_v2_coverage_01_s09_s10_l13_l14_daily_bridge | ok | -514,545,798 | 312.19 | 21,987 | 103.20 | loss_plus_mdd |
| 1 | body_02_lattice_v2_coverage_03_l13_l14_l1430_daily_boost | ok | -373,908,892 | 188.20 | 12,981 | 60.90 | loss_plus_mdd |
| 2 | body_03_lattice_v2_coverage_06_momentum_strength_surge_coverage | ok | -288,376,184 | 207.91 | 11,249 | 52.80 | loss_plus_mdd |
| 3 | body_04_lattice_v2_risk_01_mdd10_l13_l14_default_diverse | ok | -106,616,341 | 127.28 | 5,015 | 23.50 | loss_plus_mdd |
| 4 | body_05_lattice_v2_risk_08_dailycovered_nonpositive_repair | ok | -881,171,389 | 441.67 | 30,653 | 143.90 | loss_plus_mdd |
| 5 | body_06_lattice_v2_seed_01_rank03_r2_l13_l1430_component_only | ok | -103,427,022 | 90.64 | 4,487 | 21.10 | loss_plus_mdd |
| 6 | body_07_lattice_v2_neg_01_tick_prevday_active_0900_loss_shape | error | 0 | 0.00 | 0 | 0.00 | no_metrics |
| 7 | body_08_lattice_v2_hold_04_holdout_rank03_r2_l13_l1430_default | ok | -101,728,684 | 89.63 | 4,365 | 20.50 | loss_plus_mdd |

## Artifacts

- Source receipt: `docs\research\condition_research\generated_conditions\lattice_v2_to_plan_d_conditional_20260708\source_read_receipt_risk_sell_review_20260709.json`
- Decomposition JSON: `docs\research\condition_research\generated_conditions\lattice_v2_to_plan_d_conditional_20260708\v2_risk_sell_failure_decomposition_20260709.json`
- Decomposition MD: `docs\research\condition_research\generated_conditions\lattice_v2_to_plan_d_conditional_20260708\v2_risk_sell_failure_decomposition_20260709.md`
- Repair decision: `docs\research\condition_research\generated_conditions\lattice_v2_to_plan_d_conditional_20260708\v2_risk_sell_repair_decision_20260709.json`

## Next Command

```text
$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v2_closeout_or_new_design_review_20260709.md

??? v2 body branch? ?? ????? ??, ?? ??? ??/???? ?? ??? ?? generation design?? ?? ???? ???.

??: DB INSERT/UPDATE/DELETE, replay, OOS, Plan D, portfolio, export/live/final promotion.
```
