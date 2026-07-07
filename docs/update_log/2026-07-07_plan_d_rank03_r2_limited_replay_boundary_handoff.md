# 2026-07-07 Plan D Rank03 R2 Limited Replay Boundary Handoff

## 1. 실행 범위

계획: `.omo/plans/lattice-rereview-rank03-r2-boundary-20260707.md`

이번 실행은 rank03 R2 한 사이클만 진행했다. 목적은 Plan D를 무제한 계속하지 않고, rank03 R1 OOS survivor에서 의미 있는 추가 개선이 있는지 제한 실험으로 확인하는 것이었다.

실행하지 않은 것:
- OOS
- portfolio
- export/live/final promotion
- full tick 288
- full min 288
- DB UPDATE/DELETE

## 2. 원문 재확인과 부모 freeze

Read-first 원문 전체를 EOF까지 다시 읽고 source receipt를 기록했다.

- source receipt: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_source_read_receipt_20260707.json`
- parent freeze check: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_active_parent_freeze_check_20260707.json`
- parent freeze ledger: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_active_parent_freeze_ledger_20260707.jsonl`

부모는 `plan_d_rank03_r1_oos_20260707_01`로 고정했다. DB의 buy/sell SHA가 survivor 결과와 일치했다.

| 항목 | 값 |
|---|---|
| parent condition | `plan_d_r1_rank03_r1_08_parent_buy_default_tp3_sl3_hold90` |
| parent buy | `LAT_plan_d_r1_rank03_r1_08_parent_buy_default_tp3_sl3_hold90_B` |
| parent sell | `LAT_plan_d_r1_rank03_r1_08_parent_buy_default_tp3_sl3_hold90_S` |
| parent preflight profit | 1,652,322 |
| parent preflight MDD | 15.79 |
| parent preflight trades | 181 |
| parent preflight daily | 0.8 |
| selected OOS-style profit | 931,411 |
| selected OOS-style MDD | 6.14 |

## 3. R2 후보와 DB 등록

R2 후보 8개를 생성했고 static gate는 8/8 통과했다.

- design: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_design_20260707.json`
- seeds: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_generate8_seeds_20260707.json`
- static gate: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_static_gate_20260707.json`

DB 등록은 dry-run 후 INSERT-only로 진행했다.

| 항목 | 결과 |
|---|---|
| dry-run | `dry_run_ok`, conflicts 0 |
| INSERT-only apply | inserted 8 seeds / 16 rows |
| backup | `ai_strategy_loop\state\loop_strategies.db.bak.lattice_20260707T121133Z` |
| DB SHA check | 16/16 match |

## 4. 공식 limited replay 결과

run_id: `lat_plan_d_rank03_r2_8_min_warm64_20260707`

프로파일:
- lane: `min`
- DB: `_database/stock_min_back.db`
- 기간: `2025-04-07~2026-02-27`
- 시간: min full session, `09:00~15:19`
- engine: `warm64`
- pairs: 8

warm prepare는 `status=ok`, `back_count=1379`, `elapsed=119s`였다.

결과 파일:
- result: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_limited_replay_result_20260707.json`
- round decision: `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_round_decision_20260707.json`

요약:

| 항목 | 값 |
|---|---:|
| honest rows | 8 |
| status ok | 8 |
| gate passed | 8 |
| improved | 1 |
| hold | 3 |
| flat | 1 |
| no_go | 3 |

상세:

| 후보 | 판정 | profit | MDD | trades | daily | 핵심 해석 |
|---|---|---:|---:|---:|---:|---|
| R2-01 amount9000 default | hold | 1,605,526 | 15.79 | 184 | 0.9 | 부모와 거의 유사, coverage 소폭 증가 |
| R2-02 rate75 default | hold | 1,609,094 | 15.77 | 186 | 0.9 | 부모와 거의 유사, MDD 소폭 개선 |
| R2-03 end1500 default | hold | 1,735,804 | 16.72 | 222 | 1.0 | profit/coverage 증가, MDD 악화 |
| R2-04 L14+L1430 default | flat | 1,457,092 | 19.64 | 259 | 1.2 | coverage 증가가 손익/MDD 악화로 상쇄 |
| R2-05 L13+L1430 default | improved | 1,912,728 | 10.79 | 439 | 2.1 | profit, MDD, coverage 모두 개선 |
| R2-06 SL2.5 | no_go | 1,300,942 | 26.00 | 182 | 0.9 | stop-loss 조임이 MDD/손익 모두 악화 |
| R2-07 hold60 | no_go | 1,318,354 | 33.04 | 184 | 0.9 | 보유시간 단축이 MDD 위험 증가 |
| R2-08 loose TP4 control | no_go | 874,241 | 17.04 | 179 | 0.8 | 원래 loose sell 수준으로 회귀 |

## 5. 판단

성과는 있다. R2-05는 단순 gate 통과가 아니라 부모 대비 다음을 동시에 만족했다.

- profit: `+260,406`
- MDD: `-5.00`
- trades: `+258`
- daily_avg_trades: `+1.3`

따라서 Plan D를 즉시 중단할 근거는 아니다. 다만 무제한 계속할 근거도 아니다. 다음은 R2-05 1개만 selected OOS-style robustness replay로 확인하고, 실패하면 Plan D를 멈추고 lattice/condition-generation 설계 재검토로 전환하는 것이 맞다.

## 6. 다음 추천 명령

```text
$start-work .omo/plans/lattice-rereview-rank03-r2-boundary-20260707.md

범위는 rank03-r2-selected-oos-prereg-no-portfolio-export까지만 진행한다.
목표는 R2 improved 후보 1개
`plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90`만
freeze/preregistration 확정 후 공식 OOS-style robustness replay로 검증하고,
Plan D 지속/중단 여부를 판단하는 것이다.

반드시 먼저 읽을 문서:
- docs/update_log/2026-07-07_plan_d_rank03_r2_limited_replay_boundary_handoff.md
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_limited_replay_result_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_round_decision_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_selected_freeze_ledger_20260707.jsonl
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_e_r2_boundary_20260707/plan_d_rank03_r2_selected_oos_preregistration_draft_20260707.md

진행:
1. selected R2-05의 buy/sell SHA와 DB mapping을 다시 확인한다.
2. preregistration을 확정한다.
3. selected 1개만 공식 min warm64 OOS-style replay로 실행한다.
4. 결과를 survivor/hold/no_go로 분류한다.
5. survivor가 있으면 append-only survivor/seed_pool 기록 가능 여부만 판단한다.
6. survivor가 없으면 Plan D를 중단하고 lattice/condition-generation redesign handoff를 작성한다.
7. R3, portfolio, export/live/final은 실행하지 않는다.

금지:
- selected 1개 외 OOS 실행 금지
- portfolio 산출 금지
- export/live/final promotion 금지
- full tick 288 실행 금지
- full min 288 실행 금지
- DB UPDATE/DELETE 금지
- git add -A 금지
- dashboard 7파일, .gjc, unrelated .omo 잔재 스테이징 금지
```

## 7. 운영 주의

기존 dirty worktree에는 dashboard 7파일, `.gjc`, unrelated `.omo` 잔재가 있다. 이번 scope 파일만 명시 스테이징해야 하며 `git add -A`는 사용하지 않는다.
