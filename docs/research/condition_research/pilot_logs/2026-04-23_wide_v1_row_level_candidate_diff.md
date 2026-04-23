# Wide v1 Row-Level Candidate Diff Pilot

## 목적

기존 best 후보 `WideV1RetentionCand5_20260422__cand003`과 v2 best 후보 `WideV1IterationV2_20260423__cand005`의 거래 단위 차이를 비교해 v2 score 하락 원인을 설명한다.

## 전체 플로우

```text
[기존 best cand003 CSV]
        |
        v
[v2 best cand005 CSV]
        |
        v
[trade key 기반 row-level diff]
        |
        v
[common / cand003_only / v2_only 분리]
        |
        v
[손익 요약 및 score 하락 원인 해석]
        |
        v
[HOLD]
```

## 입력

```text
left_label=WideV1RetentionCand5_20260422__cand003
left_csv=C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv
right_label=WideV1IterationV2_20260423__cand005
right_csv=C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv
```

## trade set counts

```text
left=36918
right=36096
common=32575
left_only=4343
right_only=3521
```

## summaries

```text
left.trade_count=36918
left.avg_return=-0.653625331816458
left.total_profit=-4835431554.0
right.trade_count=36096
right.avg_return=-0.645012189716312
right.total_profit=-4665122733.0
common.trade_count=32575
common.avg_return=-0.6435475057559479
common.total_profit=-4200336872.0
common_avg_return_delta=0.0
common_total_profit_delta=0.0
left_only.trade_count=4343
left_only.avg_return=-0.7292148284595902
left_only.total_profit=-635094682.0
right_only.trade_count=3521
right_only.avg_return=-0.6585629082646975
right_only.total_profit=-464785861.0
```

## 해석

- cand003에만 있던 거래인 `left_only`는 4,343건이고 총손익은 `-635,094,682원`이다.
- v2 cand005에만 있던 거래인 `right_only`는 3,521건이고 총손익은 `-464,785,861원`이다.
- 양쪽 공통 거래의 평균수익률과 총손익 delta는 `0.0`으로, 공통 거래 자체의 성능 악화는 확인되지 않았다.
- right_only도 손실 구간이지만 left_only보다 더 나쁜 손실 구간이라고 보기 어렵다.
- 따라서 row-level set 분리는 성공했지만, 이 요약만으로 v2 score 하락 원인을 충분히 설명하지 못한다.
- 다음 단계는 key 정합성 보강 또는 더 세밀한 row-level drill-down이 필요하다.

## decision

```text
decision=HOLD
reason=row-level sets were built but score decline cause is not conclusive
next_command=$brainstorming Wide v1 row-level key 정합성 보강 설계
```

## 남은 리스크

- 현재 trade key는 `종목명`, `매수시간`, `매수가` 중심이다. 매도시간과 매도가를 포함한 더 강한 key 정합성 검토가 필요하다.
- cand003_only/right_only 요약만으로 adjusted_score 하락을 충분히 설명하지 못했다.
- feature bucket별 세부 분석과 top loss/profit drill-down을 더 정교하게 문서화해야 한다.
- 최종 채택 전에는 promote/WFO 검증이 필요하다.
