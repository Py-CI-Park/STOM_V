# Wide v2 v5 candidate pool recovery design

## Purpose

이 문서는 Wide v2 MVP가 더 이상 방향을 잃지 않도록 현재 위치, 최종 목적지, 남은 단계, 그리고 `best_feature_mix_v5` 후보 풀 0개 문제의 복구 설계를 고정한다.

최종 목적지는 실거래 자동 운용이 아니다. MVP의 최종 목적지는 다음 CLI 연구 루프가 재현 가능하게 동작하는 것이다.

```text
기준 조건식
-> 백테스트
-> 결과 CSV/JSON/Markdown 기록
-> 데이터/퀀트 분석
-> 후보 조건식 자동 생성
-> 후보 백테스트
-> 성능/거래수/집중도/row-set 중복 평가
-> best 후보 선택
-> 다음 round seed로 반복
-> final_best_candidate 선정
-> WFO/OOS 검증 대상으로 handoff
```

Wide v2 MVP 완료 조건은 `final_best_candidate`를 실전 승인하는 것이 아니라, 반복 개선 루프가 후보를 만들고 백테스트하고 최종 WFO/OOS 검증 대상으로 넘길 수 있음을 증명하는 것이다.

## Current Branch State

현재 작업 브랜치:

```text
feature/wide-v2-smoke-full-run-validation-exec
```

이 브랜치에는 다음 실행 증거가 기록되어 있다.

```text
28dcc016 Wide v2 smoke 실패 결과를 기록한다
```

중요한 운영 원칙:

```text
계획/구현/검증이 끝나기 전에는 PR merge를 하지 않는다.
PR은 구현과 검증이 통과한 뒤 생성한다.
```

## Wide v1 and Wide v2 Flow

Wide v1은 조건식 개선을 단일 라운드에서 검증한 흐름이다.

```text
기존 기준 전략
-> 백테스트 실행
-> 백테스트 CSV 분석
-> feature별 후보 조건 추출
-> 후보 조건식 생성
-> candidate_count 후보 백테스트
-> 후보 성능 비교
-> 거래수/유지율/집중도 확인
-> row-set 중복 확인
-> 대표 후보 선정
-> WideV1Final_B_20260425 생성
-> WFO 검증
-> MVP freeze 후보 고정
```

Wide v1 내부 단계는 다음 의미로 정리한다.

```text
Wide v1 초기
-> 백테스트 결과에서 기본 후보 조건식을 생성하는 루프

Wide v1 v2
-> 기존 best 후보를 seed로 삼아 feature 조합 후보 생성

Wide v1 v3
-> 비슷한 후보들의 ranking/tie-break 기준 보강

Wide v1 v4
-> 조건식은 달라도 실제 거래 row-set이 같은지 검사
-> row-set 다양성 개념 도입

Wide v1 v5
-> 후보 백테스트 전에 실제 row-set 대표 후보를 골라 실행
-> 중복 후보를 줄이고 의미 있는 후보만 백테스트하려는 단계

WideV1Final_B_20260425
-> v5/promote/WFO 이후 생성된 현재 기준 seed 조건식
```

Wide v2는 Wide v1 v5를 여러 라운드 반복하는 자동 개선 루프다.

```text
WideV1Final_B_20260425
-> round 1 baseline backtest
-> round 1 분석
-> round 1 후보 조건식 생성
-> round 1 후보 백테스트
-> round 1 best 선택
-> round 1 best를 round 2 seed로 승격
-> round 2 반복
-> global leaderboard 누적
-> final_best_candidate 선정
-> WFO/OOS handoff
```

따라서 지금 고치는 대상은 `Wide v2 optimizer` 전체 재작성도, Wide v6/v7 신규 단계도 아니다. 지금 고치는 대상은 Wide v2 안에서 사용하는 `best_feature_mix_v5` 후보 생성 shortfall이다.

## Smoke Failure Summary

실제 smoke 실행 결과:

