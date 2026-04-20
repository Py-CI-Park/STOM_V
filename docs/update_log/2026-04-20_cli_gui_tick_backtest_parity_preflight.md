# 2026-04-20 CLI/GUI Tick Backtest Parity Preflight

## 목적

CLI 자동 연구 루프를 재개하기 전에 GUI/STOM Wide v1 tick 백테스트와 CLI 실행 환경의 정합성을 확인하기 위한 preflight 변경과 검증 결과를 기록한다.

## 전체 흐름

```text
[Wide v1 GUI/STOM 백테스트 성공]
        |
        v
[CLI/GUI Tick Backtest Parity Preflight]
        |
        v
[후속: CLI baseline 1회 검증]
        |
        v
[후속: Wide v1 Retention-Aware 후보 5개 실행]
        |
        v
[후속: 반복 개선 루프 v2]
        |
        v
[후속: 최종 promote/WFO 검증]
```

## 변경 사항

- `cli/runtime_preflight.py` 추가
- `runtime-preflight` CLI 명령 추가
- `stom_backtest.py` 공개 진입점에 `runtime-preflight` 라우팅 추가
- `cli/backtest_checkpoints.py` 추가
- `cli.runner.run_backtest()` timeout checkpoint 필드 연결
- runtime preflight, subcommand, checkpoint 테스트 추가

## 검증 결과

검증 범위: 이 작업에서는 unit tests, nonrelease sync, `runtime-preflight` 공개 CLI 실제 실행을 검증했다. CLI baseline 1회 백테스트, GUI 결과 비교, `candidate_count=5` 후보 실행은 아직 검증하지 않았다.

### focused tests: PASS

```powershell
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_runner_helpers.py -q
```

결과:

```text
113 passed in 8.94s
```

### full unit tests: PASS

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
1019 passed, 1 skipped, 10 warnings in 71.64s (0:01:11)
```

### verify_nonrelease_sync.py: PASS

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

## 남은 위험

- 이 작업에서는 실제 Wide v1 `candidate_count=5` 백테스트를 실행하지 않았다.
- CLI baseline 1회 결과와 GUI 결과 비교는 후속 작업이다.
- `strategy.db`가 다시 `????` 형태로 손상되면 preflight가 반드시 차단해야 한다.
- feature worktree의 heavy tick 실행은 명시적인 runtime profile이 정해질 때까지 제한된다.

## 다음 단계

1. `wt-dev`에서 `runtime-preflight` 실행
2. `ResearchTest` wide 조건식 코드 정상성 확인
3. CLI baseline 1회 백테스트 실행
4. GUI 기준 결과와 비교
5. 통과 시 Wide v1 Retention-Aware 후보 5개 실행 재개
## wt-dev runtime-preflight 파일럿 결과

구현 브랜치 코드(`STOM_V.wt-cli-parity`)에서 공개 진입점 `python stom_backtest.py runtime-preflight`를 사용했고, runtime DB는 `STOM_CLI_DATABASE_DIR=C:\System_Trading\STOM\STOM_V.wt-dev\_database`로 지정했다.

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
strategy_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\strategy.db
setting_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\setting.db
backtest_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\backtest.db
stock_back_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db
stock_back_db_kind=tick
stock_back_db_integrity=table_probe_only
stock_back_db_table_count=2427
buy_status=ok
buy_code_length=270
sell_status=ok
sell_code_length=137
start=20250101
end=20251231
timeframe=tick
avg_time=30
start_time=90000
end_time=92800
engines=32
timeout=900
```

해석:

- 공개 CLI 진입점의 `runtime-preflight` 라우팅은 정상 동작한다.
- `wt-dev` runtime DB 기준으로 ResearchTest wide 매수/매도 조건식은 정상 문자열로 읽히고 compile/evaluate 단계도 통과한다.
- 이번 파일럿은 preflight 검증이며, CLI baseline 1회 백테스트와 GUI 결과 비교는 아직 수행하지 않았다.
- 따라서 다음 단계는 candidate_count=5가 아니라 CLI baseline 1회 백테스트다.
- 위 파일럿으로 `runtime-preflight` 공개 CLI 실제 실행은 검증 완료로 전환한다. 아직 남은 미검증 항목은 CLI baseline 1회 백테스트, GUI 결과 비교, `candidate_count=5` 실행이다.
