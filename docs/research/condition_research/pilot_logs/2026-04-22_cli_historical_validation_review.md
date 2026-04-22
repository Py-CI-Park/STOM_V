# Historical CLI Validation Review

- 작성일: 2026-04-22
- 대상 브랜치: `feature/cli-backtest-moneytop-protocol-parity`
- 범위: 문서 조사 및 분류만 수행한다. 코드, runtime DB, CSV, graph, temp 파일은 검증 대상으로만 보며 변경하지 않는다.
- 조사 범위: `docs/research`, `docs/pr`, `tests/unit`

## 분류 기준

| 수준 | 의미 |
| --- | --- |
| Level 0 | Parser, help, dry-run, runtime-preflight처럼 실제 백테스트 실행 전 설정/입력/환경만 확인한 증거 |
| Level 1 | mocked runner 또는 helper 단위 테스트처럼 실제 runner/DB/CSV 백테스트를 끝까지 돌리지 않은 증거 |
| Level 2 | 실제 CLI 백테스트 또는 후보 백테스트 실행이 성공하고 결과/CSV/report/trade_count를 남긴 증거 |
| Level 3 | GUI와 CLI가 같은 전략, 날짜, 시간, timeframe, engine 수로 실행되고 `back_count`와 `trade_count`를 비교한 parity 증거 |

## 조사 결과 요약

현재 Wide v1 요구사항을 기준으로 Level 3을 만족하는 과거 증거는 없다.

과거 증거는 각자의 범위에서는 유효하다. 예를 들어 dry-run, runtime-preflight, mocked runner 단위 테스트, candidate backtest loop, discovery promote 실행은 모두 해당 단계의 신뢰성을 올린다. 그러나 Wide v1 Level 3은 더 좁고 강한 요구사항이다. 같은 ResearchTest wide 전략과 같은 2025년 tick 조건에서 GUI 결과와 CLI 결과를 수치로 비교해야 하며, 과거 기록에는 이 비교가 없다.

## 증거별 분류

| 출처 | 최대 수준 | 요약 | Level 3이 아닌 이유 |
| --- | --- | --- | --- |
| `docs/research/2026-03-05_v251_cli_comprehensive_review_plan.md` | Level 0 | 당시 CLI는 구조 설계는 있었지만 실제 백테스트 1회 성공 증거가 없다고 명시했다. `--dry-run`, E2E, GUI vs CLI 결과 정합성 검증은 향후 계획으로 정리되어 있다. | 실행 결과가 아니라 계획/리스크 문서다. 같은 Wide v1 조건의 GUI/CLI 비교가 없다. |
| `docs/research/2026-03-15_current_branch_actual_test_report.md` | Level 2 | 102개 unit test 통과, `--version`, `--dry-run`, `discovery analyze/ml-analyze/generate`, 실제 `discovery promote`까지 실행했다. promote는 `status=ok`, `promoted=true`, report JSON/Markdown 저장, WFO `mean_trade_count=72.0`을 기록했다. | auto-discovery/promote pipeline 검증이다. Wide v1 전략/기간/timeframe/engine 조건이 아니며 GUI 결과와 `back_count`/`trade_count`를 비교하지 않았다. |
| `docs/research/2026-03-17_auto_discovery_pipeline_roadmap.md` | Level 1 | auto-discovery 구조, CSV 회수, batch, report, history, E2E test 계획과 단위 검증 이력을 정리했다. `run_backtest`가 CSV path를 반환하는 설계와 다수 unit test 통과가 기록되어 있다. | roadmap 및 unit/mock 중심 증거다. 실제 Wide v1 CLI baseline 성공과 GUI 비교가 없다. |
| `docs/pr/2026-04-18_candidate_backtest_runtime_hardening_pr.md` | Level 1 | candidate backtest timeout/date/cleanup/reporting을 보강했고 관련 unit test 92개, 확장 unit 141개, 전체 unit 938개 통과를 기록했다. | runtime hardening 검증이며 실제 Wide v1 baseline backtest 성공이나 GUI 비교가 아니다. |
| `docs/pr/2026-04-18_backtest_iteration_research_loop_pr.md` | Level 2 | `discovery research --run-candidates` 실제 파일럿에서 `return_code=0`, `status=ok`, `phase=candidates_evaluated`, 후보 3개 평가와 candidate trade_count 109/413/469를 기록했다. | 후보 loop 실행 증거다. Wide v1 GUI 기준과 같은 조건의 CLI baseline 1회 비교가 아니며 `back_count` 비교도 없다. |
| `docs/pr/2026-04-21_cli_gui_tick_backtest_parity_preflight_pr.md` | Level 0 | `runtime-preflight` 명령, checkpoint 기반, focused tests 115개, 전체 unit 1021개, scoped mypy, wt-dev runtime-preflight 실제 통과를 기록했다. 문서 자체가 CLI baseline 1회 백테스트와 GUI 비교는 다음 단계라고 명시한다. | preflight는 DB/전략/timeframe/인자 접근성 확인이다. 실제 CLI baseline backtest가 아니며 후보 5개나 GUI/CLI parity 승인이 아니다. |
| `tests/unit/test_runner_helpers.py` | Level 1 | DICT_SET sync, timeout field, queue drain, cleanup, shared memory cleanup, checkpoint recorder source contract 등을 단위 테스트한다. 일부 테스트는 fake process, monkeypatch, source string 검사다. | 실제 CLI process가 실제 DB로 백테스트를 완료하지 않는다. CSV 생성과 GUI 비교가 없다. |
| `tests/unit/test_exit_codes.py` | Level 0 / Level 1 | `--help`, `--list-strategies` subprocess exit code와 monkeypatched runner execution error code를 확인한다. | parser/exit code와 fake runner 경로 검증이다. 실제 백테스트 성공이나 parity 비교가 아니다. |

