# Wide v1 Score Baseline Reassessment

## 목적

PR #19와 PR #20에서 서로 다른 baseline의 `adjusted_score`를 직접 비교한 문제를 재평가한다.

## 전체 플로우

```text
[wide baseline]
        |
        +--> [cand003] => wide_to_cand003
        |
        +--> [cand005] => wide_to_cand005

[cand003]
        |
        +--> [cand005] => cand003_to_cand005 incremental
```

## 재평가 결과

```text
wide_to_cand003.adjusted_score=10943.034141541459
wide_to_cand003.trade_count=36918
wide_to_cand003.avg_return=-0.653625331816458
wide_to_cand003.total_profit=-4835431554.0

cand003_to_cand005.incremental_adjusted_score=2554.7109523820864
cand003_to_cand005.trade_count=36096
cand003_to_cand005.avg_return=-0.645012189716312
cand003_to_cand005.total_profit=-4665122733.0

wide_to_cand005.reference_adjusted_score=13497.662902097409
wide_to_cand005.trade_count=36096
wide_to_cand005.avg_return=-0.645012189716312
wide_to_cand005.total_profit=-4665122733.0
```

## 판정

```text
decision=PASS_TO_IMPLEMENT_SCORE_REFERENCE
reason=v2 cand005 is better than cand003 when both are compared against the same wide baseline
```

## 해석

- `cand003 -> cand005`의 `2554.7109523820864`는 기존 cand003 점수와 직접 비교할 값이 아니라 추가 개선 점수다.
- 같은 `wide` 기준으로 비교하면 `cand005.reference_adjusted_score=13497.662902097409`로 `cand003.adjusted_score=10943.034141541459`보다 높다.
- 따라서 PR #19의 `HOLD` 근거는 “v2가 나빠졌다”라기보다 “서로 다른 baseline 점수를 직접 비교했다”는 구조 문제로 보는 것이 맞다.
- 다음 구현은 신규 후보 생성이 아니라 `score_reference_csv` 기반 reference scoring과 report/ranking 반영이다.

## 남은 리스크

- wide 기준 reference score가 더 높아도 최종 실전 채택을 의미하지는 않는다.
- 여전히 손실 전략이며, 현재 단계의 목적은 수익 전략 완성이 아니라 자동 개선 루프의 비교 기준 정합성 보강이다.
- 최종 채택 전에는 promote/WFO 검증이 필요하다.
