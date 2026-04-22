# 2026-04-22 CLI BackTest Moneytop Protocol Parity Design

## 목적

이번 설계의 목적은 GUI/STOM에서 성공한 백테스트 실행 protocol을 CLI가 동일하게 재현하지 못하는 이유를 `moneytop` 의존성과 parent/child runtime DB 경로 관점에서 분석하고, CLI 백테스트가 GUI와 같은 기준으로 실행되도록 최소 보강 방향을 정하는 것이다.

이번 단계는 후보 조건식 개선이나 `candidate_count=5` 실행 단계가 아니다. AI 자동 조건식 연구 루프가 신뢰 가능한 백테스트 결과를 얻기 위해, CLI 백테스트 실행 자체를 확실하게 만드는 기반 작업이다.

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
[현재 문제] BackTest child moneytop table 조회 실패
        |
        v
[이번 설계] GUI/CLI moneytop protocol parity 분석
        |
        v
[다음] CLI BackTest moneytop dependency 최소 보강
        |
        v
[그 다음] CLI baseline 재시도 및 GUI 결과 비교
```

## 현재까지 확인된 사실

### GUI 기준 결과

사용자는 `STOM_V.wt-dev` GUI/STOM 환경에서 아래 조건으로 Wide v1 백테스트를 직접 성공시켰다.

```text
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
start=20250101
end=20251231
time=090000~092800
timeframe=tick
avg_time=30
engine_multi=32
back_count=1638
trade_count=40937
runtime=0:01:00.675279
```

이 결과는 현재 전체 연구 루프의 GUI 기준 truth다.

### CLI runtime-preflight 결과

PR #15 이후 `runtime-preflight`는 통과했다.

```text
status=ok
failed_checks=[]
validation_errors=[]
timeframe_match.status=ok
stock_back_db_integrity=table_probe_only
stock_back_db_table_count=2427
buy_status=ok
buy_code_length=270
sell_status=ok
sell_code_length=137
```

따라서 조건식 이름, 전략 DB, 설정 DB, tick DB 사전 확인 단계는 정상이다.

### CLI baseline gate 결과

CLI baseline 1회 백테스트는 처음에는 외부 timeout까지 반환되지 않았다.

```text
external_timeout_ms=964079
result_json_created=False
new_csv_created=False
shared_memory_remaining=backdata_0..31
```

이후 data loading timeout/checkpoint 보강으로 다음 상태까지 개선되었다.

```text
smoke_32=status=error, last_checkpoint=csv_detected
smoke_4=status=error, last_checkpoint=csv_detected
full_retry_2025=status=error, last_checkpoint=csv_detected
```

즉 CLI는 이제 외부 timeout 없이 구조화된 error JSON을 반환한다. data loading은 완료된다. 다음 병목은 BackTest child 내부의 `moneytop` table 조회다.

### 현재 오류

BackTest child traceback 요약:

```text
sqlite3.OperationalError: no such table: moneytop
pandas.errors.DatabaseError:
SELECT * FROM moneytop WHERE `index` >= ... AND `index` <= ...
```

따라서 현재 실패는 preflight 또는 data loading 문제가 아니라, BackTest child가 기대하는 `moneytop` table과 CLI runtime context가 맞지 않는 문제다.

## GUI에서 moneytop이 관련 있는가

관련 있다. GUI도 `moneytop`을 사용한다.

GUI `backengine_start()` 단계는 `stock_tick_back.db` 또는 해당 timeframe DB에서 `moneytop`을 조회한다.

```text
GUI backengine_start()
        |
        v
stock_tick_back.db 연결
        |
        v
GetMoneytopQuery(...)
        |
        v
df_mt = read_sql(moneytop query)
        |
        v
day_list / code_set / day_codes / code_days 생성
        |
        v
engine별 데이터 로딩
        |
        v
shared_info 생성
        |
        v
back_count 확정
        |
        v
백테엔진 준비 완료
```

즉 `moneytop`은 GUI에서도 백테스트 대상 종목 universe와 날짜/시간 구간을 만드는 핵심 입력이다.

## GUI와 CLI의 핵심 차이

### GUI protocol

GUI는 백테스트를 두 단계로 실행한다.

```text
[1. 백테스트 엔진 실행]
        |
        v
moneytop 조회
engine data loading
shared_info 생성
back_count 확정
백테엔진 준비 완료
        |
        v
[2. 백테스트 실행 버튼]
        |
        v
조건식 / 백테정보 전달
BackTest 실행
```

GUI에서 백테스트 실행 버튼을 누르면 이미 준비된 엔진과 shared_info 상태를 사용한다.

### CLI protocol

현재 CLI는 단일 명령 안에서 엔진 준비와 BackTest 실행을 재구성한다.

```text
[CLI run_backtest]
        |
        v
