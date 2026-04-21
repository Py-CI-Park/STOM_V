# 2026-04-20 CLI/GUI Tick Backtest Parity Design

## 목적

이번 설계의 목적은 사람이 GUI/STOM으로 수행하던 tick 백테스트 연구를 AI와 CLI 기반 자동 연구 루프가 같은 조건으로 재현할 수 있게 만드는 것이다.

현재 전체 개발 방향은 바뀌지 않는다. 기존 목표는 여전히 백테스트 결과 CSV 분석, 후보 조건식 생성, 후보 백테스트, ranking, 조건식 개선 반복, 최종 promote/WFO 검증으로 이어지는 자동 조건식 연구 루프다.

이번 설계는 그 흐름 중 `Wide v1 Retention-Aware 후보 개선`을 계속하기 전에 필요한 실행 신뢰성 게이트다.

```text
[사람의 GUI 연구]
조건식 선택
 -> GUI 백테스트
 -> CSV 확인
 -> 결과 분석
 -> 조건식 개선
 -> 다시 백테스트

[목표 자동화 연구]
조건식 선택/생성
 -> CLI 백테스트
 -> CSV 자동 분석
 -> 후보 조건식 생성
 -> CLI 후보 백테스트
 -> ranking
 -> 조건식 개선 반복
 -> 최종 promote/WFO 검증
```

## 현재 위치

`STOM_Version_2U_C`에는 다음 기반이 이미 들어와 있다.

```text
[1. Backtest Iteration Research Loop v1]
        |
        v
[2. Candidate Quality Gate / Retention-Aware Selection]
        |
        v
[3. Tick Research Baseline Condition]
        |
        v
[4. Wide v1 GUI/STOM 백테스트 성공]
        |
        v
[5. CLI/GUI Tick Backtest Parity 확보]  <- 이번 설계
        |
        v
[6. Wide v1 Retention-Aware 후보 5개 실행]
        |
        v
[7. 반복 개선 루프 v2]
        |
        v
[8. 최종 promote/WFO 검증]
```

Wide v1 연구용 조건식은 다음이다.

```text
buy:
ResearchTest_Tick_B_090000_092800_Wide_20260419

sell:
ResearchTest_Tick_S_090000_092800_Wide_20260419
```

사용자가 `STOM_V.wt-dev`의 실제 GUI/STOM 실행 환경에서 같은 조건식을 다시 로딩해 직접 백테스트했고, 아래 결과를 확보했다.

```text
period: 2025-01-01 ~ 2025-12-31
time: 09:00:00 ~ 09:28:00
timeframe: tick
avg_time: 30
engine_multi: 32
back_count: 1638
trade_count: 40,937
daily_avg_trade_count: 169.9
avg_hold_time: 228.19 seconds
win_rate: 30.02%
avg_return: -0.68%
total_return: -695.09%
tpi: 0.60
runtime: 0:01:00.675279
```

생성된 기준 CSV는 다음이다.

