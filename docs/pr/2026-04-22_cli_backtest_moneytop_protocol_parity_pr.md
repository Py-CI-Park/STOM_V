# CLI BackTest Moneytop Protocol Parity PR 보고서

## 1. 이번 PR의 목적

이번 PR은 CLI 백테스트가 GUI/STOM 백테스트와 같은 실행 protocol을 재현하지 못하는 원인을 `moneytop` 의존성과 parent/child runtime DB 경로 관점에서 확인할 수 있도록 진단 기반을 추가한다.

이번 PR은 후보 조건식 개선, `candidate_count=5`, WFO, promote 작업이 아니다. 이번 PR의 목적은 CLI 백테스트 실패 원인을 더 이상 추정하지 않고, JSON 결과에서 확인 가능하게 만드는 것이다.

```text
[GUI Wide v1 백테스트 성공]
        |
        v
[CLI runtime-preflight 성공]
        |
        v
[CLI data loading hang 구조화]
        |
        v
[이번 PR] BackTest child moneytop 진단 노출
        |
        v
[다음] child runtime DB override 전달 설계
        |
        v
[그 다음] CLI baseline 재시도 / GUI 결과 비교
```

## 2. 전체 계획에서 현재 단계

전체 자동 조건식 연구 흐름에서 현재 위치는 아래와 같다.

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
[8. CLI/GUI Tick Backtest Parity Preflight]
        |
        v
[9. CLI data loading hang 구조화]
        |
        v
[10. BackTest child moneytop protocol 진단]  <- 이번 PR
        |
        v
[11. child runtime DB override 전달]
        |
        v
[12. CLI baseline 재시도 / GUI 결과 비교]
        |
        v
[13. Wide v1 Retention-Aware 후보 5개 실행]
```

이번 PR은 10번 단계다. 아직 CLI baseline이 GUI와 동일한 metrics/CSV를 생성한 것은 아니다.

## 3. 이전 문제 요약

### 3.1 CLI preflight는 통과

PR #15 이후 `runtime-preflight`는 통과했다.

```text
status=ok
failed_checks=[]
strategy_db=ok
setting_db=ok
stock_tick_back.db=table_probe_only
buy_strategy=ok
sell_strategy=ok
```

### 3.2 CLI data loading hang은 개선

이전 단계에서 CLI가 data loading 단계에서 외부 timeout까지 무응답이던 문제는 개선했다.

```text
이전:
  외부 timeout
  JSON 없음
  CSV 없음
  last_checkpoint 없음

개선 후:
  JSON error 반환
  checkpoint 기록
  data loading 완료 여부 확인 가능
```

### 3.3 새로 확인된 문제: BackTest child moneytop

data loading 이후 BackTest child가 `moneytop` 테이블을 찾지 못했다.

```text
sqlite3.OperationalError: no such table: moneytop
```

이번 PR은 이 실패를 JSON에 명확히 노출한다.

## 4. 이번 PR의 변경 사항

### 4.1 과거 CLI 검증 범위 재분류 문서

추가:

```text
docs/research/condition_research/pilot_logs/2026-04-22_cli_historical_validation_review.md
```

핵심 내용:

```text
Level 0: Parser / dry-run
Level 1: Mocked runner
Level 2: Actual CLI backtest execution
Level 3: GUI/CLI result parity with back_count/trade_count
```

현재 Wide v1 자동 연구 루프에 필요한 것은 Level 3이며, 과거 기록만으로는 이 조건을 모두 충족한다고 보기 어렵다는 점을 정리했다.

### 4.2 GUI/CLI protocol diff 문서

추가:

```text
docs/research/condition_research/pilot_logs/2026-04-22_gui_cli_backtest_protocol_diff.md
```

핵심 차이:

```text
GUI:
  engine start 단계에서 moneytop 조회
  shared_info/back_count 준비
  준비된 엔진으로 백테스트 실행

CLI:
  parent가 moneytop 조회
  data loading 완료
  BackTest child 실행
  child가 다시 moneytop 조회
