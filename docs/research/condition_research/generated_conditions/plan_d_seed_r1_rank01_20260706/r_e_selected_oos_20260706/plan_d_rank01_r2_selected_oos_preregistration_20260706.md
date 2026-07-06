# Plan D rank01 R2 Selected OOS Preregistration

- created_at: 2026-07-06T18:48:27+09:00
- scope: `plan-d-rank01-r2-selected-oos-prereg-no-portfolio-export`
- lane: min
- profile: official OOS-style min warm64
- OOS-style window: 2026-01-01~2026-02-27
- time window: 09:00~15:19
- candidate_count: 3
- forbidden: no portfolio, no export/live/final promotion, no DB UPDATE/DELETE, no candidates outside selected 3

## Selection Rule

Use only `recommended_freeze_next` from the R2 round decision:

| order | reason | label | R2 profit | R2 MDD | R2 trades | R2 daily |
|---:|---|---|---:|---:|---:|---:|
| 1 | best_profit | `plan_d_r1_rank01_r2_15_l14_amt14000_default_tp3_sl3_hold90` | 2,773,694 | 15.75 | 192 | 0.90 |
| 2 | lowest_mdd_among_improved | `plan_d_r1_rank01_r2_21_l14_rate_floor85_default_tp3_sl3_hold90` | 2,515,910 | 15.57 | 188 | 0.90 |
| 3 | nearby_amount_axis_confirmation | `plan_d_r1_rank01_r2_12_l14_amt13000_default_tp3_sl3_hold90` | 2,550,258 | 15.75 | 197 | 0.90 |

## Decision Rule

- survivor: status ok, gate_passed true, profit > 0, MDD <= 35, daily_avg_trades >= 0.5
- hold: status ok and profit > 0 but one non-critical gate fails
- no_go: error/no_trades, profit <= 0, or MDD > 35

## Caveat

This is robustness/OOS-style evidence because the selected R2 candidates came from full-period replay that included this window. Do not treat it as fully blind discovery OOS.
