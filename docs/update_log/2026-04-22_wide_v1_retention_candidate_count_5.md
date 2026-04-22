# 2026-04-22 Wide v1 Retention-Aware Candidate Count 5

## 목적

Wide v1 CLI baseline PASS 이후 Retention-Aware 후보 5개 자동 백테스트를 재개하고 실행 결과를 문서화했다.

## 전체 플로우

```text
[완료] Wide v1 CLI baseline GUI compare PASS
        |
        v
[이번 작업] runtime DB path 검증
        |
        v
[이번 작업] candidate_count=5 실행
        |
        v
[이번 작업] ranking / cleanup 확인
        |
        v
[판정] PASS_FOR_EXECUTION
```

## 결과 요약

```text
status=ok
phase=candidates_evaluated
candidate_count_observed=5
retention_selection.selected_count=5
retention_selection.fallback_count=0
best_candidate=WideV1RetentionCand5_20260422__cand003
best_candidate.trade_count=36918
best_candidate.trade_count_retention=0.9018247551115128
best_candidate.promotion_score=10943.034141541459
best_candidate.adjusted_score=10943.034141541459
cleanup.deleted_count=4
cleanup.kept_count=1
cleanup.failed_count=0
decision=PASS_FOR_EXECUTION
```

## 판정

```text
decision=PASS_FOR_EXECUTION
reason=candidate_count=5 executed and ranking data is present.
next_command=$brainstorming Wide v1 후보 결과 분석 및 반복 개선 루프 v2 설계
```

## 남은 리스크

- best candidate는 최종 채택이 아니다.
- 최종 채택 전에는 반복 개선 루프 v2, promote 또는 WFO 검증이 필요하다.
- 후보 표현식의 한글 컬럼명이 일부 CLI JSON에서 mojibake로 보인다.
- runtime JSON/CSV/graph 산출물은 Git에 포함하지 않는다.

## 다음 단계

```text
$brainstorming Wide v1 후보 결과 분석 및 반복 개선 루프 v2 설계
```
