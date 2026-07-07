# 2026-07-07 Plan D rank02 R5 INSERT + limited replay handoff

## 1. Scope

- Scope: `plan-d-rank02-r5-insert-limited-replay-no-oos-portfolio-export`
- Active seed: `plan_d_rank02_r3_oos_20260707_01`
- Baseline comparator: `plan_d_r1_rank02_r3_01_amt8000_default_tp3_sl3_hold90`
- Purpose: R5 dry-run 8-slot candidates only were INSERT-only registered, then official min full-period warm64 limited replay was run for exactly 8 pairs.
- Not executed: OOS, portfolio, export/live/final promotion, full tick 288, full min 288.

## 2. Evidence Paths

| Item | Path |
|---|---|
| Preapply absence check | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_n_r5_insert_replay_20260707/plan_d_rank02_r5_preapply_absence_check_20260707.json` |
| Register apply report | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_n_r5_insert_replay_20260707/register_plan_d_rank02_r5_apply_20260707.json` |
| Postapply DB check | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_n_r5_insert_replay_20260707/plan_d_rank02_r5_postapply_db_check_20260707.json` |
| Pairs used | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_n_r5_insert_replay_20260707/pairs_plan_d_rank02_r5_8_inserted_20260707.json` |
| Replay result | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_n_r5_insert_replay_20260707/plan_d_rank02_r5_limited_replay_result_20260707.json` |
| Round decision | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_n_r5_insert_replay_20260707/plan_d_rank02_r5_round_decision_20260707.json` |
| Empty selected OOS draft | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_n_r5_insert_replay_20260707/pairs_plan_d_rank02_r5_selected_oos_draft_20260707.json` |
| Replay raw log | `artifacts/plan_d_rank02_r5_8_min_warm64_20260707.log` |

## 3. INSERT-only Result

| Metric | Value |
|---|---:|
| planned_seed_count | 8 |
| planned_insert_count | 16 |
| inserted_seed_count | 8 |
| inserted_row_count | 16 |
| conflicts | 0 |
| DB UPDATE/DELETE | no |

DB backup was created by the registration tool and is runtime evidence, not selected for commit staging.

## 4. Limited Replay Result

| Metric | Value |
|---|---:|
| run_id | `lat_plan_d_rank02_r5_8_min_warm64_20260707` |
| warm prepare | unknown |
| back_count | None |
| elapsed prepare seconds | None |
| honest rows | 8/8 |
| status_counts | ok 8 |
| gate_passed | 7/8 |
| improved | 0 |
| flat | 7 |
| no_go | 1 |

## 5. Candidate Decision

| Decision | Candidate | Key Metrics |
|---|---|---|
| best profit, flat | `plan_d_r1_rank02_r5_08_eod1515_default` | profit 2,071,786 / MDD 15.92 / trades 209 |
| no_go | `plan_d_r1_rank02_r5_07_morning_amt1000_3500_default` | profit -812,381 / MDD 33.01 / trades 252 |
| watch | `plan_d_r1_rank02_r5_08_eod1515_default` | closest to baseline, but still below active R3 profit |

No R5 candidate improved over the active R3 full-period baseline (`2,297,191` profit / `16.31` MDD). Therefore selected OOS remains closed for this round, and `rounds_no_improve_delta=2` is recorded.

## 6. Next Page

Recommended next action is not OOS. Choose one of these bounded paths:

1. `rank02-r6-generate8-dryrun-no-oos-portfolio-export`: one final dry-run around the R5 watch axis (`eod1515`) combined with conservative buy-side filters.
2. `rank02-branch-terminal-review`: stop rank02 mutation rounds after two no-improve replays and move Plan D intake to the next seed.

Do not run OOS, portfolio, export/live/final, or more than the bounded dry-run/replay scope unless a later page explicitly opens it.
