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
smoke_4=status=error,last_checkpoint=backtest_process_started
smoke_32=status=error,last_checkpoint=backtest_process_started
```

## smoke 판정

```text
decision=PASS_FOR_CHILD_DB_OVERRIDE
reason=shared memory 정리 후 smoke 4/32 모두 child moneytop 오류 없이 BackTest process 시작 단계까지 도달했다. child runtime DB mismatch blocker는 해소된 것으로 판단하며, 다음 병목은 BackTest process timeout이다.
```

## 남은 리스크

- CLI baseline은 아직 metrics/CSV를 생성하지 못한다.
- BackTest process가 300초 timeout 안에 완료되지 않는다.
- GUI와 CLI 결과 비교는 아직 불가능하다.
- candidate_count=5는 아직 실행하면 안 된다.

## 다음 단계

```text
$brainstorming CLI BackTest process timeout 및 결과 생성 protocol 분석 설계
```

다음 설계에서 결정할 것:

```text
1. BackTest process가 300초 안에 완료되지 않는 이유
2. Total process / mq.get() / 결과 DB write protocol 확인
3. GUI 실행에서는 같은 짧은 기간이 얼마나 걸리는지 비교
4. timeout을 늘릴 문제인지, 프로토콜 불일치 문제인지 구분
5. CLI baseline이 metrics/CSV를 생성하도록 다음 보강 범위 결정
```
