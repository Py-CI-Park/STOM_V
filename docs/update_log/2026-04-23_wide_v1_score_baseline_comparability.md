# 2026-04-23 Wide v1 Score Baseline Comparability

## 요약

v2 cand005는 cand003보다 낮은 점수로 실패한 것이 아니라, 서로 다른 baseline 점수를 직접 비교해 잘못 `HOLD`로 해석됐을 가능성이 높다.

```text
wide_to_cand003.adjusted_score=10943.034141541459
cand003_to_cand005.incremental_adjusted_score=2554.7109523820864
wide_to_cand005.reference_adjusted_score=13497.662902097409
```

## 현재 판단

```text
decision=PASS_TO_IMPLEMENT_SCORE_REFERENCE
reason=same-baseline comparison shows cand005 > cand003
```

## 다음 단계

```text
$subagent-driven-development Wide v1 score baseline comparability 및 key diagnostics 구현
```
