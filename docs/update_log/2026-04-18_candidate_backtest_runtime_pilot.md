# 2026-04-18 후보 백테스트 런타임 파일럿 검증

## 목적

PR #11 `후보 백테스트 런타임 안정화`가 `STOM_Version_2U_C`에 머지된 뒤, 실제 `discovery research --run-candidate` 경로가 짧은 후보 구간에서 실행 가능한지 확인했다.

이번 검증은 다음 Phase인 `Backtest Iteration Research Loop`로 넘어가기 전, 후보 1개 백테스트 실행이 timeout 없이 끝나고 결과/비교/승격 평가까지 반환되는지 확인하기 위한 사후 파일럿이다.

## 기준 상태

- 브랜치: `STOM_Version_2U_C`
- 기준 커밋: `f94ae507 후보 백테스트 런타임 안정화`
- 비교 기준 CSV: `backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv`
- 기준 매수 전략: `Min_B_Study_251227`
- 매도 전략: `Min_S_Study_251227`
- 후보 전략명: `AutoResearchPilot_20260418_Runtime01`

## 진행 로그

### 1. 브랜치 상태 확인

```powershell
git status --short --branch
```

결과:

```text
## STOM_Version_2U_C...origin/STOM_Version_2U_C
?? backtest/graph/
```

`backtest/graph/`는 기존 보호 결과 데이터로 판단하여 건드리지 않았다.

### 2. 단위 테스트 및 비정식 워크트리 가드레일 확인

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

결과:

```text
92 passed in 4.62s
```

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

### 3. 실제 후보 백테스트 파일럿 실행

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py discovery research AutoResearchPilot_20260418_Runtime01 `
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidate `
  --candidate-start 20250407 `
  --candidate-end 20250407 `
  --candidate-timeout 120
```

주요 결과:

```text
status: ok
candidate_csv: backtest/csv\stock_bt_AutoResearchPilot_20260418_Runtime01_20260418113951.csv
candidate duration: 50.5s
candidate trade_count: 4
candidate win_rate: 50.0
candidate avg_profit_pct: 1.12
candidate tpi: 1.44
candidate expression: 시가총액 <= 2793.5
promotion passed: false
promotion reasons: trade_count<20, trade_count_retention<0.4, date_concentration>0.5
```

해석:

- 후보 백테스트는 `candidate_timeout=120` 안에서 완료됐다.
- 후보 결과 CSV와 비교 결과, 승격 평가가 정상 반환됐다.
- 후보 구간을 1일로 제한했기 때문에 거래 수가 4회에 그쳤고, 승격 게이트는 통과하지 않았다.
- 이 결과는 런타임 안정화 검증에는 충분하지만 전략 품질 판단에는 충분하지 않다.

### 4. 테스트 후보 전략 정리

파일럿 성공 시 성공 후보 전략은 의도적으로 자동 삭제되지 않는다. 이번 후보는 검증용 이름이므로 `strategy.db` 오염을 막기 위해 수동 정리했다.

```powershell
@'
from cli.paths import DB_STRATEGY
from cli.strategy_generator import delete_strategy_from_db
print(delete_strategy_from_db(DB_STRATEGY, 'AutoResearchPilot_20260418_Runtime01', 'buy'))
'@ | python -
```

결과:

```text
{'status': 'ok', 'name': 'AutoResearchPilot_20260418_Runtime01', 'action': 'deleted'}
```

정리 확인:

```text
present=False
```

### 5. 다음 Phase 판단

이번 검증 결과, `discovery research --run-candidate`는 짧은 후보 구간에서 실제 실행 가능한 상태로 확인됐다. 따라서 다음 개발은 WFO가 아니라 `Backtest Iteration Research Loop`로 이어가는 것이 맞다.

다음 Phase의 목표:

```text
백테스트 결과 분석
-> 후보 N개 생성
-> 후보별 짧은 백테스트
-> 기준/후보 비교
-> 최고 후보 선택
-> 반복
```

## 남은 리스크

- 1일 후보 구간은 런타임 검증에는 좋지만 전략 품질 검증에는 표본이 너무 작다.
- 성공한 후보 전략은 자동 삭제되지 않으므로, 반복 루프에서는 임시 후보명 정책과 성공 후보 보존/정리 정책을 명확히 해야 한다.
- 후보 N개 반복 실행은 아직 구현되지 않았다.
- 현재 승격 게이트는 단일 후보 평가 기준이며, 후보 간 랭킹/동률 처리/실패 후보 제외 정책은 다음 Phase에서 정의해야 한다.
- 생성된 후보 CSV는 결과 분석 근거로 남겼지만, 결과 파일 누적 관리 정책은 별도 정리가 필요하다.
