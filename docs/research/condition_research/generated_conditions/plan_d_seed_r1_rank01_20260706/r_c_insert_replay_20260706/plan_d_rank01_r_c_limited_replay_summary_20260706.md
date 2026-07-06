# Plan D rank01 R-c limited replay summary

- created_at: 2026-07-06T16:07:03+09:00
- run_id: `lat_plan_d_r1_rank01_r_c_generate8_min_warm64_20260706`
- profile: official min full-period warm64
- scope: INSERT-only DB apply + 8-pair limited replay only
- forbidden actions observed: no OOS, no portfolio, no export/live/final, no UPDATE/DELETE, no extra pairs

## DB registration

- status: `inserted`
- inserted rows: 16 / planned 16
- backup: `ai_strategy_loop\state\loop_strategies.db.bak.lattice_20260706T065150Z`

## Replay result

- warm prepare: None / back_count=None / elapsed=Nones
- honest rows: 8/8
- status_counts: {'ok': 8}
- gate_passed: 8/8
- decision_counts: {'flat': 7, 'improved': 1}

## Candidate table

| gen | label | decision | profit | MDD | trades | daily | parent profit delta | parent MDD delta |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 0 | plan_d_r1_rank01_01_repair_strength_plus1_default | flat | 1590104 | 21.83 | 198 | 0.90 | -297067 | 2.58 |
| 1 | plan_d_r1_rank01_02_repair_momentum_wider_default | flat | 1135665 | 20.57 | 213 | 1.00 | -751506 | 1.32 |
| 2 | plan_d_r1_rank01_03_repair_l14_liquidity_relaxed_default | flat | 764267 | 23.05 | 237 | 1.10 | -1122904 | 3.80 |
| 3 | plan_d_r1_rank01_04_repair_l14_liquidity_tight_default | improved | 2153579 | 18.69 | 201 | 0.90 | 266408 | -0.56 |
| 4 | plan_d_r1_rank01_05_repair_exit_protect_tp28_sl25_hold60 | flat | 1049194 | 16.74 | 209 | 1.00 | -837977 | -2.51 |
| 5 | plan_d_r1_rank01_06_discovery_adjacent_l13_l14_coverage | flat | 1059257 | 18.49 | 448 | 2.10 | -827914 | -0.76 |
| 6 | plan_d_r1_rank01_07_discovery_adjacent_l14_l1430_extension | flat | 1123124 | 22.58 | 262 | 1.20 | -764047 | 3.33 |
| 7 | plan_d_r1_rank01_08_discovery_balanced_l14_tight_exit | flat | 751652 | 18.99 | 198 | 0.90 | -1135519 | -0.26 |

## R-d decision

- R-d decision possible: `True`
- recommended active seed: `plan_d_r1_rank01_04_repair_l14_liquidity_tight_default`
- reason: ?? rank01?? profit? ?? MDD? ??? ??? ?????.
- coverage watch: `plan_d_r1_rank01_06_discovery_adjacent_l13_l14_coverage`? ???/??? ??? ?? ???? profit? ?? ?? ?? ???? ???.
