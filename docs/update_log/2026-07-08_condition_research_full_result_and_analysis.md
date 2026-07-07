# 2026-07-08 Condition Research Full Result And Analysis

작성시각: 2026-07-07 22:32 KST

이 문서는 2026-07-02 계획군에서 시작한 조건식 연구의 현재 종결 상태를 기록한다. 파일명은 다음 세션 기준 closeout 날짜인 2026-07-08을 따른다.

## 1. Executive Summary

공식 warm64 전체기간 기준으로 576 lattice는 strategy survivor를 만들지 못했다. 다만 실패 자체는 무의미하지 않았다. tick/min lane별로 어떤 축이 손실, MDD, 거래수 부족을 만드는지 분해했고, 그 결과 단일 lattice seed보다 coverage/composite 방식과 Plan D seed 연구가 더 적합하다는 결론을 얻었다.

최종적으로 repair composite OOS-style 검증에서 15개 survivor를 만들었고, Plan D seed 연구에서는 rank01/rank02/rank03 계열 survivor를 누적했다. 이번 closeout의 최신 결과는 rank03 R2-05 1개 selected OOS-style robustness replay이며, 결과는 `survivor`다.

| item | result |
|---|---:|
| R2-05 OOS-style profit | 554,624 |
| MDD | 5.24 |
| trades | 80 |
| daily_avg_trades | 2.20 |
| gate_passed | true |
| classification | survivor |

단, 이 결과는 fully blind OOS가 아니다. rank03 R2-05는 full-period min replay에서 고른 후보이고, 그 full-period에는 2026-01-01~2026-02-27 구간이 포함되어 있었다. 따라서 이 결과는 promotion 근거가 아니라 다음 연구에 남길 seed 근거다.

## 2. 전체 연구 타임라인

| phase | 목적 | 주요 산출물 | 결론 |
|---|---|---|---|
| Plan A | provider 안정화 | FailoverProvider, upper entrypoints, A3 승인 보류 기록 | 연구 loop 실행 안정성을 개선했고 promotion 관련 A3는 보류 |
| Plan C | DB 등재 CSS_V7 검증 | static gate, pair list, DB mirror, smoke/train/OOS/WF 검증 | DB 등재 조건식의 타당성 검증 경로를 마련 |
| Plan B/P5 | lattice 576 공식 warm64 전체기간 실행 | tick 288, min 288 export summary | 576/576 coverage는 확보했으나 survivor 0 |
| Plan B/P6 | coverage/gaps/go-no-go 정리 | `p6_lattice_go_no_go_hold_20260705.json` | go 0, hold 0, no_go 576 |
| Repair composite | daily 거래수 부족과 단일 seed 실패 보완 | composite preflight, expanded preflight, selected OOS-style | selected 16 중 survivor 15 |
| Plan D rank01 | survivor seed 기반 연구 | rank01 R2/R3 selected OOS | survivor 생성, 그러나 과최적화 caveat 유지 |
| Plan D rank02 | 다음 seed branch 연구 | rank02 R1/R2/R3/R4~R6 | R1/R2/R3 survivor 생성, 후속 라운드 효율 저하 |
| Plan D rank03 | rank03 boundary 연구 | R1 survivor, R2-05 selected OOS-style | R2-05 survivor 기록, R3 자동 진행 금지 |

## 3. Plan A/B/C/D 목적과 실행 결과

### Plan A

목적은 AI loop provider 경로를 안정화하고, 분석 후보 연결부가 끊기지 않도록 provider failover와 upper entrypoint를 보강하는 것이었다. A1/A2는 완료했고, A3 promotion-review는 사용자 승인 없이는 건드리지 않는 보류 상태로 남겼다.

효과:

- 연구 loop 실행 중 provider 단일 장애 위험을 낮췄다.
- export/live/final promotion 경로와 분리된 research lane 원칙을 유지했다.
- 이후 긴 batch 연구에서 provider 이슈와 조건식 성과 이슈를 분리할 수 있었다.

