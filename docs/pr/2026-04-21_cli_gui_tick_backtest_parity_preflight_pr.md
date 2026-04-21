# CLI/GUI Tick Backtest Parity Preflight PR 보고서

## 1. 이번 PR의 목적

이번 PR의 목적은 사람이 GUI/STOM으로 수행하던 tick 백테스트 연구를 AI/CLI 자동 연구 루프가 같은 runtime 조건으로 재현할 수 있도록, **CLI/GUI 백테스트 정합성 preflight 기반**을 추가하는 것이다.

이번 PR은 후보 조건식 개선 완료 PR이 아니다. 전체 자동 조건식 연구 계획 안에서 보면, 이번 PR은 Wide v1 CSV 기반 후보 5개 백테스트를 재개하기 전에 필요한 **CLI 실행 신뢰성 게이트**다.

```text
[사람의 기존 연구 흐름]
GUI/STOM 조건식 선택
        |
        v
GUI 백테스트 실행
        |
        v
CSV/결과 확인
        |
        v
조건식 개선
        |
        v
다시 GUI 백테스트

[목표 자동화 연구 흐름]
CLI 조건식 선택/생성
        |
        v
CLI 백테스트 실행
        |
        v
CSV 자동 분석
        |
        v
후보 조건식 생성
        |
        v
CLI 후보 백테스트
        |
        v
ranking / best_candidate 분석
        |
        v
반복 개선
        |
        v
최종 promote/WFO 검증
```

사람이 GUI로 직접 수행하던 과정을 AI가 대신하려면 CLI가 GUI와 같은 전략 DB, 설정 DB, tick DB, 기간, 시간, avg, engine 수를 보고 있다는 증거가 먼저 필요하다. 그래서 이번 PR은 조건식 후보 개선으로 바로 가지 않고, CLI가 실제로 같은 runtime 환경을 볼 수 있는지 검증하는 preflight와 checkpoint 기반을 만든다.

## 2. 전체 계획에서 현재 단계

초기 superpower 흐름과 최근 PR들의 누적 방향은 아래와 같다.

```text
[0. 기준 전략 / 기준 CSV]
        |
        v
[1. CSV 분석]
        |
        v
[2. 후보 expression pool 생성]
        |
        v
[3. 후보 전략 저장/검증]
        |
        v
[4. 후보 백테스트 런타임 안정화]
        |
        v
[5. 후보 N개 백테스트 / ranking]
        |
        v
[6. Retention-Aware 후보 선별]
        |
        v
[7. 연구용 Wide tick baseline 확보]
        |
        v
[8. CLI/GUI Tick Backtest Parity Preflight]  <- 이번 PR
        |
        v
[9. CLI baseline 1회 백테스트]              <- 다음 단계
        |
        v
[10. GUI 결과와 CLI 결과 비교]
        |
        v
[11. Wide v1 Retention-Aware 후보 5개 실행]
        |
        v
[12. 반복 개선 루프 v2]
        |
        v
[13. 최종 promote/WFO 검증]
```

이번 PR의 현재 위치는 **8번 단계 완료**다. 원래 기대했던 다음 작업은 Wide v1 CSV를 바로 후보 5개 루프에 넣는 것이었지만, 실제 작업 중 아래 문제가 확인되었다.

```text
GUI/STOM 직접 백테스트:
  Wide v1 조건식 1년 tick 백테스트 약 1분 완료
  거래 40,937건 CSV 확보

CLI/headless 백테스트:
  같은 의도 조건에서 timeout 또는 runtime DB/전략코드 불일치 가능성 확인
```

따라서 수정된 올바른 순서는 다음이다.

```text
[수정 전 예상]
Wide v1 CSV
        |
        v
candidate_count=5 후보 백테스트

[수정 후 안전한 순서]
Wide v1 CSV
        |
        v
CLI/GUI runtime preflight
        |
        v
CLI baseline 1회 백테스트
        |
        v
GUI 결과와 CLI 결과 비교
        |
        v
candidate_count=5 후보 백테스트
```

이 수정은 전체 방향을 바꾼 것이 아니라, 전체 자동화 방향을 신뢰 가능하게 만들기 위한 선행 게이트다.

## 3. 이전 PR 흐름과의 연결

