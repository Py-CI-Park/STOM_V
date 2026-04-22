# CLI Data Loading Timeout Smoke Pilot

## 목적

CLI baseline이 data loading 단계에서 외부 timeout까지 멈추는 문제를 구조화된 success/error JSON으로 전환할 수 있는지 확인했다.

## 이전 실패 증거

```text
CLI baseline command=FAIL
external_timeout_ms=964079
result_json_created=False
new_csv_created=False
shared_memory_remaining=backdata_0..31
```

## 변경 후 기대

```text
success 또는 error JSON 반환
last_checkpoint 존재
engine_data_loading 필드 존재 또는 success/error checkpoint 존재
외부 timeout 없이 종료
```

## 실행 환경 주의

feature worktree에는 `_database`가 없어서 legacy `utility.setting`이 상대경로 `_database/setting.db`를 읽을 수 없다. 따라서 실행 전 `wt-dev`의 작은 runtime DB를 feature worktree로 복사했다.

```text
copied_runtime_db:
  _database/strategy.db
  _database/setting.db
  _database/backtest.db

stock_tick_back.db:
  STOM_CLI_DATABASE_DIR=C:\System_Trading\STOM\STOM_V.wt-dev\_database
```

이는 runtime 산출물 준비이며 Git에 커밋하지 않는다.

## smoke 32엔진 결과

명령:

```text
20250102~20250103 tick avg_time=30 engines=32 timeout=300
```

결과:

```text
command_exit_code=2
json_exists=True
status=error
message=backtest completed without metrics
checkpoint_status=error
last_checkpoint=csv_detected
engine_data_loading=not_present
csv_path=None
elapsed_seconds=75.063
checkpoints_count=48
```

주요 checkpoint:

```text
engine_processes_started
moneytop_loaded
engine_data_load_requested
engine_data_response_wait_started
engine_data_response_received x32
shared_data_loaded
engine_data_load_completed
back_count_ready
backtest_process_started
backtest_process_finished
csv_detected
shared_memory_cleanup_started
shared_memory_cleanup_completed
```

해석:

```text
data loading 단계는 32개 engine 응답을 모두 수집했다.
외부 timeout 없이 JSON error를 반환했다.
다음 실패 지점은 BackTest 내부 moneytop table 의존성이다.
```

BackTest child traceback 요약:

```text
sqlite3.OperationalError: no such table: moneytop
pandas.errors.DatabaseError:
SELECT * FROM moneytop WHERE `index` >= 20250102090030 AND `index` <= 20250103092800
```

## smoke 4엔진 결과

명령:

```text
20250102~20250103 tick avg_time=30 engines=4 timeout=300
```

결과:

```text
command_exit_code=2
json_exists=True
status=error
message=backtest completed without metrics
checkpoint_status=error
last_checkpoint=csv_detected
engine_data_loading=not_present
csv_path=None
elapsed_seconds=36.516
checkpoints_count=20
```

해석:

```text
engine 수를 4로 줄여도 같은 moneytop table 문제로 실패했다.
따라서 최초 외부 timeout 문제는 engine fan-out 자체보다 data loading 이후 BackTest protocol/DB 의존성 문제로 좁혀졌다.
```

## 2025 전체 재시도 결과

명령:

```text
20250101~20251231 tick avg_time=30 engines=32 timeout=900
```

결과:

```text
executed=yes
command_exit_code=2
json_exists=True
status=error
message=backtest completed without metrics
checkpoint_status=error
last_checkpoint=csv_detected
engine_data_loading=not_present
csv_path=None
elapsed_seconds=76.203
checkpoints_count=48
```

해석:

```text
2025 전체 조건에서도 외부 timeout 없이 구조화된 error JSON을 반환했다.
data loading은 완료되고 BackTest child가 시작된 뒤, moneytop table 누락으로 결과 metrics가 생성되지 않았다.
```

## shared memory cleanup 확인

세 실행 이후 Python 백테스트 프로세스 잔여는 확인되지 않았다.

```text
python_process_remaining=False
```

다만 `backdata_0..31` shared memory 이름은 실행 후에도 관측되었다. 수동 `unlink()`를 시도했지만 Windows에서 동일 이름이 계속 관측되었다.

```text
shared_memory_remaining=backdata_0..31
manual_unlink_attempted=True
remaining_after_cleanup=backdata_0..31
```

이는 후속 작업에서 별도로 다뤄야 한다.

## 판정

이번 작업의 목적은 data loading hang을 외부 timeout 없이 구조화된 JSON으로 전환하는 것이었다.

```text
decision=PASS_FOR_DATA_LOADING_TIMEOUT_FIX
reason=Smoke 32, smoke 4, and 2025 full retry all returned structured error JSON before external timeout. Data loading completed and the next blocker is BackTest moneytop table dependency.
```

후보 5개 실행 관점에서는 아직 PASS가 아니다.

```text
candidate_count_5_gate=BLOCKED
reason=CLI baseline still does not produce metrics or CSV.
```

## 다음 단계

```text
$brainstorming CLI BackTest moneytop table dependency 및 GUI runner protocol 차이 설계
```

다음 분석에서 확인할 항목:

```text
1. BackTest.Start()가 moneytop을 어느 DB에서 읽는지
2. GUI/STOM에서는 moneytop table이 언제/어디에 준비되는지
3. CLI runner는 moneytop을 stock_tick_back.db에서 읽고 BackTest child는 다른 DB를 읽는지
4. BackTest child process에 CLI runtime DB 경로를 어떻게 전달해야 하는지
5. moneytop table 의존성을 없애거나 동일 데이터를 넘기는 더 안전한 방법
6. shared memory cleanup이 Windows에서 이름을 계속 남기는 이유
```
