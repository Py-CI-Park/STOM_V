# Wide v2 WFO/OOS 검증 PR 보고서

## 전체 계획

1. Wide v2 v5 full-run에서 선정된 cand007을 WFO/OOS 검증 대상으로 고정한다.
2. 임시 후보 전략명이 DB에 남아 있다는 가정을 제거하고, 조건식을 `WideV1Final_B_20260425`에 재결합해 `WideV2Final_B_20260428`로 저장한다.
3. runtime-preflight로 전략 로딩과 실행 전제를 확인한다.
4. WFO dry-run으로 train/test window 수와 기간을 확인한다.
5. 실제 WFO/OOS를 실행하고 balanced preset으로 MVP freeze 가능 여부를 판정한다.
6. 결과에 따라 MVP freeze 또는 조건식 개선 루프 보강으로 분기한다.

## 현재 계획 결과

- final_buy_strategy=WideV2Final_B_20260428
- base_buy_strategy=WideV1Final_B_20260425
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
- source_run=WideV2V5DirectV4ShortfallRecovery_20260428
- source_candidate=WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007
- source_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535
- runtime_preflight_status=ok
- wfo_window_count=8
- wfo_status=ok
- elapsed=00:30:22.5225589
- exit_code=0
- round_count=8
- success_count=8
- success_rate=1.0
- mean_oos_metric=0.5725
- best_oos_metric=0.68
- mean_trade_count=2045.125
- zero_trade_rounds=0
- balanced_passed=True
- conservative_passed=True
- decision=PROCEED_TO_MVP_FREEZE
- next_command=$writing-plans Wide v2 MVP freeze 및 PR 병합 보고서 작성

## 검토 의견

- 퀀트 관점: cand007은 `candidate_count=10` full-run에서 점수와 실제 row-set 기준으로 선택된 검증 대상이다. WFO/OOS에서 8개 window 모두 성공했고 평균 OOS tpi가 0.5725로 balanced/conservative 기준을 모두 통과했다.
- CLI 관점: 연구 루프와 WFO를 분리한 구조가 맞다. 연구 루프는 후보를 빠르게 만들고, WFO는 느리지만 최종 후보만 검증한다. 이번 실행은 30분 22초로 2시간 제한 안에 종료됐다.
- 프로젝트 관점: raw backtest 산출물은 보호 경로에 남기고, 판단에 필요한 manifest, window schedule, WFO report, decision, PR 문서만 커밋한다.
- 운영 관점: 이 결과는 MVP freeze로 이동할 수 있다는 개발 검증 증거다. 실거래 승인 자체로 해석하지 않고, freeze 단계에서 재현 문서와 merge point를 정리해야 한다.

## 변경 파일

- `docs/superpowers/plans/2026-04-28-wide-v2-wfo-oos-validation-execution.md`
- `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.json`
- `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.md`
- `utility/ai_agent/WideV2Final_B_20260428.py`
- `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_windows.json`
- `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json`
- `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md`
- `docs/pr/2026-04-28_wide_v2_wfo_oos_validation_pr.md`

## 검증

- `python .\stom_backtest.py runtime-preflight ...`
- `python .\stom_backtest.py wfo --dry-run ...`
- `python .\stom_backtest.py wfo ...`
- WFO/OOS result: `status=ok`, `round_count=8`, `success_rate=1.0`, `mean_oos_metric=0.5725`
- balanced preset: passed
- conservative preset: passed

## 남은 위험

- WFO/OOS는 기간 분할 검증이며, 실거래 체결 품질과 장애 대응을 완전히 대체하지 않는다.
- `utility/strategy.db`는 런타임 DB라 커밋하지 않는다. 전략 코드는 `utility/ai_agent/WideV2Final_B_20260428.py`로 추적한다.
- 다음 단계에서 MVP freeze 문서와 PR merge point를 정리하기 전까지 기준 브랜치 병합은 보류한다.
