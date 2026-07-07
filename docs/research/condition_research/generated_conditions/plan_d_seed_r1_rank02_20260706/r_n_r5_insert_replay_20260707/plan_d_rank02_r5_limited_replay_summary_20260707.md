# Plan D rank02 R5 limited replay summary

## Scope
- scope: `plan-d-rank02-r5-insert-limited-replay-no-oos-portfolio-export`
- run_id: `lat_plan_d_rank02_r5_8_min_warm64_20260707`
- lane/profile: min official full-period warm64
- OOS/portfolio/export/live/final: not executed

## Result
| metric | value |
|---|---:|
| honest rows | 8/8 |
| status ok | 8 |
| gate passed | 7/8 |
| improved | 0 |
| flat | 7 |
| no_go | 1 |
| best profit | plan_d_r1_rank02_r5_08_eod1515_default / 2,071,786 |
| best MDD | plan_d_r1_rank02_r5_08_eod1515_default / 15.92 |

## Candidate Decisions
| candidate | decision | profit | mdd | trades | delta profit | delta mdd |
|---|---|---:|---:|---:|---:|---:|
| `plan_d_r1_rank02_r5_01_l14_rate_floor7_default` | flat | 1,209,894 | 19.76 | 237 | -1,087,297 | 3.45 |
| `plan_d_r1_rank02_r5_02_l14_rate_floor10_default` | flat | 1,817,290 | 16.23 | 177 | -479,901 | -0.08 |
| `plan_d_r1_rank02_r5_03_pmax_strength_relax_default` | flat | 383,535 | 23.47 | 236 | -1,913,656 | 7.16 |
| `plan_d_r1_rank02_r5_04_pmax_strength_tight_default` | flat | 573,350 | 21.30 | 195 | -1,723,841 | 4.99 |
| `plan_d_r1_rank02_r5_05_openpos_floor992_default` | flat | 1,319,086 | 16.61 | 216 | -978,105 | 0.30 |
| `plan_d_r1_rank02_r5_06_openpos_floor996_default` | flat | 1,504,074 | 17.13 | 196 | -793,117 | 0.82 |
| `plan_d_r1_rank02_r5_07_morning_amt1000_3500_default` | no_go | -812,381 | 33.01 | 252 | -3,109,572 | 16.70 |
| `plan_d_r1_rank02_r5_08_eod1515_default` | flat | 2,071,786 | 15.92 | 209 | -225,405 | -0.39 |

## Judgment
- R5 produced clean process evidence, but no candidate improved over the active R3 full-period baseline.
- Selected OOS is not opened from R5.
- `rounds_no_improve_delta=2`; the next decision is either one final R6 dry-run based on the R5 watch axis, or terminal review of the rank02 branch before moving to another seed.