```text
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

이 전략은 실전 후보가 아니라 연구용 wide baseline이다. 수익률과 낙폭은 매우 나쁘지만, 40,937건의 체결 표본을 확보했으므로 Retention-Aware 후보 개선 루프의 기준 CSV로는 가치가 있다.

## 문제 정의

사용자가 GUI/STOM에서 같은 조건을 직접 실행했을 때 백테스트는 약 1분에 완료되었다. 그러나 CLI/headless 경로에서는 동일 목적의 실행이 timeout되었고, 일부 확인에서는 `strategy.db`의 전략코드가 `????`로 읽히는 현상도 관측되었다.

따라서 현재 문제는 조건식 자체의 실패로 단정할 수 없다. 더 정확한 문제는 다음이다.

```text
GUI/STOM이 읽은 runtime DB, 전략코드, tick DB, 설정값과
CLI가 읽은 runtime DB, 전략코드, tick DB, 설정값이
같은지 아직 보장되지 않는다.
```

같은 컴퓨터에서 같은 전략명을 사용해도, worktree와 현재 작업 디렉터리가 다르면 다음 파일들이 달라질 수 있다.

```text
strategy.db        조건식 저장 DB
setting.db         백테스트 설정 DB
backtest.db        백테스트 결과 DB
stock_tick_back.db tick 백테스트 데이터 DB
backtest/csv       결과 CSV 저장 폴더
```

자동 연구 루프가 CLI 백테스트에 의존하려면, CLI가 GUI와 같은 백테스트를 수행한다는 증거가 먼저 필요하다.

## 설계 목표

1. GUI/STOM에서 성공한 Wide v1 tick 백테스트 조건을 CLI에서도 검증 가능하게 만든다.
2. CLI가 사용하는 runtime DB 경로와 전략코드 상태를 백테스트 시작 전에 명확히 출력한다.
3. 전략명은 존재하지만 코드가 깨진 경우 백테스트를 시작하지 않고 즉시 실패한다.
4. 후보 5개 백테스트 전에 baseline CLI 1회 백테스트를 선행 게이트로 둔다.
5. timeout 발생 시 마지막 진행 checkpoint를 기록해 원인 분리가 가능하게 한다.
6. Wide v1 Retention-Aware 후보 개선은 이 parity 게이트 통과 후 재개한다.

## 비목표

- CLI 전체를 대규모 재작성하지 않는다.
- GUI 백테스트의 모든 기능을 한 번에 CLI로 완전 대체하지 않는다.
- Wide v2 조건식을 이번 설계에서 만들지 않는다.
- 후보 조건식 개선이나 ranking 결과를 이번 설계의 완료 조건으로 삼지 않는다.
- WFO를 `discovery research` 안으로 다시 넣지 않는다.
- runtime DB, generated CSV, graph 산출물을 Git에 커밋하지 않는다.

## 권장 접근

추천은 독립 preflight 경로를 먼저 만들고, 이후 후보 루프의 선행 게이트로 연결하는 단계적 방식이다.

```text
[PR 1: CLI/GUI Tick Backtest Parity Preflight]
        |
        v
[PR 2: Wide v1 Retention-Aware 후보 개선 재실행]
```

### PR 1

```text
runtime-preflight 또는 동등한 독립 진단 경로 추가
DB 경로 출력
전략코드 정상성 검증
실행 config 출력
timeout checkpoint 기반 추가
테스트/문서화
```

### PR 2

```text
preflight 통과 증거 확보
CLI baseline 1회 백테스트 성공
Wide v1 CSV 기반 후보 5개 백테스트
estimated_retention 기록
actual trade_count_retention 기록
adjusted_score ranking 기록
best_candidate 분석
candidate cleanup 확인
```

## Runtime Preflight 설계

CLI는 heavy 백테스트를 시작하기 전에 현재 사용하는 runtime 파일과 실행 조건을 출력하고 검증해야 한다.

필수 출력 항목은 다음이다.

```text
project_root
strategy_db_path
setting_db_path
backtest_db_path
stock_tick_back_db_path
csv_output_dir

buy_strategy_name
buy_strategy_exists
buy_strategy_code_length
buy_strategy_compile_status
buy_strategy_evaluate_status

sell_strategy_name
sell_strategy_exists
sell_strategy_code_length
sell_strategy_compile_status
sell_strategy_evaluate_status

start
end
timeframe
avg_time
start_time
end_time
engines
timeout
```

치명 실패 조건은 다음이다.

```text
strategy.db 없음
stock_tick_back.db 없음
전략명 없음
전략코드가 비정상적으로 짧음
전략코드가 ????로 읽힘
compile 실패
evaluate_strategy 실패
```

이 중 하나라도 발생하면 CLI는 후보 백테스트를 시작하지 않는다.

## Baseline CLI Gate 설계

Wide v1 후보 5개 백테스트 전에 baseline 전략 1회를 CLI로 먼저 실행한다.

```text
[Runtime Preflight]
        |
        v
[Baseline CLI Backtest 1회]
        |
        +-- success -> candidate_count=5 실행
        |
        +-- fail    -> candidate loop 중단
