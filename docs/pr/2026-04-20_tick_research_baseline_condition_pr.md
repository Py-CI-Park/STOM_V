# Tick Research Baseline Condition PR 보고서

## 1. 이번 PR의 목적

이번 PR은 자동 조건식 연구/개선 루프의 다음 입력이 될 **넓은 tick 연구용 baseline 조건식**을 문서화하고, 실제 `wt-dev` 실행 결과를 기록한다.

전체 플로우에서 이번 PR의 위치는 다음과 같다.

```text
[0. 외부 우수 전략 보고서]
        |
        v
[1. docs에 원문/요약 보존]          <- 이번 PR
        |
        v
[2. Wide tick 조건식 문서화]        <- 이번 PR
        |
        v
[3. strategy.db 저장/검증]          <- 이번 PR 기록
        |
        v
[4. 직접 백테스트 결과 기록]        <- 이번 PR
        |
        v
[5. Wide v1 CSV 확보]              <- 완료
        |
        v
[6. Retention-Aware 후보 선별]      <- 다음 단계
        |
        v
[7. 후보 N개 백테스트/랭킹]
```

## 2. 이번 PR의 변경 사항

### 2.1 condition 연구 문서 트리 구성

```text
docs/research/condition_research/
  README.md
  source_reports/
  summaries/
  strategy_designs/
  generated_conditions/
  pilot_logs/
```

### 2.2 외부 원본 보고서 보존

원본:

```text
E:\Download\backtest_analysis_report_v2.md
```

보존 위치:

```text
docs/research/condition_research/source_reports/2026-01-31_backtest_analysis_report_v2.md
```

SHA256 동일 확인:

```text
DC875EF8CF80851397C48A55D5F76D7CA80FDEFD2C21DF826F72C71B6E30B1FD
```

참고:

```text
원본 hash 동일 보존을 위해 trailing whitespace를 수정하지 않았다.
따라서 git diff --check는 source report 원문 4줄을 trailing whitespace로 보고한다.
이 내용은 README와 summary에 운영 메모로 명시했다.
```

### 2.3 보고서 요약

요약 파일:

```text
docs/research/condition_research/summaries/2026-04-19_backtest_analysis_report_v2_summary.md
```

반영한 핵심:

- 권장 시간대: `09:00 ~ 09:30`
- 현재 연구 적용 시간대: `09:00 ~ 09:28`
- 평균 실틱수: `30`
- 매수 후보 변수:
  - 현재가
  - 등락율
  - 거래대금
  - 거래량
  - 호가
  - VI
  - 시가총액
  - 시분초
  - 체결강도
- 매도 후보 변수:
  - 체결강도
  - 이동평균
  - 수익률
  - 최고수익률
  - 매수시간
- wide baseline에서는 거래량/호가/VI 계열을 처음부터 강하게 제한하지 않고 후속 Retention-Aware 개선 후보로 남긴다.

### 2.4 넓은 tick 연구용 조건식 문서화

전략명:

```text
buy:
ResearchTest_Tick_B_090000_092800_Wide_20260419

sell:
ResearchTest_Tick_S_090000_092800_Wide_20260419
```

문서:

```text
docs/research/condition_research/strategy_designs/2026-04-19_tick_research_baseline_condition_design.md
docs/research/condition_research/generated_conditions/2026-04-19_research_test_tick_wide_conditions.md
```

매수 조건식 목적:

```text
수익률 최적화가 아니라 연구 데이터 확보용 거래 수 증가
```

매도 조건식 목적:

```text
거래를 단순하고 일관되게 닫는 기본 청산
```

### 2.5 strategy.db 저장 기록

기록 문서:

```text
docs/research/condition_research/pilot_logs/2026-04-19_research_test_tick_wide_strategy_save.md
```

결과:

```text
validate_buy: ok
validate_sell: ok
save_buy: created
save_sell: created
evaluate_buy: ok
evaluate_sell: ok
```

주의:

```text
strategy.db는 로컬 런타임 DB라 Git에 커밋하지 않았다.
기존 Tick_B_902_905_Update_2 / Tick_S_902_905_Update_2는 덮어쓰지 않았다.
```

### 2.6 직접 백테스트 기록

기록 문서:

```text
docs/research/condition_research/pilot_logs/2026-04-19_research_test_tick_wide_backtest.md
docs/update_log/2026-04-19_tick_research_baseline_condition.md
```

