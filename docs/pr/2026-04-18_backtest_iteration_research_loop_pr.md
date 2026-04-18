# Backtest Iteration Research Loop v1 PR 보고서

## 목적

이번 PR은 `discovery research`를 빠른 조건식 연구 루프로 유지하면서, 기존 단일 후보 실행을 확장해 **후보 N개를 한 라운드에서 백테스트하고 순위를 매기는 기능**을 추가한다.

현재까지 완료된 기반은 다음과 같다.

```text
세그먼트 기반 CSV 분석
-> 후보 조건식 생성
-> 단일 후보 전략 저장
-> 단일 후보 백테스트
-> 후보 백테스트 timeout/date/cleanup 안정화
```

이번 PR은 그 다음 단계다.

```text
baseline CSV 분석 1회
-> 후보 조건식 N개 생성
-> 후보별 독립 전략명 생성
-> 후보별 백테스트
-> 후보별 comparison/promotion 평가
-> 후보별 ranking
-> best_candidate 선택
-> failed/loser/best cleanup 정책 적용
-> JSON/Markdown 리포트
```

## 전체 계획에서 현재 위치

전체 자동 조건식 개선 계획을 기준으로 현재 위치는 **“단일 후보 실행 안정화 이후, 다중 후보 1라운드 평가 루프 구현 완료”**다.

```text
완료됨:
1. 백테스트 CSV 분석
2. 후보 조건식 생성
3. 단일 후보 전략 생성/백테스트
4. 단일 후보 런타임 안정화
5. WFO 제거 및 역할 분리
6. 후보 N개 1라운드 백테스트/랭킹

아직 남음:
7. best_candidate 기반 조건식 재생성
8. 다중 라운드 반복 개선
9. 반복 종료 조건
10. 최종 후보 promote/WFO 검증
11. 장기 구간 운영 파일럿
```

이번 PR은 “완전 자동 개선 루프”의 완성은 아니다. 다음 Phase에서 자동 재생성/반복 종료 조건을 붙이기 전, 후보 여러 개를 안전하게 실행하고 비교하는 기반을 만든다.

## WFO 역할

이번 PR은 WFO를 다시 `discovery research`에 넣지 않는다.

역할은 기존 결정대로 유지한다.

```text
discovery research:
  빠른 조건식 연구/후보 재백테스트 루프

discovery promote / cli.wfo / auto_discovery:
  무거운 최종 검증 루프
```

## 주요 변경 사항

### 1. `discovery research --run-candidates`

새 옵션:

```text
--run-candidates
--candidate-count
--candidate-name-prefix
--cleanup-best-candidate
--keep-loser-candidates
```

기존 후보 런타임 옵션은 재사용한다.

```text
--candidate-start
--candidate-end
--candidate-timeout
--keep-failed-candidate
```

충돌 방지:

```text
--run-candidate + --run-candidates => error
--candidate-plan-only + --run-candidates => error
candidate_count < 1 => error
expression 수 < candidate_count => insufficient_expressions
```

### 2. 후보별 독립 전략명

후보 이름은 deterministic하게 생성된다.

```text
{name}__cand001
{name}__cand002
{name}__cand003
```

`--candidate-name-prefix`가 있으면 prefix를 기준으로 만든다.

### 3. 후보별 단일 expression 실행

다중 후보 모드에서는 후보 하나가 expression 하나만 평가한다.

```text
cand001 = expression[0]
cand002 = expression[1]
cand003 = expression[2]
```

이렇게 해야 어떤 조건식이 성과를 개선하거나 악화시켰는지 분리해서 볼 수 있다.

### 4. 후보 ranking

ranking 기준:

```text
1. promotion.passed=True 우선
2. promotion.score 높은 순
3. candidate trade_count 높은 순
4. trade_count_retention 높은 순
5. date_concentration 낮은 순
6. symbol_concentration 낮은 순
7. index 낮은 순
```

`best_candidate`는 “이번 후보 묶음에서 가장 나은 후보”이며, promotion 통과를 의미하지 않는다.

### 5. cleanup 정책

기본 정책:

```text
best 후보: 보존
loser 후보: 삭제
failed 후보: 삭제
```

옵션:

```text
--cleanup-best-candidate:
  best 후보도 삭제

--keep-loser-candidates:
  loser 후보도 보존

--keep-failed-candidate:
  실패 후보도 보존
```

