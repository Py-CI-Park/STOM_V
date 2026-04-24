# Wide v1 v3 결과 분석 및 v4 여부 판단 PR 보고서

## 1. 이번 PR의 목적

이번 PR의 목적은 PR #22 이후 `WideV1IterationV3_20260423` runtime 결과를 재현 가능한 방식으로 분석하고, v4 후보 생성으로 바로 넘어갈지 여부를 판정하는 것이다.

핵심 목적:

```text
1. v3 runtime JSON을 인코딩 차이와 무관하게 로드
2. cand005 control reference score를 wide baseline 기준으로 재계산
3. top 후보 tie 상태를 rank metric 기준으로 분류
4. v3 후보 family가 retention/selection/execution 단계에서 어떻게 남았는지 분석
5. 다음 superpower 명령을 보고서에 명시
```

이번 PR은 v4 후보 생성, promote, WFO, `strategy.db` 변경을 수행하지 않는다. 현재 결과가 바로 실전 채택 근거인지 판단하지 않고, 다음 연구 분기를 안전하게 결정하는 gate를 추가하는 PR이다.

## 2. 전체 개발 흐름과 현재 위치

```text
[0. Wide baseline CSV]
        |
        v
[1. Retention-Aware candidate_count=5]
        |
        v
[2. best_candidate=cand003]
        |
        v
[3. Iteration Loop v2: cand003 -> cand005]
        |
        v
[4. score baseline comparability 보강]
        |
        v
[5. v3 후보 생성 규칙 구현 + candidate_count=10 실행]
        |
        v
[6. 이번 PR: v3 결과 분석 및 v4 여부 판단]
        |
        v
[7. 다음: v3 tie-break 및 ranking 보강 설계]
        |
        v
[8. v4 후보 생성 또는 selection 조정]
        |
        v
[9. 최종 promote/WFO 검증]
```

현재 단계는 `[6. v3 결과 분석 및 v4 여부 판단]`이다. v3 실행은 성공했지만 top 10 후보가 같은 rank metric으로 묶였고, selected/executed family가 `v3_tighten_secondary`에 치우쳐 있다. 따라서 v4로 바로 진행하기보다 tie-break와 ranking 기준을 먼저 보강하는 것이 맞다.

## 3. 현재 계획

현재 완료:

```text
- v3 결과 분석 spec 작성
- v3 결과 분석 구현 계획 작성
- 순수 helper `cli/research_v3_decision.py` 추가
- CLI 분석 wrapper `scripts/analyze_wide_v1_v3_decision.py` 추가
- 실제 runtime/CSV 기반 분석 보고서 생성
- full unit test, ruff, sync guard, diff check 검증
- 최종 코드 리뷰 승인
```

현재 판단:

```text
decision=HOLD_V3_TIE_REVIEW
next_command=$brainstorming Wide v1 v3 tie-break 및 ranking 보강 설계
control_status=ok
stored_control_score_status=missing
recomputed_reference_adjusted_score=13497.662902097409
tie_status=rank_metric_tie
tie_candidate_count=10
row_set_identity_status=not_evaluated
selected_family=v3_tighten_secondary only
```

다음 계획:

```text
1. tie-break 기준 설계
2. rank metric이 같을 때 row-set identity 또는 secondary diagnostics를 붙일지 결정
3. repair/replace 후보가 retention pass 후 selection에서 탈락한 이유 검토
4. ranking 보강 후 v4 후보 생성 또는 selection 조정 계획 작성
5. 그 전까지 promote/WFO는 보류
```

## 4. 이번 PR의 변경 사항

변경 파일:

```text
docs/superpowers/specs/2026-04-24-wide-v1-v3-result-analysis-and-v4-decision-design.md
docs/superpowers/plans/2026-04-24-wide-v1-v3-result-analysis-and-v4-decision.md
cli/research_v3_decision.py
scripts/analyze_wide_v1_v3_decision.py
tests/unit/test_research_v3_decision.py
docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md
docs/pr/2026-04-24_wide_v1_v3_result_analysis_and_v4_decision_pr.md
```

핵심 구현:

```text
1. Control Score Gate:
   - runtime에 저장된 control score가 missing이어도 CSV 기준 재계산이 가능하면 ok로 판정
   - 저장값과 재계산값이 다르면 RECHECK_CONTROL로 보수적 차단

2. Tie Gate:
   - runtime rank를 먼저 반영해 top 후보군을 정렬
   - 최고점 cohort 안의 score/rank metric tie를 분리
   - row-set 동일성은 계산하지 않았으므로 not_evaluated로 명시

3. Candidate Family Gate:
   - pool, retention observed, retention pass, fallback, selected, executed 분포를 분리
   - repair/replace는 retention pass only, tighten은 selected/executed로 요약

4. Decision Routing:
   - control 실패는 RECHECK_CONTROL
   - score/rank metric tie는 HOLD_V3_TIE_REVIEW
   - gate가 모두 통과할 때만 PROCEED_TO_V4_PLAN
```