feature worktree CLI에서는 정상 완료하지 못했지만, 사용자가 `STOM_V.wt-dev` 실제 실행 환경에서 동일 조건식을 다시 로딩해 직접 실행한 결과 정상 완료됐다.

## 3. wt-dev 실제 백테스트 결과

실행 조건:

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
거래횟수: 40,937회
일평균거래횟수: 169.9회
적정최대보유종목수: 40개
평균보유기간: 228.19초
익절: 12,289회
손절: 28,648회
승률: 30.02%
평균수익률: -0.68%
수익률합계: -695.09%
수익금합계: -5,564,960,005원
최대낙폭금액: 5,566,752,407원
최대낙폭률: 693.76%
매매성능지수: 0.60
연간예상수익률: -721.05%
백테스트 소요시간: 0:01:00.675279
```

CSV:

```text
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

## 4. 검증 결과

### strategy/subcommand tests

```powershell
python -m pytest tests/unit/test_strategy.py tests/unit/test_subcommands.py -q
```

결과:

```text
67 passed
```

### non-release sync

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

### 최종 리뷰

최종 리뷰 결과:

```text
APPROVED
Blocking/Major issue 없음
```

## 5. 7dd225f 이후 전체 개발 흐름에서의 위치

```text
7dd225f
  백테스트 실행조건 로그 계측
  -> 재현성 기반

e8a75547
  세그먼트 기반 조건식 연구 루프
  -> CSV 분석, 후보 생성, 단일 후보 백테스트 기반

a3f093cc
  research WFO 연결 실험
  -> 후보 검증을 research에 붙이는 시도

a62c9754
  research WFO 제거
  -> 빠른 research / 무거운 promote-WFO 역할 분리

f94ae507
  후보 백테스트 런타임 안정화
  -> timeout, date, cleanup, plan-only

PR #12 / 3cef3749
  Backtest Iteration Research Loop v1
  -> 후보 N개 백테스트, ranking, best_candidate

PR #13 / ce2a2fed
  Candidate Quality Gate / Retention-Aware Selection
  -> estimated_retention 선별, adjusted_score ranking

이번 PR
  Tick Research Baseline Condition
  -> 연구용 wide baseline 조건식과 기준 CSV 확보
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
[8. 반복 개선 루프 v2]
        |
        v
[9. 최종 promote/WFO 검증]
```

현재 완료된 것:

- 외부 우수 전략 보고서 보존
- 보고서 요약
- 연구용 wide tick 조건식 문서화
- strategy.db 저장/검증
- `wt-dev` 실제 백테스트 성공
- 거래 40,937회 기준 CSV 확보

다음 단계:

- Wide v1 CSV를 `discovery research --run-candidates` 입력으로 사용
- Retention-Aware 후보 선별 결과 확인
- 후보 N개 백테스트/랭킹
- best_candidate 및 실패 이유 분석
- 필요 시 Wide2 조건식 설계

## 7. 남은 리스크

- Wide v1은 실전 전략으로는 손실과 낙폭이 매우 크다.
- Wide v1은 연구 baseline이지 live 후보가 아니다.
- feature worktree CLI 실행과 `wt-dev` 실제 실행 환경의 결과가 달랐다.
- 실제 백테스트 판단은 `wt-dev` 기준으로 기록한다.
- 다음 Retention-Aware 개선 후에도 `best_candidate`는 promotion 통과를 의미하지 않는다.
- 최종 채택 전에는 `discovery promote` 또는 WFO 검증이 필요하다.
- 원본 보고서는 hash 동일 보존 때문에 trailing whitespace가 유지된다.

## 8. 다음 단계 안내

다음 실행 명령:

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'

python stom_backtest.py discovery research ResearchWideRetention_20260420 `
  --input C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv `
  --base-buy-strategy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --min-samples 30 `
  --run-candidates `
  --candidate-count 5 `
  --min-estimated-retention 0.4 `
  --candidate-start 20250101 `
  --candidate-end 20251231 `
  --candidate-timeout 900 `
  --cleanup-best-candidate
```

이 명령의 목적:

```text
Wide v1 기준 CSV를 Retention-Aware 후보 개선 루프에 넣고,
후보 N개를 생성/백테스트/랭킹해 다음 best_candidate를 찾는다.
```
