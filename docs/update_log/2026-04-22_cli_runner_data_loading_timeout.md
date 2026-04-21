# 2026-04-22 CLI Runner Data Loading Timeout

## 목적

CLI baseline 백테스트가 data loading 단계에서 JSON 없이 멈추는 문제를 막기 위해, data loading 응답 수집 구간에 timeout과 checkpoint를 추가했다.

## 이전 문제

Wide v1 CLI baseline gate에서 아래 실패가 확인됐다.

```text
runtime-preflight=PASS
CLI baseline command=FAIL
external_timeout_ms=964079
result_json_created=False
new_csv_created=False
shared_memory_remaining=backdata_0..31
```

가장 의심되는 지점은 `cli.runner.run_backtest()`의 data loading 응답 수집 구간이었다.

```python
for i in range(multi):
    shared_info_ = backQ.get()
```

이 구간에는 timeout이 없었고, `--timeout`은 뒤쪽 BackTest process join 단계에만 적용됐다.

## 변경 사항

- `backQ.get(timeout=remaining)` 적용
- `queue.Empty` 처리
- `engine_data_response_*` checkpoint 추가
- `engine_data_loading` structured error field 추가
- error/success JSON에서 checkpoint 진단 필드 보존
- BackTest가 metrics를 생성하지 못한 경우 success가 아니라 error로 반환
- shared memory cleanup checkpoint 추가

## 검증

```text
test_runner_helpers.py=38 passed
test_backtest_checkpoints.py + test_runner_helpers.py=41 passed
test_output.py + test_runner_helpers.py=84 passed
focused_tests=166 passed
verify_nonrelease_sync=PASS
smoke_32=error_json_returned
smoke_4=error_json_returned
full_retry=error_json_returned
```

## smoke 결과 요약

```text
smoke_32:
  command_exit_code=2
  status=error
  message=backtest completed without metrics
  last_checkpoint=csv_detected
  elapsed_seconds=75.063

smoke_4:
  command_exit_code=2
  status=error
  message=backtest completed without metrics
  last_checkpoint=csv_detected
  elapsed_seconds=36.516

full_retry_2025:
  command_exit_code=2
  status=error
  message=backtest completed without metrics
  last_checkpoint=csv_detected
  elapsed_seconds=76.203
```

## 판정

```text
decision=PASS_FOR_DATA_LOADING_TIMEOUT_FIX
reason=세 실행 모두 외부 timeout 없이 구조화된 error JSON을 반환했다. data loading은 완료됐고 다음 병목은 BackTest moneytop table 의존성이다.
```

후보 5개 실행은 아직 금지한다.

```text
candidate_count_5_gate=BLOCKED
reason=CLI baseline still does not produce metrics or CSV.
```

## 남은 리스크

- BackTest child process가 `moneytop` table을 기대하지만 현재 CLI 실행 경로에서는 해당 table이 준비되지 않는다.
- CLI runner는 stock tick DB에서 moneytop 성격 데이터를 읽지만, BackTest child는 다른 DB의 `moneytop` table을 조회하는 것으로 보인다.
- GUI/STOM 실행에서는 백테스트 엔진 구동 또는 GUI protocol 중 `moneytop` table이 준비될 가능성이 있다.
- `backdata_0..31` shared memory 이름이 manual unlink 이후에도 관측된다.
- candidate_count=5는 아직 실행하면 안 된다.

## 다음 단계

```text
$brainstorming CLI BackTest moneytop table dependency 및 GUI runner protocol 차이 설계
```

다음 브레인스토밍에서 결정할 것:

```text
1. BackTest.Start()의 moneytop DB 의존성 분석
2. GUI runner가 moneytop을 준비하는 위치 확인
3. CLI runner가 BackTest child에 같은 데이터를 전달하지 못하는 이유 확인
4. moneytop table을 생성/전달/우회하는 최소 수정 방향
5. shared memory cleanup 잔여 원인 분석
```
