# 2026-07-06 Plan D Rank01 R2 Selected OOS Handoff

## 1. Scope

- plan: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`
- scope: `plan-d-rank01-r2-selected-oos-prereg-no-portfolio-export`
- objective: freeze selected R2 improved candidates, preregister them, and run only official OOS-style min warm64 for those selected candidates.
- hard stops observed: no portfolio, no export/live/final promotion, no DB UPDATE/DELETE, no candidates outside selected 3.

## 2. Inputs

- source receipt: `.omo/evidence/plan-d-rank01-r2-selected-oos-prereg-no-portfolio-export-20260706/source_read_receipt.md`
- preregistration: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank01_20260706/r_e_selected_oos_20260706/plan_d_rank01_r2_selected_oos_preregistration_20260706.md`
- pairs: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank01_20260706/r_e_selected_oos_20260706/pairs_plan_d_rank01_r2_selected3_oos_20260706.json`
- config: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank01_20260706/r_e_selected_oos_20260706/oos_config_min_plan_d_rank01_r2_selected3_20260706.json`

## 3. OOS-style Result

| run_id | rows | ok | gate_passed | survivor | hold | no_go | positive_control |
|---|---:|---:|---:|---:|---:|---:|---|
| lat_plan_d_rank01_r2_selected3_oos_min_warm64_20260706 | 3 | 3 | 3 | 3 | 0 | 0 | gate_healthy |

## 4. Survivors

| label | profit | MDD | trades | daily | score | note |
|---|---:|---:|---:|---:|---:|---|
| `plan_d_r1_rank01_r2_21_l14_rate_floor85_default_tp3_sl3_hold90` | 1,174,545 | 3.25 | 17 | 0.50 | 23.57 | trade_count<20 advisory |
| `plan_d_r1_rank01_r2_15_l14_amt14000_default_tp3_sl3_hold90` | 1,079,768 | 4.06 | 19 | 0.50 | 10.30 | trade_count<20 advisory |
| `plan_d_r1_rank01_r2_12_l14_amt13000_default_tp3_sl3_hold90` | 1,079,768 | 4.06 | 19 | 0.50 | 10.30 | trade_count<20 advisory |

## 5. Decision

- decision: `continue_rank01_r3_readiness_next_scope`
- recommended next parent: `plan_d_r1_rank01_r2_21_l14_rate_floor85_default_tp3_sl3_hold90`
- reason: all selected R2 candidates survived the OOS-style replay; the best OOS candidate has the highest OOS profit and lowest MDD among the selected set.
- caveat: this is fixed OOS-style robustness evidence, not fully blind discovery OOS, because selected candidates came from full-period R2 replay.
- low trade-count advisory: all survivors have 17~19 trades, so portfolio/export remains closed.

## 6. Next Recommended Command

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

??? plan-d-rank01-r2-survivor-freeze-r3-readiness-no-portfolio-export??? ????.
??? R2 selected OOS survivor ? ??? ??? ?? active parent? freeze??,
R3 ??? ?? R-a/R-b readiness? context pack? ??? R3 ?? ?? ?? ??? ???? ???.

??:
- portfolio ?? ??
- export/live/final promotion ??
- R3 ?? replay ?? ??
- DB UPDATE/DELETE ??
- git add -A ??
```