## 5. 실제 분석 결과

분석 대상:

```text
runtime_path=C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json
wide_reference_csv=C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
control_csv=C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv
```

판정:

```text
decision=HOLD_V3_TIE_REVIEW
next_command=$brainstorming Wide v1 v3 tie-break 및 ranking 보강 설계
```

Control Score Gate:

```text
status=ok
stored_reference_adjusted_score=None
recomputed_reference_adjusted_score=13497.662902097409
reference_adjusted_score=13497.662902097409
stored_score_status=missing
score_match=None
```

Tie Gate:

```text
status=rank_metric_tie
score_tie=True
metric_tie=True
row_set_identity_status=not_evaluated
top_count=10
tie_candidate_count=10
```

Candidate Family Gate:

```text
pool:
  v3_repair_trade_amount=3
  v3_replace_secondary=15
  v3_tighten_secondary=15
  v3_control_keep_best=1

retention_pass:
  v3_repair_trade_amount=3
  v3_replace_secondary=15
  v3_tighten_secondary=15

selected/executed:
  v3_tighten_secondary=10

summary:
  v3_repair_trade_amount=retention-pass only
  v3_replace_secondary=retention-pass only
  v3_tighten_secondary=selected/executed
```

해석:

```text
- control score는 runtime 저장값이 없었지만, wide baseline 기준 재계산은 성공했다.
- top 10 후보는 rank metric상 동일하므로 cand001 단독 우위로 해석하면 안 된다.
- repair/replace family는 생성과 retention pass까지는 남았지만 최종 selected/executed에 반영되지 않았다.
- 따라서 v4 후보 생성보다 tie-break 및 ranking 보강이 먼저다.
```

## 6. 검증 결과

```text
focused tests:
  python -m pytest tests/unit/test_research_v3_decision.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py -q
  result=51 passed

full unit tests:
  python -m pytest tests/unit/ -q
  result=1126 passed, 1 skipped, 10 warnings

ruff:
  python -m ruff check cli/research_v3_decision.py scripts/analyze_wide_v1_v3_decision.py tests/unit/test_research_v3_decision.py
  result=All checks passed

sync guard:
  python scripts/verify_nonrelease_sync.py
  result=PASS

analysis script:
  python scripts/analyze_wide_v1_v3_decision.py
  result=decision=HOLD_V3_TIE_REVIEW

diff check:
  git diff --check
  result=PASS

code review:
  final review result=APPROVED
```

## 7. 남은 리스크

- row-set identity는 아직 계산하지 않았고, 보고서에도 `not_evaluated`로 명시했다.
- rank metric tie가 완전히 같은 후보들의 실제 거래 row 차이는 다음 단계에서 추가 분석이 필요하다.
- repair/replace family가 selection에서 빠진 이유는 selection/ranking 보강 단계에서 확인해야 한다.
- 이번 PR은 promote/WFO를 수행하지 않는다.

## 8. 다음 단계 안내

이번 PR merge 후 다음 명령은 아래가 맞다.

```text
$brainstorming Wide v1 v3 tie-break 및 ranking 보강 설계
```

다음 단계에서 다룰 것:

```text
1. top tie 후보들의 row-set identity를 계산할지 결정
2. 같은 rank metric일 때 사용할 tie-break 기준 확정
3. family 다양성을 selection에 반영할지 검토
4. v4 후보 생성으로 넘어가기 전 gate를 다시 정의
```

## 9. PR 본문 요약

```markdown
## Summary
- Wide v1 v3 runtime 결과를 재분석하는 helper와 CLI wrapper를 추가했습니다.
- cand005 control score를 wide baseline 기준으로 재계산하고, top 10 rank metric tie와 family selection 편향을 문서화했습니다.
- 최종 판정은 `HOLD_V3_TIE_REVIEW`이며, 다음 단계는 v4 후보 생성이 아니라 tie-break/ranking 보강입니다.

## Test Plan
- python -m pytest tests/unit/test_research_v3_decision.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py -q
- python -m pytest tests/unit/ -q
- python -m ruff check cli/research_v3_decision.py scripts/analyze_wide_v1_v3_decision.py tests/unit/test_research_v3_decision.py
- python scripts/verify_nonrelease_sync.py
- python scripts/analyze_wide_v1_v3_decision.py
- git diff --check

## Remaining Risk
- row-set identity는 아직 계산하지 않았고 `not_evaluated`로 남겨두었습니다.
- rank metric tie와 family selection 편향 때문에 promote/WFO는 아직 진행하지 않습니다.
```
