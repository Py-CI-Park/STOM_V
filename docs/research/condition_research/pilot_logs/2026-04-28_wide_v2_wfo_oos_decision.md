# Wide v2 WFO/OOS 검증 판정

## Decision

- decision=PROCEED_TO_MVP_FREEZE
- next_command=$writing-plans Wide v2 MVP freeze 및 PR 병합 보고서 작성
- final_buy_strategy=WideV2Final_B_20260428
- base_buy_strategy=WideV1Final_B_20260425
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
- source_run=WideV2V5DirectV4ShortfallRecovery_20260428
- source_candidate=WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007
- source_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535

## Runtime

- run_id=wide_v2_wfo_oos_validation_20260428
- started_at=2026-04-28T22:01:13.3984848+09:00
- ended_at=2026-04-28T22:31:35.9210437+09:00
- elapsed=00:30:22.5225589
- exit_code=0

## WFO summary

- status=ok
- round_count=8
- success_count=8
- success_rate=1.0
- metric=tpi
- mean_oos_metric=0.5725
- best_oos_metric=0.68
- trade_count_rounds=8
- zero_trade_rounds=0
- mean_trade_count=2045.125

## Balanced evaluation

- passed=True
- reasons=[]
- criteria={'min_rounds': 2, 'min_success_rate': 0.6, 'min_mean_oos_metric': 0.0, 'min_avg_trade_count': 50.0}

## Conservative comparison

- passed=True
- reasons=[]
- criteria={'min_rounds': 3, 'min_success_rate': 0.8, 'min_mean_oos_metric': 0.1, 'min_avg_trade_count': 100.0}

## Interpretation

- Wide v2 v5는 조건식 자동 개선 루프의 후보 생성과 후보 선별 단계다.
- 이번 WFO/OOS는 final candidate의 기간 분할 안정성을 확인하는 검증 단계다.
- balanced 기준과 conservative 기준을 모두 통과했으므로, 다음 단계는 신규 후보 생성보다 MVP freeze, 재현성 문서화, PR merge point 정리로 이동하는 것이 맞다.
- 이 결과는 실거래 승인 자체가 아니라 MVP 개발 종료 판단을 위한 검증 증거다.
