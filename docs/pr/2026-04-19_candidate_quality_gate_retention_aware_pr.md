# Candidate Quality Gate / Retention-Aware Selection PR 보고서

## 1. 이번 PR의 목적

이번 PR은 `Backtest Iteration Research Loop v1` 이후 확인된 후보 품질 문제를 해결하기 위한 후속 작업이다.

최근 tick 후보 5개 파일럿에서 후보 실행, ranking, cleanup은 정상 동작했지만 모든 후보가 아래 사유로 promotion을 통과하지 못했다.

```text
trade_count_retention<0.4
```

`trade_count_retention`의 의미는 다음이다.

```text
candidate trade count / baseline trade count
```

즉 후보 조건식이 손실 구간을 줄였을 수는 있지만, 기준 전략 대비 거래를 너무 많이 제거해서 실전 후보로 보기 어렵다는 뜻이다.

이번 PR은 promotion gate를 완화하지 않고, 후보 품질 자체를 개선하는 방향으로 해결한다.

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
[4. Retention-Aware 후보 선별]      <- 이번 PR
        |
        v
[5. 후보 N개 백테스트]
        |
        v
[6. Retention-Penalized Ranking]    <- 이번 PR
        |
        v
[7. best_candidate 선택]
        |
        v
[8. 반복 개선 루프 v2]
        |
        v
[9. 최종 promote/WFO 검증]
```

핵심 목표:

- 후보 실행 전 `estimated_retention`을 계산한다.
- 거래를 너무 많이 제거할 후보를 후순위로 보낸다.
- 후보 부족 시 fallback 여부를 명시한다.
- 후보 실행 후 `retention_penalty`와 `adjusted_score`를 ranking에 반영한다.
- 기존 promotion gate `min_trade_count_retention=0.4`는 완화하지 않는다.
- WFO는 `discovery research`에 다시 넣지 않는다.

## 2. 이번 PR의 변경 사항

### 2.1 신규 모듈

```text
cli/research_retention.py
```

역할:

- baseline 거래 CSV 기준 `estimated_retention` 계산
- `B_` 접두 컬럼 alias 처리
- expression 평가 실패를 low-retention 후보로 보수 처리
- retention 통과 후보 우선 선택
- fallback 후보 선별
- `retention_penalty` / `adjusted_score` 계산

### 2.2 research loop 연결

```text
cli/research_loop.py
```

추가된 흐름:

```text
generate_condition_expressions_from_analysis()
-> annotate_candidate_retention()
-> select_retention_aware_candidates()
-> _build_candidate_specs()
-> _execute_candidate_spec()
-> _rank_candidate_results() with adjusted_score
```

추가된 `ResearchLoopConfig` 필드:

```python
min_estimated_retention: float = 0.40
allow_retention_fallback: bool = True
use_retention_penalty: bool = True
candidate_pool_multiplier: int = 3
```

### 2.3 CLI 옵션 추가

```text
cli/subcommands.py
```

추가 옵션:

```text
--min-estimated-retention
--no-retention-fallback
--no-retention-penalty
--candidate-pool-multiplier
```

기본 정책:

```text
retention-aware selection: enabled
fallback: enabled
retention penalty: enabled
candidate_pool_multiplier: 3
```

### 2.4 리포트 확장

```text
cli/research_report.py
```

추가 리포트 섹션:

```text
## Retention-Aware Candidate Selection
## Retention-Penalized Ranking
```

표시 정보:

- `retention_selection`
- 후보별 `estimated_retention`
- `retention_filter_passed`
- `retention_fallback_used`
- `retention_penalty`
- `adjusted_score`

### 2.5 테스트 추가

추가/확장 테스트:

```text
tests/unit/test_research_retention.py
tests/unit/test_research_loop.py
tests/unit/test_research_report.py
tests/unit/test_subcommands.py
```

검증 항목:

- `B_` alias 처리
- expression 평가 실패 방어
- retention pass/fallback 정책
- fallback disabled error
- candidate_count 계약 유지
- negative score penalty 보정
- CLI payload 전달
- Markdown report 렌더링

### 2.6 update log

```text
docs/update_log/2026-04-19_candidate_quality_gate_retention_aware.md
```

포함 내용:

- 변경 사항
- 검증 결과
- tick 파일럿 결과
- 남은 리스크
- 다음 파일럿 권장 순서

## 3. 검증 결과

### 3.1 focused tests

```powershell
python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

