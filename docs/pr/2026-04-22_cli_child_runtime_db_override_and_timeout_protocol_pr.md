# CLI Child Runtime DB Override 및 BackTest Timeout Protocol PR 보고서

## 1. 이번 PR의 목적

이번 PR은 CLI 백테스트가 GUI와 같은 runtime DB와 설정 계약을 사용하도록 보강하고, `backtest_process_started` 이후 timeout으로 보이던 문제를 실제 원인까지 추적 가능하게 만든다.

핵심 목적은 두 가지다.

```text
1. CLI parent와 BackTest/Total/engine child process가 같은 runtime DB 경로를 보도록 한다.
2. CLI tick 백테스트가 BackTest process 시작 이후 멈출 때 내부 protocol 진행 지점을 JSON/log로 확인할 수 있게 한다.
```

이 작업은 전체 자동 조건식 연구 흐름에서 아래 위치에 해당한다.

```text
[기준 전략/GUI Wide v1 결과]
        |
        v
[CLI preflight]
        |
        v
[CLI data loading 구조화]
        |
        v
[moneytop / child DB 경로 진단]
        |
        v
[이번 PR] child DB override + timeout protocol 계측 + tick 설정 키 보강
        |
        v
[다음] Wide v1 full-year CLI baseline과 GUI 결과 비교
        |
        v
[그 다음] 후보 조건식 N개 자동 백테스트
```

## 2. 이번 PR의 변경 사항

### 2.1 child runtime DB override

- `utility/setting_base.py`
  - `STOM_CLI_DATABASE_DIR`
  - `STOM_CLI_DB_SETTING`
  - `STOM_CLI_DB_STRATEGY`
  - `STOM_CLI_DB_BACKTEST`
  - `STOM_CLI_DB_STOCK_BACK_TICK`
  - `STOM_CLI_DB_STOCK_BACK_MIN`
- `cli/runner.py`
  - `_ensure_cli_db_env()` 추가
  - Windows spawn child process가 parent CLI와 같은 DB path를 보도록 env 전파

### 2.2 BackTest timeout protocol 계측

- `cli/queue_drain.py`
  - `[CLI_DIAG]` JSON 메시지를 `protocol_diagnostics`로 보존
- `backtest/backtest.py`
  - `BackTest.Start()` checkpoint 추가
  - `Total.MainLoop()` / `Total.Report()` checkpoint 추가
- `cli/runner.py`
  - `STOM_CLI_BACKTEST_PROTOCOL_DIAG=1` 전파
  - timeout/error 결과에 `backtest_process_diagnostics` summary 연결
- `cli/output.py`
  - error JSON에서 `backtest_process_diagnostics`를 보존

### 2.3 CLI tick 설정 키 보강

smoke 중 확인된 실제 원인:

```text
KeyError: '시장미시구조분석'
KeyError: '시장리스크분석'
```

조치:

```text
CLI DICT_SET:
  시장미시구조분석=False
  시장리스크분석=False

_STOM_CLI_DICT_SET child payload:
  시장미시구조분석=False
  시장리스크분석=False
```

## 3. 검증 결과

### 3.1 단위 테스트

```text
focused tests:
  python -m pytest tests/unit/test_queue_drain.py tests/unit/test_backtest_process_protocol_diagnostics.py tests/unit/test_runner_helpers.py tests/unit/test_output.py -q
  result=123 passed

full unit tests:
  python -m pytest tests/unit/ -q
  result=1052 passed, 1 skipped, 10 warnings
```

### 3.2 sync guard

```text
python scripts/verify_nonrelease_sync.py
result=PASS
```

### 3.3 diff check

```text
git diff --check
result=PASS
```

### 3.4 tick smoke

조건:

```text
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
period=20250102~20250103
time=090000~092800
timeframe=tick
avg_time=30
runtime_db=C:\System_Trading\STOM\STOM_V.wt-dev\_database
```

결과:

