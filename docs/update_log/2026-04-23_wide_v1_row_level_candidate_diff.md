# 2026-04-23 Wide v1 Row-Level Candidate Diff

## 목적

cand003과 v2 cand005의 거래 단위 차이를 분석해 v2 score 하락 원인을 설명하려 했다.

## 결과 요약

```text
common=32575
left_only=4343
right_only=3521
common_avg_return_delta=0.0
common_total_profit_delta=0.0
left_only.total_profit=-635094682.0
right_only.total_profit=-464785861.0
decision=HOLD
```

## 판정

```text
decision=HOLD
reason=row-level sets were built but score decline cause is not conclusive
next_command=$brainstorming Wide v1 row-level key 정합성 보강 설계
```

## 해석

```text
row-level set 분리는 성공했다.
하지만 common 거래 성능 차이는 0이고, right_only 손실이 left_only보다 더 나쁘다는 증거도 부족하다.
따라서 현재 row-level 요약만으로는 v2 score 하락 원인을 충분히 설명하지 못한다.
```

## 다음 단계

```text
$brainstorming Wide v1 row-level key 정합성 보강 설계
```