결과:

```text
145 passed
```

### 3.2 full unit tests

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
993 passed, 1 skipped, 10 warnings
```

경고는 기존 SciPy precision warning, binance/websockets deprecation warning 계열이며 이번 변경에서 새로 만든 실패는 아니다.

### 3.3 ruff

```powershell
ruff check cli/research_retention.py cli/research_loop.py cli/research_report.py cli/subcommands.py tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py
```

결과:

```text
All checks passed!
```

### 3.4 non-release sync

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

### 3.5 tick 파일럿 결과

#### 1차 파일럿

조건:

```text
strategy: Tick_B_902_905_Update_2 / Tick_S_902_905_Update_2
timeframe: tick
period: 2025-01-01 ~ 2025-12-31
time: 09:00:00 ~ 09:28:00
avg_time: 30
engines: 32
candidate_count: 5
min_estimated_retention: 0.4
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

#### 후보 생성 조건 확인

분석 조건만 변경해서 후보 생성 가능 여부를 확인했다.

```text
min_samples=30: expression 0개
min_samples=20: expression 0개
min_samples=10: expression 15개 이상
min_samples=5: expression 15개 이상
```

#### 2차 파일럿

조건:

```text
1차 조건 + --min-samples 10
```

결과:

```text
외부 실행 timeout
```

상태:

```text
full-year tick 후보 5개, 32멀티수 조건은 현재 세션 제한 시간 안에 완료되지 않았다.
timeout 뒤 후보 전략 잔여를 확인했고, 남아 있던 cand001은 수동 삭제했다.
```

후보 전략 cleanup 확인:

```text
TickResearchRetentionPilot_20260419_MS10__cand001 0
TickResearchRetentionPilot_20260419_MS10__cand002 0
TickResearchRetentionPilot_20260419_MS10__cand003 0
TickResearchRetentionPilot_20260419_MS10__cand004 0
TickResearchRetentionPilot_20260419_MS10__cand005 0
```

## 4. 남은 리스크

### 4.1 full-year tick candidate_count=5 파일럿 성공 완료 증거 부족

이번 PR은 단위/통합 테스트와 설계된 기능 경로는 통과했지만, full-year tick 후보 5개 파일럿은 세션 제한 시간 안에 완료하지 못했다.

해결 방향:

```text
candidate_count=1~2로 smoke 확인
또는 기간을 월/분기 단위로 줄여 먼저 성공 경로 확인
```

### 4.2 estimated_retention은 baseline executed trades 기준 추정치

`estimated_retention`은 기존 기준 전략에서 실제 체결된 거래를 기준으로 계산한다.

따라서 후보 전략이 새로 만들 수 있는 신규 거래 가능성은 사전 예측하지 못한다.

이 값은 최종 판단이 아니라 실행 전 후보 품질 보정용이다.

### 4.3 best_candidate는 promotion 통과를 의미하지 않음

`best_candidate`는 후보 묶음 안에서 상대적으로 가장 나은 후보일 뿐이다.

실전 채택 후보가 되려면:

```text
promotion.passed = True
```

또는 별도 `discovery promote` / WFO 검증이 필요하다.

### 4.4 Tick Research Baseline Condition 설계 필요

현재 기준 tick 전략의 거래 수는 연구 데이터 확보 관점에서 충분하지 않을 수 있다.

