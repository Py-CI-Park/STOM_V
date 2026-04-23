# Wide v1 Score Baseline Comparability 및 Key Diagnostics 설계

## 1. 목적

이번 설계의 목적은 Wide v1 반복 개선 루프에서 후보 점수를 같은 기준선으로 비교하도록 만드는 것이다.

PR #19와 PR #20의 흐름에서는 다음 두 점수가 직접 비교되었다.

```text
wide -> cand003 adjusted_score = 10943.034141541459
cand003 -> cand005 adjusted_score = 2554.7109523820864
```

하지만 이 두 점수는 기준선이 다르다.

```text
10943.0341 = wide baseline 대비 cand003의 개선 점수
2554.7109  = cand003 대비 cand005의 추가 개선 점수
```

따라서 `2554 < 10943`이라는 이유로 v2가 실패했다고 판단하면 안 된다. 같은 wide baseline 기준으로 cand005를 다시 비교하면 다음과 같다.

```text
wide -> cand003 adjusted_score = 10943.034141541459
cand003 -> cand005 incremental adjusted_score = 2554.7109523820864
wide -> cand005 reference adjusted_score = 13497.662902097409
```

즉, 현재 근거로는 v2 cand005가 기존 cand003보다 나쁜 것이 아니라, wide baseline 기준으로는 더 좋아졌다고 보는 것이 더 타당하다.

## 2. 전체 개발 흐름에서의 위치

```text
[0. Wide baseline CSV]
        |
        v
[1. Retention-Aware candidate_count=5]
        |
        v
[2. best_candidate=cand003]
        |
        v
[3. Iteration Loop v2: cand003 -> cand005]
        |
        v
[4. PR #20 row-level diff: HOLD]
        |
        v
[5. 이번 설계: score baseline comparability 보강]
        |
        v
[6. v2 결과 재판정]
        |
        v
[7. v3 후보 생성 또는 candidate_count=10 확장]
        |
        v
[8. 최종 promote/WFO 검증]
```

이번 단계는 자동 조건식 연구 방향을 바꾸는 작업이 아니다. 기존 목표인 `백테스트 결과 분석 -> 조건식 개선 -> 다시 백테스트 -> 결과 비교` 루프에서, 결과 비교 기준을 바로잡는 작업이다.

## 3. 확인된 사실

### 3.1 row-level key 중복도

cand003와 v2 cand005 CSV에서 현재 key와 강화 key를 비교했다.

```text
current key:
  종목명 + 매수시간 + 매수가

strong key:
  종목명 + 매수시간 + 매수가 + 매도시간 + 매도가

full key:
  종목명 + 매수시간 + 매수가 + 매도시간 + 매도가 + 보유시간 + 매도조건
```

진단 결과:

```text
current key:
  left unique=36918 duplicate_rows=0
  right unique=36096 duplicate_rows=0
  common=32575 left_only=4343 right_only=3521

with sell identity:
  left unique=36918 duplicate_rows=0
  right unique=36096 duplicate_rows=0
  common=32575 left_only=4343 right_only=3521

with hold and sell condition:
  left unique=36918 duplicate_rows=0
  right unique=36096 duplicate_rows=0
  common=32575 left_only=4343 right_only=3521
```

해석:

```text
현재 CSV 기준으로 key 중복 문제는 관찰되지 않았다.
매도시간/매도가/보유시간/매도조건을 추가해도 row-level 분리 결과는 바뀌지 않았다.
따라서 현재 HOLD의 핵심 원인은 key 불일치라기보다 score baseline 비교 기준 문제다.
```

### 3.2 score baseline 재계산

같은 wide baseline 기준으로 재계산한 결과:

```text
wide -> cand003:
  trade_count: 40937 -> 36918
  avg_return: -0.6782570779490436 -> -0.653625331816458
  total_profit: -5564960005.0 -> -4835431554.0
  adjusted_score: 10943.034141541459

cand003 -> cand005:
  trade_count: 36918 -> 36096
  avg_return: -0.653625331816458 -> -0.645012189716312
  total_profit: -4835431554.0 -> -4665122733.0
  incremental_adjusted_score: 2554.7109523820864

wide -> cand005:
  trade_count: 40937 -> 36096
  avg_return: -0.6782570779490436 -> -0.645012189716312
  total_profit: -5564960005.0 -> -4665122733.0
  reference_adjusted_score: 13497.662902097409
```

해석:

```text
cand005는 cand003보다 trade_count가 줄었지만 평균수익률과 총손익은 개선됐다.
wide 기준 adjusted_score도 cand003보다 cand005가 더 높다.
따라서 v2 결과는 실패가 아니라 재판정이 필요하다.
```

## 4. 설계 원칙

1. 서로 다른 baseline에서 계산한 `adjusted_score`를 직접 비교하지 않는다.
2. 반복 개선 루프에서는 항상 두 점수를 구분한다.
   - `incremental_score`: 직전 best 후보 대비 추가 개선 점수
   - `reference_score`: root wide baseline 대비 누적 개선 점수
3. best 후보 ranking은 가능한 경우 `reference_adjusted_score`를 우선 사용한다.
4. row-level key 진단은 계속 유지하되, key가 원인이 아닌 경우 score decomposition으로 넘어간다.
5. 신규 백테스트를 실행하지 않고 기존 CSV만으로 재판정 가능한 범위를 먼저 처리한다.

## 5. 권장 접근안

### A. key 정합성만 보강

장점:

```text
PR #20의 다음 명령과 가장 직접적으로 연결된다.
row-level diff의 신뢰도를 조금 높인다.
```

단점:

```text
이미 key 강화 진단에서 counts가 변하지 않았다.
핵심 문제인 baseline score 비교 오류를 해결하지 못한다.
```

판정: 단독 진행은 비추천.

### B. score baseline comparability만 보강

장점:

```text
현재 발견된 핵심 오류를 직접 해결한다.
v2 결과를 즉시 재판정할 수 있다.
```

단점:

```text
row-level diff 신뢰도 진단이 report에 충분히 남지 않을 수 있다.
```

판정: 핵심 구현으로 적합.

### C. score baseline comparability + key diagnostics

장점:

```text
점수 비교 오류를 해결하면서 row-level key 신뢰도도 자동 보고한다.
앞으로 v3/v4 후보에서도 같은 실수를 방지한다.
```

단점:

```text
작업 범위가 A/B보다 조금 넓다.
```

판정: 추천안.

## 6. 추천 설계

추천안은 C다.

`ResearchLoopConfig`에 root/reference baseline CSV 개념을 추가하고, 후보 결과마다 기존 comparison 외에 reference comparison을 선택적으로 계산한다.

```text
baseline_csv:
  현재 반복의 기준 후보 CSV
  예: cand003 CSV

score_reference_csv:
  전체 연구 루프의 root 기준 CSV
  예: Wide baseline CSV
```

후보별 결과는 다음 구조를 갖는다.

```text
comparison:
  current baseline 대비 비교
  예: cand003 -> cand005

promotion:
  comparison 기반 incremental promotion

reference_comparison:
  score_reference_csv 대비 비교
  예: wide -> cand005

reference_promotion:
  reference_comparison 기반 cumulative promotion

rank_score:
  reference_promotion이 있으면 reference_adjusted_score 우선
  없으면 기존 adjusted_score 유지
```

## 7. 데이터 흐름

```text
[score_reference_csv: wide baseline]
        |
        |---- compare -> [cand003] => reference_score(cand003)=10943
        |
        |---- compare -> [cand005] => reference_score(cand005)=13497

[baseline_csv: cand003]
        |
        |---- compare -> [cand005] => incremental_score=2554
```

report에서는 반드시 두 점수를 분리해서 표시한다.