```

baseline CLI 성공 기준은 다음이다.

```text
status=success
csv_path exists
back_count 기록
trade_count 기록
runtime 기록
backtest.db 결과 row 확인
GUI 기준 결과와 비교 가능한 summary 기록
```

초기 단계에서는 거래 수가 GUI 결과와 1건까지 완전히 같아야 한다고 강제하지 않는다. 먼저 실행 완료, CSV 생성, 거래 수 존재, back_count 비교를 1차 성공 기준으로 둔다. 이후 CLI/GUI 차이가 남으면 수치 parity 기준을 강화한다.

## Timeout Checkpoint 설계

timeout은 단순 실패가 아니라 마지막 진행 상태와 함께 기록되어야 한다.

권장 checkpoint는 다음이다.

```text
preflight_started
strategy_validated
tick_db_opened
moneytop_loaded
engine_processes_started
shared_data_loaded
back_count_ready
backtest_process_started
backtest_process_finished
csv_detected
backtest_db_row_detected
cleanup_done
```

timeout 결과는 다음 정보를 포함한다.

```text
status=timeout
elapsed_seconds=900
last_checkpoint=shared_data_loaded
runtime_profile=wt-dev-runtime
buy_strategy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
cleanup_status=ok 또는 failed
```

이 구조가 있어야 timeout 원인이 조건식, DB 경로, 데이터 로딩, engine process, BackTest process, CSV 감지 중 어디에 가까운지 분리할 수 있다.

## Worktree 실행 정책

현재 단계에서는 heavy tick 백테스트를 `wt-dev` runtime 기준으로 검증한다.

feature worktree는 코드와 문서 작업에는 적합하지만, runtime DB와 generated output은 worktree마다 달라질 수 있다. 따라서 tick 백테스트 실행은 다음 정책을 따른다.

```text
1. wt-dev GUI/STOM 성공 결과를 기준 truth로 둔다.
2. heavy tick baseline 검증은 우선 wt-dev runtime에서 수행한다.
3. feature worktree에서 실행해야 할 경우 runtime profile로 wt-dev DB 경로를 명시한다.
4. runtime DB 복사나 overlay는 기본 방식으로 삼지 않는다.
5. 후보 전략 cleanup 결과를 반드시 확인한다.
```

장기적으로는 feature worktree에서도 다음처럼 명시 runtime profile을 통해 같은 DB를 바라보게 할 수 있다.

```text
profile:
wt-dev-runtime

strategy_db:
C:\System_Trading\STOM\STOM_V.wt-dev\_database\strategy.db

setting_db:
C:\System_Trading\STOM\STOM_V.wt-dev\_database\setting.db

backtest_db:
C:\System_Trading\STOM\STOM_V.wt-dev\_database\backtest.db

stock_tick_back_db:
C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db

csv_dir:
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv
```

## CLI 표면 선택지

### 선택지 A: 기존 diagnose 확장

기존 진단 기능에 runtime preflight를 추가한다.

장점:

```text
기존 진단 기능과 성격이 맞음
후보 루프와 분리되어 안전함
PR 범위가 작음
```

단점:

```text
후보 루프와 자동 연결하려면 추가 옵션이 필요함
```

### 선택지 B: 새 runtime-preflight 서브커맨드 추가

독립 명령으로 runtime preflight를 추가한다.

장점:

```text
명령 의미가 명확함
GUI/CLI parity 검증 전용으로 설계하기 좋음
후속 단계에서 discovery research의 선행 게이트로 재사용하기 좋음
```

단점:

```text
새 CLI 표면이 추가됨
subcommands 구조에 새 명령을 넣어야 함
```

### 선택지 C: discovery research 내부에 강제 preflight 추가

후보 루프 실행 전에 자동으로 preflight를 수행한다.

장점:

```text
preflight 없이 후보 루프를 실행하는 실수를 줄임
자동 연구 루프와 직접 연결됨
```

단점:

```text
discovery research가 더 무거워짐
실패 원인이 후보 생성과 runtime 진단 사이에서 섞일 수 있음
```

최종 추천은 B를 먼저 적용하고 C를 후속으로 연결하는 것이다.

```text
[1차]
runtime-preflight 독립 진단 경로
        |
        v
