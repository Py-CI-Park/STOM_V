# 2026-04-22 CLI Runner Data Loading Timeout Design

## 목적

이번 설계의 목적은 CLI baseline 백테스트가 data loading 단계에서 무한 대기하지 않도록 만들고, 실패하더라도 JSON/checkpoint로 어디서 멈췄는지 기록하게 만드는 것이다.

이번 작업은 조건식 개선이 아니다. 이번 작업은 AI/CLI 자동 연구 루프의 기반인 CLI 백테스트 실행 경로를 안정화하는 작업이다.

```text
[완료] GUI Wide v1 백테스트 성공
        |
        v
[완료] CLI runtime-preflight 성공
        |
        v
[실패] CLI baseline 1회 백테스트
        |
        v
[이번 설계] data loading timeout / checkpoint 보강
        |
        v
[다음] smoke 재현
        |
        v
[그 다음] 2025 전체 baseline 재시도
```

## 배경

이전 PR #15에서 `runtime-preflight`를 추가해 CLI가 `wt-dev` runtime DB와 ResearchTest wide 조건식을 정상 확인할 수 있게 했다.

그 다음 단계로 Wide v1 CLI baseline gate를 실행했다.

결과:

```text
runtime-preflight=PASS
CLI baseline command=FAIL
external_timeout_ms=964079
result_json_created=False
new_csv_created=False
shared_memory_remaining=backdata_0..31
```

중요한 점은 preflight가 통과했다는 것이다.

```text
strategy.db 정상
setting.db 정상
backtest.db 정상
stock_tick_back.db table_probe_only 통과
buy strategy 정상
sell strategy 정상
```

따라서 이번 실패는 조건식/DB 사전검증 실패가 아니라, CLI runner의 실제 실행 경로에서 발생한 blocking 문제로 본다.

## 현재 실패 가설

현재 가장 유력한 실패 지점은 `cli/runner.py`의 data loading 응답 수집 구간이다.

현재 구조:

```python
shared_info.clear()
for i in range(multi):
    shared_info_ = backQ.get()
    shared_info += shared_info_
```

이 구간에는 timeout이 없다. 일부 engine process가 응답하지 않으면 parent process가 `backQ.get()`에서 계속 대기할 수 있다.

현재 `--timeout`은 뒤쪽의 `proc_backtest.join(timeout=timeout)`에 적용된다. 따라서 BackTest process를 시작하기 전 data loading 단계에서 멈추면 `--timeout`으로 빠져나오지 못한다.

```text
[engine process 시작]
        |
        v
[engine별 데이터 로딩 요청]
        |
        v
[parent가 backQ.get()으로 응답 수집]
        |
        v
[일부 engine 응답 누락 시 blocking]
        |
        v
[BackTest process 시작 전이므로 --timeout join 단계에 도달하지 못함]
```

## 설계 목표

1. data loading 단계의 무한 대기를 방지한다.
2. engine별 응답 수집 상태를 checkpoint로 기록한다.
3. timeout 발생 시 `status=error` JSON을 반환한다.
4. 실패 시 `expected_count`, `received_count`, `missing_count`, `timeout_seconds`를 기록한다.
5. shared memory cleanup 시도와 결과를 기록한다.
6. smoke 조건과 2025 전체 조건에서 재현 결과를 문서화한다.

## 비목표

- 이번 단계에서 `candidate_count=5`를 실행하지 않는다.
- 조건식을 개선하지 않는다.
- WFO 또는 `discovery promote`를 실행하지 않는다.
- GUI 코드를 수정하지 않는다.
- CLI runner 전체를 재작성하지 않는다.
- 수익률 또는 best_candidate를 평가하지 않는다.

## 핵심 변경 방향

### 1. data loading deadline

data loading 메시지를 engine queue에 보낸 직후 deadline을 시작한다.

```python
timeout = getattr(config, 'timeout', 3600) or 3600
data_load_deadline = time.time() + timeout
```

그 다음 engine 응답을 수집할 때 남은 시간을 계산한다.

```python
remaining = data_load_deadline - time.time()
if remaining <= 0:
    return data_loading_timeout_result
shared_info_ = backQ.get(timeout=remaining)
```

이 방식은 전체 `config.timeout`을 data loading 단계에도 적용한다.

