# 2026-04-23 Wide v1 후보 결과 분석 및 반복 개선 루프 v2 설계

## 목적

이번 설계의 목적은 Wide v1 Retention-Aware 후보 5개 실행 결과를 분석하고, best candidate인 `WideV1RetentionCand5_20260422__cand003`을 중심으로 다음 반복 개선 루프 v2를 설계하는 것이다.

이번 단계는 최종 채택, WFO, promote가 아니다. 현재까지 확인된 후보 결과를 바탕으로 다음 후보군을 더 의미 있게 생성하고, v2 실행을 위한 gate를 정의한다.

```text
[완료] Wide v1 CLI baseline GUI compare PASS
        |
        v
[완료] Retention-Aware candidate_count=5 실행
        |
        v
[이번 설계] 후보 결과 분석 + 반복 개선 루프 v2 설계
        |
        v
[다음] v2 후보 생성/실행 계획
        |
        v
[그 다음] v2 candidate_count=5 실행
        |
        v
[조건 충족 시] candidate_count=10 확장
```

## 배경

PR #18에서 Wide v1 full-year CLI baseline과 GUI 기준 결과가 일치했고, `candidate_count=5` 후보 실행도 완료했다.

기준 baseline:

```text
base_buy_strategy=ResearchTest_Tick_B_090000_092800_Wide_20260419
base_sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
baseline_trade_count=40937
baseline_back_count=1638
```

후보 5개 실행 결과:

```text
status=ok
phase=candidates_evaluated
candidate_count_observed=5
retention_selection.selected_count=5
retention_selection.fallback_count=0
all_candidates_backtested=True
all_candidates_promotion_passed=True
cleanup_failed_count=0
best_candidate=WideV1RetentionCand5_20260422__cand003
```

best candidate:

```text
strategy_name=WideV1RetentionCand5_20260422__cand003
expression=66.999 <= 시가총액 < 2_580
trade_count=36918
trade_count_retention=0.9018247551115128
promotion_passed=True
promotion_score=10943.034141541459
retention_penalty=1.0
adjusted_score=10943.034141541459
cleanup=best_candidate_kept
```

## 전체 개발 흐름에서의 위치

```text
[0. 기준 전략 / 기준 CSV]
        |
        v
[1. CSV 분석]
        |
        v
[2. 후보 expression pool 생성]
        |
        v
[3. Retention-Aware 후보 선별]
        |
        v
[4. 후보 5개 백테스트 / ranking]
        |
        v
[5. best_candidate 분석]              <- 이번 설계
        |
        v
[6. 반복 개선 루프 v2]                <- 이번 설계
        |
        v
[7. v2 candidate_count=5 실행]
        |
        v
[8. 조건 충족 시 candidate_count=10]
        |
        v
[9. 최종 promote/WFO 검증]
```

## 후보 5개 요약

```text
rank=1
strategy=WideV1RetentionCand5_20260422__cand003
feature=시가총액
expression=66.999 <= 시가총액 < 2_580
trade_count=36918
trade_count_retention=0.9018247551115128
adjusted_score=10943.034141541459

rank=2
strategy=WideV1RetentionCand5_20260422__cand004
feature=체결강도
expression=0.009 <= 체결강도 < 55.94
trade_count=37990
trade_count_retention=0.9280113344895815
adjusted_score=9079.558772203623

rank=3
strategy=WideV1RetentionCand5_20260422__cand002
feature=등락율
expression=15.894 <= 등락율 < 25
trade_count=37582
trade_count_retention=0.9180448005471823
adjusted_score=8220.553561775416

rank=4
strategy=WideV1RetentionCand5_20260422__cand005
feature=당일거래대금
expression=1_800 <= 당일거래대금 < 3_586
trade_count=39179
trade_count_retention=0.9570559640423089
adjusted_score=4736.37085278282

rank=5
strategy=WideV1RetentionCand5_20260422__cand001
feature=시분초
expression=90029.999 <= 시분초 < 90_055
trade_count=40478
trade_count_retention=0.9887876493148008
adjusted_score=1415.192693028745
```

## 설계 판단

퀀트 관점의 핵심 질문:

```text
cand003이 우연히 1등인가?
아니면 후보 5개 전체에서 반복되는 유효한 손실 제거 패턴이 있는가?
```

