# 2026-07-07 Plan D rank02 R3 INSERT + limited replay handoff

## 1. Scope

- Scope: `plan-d-rank02-r3-insert-limited-replay-no-oos-portfolio-export`
- Active seed: `plan_d_rank02_r2_oos_20260707_01`
- Baseline comparator: `plan_d_r1_rank02_r2_06_active_buy_default_tp3_sl3_hold90`
- Purpose: R3 dry-run 8-slot candidates only were INSERT-only registered, then official min full-period warm64 limited replay was run for exactly 8 pairs.
- Not executed: OOS, portfolio, export/live/final promotion, full tick 288, full min 288.

## 2. Evidence Paths

| Item | Path |
|---|---|
| Register apply report | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/register_plan_d_rank02_r3_apply_20260707.json` |
| Pairs used | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/pairs_plan_d_rank02_r3_8_inserted_20260707.json` |
| Replay result | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/plan_d_rank02_r3_limited_replay_result_20260707.json` |
| Round decision | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/plan_d_rank02_r3_round_decision_20260707.json` |
| Selected OOS pairs draft | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/pairs_plan_d_rank02_r3_selected_oos_draft_20260707.json` |
| Selected freeze ledger draft | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/plan_d_rank02_r3_selected_freeze_ledger_draft_20260707.jsonl` |
| OOS preregistration draft | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/plan_d_rank02_r3_selected_oos_preregistration_draft_20260707.md` |
| Replay raw log | `artifacts/plan_d_rank02_r3_8_min_warm64_20260707.log` |

## 3. INSERT-only Result

| Metric | Value |
|---|---:|
| planned_seed_count | 8 |
| planned_insert_count | 16 |
| inserted_seed_count | 8 |
| inserted_row_count | 16 |
| conflicts | 0 |
| unsafe target names | 0 |
| DB UPDATE/DELETE | no |

DB backup was created by the registration tool at `ai_strategy_loop/state/loop_strategies.db.bak.lattice_20260707T064322Z`. The backup is runtime evidence and was not selected for commit staging.

## 4. Limited Replay Result

| Metric | Value |
|---|---:|
| run_id | `lat_plan_d_rank02_r3_8_min_warm64_20260707` |
| lane | min |
| profile | official full-period warm64 |
| warm prepare | ok |
| back_count | 1379 |
| elapsed prepare seconds | 105 |
| honest rows | 8/8 |
| status_counts | ok 8 |
| gate_passed | 8/8 |
| improved | 1 |
| flat | 7 |
| no_go | 0 |

## 5. Candidate Decision

| Decision | Candidate | Key Metrics |
|---|---|---|
| improved, selected OOS draft | `plan_d_r1_rank02_r3_01_amt8000_default_tp3_sl3_hold90` | profit 2,297,191 / MDD 16.31 / trades 209 / daily 1.00 |
| coverage watch | `plan_d_r1_rank02_r3_08_l13_l14_default_tp3_sl3` | profit 1,509,737 / MDD 13.59 / trades 446 / daily 2.10 |

The selected candidate improved over the active R2 full-period baseline by +116,292 profit with equal MDD. The coverage-watch candidate reduced MDD and increased trade coverage, but profit remained below the active baseline, so it is not selected for OOS.

## 6. Next Page

Recommended next command:

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

범위는 plan-d-rank02-r3-selected-oos-prereg-no-portfolio-export까지만 진행한다.
목표는 R3 limited replay improved 후보 1개만 freeze/preregistration으로 확정하고,
공식 min OOS-style warm64 selected replay를 1쌍에 한정해 실행한 뒤
survivor/hold/no_go를 분류하고 Plan D 다음 라운드 또는 terminal 가능 여부만 판단하는 것이다.

반드시 먼저 읽을 문서:
- docs/update_log/2026-07-07_plan_d_rank02_r3_insert_replay_handoff.md
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/plan_d_rank02_r3_limited_replay_result_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/plan_d_rank02_r3_round_decision_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/plan_d_rank02_r3_selected_freeze_ledger_draft_20260707.jsonl
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/plan_d_rank02_r3_selected_oos_preregistration_draft_20260707.md
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_i_r3_insert_replay_20260707/pairs_plan_d_rank02_r3_selected_oos_draft_20260707.json

진행:
1. selected 1 freeze ledger와 buy/sell sha를 재확인한다.
2. OOS preregistration을 확정한다.
3. selected 1개만 공식 OOS-style min warm64 replay로 실행한다.
4. 결과를 survivor/hold/no_go로 분류한다.
5. survivor가 있으면 append-only로 oos_survivors/seed_pool에 기록하고 next seed readiness를 작성한다.
6. portfolio와 export/live/final promotion은 실행하지 않는다.
7. handoff와 다음 명령어를 작성하고 한글 커밋한다.

금지:
- selected 1 외 OOS 실행 금지
- preregistration 없는 OOS 실행 금지
- portfolio 산출 금지
- export/live/final promotion 금지
- DB UPDATE/DELETE 금지
- git add -A 금지
- dashboard 7파일, .gjc, unrelated .omo 잔재 스테이징 금지
```

## 7. Current Judgment

Continue to the next page. R3 produced one real improved candidate under official min full-period warm64 limited replay, and the candidate has a preregistration draft. The next page is meaningful because it tests whether the R3 improvement survives the fixed selected OOS-style replay boundary before any further Plan D round is opened.
