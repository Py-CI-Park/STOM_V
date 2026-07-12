# Plan D Rank01 R2 Selected OOS Summary

- created_at: 2026-07-06T18:56:08+09:00
- scope: plan-d-rank01-r2-selected-oos-prereg-no-portfolio-export
- run_id: lat_plan_d_rank01_r2_selected3_oos_min_warm64_20260706
- profile: min warm64 OOS-style 2026-01-01~2026-02-27
- selected candidates only: 3
- portfolio/export/live/final: not executed

## Result

| rows | ok | gate_passed | survivor | hold | no_go | positive_control |
|---:|---:|---:|---:|---:|---:|---|
| 3 | 3 | 3 | 3 | 0 | 0 | gate_healthy |

## Survivors

| label | profit | MDD | trades | daily | score | advisory |
|---|---:|---:|---:|---:|---:|---|
| `plan_d_r1_rank01_r2_21_l14_rate_floor85_default_tp3_sl3_hold90` | 1,174,545 | 3.25 | 17 | 0.50 | 23.57 | trade_count_below_20_plan_d_advisory |
| `plan_d_r1_rank01_r2_15_l14_amt14000_default_tp3_sl3_hold90` | 1,079,768 | 4.06 | 19 | 0.50 | 10.30 | trade_count_below_20_plan_d_advisory |
| `plan_d_r1_rank01_r2_12_l14_amt13000_default_tp3_sl3_hold90` | 1,079,768 | 4.06 | 19 | 0.50 | 10.30 | trade_count_below_20_plan_d_advisory |

## Decision

Next scope: `plan-d-rank01-r2-survivor-freeze-r3-readiness-no-portfolio-export`

The next round is justified because all 3 selected candidates survived the OOS-style replay, but the low trade-count advisory means portfolio/export should remain closed.
