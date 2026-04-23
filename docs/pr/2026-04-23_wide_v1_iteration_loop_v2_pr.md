# Wide v1 후보 결과 분석 및 반복 개선 루프 v2 PR 보고서

## 1. 이번 PR의 목적

이번 PR은 PR #18에서 확보한 Wide v1 후보 5개 실행 결과를 바탕으로, best candidate인 `WideV1RetentionCand5_20260422__cand003` 중심의 반복 개선 루프 v2를 구현하고 실행한 결과를 문서화한다.

핵심 목적:

```text
1. cand003 중심 후보 생성 규칙 구현
2. 후보 5개 전체의 공통/차이 feature를 반영한 v2 후보군 생성
3. discovery research CLI에서 v2 모드 실행 가능하게 연결
4. v2 candidate_count=5 full-year 실행 결과 기록
5. v2 결과가 기존 cand003보다 개선됐는지 PASS/HOLD/FAIL로 판정
```

이번 PR은 최종 채택, WFO, promote 작업이 아니다. v2 후보 생성/실행 경로를 검증하고, 다음 분석 단계로 넘어갈 근거를 만드는 PR이다.

## 2. 전체 흐름과 현재 위치

```text
[0. 기준 전략 / 기준 CSV]
        |
        v
[1. Wide v1 CLI baseline = GUI 결과 일치]
        |
        v
[2. Retention-Aware candidate_count=5 실행]
        |
        v
[3. best_candidate=cand003 확인]
        |
        v
[4. 이번 PR: 반복 개선 루프 v2 구현/실행]
        |
        v
[5. 다음: row-level 후보 차이 분석]
        |
        v
[6. 이후: candidate_count=10 확장 또는 v3]
        |
        v
[7. 최종 promote/WFO 검증]
```

## 3. 이번 PR의 변경 사항

### 3.1 v2 후보 생성 helper 추가

추가 파일:

```text
cli/research_iteration_v2.py
tests/unit/test_research_iteration_v2.py
```

역할:

```text
candidate_signature()
filter_duplicate_v2_candidates()
candidate_from_expression()
build_v2_candidate_pool()
```

주요 정책:

```text
primary_feature=B_시가총액
best_expression=66.999 <= 시가총액 < 2_580
secondary_features=B_체결강도,B_등락율,B_당일거래대금,B_시분초
mode=best_feature_mix
```

리뷰 중 보강한 사항:

```text
threshold 후보가 잘못 중복 제거되지 않도록 candidate_signature에 threshold 포함
secondary_features list alias 방지
best_candidate 이름만이 아니라 best_expression을 명시적으로 받아 seed로 사용
```

### 3.2 research_loop v2 wiring

변경 파일:

```text
cli/research_loop.py
tests/unit/test_research_loop.py
```

추가된 `ResearchLoopConfig` 필드:

```python
iteration_v2_mode: str = ''
iteration_v2_best_candidate: str = ''
iteration_v2_best_expression: str = ''
iteration_v2_primary_feature: str = 'B_시가총액'
iteration_v2_secondary_features: str = ''
iteration_v2_include_secondary_only: bool = True
iteration_v2_max_secondary_only: int = 1
iteration_v2_duplicate_retention_tolerance: float = 0.02
```

동작:

```text
iteration_v2_mode가 비어 있으면 기존 run_candidates 동작 유지
iteration_v2_mode=best_feature_mix일 때만 v2 후보 pool 적용
v2 후보 pool은 retention annotation 전에 적용
```

### 3.3 CLI 옵션 및 report 추가

변경 파일:

```text
cli/subcommands.py
cli/research_report.py
tests/unit/test_subcommands.py
tests/unit/test_research_report.py
```

추가 CLI 옵션:

```text
--iteration-v2-mode
--iteration-v2-best-candidate
--iteration-v2-best-expression
--iteration-v2-primary-feature
--iteration-v2-secondary-features
--no-iteration-v2-secondary-only
--iteration-v2-max-secondary-only
--iteration-v2-duplicate-retention-tolerance
```

리포트:

```text
## Iteration Loop v2 Candidate Generation
```

주의:

```text
v2 옵션을 켜지 않은 기본 run_candidates report에는 v2 섹션을 출력하지 않음
```

### 3.4 v2 실행 결과 문서화

추가 문서:

```text
docs/superpowers/specs/2026-04-23-wide-v1-candidate-result-analysis-and-iteration-loop-v2-design.md
docs/superpowers/plans/2026-04-23-wide-v1-candidate-result-analysis-and-iteration-loop-v2.md
docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v2.md
docs/update_log/2026-04-23_wide_v1_iteration_loop_v2.md
```

## 4. v2 실행 조건

