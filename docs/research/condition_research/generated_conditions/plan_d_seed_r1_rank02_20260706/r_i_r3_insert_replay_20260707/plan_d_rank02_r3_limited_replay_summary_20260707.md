# Plan D rank02 R3 limited replay summary

- run_id: `lat_plan_d_rank02_r3_8_min_warm64_20260707`
- lane: min
- profile: official full-period warm64
- honest rows: 8/8
- gate passed: 8/8
- improved: 1
- flat: 7
- no_go: 0

| label | decision | profit | MDD | trades | daily | reason |
|---|---|---:|---:|---:|---:|---|
| `plan_d_r1_rank02_r3_01_amt8000_default_tp3_sl3_hold90` | improved | 2297191 | 16.31 | 209 | 1.00 | profit_above_active_r2_full_period_and_mdd_not_worse |
| `plan_d_r1_rank02_r3_02_amt8000_tight_tp3_sl2p5_hold90` | flat | 1459465 | 13.79 | 210 | 1.00 | gate_passed_but_not_improved_vs_active_r2_full_period |
| `plan_d_r1_rank02_r3_03_active_buy_hold60_tp3_sl3` | flat | 1851564 | 19.24 | 209 | 1.00 | gate_passed_but_not_improved_vs_active_r2_full_period |
| `plan_d_r1_rank02_r3_04_active_buy_tp2p5_sl2p5_hold90` | flat | 434740 | 16.40 | 210 | 1.00 | gate_passed_but_not_improved_vs_active_r2_full_period |
| `plan_d_r1_rank02_r3_05_active_buy_tp3_sl2p5_hold60` | flat | 1190387 | 17.00 | 210 | 1.00 | gate_passed_but_not_improved_vs_active_r2_full_period |
| `plan_d_r1_rank02_r3_06_amt8500_default_tp3_sl3_hold90` | flat | 2165123 | 16.31 | 208 | 1.00 | gate_passed_but_not_improved_vs_active_r2_full_period |
| `plan_d_r1_rank02_r3_07_l1430_bridge_default_tp3_sl3` | flat | 1478669 | 17.51 | 260 | 1.20 | gate_passed_but_not_improved_vs_active_r2_full_period |
| `plan_d_r1_rank02_r3_08_l13_l14_default_tp3_sl3` | flat | 1509737 | 13.59 | 446 | 2.10 | coverage_watch_high_trades_lower_mdd_but_profit_below_active_baseline |

## Next Decision

- selected OOS preregistration can open for the improved candidate only.
- OOS/portfolio/export/live/final were not executed in this scope.
