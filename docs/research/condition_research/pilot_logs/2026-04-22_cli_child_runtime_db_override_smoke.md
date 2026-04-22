# CLI Child Runtime DB Override Smoke

## 목적

BackTest child가 parent와 같은 runtime DB 경로를 보도록 `utility.setting_base`와 runner env propagation을 보강한 결과를 확인한다.

## 구현 확인

단위 테스트 기준으로 아래는 확인됐다.

```text
setting_base_default_path=./_database
setting_base_STOM_CLI_DATABASE_DIR=applied
setting_base_individual_empty_override=fallback_to_database_dir
runner_env_propagation=STOM_CLI_DB_* setdefault before _sync_dict_set
```

## smoke 4 결과

명령:

```text
20250102~20250103 tick avg_time=30 engines=4 timeout=300
```

결과:

```text
command_exit_code=3
json_exists=True
status=error
message=백테스트 시간 초과 (300초)
checkpoint_status=timeout
last_checkpoint=backtest_process_started
engine_data_loading=not_present
backtest_child_diagnostics=not_present
csv_path=None
elapsed_seconds=329.453
```

해석:

```text
data loading은 완료됐다.
BackTest child moneytop 오류는 발생하지 않았다.
BackTest process가 시작된 뒤 300초 timeout에 걸렸다.
```

확인된 parent DB path:

```text
stock_back_db_selected.db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db
```

## smoke 32 결과

명령:

```text
20250102~20250103 tick avg_time=30 engines=32 timeout=300
```

결과:

```text
command_exit_code=3
json_exists=True
status=error
message=백테스트 시간 초과 (300초)
checkpoint_status=timeout
last_checkpoint=backtest_process_started
engine_data_loading=not_present
backtest_child_diagnostics=not_present
csv_path=None
elapsed_seconds=352.657
```

해석:

```text
32엔진에서도 data loading은 완료됐다.
BackTest child moneytop 오류는 발생하지 않았다.
BackTest process가 시작된 뒤 300초 timeout에 걸렸다.
```

## 판정

```text
decision=PASS_FOR_CHILD_DB_OVERRIDE
reason=shared memory 정리 후 smoke 4/32 모두 child moneytop 오류 없이 BackTest process 시작 단계까지 도달했다. child runtime DB mismatch blocker는 해소된 것으로 판단하며, 다음 병목은 BackTest process timeout이다.
```

## 다음 단계

```text
$brainstorming CLI BackTest process timeout 및 결과 생성 protocol 분석 설계
```

다음 단계에서 확인할 것:

```text
1. BackTest process가 300초 안에 완료되지 않는 이유
2. Total process / mq.get() / 결과 DB write protocol 확인
3. GUI 실행에서는 같은 짧은 기간이 얼마나 걸리는지 비교
4. timeout을 늘릴 문제인지, 프로토콜 불일치 문제인지 구분
5. CLI baseline이 metrics/CSV를 생성하도록 다음 보강 범위 결정
```
