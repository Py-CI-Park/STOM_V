# Wide v1 MVP freeze

## Freeze decision

- decision=FREEZE_WIDE_V1_MVP_CANDIDATE
- frozen_at=2026-04-26
- final_buy_strategy=WideV1Final_B_20260425
- base_buy_strategy=WideV1IterationV2_20260423__cand005
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
- primary_candidate=WideV1IterationV5ObservableFull_20260425__cand017
- primary_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
- source_candidate_csv=backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand017_20260425125216.csv

## Why freeze now

- v5에서 실제 row-set 기준 대표 후보 10개를 확보했다.
- cand017은 selected_as_best=True 및 actual_rowset_selected=True로 선택되었다.
- cand017 임시 전략은 cleanup으로 삭제될 수 있어 조건식을 영구 전략 `WideV1Final_B_20260425`로 재생성했다.
- `runtime-preflight`가 `status=ok`로 통과했다.
- WFO는 8개 window에서 `status=ok`로 완료되었다.
- balanced preset과 conservative preset 모두 통과했다.

## WFO evidence

- round_count=8
- success_count=8
- success_rate=1.0
- metric=tpi
- mean_oos_metric=0.5762499999999999
- best_oos_metric=0.68
- mean_trade_count=2131.75
- zero_trade_rounds=0

## Freeze gates

| Gate | Required | Actual | Result |
| --- | --- | --- | --- |
| actual row-set selection | selected_count >= 10 | selected_count=10 | PASS |
| final strategy recreation | DB-loadable strategy snapshot | WideV1Final_B_20260425 snapshot exists | PASS |
| runtime preflight | status=ok | status=ok | PASS |
| WFO rounds | round_count >= 3 | round_count=8 | PASS |
| WFO success rate | success_rate >= 0.60 | success_rate=1.0 | PASS |
| WFO mean OOS metric | mean_oos_metric >= 0.00 | mean_oos_metric=0.5762499999999999 | PASS |
| WFO average trades | mean_trade_count >= 50 | mean_trade_count=2131.75 | PASS |
| no-trade failure | zero_trade_rounds < round_count | zero_trade_rounds=0 | PASS |

## Rejected alternatives

- v6 후보 생성으로 즉시 진행하지 않는다. WFO 기준을 통과했으므로 신규 후보 탐색보다 freeze와 운영 재현성 고정이 우선이다.
- `discovery research`에 WFO를 다시 붙이지 않는다. research는 빠른 후보 생성 루프이고 WFO는 별도 최종 검증 루프다.
- raw WFO JSON 전체를 PR에 넣지 않는다. compact report를 커밋하고 raw runtime copy는 `backtest/temp` 증거로 둔다.

## Freeze meaning

- 이 freeze는 실거래 수익 보장이 아니다.
- 이 freeze는 Wide v1 연구 루프의 MVP 후보를 더 이상 v6/v7 탐색으로 확장하지 않고 운영 재현 문서화 단계로 이동한다는 기준점이다.
- 실거래 전에는 별도 소액 파일럿, 슬리피지 확인, 장중 장애 대응, broker/API runtime 확인이 필요하다.
