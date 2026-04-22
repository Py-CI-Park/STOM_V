# 2026-04-22 CLI Child Runtime DB Override

## 목적

BackTest child process가 parent CLI와 같은 runtime DB 경로를 보도록 legacy `utility.setting_base`에 CLI DB override를 적용했다.

## 변경 사항

- `utility.setting_base` env-aware DB resolver 추가
- 빈 개별 DB override는 기본 경로로 fallback
- `cli.runner` child DB env propagation 추가
- setting_base override tests 추가
- runner env propagation tests 추가

## 검증

```text
setting_base_tests=4 passed
runner_helper_and_setting_base_tests=49 passed
focused_tests=185 passed
verify_nonrelease_sync=PASS
smoke_4=status=error,last_checkpoint=engine_data_response_timeout
smoke_32=not_executed
```

## smoke 판정

```text
decision=HOLD
reason=child runtime DB override 구현은 완료됐지만, stale shared memory backdata_0..31 때문에 smoke가 data loading timeout에서 멈춰 child moneytop 단계까지 도달하지 못했다.
```

## 남은 리스크

- child_stock_back_db_path가 실제로 wt-dev runtime DB로 바뀌었는지는 live smoke에서 아직 확인하지 못했다.
- shared memory 잔여가 다음 CLI 실행을 계속 방해할 수 있다.
- candidate_count=5는 아직 실행하면 안 된다.

## 다음 단계

```text
$brainstorming CLI shared memory cleanup 및 child runtime DB override smoke 재검증 설계
```

다음 설계에서 결정할 것:

```text
1. stale backdata shared memory 정리 방법
2. 정리 후 smoke 4/32 재실행 순서
3. child runtime DB override 검증 기준
4. smoke가 moneytop을 통과하면 CLI baseline GUI 비교로 넘어갈 조건
```