## Wide v1 관련 최신 문맥

| 출처 | 역할 | 요약 |
| --- | --- | --- |
| `docs/research/condition_research/pilot_logs/2026-04-19_research_test_tick_wide_backtest.md` | GUI 기준값 | `wt-dev` 실제 실행 환경에서 ResearchTest wide tick backtest가 완료되었다. 조건은 `20250101~20251231`, `090000~092800`, `avg_time=30`, `engine_multi=32`이며 `back_count=1638`, `trade_count=40937`, CSV 생성 성공을 기록했다. |
| `docs/pr/2026-04-20_tick_research_baseline_condition_pr.md` | GUI 기준값 PR 요약 | Wide v1 CSV 확보와 같은 GUI 기준 결과를 PR 수준에서 정리했다. 이 값은 연구 baseline이지 live 후보 성능 승인이 아니라고 명시했다. |
| `docs/research/condition_research/pilot_logs/2026-04-21_wide_v1_cli_baseline_backtest.md` | Level 3 시도 실패 기록 | runtime-preflight는 `command_exit_code=0`, `status=ok`로 통과했다. 그러나 CLI baseline 본 실행은 `command_exit_code=124`, 결과 JSON 없음, 신규 CSV 없음, `cli_back_count=not_present_no_result_json`, `cli_trade_count=not_present_no_result_json`, `decision=FAIL`로 기록되었다. |

이 최신 문맥은 Level 3에 필요한 GUI 쪽 기준값과 CLI preflight 통과 증거를 제공한다. 하지만 CLI baseline 실행 결과가 없으므로 parity 비교는 수행되지 않았다.

## 현재 Wide v1 Level 3 충족 여부

충족하지 않는다.

Level 3을 만족하려면 아래 조건이 한 묶음으로 존재해야 한다.

| 항목 | 필요한 값 |
| --- | --- |
| buy | `ResearchTest_Tick_B_090000_092800_Wide_20260419` |
| sell | `ResearchTest_Tick_S_090000_092800_Wide_20260419` |
| 날짜 | `20250101~20251231` |
| 시간 | `090000~092800` |
| timeframe | `tick` |
| avg_time | `30` |
| engines | `32` |
| GUI 기준 | `back_count=1638`, `trade_count=40937` |
| CLI 기준 | command exit 0, result JSON 또는 동등한 결과 기록, 신규 CSV, CLI `back_count`, CLI `trade_count` |
| 비교 | GUI/CLI `back_count` 차이와 `trade_count` 차이 또는 허용 기준 내 일치 판정 |

현재 보유한 증거 중 GUI 기준값은 있다. CLI preflight 통과도 있다. 그러나 CLI baseline 실행이 timeout으로 실패했고 CLI `back_count`/`trade_count`가 없으므로 비교 결과도 없다. 따라서 현재 Wide v1 CLI/GUI parity는 입증되지 않았다.

## Wide v1 tick baseline에 새로 필요한 검증

1. 같은 조건의 CLI baseline 1회 실행을 정상 종료시킨다.
   - exit code 0
   - `--format json -o ...` 결과 파일 생성
   - 신규 ResearchTest wide CSV 생성
   - checkpoint payload 기록

2. CLI 결과에서 비교 가능한 수치를 확보한다.
   - `cli_back_count`
   - `cli_trade_count`
   - 필요 시 runtime, win_rate, avg_return, total_return, TPI 등 보조 지표

3. GUI 기준값과 CLI 값을 같은 표에서 비교한다.
   - GUI `back_count=1638`
   - GUI `trade_count=40937`
   - CLI `back_count`
   - CLI `trade_count`
   - absolute diff
   - diff percent
   - PASS/HOLD/FAIL 판정 기준

4. 실패하면 실패 지점을 checkpoint로 좁힌다.
   - pre-backtest hang인지
   - `backQ.get()` 또는 data loading wait인지
   - shared memory 생성 이후 child process 시작 전/후 문제인지
   - `--timeout` 적용 범위가 충분한지
   - Windows shared memory cleanup 잔여물이 있는지

5. 위 비교가 통과한 뒤에만 Wide v1 Retention-Aware `candidate_count=5` 실행으로 넘어간다.
   - 과거 candidate loop 성공은 다른 scope의 Level 2 증거다.
   - 현재 Wide v1 후보 5개 실행의 신뢰성은 Wide v1 CLI/GUI parity가 먼저 확인되어야 한다.

## 결론

과거 CLI 검증 이력은 단계별로 유효하다.

- parser/dry-run/preflight는 Level 0 증거다.
- mocked/helper unit test는 Level 1 증거다.
- discovery promote 및 candidate backtest loop 실제 실행은 Level 2 증거다.
- 현재 Wide v1 CLI/GUI parity를 증명하는 Level 3 증거는 아직 없다.

따라서 과거 증거를 현재 Wide v1 Level 3 완료로 승격하면 안 된다. 다음 작업은 후보 5개 실행이 아니라, 같은 Wide v1 조건에서 CLI baseline 1회를 성공시키고 GUI 기준 `back_count=1638`, `trade_count=40937`과 비교하는 검증이어야 한다.
