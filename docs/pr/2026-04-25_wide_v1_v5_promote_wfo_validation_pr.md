# Wide v1 v5 promote 및 WFO 검증 PR 보고서

## 전체 계획

1. v5 풀런 runtime JSON에서 실제 row-set 기준 대표 후보 10개를 고정 기록한다.
2. 1순위 대표 후보 cand017의 조건식을 기존 베이스 매수 전략에 결합해 영구 전략 `WideV1Final_B_20260425`로 저장한다.
3. runtime-preflight로 전략 로딩, 문법, 실행 전제 조건을 검증한다.
4. WFO dry-run으로 train/test 창 수와 기간을 먼저 검증한다.
5. 실제 WFO를 실행하고 balanced 및 conservative preset 기준으로 승격 여부를 판정한다.
6. 결과에 따라 MVP freeze 또는 WFO 실패 분석으로 다음 브랜치를 분기한다.

## 현재 계획 결과

- final_buy_strategy=WideV1Final_B_20260425
- base_buy_strategy=WideV1IterationV2_20260423__cand005
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
- primary_candidate=WideV1IterationV5ObservableFull_20260425__cand017
- primary_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
- primary_candidate_csv=backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand017_20260425125216.csv
- wfo_status=ok
- round_count=8
- success_rate=1.0
- mean_oos_metric=0.5762499999999999
- mean_trade_count=2131.75
- zero_trade_rounds=0
- balanced_passed=True
- conservative_passed=True
- decision=PROCEED_TO_MVP_FREEZE
- next_command=$writing-plans Wide v1 MVP freeze 및 운영 재현 문서 작성

## 검토 의견

- 퀀트 트레이더 관점: v5까지의 후보 생성은 데이터 분석과 조건식 생성 단계였고, 이번 단계는 신규 조건을 더 만드는 것이 아니라 선택 후보의 OOS 안정성을 확인하는 검증 단계다.
- CLI 개발 관점: `discovery research`에 WFO를 다시 붙이지 않고 별도 `wfo` 단계로 분리한 현재 구조가 맞다. 연구 루프는 빠른 후보 생성, WFO는 느린 최종 검증으로 역할이 분리된다.
- 전체 프로젝트 관점: cand017 임시 전략은 cleanup으로 삭제될 수 있으므로, 런타임 JSON의 조건식을 베이스 전략에 재결합해 영구 전략명으로 저장한 뒤 검증하는 방식이 관리 가능하다.
- 이번 실행 중 발견된 기존 버그는 `wfo` CLI가 dict config를 넘기는데 `run_walk_forward()`가 dataclass 속성만 접근한 문제였다. dict와 dataclass 입력을 모두 지원하도록 테스트와 함께 수정했다.

## 변경 파일

- `cli/wfo.py`
- `tests/unit/test_wfo.py`
- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.json`
- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.md`
- `utility/ai_agent/WideV1Final_B_20260425.py`
- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_windows.json`
- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json`
- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_wfo_decision.md`
- `docs/pr/2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md`

## 검증

- `runtime-preflight` 실행: `status=ok`, `failed_checks=[]`
- `stom_backtest.py wfo --dry-run` 실행: `round_count=8`
- `stom_backtest.py wfo` 실행: `status=ok`, `round_count=8`, `success_rate=1.0`, `mean_oos_metric=0.5762499999999999`, `mean_trade_count=2131.75`, `zero_trade_rounds=0`
- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py -q`: 14 passed`n- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q`: 113 passed`n- `python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q`: 167 passed`n- `cmd /c "git diff --check --ignore-cr-at-eol 2>&1"`: whitespace 오류 없음, Windows line-ending 경고만 출력

## 남은 위험

- WFO는 기간 분할 검증이므로 실거래 슬리피지, 호가 체결 우선순위, 장중 시스템 장애 위험을 완전히 대체하지 않는다.
- `utility/strategy.db`는 런타임 DB라서 코드 리뷰에서 diff로 확인하기 어렵다. 최종 전략 코드는 `utility/ai_agent/WideV1Final_B_20260425.py` 스냅샷으로 함께 추적한다.
- WFO 결과가 통과했더라도 다음 단계에서는 MVP freeze 문서와 운영 재현 명령을 고정해야 한다.
