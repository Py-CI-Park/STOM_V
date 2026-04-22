# 2026-04-22 CLI BackTest Process Timeout Protocol

## 목적

CLI 백테스트가 BackTest process 시작 후 timeout될 때 내부 protocol 진행 지점을 확인할 수 있게 하고, smoke에서 발견된 CLI tick 설정 키 누락을 보강했다.

## 변경 사항

- `QueueDrainer`가 `[CLI_DIAG]` JSON 메시지를 `protocol_diagnostics`에 보존
- `BackTest` / `Total`에 CLI-only protocol checkpoint 추가
- `runner`가 CLI 실행 중 `STOM_CLI_BACKTEST_PROTOCOL_DIAG=1`을 자식 프로세스에 전파
- timeout/error result에 `backtest_process_diagnostics` summary 추가
- `output.py` error JSON 허용 필드에 `backtest_process_diagnostics` 추가
- CLI `DICT_SET`에 tick engine 필수 키 추가
  - `시장미시구조분석=False`
  - `시장리스크분석=False`

## 검증

```text
queue_drain/backtest_protocol/runner/output focused tests=123 passed
full_unit_tests=1052 passed, 1 skipped, 10 warnings
verify_nonrelease_sync=PASS
git_diff_check=PASS
smoke_4=status=success,last_checkpoint=csv_detected,trade_count=194,csv_created=True,elapsed_seconds=45.594
smoke_32=status=success,last_checkpoint=csv_detected,trade_count=194,csv_created=True,elapsed_seconds=60.125
```

## 원인 정리

```text
증상=CLI BackTest process timeout after backtest_process_started
직접 원인=engine worker Strategy()에서 CLI DICT_SET 누락 키 KeyError 발생
누락 키=시장미시구조분석, 시장리스크분석
결과=engine 중단 -> Total 완료 신호 미수신 -> BackTest.Start() mq.get() 대기 -> parent timeout
```

## 판정

```text
decision=PASS_FOR_CLI_SMOKE_AND_PROTOCOL_PATH
reason=시장 분석 키 보강 후 4/32 engine smoke 모두 metrics와 CSV를 생성했다.
```

## 남은 리스크

- 이번 smoke는 20250102~20250103 짧은 기간이다.
- full-year 20250101~20251231 GUI/CLI 결과 비교는 아직 이번 로그에서 확정하지 않았다.
- success JSON은 protocol diagnostics를 노출하지 않고, 성공 경로의 checkpoint는 stderr log에 남는다.
- 다음 단계에서 Wide v1 full-year CLI baseline과 사용자 GUI 결과를 직접 비교해야 한다.