따라서 v2는 `cand003` 하나만 좁게 최적화하지 않는다. `cand003`을 중심축으로 삼되, 후보 5개 전체의 공통/차이 패턴을 함께 반영한다.

```text
권장 접근=A+B 혼합
A=cand003 중심 분석
B=후보 5개 공통/차이 패턴 분석
```

## 접근안

### A. cand003 중심 v2

`cand003`의 시가총액 조건을 중심으로 주변 범위를 변형한다.

예시:

```text
시가총액 하한/상한 변형
66.999 <= 시가총액 < 2_580
50 <= 시가총액 < 2_580
100 <= 시가총액 < 2_580
66.999 <= 시가총액 < 2_000
66.999 <= 시가총액 < 3_000
```

장점:

```text
현재 best candidate를 직접 개선한다.
분석과 다음 실행이 명확하다.
```

단점:

```text
시가총액 단일 feature에 과적합될 수 있다.
```

### B. 후보 5개 전체 패턴 기반 v2

상위 후보의 feature를 조합한다.

예시:

```text
시가총액 + 체결강도
시가총액 + 등락율
시가총액 + 당일거래대금
시가총액 + 시분초
```

장점:

```text
특정 feature 하나에 과적합될 위험을 줄인다.
후보 5개 결과 전체를 활용한다.
```

단점:

```text
조합이 많아지면 후보가 중복되거나 과도하게 좁아질 수 있다.
```

### C. row-level CSV 분석 우선

baseline CSV와 cand003 CSV를 거래 단위로 비교해 제거된 거래와 유지된 거래의 손익 특성을 먼저 분석한다.

장점:

```text
손실 제거의 실제 원인을 가장 정밀하게 확인할 수 있다.
```

단점:

```text
범위가 커지고 v2 후보 생성이 늦어진다.
```

판단:

```text
C는 v2의 필수 선행 단계가 아니라 보조 검증 단계로 둔다.
v2 결과가 기대와 다르거나 cand003 개선 원인이 불명확할 때 별도 설계로 올린다.
```

## 권장 설계

이번 설계는 A+B 혼합을 채택한다.

```text
1. cand003 중심 변형 후보 생성
2. cand003 + 보조 feature 조합 후보 생성
3. 중복/과도 축소 후보 제거
4. v2 candidate_count=5 기본 실행
5. 조건 충족 시 candidate_count=10 확장
```

## v2 후보 생성 규칙

### 1. 중심 feature

```text
primary_feature=시가총액
primary_expression=66.999 <= 시가총액 < 2_580
```

### 2. 보조 feature

```text
secondary_features:
  - 체결강도
  - 등락율
  - 당일거래대금
  - 시분초
```

### 3. 후보군 유형

```text
Type A: 시가총액 범위 변형
Type B: 시가총액 + 보조 feature 1개 조합
Type C: 보조 feature 단독 재검증
```

Type C는 후보 다양성을 위해 제한적으로만 포함한다. v2의 중심은 cand003 기반 변형이다.

### 4. 후보 중복 제거

아래 조건이면 중복 후보로 본다.

```text
같은 primary feature
유사한 lower/upper bound
estimated_retention 차이 < 0.02
예상 trade removal 구간이 거의 동일
```

중복 후보는 하나만 남긴다.

### 5. retention 정책

기존 정책 유지:

```text
min_estimated_retention=0.4
retention_fallback=enabled
retention_penalty=enabled
```

추가 관찰:

```text
estimated_retention
actual trade_count_retention
estimated_vs_actual_retention_gap
```

## 실행 gate

### v2 기본 실행

```text
candidate_count=5
candidate_timeout=900
candidate_pool_multiplier=3
```

목표:

```text
v2 후보 생성 규칙이 cand003보다 나은 후보를 만들 수 있는지 확인
```

### v2 확장 실행

```text
candidate_count=10
```

candidate_count=10은 바로 실행하지 않는다. 아래 조건 중 하나 이상을 만족할 때 확장한다.

```text
v2 candidate_count=5에서 best_candidate가 cand003보다 adjusted_score 개선
상위 후보들이 서로 다른 feature 조합을 보여줌
후보 중복률이 낮음
runtime-preflight 통과
cleanup 실패 없음
```

