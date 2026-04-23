# 2026-04-23 Wide v1 Iteration Loop v2

## 목적

`cand003` 중심 후보 분석과 후보 5개 공통/차이 패턴을 반영한 v2 후보 생성/실행 결과를 기록했다.

## 결과 요약

```text
status=ok
phase=candidates_evaluated
candidate_count_observed=5
best_candidate=WideV1IterationV2_20260423__cand005
best_adjusted_score=2554.7109523820864
baseline_adjusted_score=10943.034141541459
best_trade_count=36096
best_trade_count_retention=0.9777344384852917
promotion_passed=True
cleanup_failed_count=0
decision=HOLD
```

## 판정

```text
decision=HOLD
reason=v2 executed but did not improve over cand003 baseline or needs row-level analysis.
next_command=$brainstorming Wide v1 row-level 후보 차이 분석 설계
```

## 해석

```text
v2 candidate_count=5 실행 자체는 성공했다.
하지만 기존 cand003의 adjusted_score를 넘지 못했다.
따라서 candidate_count=10 확장으로 바로 가지 않는다.
```

## 남은 리스크

- v2 후보들이 왜 기존 cand003보다 낮은 score를 냈는지 row-level로 확인해야 한다.
- 한글 feature 인자/JSON 표시에서 mojibake가 있어 리포트 품질 개선 여지가 있다.
- best_candidate는 최종 채택이 아니며 promote/WFO 검증이 필요하다.

## 다음 단계

```text
$brainstorming Wide v1 row-level 후보 차이 분석 설계
```