```text
baseline_csv=C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv
base_buy_strategy=WideV1RetentionCand5_20260422__cand003
sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
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
iteration_v2_mode=best_feature_mix
iteration_v2_best_candidate=WideV1RetentionCand5_20260422__cand003
iteration_v2_best_expression=66.999 <= 시가총액 < 2_580
iteration_v2_primary_feature=B_시가총액
iteration_v2_secondary_features=B_체결강도,B_등락율,B_당일거래대금,B_시분초
```

runtime DB:

```text
STOM_CLI_DATABASE_DIR=C:\System_Trading\STOM\STOM_V.wt-dev\_database
```

운영 정책:

```text
STOM_V.wt-dev라는 폴더명에 의미적으로 의존하지 않음
실제 운용 _database 경로를 STOM_CLI_DATABASE_DIR로 지정
운용 폴더명이 바뀌면 env 값만 새 _database 경로로 변경
```

## 5. v2 실행 결과

```text
status=ok
phase=candidates_evaluated
candidate_count_observed=5
best_candidate=WideV1IterationV2_20260423__cand005
best_adjusted_score=2554.7109523820864
baseline_adjusted_score=10943.034141541459
best_trade_count=36096
best_trade_count_retention=0.9777344384852917
promotion_passed=True
cleanup_failed_count=0
decision=HOLD
```

후보별 결과:

```text
rank=1
strategy_name=WideV1IterationV2_20260423__cand005
expression=66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4
trade_count=36096
trade_count_retention=0.9777344384852917
promotion_passed=True
adjusted_score=2554.7109523820864

rank=2
strategy_name=WideV1IterationV2_20260423__cand004
expression=66.999 <= 시가총액 < 2_580 and 178.999 <= 당일거래대금 < 1805.7
trade_count=36311
trade_count_retention=0.9835581559131047
promotion_passed=True
adjusted_score=2086.5774701825367

rank=3
strategy_name=WideV1IterationV2_20260423__cand001
expression=66.999 <= 시가총액 < 2_580 and 0.039 <= 체결강도 < 54.89
trade_count=36364
trade_count_retention=0.9849937699767052
promotion_passed=True
adjusted_score=1987.2564590451425
```

## 6. 판정

```text
decision=HOLD
reason=v2 executed but did not improve over cand003 baseline or needs row-level analysis.
```

해석:

```text
v2 candidate_count=5 실행 자체는 성공
후보 5개 모두 full-year 백테스트와 promotion gate 통과
하지만 기존 cand003 adjusted_score=10943.034141541459를 넘지 못함
따라서 candidate_count=10 확장으로 바로 가지 않음
```

## 7. 검증 결과

```text
focused tests:
  python -m pytest tests/unit/test_research_iteration_v2.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py -q
  result=151 passed

full unit tests:
  python -m pytest tests/unit/ -q
  result=1069 passed, 1 skipped, 10 warnings

sync guard:
  python scripts/verify_nonrelease_sync.py
  result=PASS

diff check:
  git diff --check
  result=PASS

final review:
  Critical/Important issues=0
```

## 8. 남은 리스크

- v2 후보가 모두 실행됐지만 기존 best보다 score가 낮다.
- scalar score만으로는 왜 v2가 개선 실패했는지 충분히 설명하기 어렵다.
- 다음 단계는 row-level CSV 비교다.
- v2 실행 명령의 한글 feature 인자가 runtime JSON에서 mojibake로 보인다.
- best_candidate는 최종 채택이 아니며 promote/WFO 검증이 필요하다.

## 9. 다음 단계 안내

PR merge 후 다음 superpower 명령:

```text
$brainstorming Wide v1 row-level 후보 차이 분석 설계
```

다음 설계에서 결정할 것:

```text
1. 기존 cand003과 v2 best cand005의 거래 단위 차이 분석
2. cand003이 유지/제거한 거래와 cand005가 추가로 제거한 거래 비교
3. adjusted_score 하락 원인 분석
4. 시가총액 + 당일거래대금 조합이 왜 cand003보다 낮은지 확인
5. v3 또는 candidate_count=10 확장 전에 필요한 조건 정의
```

## 10. PR 본문 요약

```markdown
## Summary
- cand003 중심 반복 개선 루프 v2 후보 생성 helper와 research loop 연결을 추가했습니다.
- discovery research CLI에 iteration-v2 옵션과 리포트 섹션을 추가했습니다.
- v2 candidate_count=5를 실행했고, 실행은 성공했지만 기존 cand003보다 개선하지 못해 HOLD로 판정했습니다.

## Test Plan
- python -m pytest tests/unit/ -q
- python scripts/verify_nonrelease_sync.py
- git diff --check
- runtime-preflight
- discovery research iteration-v2 candidate_count=5

## Remaining Risk
- v2 결과가 기존 cand003보다 낮아 row-level 차이 분석이 필요합니다.
- WFO/promote는 아직 실행하지 않았습니다.
```
