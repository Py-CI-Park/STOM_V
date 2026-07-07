# 2026-07-07 lattice 연구 재검토와 rank03 R2 제한 권고

## 1. 목적

이번 기록의 목적은 지금까지의 조건식 연구를 다시 점검해 다음 질문에 답하는 것이다.

| 질문 | 결론 |
|---|---|
| lattice 576개가 실행 오류 때문에 실패했나? | 아니다. tick 288/288, min 288/288 coverage가 공식 전체기간 warm64 기준으로 확보됐다. |
| gate가 너무 엄격해서 전부 탈락했나? | gate만의 문제는 아니다. 576개 중 `positive_profit + mdd<=35 + daily>=0.5` 교집합이 0이다. |
| lattice 자체가 잘못 형성됐나? | 생성/등록/coverage 절차는 정상이다. 다만 "완성 전략 후보"를 기대하기에는 축 설계와 sell 구조가 너무 단순했다. |
| lattice는 원래 손실만 나는 구조였나? | tick lane은 이 profile에서 broad loss 구조였다. min lane은 10개 양수익 저MDD near-miss가 있었지만 거래 빈도가 부족했다. |
| Plan D를 계속 돌릴 가치가 있나? | 무제한 반복은 비효율적이다. rank03 R2 한 사이클만 더 진행하고, 개선이 없으면 Plan D를 중단한 뒤 lattice/condition-generation 설계를 재검토한다. |

## 2. 다시 확인한 원문과 산출물

| 파일 | line_count | sha256 | 적용 섹션 |
|---|---:|---|---|
| `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md` | 392 | `6ecc9544248ca7100bef707e0d7e778f6a517522f9a2f6dd8b8368a7d739629b` | lattice 생성, DB 등재, smoke/coverage/refinement/OOS |
| `docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md` | 143 | `e0dae7379559fe6556a769c8e4312a6f48d926fc299c9e78373afab00dd16ae7` | seed 연구 프로그램, round 중단 조건 |
| `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md` | 384 | `d6acdc65ff73dfd85f656463128b43005935e779d0bbe9a9e1f99bc96d2737fe` | 실제 수행 상태, P5/P6/P7 흐름 |
| `docs/research/condition_research/generated_conditions/lattice/lattice_seeds.json` | 10528 | `685566e1da7bd7158ab40c1e73ef7b9c7d753dc25aee9f0363f188b33a2d0398` | 576 seed 구조 |
| `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_export_summary_20260705.json` | 1936 | `391c51d95c6a128b4a1bf20a192369a853af86c3c25748c739c52d06962be183` | tick 288 공식 결과 |
| `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_export_summary_20260705.json` | 2374 | `6e548da4d40ec262bfa0b15431ce1ac78461415a9fdea1ca454d066e4d45aea3` | min 288 공식 결과 |
| `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_coverage_gaps_batch_plan_no_d_20260705.json` | 70 | `f489b37ba6d9f3663c5b62e56110f890d08732f54d06c0b8cd656828d72058af` | P6 go/hold/no_go |
| `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_overnight_20260705/overnight_no_d_576_deep_analysis_20260705.json` | 1697 | `17aa5833132588b918b6773290292acd5b683235c26821c34ebbadda4194cce5` | 576개 실패 원인 심화 분석 |
| `docs/update_log/2026-07-07_plan_d_rank03_r1_selected_oos_retry03_survivor_handoff.md` | 77 | `5272bf64951e4eaa0cb74d5f8412994568890b9cbd4cf4fbad512d5f5a8a895f` | 최신 rank03 R1 handoff |
| `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_d_selected_oos_20260707/plan_d_rank03_r1_selected_oos_retry03_result_20260707.json` | 119 | `e6eded6f15c23eef4831f3bad4d92155c6e50931d0eee7008b58120ce050e162` | 최신 rank03 R1 survivor 결과 |

## 3. lattice 구조 재정리

`lattice`는 자동 생성된 research-only 조건식 격자다. 최종 전략이 아니라 넓은 탐색 지도를 만들기 위한 `hypothesis_seed` 집합이다.

| 축 | 값 | 개수 기여 |
|---|---|---:|
| lane | tick, min | 2 |
| time bucket | lane별 6개 | 6 |
| size | small, midsmall, midlarge, large | 4 |
| strength | low, mid, high | 3 |
| family | momentum_breakout, volume_surge, strength_surge, prevday_active | 4 |
| 합계 | `2 x 6 x 4 x 3 x 4` | 576 |

`lattice_seeds.json`의 schema는 `seed_lattice_seeds_v1`이고 seed_count는 576이다. 각 seed는 `condition_id`, `cell_id`, `family`, `buy_code`, `sell_code`, buy/sell sha256, params, passport 경로를 가진다.

## 4. 공식 288+288 결과

| 항목 | tick 공식 full warm64 | min 공식 full warm64 |
|---|---:|---:|
| row coverage | 288/288 | 288/288 |
| status ok | 288 | 281 |
| status error/no_metrics | 0 | 7 |
| gate_passed | 0 | 0 |
| 양수익 | 0 | 10 |
| 음수익 | 288 | 271 |
| MDD 초과 | 287 | 215 |
| daily 거래수 부족 | 9 | 58 |
| profit 범위 | -692,611,103 ~ -899,093 | -90,894,637 ~ 819,969 |

P6 결과는 `coverage_complete=true`, `recorded_total=576`, `go=0`, `hold=0`, `no_go=576`이다. 따라서 Plan B refinement/OOS/portfolio는 열리지 않은 것이 맞다.

## 5. 실패 이유 재검토

