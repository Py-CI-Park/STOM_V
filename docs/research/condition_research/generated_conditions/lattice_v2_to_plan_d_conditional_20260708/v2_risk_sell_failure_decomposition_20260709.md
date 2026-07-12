# V2 Risk/Sell Failure Decomposition 20260709

## Summary

| Item | Value |
|---|---:|
| row_count | 8 |
| ok_count | 7 |
| error_count | 1 |
| survivor_count | 0 |
| hold_count | 0 |
| no_go_count | 8 |
| primary_failure_counts | {'loss_plus_mdd': 7, 'no_metrics': 1} |
| parsed_csv_count | 7 |
| broad_based_loss_count | 7 |
| all_min_ok_rows_have_stop_loss | True |
| all_min_ok_rows_have_take_profit | True |
| all_min_ok_rows_have_time_stop | True |
| all_min_ok_rows_losing | True |
| all_min_ok_rows_mdd_over_cap | True |
| profile_note | one tick-origin negative-control row produced no metrics under min profile; excluded from min-origin repair decision |

## Row-Level Findings

| gen | label | status | profit | MDD | trades | daily | primary failure | loss concentration |
|---:|---|---|---:|---:|---:|---:|---|---|
| 0 | body_01_lattice_v2_coverage_01_s09_s10_l13_l14_daily_bridge | ok | -514,545,798 | 312.19 | 21,987 | 103.20 | loss_plus_mdd | broad_based |
| 1 | body_02_lattice_v2_coverage_03_l13_l14_l1430_daily_boost | ok | -373,908,892 | 188.20 | 12,981 | 60.90 | loss_plus_mdd | broad_based |
| 2 | body_03_lattice_v2_coverage_06_momentum_strength_surge_coverage | ok | -288,376,184 | 207.91 | 11,249 | 52.80 | loss_plus_mdd | broad_based |
| 3 | body_04_lattice_v2_risk_01_mdd10_l13_l14_default_diverse | ok | -106,616,341 | 127.28 | 5,015 | 23.50 | loss_plus_mdd | broad_based |
| 4 | body_05_lattice_v2_risk_08_dailycovered_nonpositive_repair | ok | -881,171,389 | 441.67 | 30,653 | 143.90 | loss_plus_mdd | broad_based |
| 5 | body_06_lattice_v2_seed_01_rank03_r2_l13_l1430_component_only | ok | -103,427,022 | 90.64 | 4,487 | 21.10 | loss_plus_mdd | broad_based |
| 6 | body_07_lattice_v2_neg_01_tick_prevday_active_0900_loss_shape | error | 0 | 0.00 | 0 | 0.00 | no_metrics | no_metrics |
| 7 | body_08_lattice_v2_hold_04_holdout_rank03_r2_l13_l1430_default | ok | -101,728,684 | 89.63 | 4,365 | 20.50 | loss_plus_mdd | broad_based |

## Sell/Risk Clause Audit

| gen | stop loss | take profit | time stop | late exit | range cap | overtrade throttle |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 90.0 | 90.0 | 145500.0 | 145500.0 | True | False |
| 1 | 90.0 | 90.0 | 145500.0 | 145500.0 | True | False |
| 2 | 120.0 | 120.0 | 145500.0 | 145500.0 | True | False |
| 3 | 60.0 | 60.0 | 145000.0 | 145000.0 | True | False |
| 4 | 90.0 | 90.0 | 145500.0 | 145500.0 | True | False |
| 5 | 90.0 | 90.0 | 145500.0 | 145500.0 | True | False |
| 6 | 30.0 | 30.0 | 91500.0 | 91500.0 | True | False |
| 7 | 90.0 | 90.0 | 145500.0 | 145500.0 | True | False |

## CSV Loss Concentration

| gen | csv rows | gross win | gross loss | loss trade ratio | bottom10 loss share | worst exit condition |
|---:|---:|---:|---:|---:|---:|---|
| 0 | 21,987 | 908258346.0 | -1422804144.0 | 0.6386955928503206 | 0.002609470892853964 | elif 수익률 <= -3: |
| 1 | 12,981 | 316436972.0 | -690345864.0 | 0.7078807487866883 | 0.0048720839442879605 | elif 수익률 <= -3: |
| 2 | 11,249 | 575996410.0 | -864372594.0 | 0.6614810205351587 | 0.006104559580703226 | elif 수익률 <= -3: |
| 3 | 5,015 | 97345943.0 | -203962284.0 | 0.6811565304087737 | 0.010979662298741467 | elif 수익률 <= -2: |
| 4 | 30,653 | 1190811959.0 | -2071983348.0 | 0.6655139790558836 | 0.0019039067103545082 | elif 수익률 <= -3: |
| 5 | 4,487 | 129633375.0 | -233060397.0 | 0.6592377980833519 | 0.011572648269366846 | elif 수익률 <= -3: |
| 6 | 0 |  |  |  |  | no_metrics |
| 7 | 4,365 | 122928040.0 | -224656724.0 | 0.6618556701030928 | 0.012013145887411765 | elif 수익률 <= -3: |

## Decision

- Decision: `stop_v2_body_branch`
- Rationale: Losses are broad-based across the available OK-row CSVs despite uniform stop-loss, take-profit, and time-stop sell clauses; the branch appears structurally losing rather than missing a simple sell/risk clause.
- Next command: `$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v2_closeout_or_new_design_review_20260709.md`

## Guardrails Observed

- DB INSERT/UPDATE/DELETE not executed.
- Replay/OOS/Plan D not executed.
- Existing CSV/result/seed artifacts were read only.
