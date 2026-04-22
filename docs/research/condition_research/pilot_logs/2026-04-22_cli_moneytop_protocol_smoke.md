# CLI Moneytop Protocol Smoke

## 목적

BackTest child의 moneytop 조회 실패가 어떤 DB/runtime context에서 발생하는지 구조화된 진단 정보로 확인했다.

## 사전 조건

feature worktree에는 `_database`가 없으므로, legacy `utility.setting` import를 위해 작은 runtime DB를 `wt-dev`에서 복사했다.

```text
copied_runtime_db:
  _database/strategy.db
  _database/setting.db
  _database/backtest.db

stock_tick_back.db:
  STOM_CLI_DATABASE_DIR=C:\System_Trading\STOM\STOM_V.wt-dev\_database
```

이 파일들은 runtime 준비 산출물이며 Git에 커밋하지 않는다.

## smoke 4 결과

명령:

```text
20250102~20250103 tick avg_time=30 engines=4 timeout=300
```

결과:

```text
command_exit_code=2
json_exists=True
status=error
message=Backtest child moneytop query failed: Execution failed on sql 'SELECT * FROM moneytop WHERE `index` >= 20250102090030 AND `index` <= 20250103092800': no such table: moneytop
checkpoint_status=error
last_checkpoint=backtest_child_diagnostics
```

BackTest child diagnostics:

```text
stock_back_db_path=./_database/stock_tick_back.db
moneytop_query_status=error
moneytop_error=Execution failed on sql 'SELECT * FROM moneytop WHERE `index` >= 20250102090030 AND `index` <= 20250103092800': no such table: moneytop
startday=20250102
endday=20250103
starttime=90000
endtime=92800
ui_gubun=S
```

## smoke 32 결과

명령:

```text
20250102~20250103 tick avg_time=30 engines=32 timeout=300
```

결과:

```text
command_exit_code=2
json_exists=True
status=error
message=Backtest child moneytop query failed: Execution failed on sql 'SELECT * FROM moneytop WHERE `index` >= 20250102090030 AND `index` <= 20250103092800': no such table: moneytop
checkpoint_status=error
last_checkpoint=backtest_child_diagnostics
```

BackTest child diagnostics:

```text
stock_back_db_path=./_database/stock_tick_back.db
moneytop_query_status=error
moneytop_error=Execution failed on sql 'SELECT * FROM moneytop WHERE `index` >= 20250102090030 AND `index` <= 20250103092800': no such table: moneytop
startday=20250102
endday=20250103
starttime=90000
endtime=92800
ui_gubun=S
```

## 판정

```text
decision=PASS_FOR_DIAGNOSTICS
reason=Both smoke runs exposed BackTest child moneytop diagnostics in JSON. The child process is reading ./_database/stock_tick_back.db, while the CLI parent was configured to use the wt-dev runtime DB for stock_tick_back.db.
```

이번 결과는 백테스트 성공이 아니다. 진단 성공이다.

```text
candidate_count_5_gate=BLOCKED
reason=CLI baseline still cannot produce metrics or CSV.
```

## 다음 단계

```text
$brainstorming CLI child runtime DB override 전달 설계
```

확인할 핵심:

```text
1. BackTest child가 `./_database/stock_tick_back.db`를 보는 이유
2. STOM_CLI_DATABASE_DIR 또는 개별 DB override가 child legacy import까지 전달되지 않는 이유
3. child가 parent와 같은 `C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db`를 보게 하는 최소 수정
4. 같은 수정이 setting/strategy/backtest DB에도 필요한지 여부
```
