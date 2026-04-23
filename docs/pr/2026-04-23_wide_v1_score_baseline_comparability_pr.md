# Wide v1 Score Baseline Comparability PR 보고서

## 1. 이번 PR의 목적

이번 PR의 목적은 Wide v1 반복 개선 루프에서 서로 다른 baseline의 `adjusted_score`를 직접 비교하던 문제를 수정하는 것이다.

기존에는 다음 두 값을 직접 비교했다.

```text
wide -> cand003 adjusted_score = 10943.034141541459
cand003 -> cand005 adjusted_score = 2554.7109523820864
```

하지만 이는 비교 기준이 다르다.

```text
10943.0341 = wide baseline 대비 cand003의 누적 개선 점수
2554.7109  = cand003 대비 cand005의 추가 개선 점수
```

따라서 이번 PR은 `score_reference_csv`를 도입해 후보를 같은 root baseline 기준으로 재평가하고, report/ranking에도 그 차이를 명시적으로 반영한다.

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
[4. Row-level diff PR #20]
        |
        v
[5. 이번 PR: score baseline comparability 보강]
        |
        v
[6. 다음: v3 후보 생성 규칙 설계]
        |
        v
[7. 최종 promote/WFO 검증]
```

현재 단계는 `[5. score baseline comparability 보강]`이다. 자동 조건식 연구 방향은 유지되며, 이번 PR은 비교 기준을 바로잡아 다음 후보 생성 판단을 올바른 근거 위에 올리는 작업이다.

## 3. 이번 PR의 변경 사항

변경 파일:

```text
cli/research_loop.py
cli/subcommands.py
cli/research_report.py
cli/research_rowdiff.py
tests/unit/test_research_loop.py
tests/unit/test_subcommands.py
tests/unit/test_research_report.py
tests/unit/test_research_rowdiff.py
docs/superpowers/specs/2026-04-23-wide-v1-score-baseline-comparability-design.md
docs/superpowers/plans/2026-04-23-wide-v1-score-baseline-comparability.md
docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_score_baseline_reassessment.md
docs/update_log/2026-04-23_wide_v1_score_baseline_comparability.md
docs/pr/2026-04-23_wide_v1_score_baseline_comparability_pr.md
```

핵심 구현:

```text
1. discovery research CLI에 --score-reference-csv 추가
2. ResearchLoopConfig에 score_reference_csv 추가
3. 후보 실행 시 reference_comparison/reference_promotion 계산
4. rank_score가 reference score를 우선 사용하도록 보강
5. report에 Score Baseline Comparability 섹션 추가
6. rowdiff에 key diagnostics 추가
7. 기존 cand003/cand005 결과를 같은 wide 기준으로 재평가한 문서 추가
```

## 4. 핵심 재평가 결과

```text
wide_to_cand003.adjusted_score=10943.034141541459
cand003_to_cand005.incremental_adjusted_score=2554.7109523820864
wide_to_cand005.reference_adjusted_score=13497.662902097409
```

해석:

```text
cand005는 cand003보다 낮은 점수로 실패한 것이 아니다.
같은 wide baseline 기준으로 비교하면 cand005가 cand003보다 더 높은 reference adjusted_score를 가진다.
즉, 기존 HOLD의 핵심 원인은 v2 악화가 아니라 baseline 비교 기준 혼선이었다.
```

## 5. 검증 결과

```text
focused tests:
  python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_research_rowdiff.py tests/unit/test_subcommands.py -q
  result=157 passed

full unit tests:
  python -m pytest tests/unit/ -q
  result=1083 passed, 1 skipped, 10 warnings

ruff:
  python -m ruff check cli/research_loop.py cli/research_report.py cli/research_rowdiff.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_research_rowdiff.py tests/unit/test_subcommands.py
  result=All checks passed

sync guard:
  python scripts/verify_nonrelease_sync.py
  result=PASS

diff check:
  git diff --check
  result=PASS

score reassessment script:
  result=wide_to_cand005 reference_adjusted_score > wide_to_cand003 adjusted_score
```

## 6. 남은 리스크

- `reference_adjusted_score`가 더 높다고 해서 최종 실전 채택을 의미하지는 않는다.
- 현재 전략 자체는 여전히 손실 전략이다. 이번 PR은 수익 전략 완성이 아니라 연구 루프의 비교 기준 정합성을 보강하는 단계다.
- `score_reference_csv`가 잘못 지정되면 ranking이 다시 왜곡될 수 있다.
- 최종 채택 전에는 promote/WFO 검증이 여전히 필요하다.

## 7. 다음 단계 안내

이번 PR merge 후 다음 명령은 아래가 맞다.

```text
$brainstorming Wide v1 v3 후보 생성 규칙 설계
```

다음 단계에서 다룰 것:

```text
1. cand005를 새로운 reference best로 둘지 확정
2. v3 후보를 cand005 중심으로 생성할지, wide baseline과 함께 2중 기준으로 생성할지 결정
3. candidate_count=10 확장 필요 여부 검토
4. 최종 promote/WFO 전까지의 반복 개선 기준 재정리
```

## 8. PR 본문 요약

```markdown
## Summary
- discovery research에 `--score-reference-csv`를 추가하고, 후보별 reference_comparison/reference_promotion을 계산하도록 보강했습니다.
- ranking과 report가 incremental score와 reference score를 구분하도록 수정했습니다.
- 기존 cand003/cand005 결과를 같은 wide baseline 기준으로 재평가한 결과, cand005가 cand003보다 더 높은 reference adjusted score를 기록했습니다.

## Test Plan
- python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_research_rowdiff.py tests/unit/test_subcommands.py -q
- python -m pytest tests/unit/ -q
- python -m ruff check cli/research_loop.py cli/research_report.py cli/research_rowdiff.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_research_rowdiff.py tests/unit/test_subcommands.py
- python scripts/verify_nonrelease_sync.py
- git diff --check
- score reassessment script

## Remaining Risk
- reference score는 최종 채택 판단이 아니라 같은 baseline 비교 기준 정합성 보강이다.
- score_reference_csv가 잘못 지정되면 ranking이 왜곡될 수 있다.
- 최종 채택 전 promote/WFO가 필요하다.
```
