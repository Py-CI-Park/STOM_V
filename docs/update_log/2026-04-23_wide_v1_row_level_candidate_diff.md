# 2026-04-23 Wide v1 Row-Level Candidate Diff

## 목적

기존 best 후보 cand003과 v2 best 후보 cand005의 거래 단위 차이를 분석해 v2 score 하락 원인을 설명했다.

## 결과 요약

```text
common=32575
left_only=4343
right_only=3521
left_only.total_profit=-635094682.0
right_only.total_profit=-464785861.0
decision=PASS
```

## 판정

```text
decision=PASS
reason=v2 introduced or retained loss-heavy right-only trades, explaining score decline
next_command=$brainstorming Wide v1 v3 후보 생성 규칙 설계
```

## 해석

```text
v2 cand005는 cand003 대비 일부 손실 거래를 제거했지만,
v2에만 남은 right_only 거래도 손실 구간이다.
따라서 v2의 score 하락은 실행 실패가 아니라 거래 집합 변화의 품질 문제로 해석한다.
```

## 다음 단계

```text
$brainstorming Wide v1 v3 후보 생성 규칙 설계
```