[2차]
baseline CLI gate를 discovery research 후보 루프 앞에 선택 옵션으로 연결
        |
        v
[3차]
Wide v1 Retention-Aware 후보 5개 실행 재개
```

## 테스트 전략

단위 테스트는 heavy tick DB를 직접 돌리지 않고, preflight와 gate 판단을 빠르게 검증한다.

```text
Runtime profile resolver
- strategy.db 경로 확인
- setting.db 경로 확인
- backtest.db 경로 확인
- stock_tick_back.db 경로 확인
- csv_dir 경로 확인

Strategy preflight
- 전략명 없음 -> 실패
- 전략코드 ???? -> 실패
- 전략코드 길이 너무 짧음 -> 실패
- compile 실패 -> 실패
- 정상 전략코드 -> 통과

Backtest gate
- baseline gate 실패 시 candidate loop 차단
- baseline gate 성공 시 candidate loop 진입 허용

Timeout checkpoint reporter
- timeout 발생 시 last_checkpoint 기록
- cleanup 상태 기록
```

실제 파일럿 검증은 `wt-dev`에서 수행한다.

```text
1. wt-dev strategy.db 상태 확인
2. ResearchTest wide 매수/매도 조건식 코드 정상성 확인
3. CLI가 보는 DB 경로 출력
4. CLI baseline 1회 실행
5. GUI 결과와 비교
6. 성공 시 후보 5개 실행
```

## 성공 기준

PR 1 성공 기준:

```text
CLI가 보는 DB 경로가 명확히 출력됨
ResearchTest wide 조건식 코드 정상성이 검증됨
GUI 성공 조건과 CLI 실행 조건이 비교 가능함
CLI baseline 실행 전 실패 원인을 조기에 잡을 수 있음
timeout 발생 시 마지막 진행 지점이 남음
단위 테스트와 기존 unit test가 통과함
verify_nonrelease_sync.py가 통과함
```

PR 2 성공 기준:

```text
preflight 통과
baseline CLI 1회 백테스트 성공
Wide v1 CSV 기반 후보 5개 생성
후보별 백테스트 완료
estimated_retention 기록
actual trade_count_retention 기록
adjusted_score ranking 기록
best_candidate 기록
후보 전략 cleanup 확인
```

## 남은 리스크

1. CLI baseline 1회가 GUI와 완전히 같은 결과를 내지 않을 수 있다.
   - 이 경우 후보 루프 전에 CLI/GUI 차이 원인부터 해결한다.

2. `strategy.db` 인코딩 또는 저장 문제가 반복될 수 있다.
   - preflight에서 코드 길이, `????`, compile, evaluate로 조기 차단한다.

3. feature worktree의 runtime DB가 `wt-dev`와 달라질 수 있다.
   - heavy tick 실행은 우선 `wt-dev` runtime profile 기준으로 제한한다.

4. baseline CLI가 성공해도 후보 5개는 더 오래 걸릴 수 있다.
   - candidate timeout checkpoint와 cleanup 기록이 필요하다.

5. `best_candidate`는 promotion 통과를 의미하지 않는다.
   - 최종 채택 전 `discovery promote` 또는 WFO 검증은 여전히 필요하다.

## 다음 단계

이 spec이 승인되면 다음 단계는 `writing-plans`다.

계획 문서는 다음 작업 단위로 나누는 것이 적절하다.

```text
Task 1: runtime preflight 데이터 구조 설계
Task 2: strategy preflight 검증 함수 추가
Task 3: CLI 서브커맨드 또는 diagnose 확장
Task 4: timeout checkpoint 기록 추가
Task 5: unit test 추가
Task 6: wt-dev baseline CLI 파일럿
Task 7: 문서/update_log 작성
```

구현 완료 후 Wide v1 Retention-Aware 후보 개선은 별도 PR 또는 후속 작업으로 재개한다.