## PASS / HOLD / FAIL 기준

기준 후보:

```text
baseline_candidate=WideV1RetentionCand5_20260422__cand003
baseline_adjusted_score=10943.034141541459
baseline_trade_count=36918
baseline_trade_count_retention=0.9018247551115128
baseline_promotion_passed=True
```

### PASS

```text
v2 candidate_count=5 실행 성공
best_candidate 존재
v2_best.adjusted_score > 10943.034141541459
v2_best.trade_count_retention >= 0.4
v2_best.promotion_passed=True
cleanup_failed_count=0
```

PASS이면 candidate_count=10 확장 설계를 시작할 수 있다.

### HOLD

```text
v2 실행은 성공
best_candidate가 cand003보다 개선되지 않음
상위 후보가 대부분 중복 조건
retention은 충분하지만 score 개선이 약함
row-level CSV 분석이 필요함
```

HOLD이면 후보 결과 분석을 다시 수행하거나 row-level CSV 분석 설계로 이동한다.

### FAIL

```text
runtime-preflight 실패
candidate execution timeout
candidate result 누락
cleanup 실패
runtime DB path 불일치
result report parse 실패
```

FAIL이면 실행 실패 checkpoint 분석 설계로 이동한다.

## runtime DB 경로 정책

이 정책은 이전 단계와 동일하게 유지한다.

```text
STOM_CLI_DATABASE_DIR=<실제 운용 _database 폴더>
```

현재 개발 검증 예시:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
```

단, 의미적으로 `STOM_V.wt-dev`라는 이름에 의존하지 않는다. 운용 폴더명이 바뀌면 env 값만 새 `_database` 경로로 변경한다.

v2 실행 전 필수 확인:

```text
runtime_profile.setting_db_path
runtime_profile.strategy_db_path
runtime_profile.backtest_db_path
runtime_profile.stock_back_db_path
```

모든 path가 같은 `STOM_CLI_DATABASE_DIR` 아래에 있어야 한다.

## 문서화 산출물

spec:

```text
docs/superpowers/specs/2026-04-23-wide-v1-candidate-result-analysis-and-iteration-loop-v2-design.md
```

예상 plan:

```text
docs/superpowers/plans/2026-04-23-wide-v1-candidate-result-analysis-and-iteration-loop-v2.md
```

실행 후 pilot log:

```text
docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v2.md
```

update log:

```text
docs/update_log/2026-04-23_wide_v1_iteration_loop_v2.md
```

## 성공 기준

이번 설계의 성공 기준:

```text
1. cand003 중심 분석 방향이 명확하다.
2. 후보 5개 전체의 공통/차이 feature를 v2 후보 생성에 반영한다.
3. v2 candidate_count=5 기본 실행 gate가 정의된다.
4. candidate_count=10 확장 조건이 정의된다.
5. runtime DB path 검증 정책이 유지된다.
6. WFO/promote는 최종 검증 단계로 분리된다.
```

## 남은 리스크

1. cand003이 우연히 1등일 수 있다.
   - 후보 5개 공통/차이 분석으로 완화한다.

2. 시가총액 중심 후보가 과적합될 수 있다.
   - 보조 feature 조합 후보를 포함한다.

3. candidate_count=10 확장이 후보 중복만 늘릴 수 있다.
   - 중복 제거와 feature 다양성 기준을 먼저 적용한다.

4. row-level CSV 분석 없이 scalar score만으로는 원인 해석이 부족할 수 있다.
   - v2 결과가 HOLD이면 row-level 분석을 별도 설계로 올린다.

5. best_candidate는 최종 채택이 아니다.
   - 최종 채택 전에는 promote/WFO 검증이 필요하다.

## 다음 단계

이 spec이 승인되면 다음은 `writing-plans`다.

권장 명령:

```text
$writing-plans Wide v1 후보 결과 분석 및 반복 개선 루프 v2 계획 작성
```

실행 결과별 다음 명령:

```text
PASS:
  $brainstorming Wide v1 candidate_count=10 확장 실행 설계

HOLD:
  $brainstorming Wide v1 row-level 후보 차이 분석 설계

FAIL:
  $brainstorming Wide v1 v2 실행 실패 checkpoint 분석 설계
```
