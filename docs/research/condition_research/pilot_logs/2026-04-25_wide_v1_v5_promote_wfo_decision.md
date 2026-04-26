# Wide v1 v5 promote WFO decision

## Decision

- decision=PROCEED_TO_MVP_FREEZE
- next_command=$writing-plans Wide v1 MVP freeze 및 운영 재현 문서 작성
- final_buy_strategy=WideV1Final_B_20260425
- primary_candidate=WideV1IterationV5ObservableFull_20260425__cand017
- primary_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
- source_csv=backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand017_20260425125216.csv

## WFO summary

- status=ok
- round_count=8
- success_rate=1.0
- mean_oos_metric=0.5762499999999999
- mean_trade_count=2131.75
- zero_trade_rounds=0

## Balanced evaluation

- passed=True
- reasons=
- criteria={"min_rounds":2,"min_success_rate":0.6,"min_mean_oos_metric":0.0,"min_avg_trade_count":50.0,"preset":"balanced"}

## Conservative comparison

- passed=True
- reasons=
- criteria={"min_rounds":3,"min_success_rate":0.8,"min_mean_oos_metric":0.1,"min_avg_trade_count":100.0,"preset":"conservative"}

## Interpretation

- v5는 후보 생성과 실제 row-set 중복 제거까지 완료한 데이터 분석 단계다.
- 이번 단계는 새로운 조건식을 더 생성한 것이 아니라, v5에서 선택된 대표 후보를 영구 전략으로 승격하고 OOS 안정성을 검증한 단계다.
- balanced 기준을 통과했으므로 다음 단계는 신규 후보 탐색보다 MVP freeze, 운영 재현성 문서화, 최종 릴리스 검증으로 이동하는 것이 맞다.
