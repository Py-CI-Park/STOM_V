# Wide v1 v3 후보 생성 규칙 PR 보고서

## 1. 이번 PR의 목적

이번 PR의 목적은 PR #21 이후 `WideV1IterationV2_20260423__cand005`를 새 reference best로 삼아 `best_feature_mix_v3` 후보 생성 규칙을 구현하고, 실제 `candidate_count=10` runtime 결과까지 기록하는 것이다.

핵심 목적:

```text
1. cand005 기준의 v3 후보 생성 helper 추가
2. discovery research loop에 best_feature_mix_v3 연결
3. CLI parser와 report가 v3 metadata를 처리하게 보강
4. malformed v3 제어식과 optional control reference score 경로를 안전하게 보완
5. candidate_count=10 full-year runtime 결과를 문서화
```

이번 PR은 최종 실전 채택, promote, WFO 작업이 아니다. v3 후보 생성과 실행 근거를 고정하고, 다음 분석 단계로 넘어갈 수 있는 상태를 만드는 PR이다.

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
[5. 이번 PR: v3 후보 생성 규칙 구현 + candidate_count=10 실행]
        |
        v
[6. 다음: v3 결과 분석 / v4 여부 판단]
        |
        v
[7. 최종 promote/WFO 검증]
```

현재 단계는 `[5. v3 후보 생성 규칙 구현 + candidate_count=10 실행]`이다. 자동 조건식 연구 방향은 유지되고, 이번 단계의 산출물은 “v3가 실행되며 무엇이 나왔는가”를 확정하는 데 있다.

## 3. 현재 계획

현재 계획은 아래와 같이 정리된다.

```text
현재 완료:
  - best_feature_mix_v3 helper 구현
  - research loop / CLI / report 연결
  - malformed v3 제어식 검증 보강
  - optional control reference score 경로를 graceful degradation으로 보강
  - candidate_count=10 runtime 실행 및 pilot/update/pr 문서화

현재 판단:
  - runtime status=ok
  - top 10 후보가 모두 같은 reference score로 tie
  - control_reference_adjusted_score는 runtime artifact에서 null
  - 계획 규칙 적용 결과 derived_decision=PASS_TO_V3_EXECUTION_RESULT_ANALYSIS

다음 계획:
  - v3 결과 분석 및 v4 여부 판단 설계
  - tie 상태 해석과 candidate rule 재검토
  - 필요하면 tie-break 기준 또는 후보 생성 규칙 추가 조정
```

## 4. 이번 PR의 변경 사항

변경 파일:

```text
cli/research_iteration_v3.py
cli/research_loop.py
cli/subcommands.py
cli/research_report.py
tests/unit/test_research_iteration_v3.py
tests/unit/test_research_loop.py
tests/unit/test_subcommands.py
tests/unit/test_research_report.py
docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md
docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v3.md
docs/pr/2026-04-23_wide_v1_v3_candidate_generation_rules_pr.md
```

핵심 구현:

```text
1. v3 helper:
   - best expression 2조건 parsing
   - v3_tighten_secondary / v3_repair_trade_amount / v3_replace_secondary 후보군 생성
   - v3_control_keep_best metadata 유지

2. research loop:
   - iteration_v2_mode=best_feature_mix_v3 허용
   - iteration_v3 metadata 반환
   - malformed v3 제어식을 validation 단계에서 차단
   - optional control reference score 경로를 safe helper로 분리

3. CLI:
   - discovery research parser가 best_feature_mix_v3 값을 받도록 보강

4. report:
   - Iteration Loop v3 Candidate Generation 섹션 추가
   - control metadata와 type counts 출력

5. follow-up fixes:
   - standalone retention prefilter 제거
   - baseline/reference CSV로 control reference score를 가능한 경우 채움
   - malformed reference input 시 control score는 None으로 degrade