다음 단계에서는 수익률 최적화보다 넓은 거래 데이터 확보를 목표로 하는 연구용 tick baseline 조건식을 설계하는 것이 적절하다.

## 5. 7dd225f 이후 merge 흐름 분석

기준 커밋:

```text
7dd225f662fd59ec321e008cd0650f2f72ecc6cd
주식 백테스트 실행조건 로그를 추가한다
```

이후 `STOM_Version_2U_C`에서 진행된 주요 merge 흐름은 모두 자동 조건식 연구/개선 개발의 연장선이다.

```text
7dd225f
  백테스트 실행조건 로그 계측
  목적: 백테스트 실행 조건을 명확히 기록해 후속 연구 루프의 재현성 기반 확보

e8a75547
  세그먼트 기반 조건식 연구 루프 추가
  담당 단계: CSV 분석, 후보 조건식 생성, 단일 후보 백테스트, 비교/리포트 기반 구축

a3f093cc
  discovery research WFO 검증 연결
  담당 단계: research 후보를 WFO로 검증하는 실험적 연결

a62c9754
  discovery research에서 WFO 연결 제거
  담당 단계: research는 빠른 루프로 유지하고 WFO는 promote/final validation으로 역할 분리

f94ae507
  후보 백테스트 런타임 안정화
  담당 단계: candidate_start/end/timeout, plan-only, 실패 후보 cleanup

3cef3749 / PR #12
  Backtest Iteration Research Loop v1
  담당 단계: 후보 N개 백테스트, ranking, best_candidate 선택, cleanup/report

이번 PR
  Candidate Quality Gate / Retention-Aware Selection
  담당 단계: 후보 실행 전 retention-aware 선별, 실행 후 retention-penalized ranking
```

## 6. 전체 개발 단계와 현재 위치

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
[4. Retention-Aware 후보 선별]      <- 이번 PR
        |
        v
[5. 후보 N개 백테스트]
        |
        v
[6. Retention-Penalized Ranking]    <- 이번 PR
        |
        v
[7. best_candidate 선택]
        |
        v
[8. 반복 개선 루프 v2]
        |
        v
[9. 최종 promote/WFO 검증]
```

현재 완료된 단계:

- CSV 분석
- 후보 조건식 생성
- 단일 후보 백테스트
- 후보 N개 백테스트/랭킹
- Retention-Aware 후보 선별
- Retention-Penalized Ranking

아직 남은 단계:

- 넓은 연구용 tick baseline 조건식 설계
- best_candidate 기반 조건식 재생성
- 반복 개선 루프 v2
- 최종 promote/WFO 검증
- 장기 품질 검증

## 7. 다음 단계 안내

PR merge 후 다음 브레인스토밍은 아래 명령으로 시작하는 것이 적절하다.

```text
$brainstorming Tick Research Baseline Condition 설계
```

포함할 맥락:

- Backtest Iteration Research Loop v1 완료
- Candidate Quality Gate / Retention-Aware Selection 완료
- 기존 `Tick_B_902_905_Update_2` 기준 전략은 거래 수가 100회 수준이라 연구 데이터가 부족함
- 다음 목표는 수익률 최적화가 아니라 연구 데이터 확보용 넓은 tick baseline 조건식 설계
- `E:\Download\backtest_analysis_report_v2.md`를 `docs/research/condition_research/source_reports/`로 복사/보존
- 보고서 기반으로 09:00:00~09:28:00, 30틱, 32멀티수 조건에서 넓은 매수/매도 조건식 생성
- `strategy.db`에 research/test/tick/wide임을 구분할 수 있는 이름으로 저장
- 직접 백테스팅 후 그 결과를 다음 자동 개선 루프의 기준 CSV로 사용

추천 연구용 전략명:

```text
ResearchTest_Tick_B_090000_092800_Wide_20260419
ResearchTest_Tick_S_090000_092800_Wide_20260419
```
