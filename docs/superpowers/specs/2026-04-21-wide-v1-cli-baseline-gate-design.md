# 2026-04-21 Wide v1 CLI Baseline Gate Design

## 목적

이번 설계의 목적은 `runtime-preflight`가 통과한 Wide v1 ResearchTest 조건식을 CLI로 1회 baseline 백테스트하고, 사용자가 GUI/STOM에서 직접 실행한 기준 결과와 비교해 `candidate_count=5` 후보 루프로 넘어갈 수 있는지 판단하는 것이다.

이번 단계는 조건식 후보 개선 단계가 아니다. 이번 단계는 AI/CLI 자동 연구 루프가 GUI 백테스트와 같은 기준에서 움직이는지 검증하는 **baseline gate**다.

```text
[완료] Wide v1 GUI/STOM 백테스트 성공
        |
        v
[완료] CLI/GUI runtime-preflight
        |
        v
[이번 설계] CLI baseline 1회 백테스트 Gate
        |
        v
[다음] GUI 결과와 CLI 결과 비교
        |
        v
[그 다음] Wide v1 Retention-Aware 후보 5개 실행
```

## 배경

이전 PR #15에서 `runtime-preflight`와 runner checkpoint 기반을 추가했다.

확보된 상태:

```text
runtime-preflight 공개 CLI 진입점 통과
wt-dev runtime DB 경로 확인
ResearchTest wide 매수/매도 전략코드 정상 확인
stock_tick_back.db table_probe_only 통과
runner checkpoint 기반 추가
```

`wt-dev` runtime-preflight 결과:

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

따라서 다음 작업은 후보 5개 실행이 아니라, 먼저 CLI baseline 1회 백테스트를 실행하고 GUI 결과와 비교하는 것이다.

## 전체 개발 흐름에서의 위치

```text
[0. 기준 전략 / 기준 CSV]
        |
        v
[1. CSV 분석]
        |
        v
[2. 후보 expression pool 생성]
        |
        v
[3. 후보 전략 저장/검증]
        |
        v
[4. 후보 백테스트 런타임 안정화]
        |
        v
[5. 후보 N개 백테스트 / ranking]
        |
        v
[6. Retention-Aware 후보 선별]
        |
        v
[7. 연구용 Wide tick baseline 확보]
        |
        v
[8. CLI/GUI Tick Backtest Parity Preflight]
        |
        v
[9. CLI baseline 1회 백테스트 Gate]  <- 이번 설계
        |
        v
[10. GUI 결과와 CLI 결과 비교]
        |
        v
[11. Wide v1 Retention-Aware 후보 5개 실행]
        |
        v
[12. 반복 개선 루프 v2]
        |
        v
[13. 최종 promote/WFO 검증]
```

이번 설계는 전체 계획을 벗어난 우회가 아니다. 사람의 GUI 연구 과정을 AI/CLI 자동화로 옮기기 위해 필요한 검증 단계다.

## 기준 GUI 결과

사용자가 `STOM_V.wt-dev`의 GUI/STOM 실행 환경에서 직접 실행해 확보한 Wide v1 기준 결과는 다음이다.

```text
startday=20250101
endday=20251231
starttime=090000
endtime=092800
avgtime=30
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
back_count=1638
engine_start=90000
engine_end=92800
engine_avg=[30]
engine_multi=32
```

결과:

```text
거래횟수=40,937
일평균거래횟수=169.9
평균보유기간=228.19초
익절=12,289
손절=28,648
승률=30.02%
평균수익률=-0.68%
수익률합계=-695.09%
수익금합계=-5,564,960,005
최대낙폭금액=5,566,752,407
최대낙폭률=693.76%
매매성능지수=0.60
연간예상수익률=-721.05%
백테스트 소요시간=0:01:00.675279
```

기준 CSV:

```text
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

## 설계 목표

1. `runtime-preflight` 통과를 baseline 실행 전 필수 조건으로 둔다.
2. 같은 조건으로 CLI baseline 1회 백테스트를 실행한다.
3. CLI 결과의 CSV, checkpoint, metrics, back_count, trade_count를 수집한다.
4. GUI 기준 결과와 CLI 결과를 비교한다.
5. PASS / HOLD / FAIL 판정을 문서화한다.
6. PASS 또는 설명 가능한 HOLD일 때만 `candidate_count=5` 후보 루프로 넘어간다.

## 비목표

- 이번 단계에서 `candidate_count=5`를 실행하지 않는다.
- 이번 단계에서 best_candidate나 promotion 판단을 하지 않는다.
- WFO를 `discovery research` 안으로 다시 넣지 않는다.
- CLI baseline 결과 없이 후보 조건식 개선으로 넘어가지 않는다.
- runtime DB, 신규 CSV, graph 산출물, 대형 JSON 원문을 Git에 커밋하지 않는다.
- CLI 전체를 재작성하지 않는다.

## 실행 순서

```text
[0. 상태 확인]
        |
        v
