# Plan D rank01 R3 limited replay summary

- run_id: `lat_plan_d_rank01_r3_8_min_warm64_20260706`
- rows: 8
- gate_passed: 8
- decision_counts: `{'hold': 1, 'flat': 6, 'improved': 1}`
- selected_oos_ready: True

| label | decision | profit | MDD | trades | daily | reason |
|---|---|---:|---:|---:|---:|---|
| `plan_d_r1_rank01_r3_01_l14_rate80_hold90` | hold | 2,482,914 | 15.75 | 198 | 0.90 | near_parent_profit_with_coverage_gain_mdd_tolerable |
| `plan_d_r1_rank01_r3_02_l14_amt11500_rate85_hold90` | flat | 2,350,845 | 15.57 | 189 | 0.90 | gate_passed_but_not_improved_for_r3_coverage_objective |
| `plan_d_r1_rank01_r3_03_l14_amt11000_rate85_hold90` | flat | 2,350,845 | 15.57 | 189 | 0.90 | gate_passed_but_not_improved_for_r3_coverage_objective |
| `plan_d_r1_rank01_r3_04_l14_end1445_rate85_hold90` | flat | 1,742,342 | 17.95 | 234 | 1.10 | gate_passed_but_not_improved_for_r3_coverage_objective |
| `plan_d_r1_rank01_r3_05_l13_l14_rate85_hold90` | improved | 2,124,078 | 11.55 | 386 | 1.80 | coverage_risk_improved_trade_count_1p5x_and_mdd_lower_positive_profit |
| `plan_d_r1_rank01_r3_06_l1430_bridge_rate85_hold90` | flat | 1,742,342 | 17.95 | 234 | 1.10 | gate_passed_but_not_improved_for_r3_coverage_objective |
| `plan_d_r1_rank01_r3_07_morning_strength_relax_hold90` | flat | 1,622,084 | 18.44 | 198 | 0.90 | gate_passed_but_not_improved_for_r3_coverage_objective |
| `plan_d_r1_rank01_r3_08_momentum_mult992_hold90` | flat | 1,537,805 | 17.05 | 195 | 0.90 | gate_passed_but_not_improved_for_r3_coverage_objective |
