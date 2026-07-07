# 2026-07-07 Plan D rank02 R2 generate8 dry-run handoff

## 1. 목적

rank02 R1 selected OOS retry02에서 survivor가 된 `plan_d_rank02_r1_oos_20260707_02`를 active seed 후보로 잡고, 다음 Plan D round 후보 8개를 설계했다.

이번 범위는 후보 생성, static gate, DB registration dry-run까지만 수행했다. 공식 replay, OOS, portfolio, export/live/final promotion, DB INSERT apply는 실행하지 않았다.

## 2. 입력

| 항목 | 값 |
|---|---|
| active seed | `plan_d_rank02_r1_oos_20260707_02` |
| active condition | `plan_d_r1_rank02_r1_02_l14_amt9000_rate80_hold90` |
| comparator | `plan_d_rank02_r1_oos_20260707_01` |
| source OOS run | `lat_plan_d_rank02_r1_selected2_oos_min_warm64_retry02_20260707` |
| OOS frame | min, 2026-01-01~2026-02-27, warm64 |

Active seed 성과:

| profit | MDD | trades | daily | gate |
|---:|---:|---:|---:|---|
| 1,124,220 | 4.12 | 18 | 0.50 | true |

## 3. 생성 후보

| slot | condition_id | quota | 의도 |
|---:|---|---|---|
| 1 | `plan_d_r1_rank02_r2_01_l14_amt8000_rate80_hold90` | repair | L14 amount floor 9000 -> 8000 |
| 2 | `plan_d_r1_rank02_r2_02_l14_amt9000_rate75_hold90` | repair | L14 rate floor 8.0 -> 7.5 |
| 3 | `plan_d_r1_rank02_r2_03_l14_end1445_amt9000_rate80_hold90` | repair | L14 window 14:00~14:30 -> 14:00~14:45 |
| 4 | `plan_d_r1_rank02_r2_04_l13_l14_amt9000_rate80_hold90` | repair | L13 bridge component 추가 |
| 5 | `plan_d_r1_rank02_r2_05_l1430_bridge_amt9000_rate80_hold90` | repair | 14:30~14:45 bridge component 추가 |
| 6 | `plan_d_r1_rank02_r2_06_active_buy_default_tp3_sl3_hold90` | discovery | active buy + TP3/SL3/hold90 |
| 7 | `plan_d_r1_rank02_r2_07_active_buy_tight_tp3_sl2p5_hold90` | discovery | active buy + TP3/SL2.5/hold90 |
| 8 | `plan_d_r1_rank02_r2_08_active_buy_loose_hold60_tp4_sl3` | discovery | active buy + TP4/SL3/hold60 |

Static gate:

- candidate_count: 8
- passed_count: 8
- failed_count: 0

DB registration dry-run:

- status: `dry_run_ok`
- planned_seed_count: 8
- planned_insert_count: 16
- inserted_row_count: 0
- conflicts: 0
- unsafe target names: 0

## 4. 산출물

| 구분 | 경로 |
|---|---|
| source receipt | `.omo/evidence/plan-d-rank02-r1-survivor-next-round-generate8-dryrun-no-portfolio-export-20260707/source_read_receipt.md` |
| seed JSON | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/plan_d_rank02_r2_generate8_seeds_20260707.json` |
| design JSON | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/plan_d_rank02_r2_design_20260707.json` |
| static gate | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/plan_d_rank02_r2_static_gate_20260707.json` |
| registration dry-run | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/register_plan_d_rank02_r2_generate8_dryrun_20260707.json` |
| pairs | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/pairs_plan_d_rank02_r2_generate8_20260707.json` |
| pairs_min | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/pairs_min.json` |
| mapping ledger | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/plan_d_rank02_r2_strategy_name_mapping_20260707.jsonl` |
| summary | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/plan_d_rank02_r2_generate8_dryrun_summary_20260707.json` |
| verification | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/plan_d_rank02_r2_generate8_dryrun_verification_receipt_20260707.json` |

## 5. 현재 판단

다음 페이지는 열 수 있다. dry-run이 clean이므로 다음 범위에서는 이 8개만 INSERT-only apply 후, 공식 min 전체기간 warm64 limited replay 8쌍을 실행해 R-d round decision을 판단한다.

아직 열면 안 되는 것:

- OOS
- portfolio
- export/live/final promotion
- 8쌍 초과 replay
- DB UPDATE/DELETE

## 6. 다음 추천 명령어

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

범위는 plan-d-rank02-r2-insert-limited-replay-no-oos-portfolio-export까지만 진행한다.
목표는 rank02 R2 dry-run 통과 8개 후보만 INSERT-only로 등록하고,
공식 min 전체기간 warm64 limited replay를 8쌍에 한정해 실행한 뒤
R-d round decision과 selected OOS 개방 가능 여부만 판단하는 것이다.

반드시 먼저 읽을 문서:
- docs/update_log/2026-07-07_plan_d_rank02_r2_generate8_dryrun_handoff.md
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/plan_d_rank02_r2_generate8_dryrun_summary_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/plan_d_rank02_r2_generate8_seeds_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/register_plan_d_rank02_r2_generate8_dryrun_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_e_survivor_next_generate8_dryrun_20260707/pairs_plan_d_rank02_r2_generate8_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_d_selected_oos_20260707/plan_d_rank02_r1_selected_oos_retry02_result_20260707.json

진행:
1. dry-run receipt와 static gate 8/8 pass를 재확인한다.
2. DB 등록 전 충돌 여부를 다시 확인한다.
3. 위 8개 후보만 INSERT-only apply로 등록한다.
4. 새 run_id로 공식 min 전체기간 warm64 limited replay 8쌍만 실행한다.
5. 결과를 improved/flat/no_go로 분류한다.
6. selected OOS 후보가 있으면 freeze/preregistration 초안까지만 작성한다.
7. OOS, portfolio, export/live/final promotion은 실행하지 않는다.
8. handoff와 다음 명령어를 작성하고 한글 커밋한다.

금지:
- OOS 실행 금지
- portfolio 산출 금지
- export/live/final promotion 금지
- 8쌍 초과 replay 금지
- DB UPDATE/DELETE 금지
- git add -A 금지
- A3/promotion/export/live/final 경로 수정 금지
- dashboard 7파일, .gjc, unrelated .omo 잔재 스테이징 금지
```
