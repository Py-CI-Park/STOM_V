# 2026-04-22 CLI Child Runtime DB Override Design

## 목적

이번 설계의 목적은 CLI parent와 BackTest child가 서로 다른 runtime DB를 보는 문제를 해결하는 것이다.

현재 BackTest child는 `./_database/stock_tick_back.db`를 보고 있으며, 이 DB에는 `moneytop` 테이블이 없어 CLI baseline 백테스트가 실패한다. 반면 CLI parent는 `STOM_CLI_DATABASE_DIR`를 통해 `wt-dev` runtime DB를 볼 수 있다.

이번 작업은 child process도 parent와 같은 runtime DB 경로를 보게 만드는 설계다.

```text
[현재]
CLI parent:
  C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db

BackTest child:
  ./_database/stock_tick_back.db

[목표]
CLI parent:
  C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db

BackTest child:
  C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db
```

## 배경

이전 PR #16에서 BackTest child moneytop 실패를 JSON으로 노출했다.

확인된 child diagnostic:

```text
stock_back_db_path=./_database/stock_tick_back.db
moneytop_query_status=error
moneytop_error=no such table: moneytop
```

이 결과로 문제의 핵심이 명확해졌다.

```text
문제:
  moneytop 테이블 자체가 갑자기 필요한 것이 아니라,
  BackTest child가 parent와 같은 runtime DB를 보지 못한다.
```

## 전체 개발 흐름에서의 위치

```text
[완료] GUI Wide v1 백테스트 성공
        |
        v
[완료] CLI runtime-preflight 성공
        |
        v
[완료] CLI data loading hang 구조화
        |
        v
[완료] BackTest child moneytop diagnostic 추가
        |
        v
[이번 설계] child runtime DB override 전달
        |
        v
[다음] CLI baseline 재시도
        |
        v
[그 다음] GUI 결과와 CLI 결과 비교
        |
        v
[그 다음] Wide v1 Retention-Aware 후보 5개 실행
```

이번 단계가 끝나기 전에는 `candidate_count=5`를 실행하지 않는다.

## 현재 코드 구조

### `cli.paths`

`cli/paths.py`는 CLI 전용 경로 resolver를 가지고 있다.

```python
DATABASE_DIR = Path(
    os.environ.get("STOM_CLI_DATABASE_DIR", str(PROJECT_ROOT / "_database"))
)

DB_SETTING = _resolve_db("setting.db", "STOM_CLI_DB_SETTING")
DB_STRATEGY = _resolve_db("strategy.db", "STOM_CLI_DB_STRATEGY")
DB_BACKTEST = _resolve_db("backtest.db", "STOM_CLI_DB_BACKTEST")
DB_STOCK_BACK_TICK = _resolve_db("stock_tick_back.db", "STOM_CLI_DB_STOCK_BACK_TICK")
DB_STOCK_BACK_MIN = _resolve_db("stock_min_back.db", "STOM_CLI_DB_STOCK_BACK_MIN")
```

따라서 CLI parent는 env override를 적용할 수 있다.

### `utility.setting_base`

`utility/setting_base.py`는 legacy runtime 경로를 정적 상대경로로 정의한다.

```python
DB_PATH = './_database'
DB_SETTING = './_database/setting.db'
DB_BACKTEST = './_database/backtest.db'
DB_STRATEGY = './_database/strategy.db'
DB_STOCK_TICK_BACK = './_database/stock_tick_back.db'
DB_STOCK_MIN_BACK = './_database/stock_min_back.db'
```

BackTest child는 이 legacy module을 import한다. Windows spawn child process에서는 module import가 다시 일어나므로, child는 `./_database` 기준을 다시 볼 수 있다.

## 문제 정의

현재 `STOM_CLI_DATABASE_DIR`는 `cli.paths`에는 적용되지만, `utility.setting_base`에는 적용되지 않는다.

결과:

```text
parent:
  cli.paths.DB_STOCK_BACK_TICK
  -> STOM_CLI_DATABASE_DIR 기반 wt-dev DB

child:
  utility.setting_base.DB_STOCK_TICK_BACK
  -> ./_database/stock_tick_back.db
```

BackTest child가 `./_database/stock_tick_back.db`를 조회하면 `moneytop` 테이블이 없어서 실패한다.

## 설계 목표

1. `utility.setting_base`도 CLI DB override 환경변수를 읽도록 한다.
2. child process가 parent와 같은 runtime DB 경로를 보게 한다.
3. GUI 실행은 환경변수가 없을 때 기존 `./_database` 경로를 유지한다.
4. 개별 DB override가 `STOM_CLI_DATABASE_DIR`보다 우선하도록 한다.
5. smoke 실행에서 child diagnostic의 `stock_back_db_path`가 wt-dev runtime DB 경로로 바뀌는지 확인한다.
6. `moneytop` table 오류가 사라지는지 확인한다.

## 비목표

- 임시 `moneytop` table을 생성하지 않는다.
- GUI 코드를 수정하지 않는다.
- `candidate_count=5`를 실행하지 않는다.
- WFO 또는 promote를 실행하지 않는다.
- CLI engine session을 새로 만들지 않는다.
- runtime DB를 Git에 커밋하지 않는다.

## 권장 설계

### 1. `utility.setting_base`에 env-aware resolver 추가

`setting_base.py` 상단에 `os`와 경로 resolver를 추가한다.

개념:

```python
import os

DB_PATH = os.environ.get('STOM_CLI_DATABASE_DIR', './_database')

def _resolve_db(filename, env_name):
    override = os.environ.get(env_name)
    if override:
        return override
    return f'{DB_PATH}/{filename}'
```