안전 보강:

- 후보 전략이 생성되기 전 실패한 경우 기존 strategy를 삭제하지 않도록 `candidate_not_created`로 보존한다.
- `candidate_name_conflict` 같은 저장 전 실패가 기존 전략 삭제로 이어지지 않도록 막았다.
- cleanup summary는 `attempted_count`, `deleted_count`, `kept_count`, `failed_count`, `items` 계약을 따른다.

### 6. 리포트 확장

`build_research_report()`와 Markdown 렌더링에 다음 필드를 추가했다.

```text
phase
iteration_plan
candidates
best_candidate
cleanup_summary
```

Markdown 섹션:

```text
## Candidate Iteration
## Candidate Ranking
## Cleanup Summary
```

## 변경 파일

```text
cli/ai_controller.py
cli/research_loop.py
cli/research_report.py
cli/subcommands.py
tests/unit/test_ai_controller.py
tests/unit/test_research_loop.py
tests/unit/test_research_report.py
tests/unit/test_subcommands.py
docs/update_log/2026-04-18_backtest_iteration_research_loop.md
```

## 검증 결과

### focused regression

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py tests/unit/test_ai_controller.py -q
```

결과:

```text
154 passed
```

### full unit

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
962 passed, 1 skipped, 10 warnings
```

### non-release sync

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

### 실제 파일럿

feature worktree의 ignored `_database`를 실제 검증 데이터로 맞춘 뒤 실행했다.

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py discovery research AutoResearchIterationPilot_20260418_T6R5 `
  --input C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidates `
  --candidate-count 3 `
  --candidate-start 20250407 `
  --candidate-end 20250418 `
  --candidate-timeout 180 `
  --cleanup-best-candidate
```

결과:

```text
return_code: 0
status: ok
phase: candidates_evaluated
candidates_count: 3
best_candidate: AutoResearchIterationPilot_20260418_T6R5__cand001
best_expression: 시가총액 <= 2793.5
best_promotion_passed: False
best_score: 16123.392637215471
cleanup_summary: attempted_count=3, deleted_count=3, kept_count=0, failed_count=0
```

후보별 결과:

```text
rank 1: cand001, trade_count=109, cleanup=best_candidate_deleted/deleted
rank 2: cand002, trade_count=413, cleanup=loser_candidate_deleted/deleted
rank 3: cand003, trade_count=469, cleanup=loser_candidate_deleted/deleted
```

전략 잔여 확인:

```text
AutoResearchIterationPilot_20260418_T6R5__cand001 0
AutoResearchIterationPilot_20260418_T6R5__cand002 0
AutoResearchIterationPilot_20260418_T6R5__cand003 0
```

## 코드 리뷰

최종 코드 리뷰 결과:

```text
APPROVED
blocking/major issue 없음
```

최종 리뷰에서 지적된 두 가지는 수정 완료했다.

```text
1. run_candidate + run_candidates explicit conflict가 public controller에서 무시되던 문제
2. expression 수가 candidate_count보다 부족할 때 partial 실행되던 문제
```

## 남은 리스크

- `best_candidate`는 promotion 통과 후보가 아닐 수 있다.
- 이번 파일럿의 best 후보도 `promotion_passed=False`다.
- 따라서 이번 PR은 실전 채택이 아니라 다중 후보 평가 기반 완성으로 해석해야 한다.
- 최종 채택 전에는 `discovery promote` 또는 별도 WFO 검증이 필요하다.
- 실제 파일럿은 ignored `_database`와 기준 CSV 준비에 의존한다.
- 장기간 후보 N개 품질 검증은 아직 수행하지 않았다.
- 다음 Phase인 다중 라운드 자동 재생성은 아직 구현하지 않았다.

## 다음 단계

이번 PR이 merge되면 다음 개발은 다음 중 하나다.

```text
1. Backtest Iteration Improvement Loop v2
   best_candidate 기반 조건식 재생성
   다중 라운드 반복
   개선 없음/stagnation 종료 조건

2. 후보 품질 파일럿
   candidate_count와 기간을 늘려 장기 구간 후보 품질 확인
   promotion gate 조정 필요성 검토
```

권장 순서는 2번 파일럿을 짧게 한 뒤 1번 설계로 들어가는 것이다.
