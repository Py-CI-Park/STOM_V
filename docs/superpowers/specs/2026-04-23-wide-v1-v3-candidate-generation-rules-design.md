# Wide v1 v3 후보 생성 규칙 설계

## 1. 목적

이번 설계의 목적은 Wide v1 반복 개선 루프에서 v2 best 후보 `WideV1IterationV2_20260423__cand005`를 다음 기준 후보로 사용해 v3 후보 생성 규칙을 정의하는 것이다.

PR #21에서 비교 기준이 정리되었다.

```text
wide_to_cand003.adjusted_score=10943.034141541459
cand003_to_cand005.incremental_adjusted_score=2554.7109523820864
wide_to_cand005.reference_adjusted_score=13497.662902097409
```

따라서 `cand005`는 기존 `cand003`보다 나쁜 후보가 아니다. 같은 wide baseline 기준으로는 더 높은 reference score를 기록했다. 이제 다음 단계는 `cand005`를 새로운 reference best로 두고, v3 후보를 생성하는 것이다.

## 2. 전체 개발 흐름에서 현재 위치

```text
[0. Wide baseline 조건식]
        |
        v
[1. candidate_count=5 Retention-Aware 실행]
        |
        v
[2. cand003 best 확인]
        |
        v
[3. cand003 중심 Iteration Loop v2]
        |
        v
[4. cand005 best 확인]
        |
        v
[5. score_reference_csv로 같은 기준 비교 보강]
        |
        v
[6. 이번 설계: v3 후보 생성 규칙]
        |
        v
[7. v3 candidate_count=10 실행]
        |
        v
[8. 결과 분석 / 반복 개선 v4 여부 판단]
        |
        v
[9. 최종 promote/WFO 검증]
```

이번 단계는 최종 전략 채택이 아니다. 목표는 백테스트 결과를 바탕으로 조건식 후보를 더 체계적으로 생성하고, 같은 기준선에서 반복 비교할 수 있게 하는 것이다.

## 3. 현재 기준 후보

### 3.1 wide baseline

```text
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
period=20250101~20251231
time=090000~092800
avg_time=30
engines=32
baseline_trade_count=40937
```

### 3.2 v1 best: cand003

```text
strategy=WideV1RetentionCand5_20260422__cand003
expression=66.999 <= 시가총액 < 2_580
trade_count=36918
wide_reference_adjusted_score=10943.034141541459
```

### 3.3 v2 best: cand005

```text
strategy=WideV1IterationV2_20260423__cand005
expression=66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4
trade_count=36096
wide_reference_adjusted_score=13497.662902097409
```

해석:

```text
cand005는 cand003에 당일거래대금 중간 구간을 추가한 후보다.
거래 수는 36918 -> 36096으로 줄었고, wide 기준 score는 개선됐다.
따라서 v3는 cand005를 기준 best로 삼는 것이 타당하다.
```

## 4. 설계 질문

v3 후보 생성의 핵심 질문은 다음이다.

```text
1. cand005 조건을 더 조일 것인가?
2. cand005 조건을 조금 완화해 누락된 좋은 거래를 회복할 것인가?
3. 둘 다 후보군으로 만들고, wide reference score로 같은 기준에서 비교할 것인가?
```

## 5. 접근안

### A. Tighten-only 방식

cand005 조건에 추가 필터를 더 붙인다.

예:

```text
66.999 <= 시가총액 < 2_580
and 1805.7 <= 당일거래대금 < 3654.4
and 체결강도 구간
```

장점:

```text
손실 거래를 더 줄일 가능성이 있다.
구현이 단순하다.
```

단점:

```text
거래 수가 계속 줄어 과최적화 위험이 커진다.
조건식이 타이트해지면 장기 안정성이 약해질 수 있다.
```

판정:

```text
단독으로는 비추천.
```

### B. Relax-and-repair 방식

cand005에서 추가된 `당일거래대금` 구간을 조금 넓히거나 인접 구간을 다시 열어 좋은 거래를 회복한다.

예:

```text
66.999 <= 시가총액 < 2_580
and 1500 <= 당일거래대금 < 3654.4
```

장점:

```text
v2에서 과하게 제거된 거래가 있다면 회복 가능하다.
거래 수 유지에 유리하다.
```

단점:

