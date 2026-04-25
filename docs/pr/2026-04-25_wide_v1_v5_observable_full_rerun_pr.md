# Wide v1 v5 observable full rerun PR

## 전체 계획

Wide v1 MVP의 현재 흐름은 `v5 actual row-set 검증 -> promote/WFO -> MVP freeze`다. 이번 PR은 runtime checkpoint와 후보별 관측 로그를 적용한 상태에서 full v5를 실행해, v6 보강 없이 promote/WFO로 진행할 수 있는지 확인한다.

## 현재 계획

1. `candidate_count=10` full v5를 실행한다.
2. runtime JSON으로 후보별 조건식, 소요 시간, 거래 수를 확인한다.
3. actual row-set 대표 10개 확보 여부를 판정한다.
4. 결과에 따라 `promote/WFO` 또는 `v6 actual row-set generation expansion`으로 분기한다.

## 실행 결과

- runtime path: `backtest/temp/wide_v1_v5_observable_full_20260425.json`
- status: `ok`
- phase: `candidates_evaluated`
- elapsed_seconds: `2680.031`
- elapsed_minutes: `44.67`
- executed candidates: `17`
- successful candidates: `17`
- failed candidates: `0`
- actual_rowset_selection.status: `ok`
- row_set_identity_status: `all_distinct`
- requested_count: `10`
- selected_count: `10`
- actual_group_count: `11`
- duplicate_actual_rowset_count: `6`

## 주요 확인 사항

- `candidate_count=10` 요청에서 실제 실행 후보는 17개였다.
- 후보별 소요 시간은 대부분 143~161초 범위였다.
- 느린 후보들은 대부분 `trade_count`가 35,000건 이상이었다.
- 조건식은 달라도 동일 actual row-set을 만드는 중복 그룹이 1개 있었다.
- 중복이 있었지만 actual group이 11개라 대표 10개 확보에는 성공했다.

## 결정

- decision: `PROCEED_TO_PROMOTE_WFO_PLAN`
- next command: `$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성`

## 변경 파일

- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_observable_full_actual_rowset_selection.md`
- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_observable_full_rerun.md`
- `docs/pr/2026-04-25_wide_v1_v5_observable_full_rerun_pr.md`

## 커밋 제외 파일

- `backtest/temp/wide_v1_v5_observable_full_20260425.json`
- `backtest/temp/wide_v1_v5_observable_full_20260425.stdout.txt`
- `backtest/temp/wide_v1_v5_observable_full_20260425.stderr.txt`
- `backtest/temp/wide_v1_v5_observable_full_20260425.pid`
- `backtest/csv/`
- `backtest/graph/`

## 검증

- `python scripts/analyze_wide_v1_v5_actual_rowset_selection.py --runtime-path backtest\temp\wide_v1_v5_observable_full_20260425.json --output docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_observable_full_actual_rowset_selection.md`
- `python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q`
- `cmd /c "git diff --check --ignore-cr-at-eol 2>&1"`

## 다음 단계

다음 단계는 v6가 아니라 promote/WFO 검증 계획이다. full v5에서 actual row-set 대표 10개를 확보했으므로, 이제 선택된 대표 후보를 기준으로 promote 후보를 확정하고 WFO 검증으로 넘어간다.
