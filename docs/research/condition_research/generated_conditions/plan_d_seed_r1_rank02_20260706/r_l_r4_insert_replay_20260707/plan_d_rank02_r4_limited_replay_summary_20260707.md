# Plan D rank02 R4 limited replay summary

## Scope
- scope: `plan-d-rank02-r4-insert-limited-replay-no-oos-portfolio-export`
- run_id: `lat_plan_d_rank02_r4_8_min_warm64_20260707`
- lane/profile: min official full-period warm64
- OOS/portfolio/export/live/final: not executed

## Result
| metric | value |
|---|---:|
| honest rows | 8/8 |
| status ok | 8 |
| gate passed | 8/8 |
| improved | 0 |
| flat | 8 |
| no_go | 0 |
| best profit | plan_d_r1_rank02_r4_02_amt8500_default_tp3_sl3_hold90 / 2,165,123 |
| best MDD | plan_d_r1_rank02_r4_08_l13_l14_default_tp3_sl3 / 13.59 |

## Candidate Decisions
| candidate | decision | profit | mdd | trades | delta profit | delta mdd |
|---|---|---:|---:|---:|---:|---:|
| `plan_d_r1_rank02_r4_01_amt7500_default_tp3_sl3_hold90` | flat | 1,992,815 | 17.42 | 214 | -304,376 | 1.11 |
| `plan_d_r1_rank02_r4_02_amt8500_default_tp3_sl3_hold90` | flat | 2,165,123 | 16.31 | 208 | -132,068 | 0.00 |
| `plan_d_r1_rank02_r4_03_amt8000_default_tp3_sl3_hold60` | flat | 1,967,856 | 19.22 | 212 | -329,335 | 2.91 |
| `plan_d_r1_rank02_r4_04_amt8000_tight_sl2p5_hold90` | flat | 1,459,465 | 13.79 | 210 | -837,726 | -2.52 |
| `plan_d_r1_rank02_r4_05_amt8000_take_tp2p5_hold90` | flat | 1,121,530 | 15.75 | 212 | -1,175,661 | -0.56 |
| `plan_d_r1_rank02_r4_06_amt8000_take_tp4_hold90` | flat | 1,465,137 | 18.56 | 207 | -832,054 | 2.25 |
| `plan_d_r1_rank02_r4_07_l1430_bridge_default_tp3_sl3` | flat | 1,478,669 | 17.51 | 260 | -818,522 | 1.20 |
| `plan_d_r1_rank02_r4_08_l13_l14_default_tp3_sl3` | flat | 1,509,737 | 13.59 | 446 | -787,454 | -2.72 |

## Judgment
- R4 produced clean process evidence, but no candidate improved over the active R3 full-period baseline.
- Selected OOS is not opened from R4.
- `rounds_no_improve_delta=1`; active seed can continue to R5 dry-run under Plan D, avoiding the non-improving R4 axes.