이번 PR은 아래 흐름의 연장선이다.

### 3.1 세그먼트 기반 조건식 연구 루프

백테스트 CSV를 분석해 손실 구간과 후보 조건식을 찾는 기반을 만들었다.

역할:

```text
CSV 분석
        |
        v
후보 expression 생성
        |
        v
후보 전략 저장/검증
```

### 3.2 research WFO 연결 실험과 제거

처음에는 `discovery research` 안에서 WFO를 연결하려 했지만, 실제 파일럿에서 무거운 WFO가 빠른 연구 루프와 맞지 않는다는 점이 확인되었다. 이후 WFO는 `discovery promote`와 별도 최종 검증 경로로 분리했다.

역할 분리:

```text
discovery research:
  빠른 조건식 연구/후보 백테스트 루프

discovery promote / WFO:
  최종 후보 검증 루프
```

### 3.3 후보 백테스트 런타임 안정화

후보 백테스트 실패/timeout 시 전략 DB 오염을 줄이고, cleanup과 리포트 기록을 강화했다.

역할:

```text
후보 저장
        |
        v
후보 백테스트
        |
        v
timeout/실패 cleanup
        |
        v
리포트 기록
```

### 3.4 Backtest Iteration Research Loop v1

단일 후보에서 후보 N개 실행과 ranking 구조로 확장했다.

역할:

```text
후보 N개 생성
        |
        v
후보별 백테스트
        |
        v
후보별 comparison/promotion 평가
        |
        v
ranking / best_candidate
```

### 3.5 Candidate Quality Gate / Retention-Aware Selection

기준 전략 대비 거래가 너무 많이 제거되는 후보를 줄이기 위해 `estimated_retention`, `retention_penalty`, `adjusted_score` ranking을 추가했다.

역할:

```text
후보 expression pool
        |
        v
estimated_retention 사전 선별
        |
        v
후보 백테스트
        |
        v
retention_penalty / adjusted_score ranking
```

### 3.6 Tick Research Baseline Condition

기존 최적화 tick 조건식은 거래 수가 너무 적어 후보 연구 데이터로 부족했다. 그래서 의도적으로 넓은 연구용 tick baseline 조건식인 Wide v1을 만들고, GUI/STOM 직접 백테스트로 40,937건 거래 CSV를 확보했다.

Wide v1 직접 실행 결과:

```text
기간: 2025-01-01 ~ 2025-12-31
시간: 09:00:00 ~ 09:28:00
avg_time: 30
engine_multi: 32
거래횟수: 40,937회
소요시간: 0:01:00.675279
```

### 3.7 이번 PR: CLI/GUI Tick Backtest Parity Preflight

Wide v1 CSV를 후보 5개 루프로 바로 넣기 전에, CLI가 GUI와 같은 runtime 조건을 볼 수 있는지 검증하는 장치를 추가했다.

## 4. 이번 PR의 변경 사항

### 4.1 `cli/runtime_preflight.py` 추가

CLI 백테스트 실행 전 runtime 상태를 JSON으로 검증한다.

검증 항목:

```text
strategy.db 경로와 존재 여부
setting.db 경로와 SQLite integrity
backtest.db 경로와 SQLite integrity
stock_tick_back.db 경로와 table probe
csv output dir 존재 여부
매수 전략코드 정상성
매도 전략코드 정상성
날짜/engine/avg_time config 정상성
tick/min 전략명-타임프레임 정합성
```

특히 아래 실패를 구조화된 JSON 오류로 반환한다.

```text
전략코드가 ????로 깨짐
전략코드가 너무 짧음
전략코드가 non-string
strategy.db 누락
손상된 SQLite DB
잘못된 start/end 날짜
engine_count < 1
잘못된 avg_time
tick/min 전략명 mismatch
```

### 4.2 `runtime-preflight` CLI 명령 추가

예시:

```powershell
python stom_backtest.py runtime-preflight `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900
```

`stom_backtest.py` 공개 진입점에도 `runtime-preflight` 라우팅을 추가했다.

### 4.3 CLI 인자 해석 parity 보강

`runtime-preflight`가 기존 CLI 백테스트와 다른 인자 해석을 하지 않도록 보강했다.

대표 보강:

```text
--avg-time 30       -> 30
--avg-time 60,120   -> [60, 120]
--avg-time abc      -> traceback 대신 JSON 오류
--divid-mode        -> 기존 runtime choices와 정합성 유지
```

### 4.4 `cli/backtest_checkpoints.py` 추가

백테스트 실행 중 checkpoint를 구조화된 JSON 필드로 남기는 기록기를 추가했다.

기록 예:

```text
preflight_started
dict_set_synced
backtest_watermark_ready
stock_back_db_selected
moneytop_loaded
shared_data_loaded
back_count_ready
backtest_process_started
backtest_process_finished
csv_detected
```

### 4.5 `cli.runner.run_backtest()` checkpoint 연결

timeout, 조기 실패, 성공, 예외 반환에 checkpoint 필드를 붙였다.

예시 필드:

```text
checkpoint_status
last_checkpoint
elapsed_seconds
checkpoints
cleanup_status
```

또한 `BackTest` child process가 non-zero exit code로 종료되면 metrics만 보고 성공 처리하지 않고 error로 반환하도록 보강했다.

### 4.6 문서 추가

추가/갱신 문서:

```text
docs/superpowers/specs/2026-04-20-cli-gui-tick-backtest-parity-design.md
docs/superpowers/plans/2026-04-20-cli-gui-tick-backtest-parity-preflight.md
docs/update_log/2026-04-20_cli_gui_tick_backtest_parity_preflight.md
```

이 브랜치에는 이전 준비 단계 문서도 포함된다.

```text
docs/superpowers/specs/2026-04-20-wide-v1-retention-aware-candidate-improvement-design.md
docs/superpowers/plans/2026-04-20-wide-v1-retention-aware-candidate-improvement.md
```

## 5. 검증 결과

### 5.1 focused tests

```powershell
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_runner_helpers.py -q
```

결과:

```text
115 passed in 8.82s
```

### 5.2 full unit tests

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
1021 passed, 1 skipped, 10 warnings in 72.11s (0:01:12)
```

### 5.3 non-release sync 검증

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

### 5.4 scoped mypy

```powershell
python -m mypy cli\runtime_preflight.py cli\backtest_checkpoints.py cli\subcommands.py --ignore-missing-imports --follow-imports=skip
```

결과:

```text
Success: no issues found in 3 source files
```

### 5.5 wt-dev runtime-preflight 파일럿

명령:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
python stom_backtest.py runtime-preflight `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900
```

결과:

```text
COMMAND_EXIT_CODE=0
status=ok
failed_checks=[]
validation_errors=[]
timeframe_match.status=ok
stock_back_db_integrity=table_probe_only
stock_back_db_table_count=2427
buy_status=ok
buy_code_length=270
sell_status=ok
sell_code_length=137
```

### 5.6 invalid avg-time 구조화 오류 검증

명령:

```powershell
python stom_backtest.py runtime-preflight --buy BuyWide --sell SellWide --start 20250101 --end 20251231 --avg-time abc
```

결과:

```text
COMMAND_EXIT_CODE=1
status=error
failed_checks=["config"]
validation_errors=["avg_time must be a positive integer: 'abc'"]
```

## 6. merge 승인 판단

이번 PR은 merge 승인 가능하다고 판단한다.

근거:

```text
focused tests 통과
full unit tests 통과
verify_nonrelease_sync.py 통과
scoped mypy 통과
wt-dev runtime-preflight 실제 실행 통과
최종 코드 리뷰 Critical/Important 이슈 없음
runtime DB/CSV/graph 산출물 미커밋
```

단, 이 merge 승인은 **CLI/GUI parity preflight 기반**에 대한 승인이다. 후보 5개 백테스트 결과나 best_candidate 품질에 대한 승인이 아니다.

## 7. 남은 리스크

### 7.1 CLI baseline 1회 백테스트 미실행

이번 PR은 preflight 단계까지다. 아직 아래 명령 계열의 실제 baseline 백테스트는 수행하지 않았다.

```text
ResearchTest_Tick_B_090000_092800_Wide_20260419
ResearchTest_Tick_S_090000_092800_Wide_20260419
20250101~20251231
090000~092800
tick
avg_time=30
engines=32
```

다음 단계에서 CLI baseline 1회를 실행해야 한다.

