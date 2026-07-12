# Plan D rank02 R1 INSERT/replay handoff

## Scope

- Plan: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`
- Scope: `plan-d-rank02-r1-insert-replay-no-portfolio-export`
- Run ID: `lat_plan_d_rank02_r1_8_min_warm64_20260706`
- OOS/portfolio/export/live/final: not executed

## Result

| Item | Value |
|---|---:|
| DB inserted rows | 16 |
| replay honest rows | 8/8 |
| status ok | 8 |
| gate passed | 8 |
| improved | 2 |
| flat | 6 |
| no_go | 0 |

## Improved candidates

| Label | Profit | MDD | Trades | Daily | Reason |
|---|---:|---:|---:|---:|---|
| `plan_d_r1_rank02_r1_08_parent_buy_default_tp3_sl3_hold90` | 2216506 | 16.31 | 203 | 1.00 | best_profit_and_lower_mdd_vs_rank02_parent_preflight |
| `plan_d_r1_rank02_r1_02_l14_amt9000_rate80_hold90` | 1348845 | 18.56 | 204 | 1.00 | secondary_improved_confirmation_same_or_better_mdd |

## Evidence

- source receipt: `.omo/evidence/plan-d-rank02-r1-insert-limited-replay-no-portfolio-export-20260706/source_read_receipt.md`
- register apply: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_c_insert_replay_20260706/register_plan_d_rank02_r1_apply_20260706.json`
- preapply check: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_c_insert_replay_20260706/plan_d_rank02_r1_preapply_absence_check_20260706.json`
- postapply check: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_c_insert_replay_20260706/plan_d_rank02_r1_postapply_db_check_20260706.json`
- replay result: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_c_insert_replay_20260706/plan_d_rank02_r1_limited_replay_result_20260706.json`
- summary: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_c_insert_replay_20260706/plan_d_rank02_r1_limited_replay_summary_20260706.md`
- round decision: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_c_insert_replay_20260706/plan_d_rank02_r1_round_decision_20260706.json`
- raw log: `artifacts/plan_d_rank02_r1_8_min_warm64_20260706.log`

## Guardrails observed

| Guardrail | Result |
|---|---|
| DB UPDATE/DELETE | not used |
| INSERT-only | used; 16 rows inserted |
| pair cap | 8/8 only |
| OOS | not executed |
| portfolio/export/live/final | not executed |
| full tick/min 288 | not executed |

## Next command

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

Scope: plan-d-rank02-selected-oos-prereg-no-portfolio-export only.
Goal: freeze/preregister only the improved rank02 R1 limited-replay candidates,
then run selected OOS-style min warm64 replay and classify survivor/hold/no_go.

Forbidden: portfolio/export/live/final, DB UPDATE/DELETE,
OOS without preregistration, and OOS for candidates outside the selected set.
```