```text
command: discovery optimize-wide-v2
candidate_count: 2
max_rounds: 2
elapsed: 4.82 minutes
status: error
stop_reason: insufficient_candidates
failure_phase: insufficient_retention_candidates
failure_message: candidate_count=2 requested but only 0 candidates selected after retention filtering
completed_round_count: 0
leaderboard_count: 0
final_best_candidate: none
wfo_candidate: none
```

baseline backtest는 성공했다.

```text
baseline_csv: backtest/csv\stock_bt_WideV1Final_B_20260425_20260427160214.csv
baseline trade_count: 27416
baseline elapsed_seconds: 277.782
iteration runtime elapsed_seconds: 285.25
```

후보 생성/선택 상태:

```text
requested_candidate_count: 2
selected_candidate_count: 0
v4_candidate_count: 0
eligible_count: 0
execution_count: 0
planned_execution_count: 0
retention pool_count: 0
retention selected_count: 0
```

결론:

```text
백테스트 엔진 실패가 아니다.
수익성 평가 실패도 아니다.
후보 조건식 생성 단계에서 v5가 실행 후보 풀을 만들지 못했다.
```

## Root Cause

현재 v5 흐름은 다음과 같이 좁아진다.

```text
analysis_result.recommended_candidates 전체
-> generate_condition_expressions_from_analysis(top_n)
-> selected_candidates 일부만 expression_candidates로 전달
-> build_v4_candidate_pool()
-> trade_amount_feature 후보 또는 secondary_features 후보만 조합
-> 후보가 없으면 v4_candidate_count=0
-> retention pool_count=0
-> insufficient_candidates
```

이번 smoke 설정:

```text
candidate_count=2
candidate_pool_multiplier=3
effective_top_n=6
trade_amount_feature=B_등락율
secondary_features=empty
```

분석 결과 전체에는 `B_등락율` 후보가 있었다. 그러나 v4/v5 조합 후보로 이어지지 못했다. 즉 현재 규칙은 "분석 결과에는 후보가 있는데 중간 후보 생성기가 그 후보를 놓쳐 실행 후보가 0개가 되는" 구조적 위험이 있다.

문제는 4개다.

```text
1. 후보 공급 범위가 좁다.
   recommended_candidates 전체가 아니라 top_n 일부만 v4 후보 생성으로 들어간다.

2. v4 후보 생성 규칙이 좁다.
   trade_amount_feature 또는 secondary_features에 해당하는 후보가 없으면 후보가 0개가 된다.

3. v5 복구 경로가 없다.
   v4_candidate_count=0이면 recommended_candidates 전체를 다시 훑는 recovery layer가 없다.

4. 관찰성이 부족하다.
   optimizer summary 최상위 requested_candidate_count/selected_candidate_count가 null로 남아 round JSON까지 내려가야 원인을 알 수 있다.
```

## Design Decision

선택한 설계는 `v5 recovery layer` 추가다.

```text
기본 v4 후보 생성
-> 후보가 있으면 기존 v5 row-set/retention selection 사용
-> 후보가 0개면 v5 recovery 시작
-> recommended_candidates 전체에서 후보 재탐색
-> recovery family 후보 생성
-> retention/row-set proxy 평가
-> candidate_count 후보 선택
-> 후보 백테스트
```

이 선택의 기준:

```text
후보 생성 단계는 충분히 넓게 만든다.
후보 선별 단계는 retention/row-set 기준으로 엄격히 거른다.
후보 실행 단계는 최소 smoke candidate_count를 만족하도록 한다.
후보 평가 단계는 leaderboard로 비교한다.
```

## Rejected Approaches

### Rejected: only increase CLI top_n

`--top-n 20` 또는 `candidate_pool_multiplier` 증가만으로 해결하는 방식은 제외한다.

이 방식은 이번 seed에서는 후보가 나올 수 있지만, 다음 round seed가 바뀌면 다시 후보 풀이 0개가 될 수 있다. 이것은 자동 개선 루프의 구조적 복구가 아니라 실행 파라미터 의존이다.

### Rejected: relax retention first

`min_estimated_retention`을 낮춰서 후보를 통과시키는 방식도 1차 해결책으로 쓰지 않는다.