BackSubTotal 생성
BackEngine 생성
parent가 moneytop 조회
engine data loading
shared_info 생성
BackTest child 생성
BackTest.Start()
child가 moneytop 재조회
```

문제는 CLI parent와 BackTest child가 같은 runtime DB context를 확실히 공유하지 못할 수 있다는 점이다.

```text
CLI parent:
  cli.paths 또는 STOM_CLI_DATABASE_DIR 기준 stock_tick_back.db 조회

BackTest child:
  legacy utility.setting_base / utility.setting 기준 DB 경로 import
  다른 worktree 또는 다른 _database를 볼 수 있음
```

이 차이 때문에 parent는 `moneytop`을 읽었지만, child는 `moneytop`이 없는 DB를 볼 수 있다.

## 과거 CLI 검증 기록을 포함해야 하는 이유

과거에 “CLI 백테스트가 된다” 또는 “GUI와 결과가 동일하다”고 판단했던 기록은 반드시 재검토해야 한다.

목적은 과거 판단을 부정하는 것이 아니라, 그 검증의 범위를 정확히 분류하는 것이다.

검증 레벨:

```text
Level 0: Parser / dry-run 검증
  - CLI 인자 파싱
  - --dry-run
  - strategy list
  - DB 존재 확인

Level 1: Mocked runner 검증
  - run_backtest mock
  - exit code / output format 검증

Level 2: 실제 CLI 백테스트 실행
  - run_backtest 실제 호출
  - JSON status success
  - CSV 생성

Level 3: GUI 결과와 동일성 검증
  - 같은 전략
  - 같은 기간/시간
  - 같은 tick/min
  - 같은 engine 수
  - back_count / trade_count / 주요 지표 비교