```text
cand005의 개선 포인트였던 손실 제거 효과가 약해질 수 있다.
단순 완화는 wide baseline으로 회귀할 수 있다.
```

판정:

```text
보조 후보군으로 필요하다.
```

### C. Dual-track v3 후보군 방식

v3 후보군을 두 family로 나눈다.

```text
Family 1: cand005 tighten
  cand005 조건을 유지하고 1개 조건을 추가한다.

Family 2: cand005 repair
  cand005의 당일거래대금 구간을 인접 구간으로 확장/이동한다.

공통 ranking:
  score_reference_csv=wide baseline으로 reference_adjusted_score 비교
```

장점:

```text
추가 손실 제거와 좋은 거래 회복을 동시에 탐색한다.
모든 후보를 같은 wide 기준으로 비교하므로 PR #21에서 고친 비교 기준을 유지한다.
candidate_count=10과 잘 맞는다.
```

단점:

```text
후보 생성 규칙이 v2보다 복잡하다.
중복 후보와 retention 관리가 더 중요하다.
```

판정:

```text
추천안.
```

## 6. 추천 설계

v3는 `Dual-track candidate pool`로 설계한다.

```text
v3_base_expression:
  66.999 <= 시가총액 < 2_580
  and 1805.7 <= 당일거래대금 < 3654.4

score_reference_csv:
  wide baseline CSV

candidate_count:
  10
```

v3 후보군은 아래 네 종류로 구성한다.

```text
1. v3_tighten_secondary
   cand005 조건 + 체결강도/등락율/시분초 등 보조 feature 1개 추가

2. v3_repair_trade_amount
   당일거래대금 구간을 좌우로 넓히거나 인접 구간으로 이동

3. v3_replace_secondary
   cand005의 당일거래대금 대신 다른 보조 feature를 붙여 비교

4. v3_control_keep_best
   cand005 원본 조건을 control 후보로 유지
```

## 7. 후보 생성 규칙

### 7.1 v3_tighten_secondary

입력:

```text
best_expression=66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4
secondary_features=체결강도, 등락율, 시분초, 회전율, 전일동시간비
```

생성:

```text
best_expression and <secondary_range>
```

예:

```text
66.999 <= 시가총액 < 2_580
and 1805.7 <= 당일거래대금 < 3654.4
and 0.039 <= 체결강도 < 54.89
```

제한:

```text
조건 추가는 한 번에 1개만 한다.
3중 조건까지만 허용한다.
estimated_retention은 기본 0.4 이상이어야 한다.
```

### 7.2 v3_repair_trade_amount

당일거래대금 구간을 너무 타이트하게 보지 않기 위해 좌우 변형을 만든다.

기준:

```text
1805.7 <= 당일거래대금 < 3654.4
```

생성 예:

```text
1500 <= 당일거래대금 < 3654.4
1805.7 <= 당일거래대금 < 4200
1500 <= 당일거래대금 < 4200
178.999 <= 당일거래대금 < 1805.7
```

제한:

```text
repair 후보도 항상 시가총액 best 구간은 유지한다.
너무 넓어져 wide baseline과 거의 같아지는 후보는 제외한다.
```

### 7.3 v3_replace_secondary

cand005의 `당일거래대금` 보조 조건이 정말 최선인지 검증하기 위해 같은 시가총액 구간에 다른 보조 feature를 붙인다.

예:

```text
66.999 <= 시가총액 < 2_580 and 0.039 <= 체결강도 < 54.89
66.999 <= 시가총액 < 2_580 and 15.894 <= 등락율 < 25
66.999 <= 시가총액 < 2_580 and 90029.999 <= 시분초 < 90054
```

제한:

```text
v2에서 이미 실행한 후보와 완전히 같은 expression은 중복 제거한다.
단, score_reference_csv 기준 report에는 비교 대상으로 다시 나타날 수 있다.
```

### 7.4 v3_control_keep_best

cand005 원본을 후보군에 포함한다.

목적:

```text
v3 후보들이 cand005를 실제로 넘는지 같은 실행 결과 안에서 비교한다.
```

단, 이미 strategy.db에 cand005가 존재하므로 구현에서는 다음 둘 중 하나를 선택해야 한다.

```text
1. control 후보는 백테스트 재실행 없이 기존 CSV/reference score를 report에 포함
2. control 후보도 새 이름으로 재실행
```

