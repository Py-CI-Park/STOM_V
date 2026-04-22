# 2026-04-22 CLI BackTest Process Timeout 및 결과 생성 Protocol 분석 설계

## 목적

이번 설계의 목적은 CLI 백테스트가 `backtest_process_started` 이후 `BackTest` process timeout으로 끝나는 원인을 구조적으로 확인하는 것이다.

현재까지 확인된 문제는 더 이상 `moneytop` 테이블 부재나 child runtime DB 경로 불일치가 아니다. `feature/cli-child-runtime-db-override` smoke 4/32에서 데이터 로딩은 완료됐고, BackTest child는 시작됐으며, child moneytop diagnostic은 발생하지 않았다. 남은 병목은 `BackTest.Start()` 이후 결과 생성 protocol이다.

```text
[GUI Wide v1 백테스트 성공]
        |
        v
[CLI runtime-preflight 성공]                 완료
        |
        v
[CLI data loading timeout 구조화]            완료
        |
        v
[BackTest child moneytop 진단]               완료
        |
        v
[child runtime DB override 전달]             완료 판단
        |
        v
[이번 설계] BackTest process timeout 원인 계측
        |
        v
[다음] CLI baseline metrics/CSV 생성
        |
        v
[그 다음] GUI 결과와 CLI 결과 비교
        |
        v
[그 다음] 조건 자동 탐색 후보 백테스트 실행
```

최종 목표는 사람이 GUI에서 하던 “엔진 준비 -> 조건식 선택 -> 백테스트 실행 -> 결과 확인” 과정을 CLI에서도 동일 조건으로 반복 가능하게 만드는 것이다. 그래야 AI/자동화가 조건식 생성, 백테스트, 결과 분석, 조건식 개선 루프를 안정적으로 수행할 수 있다.

## 현재 증거

`feature/cli-child-runtime-db-override`의 최신 smoke 결과:

```text
smoke_4:
  status=error
  checkpoint_status=timeout
  last_checkpoint=backtest_process_started
  engine_data_loading=not_present
  backtest_child_diagnostics=not_present
  csv_path=None
  elapsed_seconds=329.453

smoke_32:
  status=error
  checkpoint_status=timeout
  last_checkpoint=backtest_process_started
  engine_data_loading=not_present
  backtest_child_diagnostics=not_present
  csv_path=None
  elapsed_seconds=352.657
```

해석:

```text
1. engine/data loading 단계는 통과했다.
2. child DB/moneytop 오류는 재현되지 않았다.
3. BackTest process는 시작됐다.
4. parent CLI는 BackTest process가 내부 어디에서 멈췄는지 모른다.
5. metrics/CSV는 아직 생성되지 않았다.
```

## GUI와 CLI protocol 비교

GUI의 실제 실행 흐름은 두 단계다.

```text
GUI:
  1. 백테스트 엔진 시작
     ui_backtest_engine.backengine_start()
       -> BackSubTotal 20개 생성
       -> BackEngine N개 생성
       -> 종목명 전달
       -> 데이터로딩 전달
       -> shared_info 수집
       -> 공유데이터 전달
       -> "백테엔진 준비 완료"

  2. 백테스트 버튼 실행
     stock_backtest_start()
       -> clear_backtestQ()
       -> engine에 "백테유형=백테스트" 전달
       -> backQ에 조건식/기간/시간/전략 전달
       -> BackTest process 시작
       -> GUI 로그 consumer가 windowQ를 계속 소비
```

현재 CLI는 이 두 단계를 한 번의 `run_backtest()` 안에서 재구성한다.

```text
CLI:
  run_backtest()
    -> BackSubTotal 20개 생성
    -> BackEngine N개 생성
    -> 종목명 전달
    -> 데이터로딩 전달
    -> shared_info 수집
    -> 공유데이터 전달
    -> "백테유형=백테스트" 전달
    -> backQ에 조건식/기간/시간/전략 전달
    -> BackTest process 시작
    -> proc_backtest.join(timeout)
```

현재까지는 CLI가 GUI protocol을 충분히 따라가고 있지만, BackTest 내부 완료 신호까지는 관측하지 못한다.

## 실패 가능 지점

`BackTest.Start()`의 핵심 흐름:

```text
BackTest.Start()
  -> backQ.get()으로 실행조건 수신
  -> moneytop 재조회
  -> 보유종목수 배열 생성
  -> 전략코드 로딩
  -> Total process 생성
  -> totalQ에 "백테정보" 전달
  -> bstq_list에 "백테시작" 전달
  -> beq_list에 전략 실행 data 전달
  -> mq.get()으로 완료 신호 대기
```

