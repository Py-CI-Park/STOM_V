# Plan D rank02 R6 limited replay summary

- run_id: `lat_plan_d_rank02_r6_8_min_warm64_20260707`
- profile: official min full-period warm64
- warm prepare: ok / back_count 1379 / elapsed 110s
- honest rows: 8/8
- gate_passed: 8/8
- decision: improved 0 / flat 8 / no_go 0
- best profit: `plan_d_r1_rank02_r6_05_eod1515_morning_amt1500_2800` 2,015,053 / MDD 15.71
- active R3 baseline: `plan_d_r1_rank02_r3_01_amt8000_default_tp3_sl3_hold90` 2,297,191 / MDD 16.31
- OOS: not opened
- Plan D branch decision: freeze rank02 R3 branch; move to next seed intake or terminal Plan D summary.
- DB registration: INSERT-only rows verified; a later idempotency retry left the current register report as `collision_abort`, but preapply/postapply/sha checks prove replay-readiness.