이번 실패는 retention에서 떨어진 것이 아니라 retention에 들어갈 후보 풀이 0개였기 때문이다. 먼저 후보 풀을 복구하고, 그 다음 기존 retention/row-set 평가를 적용해야 한다.

### Rejected: introduce Wide v6 or v7

새 후보 생성 단계 이름을 늘리지 않는다.

MVP 지연을 줄이기 위해 Wide v2 안에서 v5 후보 생성 shortfall만 복구한다. 새로운 실험 단계명은 MVP 이후로 미룬다.

## Proposed Components

### 1. v5 recovery helper

새 helper를 작은 파일로 분리한다.

```text
cli/research_iteration_v5_recovery.py
```

책임:

```text
input:
  - full recommended_candidates
  - existing v4 result
  - best seed primary/trade condition
  - primary_feature
  - trade_amount_feature
  - secondary_features
  - candidate_count

output:
  - recovered candidate list
  - recovery metadata
```

이 파일은 백테스트를 실행하지 않는다. 후보 후보군만 만든다.

### 2. research_loop integration

`cli/research_loop.py`는 최소 연결만 담당한다.

```text
build_v4_candidate_pool()
-> if v5 and v4_candidate_count == 0:
     build_v5_recovery_candidate_pool()
-> annotate_candidate_rowset_proxy()
-> select_rowset_diverse_candidates()
```

대규모 리팩토링은 하지 않는다.

### 3. optimizer failure metadata propagation

`cli/research_optimizer.py`는 round result에 있는 실패 metadata를 최상위 summary로 보존해야 한다.

필요 필드:

```text
requested_candidate_count
selected_candidate_count
v4_candidate_count
eligible_count
execution_count
planned_execution_count
recovery_attempted
recovery_reason
```

### 4. report visibility

Markdown report에는 v5 recovery 상태를 보여준다.

필수 섹션 또는 필드:

```text
initial_v4_candidate_count
recovery_attempted
recovery_reason
recovery_family_counts
final_candidate_pool_count
eligible_count
selected_count
```

## Recovery Candidate Families

Recovery 후보 family는 출처를 명확히 남긴다.

### Family 1: direct_v4

기존 v4 후보가 존재하면 그대로 사용한다.

```text
v5_candidate_source=direct_v4
```

### Family 2: recovered_trade_feature

`recommended_candidates` 전체에서 `feature == trade_amount_feature` 후보를 다시 찾는다.

```text
v5_candidate_source=recovered_trade_feature
```

생성 방식:

```text
best_primary_condition
AND recovered_trade_feature_condition
```

목적은 현재 seed의 primary 축을 유지하면서 trade/second 축을 바꾸는 것이다.

### Family 3: auto_secondary_feature

`secondary_features`가 비어 있거나 유효 후보가 없으면, `recommended_candidates` 상위 feature 중 primary/trade feature를 제외한 feature를 자동 secondary 후보로 선택한다.

```text
v5_candidate_source=auto_secondary_feature
```

생성 방식:

```text
best_primary_condition
AND best_trade_condition
AND auto_secondary_condition

best_primary_condition
AND auto_secondary_condition
```

### Family 4: safe_recommended_fallback

위 family가 모두 부족하면, top recommended condition을 seed primary와 결합해 최소 후보 풀을 만든다.

```text
v5_candidate_source=safe_recommended_fallback
```

생성 방식:

```text
best_primary_condition
AND recommended_condition
```

단, primary condition과 완전히 동일한 후보는 제외한다.

## Selection Rules

Recovery 후보도 기존 v5와 같은 proxy/row-set selection을 통과해야 한다.

```text
recovery candidates
-> annotate_candidate_rowset_proxy()
-> select_rowset_diverse_candidates()
-> candidate_count보다 부족하면 structured insufficient_candidates
```

기본 정책:

```text
min_estimated_retention은 먼저 낮추지 않는다.
row-set diversity를 우회하지 않는다.
실행 후보 수를 채우기 위해 duplicate-only 후보를 억지로 실행하지 않는다.
```

이유:

```text
후보 생성은 넓히되, 후보 선별은 엄격하게 유지해야 과최적화 위험을 줄일 수 있다.
```

