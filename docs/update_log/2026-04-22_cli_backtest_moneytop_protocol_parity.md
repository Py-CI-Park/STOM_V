# 2026-04-22 CLI BackTest Moneytop Protocol Parity

## 목적

GUI와 CLI의 moneytop 사용 protocol 차이를 분석하고, BackTest child moneytop 실패 진단을 JSON으로 노출했다.

## 변경 사항

- 과거 CLI 검증 범위 재분류
- GUI/CLI protocol diff 문서화
- BackTest child moneytop diagnostic 추가
- CLI JSON output diagnostic 보존
- data-loading timeout 기반과 moneytop 진단 기반 통합

## 검증

```text
historical_validation_review=completed
gui_cli_protocol_diff=completed
test_output_and_runner_helpers=90 passed
moneytop_smoke_4=error_json_with_backtest_child_diagnostics
moneytop_smoke_32=error_json_with_backtest_child_diagnostics
```

## smoke 결과 요약

```text
smoke_4:
  status=error
  last_checkpoint=backtest_child_diagnostics
  stock_back_db_path=./_database/stock_tick_back.db
  moneytop_query_status=error
  moneytop_error=no such table: moneytop

smoke_32:
  status=error
  last_checkpoint=backtest_child_diagnostics
  stock_back_db_path=./_database/stock_tick_back.db
  moneytop_query_status=error
  moneytop_error=no such table: moneytop
```

## 판정

```text
decision=PASS_FOR_DIAGNOSTICS
reason=BackTest child moneytop failure is now visible in CLI JSON. The child process reads ./_database/stock_tick_back.db, which differs from the parent runtime DB override used for stock_tick_back.db.
```

후보 5개 실행은 아직 금지한다.

```text
candidate_count_5_gate=BLOCKED
reason=CLI baseline still does not produce metrics or CSV.
```

## 남은 리스크

- child process runtime DB override 전달이 아직 구현되지 않았다.
- moneytop 해결 후에도 CLI baseline GUI 비교가 필요하다.
- shared memory cleanup 잔여 문제는 별도 추적이 필요하다.
- candidate_count=5는 아직 실행하면 안 된다.

## 다음 단계

```text
$brainstorming CLI child runtime DB override 전달 설계
```

다음 설계에서 결정할 것:

```text
1. child process가 사용하는 `utility.setting_base` DB path를 어떻게 override할지
2. STOM_CLI_DATABASE_DIR을 legacy setting_base까지 적용할지
3. 개별 DB env override를 child process import 전에 주입할지
4. wt-dev runtime DB와 feature worktree runtime DB를 어떻게 분리/보호할지
5. override 후 smoke 및 2025 baseline 재검증 기준
```
