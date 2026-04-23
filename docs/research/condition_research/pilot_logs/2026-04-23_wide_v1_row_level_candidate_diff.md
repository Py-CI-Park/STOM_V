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
[PASS]
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
- v2 cand005는 cand003 대비 일부 손실 거래를 제거했지만, v2에만 남은 right_only 거래도 손실 구간이다.
- 즉 v2 조합 조건은 실행 가능하지만, cand003 대비 손실 제거 효율이 충분하지 않았고 adjusted_score 하락을 설명할 수 있다.
- cand003에서 제거된 거래가 전부 나쁜 거래는 아니며, v2가 추가로 남긴 거래도 손실 구간이므로 candidate_count=10으로 바로 확장하지 않는다.

## decision

```text
decision=PASS
reason=v2 introduced or retained loss-heavy right-only trades, explaining score decline
next_command=$brainstorming Wide v1 v3 후보 생성 규칙 설계
```

## 남은 리스크

- trade key는 `종목명`, `매수시간`, `매수가` 중심으로 만들어졌으므로 완전한 체결 단위 동일성은 추가 검증 여지가 있다.
- row-level 분석은 v2 score 하락의 큰 방향을 설명하지만, v3 후보 생성 규칙은 별도 설계가 필요하다.
- 최종 채택 전에는 promote/WFO 검증이 필요하다.