### 2. engine 응답 수집 상태

추적할 값:

```text
expected_count = multi
received_count = 0
missing_count = expected_count - received_count
received_lengths = []
```

응답을 받을 때마다:

```text
received_count += 1
received_lengths.append(len(shared_info_))
```

### 3. timeout 예외 처리

`multiprocessing.Queue().get(timeout=...)`는 timeout 시 `queue.Empty`를 발생시킨다.

따라서 runner에서 아래 import가 필요하다.

```python
from queue import Empty
```

timeout 시 결과는 error JSON으로 반환한다.

```python
result['status'] = 'error'
result['message'] = 'engine data loading timed out'
result['engine_data_loading'] = {
    'expected_count': multi,
    'received_count': received_count,
    'missing_count': multi - received_count,
    'timeout_seconds': timeout,
}
result.update(checkpoint.to_result_fields(status='error'))
return result
```

## 추가 checkpoint

`cli/runner.py`에 아래 checkpoint를 추가한다.

```text
engine_processes_started
engine_data_load_requested
engine_data_response_wait_started
engine_data_response_received
engine_data_response_timeout
engine_data_load_completed
shared_memory_cleanup_started
shared_memory_cleanup_completed
```

각 checkpoint detail 예:

```text
engine_processes_started:
  engine_count

engine_data_load_requested:
  expected_count
  data_list_count
  avg_list

engine_data_response_wait_started:
  expected_count
  timeout_seconds

engine_data_response_received:
  expected_count
  received_count
  response_index
  chunk_count

engine_data_response_timeout:
  expected_count
  received_count
  missing_count
  timeout_seconds

engine_data_load_completed:
  back_count
  expected_count
  received_count
```

## 실패 JSON 구조

data loading timeout 발생 시 최소 아래 형태의 JSON이 나와야 한다.

```json
{
  "status": "error",
  "message": "engine data loading timed out",
  "checkpoint_status": "error",
  "last_checkpoint": "engine_data_response_timeout",
  "engine_data_loading": {
    "expected_count": 32,
    "received_count": 17,
    "missing_count": 15,
    "timeout_seconds": 300
  },
  "checkpoints": []
}
```

이 결과가 있으면 다음 분석에서 어떤 engine 응답 수집이 누락됐는지 판단할 수 있다.

## cleanup 설계

기존 `finally` 구조는 유지한다.

```python
finally:
    _cleanup_shared_memory(shared_info)
    _drain_queues(all_queues + back_sques + back_eques)
    drainer.stop()
    drainer.join(timeout=2)
    _cleanup_procs()
```

다만 cleanup 시작/완료 checkpoint를 남긴다.

```text
shared_memory_cleanup_started
shared_memory_cleanup_completed
```

주의:

```text
shared_info가 일부만 수집된 상태일 수 있다.
cleanup은 partial shared_info에서도 안전해야 한다.
```

이번 설계에서는 cleanup 함수 전체를 재작성하지 않는다. 우선은 cleanup 시도 여부와 결과를 기록하는 것이 목적이다.

## 재현/검증 순서

구현 후 실제 CLI 명령은 세 단계로 실행한다.

### 1. 짧은 smoke + engines=32

목적:

```text
32개 engine fan-out 자체가 짧은 기간에서도 blocking되는지 확인
```

명령:

```powershell
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250102 `
  --end 20250103 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 300 `
  --format json `
  -o backtest\temp\wide_v1_cli_smoke_32_20260422.json
```

### 2. 짧은 smoke + engines=4

목적:

```text
engine 수를 줄이면 통과하는지 확인
```

명령:

```powershell
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250102 `
  --end 20250103 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 4 `
  --timeout 300 `
  --format json `
  -o backtest\temp\wide_v1_cli_smoke_4_20260422.json
```

### 3. 2025 전체 + engines=32

smoke 결과가 의미 있게 나오면 기존 실패 조건을 다시 실행한다.

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
  -o backtest\temp\wide_v1_cli_baseline_retry_20260422.json
```

## 결과 판정

### 성공

```text
status=success
csv_path 존재
checkpoint_status=success
last_checkpoint=csv_detected 또는 이후
```

다음 단계:

```text
GUI 결과와 비교
```

