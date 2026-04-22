# 2026-04-22 Wide v1 CLI Baseline Backtest Gate 및 GUI 결과 비교 설계

## 목적

이번 설계의 목적은 Wide v1 ResearchTest tick 조건식을 CLI에서 full-year 기준으로 실행하고, 사용자가 GUI/STOM에서 직접 확보한 기준 결과와 비교해 다음 자동 후보 백테스트 단계로 넘어갈 수 있는지 판단하는 것이다.

이번 단계는 후보 조건식 개선이 아니다. 사람이 GUI에서 수행한 백테스트를 AI/CLI가 같은 조건으로 재현할 수 있는지를 검증하는 baseline gate다.

```text
[기준 GUI Wide v1 결과]
        |
        v
[PR #17: CLI child DB / timeout protocol / tick 설정 키 보강]
        |
        v
[이번 설계: full-year CLI baseline 실행]
        |
        v
[GUI 결과와 metric/CSV 비교]
        |
        v
[PASS/HOLD/FAIL gate]
        |
        v
[후보 N개 자동 백테스트 재개]
```

## 배경

PR #17에서 CLI 백테스트의 주요 blocker를 해결했다.

```text
1. child process가 parent와 같은 runtime DB를 보도록 setting_base/runner DB override 전파
2. BackTest/Total protocol checkpoint 계측
3. tick engine이 요구하는 시장 분석 설정 키 보강
   - 시장미시구조분석=False
   - 시장리스크분석=False
4. 20250102~20250103 smoke 4/32 모두 metrics/CSV 생성 성공
```

이번 gate 실행 중 추가로 확인한 보정 포인트:

```text
legacy utility.setting.py도 STOM_CLI_DATABASE_DIR 및 STOM_CLI_DB_* override를 따라야 한다.
GUI 기준 배팅금액은 종목당 20,000,000원이므로 CLI 명령에는 --betting 20을 포함해야 한다.
```

짧은 smoke 결과:

```text
smoke_4:
  status=success
  trade_count=194
  elapsed_seconds=45.594
  csv_created=True

smoke_32:
  status=success
  trade_count=194
  elapsed_seconds=60.125
  csv_created=True
```

따라서 다음 검증은 짧은 smoke가 아니라 사용자가 GUI에서 이미 실행한 full-year 기준 결과와 같은 조건의 CLI full-year baseline을 비교하는 것이다.

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
[9. CLI child DB / timeout protocol 보강]       완료: PR #17
        |
        v
[10. Wide v1 full-year CLI baseline gate]      이번 설계
        |
        v
[11. GUI 결과와 CLI 결과 비교]
        |
        v
[12. Wide v1 후보 N개 자동 백테스트]
        |
        v
[13. 반복 개선 루프 v2]
        |
        v
[14. 최종 promote/WFO 검증]
```

## 기준 GUI 결과

사용자가 GUI/STOM에서 직접 실행한 기준 결과:

```text
startday=20250101
endday=20251231
starttime=090000
endtime=092800
avgtime=30
betting=20
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
back_count=1638
engine_start=90000
engine_end=92800
engine_avg=[30]
engine_multi=32
betting_amount=20,000,000원
```

결과:

```text
거래횟수=40,937
일평균거래횟수=169.9
적정최대보유종목수=40
평균보유기간=228.19초
익절=12,289
손절=28,648
승률=30.02%
평균수익률=-0.68%
수익률합계=-695.09%
수익금합계=-5,564,960,005원
최대낙폭금액=5,566,752,407원
최대낙폭률=693.76%
매매성능지수=0.60
연간예상수익률=-721.05%
백테스트 소요시간=0:01:00.675279
```

GUI 기준 CSV:

```text
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

## 설계 목표

1. PR #17이 merge되기 전에는 이 브랜치를 stacked branch로 유지한다.
2. PR #17 merge 후 `STOM_Version_2U_C` 최신 상태에서 full-year CLI baseline을 실행한다.
3. CLI 결과 JSON, CSV, checkpoint, DB 최신 row를 수집한다.
4. GUI 기준 결과와 CLI 결과를 비교한다.
5. PASS/HOLD/FAIL을 명확히 문서화한다.
6. PASS일 때만 후보 N개 자동 백테스트 브레인스토밍으로 넘어간다.

## 비목표

```text
candidate_count=5 실행하지 않음
조건식 개선/재생성하지 않음
WFO/promote 실행하지 않음
GUI 결과를 새로 만들거나 수정하지 않음
runtime DB/CSV/graph/temp JSON을 Git에 커밋하지 않음
utility.setting DB override 보강 외의 CLI/backtest 기능 변경은 하지 않음
```

## 접근안

### A. full-year scalar metric gate 추천

CLI full-year를 1회 실행하고, GUI 기준의 핵심 scalar metric과 비교한다.

비교 항목:

```text
back_count
trade_count
win_rate
avg_profit_pct
total_profit_pct
total_profit_krw
mdd_pct
tpi
max_hold_count
avg_hold_time
csv_row_count
```

장점:

```text
GUI 결과와 직접 비교 가능
후보 루프로 넘어갈 최소 신뢰 기준을 세우기 좋음
구현 범위가 작음
```

단점:

```text
거래별 상세 mismatch 원인은 scalar만으로는 알 수 없음
차이가 나면 별도 원인 분석 단계가 필요함
```

판단: 추천한다. 지금 필요한 것은 상세 분석기가 아니라 다음 후보 루프로 넘어갈 수 있는 gate다.

### B. CSV row-level 비교까지 즉시 수행

GUI CSV와 CLI CSV의 거래 row를 직접 비교한다.

장점:

```text
거래 수가 같아도 체결시간/종목/수익률 차이를 조기에 찾을 수 있음
```

단점:

```text
CSV schema, encoding, row sort, timestamp 차이를 먼저 정리해야 함
현재 단계의 범위가 커짐
```

판단: 이번 gate의 보조 옵션으로 둔다. scalar PASS 후 row-level 비교는 별도 hardening 단계로 분리한다.

### C. 후보 N개를 바로 실행하면서 비교

baseline 비교를 생략하고 후보 5개를 실행한다.

장점:

```text
연구 루프로 빨리 넘어감
```

단점:

```text
CLI와 GUI baseline이 같은지 모른 채 후보 결과를 해석하게 됨
문제가 생기면 조건식 문제인지 실행 경로 문제인지 구분하기 어렵다
```

판단: 채택하지 않는다.

## 권장 설계

이번 단계는 A안을 채택한다.

### 1. 실행 전제

PR #17이 merge되기 전:

```text
feature/wide-v1-cli-baseline-gui-compare는 feature/cli-child-runtime-db-override 위의 stacked branch로 유지
PR #17 merge 후 STOM_Version_2U_C 기준으로 재정렬 또는 새 branch 생성
```

PR #17 merge 후:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-dev
git switch STOM_Version_2U_C
git pull origin STOM_Version_2U_C
git switch -c feature/wide-v1-cli-baseline-gui-compare
```

이미 stacked branch에서 작성한 spec/plan은 PR #17 merge 후 rebase/cherry-pick으로 가져온다.

### 2. runtime-preflight

full-year baseline 실행 전 필수로 실행한다.

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
python stom_backtest.py runtime-preflight `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --betting 20 `
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
buy.status=ok
sell.status=ok
stock_back_db_usable=true
```

### 3. CLI full-year baseline

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --betting 20 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900 `
  --format json `
  -o backtest\temp\wide_v1_cli_baseline_gui_compare_20260422.json
```

`backtest/temp/*.json`, 신규 `backtest/csv/*.csv`, `backtest/graph/`는 runtime artifact다. 커밋하지 않는다.

### 4. 비교 기준

#### Hard gate

```text
status=success
checkpoint_status=success
last_checkpoint=csv_detected
csv_path exists
trade_count present
trade_count equals GUI 기준 40937
```

`back_count`는 현재 runner JSON이 직접 노출하지 않을 수 있다. 노출되지 않으면 checkpoint의 `back_count_ready` detail 또는 smoke log를 사용한다. 그래도 확인 불가하면 HOLD다.

#### PASS

```text
preflight=ok
CLI status=success
csv_path exists
checkpoint_status=success
trade_count=40937
back_count=1638 확인 가능
```

#### HOLD

```text
CLI status=success
csv_path exists
trade_count가 GUI 기준과 다름
차이 비율 <= 0.1%
또는 back_count가 runner JSON에서 확인 불가
```

HOLD에서는 후보 N개로 넘어가지 않고 원인 분석 설계를 시작한다.

#### FAIL

```text
preflight=error
CLI status=error
timeout
csv_path 없음
trade_count diff ratio > 0.1%
BackTest/Total protocol diagnostic이 failure를 가리킴
```

### 5. 비교 리포트

pilot log:

```text
docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_cli_baseline_gui_compare.md
```

update log:

```text
docs/update_log/2026-04-22_wide_v1_cli_baseline_gui_compare.md
```

포함 항목:

```text
preflight 결과
CLI full-year 실행 조건
CLI metrics
CLI checkpoint summary
CSV path
GUI 기준값
metric별 diff
PASS/HOLD/FAIL 판정
다음 superpower 명령
```

## 테스트 전략

이번 단계는 실행/문서화 작업이므로 코드 변경은 원칙적으로 하지 않는다.

검증:

```powershell
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_runner_helpers.py tests/unit/test_output.py -q
python scripts/verify_nonrelease_sync.py
git diff --check
```

full-year CLI 실행 자체가 주요 acceptance test다.

## 성공 기준

```text
1. PR #17 변경 기반에서 runtime-preflight가 통과한다.
2. full-year CLI baseline이 metrics/CSV를 생성한다.
3. GUI 기준 결과와 trade_count/back_count 비교가 문서화된다.
4. PASS/HOLD/FAIL 판정이 남는다.
5. PASS일 때만 후보 N개 자동 백테스트 단계로 이동한다.
```

## 남은 리스크

1. GUI 기준 결과와 CLI 결과가 다를 수 있다.
   - 이 경우 조건식 연구가 아니라 CLI/GUI 차이 분석이 우선이다.

2. runner JSON이 `back_count`를 직접 노출하지 않을 수 있다.
   - checkpoint detail에서 보조 확인하고, 부족하면 다음 PR에서 output field를 보강한다.

3. full-year CLI runtime이 GUI보다 길 수 있다.
   - runtime 자체는 hard fail이 아니다. 900초 timeout 초과만 FAIL이다.

4. CSV row-level 비교는 이번 gate의 필수 범위가 아니다.
   - scalar PASS 후 필요하면 별도 row-level parity 설계를 진행한다.

5. PR #17이 아직 merge되지 않았다.
   - 이 branch는 PR #17 위 stacked branch로 다루고, PR #17 merge 후 재정렬한다.

## 다음 단계

이 spec이 승인되면 다음은 `writing-plans`다.

권장 명령:

```text
$writing-plans Wide v1 CLI Baseline Backtest Gate 및 GUI 결과 비교 실행 계획 작성
```

판정별 다음 명령:

```text
PASS:
  $brainstorming Wide v1 Retention-Aware candidate_count=5 실행 재개 설계

HOLD:
  $brainstorming Wide v1 CLI/GUI 결과 차이 원인 분석 설계

FAIL:
  $brainstorming CLI baseline backtest failure checkpoint 분석 설계
```