[1. runtime-preflight]
        |
        v
[2. CLI baseline 1회 백테스트]
        |
        v
[3. 결과 CSV / checkpoint 확인]
        |
        v
[4. GUI 기준값과 비교]
        |
        v
[5. PASS / HOLD / FAIL 문서화]
```

## 0. 상태 확인

작업은 `STOM_Version_2U_C`를 보유한 `wt-dev`에서 시작한다.

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-dev
git status --short --branch
git log --oneline -5
```

기대 상태:

```text
## STOM_Version_2U_C...origin/STOM_Version_2U_C
?? backtest/graph/
```

`backtest/graph/`는 protected 산출물이므로 건드리지 않는다.

## 1. runtime-preflight 명령

```powershell
python stom_backtest.py runtime-preflight `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900
```

통과 기준:

```text
status=ok
failed_checks=[]
validation_errors=[]
timeframe_match.status=ok
strategies.buy.status=ok
strategies.sell.status=ok
runtime_profile.stock_back_db_usable=true
runtime_profile.stock_back_db_integrity=table_probe_only
```

preflight가 실패하면 CLI baseline 백테스트를 실행하지 않는다.

## 2. CLI baseline 1회 백테스트 명령

preflight가 통과하면 동일 조건으로 baseline 1회를 실행한다.

```powershell
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900 `
  --format json `
  -o backtest\temp\wide_v1_cli_baseline_20260421.json
