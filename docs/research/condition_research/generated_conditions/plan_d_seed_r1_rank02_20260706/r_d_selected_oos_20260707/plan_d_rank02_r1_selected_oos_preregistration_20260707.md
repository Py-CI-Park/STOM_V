# Plan D rank02 R1 Selected OOS Preregistration

- created_at: 2026-07-07T00:06:43+09:00
- scope: `plan-d-rank02-selected-oos-prereg-no-portfolio-export`
- lane: min
- profile: official OOS-style min warm64
- OOS-style window: 2026-01-01~2026-02-27
- time window: 09:00~15:19
- candidate_count: 2
- forbidden: no portfolio, no export/live/final promotion, no DB UPDATE/DELETE, no candidates outside selected 2

## Selection Rule

Use only improved candidates from the rank02 R1 round decision:

| order | reason | label | R1 profit | R1 MDD | R1 trades | R1 daily |
|---:|---|---|---:|---:|---:|---:|
| 1 | best_profit_and_lower_mdd_vs_rank02_parent_preflight | `plan_d_r1_rank02_r1_08_parent_buy_default_tp3_sl3_hold90` | 2,216,506 | 16.31 | 203 | 1.00 |
| 2 | secondary_improved_confirmation_same_or_better_mdd | `plan_d_r1_rank02_r1_02_l14_amt9000_rate80_hold90` | 1,348,845 | 18.56 | 204 | 1.00 |

## Decision Rule

- survivor: status ok, gate_passed true, profit > 0, MDD <= 35, daily_avg_trades >= 0.5
- hold: status ok and profit > 0 but one non-critical gate fails
- no_go: error/no_trades, profit <= 0, or MDD > 35

## Caveat

This is robustness/OOS-style evidence because the selected R1 candidates came from full-period replay that included this window. Do not treat it as fully blind discovery OOS.