### 구조화된 실패

```text
status=error
checkpoint_status=error
last_checkpoint=engine_data_response_timeout
engine_data_loading.expected_count 존재
engine_data_loading.received_count 존재
engine_data_loading.missing_count 존재
```

이번 작업 관점에서는 구조화된 실패도 성공적인 진단 결과다.  
현재 문제는 실패 자체가 아니라, 실패가 JSON/checkpoint 없이 외부 timeout으로 끝난다는 점이었기 때문이다.

### 비구조화 실패

```text
외부 timeout
JSON 없음
CSV 없음
프로세스 잔여
shared memory 잔여
```

이 경우 이번 작업은 실패다. 더 앞단계 lifecycle 계측이 필요하다.

## 테스트 전략

heavy tick 백테스트를 unit test에 넣지 않는다.

대신 `tests/unit/test_runner_helpers.py`에서 source contract를 추가한다.

검증할 내용:

```text
queue.Empty 처리
backQ.get(timeout=...) 사용
engine_data_response_wait_started checkpoint
engine_data_response_received checkpoint
engine_data_response_timeout checkpoint
engine_data_loading result field
timeout 시 status='error' 반환
```

기존 runner helper tests가 source contract 방식이므로 이번 보강도 같은 패턴을 따른다.

## 문서화 산출물

### update log

```text
docs/update_log/2026-04-22_cli_runner_data_loading_timeout.md
```

포함 내용:

```text
왜 이 작업이 필요한가
이전 실패 증거
추가한 checkpoint
추가한 timeout
테스트 결과
smoke 실행 결과
남은 리스크
```

### pilot log

```text
docs/research/condition_research/pilot_logs/2026-04-22_cli_data_loading_timeout_smoke.md
```

포함 내용:

```text
smoke 32엔진 결과
smoke 4엔진 결과
2025 전체 재시도 결과
각 결과의 status/checkpoint/engine_data_loading
shared memory cleanup 결과
다음 판단
```

## Git 포함/제외

커밋 포함:

```text
cli/runner.py
tests/unit/test_runner_helpers.py
docs/update_log/2026-04-22_cli_runner_data_loading_timeout.md
docs/research/condition_research/pilot_logs/2026-04-22_cli_data_loading_timeout_smoke.md
```

커밋 제외:

```text
backtest/temp/*.json
backtest/csv/*.csv
backtest/graph/
_database/*.db
shared memory 관련 임시 파일
```

## 성공 기준

이번 작업의 성공 기준:

```text
1. data loading hang이 외부 timeout까지 가지 않는다.
2. 성공 또는 구조화된 error JSON을 반환한다.
3. last_checkpoint가 남는다.
4. data loading timeout이면 engine_data_loading 필드가 남는다.
5. smoke 결과가 pilot log에 기록된다.
6. focused tests와 verify_nonrelease_sync.py가 통과한다.
```

## 실패 후 분기

### smoke 32 실패, smoke 4 성공

```text
engine fan-out 문제 가능성
        |
        v
engine_count별 안정 범위 설계
```

### smoke 32 실패, smoke 4도 실패

```text
CLI runner protocol 문제 가능성
        |
        v
GUI runner와 CLI runner message protocol 비교
```

### smoke 32 성공, 2025 전체 실패

```text
대형 데이터량 또는 특정 일자/종목 문제 가능성
        |
        v
날짜 이분 탐색 / data segment 분석
```

### 2025 전체 성공

```text
baseline gate 재시도
        |
        v
GUI 결과 비교
        |
        v
candidate_count=5 설계 가능
```

## 다음 단계

이 spec이 승인되면 다음 단계는 `writing-plans`다.

예상 계획 제목:

```text
CLI Runner Data Loading Timeout 실행 계획
```

예상 작업 단위:

```text
Task 1: runner data loading timeout source contract test 작성
Task 2: cli/runner.py data loading deadline/checkpoint 구현
Task 3: focused unit 검증
Task 4: smoke 32/4 실행
Task 5: 2025 전체 재시도
Task 6: pilot log/update_log 작성
```

후보 5개 실행은 이번 작업 결과가 success 또는 구조화된 실패로 문서화된 뒤 별도 브레인스토밍에서 결정한다.