### Plan C

목적은 DB에 등재된 CSS_V7 및 조합 후보를 정적 gate와 protocol로 검증하는 것이었다. static gate, unique pair list, loop DB mirror INSERT-only 원칙을 적용했다.

결론:

- 조건식 실행 가능성 검증 체계를 만들었다.
- 단, Plan C 자체가 최종 survivor를 만드는 단계는 아니었고, Plan B/P5의 공식 warm64 전체기간 검증으로 넘어갈 준비 단계였다.

### Plan B

목적은 자동 생성 lattice 576개를 공식 backtest 조건에서 전수 검증하는 것이었다.

실행 범위:

- tick lattice 288개: `_database/stock_tick_back.db`, 2022-03-23~2026-02-27, warm64.
- min lattice 288개: `_database/stock_min_back.db`, 2025-04-07~2026-02-27, warm64.
- wrong-profile 8-engine/2025Q1 run은 공식 결과에서 제외했다.

결론:

- coverage는 576/576까지 확보했다.
- survivor는 0개였다.
- 이 결과는 backtest 엔진 실패가 아니라 조건식 구조 실패로 분류한다.

### Plan D

목적은 576 lattice 전수 결과가 survivor를 만들지 못한 뒤, composite OOS-style survivor를 seed_pool로 삼아 더 작고 통제된 seed 연구를 수행하는 것이었다.

결론:

- Plan D는 의미가 있었다. rank01/rank02/rank03에서 survivor seed를 만들었다.
- 하지만 unlimited loop로 계속 돌릴 단계는 아니다. fully blind OOS가 아니므로 promotion이 아니라 seed inventory와 구조 재설계 입력으로 봐야 한다.

## 4. Provider 안정화 성과

Provider 안정화의 핵심 성과는 연구 결과 해석에서 runtime 실패와 조건식 실패를 분리할 수 있게 만든 점이다. 이후 연구에서 warm64 prepare wait, stale/partial, wrong-profile 문제는 각각 별도 receipt로 남겼고, 공식 결과에는 DB 전체기간/warm64/profile이 맞는 실행만 반영했다.

## 5. CSS_V7 검증 결과

CSS_V7 검증은 DB 등재 후보가 실행 가능한 STOM 조건식인지, pair list와 loop DB mirror가 INSERT-only 원칙을 지키는지를 확인하는 준비 단계였다. 이 단계에서 얻은 가장 중요한 교훈은 “DB에 들어간 조건식”과 “수익 survivor 조건식”은 다르다는 점이다. Plan B 이후부터는 등재 여부가 아니라 공식 warm64 전체기간 성과로 판단했다.

## 6. tick 288 공식 warm64 결과

Source:

- `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_export_summary_20260705.json`

| metric | value |
|---|---:|
| rows | 288 |
| status ok | 288 |
| gate_passed | 0 |
| negative_profit_count | 288 |
| mdd_excess_count | 287 |
| low_daily_trades_count | 9 |
| avg_profit | -156,454,183 |
| median_profit | -127,477,017 |
| avg_MDD | 512.22 |
| median_MDD | 468.88 |

tick lane 결론:

- 엔진은 정상이다. 288/288이 status ok였다.
- 성과는 전부 손실이다. gate 완화로 해결되는 문제가 아니다.
- tick lattice는 전략 후보가 아니라 실패 지도였다.

## 7. min 288 공식 warm64 결과

Source:

- `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_export_summary_20260705.json`

| metric | value |
|---|---:|
| rows | 288 |
| status ok | 281 |
| error/no metrics | 7 |
| gate_passed | 0 |
| negative_profit_count | 271 |
| mdd_excess_count | 215 |
| low_daily_trades_count | 58 |
| avg_profit | -14,177,407 |
| median_profit | -10,967,726 |
| avg_MDD | 70.99 |
| median_MDD | 55.82 |