적용 대상:

```python
DB_SETTING = _resolve_db('setting.db', 'STOM_CLI_DB_SETTING')
DB_BACKTEST = _resolve_db('backtest.db', 'STOM_CLI_DB_BACKTEST')
DB_STRATEGY = _resolve_db('strategy.db', 'STOM_CLI_DB_STRATEGY')
DB_STOCK_TICK_BACK = _resolve_db('stock_tick_back.db', 'STOM_CLI_DB_STOCK_BACK_TICK')
DB_STOCK_MIN_BACK = _resolve_db('stock_min_back.db', 'STOM_CLI_DB_STOCK_BACK_MIN')
```

### 2. alias 상수 유지

기존 compatibility alias는 유지한다.

```python
DB_STOCK_BACK_TICK = DB_STOCK_TICK_BACK
DB_STOCK_BACK_MIN = DB_STOCK_MIN_BACK
```

### 3. CLI parent에서 env를 명시적으로 보장

`cli.paths`는 이미 env를 읽는다. 다만 child가 `utility.setting_base`를 import하기 전에 env가 존재해야 한다.

`run_backtest()` 또는 `_sync_dict_set()`에서 아래를 보장한다.

```text
STOM_CLI_DATABASE_DIR
STOM_CLI_DB_SETTING
STOM_CLI_DB_STRATEGY
STOM_CLI_DB_BACKTEST
STOM_CLI_DB_STOCK_BACK_TICK
STOM_CLI_DB_STOCK_BACK_MIN
```

이미 사용자가 명시한 env가 있으면 덮어쓰지 않는다. CLI 기본값이 필요한 경우 `cli.paths`에서 계산된 값을 env에 넣는다.

목표:

```text
Windows spawn child process가 utility.setting_base를 import할 때
같은 env 값을 상속받는다.
```

## 대안 검토

### A. `utility.setting_base` env override 지원 추천

장점:

```text
parent/child 경로를 같은 환경변수 체계로 통일
GUI는 env 없이 기존 동작 유지
DB 복사/임시 table 불필요
```

단점:

```text
setting_base는 넓게 쓰이는 파일이므로 회귀 테스트 필요
```

### B. child process에서 상수 monkey patch

장점:

```text
runner 내부로 범위 제한 가능
```

단점:

```text
import 순서에 취약
BackTest/Total/engine child 모두 누락 가능
장기 유지보수 어려움
```

### C. worktree에 DB 복사/링크

장점:

```text
코드 수정이 적음
```

단점:

```text
30GB tick DB 관리 문제
runtime artifact 오염
자동화에 부적합
worktree마다 반복 작업 필요
```

추천은 A안이다.

## 테스트 전략

### 단위 테스트

`tests/unit/test_setting_base_cli_overrides.py`를 추가한다.

검증:

```text
env 없음:
  DB_PATH == './_database'
  DB_STOCK_TICK_BACK == './_database/stock_tick_back.db'

STOM_CLI_DATABASE_DIR 설정:
  DB_PATH == 지정 경로
  DB_STOCK_TICK_BACK == 지정 경로/stock_tick_back.db
  DB_BACKTEST == 지정 경로/backtest.db

개별 env 설정:
  STOM_CLI_DB_STOCK_BACK_TICK가 DB_PATH보다 우선
```

### runner env propagation test

`tests/unit/test_runner_helpers.py`에 source/behavior test를 추가한다.

검증:

```text
run_backtest 또는 _sync_dict_set에서 STOM_CLI_DB_* env를 보장
DB_STOCK_BACK_TICK 값이 env에 전파됨
```

### smoke

수정 후 smoke:

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
  -o backtest\temp\wide_v1_cli_child_db_override_smoke_4_20260422.json
```

기대:

```text
child diagnostic stock_back_db_path가 wt-dev runtime DB 경로로 변경
또는 moneytop 오류가 사라지고 다음 단계로 진행
```

## 성공 기준

이번 작업의 성공 기준:

```text
1. utility.setting_base가 STOM_CLI_DATABASE_DIR와 개별 DB override를 읽는다.
2. GUI 기본 환경에서는 기존 ./_database 경로가 유지된다.
3. CLI child diagnostic의 stock_back_db_path가 wt-dev runtime DB 경로로 바뀐다.
4. `no such table: moneytop` 오류가 사라지거나, 최소한 child path mismatch가 해소된다.
5. smoke 결과가 문서화된다.
```

## 남은 리스크

1. child가 올바른 DB를 봐도 다른 BackTest/Total protocol 문제가 나올 수 있다.
2. setting_base env override가 다른 CLI/GUI 경로에 영향을 줄 수 있다.
3. shared memory 잔여 문제는 이 설계의 직접 해결 대상이 아니다.
4. moneytop 오류가 사라져도 GUI/CLI 결과 비교는 별도 baseline gate에서 수행해야 한다.

## 다음 단계

이 spec이 승인되면 `writing-plans`로 구현 계획을 작성한다.

예상 계획 제목:

```text
CLI Child Runtime DB Override 실행 계획
```

예상 작업 단위:

```text
Task 1: setting_base env override 테스트 작성
Task 2: setting_base env-aware resolver 구현
Task 3: runner env propagation 보강
Task 4: smoke 4/32 실행
Task 5: pilot/update log 작성
Task 6: focused/full 검증 및 PR 보고서
```

`candidate_count=5`는 child runtime DB override 이후 CLI baseline이 metrics/CSV를 만들고 GUI와 비교 가능해질 때까지 계속 보류한다.
