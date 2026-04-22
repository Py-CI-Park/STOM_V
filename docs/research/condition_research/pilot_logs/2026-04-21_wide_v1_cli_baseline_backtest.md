# Wide v1 CLI Baseline Backtest Pilot

## 목적

GUI/STOM에서 성공한 ResearchTest wide 기준 전략을 CLI에서 1회 실행해, Wide v1 Retention-Aware 후보 5개 루프 진입 가능 여부를 판단한다.

## 전체 흐름

```text
[runtime-preflight]
        |
        v
[CLI baseline 1회 백테스트]
        |
        v
[GUI 기준 결과와 비교]
        |
        v
[PASS/HOLD/FAIL 판정]
```

## 실행 조건

```text
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
start=20250101
end=20251231
timeframe=tick
avg_time=30
start_time=90000
end_time=92800
engines=32
timeout=900
```

## preflight 결과

`STOM_V.wt-dev`에서 공개 CLI 진입점으로 실행했다.

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

결과:

```text
command_exit_code=0
status=ok
failed_checks=[]
validation_errors=[]
timeframe_match.status=ok
buy.status=ok
buy.code_length=270
sell.status=ok
sell.code_length=137
stock_back_db_usable=True
stock_back_db_integrity=table_probe_only
stock_back_db_table_count=2427
strategy_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\strategy.db
setting_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\setting.db
backtest_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\backtest.db
stock_back_db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db
```

preflight는 통과했다. 따라서 CLI baseline 1회 실행 조건은 충족했다.

## CLI baseline 명령

실제 baseline은 `STOM_V.wt-dev`에서 실행했다. 앞서 feature worktree에서 `STOM_CLI_DATABASE_DIR`만 지정해 실행했을 때는 legacy `utility.setting`이 상대경로 `_database/setting.db`를 읽어 `no such table: main`으로 실패했다. 따라서 baseline 실행은 spec 의도대로 `wt-dev`에서 수행했다.

```powershell
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900 `
  --format json `
  -o backtest\temp\wide_v1_cli_baseline_20260421.json
```

## CLI baseline 결과

```text
command_exit_code=124
external_timeout_ms=964079
result_json_created=False
csv_path=None
checkpoint_status=not_available
last_checkpoint=not_available
```

명령은 외부 실행 제한 약 964초까지 반환되지 않았다. `--timeout 900`을 지정했지만 CLI 프로세스가 정상 JSON 결과를 쓰고 종료하지 못했다.

생성 확인:

```text
backtest\temp\wide_v1_cli_baseline_20260421.json: 없음
ResearchTest wide 신규 CSV: 없음
최신 ResearchTest wide CSV: 기존 GUI 실행 파일
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

실행 후 남은 Python 프로세스 1개를 강제 종료했다.

```text
process_cleanup=done
```

실행 후 shared memory `backdata_0`부터 `backdata_31`까지 잔여가 확인되었다. 이는 최소한 데이터 로딩 또는 공유 메모리 생성 단계까지 진행되었음을 시사하지만, JSON checkpoint가 기록되지 않았으므로 정확한 runner 내부 `last_checkpoint`는 확보하지 못했다.

```text
shared_memory_remaining=backdata_0..backdata_31
shared_memory_cleanup_attempted=True
```

정리 스크립트로 `unlink()`를 시도했지만 Windows shared memory name이 계속 관측되었다. 후속 분석에서 별도 정리/재부팅/프로세스 핸들 확인이 필요할 수 있다.

## GUI 기준 결과

```text
back_count=1638
trade_count=40937
runtime=0:01:00.675279
win_rate=30.02%
avg_return=-0.68%
total_return=-695.09%
tpi=0.60
```

## 비교 결과

```text
cli_back_count=not_present_no_result_json
cli_trade_count=not_present_no_result_json
back_count_diff=not_available
trade_count_diff=not_available
trade_count_diff_pct=not_available
```

CLI baseline이 JSON 결과를 생성하지 못했으므로 GUI 결과와 수치 비교는 수행할 수 없다.

## 판정

```text
decision=FAIL
reason=CLI baseline command did not return within the external 964 second limit, did not write result JSON, did not create a new CSV, and left backdata_0..31 shared memory segments.
```

이번 실패는 조건식 preflight 실패가 아니다. preflight는 통과했다. 실패 지점은 CLI baseline runner 실행 경로다.

## 다음 단계

```text
$brainstorming CLI baseline backtest failure checkpoint 분석 설계
```

다음 분석에서 확인할 항목:

```text
1. run_backtest 내부에서 parent process가 어디서 blocking되는지 확인
2. backQ.get() 데이터 로딩 대기 구간 timeout/condition wait 필요 여부
3. shared memory 생성 후 BackTest process 시작 전/후 상태
4. --timeout 900이 proc_backtest.join() 단계에만 적용되어 pre-backtest hang을 잡지 못하는지 확인
5. GUI/STOM 실행과 CLI runner의 engine/data loading protocol 차이
6. 실패 후 shared memory cleanup이 Windows에서 완전히 해제되지 않는 이유
```
