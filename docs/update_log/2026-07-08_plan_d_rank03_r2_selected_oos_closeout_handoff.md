# 2026-07-08 Plan D Rank03 R2 Selected OOS Closeout Handoff

작성시각: 2026-07-07 22:32 KST

## 1. 이번 범위

Plan: `.omo/plans/lattice-rereview-rank03-r2-boundary-20260707.md`

이번 범위는 Plan D rank03 R2 selected 후보 1개만 OOS-style robustness replay로 확인하고, 전체 조건식 연구 결과를 정리하는 것이었다.

금지 범위는 유지했다.

- lattice 재설계 실행 안 함
- R3 자동 진행 안 함
- selected 1개 외 OOS 안 함
- full tick 288 / full min 288 안 함
- portfolio 산출 안 함
- export/live/final promotion 안 함
- DB UPDATE/DELETE 안 함

## 2. Read-First

원문은 full document로 읽고 receipt를 남겼다.

- `.omo/ulw-loop/evidence/20260708_rank03_r2_closeout_loop_v2/source_read_receipt.json`
- `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_selected_oos_source_read_receipt_20260708.json`

## 3. Selected Candidate

| item | value |
|---|---|
| label | `plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90` |
| buy | `LAT_plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90_B` |
| sell | `LAT_plan_d_r1_rank03_r2_05_l13_l1430_default_tp3_sl3_hold90_S` |
| buy_sha256 | `162391fa9848410b0771df5e558ba7af6014eb1a3a0c1ef521ecf80aaa559518` |
| sell_sha256 | `5c02facbbb42d2072a699f054a86d79f31695ef5fc0fbdd9e1d902fb7be83271` |
| DB SHA match | true |

Freeze recheck:

- `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_selected_freeze_recheck_20260708.json`

## 4. Preregistration

확정 preregistration:

- `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_selected_oos_preregistration_20260708.md`

실행 pair/config:

- `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/pairs_plan_d_rank03_r2_selected1_oos_20260708.json`
- `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/oos_config_min_plan_d_rank03_r2_selected1_20260708.json`

config는 기존 R2 selected OOS config의 실행 필드를 유지하되, stale R1 설명 메타데이터를 R2-05용으로 정정한 copy다.

## 5. OOS-Style Result

run_id: `lat_plan_d_rank03_r2_selected1_oos_min_warm64_20260708`

Runtime:

- lane: min
- DB: `_database/stock_min_back.db`
- window: 2026-01-01~2026-02-27
- time: 09:00~15:19
- engine: warm64
- pairs: 1

Warm prepare:

- status: ok
- back_count: 480
- elapsed: 161s

Result:

| metric | value |
|---|---:|
| status | ok |
| gate_passed | true |
| profit | 554,624 |
| MDD | 5.24 |
| trades | 80 |
| daily_avg_trades | 2.20 |
| payoff_ratio | 1.1231 |
| score | 1.5294 |
| classification | survivor |

Result file:

- `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_selected_oos_result_20260708.json`

Transcript:

- `.omo/ulw-loop/evidence/20260708_rank03_r2_closeout_loop_v2/C001_r2_05_oos_transcript.txt`

## 6. Survivor Append

R2-05가 preregistered survivor rule을 충족했으므로 append-only 기록을 남겼다.

| target | appended |
|---|---|
| local survivors | `plan_d_rank03_r2_oos_20260708_01` |
| global oos_survivors | `plan_d_rank03_r2_oos_20260708_01` |
| seed_pool | `plan_d_rank03_r2_oos_20260708_01` |
| passport | `docs/research/condition_research/generated_conditions/plan_d_seed_pool_20260706/passports/plan_d_rank03_r2_oos_20260708_01.md` |

Append receipt:

- `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_oos_survivor_append_receipt_20260708.json`

Boundary receipt:

- `.omo/ulw-loop/evidence/20260708_rank03_r2_closeout_loop_v2/C002_boundary_receipt.json`
- `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_boundary_receipt_20260708.json`

## 7. 전체 연구 정리

전체 연구 분석 문서:

- `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md`

핵심 결론:

- 576 lattice는 공식 warm64 전체기간에서 survivor 0이다.
- 실패는 engine/profile 문제가 아니라 조건식 구조 문제다.
- gate가 과도해서 전부 탈락한 것이 아니라, tick은 전부 손실이고 min은 positive/MDD/daily 교집합이 0이었다.
- repair composite 방식은 효과가 있었고 selected 16 OOS-style 중 survivor 15를 만들었다.
- Plan D는 의미가 있었지만 unlimited loop로 계속 열면 과최적화 위험이 커진다.
- rank03 R2-05는 survivor seed로 기록하되 R3 자동 진행은 금지한다.

## 8. 다음 판단

Plan D는 “종결 가능한 상태”까지 왔다.

추천:

1. 지금 커밋 이후 PR 점검으로 마무리한다.
2. 다음 연구는 R3 자동 진행이 아니라 lattice/condition-generation 재설계 계획부터 시작한다.
3. 재설계 전에는 portfolio/export/live/final promotion을 열지 않는다.
4. 새 연구는 fully blind split 또는 walk-forward 평가 경계부터 정의한다.

## 9. 다음 추천 명령어

```text
$ulw-plan

목표는 기존 576 lattice와 Plan D seed 연구 결과를 입력으로,
lattice/condition-generation v2 재설계 계획을 수립하는 것이다.

반드시 먼저 읽을 문서:
- docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md
- docs/update_log/2026-07-08_plan_d_rank03_r2_selected_oos_closeout_handoff.md
- docs/research/condition_research/research_runs/seed_lattice_20260702/repair_overnight_20260705/overnight_no_d_576_deep_analysis_20260705.json
- docs/research/condition_research/generated_conditions/seed_pool.jsonl

목표:
1. 576 lattice 구조에서 버릴 축과 유지할 축을 정리한다.
2. min/composite/coverage 중심 generation v2 후보군을 설계한다.
3. fully blind 또는 walk-forward 검증 경계를 먼저 설계한다.
4. Plan D survivor seed를 promotion이 아니라 설계 입력으로만 사용한다.
5. 실행 명령어는 아직 만들지 말고 계획서만 작성한다.
```

## 10. 운영 주의

- 기존 dashboard 7파일, `.gjc`, unrelated `.omo` 잔재는 이번 커밋에 포함하지 않는다.
- `git add -A`를 사용하지 않는다.
- ignored runtime DB/CSV는 evidence로만 남기고 stage하지 않는다.
- R2-05 survivor는 research lane only이며 portfolio_ready=false다.
