# Wide v2 MVP freeze

## Freeze decision

- decision=FREEZE_WIDE_V2_MVP_CANDIDATE
- frozen_at=2026-04-29
- final_buy_strategy=WideV2Final_B_20260428
- base_buy_strategy=WideV1Final_B_20260425
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
- source_run=WideV2V5DirectV4ShortfallRecovery_20260428
- source_candidate=WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007
- source_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535

## Why freeze now

- Wide v2 v5 direct_v4 shortfall recovery가 실제 `candidate_count=10` 검증에서 작동했다.
- 후보 풀은 direct_v4 4개에서 recovery 포함 28개로 보강되었고, 실제 실행은 20개 후보까지 진행되었다.
- actual row-set 기준으로 10개 대표 후보가 선택되었고 `row_set_identity_status=all_distinct`를 만족했다.
- final best와 WFO handoff candidate가 동일하게 `cand007`로 선정되었다.
- `WideV2Final_B_20260428` 전략 스냅샷이 생성되었고 DB reload 검증을 통과했다.
- runtime-preflight가 `status=ok`, `failed_checks=[]`, `validation_errors=[]`로 통과했다.
- WFO/OOS는 8개 window에서 `status=ok`로 완료되었다.
- balanced preset과 conservative preset을 모두 통과했다.

## WFO/OOS evidence

- report_path=docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json
- decision_path=docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md
- elapsed=00:30:22.5225589
- exit_code=0
- round_count=8
- success_count=8
- success_rate=1.0
- metric=tpi
- mean_oos_metric=0.5725
- best_oos_metric=0.68
- trade_count_rounds=8
- zero_trade_rounds=0
- mean_trade_count=2045.125

## Freeze gates

| Gate | Required | Actual | Result |
| --- | --- | --- | --- |
| v5 recovery | direct_v4 shortfall recovers to candidate_count target | final_candidate_pool_count=28 | PASS |
| actual row-set selection | selected_count >= 10 | actual_selected_count=10 | PASS |
| row-set identity | representatives are distinct | row_set_identity_status=all_distinct | PASS |
| final strategy snapshot | DB-loadable strategy snapshot | WideV2Final_B_20260428 snapshot exists | PASS |
| runtime preflight | status=ok and no failed checks | status=ok, failed_checks=[] | PASS |
| WFO windows | round_count >= 3 | round_count=8 | PASS |
| WFO success rate | success_rate >= 0.60 | success_rate=1.0 | PASS |
| WFO mean OOS metric | mean_oos_metric >= 0.00 | mean_oos_metric=0.5725 | PASS |
| WFO average trades | mean_trade_count >= 50 | mean_trade_count=2045.125 | PASS |
| no-trade failure | zero_trade_rounds < round_count | zero_trade_rounds=0 | PASS |

## Rejected alternatives

- v6/v7 후보 생성을 즉시 진행하지 않는다. WFO/OOS 기준을 통과했으므로 신규 탐색보다 MVP 종료와 재현성 고정이 우선이다.
- `discovery research`에 WFO를 다시 붙이지 않는다. research loop는 빠른 후보 생성, WFO/OOS는 별도 최종 검증으로 분리한다.
- 실거래 승인으로 표현하지 않는다. 이번 freeze는 MVP 개발 종료 판단이며, 실거래 전에는 post-MVP 운영 파일럿 검증이 필요하다.

## Freeze meaning

- 이 freeze는 Wide v2 조건식 자동 개선 MVP가 후보 생성, 후보 보강, 실제 row-set 선별, WFO/OOS 검증까지 통과했다는 기준점이다.
- 이 freeze는 실거래 수익 보장이 아니다.
- 다음 단계는 PR merge point 생성, 운영 재현 문서 확인, post-MVP risk backlog 및 소액 파일럿 체크리스트 작성이다.