```

### 4.3 BackTest child moneytop diagnostic 추가

수정:

```text
backtest/backtest.py
cli/runner.py
cli/output.py
```

BackTest child가 moneytop 조회에 실패하면 아래 진단 정보를 queue로 전달하고, CLI JSON이 이를 보존한다.

```json
{
  "backtest_child_diagnostics": {
    "stock_back_db_path": "./_database/stock_tick_back.db",
    "moneytop_query_status": "error",
    "moneytop_error": "no such table: moneytop",
    "startday": 20250102,
    "endday": 20250103,
    "starttime": 90000,
    "endtime": 92800,
    "ui_gubun": "S"
  }
}
```

### 4.4 data-loading timeout 기반 통합

이 브랜치는 `feature/cli-runner-data-loading-timeout` 기반도 통합한다.

포함 내용:

```text
backQ.get(timeout=...)
engine_data_response_* checkpoint
engine_data_loading structured error
빈 metrics를 success로 보지 않음
data-loading timeout exit code 정합화
```

## 5. smoke 결과

추가:

```text
docs/research/condition_research/pilot_logs/2026-04-22_cli_moneytop_protocol_smoke.md
```

### smoke 4

```text
status=error
last_checkpoint=backtest_child_diagnostics
stock_back_db_path=./_database/stock_tick_back.db
moneytop_query_status=error
moneytop_error=no such table: moneytop
```

### smoke 32

```text
status=error
last_checkpoint=backtest_child_diagnostics
stock_back_db_path=./_database/stock_tick_back.db
moneytop_query_status=error
moneytop_error=no such table: moneytop
```

판정:

```text
decision=PASS_FOR_DIAGNOSTICS
candidate_count_5_gate=BLOCKED
```

의미:

```text
성공:
  child가 어떤 DB를 보고 왜 moneytop 조회에 실패했는지 JSON으로 확인 가능

아직 미해결:
  CLI baseline metrics/CSV 생성
```

## 6. 검증 결과

```text
focused tests:
  python -m pytest tests/unit/test_output.py tests/unit/test_runner_helpers.py -q
  90 passed

full unit tests:
  python -m pytest tests/unit/ -q
  1037 passed, 1 skipped, 10 warnings

verify_nonrelease_sync.py:
  PASS
```

최종 리뷰 결과:

```text
Critical issues: none
Important issues: none
PR readiness: yes
```

## 7. merge 승인 판단

이번 PR은 merge 가능하다.

근거:

```text
focused/full unit tests 통과
verify_nonrelease_sync.py 통과
smoke 4/32 결과 문서화
BackTest child moneytop 실패 원인 JSON 노출
runtime DB/CSV/graph/temp 산출물 미커밋
```

단, 이 merge 승인은 **진단 기반 PR**에 대한 승인이다. CLI baseline 성공 또는 후보 5개 실행 승인과는 다르다.

## 8. 남은 리스크

```text
1. child process runtime DB override 전달은 아직 미구현
2. CLI baseline metrics/CSV는 아직 생성되지 않음
3. GUI/CLI 결과 비교는 아직 불가능
4. shared memory cleanup 잔여 문제는 별도 추적 필요
5. candidate_count=5는 계속 금지
```

## 9. 다음 단계

이번 PR merge 후 다음 브레인스토밍:

```text
$brainstorming CLI child runtime DB override 전달 설계
```

포함할 맥락:

```text
확인된 사실:
- BackTest child는 ./_database/stock_tick_back.db를 본다.
- parent는 STOM_CLI_DATABASE_DIR로 wt-dev runtime DB를 보게 할 수 있다.
- child legacy import에는 이 override가 적용되지 않는다.
- moneytop table은 child가 보는 ./_database/stock_tick_back.db에 없다.

목표:
- child process가 parent와 같은 stock_tick_back.db를 보게 한다.
- 필요하면 setting/strategy/backtest DB도 같은 runtime context로 맞춘다.
- 임시 moneytop table 생성은 최후 수단으로 둔다.
- 수정 후 smoke 4/32와 2025 baseline을 재시도한다.
```

## 10. 결론

이번 PR은 CLI 백테스트 최종 성공 PR이 아니다. 하지만 CLI 실패 원인을 더 이상 추정하지 않고, BackTest child가 실제로 어떤 DB를 보고 실패하는지 확인할 수 있게 만들었다.

다음 PR에서 child runtime DB override를 전달하면, CLI baseline이 GUI와 같은 runtime DB를 보는지 다시 검증할 수 있다.
