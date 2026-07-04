# 개선된 조건식 연구 프로세스 다음 실행 계획서

## 목적

이번 계획서는 개선된 process-research v2 구조를 실제 연구처럼 실행하기 전 고정하는 연구 계획서다. 목표는 프로세스 통과가 아니라 **좋은 조건식을 만들 확률을 높이는 반복 연구**다.

- canonical process: `process-research`
- preset: `research`
- mode: research-only advisory
- 금지: export=false, live=false, finalPromotion=false
- 3틱 슬리피지: 즉시 생성 hard gate가 아니라 promotion/live 전 advisory risk
- 기본 엔진: 64 우선, warm prepare failure / engine_data_response_timeout / no-metrics / replay failure 시 32 fallback receipt 기록

## 시작 seed 결정

| 역할 | condition_id | human_name | 근거 | 연구 사용 방식 |
|---|---|---|---|---|
| 1차 시작 seed | `rr8_12_turnover_min_902=1.5` | `OOSStable_Open902_TurnoverMin_v1` | 4/4 OOS-style window 통과, profit 3,062,696, MDD 12.87 | 첫 repair 부모. buy/sell 전문을 Context Pack에 넣고 시작 |
| profit comparator | `rr8_21_trail_keep=0.7` | `ProfitLead_TrailKeep070_2025Comparator` | 2025 full-period profit 3,089,180, MDD 18.84, trades 165 | profit 비교 기준. 직접 승격 아님 |
| segment comparator | `rr8_0_cap_max=2500` | `CapLimited_2500_Comparator` | profit 3,047,522, MDD 17.34, trades 145 | 시총/coverage 비교 기준 |
| 실패/coverage 참고 | `human_seed_gptauth_B_gen8` | `GPTGen8_HighCoverage_FailedProfitContext` | profit 1,772,126, MDD 15.14, trades 550, daily 2.3 | coverage는 높지만 품질 낮은 실패 사례로 분석 |

### 시작 seed 선택 판단

`rr8_12_turnover_min_902=1.5`를 첫 시작점으로 둔다. 이유는 profit leader가 아니라 **안정 기준선**이기 때문이다. 좋은 조건식 연구의 다음 단계는 최고 profit 하나를 추격하는 것이 아니라, 안정적인 부모에서 작은 단일축 repair를 반복하여 overfit 없이 개선 가능성을 찾는 것이다.

## 실행 전 필수 준비

| 단계 | 작업 | 산출물 | 실패 시 처리 |
|---|---|---|---|
| 0-1 | seed id별 buy/sell 조건식 전문 resolve | condition passport 초안 | 전문 누락 시 연구 시작 금지 |
| 0-2 | buy/sell sha256 계산 | `buy_code_sha256`, `sell_code_sha256` | hash 누락 시 Context Pack 생성 금지 |
| 0-3 | 기존 공식 결과 연결 | baseline csv, metrics, analysis refs | no-metrics면 replay 먼저 |
| 0-4 | Condition Passport 작성 | `condition_passports/*.md` | 사람이 검토 가능한 이름 부여 |
| 0-5 | Research Prompt Context Pack 생성 | `research_context_pack.json` | 250k budget 초과 시 fail-closed |

## Research Prompt Context Pack 필수 내용

| 범주 | 포함 내용 | 이유 |
|---|---|---|
| STOM 규칙 | `strategy.txt`, `rules.txt`, system prompt, variables reference, forbidden, examples | LLM이 문법/금지 변수를 정확히 알게 함 |
| 부모 조건식 | 이전 buy 전문, 이전 sell 전문, id, sha256 | id가 아니라 구조를 보고 repair 하게 함 |
| 공식 결과 | profit, MDD, trades, daily, win, payoff | prompt score가 아니라 실제 결과 기준 |
| 시간대 분석 | 09:00~09:05, 09:05~09:10 등 | open loss/give-back 진단 |
| 시가총액 분석 | small/mid/large cap | 시총별 약점/강점 분리 |
| 국면 분석 | 등락률, 거래대금, 체결강도, 체결강도 변화 | feature family 가설 생성 |
| 히트맵 | time x cap x regime | avoid/prefer zone 추출 |
| MFE/MAE | give-back, adverse excursion | exit/trailing repair 판단 |
| correlation/redundancy | 중복 변수 그룹 | 같은 의미 변수 반복 방지 |
| root-cause | 가장 큰 실패 원인 1~3개 | 후보 mutation axis 제한 |
| candidate hypotheses | 후보별 hypothesis/expected effect/risk | 다중 후보 생성을 명확히 함 |
| authority | research-only, no export/live/final promotion | 경계 유지 |

## 후보 생성 계획

하나의 분석 카드에서 후보 1개만 만들지 않는다. 최소 2개, 권장 3개를 생성한다.

