# 후보 백테스트 런타임 안정화 PR 보고서

## 목적

`discovery research --run-candidate` 후보 백테스트가 실패하거나 timeout되어도 연구 루프가 안전하게 복구되도록 실행 제어와 cleanup을 추가한다.

기존 실제 파일럿에서 preview 모드는 정상 동작했지만, 후보 백테스트는 짧은 기간에서도 timeout될 수 있었다. 이번 PR은 후보 N개 반복 연구 루프로 넘어가기 전에 후보 1개의 실행 실패가 `strategy.db`를 오염시키지 않고, 결과 리포트에 원인과 cleanup 상태가 남도록 하는 기반이다.

## 변경 요약

- 후보 실행 계획 `candidate_plan` 추가
- `--candidate-start`, `--candidate-end` 추가
- `--candidate-timeout` 추가
- `--candidate-plan-only` 추가
- `--keep-failed-candidate` 추가
- 후보 백테스트 전용 기간/timeout을 candidate run config에 반영
- 후보 백테스트 실패/timeout phase 구분
- 실패/timeout 후보 전략 기본 삭제
- 후보 CSV 누락과 비교 실패 시 cleanup
- cleanup 실패가 원래 오류를 가리지 않도록 방어
- 리포트에 `## Candidate Runtime` 섹션 추가
- update_log 추가

## CLI 예시

### 실행 계획만 확인

```powershell
python stom_backtest.py discovery research AutoResearchPlan01 `
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --candidate-start 20250407 `
  --candidate-end 20250408 `
  --candidate-timeout 300 `
  --candidate-plan-only
```

### 짧은 후보 백테스트 실행

```powershell
python stom_backtest.py discovery research AutoResearchRun01 `
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidate `
  --candidate-start 20250407 `
  --candidate-end 20250408 `
  --candidate-timeout 300
```

## 검증

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

결과:

```text
92 passed
```

```powershell
python -m pytest tests/unit/test_research_metrics.py tests/unit/test_research_segments.py tests/unit/test_research_candidates.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py tests/unit/test_research_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

결과:

```text
141 passed
```

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
938 passed, 1 skipped, 10 warnings
```

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

## 남은 리스크

- 후보 백테스트 자체가 여전히 느릴 수 있다.
- 너무 짧은 candidate 기간은 통계적으로 의미가 약할 수 있다.
- `--keep-failed-candidate` 사용 시 실패 후보가 `strategy.db`에 남으므로 수동 정리가 필요할 수 있다.
- 다음 단계는 후보 N개 반복 실행과 최고 후보 선택이다.

## 다음 단계

후보 백테스트 런타임 안정화가 머지되면 다음 큰 단계는 `Backtest Iteration Research Loop`이다.

```text
백테스트 결과 분석
-> 후보 N개 생성
-> 후보별 백테스트
-> 기준/후보 비교
-> 최고 후보 선택
-> 반복
```
