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
20250102~20250103 tick avg_time=30 engines=4 timeout=30
```

결과:

```text
command_exit_code=3
json_exists=True
status=error
message=engine data loading timed out
checkpoint_status=error
last_checkpoint=engine_data_response_timeout
engine_data_loading.expected_count=4
engine_data_loading.received_count=0
engine_data_loading.missing_count=4
child_stock_back_db_path=not_reached
moneytop_query_status=not_reached
csv_path=None
```

해석:

```text
parent runner는 stock_back_db_selected checkpoint에서 wt-dev runtime DB를 사용했다.
하지만 stale shared memory backdata_0..31 때문에 engine DataLoad가 FileExistsError로 실패했고, BackTest child moneytop 단계까지 도달하지 못했다.
```

확인된 parent DB path:

```text
stock_back_db_selected.db_path=C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db
```

## smoke 32 결과

```text
executed=no
reason=smoke 4가 stale shared memory로 data loading timeout에 걸렸으므로, 같은 상태에서 32엔진 재실행은 의미가 낮고 추가 오염 위험이 있다.
```

## 판정

```text
decision=HOLD
reason=setting_base env override와 runner env propagation은 단위 테스트로 확인됐지만, stale shared memory 때문에 live smoke가 child moneytop 단계까지 도달하지 못했다.
```

## 다음 단계

```text
$brainstorming CLI shared memory cleanup 및 child runtime DB override smoke 재검증 설계
```

다음 단계에서 확인할 것:

```text
1. stale backdata shared memory 정리 방법
2. 정리 후 smoke 4/32 재실행
3. child_stock_back_db_path가 wt-dev runtime DB로 바뀌는지 확인
4. moneytop 오류가 사라지는지 확인
```