| 원인 후보 | 판단 | 근거 |
|---|---|---|
| 백테스트 엔진/기간 오류 | 주원인 아님 | wrong-profile 실행은 폐기했고, 이후 DB 전체기간 + warm64 공식 실행이 완료됐다. |
| DB 등재 또는 파일명 오류 | 초기 blocker였으나 해결됨 | sanitized 전략명으로 INSERT-only 재등재했고, official coverage가 완성됐다. |
| gate 과도 엄격 | 단독 원인 아님 | 양수익 10개는 모두 min이고, 그 10개 모두 daily>=0.5를 충족하지 못했다. |
| tick lane 특성 | 큰 원인 | tick 288개는 전부 음수익이며 MDD 초과가 287개다. |
| min lane 조건 구조 | 큰 원인 | min은 양수익 저MDD near-miss가 있으나 거래 빈도와 수익 지속성이 동시에 맞지 않았다. |
| sell 구조 | 개선 필요 | 기본 TP/SL/hold 조합이 단순해 과다 MDD 또는 sparse trade 문제를 해결하지 못했다. |
| condition-generation 설계 | 재검토 필요 | 단일 축 family seed는 지도 작성에는 유효했지만 완성 후보로는 약했다. composite/coverage 방식에서야 survivor가 생겼다. |

핵심 수치:

| predicate | count |
|---|---:|
| positive_profit | 10 |
| positive_and_mdd_le_35 | 10 |
| positive_and_daily_ge_0_5 | 0 |
| positive_mdd_le_35_daily_ge_0_5 | 0 |

즉, gate를 단순 완화하면 "통과 후보"는 만들 수 있어도 신뢰 가능한 후보를 만들 근거는 부족하다. 특히 daily 거래수만 낮춘 통과는 sparse overfit 위험이 크다.

## 6. lattice가 잘못 형성됐는지에 대한 결론

절차 관점에서는 잘못 형성됐다고 보기 어렵다.

- 576개 seed 생성이 계획식과 일치했다.
- DB 등록, sanitized mapping, provenance, chunked official run이 남아 있다.
- 공식 전체기간 warm64에서 tick 288과 min 288의 coverage가 모두 완성됐다.
- wrong-profile/Q1 warm8 결과는 공식 판단에서 제외됐다.

연구 설계 관점에서는 한계가 분명하다.

- tick early-window 단일 패턴은 전체적으로 손실 구조였다.
- min 단일 seed는 일부 양수익 저MDD 신호를 만들었지만 거래 빈도가 부족했다.
- family 4종은 시장 상태, exit 품질, 포지션 유지 조건, 다중 시간대 조합을 충분히 표현하지 못했다.
- sell 조건이 static TP/SL/hold 중심이라 high-MDD와 sparse-positive 문제를 동시에 해결하지 못했다.
- 따라서 lattice는 "생존 후보 생성기"라기보다 "실패 지형도와 repair 방향을 찾는 지도"로 보는 것이 맞다.

## 7. 현재 Plan D의 의미와 한계

Plan D는 실패한 576개를 그대로 계속 돌리는 작업이 아니다. P6와 overnight 분석에서 얻은 near-miss 축을 바탕으로 composite/coverage 후보를 만들고, OOS-style survivor seed를 찾는 작업이다.

현재 성과:

| 단계 | 성과 | 한계 |
|---|---|---|
| composite/coverage repair | go 후보와 OOS-style survivor가 생김 | lattice 원형이 아니라 repair/composite 구조에서 나온 성과 |
| rank01/rank02 | 여러 OOS-style survivor가 seed_pool에 append됨 | 완전 blind OOS가 아니라 full-period replay 선택 후 OOS-style 확인 caveat 존재 |
| rank03 R1 | survivor 1개 확인: profit 931,411, MDD 6.14, trades 20, daily 0.50 | 선택 replay가 2026-01~02를 포함했으므로 robustness replay로 해석해야 함 |

따라서 Plan D는 완전히 무의미하지 않다. 다만 동일 계열의 default sell과 composite buy가 반복되고 있어 무제한 반복하면 점점 같은 구조를 재확인할 가능성이 높다.

## 8. 권고안

권고는 다음과 같이 고정한다.

1. Plan D를 무제한 계속하지 않는다.
2. rank03 R2를 한 사이클만 더 진행한다.
3. R2에서 improved 후보가 없으면 즉시 Plan D를 멈추고 lattice/condition-generation 설계 재검토로 전환한다.
4. R2에서 improved 후보가 있어도 freeze/preregistration 후 selected OOS까지만 허용한다.
5. selected OOS survivor가 없으면 Plan D를 멈춘다.
6. selected OOS survivor가 있으면 seed_pool 기록까지는 허용하되, R3로 자동 진행하지 않는다. 별도 승인 전에는 portfolio/export/live/final promotion을 열지 않는다.

## 9. rank03 R2 제한 실행 기준

| 항목 | 기준 |
|---|---|
| active parent | `plan_d_rank03_r1_oos_20260707_01` |
| 후보 수 | R2 8-slot |
| 등록 | static gate 통과 후보만 INSERT-only |
| replay | 공식 min 전체기간 warm64 limited replay, R2 후보만 |
| OOS | improved 후보가 있고 freeze/preregistration이 작성된 경우 selected max 1~2개만 |
| 중단 조건 | improved 0개, selected OOS survivor 0개, positive control 실패, stale warm blocker 반복 |
| 금지 | full tick 288, full min 288, portfolio, export/live/final, DB UPDATE/DELETE |

## 10. 다음 추천 명령어

```text
$start-work .omo/plans/lattice-rereview-rank03-r2-boundary-20260707.md
```

해당 계획은 기존 `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`를 대체하지 않는다. 다음 실행 범위만 rank03 R2 한 사이클로 제한하고, 개선이 없으면 Plan D를 멈추도록 명시한 경계 계획이다.
