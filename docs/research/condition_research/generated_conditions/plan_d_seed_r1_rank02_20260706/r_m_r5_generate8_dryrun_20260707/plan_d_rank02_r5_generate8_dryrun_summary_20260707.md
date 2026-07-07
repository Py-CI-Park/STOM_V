# Plan D rank02 R5 generate8 dry-run summary

## Scope
- scope: `plan-d-rank02-r5-generate8-dryrun-no-portfolio-export`
- active seed: `plan_d_rank02_r3_oos_20260707_01`
- boundary: static gate + DB registration dry-run only

## Result
| item | value |
|---|---:|
| candidates | 8 |
| static gate pass | 8 |
| static gate fail | 0 |
| registration planned inserts | 16 |
| inserted rows | 0 |
| conflicts | 0 |

## Candidate Axes
- `plan_d_r1_rank02_r5_01_l14_rate_floor7_default`: Relax L14 rate floor from 8.0 to 7.0 while keeping L14 amount 8000 and default sell.
- `plan_d_r1_rank02_r5_02_l14_rate_floor10_default`: Tighten L14 rate floor from 8.0 to 10.0 while keeping L14 amount 8000 and default sell.
- `plan_d_r1_rank02_r5_03_pmax_strength_relax_default`: Relax S09/S10 ???? thresholds 109/107 to 106/105.
- `plan_d_r1_rank02_r5_04_pmax_strength_tight_default`: Tighten S09/S10 ???? thresholds 109/107 to 111/109.
- `plan_d_r1_rank02_r5_05_openpos_floor992_default`: Relax M09/M10 price proximity from open*0.994 to open*0.992.
- `plan_d_r1_rank02_r5_06_openpos_floor996_default`: Tighten M09/M10 price proximity from open*0.994 to open*0.996.
- `plan_d_r1_rank02_r5_07_morning_amt1000_3500_default`: Widen morning amount band from 1500-3000 to 1000-3500 without changing L14 amount axis.
- `plan_d_r1_rank02_r5_08_eod1515_default`: Move hard time exit from 14:59 to 15:15 while leaving TP/SL/hold unchanged.

## Guardrails
- official replay executed: no
- OOS executed: no
- portfolio/export/live/final executed: no
- DB INSERT apply: no
- DB UPDATE/DELETE: no