```

## 5. runtime 실행 결과

```text
status=ok
phase=candidates_evaluated
candidate_count_observed=10
best_candidate=WideV1IterationV3_20260423__cand001
best_reference_adjusted_score=13497.662902097409
best_trade_count=36096.0
best_trade_count_retention=0.8817451205510907
control_candidate=WideV1IterationV2_20260423__cand005
control_reference_adjusted_score=null
derived_decision=PASS_TO_V3_EXECUTION_RESULT_ANALYSIS
cleanup_deleted_count=9
cleanup_kept_count=1
```

해석:

```text
- runtime JSON 자체가 decision field를 낸 것은 아니다.
- 계획서 규칙을 observed JSON에 적용하면 PASS branch로 간다.
- 단, control score가 null이므로 이것은 "cand001이 control을 이겼다"는 뜻이 아니다.
- 실제 의미는 HOLD gate가 발동하지 않았다는 정도로만 해석해야 한다.
```

후보 분포:

```json
{
  "v3_repair_trade_amount": 3,
  "v3_replace_secondary": 15,
  "v3_tighten_secondary": 15,
  "v3_control_keep_best": 1
}
```

관찰된 편차:

```text
1. 계획서의 `python -m cli.main ...`은 이 worktree에서 `No module named cli.main`으로 실패했다.
2. 실제 실행은 `python .\stom_backtest.py ...`로 같은 인자를 사용했다.
3. runtime JSON은 Tee-Object 영향으로 UTF-16 LE BOM 인코딩으로 기록됐다.
4. observed JSON의 한국어 feature/expression metadata는 mojibake 상태였다.
5. top 10 후보가 모두 같은 reference score로 tie였고, artifact는 명시적 tie-break key를 노출하지 않는다.
6. observed result에서는 `cand001`이 first-ranked/generated tied entry로 유지됐다.
```

## 6. 검증 결과

```text
focused tests:
  python -m pytest tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py -q
  result=165 passed

full unit tests:
  python -m pytest tests/unit/ -q
  result=1100 passed, 1 skipped, 10 warnings

ruff:
  python -m ruff check cli/research_iteration_v3.py cli/research_loop.py cli/subcommands.py cli/research_report.py tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py
  result=All checks passed

sync guard:
  python scripts/verify_nonrelease_sync.py
  result=PASS

syntax:
  python -m py_compile cli/research_iteration_v3.py cli/research_loop.py cli/subcommands.py cli/research_report.py tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py
  result=PASS

runtime:
  python .\stom_backtest.py discovery research WideV1IterationV3_20260423 ... --run-candidates --candidate-count 10
  result=status=ok, phase=candidates_evaluated

diff check:
  git diff --check d23c6bd4 173b7e11
  result=PASS
```

## 7. 남은 리스크

- recorded runtime는 `python -m cli.main ...`이 아니라 `python .\stom_backtest.py ...` entrypoint 기준이다.
- runtime artifact 기준 `control_reference_adjusted_score=null`이라 non-null control score를 두고 직접 비교한 결과는 아직 문서화되지 않았다.
- top 10 tie 상태라서 실제 채택 전에는 candidate rule review 또는 tie-break 기준 검토가 필요하다.
- promote/WFO 검증은 아직 수행하지 않았다.

## 8. 다음 단계 안내

이번 PR merge 후 다음 명령은 아래가 맞다.

```text
$brainstorming Wide v1 v3 결과 분석 및 v4 여부 판단 설계
```

다음 단계에서 다룰 것:

```text
1. top 10 tie 상태를 어떻게 해석할지
2. cand001 유지가 의미 있는지, 아니면 tie-break 기준이 필요한지
3. v3 candidate rule을 유지할지, v4에서 repair/replace 비중을 재조정할지
4. control score null 상태를 어떻게 재검증할지
5. promote/WFO 전 추가 gate가 필요한지
```

## 9. PR 본문 요약

```markdown
## Summary
- `best_feature_mix_v3` 후보 생성 helper와 research loop / CLI / report 연결을 추가했습니다.
- malformed v3 제어식과 optional control reference score 경로를 안전하게 보강했습니다.
- `candidate_count=10` full-year runtime 결과를 문서화했고, observed JSON 기준 `derived_decision=PASS_TO_V3_EXECUTION_RESULT_ANALYSIS`까지 기록했습니다.

## Test Plan
- python -m pytest tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py -q
- python -m pytest tests/unit/ -q
- python -m ruff check cli/research_iteration_v3.py cli/research_loop.py cli/subcommands.py cli/research_report.py tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py
- python scripts/verify_nonrelease_sync.py
- python .\stom_backtest.py discovery research WideV1IterationV3_20260423 ... --run-candidates --candidate-count 10
- git diff --check d23c6bd4 173b7e11

## Remaining Risk
- runtime artifact는 top 10 tie와 `control_reference_adjusted_score=null`을 보여주며, PASS는 plan-rule-derived branch일 뿐 control 초과를 증명하지 않습니다.
- `python -m cli.main ...` entrypoint는 이 worktree에서 검증되지 않았고, 실제 실행은 `python .\stom_backtest.py ...` 기준입니다.
- promote/WFO는 아직 수행하지 않았습니다.
```
