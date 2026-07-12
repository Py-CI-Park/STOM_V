# Plan D rank03 R1 limited replay summary

- created_at: 2026-07-07T17:55:13+09:00
- run_id: `lat_plan_d_rank03_r1_8_min_warm64_20260707`
- profile: official min full-period warm64
- period: 20250407~20260227
- warm engines: 64
- honest_rows: 8/8
- decision_counts: `{"flat": 5, "no_go": 2, "improved": 1}`

| gen | label | decision | profit | MDD | trades | daily | delta_profit | delta_mdd | reason |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 0 | `plan_d_r1_rank03_r1_01_l1430_rate75_hold90` | flat | 831013 | 16.90 | 184 | 0.90 | -43228 | -0.14 | gate_passed_but_not_improved_vs_rank03_parent_preflight |
| 1 | `plan_d_r1_rank03_r1_02_l1430_amt9000_rate80_hold90` | flat | 827445 | 17.04 | 182 | 0.90 | -46796 | 0.00 | gate_passed_but_not_improved_vs_rank03_parent_preflight |
| 2 | `plan_d_r1_rank03_r1_03_l1430_end1500_rate80_hold90` | flat | 932499 | 18.24 | 219 | 1.00 | 58258 | 1.20 | gate_passed_but_not_improved_vs_rank03_parent_preflight |
| 3 | `plan_d_r1_rank03_r1_04_l14_l1430_rate80_hold90` | flat | 726216 | 20.50 | 257 | 1.20 | -148025 | 3.46 | gate_passed_but_not_improved_vs_rank03_parent_preflight |
| 4 | `plan_d_r1_rank03_r1_05_l13_l1430_rate80_hold90` | flat | 168870 | 12.80 | 434 | 2.00 | -705371 | -4.24 | coverage_watch_trade_count_up_and_mdd_lower_but_profit_below_parent |
| 5 | `plan_d_r1_rank03_r1_06_morning_strength_relax_hold90` | no_go | -276996 | 20.15 | 191 | 0.90 | -1151237 | 3.11 | gate_failed_total_profit_-2.77e+05_le_0 |
| 6 | `plan_d_r1_rank03_r1_07_momentum_mult992_hold90` | no_go | -103864 | 19.00 | 186 | 0.90 | -978105 | 1.96 | gate_failed_total_profit_-1.039e+05_le_0 |
| 7 | `plan_d_r1_rank03_r1_08_parent_buy_default_tp3_sl3_hold90` | improved | 1652322 | 15.79 | 181 | 0.80 | 778081 | -1.25 | profit_above_rank03_parent_preflight_and_mdd_not_worse |

## Next
Open selected OOS only after freeze/preregistration. Do not run portfolio/export/live/final promotion.
