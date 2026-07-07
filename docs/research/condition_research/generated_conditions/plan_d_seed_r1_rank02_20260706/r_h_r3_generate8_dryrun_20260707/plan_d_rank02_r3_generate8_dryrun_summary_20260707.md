# Plan D rank02 R3 generate8 dry-run summary

- created_at: 2026-07-07T15:39:17+09:00
- scope: `plan-d-rank02-r3-generate8-dryrun-no-portfolio-export`
- active seed: `plan_d_rank02_r2_oos_20260707_01`
- profit comparator: `plan_d_rank02_r2_oos_20260707_03`
- candidates: 8
- static gate: 8/8
- register dry-run planned inserts: 16
- register dry-run inserted rows: 0
- conflicts: 0

| condition_id | quota | axis |
|---|---|---|
| `plan_d_r1_rank02_r3_01_amt8000_default_tp3_sl3_hold90` | repair | `amt8000_default_tp3_sl3_hold90` |
| `plan_d_r1_rank02_r3_02_amt8000_tight_tp3_sl2p5_hold90` | repair | `amt8000_tight_tp3_sl2p5_hold90` |
| `plan_d_r1_rank02_r3_03_active_buy_hold60_tp3_sl3` | repair | `active_buy_default_hold60` |
| `plan_d_r1_rank02_r3_04_active_buy_tp2p5_sl2p5_hold90` | discovery | `active_buy_tp2p5_sl2p5_hold90` |
| `plan_d_r1_rank02_r3_05_active_buy_tp3_sl2p5_hold60` | discovery | `active_buy_tp3_sl2p5_hold60` |
| `plan_d_r1_rank02_r3_06_amt8500_default_tp3_sl3_hold90` | repair | `amt8500_default_tp3_sl3_hold90` |
| `plan_d_r1_rank02_r3_07_l1430_bridge_default_tp3_sl3` | discovery | `l1430_bridge_default_tp3_sl3` |
| `plan_d_r1_rank02_r3_08_l13_l14_default_tp3_sl3` | discovery | `l13_l14_default_tp3_sl3` |

## Decision

- Next page is open for INSERT-only apply plus official min full-period warm64 limited replay for these 8 candidates only.
- OOS, portfolio, export/live/final remain closed.