```

현재 Wide v1 자동 연구 루프에 필요한 검증은 Level 3이다.

과거 기록에서 확인할 질문:

```text
1. tick이었는가, min이었는가?
2. 32 engines였는가?
3. 실제 BackTest child까지 실행됐는가?
4. CSV가 생성됐는가?
5. GUI 결과와 trade_count/back_count까지 비교했는가?
6. 어떤 worktree와 어떤 runtime DB를 사용했는가?
7. moneytop table 의존성 경로를 탔는가?
```

## 검토 대상 문서와 코드

과거 CLI 검증 재검토 대상:

```text
docs/research/2026-03-05_v251_cli_comprehensive_review_plan.md
docs/research/2026-03-15_current_branch_actual_test_report.md
docs/research/2026-03-15_auto_condition_discovery_training_guide.md
docs/research/2026-03-17_auto_discovery_pipeline_roadmap.md
docs/pr/2026-04-18_candidate_backtest_runtime_hardening_pr.md
docs/pr/2026-04-18_backtest_iteration_research_loop_pr.md
docs/pr/2026-04-19_candidate_quality_gate_retention_aware_pr.md
docs/pr/2026-04-21_cli_gui_tick_backtest_parity_preflight_pr.md
```

코드 검토 대상:

```text
ui/ui_backtest_engine.py
backtest/backtest.py
cli/runner.py
stom_backtest.py
cli/paths.py
utility/setting.py
utility/setting_base.py
tests/unit/test_runner_helpers.py
tests/unit/test_exit_codes.py
```

## 설계 목표

1. 과거 CLI 검증 기록을 Level 0~3으로 재분류한다.
2. GUI `backengine_start()`와 CLI `run_backtest()`의 데이터 전달 차이를 표로 정리한다.
3. GUI에서 `moneytop`이 사용되는 위치와 목적을 문서화한다.
4. BackTest child가 어떤 DB 경로에서 `moneytop`을 찾는지 계측한다.
5. CLI parent와 BackTest child의 runtime DB path가 같은지 비교한다.
6. CLI child에도 동일 runtime context를 전달하는 최소 수정 방향을 설계한다.
7. 임시 `moneytop` table 생성은 최후 수단으로 둔다.

## 비목표

- 이번 단계에서 `candidate_count=5`를 실행하지 않는다.
- 임시 `moneytop` table 생성으로 바로 우회하지 않는다.
- GUI 코드를 먼저 수정하지 않는다.
- CLI engine session을 대규모로 도입하지 않는다.
- WFO 또는 promote를 실행하지 않는다.
- 조건식을 개선하지 않는다.

## 구현 선택지

### A. 과거 검증 재분류 + GUI protocol diff + 최소 수정

```text
1. 과거 CLI 검증 기록을 Level 0~3으로 재분류
2. GUI/CLI moneytop 데이터 흐름 비교
3. parent/child runtime DB path 계측
4. child가 같은 DB를 보도록 최소 수정
5. smoke 재실행
```

장점:

```text
근거 기반으로 진행
GUI 성공 workflow와 정렬
DB 오염 위험 낮음
변경 범위 통제 가능
```

단점:

```text
바로 결과 CSV를 얻기보다 분석/계측 PR이 한 번 더 필요할 수 있음
```

### B. moneytop 임시 table 생성 우회

```text
1. parent가 읽은 df_mt를 child가 보는 DB에 moneytop으로 저장
2. BackTest 실행
3. cleanup
```

장점:

```text
빠르게 no such table 문제를 피할 수 있음
```

단점:

```text
DB 오염 위험
cleanup 실패 위험
GUI protocol 재현이 아니라 증상 우회
동시 실행/반복 실행에 취약
```

### C. CLI engine prepare / execute 세션 구조 도입

```text
stom_backtest.py engine prepare
stom_backtest.py run prepared
```

장점:

```text
GUI와 가장 유사한 구조
장기적으로 자동화에 적합
```

단점:

```text
상태 유지 / 프로세스 수명 / cleanup 설계가 큼
현재 단계에 과함
```

## 추천안

추천은 A안이다.

```text
A. 과거 검증 재분류 + GUI protocol diff + 최소 수정
```

이유:

```text
1. 현재 실패는 moneytop table 자체가 아니라 parent/child runtime context 차이일 가능성이 높다.
2. GUI 성공 workflow를 CLI가 재현해야 장기 자동화가 안정적이다.
3. 임시 table 생성은 빠르지만 DB 오염과 cleanup 리스크가 크다.
4. CLI engine session 도입은 맞는 방향일 수 있지만 지금은 범위가 크다.
```

## 최소 수정 우선순위

1순위: child runtime path 계측

```text
parent_stock_back_db_path
child_stock_back_db_path
parent_backtest_db_path
child_backtest_db_path
child_moneytop_query_status
child_moneytop_error
```

2순위: child process에 CLI runtime DB override 전달

```text
STOM_CLI_DATABASE_DIR
STOM_CLI_DB_STOCK_BACK_TICK
STOM_CLI_DB_BACKTEST
STOM_CLI_DB_SETTING
STOM_CLI_DB_STRATEGY
```

3순위: BackTest moneytop 조회 DB를 parent와 일치시킴

```text
BackTest child가 parent와 같은 stock_tick_back.db에서 moneytop을 읽도록 보장
```

4순위: 그래도 실패하면 데이터 전달 구조 검토

```text
parent가 만든 df_mt / arry_bct / day_count를 BackTest child에 전달
```

5순위: 최후 수단으로 임시 table 생성 검토

```text
temporary moneytop table
explicit cleanup
single-run isolation
```

## 검증 전략

### 1. 과거 CLI 검증 재분류

산출물:

```text
docs/research/condition_research/pilot_logs/2026-04-22_cli_historical_validation_review.md
```

내용:

```text
검토 문서
검증 조건
Level 0~3 분류
현재 Wide v1 조건과의 차이
유효한 과거 결론
새로 필요한 검증
```

### 2. GUI/CLI protocol diff 문서

산출물:

```text
docs/research/condition_research/pilot_logs/2026-04-22_gui_cli_backtest_protocol_diff.md
```

내용:

```text
GUI engine start 단계
GUI backtest execute 단계
CLI run_backtest 단계
moneytop 조회 위치
parent/child DB path 차이
누락 전달값
```

### 3. 코드 보강 후 smoke

smoke 순서:

```text
1. 20250102~20250103 / tick / engines=4
2. 20250102~20250103 / tick / engines=32
3. 20250101~20251231 / tick / engines=32
```

성공 기준:

```text
BackTest child moneytop query succeeds
또는 실패해도 child path와 moneytop error가 JSON에 기록됨
```

## 성공 기준

이번 작업의 성공 기준:

```text
1. 과거 CLI 검증 범위가 Level 0~3으로 재분류된다.
2. GUI/CLI moneytop protocol 차이가 문서화된다.
3. BackTest child가 보는 DB path가 JSON/checkpoint에 기록된다.
4. parent와 child의 DB path 차이가 확인 또는 해소된다.
5. smoke 실행이 moneytop table 오류 없이 진행되거나, 적어도 child DB path/moneytop error를 구조화해 반환한다.
6. candidate_count=5는 계속 보류된다.
```

## 실패 시 분기

### child DB path mismatch 확인

```text
child process runtime DB override 전달 설계
```

### child DB path는 같은데 moneytop 없음

```text
BackTest가 조회하는 DB 종류/상수 확인
parent df_mt 전달 또는 moneytop table source 재검토
```

### moneytop 해결 후 metrics 생성

```text
CLI baseline gate 재시도
GUI 결과와 비교
```

### 여전히 no metrics

```text
BackTest/Total/result DB write protocol 분석
```

## 다음 단계

이 spec이 승인되면 다음 단계는 `writing-plans`다.

예상 계획 제목:

```text
CLI BackTest Moneytop Protocol Parity 실행 계획
```

예상 작업 단위:

```text
Task 1: 과거 CLI 검증 기록 재분류
Task 2: GUI/CLI backtest protocol diff 문서화
Task 3: parent/child runtime DB path 계측 설계 구현
Task 4: moneytop query status JSON/checkpoint 추가
Task 5: smoke 실행
Task 6: pilot/update log 작성
```

후보 5개 실행은 이 작업으로 CLI baseline이 GUI와 비교 가능한 결과를 낼 수 있게 된 뒤 별도 브레인스토밍에서 결정한다.