min lane 결론:

- tick보다 덜 나쁘고 sparse positive signal이 있었다.
- 하지만 profitable + MDD <= 35 + daily >= 0.5의 교집합은 0이었다.
- 단일 lattice seed로는 survivor가 없고, coverage/composite 설계가 필요했다.

## 8. 576 lattice 공식 결과와 구조적 결론

Source:

- `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_overnight_20260705/overnight_no_d_576_deep_analysis_20260705.json`
- `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_go_no_go_hold_20260705.json`

| metric | value |
|---|---:|
| total lattice | 576 |
| status ok | 569 |
| error/no metrics | 7 |
| P6 go | 0 |
| P6 hold | 0 |
| P6 no_go | 576 |
| positive_profit | 10 |
| mdd <= 35 | 74 |
| daily >= 0.5 | 502 |
| positive + MDD <= 35 + daily >= 0.5 | 0 |

구조적 결론:

- lattice는 자동 생성 후보의 전수 실험 장치다.
- 이 lattice는 “조건식 생성기가 만들어낸 전략 후보가 대부분 어떤 이유로 실패하는지”를 보여줬다.
- 실패 원인은 엔진/기간/profile 문제가 아니라 조건식 구조와 축 조합 문제다.
- 단일 cell/time/size/strength/family 조합은 신호가 너무 단순하거나, 수익이 나면 거래수가 부족하고 거래수가 늘면 MDD/손실이 커졌다.

## 9. tick lane과 min lane의 차이

| lane | 성격 | 결론 |
|---|---|---|
| tick | 빠르고 손실 구조가 넓게 드러남 | positive_profit 0, MDD 과다, repair 우선순위 낮음 |
| min | sparse positive/low-MDD 조각이 일부 있음 | composite/seed 연구 입력으로는 의미 있음 |

tick은 거래수가 많아도 손익 구조가 무너졌다. min은 일부 양수 profit과 낮은 MDD 조각이 있었지만 daily trade gate와 동시에 만족하지 못했다. 따라서 repair는 tick이 아니라 min lane 중심으로 진행한 것이 맞았다.

## 10. 조건식 생성 실패 원인

실패 이유는 단순히 gate 기준이 엄격했기 때문이 아니다.

주요 원인:

- 매수 조건이 time_bucket, size, strength, family 축을 격자식으로 조합했지만 실제 시장 상태 전환을 충분히 반영하지 못했다.
- tick lane은 과도한 손실/MDD가 구조적으로 반복됐다.
- min lane은 수익이 나는 조각이 있었지만 거래 빈도가 너무 낮거나, 빈도를 늘리면 MDD가 커졌다.
- sell/risk profile은 일부 개선 여지가 있었지만, 매수 신호 자체의 edge 부족을 완전히 보정하지 못했다.
- 단일 seed 후보는 daily coverage가 낮아 robust하게 쓰기 어렵다.

## 11. gate 기준이 과도했는지 여부

gate가 일부 후보를 엄격하게 걸러낸 것은 맞다. 하지만 576 lattice에서는 gate를 완화해도 survivor로 볼 수 없는 문제가 많았다.

근거:

- tick은 288/288이 negative profit이었다.
- min은 positive_profit 10개가 있었지만 daily >= 0.5와 겹치지 않았다.
- P6 결과는 go 0, hold 0, no_go 576이었다.

따라서 gate는 “너무 엄격해서 좋은 후보를 버린” 것이 아니라, 구조적으로 불충분한 후보를 promotion으로 오해하지 않게 막는 역할을 했다. 단, seed 연구 단계에서는 promotion gate가 아니라 research-lane gate를 별도로 두는 것이 맞다.

## 12. 백테스트 엔진/기간/profile 문제와 조건식 성과 문제의 분리

초기에는 wrong-profile 실행이 있었다.

