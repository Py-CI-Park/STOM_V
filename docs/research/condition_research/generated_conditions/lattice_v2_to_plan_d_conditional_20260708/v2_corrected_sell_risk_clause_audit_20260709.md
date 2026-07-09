# V2 Corrected Sell/Risk Clause Audit

| Item | Result |
|---|---|
| Scope | analysis-only, no replay/OOS/DB/Plan D |
| Prior table status | superseded |
| Correction | stop/take-profit/time-stop/late-exit separated from source sell_code |
| Decision impact | no_go decision unchanged |

## Corrected Threshold Table

| Gen | Label | Family | Status | Profit | MDD | Stop | Take Profit | Hold Min | Late Exit | Previous Wrong Pattern |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 0 | `body_01_lattice_v2_coverage_01_s09_s10_l13_l14_daily_bridge` | coverage_composite | ok | -514545798.0 | 312.19 | -3.0 | 3.0 | 90 | 145500 | old_stop=90.0, old_tp=90.0 |
| 1 | `body_02_lattice_v2_coverage_03_l13_l14_l1430_daily_boost` | coverage_composite | ok | -373908892.0 | 188.2 | -3.0 | 3.0 | 90 | 145500 | old_stop=90.0, old_tp=90.0 |
| 2 | `body_03_lattice_v2_coverage_06_momentum_strength_surge_coverage` | coverage_composite | ok | -288376184.0 | 207.91 | -3.0 | 4.0 | 120 | 145500 | old_stop=120.0, old_tp=120.0 |
| 3 | `body_04_lattice_v2_risk_01_mdd10_l13_l14_default_diverse` | risk_balanced_composite | ok | -106616341.0 | 127.28 | -2.0 | 2.0 | 60 | 145000 | old_stop=60.0, old_tp=60.0 |
| 4 | `body_05_lattice_v2_risk_08_dailycovered_nonpositive_repair` | risk_balanced_composite | ok | -881171389.0 | 441.67 | -3.0 | 3.0 | 90 | 145500 | old_stop=90.0, old_tp=90.0 |
| 5 | `body_06_lattice_v2_seed_01_rank03_r2_l13_l1430_component_only` | survivor_seed_derivative | ok | -103427022.0 | 90.64 | -3.0 | 3.0 | 90 | 145500 | old_stop=90.0, old_tp=90.0 |
| 6 | `body_07_lattice_v2_neg_01_tick_prevday_active_0900_loss_shape` | negative_control | error | 0.0 | 0.0 | -2.0 | 1.0 | 30 | 91500 | old_stop=30.0, old_tp=30.0 |
| 7 | `body_08_lattice_v2_hold_04_holdout_rank03_r2_l13_l1430_default` | holdout_control | ok | -101728684.0 | 89.63 | -3.0 | 3.0 | 90 | 145500 | old_stop=90.0, old_tp=90.0 |

## Interpretation

- The prior threshold table was wrong for clause-level diagnosis because it captured hold-time or late-exit values as stop/take-profit thresholds.
- The replay-level decision remains unchanged: all OK rows lost money and exceeded the MDD cap; the only non-OK row produced no metrics.
- The branch failure is therefore not a simple reporting bug and not a gate-threshold-only failure.