현재 parent CLI는 `proc_backtest.join(timeout)`만 보고 있으므로, 아래 중 어느 지점이 원인인지 알 수 없다.

```text
1. BackTest child가 backQ 실행조건을 받지 못함
2. BackTest child가 moneytop 재조회 또는 전략코드 로딩에서 멈춤
3. Total process가 시작되지 않음
4. engine worker가 "백테시작" 이후 결과를 보내지 않음
5. BackSubTotal이 "수집완료" 또는 "백테결과"를 보내지 않음
6. Total이 결과를 받았지만 Report/DB/CSV 저장에서 멈춤
7. Report가 완료됐지만 BackTest.Start()의 두 번째 `mq.get()` 대기에서 멈춤
8. 메시지는 생성됐지만 CLI parent가 timeout 전에 관측하지 못함
```

## 접근안

### A. 내부 protocol checkpoint 계측 추천

BackTest child, Total, BackSubTotal의 주요 protocol 경계에 checkpoint를 남기고, CLI parent가 timeout 시에도 해당 진단을 JSON에 포함하도록 한다.

장점:

```text
원인을 추측하지 않고 어느 queue/protocol 경계에서 멈췄는지 확인 가능
GUI 기본 동작을 바꾸지 않고 CLI 진단만 강화 가능
다음 구현에서 작은 수정 단위로 진행 가능
```

단점:

```text
진단 queue를 잘못 소비하면 기존 engine/Total protocol을 방해할 수 있음
parent가 소비해도 안전한 채널을 신중하게 선택해야 함
```

판단: 추천한다. 지금은 기능 확장보다 실패 지점 계측이 먼저다.

### B. timeout을 크게 늘려 재시도

`--timeout 1800` 또는 `--timeout 3600`으로 늘려서 기다린다.

장점:

```text
코드 수정이 없다.
실제 heavy run이 단순히 느린 것인지 빠르게 확인할 수 있다.
```

단점:

```text
사용자 GUI 1년 Wide v1은 약 1분에 끝났으므로 2일 smoke가 300초를 넘기는 것은 단순 runtime 문제로 보기 어렵다.
timeout만 늘리면 자동 연구 루프가 다시 원인 없는 장기 대기에 빠진다.
```

판단: 보조 확인으로만 사용한다. 근본 설계로 삼지 않는다.

### C. CLI를 GUI처럼 persistent engine/session 구조로 재작성

CLI도 GUI처럼 엔진 준비 명령과 백테스트 실행 명령을 분리하고, persistent process session을 유지한다.

장점:

```text
GUI protocol과 가장 유사하다.
후보 N개 반복 백테스트에서는 엔진 재사용 가능성이 있다.
```

단점:

```text
현재 timeout 원인을 모른 채 구조를 크게 바꾸게 된다.
이번 단계의 범위를 넘고 회귀 위험이 크다.
```

판단: 장기 후보로 남긴다. 이번 단계에서는 A안으로 원인을 확정한 뒤 결정한다.

## 권장 설계

이번 단계는 A안을 채택한다.

### 1. BackTest child checkpoint 추가

`backtest/backtest.py`의 `BackTest.Start()`에 CLI 진단용 checkpoint를 추가한다. GUI 동작을 바꾸지 않도록, 기존 queue protocol에 영향을 주지 않는 별도 helper를 사용한다.

예상 checkpoint:

```text
backtest_child_started
backtest_child_config_received
backtest_child_moneytop_loaded
backtest_child_subtotal_info_sent
backtest_child_strategy_loaded
backtest_child_total_process_started
backtest_child_total_info_sent
backtest_child_engine_start_sent
backtest_child_engine_data_sent
backtest_child_waiting_mq_first
backtest_child_mq_first_received
backtest_child_waiting_mq_second
backtest_child_completed
```

### 2. Total process checkpoint 추가

`backtest/backtest.py`의 `Total.MainLoop()`와 `Total.Report()`에 최소 checkpoint를 추가한다.

예상 checkpoint:

```text
total_process_started
total_info_received
total_engine_done_count
total_subtotal_collection_done_count
total_result_received
total_report_started
total_report_no_trades
total_report_db_written
total_report_csv_written
total_report_mq_sent
```

중요한 관찰 포인트:

```text
BackSubTotal.SendSubTotal()은 결과가 없으면 ('결과없음',)을 totalQ에 보낸다.
현재 Total.MainLoop()는 ('결과없음',)을 명시 처리하지 않는다.
2일 smoke에서 거래가 없거나 일부 subtotal에 결과가 없는 경우,
이 경로가 mq 완료 신호 부재로 이어지는지 확인해야 한다.
```

이 부분은 아직 확정 원인이 아니다. 구현 전 계측으로 먼저 검증한다.

