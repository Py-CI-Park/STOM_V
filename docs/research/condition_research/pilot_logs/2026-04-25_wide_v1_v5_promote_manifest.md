# Wide v1 v5 promote manifest

## Decision

- decision=PRIMARY_CAND017_FOR_WFO
- final_buy_strategy=WideV1Final_B_20260425
- base_buy_strategy=WideV1IterationV2_20260423__cand005
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
- source_runtime=backtest\temp\wide_v1_v5_observable_full_20260425.json

## Actual row-set selection

- requested_count=10
- selected_count=10
- actual_group_count=11
- duplicate_actual_rowset_count=6
- skipped_duplicate_actual_count=7

## Selected representatives

| order | strategy | expression | csv | trades | seconds |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | `WideV1IterationV5ObservableFull_20260425__cand017` | `66.999 <= 시가총액 < 2_580 and 등락율 > 4.83` | `backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand017_20260425125216.csv` | 27601 | 142.672 |
| 2 | `WideV1IterationV5ObservableFull_20260425__cand002` | `66.999 <= 시가총액 < 2_580 and 체결강도 <= 103.92` | `backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand002_20260425121323.csv` | 29572 | 143.813 |
| 3 | `WideV1IterationV5ObservableFull_20260425__cand006` | `66.999 <= 시가총액 < 2_580 and 당일거래대금 <= 9_554` | `backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand006_20260425122347.csv` | 29792 | 148.156 |
| 4 | `WideV1IterationV5ObservableFull_20260425__cand009` | `66.999 <= 시가총액 < 2_580 and 15.18 <= 등락율 < 25` | `backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand009_20260425123135.csv` | 34091 | 154.078 |
| 5 | `WideV1IterationV5ObservableFull_20260425__cand001` | `66.999 <= 시가총액 < 2_580 and 178.999 <= 당일거래대금 < 1765.5` | `backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand001_20260425121059.csv` | 35286 | 155.328 |
| 6 | `WideV1IterationV5ObservableFull_20260425__cand003` | `66.999 <= 시가총액 < 2_580 and 85.62 <= 체결강도 < 95.04` | `backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand003_20260425121600.csv` | 35073 | 157.047 |
| 7 | `WideV1IterationV5ObservableFull_20260425__cand011` | `66.999 <= 시가총액 < 2_580 and 0.439 <= 체결강도 < 55.015` | `backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand011_20260425123649.csv` | 35589 | 156.546 |
| 8 | `WideV1IterationV5ObservableFull_20260425__cand008` | `66.999 <= 시가총액 < 2_580 and 6.23 <= 등락율 < 8.03` | `backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand008_20260425122900.csv` | 35700 | 155.891 |
| 9 | `WideV1IterationV5ObservableFull_20260425__cand007` | `66.999 <= 시가총액 < 2_580 and 1765.5 <= 당일거래대금 < 3_901` | `backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand007_20260425122624.csv` | 35898 | 156.531 |
| 10 | `WideV1IterationV5ObservableFull_20260425__cand010` | `66.999 <= 시가총액 < 2_580 and 0.61 <= 등락율 < 1.67` | `backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand010_20260425123412.csv` | 35942 | 156.813 |