```text
incremental_adjusted_score=2554.7109523820864
reference_adjusted_score=13497.662902097409
previous_best_reference_adjusted_score=10943.034141541459
reference_score_delta=2554.62876055595
```

## 8. 구현 범위

### In scope

- `ResearchLoopConfig`에 `score_reference_csv` 또는 같은 의미의 옵션 추가.
- 후보 backtest 후 `reference_comparison` / `reference_promotion` 계산.
- `_rank_candidate_results()`가 reference score를 우선 사용하도록 보강.
- report에 score 기준선과 비교 가능성 경고 추가.
- row-level key diagnostics helper 추가 또는 기존 rowdiff helper에 진단 출력 추가.
- PR #19/#20 결과 재판정 문서 추가.

### Out of scope

- 신규 조건식 생성.
- 신규 백테스트 실행.
- candidate_count=10 실행.
- promote/WFO 실행.
- GUI 수동 백테스트 재실행.
- 기존 scoring weight 재설계.

## 9. CLI 옵션 설계

권장 옵션:

```text
--score-reference-csv <path>
```

의미:

```text
현재 iteration baseline과 별개로, 모든 후보를 누적 비교할 root baseline CSV를 지정한다.
```

사용 예:

```powershell
python -m cli.main discovery research `
  --input C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv `
  --score-reference-csv C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv `
  --iteration-v2-mode best_feature_mix
```

## 10. report 설계

report에 다음 섹션을 추가한다.

```text
## Score Baseline Comparability

current_baseline_csv=...
score_reference_csv=...
comparison_scope=incremental
reference_scope=cumulative

incremental_adjusted_score=...
reference_adjusted_score=...
previous_best_reference_adjusted_score=...
reference_score_delta=...

warning:
  adjusted_score values are directly comparable only when score_reference_csv is identical.
```

row-level key diagnostics는 다음처럼 표시한다.

```text
## Row-Level Key Diagnostics

key_variant=current_buy_identity
left_duplicate_rows=0
right_duplicate_rows=0
common=32575
left_only=4343
right_only=3521

key_variant=with_sell_identity
common=32575
left_only=4343
right_only=3521

decision:
  key drift not observed
```

## 11. 테스트 전략

추가할 테스트:

```text
1. score_reference_csv가 없으면 기존 ranking 동작 유지
2. score_reference_csv가 있으면 reference_promotion.adjusted_score로 ranking
3. incremental_score와 reference_score를 report에서 분리 출력
4. 서로 다른 baseline 점수를 직접 비교하지 말라는 warning 출력
5. key diagnostics가 duplicate_rows와 key variant별 counts를 반환
6. key variant 강화 결과가 같을 때 key_drift_observed=False
```

## 12. 성공 기준

```text
score_reference_csv를 지정하면 cand005가 wide 기준 누적 score로 재평가된다.
report가 incremental_score와 reference_score를 명확히 구분한다.
v2 cand005 결과가 기존 cand003보다 개선됐는지 같은 기준으로 판정할 수 있다.
row-level key가 원인인지 아닌지 report에서 확인 가능하다.
기존 discovery research 동작은 score_reference_csv 미지정 시 그대로 유지된다.
```

## 13. 남은 리스크

- reference score가 높아도 최종 실전 채택은 아니다. 최종 채택 전 promote/WFO는 여전히 필요하다.
- score weight 자체가 현재 연구 목적에 완전히 최적인지는 별도 검토 대상이다.
- cand005가 wide 기준으로 개선되어도 손실 전략이라는 사실은 변하지 않는다. 현재 루프의 목표는 수익 전략 완성이 아니라 조건식 개선 자동화 검증이다.
- score_reference_csv가 잘못 지정되면 ranking이 다시 왜곡될 수 있으므로 report에 경로와 기준 이름을 반드시 남겨야 한다.

## 14. 다음 단계

설계가 적절하다면 다음 명령은 아래가 맞다.

```text
$writing-plans Wide v1 score baseline comparability 및 key diagnostics 구현 계획 작성
```