| issue | 처리 |
|---|---|
| 8-engine/2025Q1 tick run | 공식 판단에서 제외 |
| official tick profile | DB 전체기간 2022-03-23~2026-02-27, warm64 |
| official min profile | DB 전체기간 2025-04-07~2026-02-27, warm64 |
| stale/partial chunk | blocker/supplement/receipt로 분리 |
| warm64 prepare wait | process/DB 감사 후 retry 범위 제한 |

공식 결론은 wrong-profile 결과가 아니라 DB 전체기간/warm64 산출물에 기반한다. 따라서 “gate를 못 넘긴 이유”는 공식 실행 기준에서는 조건식 성과 문제로 봐야 한다.

## 13. no_go 원인 분석

576 deep analysis 기준:

| primary fail | count |
|---|---:|
| mdd_excess | 479 |
| mdd_excess_and_low_daily_trades | 23 |
| low_daily_trades | 44 |
| nonpositive_profit | 23 |
| no_metrics_or_error | 7 |

해석:

- MDD가 가장 큰 실패 축이다.
- min lane에서 daily trade 부족도 중요하지만, daily만 완화해도 손익/MDD 문제는 남는다.
- family/size/strength별로 완전히 안전한 축은 없었다.
- 1430p/14h late bucket은 MDD가 상대적으로 낮아 보였지만 거래 빈도와 수익 안정성이 부족했다.

## 14. repair composite 연구 성과

Source:

- `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_coverage_20260706/repair_composite_coverage_preflight_result_20260706.json`
- `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_expanded_preflight_result_20260706.json`
- `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_result_20260706.json`

| stage | result |
|---|---|
| coverage preflight 24 | go 16, hold 1, no_go 7 |
| expanded preflight 48 | go 32, no_go 16 |
| selected OOS-style 16 | survivor 15, no_go 1 |

성과:

- 단일 lattice seed보다 composite 방식이 훨씬 낫다.
- 실패한 lattice를 버린 것이 아니라, failure map에서 쓸 수 있는 조각을 조합했다.
- Plan D seed_pool을 열 수 있는 실질 근거가 생겼다.

## 15. Plan D seed 연구가 필요했던 이유

Plan D는 “좋아 보이는 후보를 계속 돌리는” 단계가 아니라, composite survivor를 seed로 고정하고 controlled mutation을 통해 어떤 축이 실제로 개선되는지 보는 단계였다.

필요했던 이유:

- 576 lattice에서 go/hold가 0이었으므로 기존 lattice만 계속 돌릴 이유가 없었다.
- composite OOS-style survivor 15개가 생기면서 seed_pool 입력이 생겼다.
- seed별로 R1/R2/R3 controlled replay를 해야 다음 generation 설계에 남길 축과 버릴 축을 알 수 있었다.

## 16. rank01/rank02/rank03 성과 비교

| rank | 주요 결과 | 해석 |
|---|---|---|
| rank01 | R2 selected OOS 3/3 survivor, R3 selected OOS 1/1 survivor | 초기에 가장 강한 seed였고 Plan D 가능성을 열었다 |
| rank02 | R1 2/2 survivor, R2 3/3 survivor, R3 1/1 survivor | 여러 sell/coverage 조합이 살아남았으나 후속 라운드 효율은 점차 낮아짐 |
| rank03 | R1 1/1 survivor, R2-05 selected OOS-style survivor | R2-05가 coverage와 MDD를 동시에 개선한 의미 있는 boundary case |

rank03 R2-05 최신 결과:

| metric | R2 limited replay | selected OOS-style |
|---|---:|---:|
| profit | 1,912,728 | 554,624 |
| MDD | 10.79 | 5.24 |
| trades | 439 | 80 |
| daily_avg_trades | 2.10 | 2.20 |
| gate | true | true |

## 17. R2-05가 의미 있는 이유

R2-05는 parent 대비 다음 항목을 동시에 개선했다.