추천은 1이다. 이미 full-year tick 결과가 있고, 불필요한 재실행을 줄인다.

## 8. ranking 기준

v3 ranking은 반드시 `score_reference_csv` 기준을 사용한다.

```text
primary sort:
  reference_promotion.passed=True 우선
  reference_adjusted_score desc
  trade_count_retention desc
  date_concentration asc
  symbol_concentration asc
```

기존 incremental score는 보조 정보로만 사용한다.

```text
incremental_score:
  cand005 대비 추가 개선 여부

reference_score:
  wide baseline 대비 누적 개선 여부
```

## 9. CLI 설계

새 mode 이름은 `best_feature_mix_v3`가 적절하다.

예상 CLI:

```powershell
python -m cli.main discovery research WideV1IterationV3_20260423 `
  --input C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv `
  --score-reference-csv C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv `
  --base-buy-strategy WideV1IterationV2_20260423__cand005 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --betting 20 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --run-candidates `
  --candidate-count 10 `
  --candidate-timeout 900 `
  --iteration-v2-mode best_feature_mix_v3 `
  --iteration-v2-best-candidate WideV1IterationV2_20260423__cand005 `
  --iteration-v2-best-expression "66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4" `
  --iteration-v2-primary-feature B_시가총액 `
  --iteration-v2-secondary-features B_체결강도,B_등락율,B_당일거래대금,B_시분초,B_회전율,B_전일동시간비
```

이름은 기존 필드를 재사용할 수 있지만, 구현 계획에서는 `iteration_v3_mode`로 분리할지도 검토한다. 장기적으로는 `iteration_mode`로 일반화하는 것이 좋지만 이번 PR에서는 범위를 줄이기 위해 기존 v2 wiring을 확장하는 편이 낫다.

## 10. 데이터 흐름

```text
[cand005 CSV]
        |
        v
[CSV 분석]
        |
        v
[v3 후보 pool 생성]
        |
        +--> tighten_secondary
        +--> repair_trade_amount
        +--> replace_secondary
        +--> control_keep_best
        |
        v
[retention-aware selection: candidate_count=10]
        |
        v
[후보별 백테스트]
        |
        v
[incremental comparison: cand005 -> candidate]
        |
        v
[reference comparison: wide -> candidate]
        |
        v
[reference-adjusted ranking]
        |
        v
[best v3 후보 선정 또는 HOLD]
```

## 11. 성공 기준

```text
1. v3 후보 10개 pool을 생성할 수 있다.
2. 모든 후보는 cand005 또는 wide reference 기준을 report에서 명확히 구분한다.
3. best 후보는 reference_adjusted_score 기준으로 선정된다.
4. cand005 control보다 높은 후보가 있으면 PASS_TO_V3_EXECUTION_RESULT_ANALYSIS.
5. cand005 control을 넘지 못하면 HOLD_FOR_CANDIDATE_RULE_REVIEW.
```

## 12. 테스트 전략

추가할 테스트:

```text
1. v3 mode가 best expression의 2개 조건을 parsing한다.
2. tighten_secondary 후보가 best expression + 1개 조건으로 생성된다.
3. repair_trade_amount 후보가 당일거래대금 범위를 좌우로 변형한다.
4. replace_secondary 후보가 시가총액 + 다른 보조 feature 조건을 생성한다.
5. control_keep_best가 candidate pool metadata에 포함된다.
6. duplicate expression은 제거된다.
7. run_research_iteration이 best_feature_mix_v3 mode를 호출한다.
8. report가 v3 candidate type counts를 표시한다.
```

## 13. 남은 리스크

- candidate_count=10은 실행 시간이 가능해 보이지만, 후보별 조건식 저장/삭제 cleanup이 더 중요해진다.
- 조건이 3개로 늘면 과최적화 위험이 커진다.
- reference score가 높아도 전략 자체가 손실 전략이라는 사실은 변하지 않는다.
- v3 best도 최종 채택이 아니며 promote/WFO 검증이 필요하다.
- cand005 control을 재실행하지 않고 기존 CSV를 쓰면 동일 조건 재현성 검증은 생략된다.

## 14. 다음 단계

설계가 적절하다면 다음 단계는 구현 계획 작성이다.

```text
$writing-plans Wide v1 v3 후보 생성 규칙 구현 계획 작성
```
