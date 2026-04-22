# 2026-04-22 Wide v1 Retention-Aware candidate_count=5 실행 재개 설계

## 목적

이번 설계의 목적은 Wide v1 full-year CLI baseline gate가 `PASS`된 상태에서 `discovery research --run-candidates --candidate-count 5` 후보 자동 백테스트를 재개하는 것이다.

이번 단계는 최종 실전 채택이나 WFO 검증이 아니다. 후보 5개를 같은 runtime DB와 같은 baseline CSV 기준으로 실행하고, Retention-Aware 선별과 Retention-Penalized ranking이 실제 full-year tick 조건에서도 동작하는지 확인하는 단계다.

```text
[완료] Wide v1 CLI baseline GUI compare PASS
        |
        v
[이번 설계] Retention-Aware candidate_count=5 실행 재개
        |
        v
[후보 5개 백테스트 결과 / ranking / cleanup 확인]
        |
        v
[best_candidate 분석]
        |
        v
[다음] 반복 개선 루프 v2 또는 후보 원인 분석
```

## 배경

직전 gate 결과:

```text
runtime-preflight=ok
CLI full-year baseline=success
back_count=1638
trade_count=40937
GUI trade_count=40937
decision=PASS
```

이제 CLI가 GUI 기준 Wide v1 baseline을 재현한다는 최소 gate는 통과했다. 따라서 후보 5개 실행을 재개할 수 있다.

다만 이번 실행에서 확인된 중요한 운영 조건이 있다.

```text
운용 폴더명은 바뀔 수 있다.
하지만 실제 runtime _database 폴더는 유지된다.
따라서 STOM_CLI_DATABASE_DIR는 특정 wt-dev 이름이 아니라 실제 운용 _database 폴더를 가리켜야 한다.
```

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
[3. Retention-Aware 후보 선별]
        |
        v
[4. 후보 N개 백테스트 / ranking]       <- 이번 설계
        |
        v
[5. best_candidate 분석]
        |
        v
[6. 반복 개선 루프 v2]
        |
        v
[7. 최종 promote/WFO 검증]
```

## 기준 입력

### 기준 조건식

```text
base_buy_strategy=ResearchTest_Tick_B_090000_092800_Wide_20260419
base_sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
```

### 기준 CSV

이번 후보 실행의 baseline CSV는 PASS된 CLI full-year baseline CSV를 사용한다.

```text
baseline_csv=backtest/csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
baseline_back_count=1638
baseline_trade_count=40937
```

GUI 기준 CSV와 CLI 기준 CSV가 scalar gate에서 일치했으므로, 후보 실행은 CLI 기준 CSV를 사용한다. 이유는 candidate backtest와 같은 CLI/runtime 환경에서 생성된 CSV가 retention estimation과 downstream 비교에 더 일관적이기 때문이다.

### 실행 조건

```text
start=20250101
end=20251231
timeframe=tick
avg_time=30
betting=20
start_time=090000
end_time=092800
engines=32
candidate_count=5
candidate_timeout=900
min_estimated_retention=0.4
candidate_pool_multiplier=3
retention_fallback=enabled
retention_penalty=enabled
```

## runtime DB 경로 정책

### 원칙

`STOM_CLI_DATABASE_DIR`는 `STOM_V.wt-dev` 같은 부모 폴더 이름에 의미적으로 의존하면 안 된다.

운용 관점의 기준은 다음이다.

```text
STOM_CLI_DATABASE_DIR=<실제 운용 _database 폴더>
```

예시:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\<현재_운용_폴더>\_database'
```

개발 worktree에서 운용 DB를 바라보는 경우:

```powershell
$env:STOM_CLI_DATABASE_DIR='C:\System_Trading\STOM\STOM_V.wt-dev\_database'
```

단, 여기서 중요한 것은 `STOM_V.wt-dev`라는 이름이 아니라 그 경로가 현재 운용 `_database`라는 사실이다. 나중에 운용 폴더명이 바뀌면 env 값만 새 `_database` 경로로 바꾸면 된다.

### 실행 전 필수 검증

candidate_count=5 실행 전 아래를 반드시 확인한다.

```text
runtime_profile.setting_db_path
runtime_profile.strategy_db_path
runtime_profile.backtest_db_path
runtime_profile.stock_back_db_path
strategies.buy.status
strategies.sell.status
```

검증 기준:

```text
모든 DB path가 같은 STOM_CLI_DATABASE_DIR 아래를 가리켜야 한다.
strategy buy/sell status가 ok여야 한다.
stock_back_db_usable=True여야 한다.
```

## 접근안

### A. full-year candidate_count=5 직접 실행 추천

PASS된 baseline 조건 그대로 candidate 5개를 실행한다.

장점:

```text
이제 CLI baseline gate가 통과했으므로 실제 후보 루프를 검증할 수 있음
후보별 actual trade_count_retention, adjusted_score, cleanup을 확인 가능
```

단점:

```text
후보 5개가 모두 quality gate를 통과한다는 보장은 없음
실패 시 후보 품질 문제와 execution 문제를 구분해야 함
```

판단: 추천한다. 이전까지 막고 있던 CLI baseline gate가 PASS됐으므로 다음 자연 단계다.

### B. candidate_count=1 또는 2 smoke 재실행

후보 1~2개만 먼저 실행한다.

장점:

```text
리스크가 작음
실패 시 빠르게 원인 확인 가능
```

단점:

```text
이미 baseline full-year가 PASS됐고 짧은 candidate smoke는 과거에 확인했으므로 진행이 느려짐
candidate_count=5 ranking/selection 목적을 검증하지 못함
```

판단: 현재는 보조 fallback으로만 둔다.

### C. 바로 반복 개선 루프 v2로 이동

후보 5개 실행을 생략하고 다음 반복 루프 설계를 시작한다.

장점:

```text
개발 진행은 빠름
```

단점:

```text
candidate_count=5 full-year 실행 증거가 없는 상태에서 v2 설계를 시작하게 됨
retention-aware 실제 효과를 확인하지 못함
```

판단: 채택하지 않는다.

## 권장 설계

이번 단계는 A안을 채택한다.

## 실행 설계

### 1. runtime-preflight

```powershell
$env:STOM_CLI_DATABASE_DIR='<실제 운용 _database 폴더>'
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
buy.status=ok
sell.status=ok
stock_back_db_usable=True
```

### 2. discovery research candidate_count=5 실행

명령어 형태:

```powershell
$env:STOM_CLI_DATABASE_DIR='<실제 운용 _database 폴더>'
python stom_backtest.py discovery research WideV1RetentionCand5_20260422 `
  --input backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv `
  --base-buy-strategy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --betting 20 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --run-candidates `
  --candidate-count 5 `
  --candidate-timeout 900 `
  --min-estimated-retention 0.4 `
  --candidate-pool-multiplier 3
```

주의:

```text
--run-candidates를 사용한다.
--run-candidate와 동시에 쓰지 않는다.
--candidate-plan-only는 쓰지 않는다.
WFO 옵션은 쓰지 않는다.
```

### 3. 결과 수집

필수 수집 항목:

```text
iteration_plan
retention_selection
candidate_results
retention-penalized ranking
best_candidate
cleanup 결과
후보 전략 잔여 여부
```

후보별 확인 항목:

```text
strategy_name
expression
estimated_retention
retention_filter_passed
retention_fallback_used
status
trade_count
trade_count_retention
promotion_score
retention_penalty
adjusted_score
csv_path
cleanup_status
```

### 4. 판정

#### PASS_FOR_EXECUTION

```text
command completes without timeout
candidate_count=5 attempted
candidate_results are recorded
candidate ranking is present
cleanup status is recorded
runtime artifacts are not staged
```

#### PASS_WITH_NO_PROMOTION

```text
execution succeeds
all candidates fail promotion gate
failure reasons are documented
cleanup is clean
```

이 상태는 실패가 아니다. 후보 품질 개선으로 넘어갈 수 있다.

#### HOLD

```text
execution succeeds but fewer than 5 candidates are selected or executed
retention fallback behavior needs interpretation
one or more candidate results are missing
```

#### FAIL

```text
runtime-preflight fails
command timeout
candidate backtest process error
candidate strategy cleanup fails
runtime DB path mismatch
result report cannot be parsed
```

## 문서화 산출물

pilot log:

```text
docs/research/condition_research/pilot_logs/2026-04-22_wide_v1_retention_candidate_count_5.md
```

update log:

```text
docs/update_log/2026-04-22_wide_v1_retention_candidate_count_5.md
```

포함 내용:

```text
전체 플로우
runtime DB path 검증
preflight 결과
candidate_count=5 실행 명령
retention selection summary
candidate result table
ranking summary
best_candidate
cleanup summary
PASS/HOLD/FAIL 판정
다음 superpower 명령
```

## 성공 기준

이번 단계의 성공 기준은 “좋은 후보가 반드시 나온다”가 아니다.

성공 기준:

```text
1. runtime DB path가 명시/검증된다.
2. candidate_count=5 실행이 timeout 없이 완료된다.
3. 후보별 결과와 ranking이 문서화된다.
4. 실패 후보도 cleanup 상태가 기록된다.
5. best_candidate가 있으면 다음 분석 단계로 연결된다.
6. best_candidate가 없어도 failure reasons가 문서화된다.
```

## 남은 리스크

1. candidate_count=5가 모두 promotion gate를 통과하지 못할 수 있다.
   - 이는 실행 실패가 아니라 후보 품질 문제일 수 있다.

2. estimated_retention은 baseline executed trades 기준 추정치다.
   - 실제 후보 백테스트 trade_count_retention과 다를 수 있다.

3. fallback 후보가 포함될 수 있다.
   - fallback이 쓰였는지 반드시 리포트에 남긴다.

4. runtime DB path를 잘못 지정하면 이전과 같은 조건식/setting DB 불일치가 재발할 수 있다.
   - preflight와 runtime_profile path 기록이 필수다.

5. best_candidate는 최종 채택이 아니다.
   - 최종 채택 전에는 반복 개선 루프 v2, promote 또는 WFO 검증이 필요하다.

## 다음 단계

이 spec이 승인되면 다음은 `writing-plans`다.

권장 명령:

```text
$writing-plans Wide v1 Retention-Aware candidate_count=5 실행 재개 계획 작성
```

실행 결과별 다음 명령:

```text
PASS_FOR_EXECUTION or PASS_WITH_NO_PROMOTION:
  $brainstorming Wide v1 후보 결과 분석 및 반복 개선 루프 v2 설계

HOLD:
  $brainstorming Wide v1 candidate_count=5 부분 실행 원인 분석 설계

FAIL:
  $brainstorming Wide v1 candidate_count=5 실행 실패 checkpoint 분석 설계
```
