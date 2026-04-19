# 2026-04-19 Candidate Quality Gate And Retention-Aware Selection

## 목적

후보 N개 파일럿에서 모든 후보가 `trade_count_retention<0.4`로 탈락한 문제를 완화하기 위해, 후보 실행 전 `estimated_retention` 선별과 실행 후 retention penalty ranking을 추가했다.

## 전체 플로우

```text
[0. 기준 전략]
        |
        v
[1. 기준 백테스트 결과 CSV]
        |
        v
[2. CSV 분석]
        |
        v
[3. 후보 expression pool 생성]
        |
        v
[4. Retention-Aware 후보 선별]
        |
        v
[5. 후보 N개 백테스트]
        |
        v
[6. Retention-Penalized Ranking]
        |
        v
[7. best_candidate 선택]
        |
        v
[8. 최종 promote/WFO 검증]
```

## 변경 사항

- `cli/research_retention.py` 추가
- baseline 거래 CSV 기준 `estimated_retention` 계산
- `B_` 접두 CSV 컬럼을 런타임 변수명으로 alias 처리
- expression 평가 실패를 low-retention 후보로 보수 처리
- retention 통과 후보 우선 선택
- 후보 부족 시 fallback 후보 포함 또는 `insufficient_retention_candidates` 반환
- `retention_penalty` / `adjusted_score` ranking 적용
- 음수 promotion score가 retention penalty로 보상받지 않도록 방어
- `discovery research` CLI 옵션 추가
  - `--min-estimated-retention`
  - `--no-retention-fallback`
  - `--no-retention-penalty`
  - `--candidate-pool-multiplier`
- Markdown 리포트에 retention-aware selection과 retention-penalized ranking 섹션 추가

## 검증

### focused tests

```powershell
python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

결과:

```text
145 passed
```

### full unit tests

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
993 passed, 1 skipped, 10 warnings
```

### non-release sync

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

### lint

```powershell
ruff check cli/research_retention.py cli/research_loop.py cli/research_report.py cli/subcommands.py tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py
```

결과:

```text
All checks passed!
```

## 파일럿

### 1차 tick retention 파일럿

명령:

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py discovery research TickResearchRetentionPilot_20260419 `
  --input backtest/csv/stock_bt_Tick_B_902_905_Update_2_20260419092230.csv `
  --base-buy-strategy Tick_B_902_905_Update_2 `
  --sell Tick_S_902_905_Update_2 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --run-candidates `
  --candidate-count 5 `
  --min-estimated-retention 0.4 `
  --candidate-start 20250101 `
  --candidate-end 20251231 `
  --candidate-timeout 900 `
  --cleanup-best-candidate
```

결과:

```text
status: error
phase: no_expressions
```

원인:

```text
기준 tick CSV row 수가 100개이고 기본 min_samples=30이라 후보 expression이 생성되지 않았다.
```

### 후보 생성 조건 확인

`min_samples`를 낮춰 분석 후보 생성 가능 여부를 확인했다.

```text
min_samples=30: expression 0개
min_samples=20: expression 0개
min_samples=10: expression 15개 이상
min_samples=5: expression 15개 이상
```

### 2차 tick retention 파일럿

명령은 1차와 같고 `--min-samples 10`을 추가했다.

결과:

```text
외부 실행 timeout
```

상태:

```text
full-year tick 후보 5개, 32멀티수 조건은 현재 세션 제한 시간 안에 완료되지 않았다.
timeout 뒤 후보 전략 잔여를 확인했고, 남아 있던 cand001은 수동 삭제했다.
```

후보 전략 잔여 확인:

```text
TickResearchRetentionPilot_20260419_MS10__cand001 0
TickResearchRetentionPilot_20260419_MS10__cand002 0
TickResearchRetentionPilot_20260419_MS10__cand003 0
TickResearchRetentionPilot_20260419_MS10__cand004 0
TickResearchRetentionPilot_20260419_MS10__cand005 0
```

## 해석

Retention-aware 기능의 단위/통합 테스트는 통과했다.

다만 요청한 full-year tick 후보 5개 파일럿은 다음 두 가지 이유로 아직 성공 완료 증거를 확보하지 못했다.

```text
1. 기본 min_samples=30에서는 후보 expression이 생성되지 않음
2. min_samples=10에서는 후보 expression은 생성되지만 full-year tick 후보 5개 실행이 세션 제한 시간 안에 끝나지 않음
```

## 남은 리스크

- `estimated_retention`은 baseline executed trade 기준 추정치이므로 신규 거래 생성 가능성은 사전 추정하지 못한다.
- tick full-year 후보 5개 파일럿은 비용이 커서 더 긴 실행 환경이 필요하다.
- `best_candidate`는 promotion 통과를 의미하지 않는다.
- promotion gate `min_trade_count_retention=0.4`는 유지되므로 후보가 계속 탈락할 수 있다.
- 최종 채택 전에는 `discovery promote` 또는 별도 WFO 검증이 필요하다.

## 다음 파일럿 권장

full-year tick 후보 5개 대신 다음 순서가 더 안전하다.

```text
1. --min-samples 10으로 후보 생성 확인
2. candidate_count=1 또는 2로 full-year tick smoke 실행
3. 성공하면 candidate_count=5로 확대
4. 또는 candidate 기간을 분기/월 단위로 줄여 retention-aware ranking 동작을 먼저 검증
```