### 3. CLI parent timeout JSON 보강

`cli/runner.py`는 timeout이 발생하면 process를 kill한 뒤 관측 가능한 diagnostic queue를 drain하여 JSON에 포함한다.

원칙:

```text
실행 중인 totalQ/beq/bstq를 parent가 임의로 소비하지 않는다.
완료 또는 timeout 후에만 안전하게 drain한다.
기존 engine/Total protocol 메시지를 뺏어가지 않는다.
```

JSON 예시:

```json
{
  "status": "error",
  "checkpoint_status": "timeout",
  "last_checkpoint": "backtest_process_started",
  "backtest_process_diagnostics": {
    "last_child_checkpoint": "backtest_child_waiting_mq_first",
    "total_last_checkpoint": "total_engine_done_count",
    "observed_messages": [...]
  }
}
```

### 4. smoke 범위

이번 구현은 full-year를 바로 목표로 하지 않는다. 먼저 짧은 smoke에서 “timeout 원인 위치”가 JSON에 남는지 확인한다.

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
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
  -o backtest\temp\wide_v1_cli_process_timeout_protocol_smoke_4_20260422.json
```

그 다음 32 engine smoke를 실행한다.

```text
smoke_4: 원인 위치 확인
smoke_32: GUI 조건과 같은 engine 수에서 원인 위치 확인
```

full-year 실행은 아래 조건 이후에만 진행한다.

```text
1. smoke가 metrics/CSV를 생성하거나
2. timeout이어도 내부 protocol checkpoint가 충분히 남거나
3. 명확한 수정 후보가 확인된 경우
```

## 성공 기준

이번 단계의 성공 기준:

```text
1. CLI timeout JSON에 BackTest child 내부 마지막 진행 지점이 남는다.
2. Total/BackSubTotal/engine 완료 흐름 중 어느 지점에서 멈췄는지 식별된다.
3. 기존 GUI protocol은 변경하지 않는다.
4. 기존 단위 테스트가 통과한다.
5. smoke 4/32 결과가 pilot log와 update_log에 기록된다.
```

성공은 곧바로 “CLI 백테스트 완료”를 의미하지 않는다. 이번 단계의 1차 성공은 원인 위치를 확정하는 것이다. 원인이 확인되면 다음 PR에서 최소 수정으로 metrics/CSV 생성까지 연결한다.

## 비목표

```text
candidate_count=5 실행하지 않음
조건식 개선 루프 실행하지 않음
WFO/promote 실행하지 않음
GUI 코드를 대규모 변경하지 않음
CLI persistent engine session을 이번 단계에서 구현하지 않음
runtime DB/CSV/graph/temp JSON을 커밋하지 않음
```

## 남은 리스크

1. `multiprocessing.Queue.empty()` 의존 구간이 실제 원인일 수 있다. 이 경우 단순 checkpoint만으로는 재현이 흔들릴 수 있다.
2. parent가 잘못된 queue를 실행 중에 drain하면 기존 protocol을 깨뜨릴 수 있다. timeout 후 수집으로 제한해야 한다.
3. smoke 기간에 거래가 없으면 “결과 없음 처리” 문제가 먼저 드러날 수 있다. 이것도 중요한 원인 후보지만 full-year 결과와 별도로 해석해야 한다.
4. GUI는 windowQ consumer와 UI 상태가 계속 살아 있고, CLI는 headless one-shot이다. 단순 함수 호출 순서가 같아도 process lifetime 차이가 남을 수 있다.
5. 이번 단계는 원인 분석 계측이므로, CLI와 GUI 결과 동일성 검증은 다음 단계로 남는다.

## 다음 단계

이 spec이 승인되면 `writing-plans`로 구현 계획을 작성한다.

권장 명령:

```text
$writing-plans CLI BackTest process timeout 및 결과 생성 protocol 계측 구현 계획 작성
```

예상 작업 단위:

```text
Task 1: timeout diagnostic contract test 작성
Task 2: BackTest child checkpoint helper 추가
Task 3: Total/Report checkpoint 추가
Task 4: CLI parent timeout JSON diagnostic 수집
Task 5: smoke 4/32 실행 및 pilot/update log 작성
Task 6: focused/full unit tests 및 verify_nonrelease_sync 실행
```

그 다음 라우팅:

```text
원인이 mq/Total/BackSubTotal protocol이면:
  $brainstorming CLI BackTest 결과 완료 protocol 수정 설계

smoke가 metrics/CSV를 생성하면:
  $brainstorming Wide v1 CLI Baseline Backtest Gate 및 GUI 결과 비교 설계

계측 후에도 원인 위치가 불명확하면:
  $brainstorming CLI persistent engine session 전환 설계
```