```

`backtest\temp\wide_v1_cli_baseline_20260421.json`은 runtime 산출물이다. Git에 커밋하지 않는다.

`--timeout 900`은 첫 baseline gate에서 15분까지 허용하기 위한 값이다. GUI 기준은 약 1분이지만, CLI headless 경로가 아직 baseline 실측되지 않았으므로 첫 gate에서는 timeout을 넉넉히 둔다.

## 3. CLI 결과 수집

JSON 결과에서 최소 아래 항목을 확인한다.

```text
status
message
csv_path
metrics
config
checkpoint_status
last_checkpoint
elapsed_seconds
checkpoints
cleanup_status
```

checkpoint에서 확인할 항목:

```text
preflight_started
dict_set_synced
backtest_watermark_ready
stock_back_db_selected
moneytop_loaded
shared_data_loaded
back_count_ready
backtest_process_started
backtest_process_finished
csv_detected
```

실패 시 특히 확인할 항목:

```text
checkpoint_status
last_checkpoint
message
cleanup_status
child exitcode
csv_path
```

## 4. PASS / HOLD / FAIL 판정

### 4.1 PASS

아래 조건을 모두 만족하면 PASS다.

```text
preflight.status=ok
command_exit_code=0
result.status=success
csv_path 존재
checkpoint_status=success
backtest_process_started checkpoint 존재
backtest_process_finished checkpoint 존재
csv_detected checkpoint 존재
BackTest child exitcode=0 또는 None
back_count=1638
trade_count=40,937
```

PASS면 다음 단계로 `Wide v1 Retention-Aware candidate_count=5 실행 재개 설계`를 시작할 수 있다.

### 4.2 HOLD

아래 조건이면 HOLD다.

```text
preflight.status=ok
CLI 실행 success
CSV 생성
checkpoint 정상 종료
back_count=1638
trade_count가 GUI 기준 40,937과 다름
trade_count 차이 비율 <= 0.1%
```

HOLD는 바로 실패가 아니라 원인 분석 보류다.

HOLD에서 확인할 항목:

```text
CSV 생성 시각이 새 실행 결과인지
기존 GUI CSV와 비교 기준이 같은지
수수료/세금/setting.db 차이가 있는지
backtest.db 결과 row가 최신인지
DICT_SET 동기화 차이가 있는지
```

HOLD 상태에서는 `candidate_count=5`로 넘어가지 않는다. 먼저 차이 원인을 분석한다.

### 4.3 FAIL

아래 중 하나라도 해당하면 FAIL이다.

```text
preflight.status=error
command_exit_code != 0
result.status=error
timeout 발생
csv_path 없음
backtest_process_started checkpoint 없음
backtest_process_finished checkpoint 없음
checkpoint_status=timeout
BackTest child exitcode != 0
back_count != 1638
trade_count 차이 비율 > 0.1%
```

FAIL이면 checkpoint 기반으로 CLI runner, runtime DB, 설정 차이를 분석한다.

## 5. 수치 비교 기준

### back_count

```text
기준: 1638
허용 오차: 0
```

`back_count`는 기간과 데이터 추출 조건의 핵심 값이므로 다르면 FAIL이다.

### trade_count

```text
기준: 40,937
PASS: 정확히 일치
HOLD: 차이 비율 <= 0.1%
FAIL: 차이 비율 > 0.1%
```

0.1%는 약 41건이다.

```text
HOLD 관찰 범위:
40,896 ~ 40,978
```

이 범위는 자동 PASS가 아니라 HOLD다. 자동 PASS는 정확히 일치할 때만 준다.

### runtime

runtime은 hard fail 기준으로 쓰지 않는다.

```text
참고 GUI 기준:
0:01:00.675279
```

다만 baseline 1회가 15분 timeout을 넘으면 FAIL 또는 timeout 분석 대상이다.

### 주요 지표

기록 대상:

```text
win_rate
avg_return
total_return
tpi
max_drawdown
profit_count
loss_count
avg_hold_time
```

이번 gate에서는 주요 지표를 hard fail 기준으로 삼기보다, `trade_count`와 함께 비교 리포트에 기록한다. 단, 거래 수가 같은데 수익률 방향이나 손익 수가 크게 다르면 HOLD 또는 FAIL로 전환한다.

## 6. 문서화 산출물

### 6.1 pilot log

```text
docs/research/condition_research/pilot_logs/2026-04-21_wide_v1_cli_baseline_backtest.md
```

포함 내용:

```text
목적
전체 흐름
preflight 명령과 결과
CLI baseline 명령
CLI baseline 결과
checkpoint 요약
CSV 경로
GUI 기준 결과
CLI 결과와 비교
PASS/HOLD/FAIL 판정
다음 단계
```

### 6.2 update log

```text
docs/update_log/2026-04-21_wide_v1_cli_baseline_gate.md
```

포함 내용:

```text
이번 단계 목적
실행 결과 요약
판정
전체 계획상 위치
남은 리스크
다음 단계
```

## 7. Git에 포함하지 않을 것

아래는 커밋하지 않는다.

```text
_database/*.db
backtest/csv/*.csv 신규 산출물
backtest/graph/
backtest/temp/*.json
대형 JSON 원문
임시 stdout 로그
shared memory 잔여 파일
```

Git에 남길 것은 요약 문서다.

```text
docs/research/condition_research/pilot_logs/*.md
docs/update_log/*.md
필요 시 docs/pr/*.md
```

## 8. 실행 후 분기

### PASS

```text
[PASS]
        |
        v
$brainstorming Wide v1 Retention-Aware candidate_count=5 실행 재개 설계
```

### HOLD

```text
[HOLD]
        |
        v
$brainstorming Wide v1 CLI/GUI 결과 차이 원인 분석 설계
```

### FAIL

```text
[FAIL]
        |
        v
$brainstorming CLI baseline backtest failure checkpoint 분석 설계
```

## 9. 리스크

1. CLI baseline 1회가 GUI와 같은 결과를 내지 않을 수 있다.
   - 이 경우 후보 5개 실행 전에 차이 원인을 분석한다.

2. CLI baseline 실행이 timeout될 수 있다.
   - runner checkpoint의 `last_checkpoint`를 기준으로 멈춘 지점을 분석한다.

3. CLI 결과 JSON에 필요한 비교 필드가 부족할 수 있다.
   - 이 경우 바로 후보 5개로 가지 않고, 결과 수집 필드 보강을 별도 계획으로 분리한다.

4. runtime은 GUI보다 느릴 수 있다.
   - runtime은 hard fail 기준이 아니라 참고값으로 기록한다. 단, timeout은 FAIL이다.

5. HOLD 판정을 과도하게 허용하면 후보 루프 신뢰성이 낮아질 수 있다.
   - HOLD는 자동 진행이 아니라 원인 분석 단계로만 사용한다.

## 10. 다음 단계

이 spec이 승인되면 다음 단계는 `writing-plans`다.

예상 계획 제목:

```text
Wide v1 CLI Baseline Backtest Gate 실행 계획
```

예상 작업 단위:

```text
Task 1: 실행 전 상태 확인과 runtime-preflight 기록
Task 2: CLI baseline 1회 백테스트 실행
Task 3: JSON/checkpoint/CSV 결과 요약
Task 4: GUI 기준값과 비교
Task 5: PASS/HOLD/FAIL 판정 문서 작성
Task 6: update_log 작성과 검증
```

후보 5개 실행은 이 gate가 PASS 또는 설명 가능한 HOLD로 판정된 뒤 별도 브레인스토밍에서 진행한다.
