# Plan D rank03 R1 selected OOS retry03 result

- run_id: `lat_plan_d_rank03_r1_selected1_oos_min_warm64_retry03_20260707`
- profile: official min OOS-style warm64, 2026-01-01 to 2026-02-27, 09:00 to 15:19
- warm prepare: ok, back_count 480, elapsed 106s
- honest rows: 1/1
- decision: survivor

| label | profit | MDD | trades | daily | gate | decision |
|---|---:|---:|---:|---:|---:|---|
| `plan_d_r1_rank03_r1_08_parent_buy_default_tp3_sl3_hold90` | 931,411 | 6.14 | 20 | 0.50 | True | survivor |

The previous three rank03 selected OOS attempts are preserved as stale prepare evidence. Retry03 was not a new candidate search; it was the same preregistered selected 1 under the same official min warm64 OOS-style profile. The successful retry was preceded by cleanup of 18 stale multiprocessing-fork children.
