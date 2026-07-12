# Plan D Rank01 R2 Limited Replay Summary

- created_at: 2026-07-06T17:17:04+09:00
- scope: plan-d-rank01-rd-freeze-r2-limited-replay-no-portfolio-export
- run_id: lat_plan_d_rank01_r2_24_min_warm64_20260706
- profile: official min full-period warm64
- limit: 24 pairs; OOS/portfolio/export not executed

## Baseline

| label | profit | mdd | trades | daily |
|---|---:|---:|---:|---:|
| plan_d_r1_rank01_04_repair_l14_liquidity_tight_default | 2,153,579 | 18.69 | 201 | 0.90 |

## Replay Result

| rows | ok | gate_passed | improved | flat | no_go |
|---:|---:|---:|---:|---:|---:|
| 24 | 24 | 24 | 9 | 15 | 0 |

## Recommended Next Freeze

| reason | label | profit | mdd | trades | daily | buy_axis | sell_profile |
|---|---|---:|---:|---:|---:|---|---|
| best_profit | plan_d_r1_rank01_r2_15_l14_amt14000_default_tp3_sl3_hold90 | 2,773,694 | 15.75 | 192 | 0.90 | l14_amt14000 | default_tp3_sl3_hold90 |
| lowest_mdd_among_improved | plan_d_r1_rank01_r2_21_l14_rate_floor85_default_tp3_sl3_hold90 | 2,515,910 | 15.57 | 188 | 0.90 | l14_rate_floor85 | default_tp3_sl3_hold90 |
| nearby_amount_axis_confirmation | plan_d_r1_rank01_r2_12_l14_amt13000_default_tp3_sl3_hold90 | 2,550,258 | 15.75 | 197 | 0.90 | l14_amt13000 | default_tp3_sl3_hold90 |

## Decision

Selected OOS preregistration can be opened in the next bounded scope. This scope did not execute OOS, portfolio, export/live/final promotion, DB UPDATE/DELETE, or more than 24 pairs.
