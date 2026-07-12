# Plan D rank02 R6 generate8 dry-run summary

## Scope
- scope: `plan-d-rank02-r6-generate8-dryrun-no-oos-portfolio-export`
- active seed: `plan_d_rank02_r3_oos_20260707_01`
- reason: R4/R5 are two consecutive no-improve replays after active R3.

## Result
| metric | value |
|---|---:|
| candidates | 8 |
| static gate passed | 8 |
| static gate failed | 0 |
| DB INSERT apply | no |
| official replay | no |
| OOS | no |
| portfolio/export/live/final | no |

## Candidate Axes
- `plan_d_r1_rank02_r6_01_eod1515_l14_rate9_default`: Keep eod1515 sell watch axis and tighten L14 rate floor from 8.0 to 9.0.\n- `plan_d_r1_rank02_r6_02_eod1515_l14_amt8500_rate9`: Keep eod1515 sell watch axis and combine conservative L14 amount 8500 with rate floor 9.0.\n- `plan_d_r1_rank02_r6_03_eod1515_pmax110_108`: Keep eod1515 sell watch axis and mildly tighten S09/S10 strength thresholds to 110/108.\n- `plan_d_r1_rank02_r6_04_eod1515_morning_amt1800_3000`: Keep eod1515 sell watch axis and narrow morning PMAX amount lower bound to 1800 while retaining upper 3000.\n- `plan_d_r1_rank02_r6_05_eod1515_morning_amt1500_2800`: Keep eod1515 sell watch axis and narrow morning PMAX amount upper bound from 3000 to 2800.\n- `plan_d_r1_rank02_r6_06_eod1515_openpos996_rate9`: Keep eod1515 sell watch axis and combine M09/M10 price proximity 0.996 with L14 rate floor 9.0.\n- `plan_d_r1_rank02_r6_07_eod1510_l14_rate9`: Test slightly earlier hard exit 15:10 with L14 rate floor 9.0 after eod1515 lowered MDD but missed profit.\n- `plan_d_r1_rank02_r6_08_eod1520_l14_rate10`: Test slightly later hard exit 15:20 with L14 rate floor 10.0 as final watch-axis extension.\n
## Judgment
- R6 is a dry-run-only terminal probe.
- If dry-run registration is clean, the next page may either run one final 8-pair limited replay or terminate rank02 and move to branch review.