## Data Flow After Recovery

목표 흐름:

```text
analysis_result.recommended_candidates
-> expression_result.selected_candidates
-> build_v4_candidate_pool
-> if v4 pool empty: build_v5_recovery_candidate_pool
-> expression_result.iteration_v5.recovery 기록
-> annotate_candidate_rowset_proxy
-> select_rowset_diverse_candidates
-> candidate specs 생성
-> candidate backtests
-> ranking
-> actual row-set representative selection
-> best_candidate
-> optimizer leaderboard
```

Smoke 통과 기준:

```text
candidate_count=2 smoke가 후보 백테스트 단계까지 진입한다.
leaderboard가 1개 이상 생성된다.
final_best_candidate 또는 구조화된 candidate runtime failure가 생성된다.
v5 recovery metadata가 summary/report에 남는다.
```

Full run 통과 기준:

```text
candidate_count=10 run이 최소 1 round를 완료한다.
leaderboard가 생성된다.
final_best_candidate가 존재한다.
wfo_candidate가 존재한다.
duplicate_rowset_only가 아니어야 한다.
```

## Error Handling

복구 이후에도 후보가 부족하면 error는 유지한다. 단, error payload는 더 설명적이어야 한다.

필수 error metadata:

```text
status=error
stop_reason=insufficient_candidates
failure_phase=insufficient_retention_candidates
failure_message=candidate_count=2 requested but only 0 candidates selected after retention filtering
requested_candidate_count=2
selected_candidate_count=0
initial_v4_candidate_count=0
recovery_attempted=true
recovery_family_counts={"recovered_trade_feature": 3, "auto_secondary_feature": 6}
final_candidate_pool_count=9
eligible_count=2
```

이렇게 하면 다음 실행에서 round JSON까지 깊게 파지 않아도 실패 위치를 알 수 있다.

## Testing Strategy

단위 테스트:

```text
1. v4 후보가 있으면 recovery를 실행하지 않는다.
2. v4 후보가 0개이고 recommended_candidates에 trade feature가 있으면 recovered_trade_feature 후보를 만든다.
3. secondary_features가 비어 있으면 auto_secondary_feature 후보를 만든다.
4. fallback 후보도 best primary condition을 포함한다.
5. primary/trade와 동일한 중복 후보는 제거한다.
6. recovery metadata에 family별 count가 남는다.
7. recovery 후보가 row-set proxy selection으로 전달된다.
8. recovery 후에도 후보가 부족하면 requested/selected count가 result 최상위와 optimizer summary에 남는다.
9. optimizer report가 recovery metadata를 렌더링한다.
```

실행 검증:

```text
1. candidate_count=2 smoke 재실행
2. smoke가 후보 백테스트 단계까지 진입하는지 확인
3. smoke 결과가 healthy하면 candidate_count=10 max_rounds=1 또는 3 실행
4. final_best_candidate가 있으면 WFO/OOS 검증 계획으로 이동
```

## MVP Completion Path

남은 MVP 단계는 새 버전 추가가 아니라 Wide v2 종료다.

```text
현재 설계 문서 승인
-> writing-plans 작성
-> v5 recovery 구현
-> unit test
-> candidate_count=2 smoke 재실행
-> candidate_count=10 full run
-> final_best_candidate WFO/OOS 검증
-> Wide v2 MVP 완료 문서
```

MVP 전에 하지 않을 것:

```text
1. Wide v6/v7 추가
2. 대규모 cli 리팩토링
3. WFO를 inner loop로 재도입
4. 실거래 자동 운용
5. strategy.db에 중간 후보 영구 누적
```

MVP 이후 리팩토링 후보:

```text
1. cli/research_loop.py 역할 분리
2. candidate generation/retention/report/optimizer 모듈 경계 정리
3. execution artifact 관리 체계 정리
```

## Next Superpowers Step

이 설계가 승인되면 다음 단계는 구현 계획 작성이다.

```text
$writing-plans Wide v2 v5 후보 풀 recovery 구현 계획 작성
```

구현 계획 이후에만 코드 변경을 시작한다.
