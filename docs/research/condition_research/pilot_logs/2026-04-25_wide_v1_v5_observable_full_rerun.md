# Wide v1 v5 observable full rerun

## 목적

runtime checkpoint와 후보별 관측 로그를 적용한 뒤 `candidate_count=10` full v5를 재실행했다. 이번 실행의 목적은 실제 백테스트 결과 기준으로 actual row-set 대표 10개를 확보할 수 있는지 확인하고, 다음 단계를 promote/WFO 또는 v6 후보 생성 확장 중 하나로 결정하는 것이다.

## 실행 조건

- branch: `feature/wide-v1-v5-observable-full-rerun`
- runtime path: `backtest/temp/wide_v1_v5_observable_full_20260425.json`
- strategy name: `WideV1IterationV5ObservableFull_20260425`
- base buy: `WideV1IterationV2_20260423__cand005`
- sell: `ResearchTest_Tick_S_090000_092800_Wide_20260419`
- period: `20250101-20251231`
- timeframe: `tick`
- engines: `32`
- candidate_count: `10`
- candidate_pool_multiplier: `3`
- candidate_timeout: `900`
- max_consecutive_candidate_failures: `3`

## 실행 결과

- runtime status: `ok`
- phase: `candidates_evaluated`
- elapsed_seconds: `2680.031`
- elapsed_minutes: `44.67`
- executed candidates: `17`
- successful candidates: `17`
- failed candidates: `0`
- failure_policy.aborted: `False`

## Actual row-set selection

- status: `ok`
- row_set_identity_status: `all_distinct`
- requested_count: `10`
- executed_count: `17`
- actual_group_count: `11`
- selected_count: `10`
- duplicate_actual_rowset_count: `6`
- skipped_duplicate_actual_count: `7`

## 선택된 대표 후보

```text
WideV1IterationV5ObservableFull_20260425__cand017
WideV1IterationV5ObservableFull_20260425__cand002
WideV1IterationV5ObservableFull_20260425__cand006
WideV1IterationV5ObservableFull_20260425__cand009
WideV1IterationV5ObservableFull_20260425__cand001
WideV1IterationV5ObservableFull_20260425__cand003
WideV1IterationV5ObservableFull_20260425__cand011
WideV1IterationV5ObservableFull_20260425__cand008
WideV1IterationV5ObservableFull_20260425__cand007
WideV1IterationV5ObservableFull_20260425__cand010
```

## 느린 후보 상위

```text
cand004 | 161.109s | trade_count=36096 | 66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4 and 등락율 > 4.83
cand005 | 157.485s | trade_count=36096 | 66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4 and 체결강도 <= 103.92
cand003 | 157.047s | trade_count=35073 | 66.999 <= 시가총액 < 2_580 and 85.62 <= 체결강도 < 95.04
cand012 | 156.844s | trade_count=36096 | 66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4 and 0.439 <= 체결강도 < 55.015
cand010 | 156.813s | trade_count=35942 | 66.999 <= 시가총액 < 2_580 and 0.61 <= 등락율 < 1.67
```

후보별 시간이 길었던 이유는 조건식 계산 자체보다 후보 조건식이 만든 실제 거래 수가 많았기 때문이다. 특히 `trade_count=36096` 후보들은 기준 CSV와 거의 같은 규모의 거래 집합을 만들었다.

## 중복 actual row-set

다음 후보들은 서로 다른 조건식이지만 동일 actual row-set으로 묶였다.

```text
group_id=11
row_count=36096
members=
- WideV1IterationV5ObservableFull_20260425__cand004
- WideV1IterationV5ObservableFull_20260425__cand005
- WideV1IterationV5ObservableFull_20260425__cand012
- WideV1IterationV5ObservableFull_20260425__cand013
- WideV1IterationV5ObservableFull_20260425__cand014
- WideV1IterationV5ObservableFull_20260425__cand015
- WideV1IterationV5ObservableFull_20260425__cand016
```

중복 그룹이 있었지만 actual group이 11개였고, 대표 10개 확보에 성공했다.

## 결정

- decision: `PROCEED_TO_PROMOTE_WFO_PLAN`
- next command: `$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성`

v6 후보 생성 확장은 현재 필요하지 않다. v6는 actual row-set 대표 10개 확보에 실패했을 때의 fallback인데, 이번 full run은 대표 10개 확보 기준을 통과했다.