```text
smoke_4:
  status=success
  last_checkpoint=csv_detected
  elapsed_seconds=45.594
  trade_count=194
  win_rate=34.54
  avg_profit_pct=-0.56
  total_profit_pct=-3.63
  csv_created=True

smoke_32:
  status=success
  last_checkpoint=csv_detected
  elapsed_seconds=60.125
  trade_count=194
  win_rate=34.54
  avg_profit_pct=-0.56
  total_profit_pct=-3.63
  csv_created=True
```

## 4. 이번 PR로 확인된 원인

이전에는 CLI가 `backtest_process_started` 이후 timeout되는 것처럼 보였다.

이번 계측으로 확인한 실제 흐름:

```text
BackTest child started
-> strategy loaded
-> engine start sent
-> engine data sent
-> BackTest waits on mq.get()
-> engine worker Strategy() KeyError
-> Total completion signal not received
-> parent CLI timeout
```

즉, 핵심 원인은 단순 성능/시간 문제가 아니라 CLI headless `DICT_SET` 계약 누락이었다.

## 5. 남은 리스크

- 이번 smoke는 `20250102~20250103` 짧은 기간이다.
- full-year `20250101~20251231` GUI/CLI 결과 비교는 아직 이 PR에서 완료하지 않았다.
- success JSON에는 `backtest_process_diagnostics`를 굳이 노출하지 않는다. 성공 경로의 protocol checkpoint는 stderr log에 남는다.
- 후보 조건식 N개 자동 백테스트는 아직 실행하지 않았다.
- 다음 단계에서 GUI 결과와 CLI 결과의 metric/CSV 정합성을 확인해야 한다.

## 6. 전체 개발 단계와 현재 위치

현재까지 완료된 흐름:

```text
[0. 기준 전략]
       |
       v
[1. GUI Wide v1 기준 백테스트]                 완료
       |
       v
[2. CLI runtime-preflight]                     완료
       |
       v
[3. CLI data loading timeout 구조화]           완료
       |
       v
[4. moneytop / child DB 경로 진단]             완료
       |
       v
[5. child runtime DB override]                 완료
       |
       v
[6. BackTest timeout protocol 계측]            완료
       |
       v
[7. CLI tick 설정 키 보강 및 smoke success]    완료
       |
       v
[8. Wide v1 full-year GUI/CLI 비교]            다음 단계
       |
       v
[9. 후보 N개 자동 백테스트]                    이후 단계
```

## 7. 다음 단계 안내

PR 이후 다음 superpower 단계:

```text
$brainstorming Wide v1 CLI Baseline Backtest Gate 및 GUI 결과 비교 설계
```

다음 설계에서 결정할 내용:

```text
1. full-year CLI baseline 실행 조건 고정
2. 사용자 GUI 결과와 비교할 metric 목록
3. 허용 오차 기준
4. CSV/DB 결과 비교 방식
5. 성공 시 candidate_count=5 실행으로 넘어가는 gate
```

## 8. PR 본문 요약

```markdown
## Summary
- CLI child process가 parent와 같은 runtime DB를 보도록 setting_base/runner DB override 전파를 추가했습니다.
- BackTest timeout 원인 분석을 위해 BackTest/Total protocol checkpoint와 JSON diagnostic 경로를 추가했습니다.
- tick engine이 요구하는 시장 분석 DICT_SET 키를 CLI headless 경로에서 보장해 smoke 4/32 모두 metrics/CSV 생성까지 확인했습니다.

## Test Plan
- python -m pytest tests/unit/test_queue_drain.py tests/unit/test_backtest_process_protocol_diagnostics.py tests/unit/test_runner_helpers.py tests/unit/test_output.py -q
- python -m pytest tests/unit/ -q
- python scripts/verify_nonrelease_sync.py
- git diff --check
- Wide v1 tick smoke 4/32

## Remaining Risk
- full-year GUI/CLI 결과 비교는 다음 PR에서 수행합니다.
- 후보 N개 자동 백테스트는 CLI baseline gate 이후 진행합니다.
```
