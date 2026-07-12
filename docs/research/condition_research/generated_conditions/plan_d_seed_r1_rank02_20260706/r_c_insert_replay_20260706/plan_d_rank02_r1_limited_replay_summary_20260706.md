# Plan D rank02 R1 limited replay summary

- created_at: 2026-07-06T23:51:54+09:00
- run_id: `lat_plan_d_rank02_r1_8_min_warm64_20260706`
- profile: official min full-period warm64
- period: 20250407~20260227
- warm engines: 64
- honest_rows: 8/8
- decision_counts: `{"flat": 6, "improved": 2}`

| gen | label | decision | profit | MDD | trades | daily | delta_profit | delta_mdd | reason |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 0 | `plan_d_r1_rank02_r1_01_l14_rate75_hold90` | flat | 765458 | 20.62 | 215 | 1.00 | -575372 | 2.06 | gate_passed_but_not_improved_vs_rank02_parent_preflight |
| 1 | `plan_d_r1_rank02_r1_02_l14_amt9000_rate80_hold90` | improved | 1348845 | 18.56 | 204 | 1.00 | 8015 | 0.00 | profit_above_rank02_parent_preflight_and_mdd_not_worse |
| 2 | `plan_d_r1_rank02_r1_03_l14_end1445_rate80_hold90` | flat | 704443 | 20.66 | 252 | 1.20 | -636387 | 2.10 | gate_passed_but_not_improved_vs_rank02_parent_preflight |
| 3 | `plan_d_r1_rank02_r1_04_l13_l14_rate80_hold90` | flat | 385845 | 16.09 | 423 | 2.00 | -954985 | -2.47 | coverage_watch_trade_count_up_and_mdd_lower_but_profit_below_parent |
| 4 | `plan_d_r1_rank02_r1_05_l1430_bridge_rate80_hold90` | flat | 704443 | 20.66 | 252 | 1.20 | -636387 | 2.10 | gate_passed_but_not_improved_vs_rank02_parent_preflight |
| 5 | `plan_d_r1_rank02_r1_06_morning_strength_relax_hold90` | flat | 572757 | 24.43 | 211 | 1.00 | -768073 | 5.87 | gate_passed_but_not_improved_vs_rank02_parent_preflight |
| 6 | `plan_d_r1_rank02_r1_07_momentum_mult992_hold90` | flat | 362725 | 25.38 | 208 | 1.00 | -978105 | 6.82 | gate_passed_but_not_improved_vs_rank02_parent_preflight |
| 7 | `plan_d_r1_rank02_r1_08_parent_buy_default_tp3_sl3_hold90` | improved | 2216506 | 16.31 | 203 | 1.00 | 875676 | -2.25 | profit_above_rank02_parent_preflight_and_mdd_not_worse |

## Next
Open selected OOS only after freeze/preregistration. Do not run portfolio/export/live/final promotion.