### 7.2 GUI 결과와 CLI 결과 비교 미완료

GUI 기준 결과는 아래와 같다.

```text
거래횟수: 40,937회
back_count: 1638
소요시간: 0:01:00.675279
```

CLI baseline이 실행된 뒤 이 값들과 비교해야 한다.

### 7.3 candidate_count=5 미실행

이번 PR은 후보 5개 백테스트를 실행하지 않았다.

```text
미실행:
Wide v1 Retention-Aware candidate_count=5
후보별 actual trade_count_retention
adjusted_score ranking
best_candidate
cleanup summary
```

### 7.4 대형 tick DB 검사는 경량 table probe

대형 `stock_tick_back.db`에 full `PRAGMA integrity_check`를 수행하면 너무 오래 걸릴 수 있다. 따라서 이번 PR에서는 대형 tick DB를 `table_probe_only` 방식으로 확인한다.

```text
확인:
SQLite open 가능
sqlite_master table count 확인
table_count > 0

미확인:
대형 DB 전체 integrity_check
```

### 7.5 runner checkpoint는 실제 heavy timeout으로 검증하지 않음

unit/source contract와 구조 검증은 통과했지만, 실제 heavy backtest timeout 상황에서 checkpoint payload가 어떻게 남는지는 후속 실제 실행에서 확인해야 한다.

## 8. 이번 PR 이후 다음 단계

이번 PR이 merge되면 다음 단계는 후보 5개 실행이 아니라 **CLI baseline 1회 백테스트 게이트 설계**다.

수정된 다음 흐름:

```text
[이번 PR merge]
        |
        v
[CLI baseline 1회 백테스트 설계]
        |
        v
[CLI baseline 1회 실행]
        |
        v
[GUI Wide v1 결과와 비교]
        |
        v
[통과 시 Wide v1 Retention-Aware 후보 5개 실행]
        |
        v
[후보 ranking / best_candidate 분석]
```

## 9. 다음 브레인스토밍 지시사항

다음 작업은 아래 명령으로 시작하는 것이 적절하다.

```text
$brainstorming Wide v1 CLI Baseline Backtest Gate 및 GUI 결과 비교 설계
```

브레인스토밍에 포함할 맥락:

```text
목표:
- runtime-preflight가 통과한 ResearchTest wide 조건식으로 CLI baseline 1회 백테스트를 실행한다.
- GUI/STOM 직접 실행 결과와 CLI 결과를 비교한다.
- 비교 결과가 충분히 일치할 때만 Wide v1 Retention-Aware candidate_count=5로 넘어간다.

기준 GUI 결과:
- 기간: 2025-01-01 ~ 2025-12-31
- 시간: 09:00:00 ~ 09:28:00
- timeframe: tick
- avg_time: 30
- engine_multi: 32
- back_count: 1638
- trade_count: 40,937
- runtime: 0:01:00.675279

이번 PR에서 확보한 것:
- runtime-preflight 공개 CLI 진입점 통과
- wt-dev runtime DB 경로 확인
- ResearchTest wide 매수/매도 전략코드 정상 확인
- stock_tick_back.db table_probe_only 통과
- runner checkpoint 기반 추가

아직 하면 안 되는 것:
- CLI baseline 결과 없이 candidate_count=5 바로 실행
- best_candidate/promotion 판단
- WFO를 discovery research 안으로 재도입

결정할 것:
1. CLI baseline 1회 백테스트 명령 형식
2. GUI/CLI 결과 비교 허용 기준
3. timeout 발생 시 checkpoint 해석 기준
4. CLI baseline 성공 후 candidate_count=5로 넘어가는 gate
5. 결과 기록 위치와 PR 분리 여부
```

## 10. 결론

이번 PR은 전체 자동 조건식 연구 계획 중 **CLI 백테스트 자동화 신뢰성 확보 단계**다. 전체 개발이 완료된 것은 아니지만, 사람이 GUI로 수행하던 백테스트 연구를 AI/CLI가 이어받기 위해 필요한 선행 조건을 완료했다.

merge 후 다음 작업은 `candidate_count=5`가 아니라, 먼저 CLI baseline 1회 백테스트와 GUI 결과 비교를 설계하고 실행하는 것이다.