| 후보 | lane | 부모 | 가설 | mutation axis | 조건 |
|---|---|---|---|---|---|
| A | repair | `OOSStable_Open902_TurnoverMin_v1` | 안정 baseline의 가장 큰 손실 cluster 하나를 제거 | exit/trailing 또는 open-loss filter 1개 | parent buy/sell 구조 보존 |
| B | repair | `OOSStable_Open902_TurnoverMin_v1` | turnover 추가 강화는 피하고 다른 실패 원인 수정 | time/cap loss segment 1개 | A와 다른 실패 원인 또는 다른 축 |
| C | discovery | 기존 rr8 계열과 다른 coverage | 새 feature family 또는 market segment 탐색 | coverage regime/feature family | novelty gate 통과 필수 |

금지 후보:

| 금지 | 이유 |
|---|---|
| `turnover_min_902 1.5 -> 3.0` 반복 | 직전 one-mutation에서 profit/MDD 모두 악화 |
| R_/S_ 결과·진단 변수 사용 | 미래/결과 누수 |
| parent id만 가진 repair | 구조 보존 검증 불가 |
| 후보 1개만 생성 | 분석 정보 활용 부족 |
| promotion-review에서 생성 | zero-generation 원칙 위반 |

## 실행 루프

| 순서 | 작업 | 입력 | 산출물 | 판단 기준 |
|---|---|---|---|---|
| 1 | baseline full-period replay | seed buy/sell 전문 | baseline receipt | 공식 결과 재확인 |
| 2 | Analysis Card v2 작성 | baseline result | analysis card | root-cause, avoid/prefer, segment contribution 존재 |
| 3 | multi-hypothesis prompt | Context Pack + card | candidate pack | repair>=1, discovery>=1, 2~3+ 후보 |
| 4 | strict validation | candidate pack | validation receipt | parent code, novelty, authority, R_/S_ leakage 검사 |
| 5 | official backtest | 각 후보 | candidate receipts | timeout/no-metrics/failure 기록 |
| 6 | analysis card update | 후보 결과 | candidate analysis cards | 왜 좋아졌거나 나빠졌는지 설명 |
| 7 | ranking | official result | branch decision | prompt score가 아니라 공식 결과 중심 |
| 8 | next iteration | best branch/reject reason | 다음 Context Pack | 단일 실패 원인/단일 축 유지 |
| 9 | promotion-review | frozen candidates | review-only report | generation 0, export/live/finalPromotion false |

## 관리 보고서 템플릿

실행 중에는 다음 표를 관리 보고서에 계속 갱신한다.

| 시각 | 단계 | 후보 | 상태 | 증거 | 결정 |
|---|---|---|---|---|---|
| T+00 | seed resolve | baseline | pending | passport path | code 누락 확인 |
| T+01 | replay | baseline | pending | backtest receipt | 64/32 engine 기록 |
| T+02 | generation | A/B/C | pending | candidate pack | 후보별 가설 확인 |
| T+03 | backtest | A | pending | candidate receipt | official result 기준 |
| T+04 | backtest | B | pending | candidate receipt | official result 기준 |
| T+05 | backtest | C | pending | candidate receipt | novelty 검토 |

## 결과 보고서 템플릿

| 항목 | 기록 내용 |
|---|---|
| Executive summary | 어떤 후보가 왜 우세/열세였는지 |
| Seed passport refs | 시작 seed와 comparator condition passport 링크 |
| Context Pack hash | 어떤 프롬프트 입력으로 생성했는지 |
| Candidate pack | 후보별 hypothesis, mutation axis, risk note |
| Official results | profit/MDD/trades/daily/win/payoff |
| Segment diagnosis | time/cap/regime heatmap 요약 |
| Root-cause updates | 새로 확인된 실패 원인 |
| Next queue | 다음 repair/discovery 우선순위 |
| Safety receipt | export/live/finalPromotion false, protected path clean |

## 다음 연구의 성공 기준

좋은 조건식은 한 번에 나오지 않는다. 따라서 다음 실행의 성공 기준은 “즉시 최고 조건식 발견”이 아니라 다음을 만족하는 것이다.

| 성공 기준 | 설명 |
|---|---|
| 재현 가능한 입력 | seed buy/sell 전문, Context Pack hash, source hash가 남아 있음 |
| 서로 다른 후보 | A/B/C가 다른 가설과 mutation axis를 가짐 |
| 공식 결과 연결 | 모든 후보가 official backtest receipt 또는 실패 receipt를 가짐 |
| 분석 환류 | 결과가 다음 Analysis Card와 후보 가설에 반영됨 |
| research-only 유지 | export/live/final promotion 없음 |
| 다음 queue 생성 | 실패해도 다음 연구 방향이 구체화됨 |

## 추천 시작 명령 개념

실제 실행 명령은 현재 런타임/대시보드 상태에 맞춰 확정해야 하지만, 연구 지시는 다음 형태가 맞다.

```text
process-research / preset=research / research-only
start_seed=rr8_12_turnover_min_902=1.5
comparators=rr8_21_trail_keep=0.7, rr8_0_cap_max=2500, human_seed_gptauth_B_gen8
require_full_parent_buy_sell_code=true
candidate_pack=min 2, target 3, repair>=1, discovery>=1
engine=64 first, 32 fallback receipt on warm prepare failure / engine_data_response_timeout / no-metrics / replay failure
no export, no live, no final promotion
```