- profit 증가
- MDD 감소
- trades/daily 증가
- selected OOS-style robustness window에서도 gate 통과

특히 daily_avg_trades가 2.20으로 유지된 점이 중요하다. 기존 lattice 실패의 핵심 중 하나가 “수익이 나면 daily가 부족하고 daily가 늘면 MDD가 커지는 구조”였기 때문이다.

## 18. 아직 남은 과최적화 위험

가장 큰 위험은 OOS-style window가 fully blind가 아니라는 점이다.

- R2-05는 full-period min replay에서 선별됐다.
- full-period에는 selected OOS-style window인 2026-01-01~2026-02-27이 포함되어 있었다.
- 따라서 이 결과는 promotion 근거가 아니라 research seed 근거다.

추가 위험:

- seed_pool이 같은 source lineage에서 파생되어 독립성이 약하다.
- 반복 R라운드는 작은 window에 맞춰지는 위험이 있다.
- unlimited Plan D loop는 seed를 개선하는 것이 아니라 window에 맞추는 과정이 될 수 있다.

## 19. 다음 연구에서 버려야 할 접근

- 576 lattice를 같은 축으로 다시 대량 실행하는 접근.
- tick lane에서 같은 time/size/strength/family 격자를 반복하는 접근.
- full-period replay에서 고른 후보를 blind OOS survivor처럼 해석하는 접근.
- go가 없는 상태에서 portfolio를 산출하는 접근.
- R3/R4를 자동으로 계속 여는 loop.

## 20. 다음 연구에서 유지해야 할 접근

- DB 전체기간/warm64/profile receipt를 먼저 고정하는 방식.
- wrong-profile, stale/partial, prepare wait를 성과 판단과 분리하는 방식.
- INSERT-only DB registration.
- selected-only preregistration 후 제한 OOS-style robustness replay.
- no_go 원인을 MDD, 손익, daily, time, size, strength, family로 분해하는 방식.
- composite coverage 방식.
- survivor를 seed_pool/passport로 기록하되 portfolio-ready로 승격하지 않는 방식.

## 21. 최종 추천안

Plan D는 여기서 자동 확장하지 않는다.

추천:

1. rank03 R2-05는 survivor seed로 보존한다.
2. R3는 자동으로 열지 않는다.
3. lattice 자체는 나중에 재설계한다. 재설계는 tick 중심이 아니라 min/composite/coverage 중심으로 한다.
4. 다음 연구는 fully blind split 또는 walk-forward 구조를 먼저 설계한 뒤 seed를 평가한다.
5. promotion/export/live/final은 여전히 금지한다.

다음에 연구를 계속한다면 목표는 “더 많은 R라운드”가 아니라 “lattice/condition-generation 설계 자체의 재검토”여야 한다.

## 22. 주요 산출물

| type | path |
|---|---|
| R2-05 OOS result | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_selected_oos_result_20260708.json` |
| boundary receipt | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_boundary_receipt_20260708.json` |
| append receipt | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_oos_survivor_append_receipt_20260708.json` |
| local survivor | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_f_selected_oos_20260708/plan_d_rank03_r2_selected_oos_survivors_20260708.jsonl` |
| seed passport | `docs/research/condition_research/generated_conditions/plan_d_seed_pool_20260706/passports/plan_d_rank03_r2_oos_20260708_01.md` |
| ULW transcript | `.omo/ulw-loop/evidence/20260708_rank03_r2_closeout_loop_v2/C001_r2_05_oos_transcript.txt` |

## 23. Final State

| item | state |
|---|---|
| R2-05 OOS classification | survivor |
| survivor append | done |
| seed_pool append | done |
| passport | done |
| R3 | not opened |
| portfolio | not generated |
| export/live/final | not touched |
| DB UPDATE/DELETE | not used |
| next recommended direction | lattice/condition-generation redesign, not unlimited Plan D |
