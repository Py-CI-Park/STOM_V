# Wide v2 WFO/OOS 검증 manifest

## 검증 대상

- final_buy_strategy=WideV2Final_B_20260428
- base_buy_strategy=WideV1Final_B_20260425
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
- source_run=WideV2V5DirectV4ShortfallRecovery_20260428
- source_candidate=WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007
- source_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535
- source_adjusted_score=112.06250936127728

## WFO 설정

- start=20250101
- end=20251231
- timeframe=tick
- betting=20
- avg_time=30
- start_time=90000
- end_time=92800
- engines=32
- train_window_days=120
- test_window_days=30
- step_days=30
- purge_days=1
- embargo_days=1
- objective=tpi
- method=grid
- max_iter=1
- timeout=1200
- promotion_preset=balanced

## 해석

- 이 manifest는 Wide v2 v5 winner를 WFO/OOS 검증 대상으로 고정한다.
- WFO 통과 전에는 운영 승인 또는 실거래 승인으로 해석하지 않는다.
