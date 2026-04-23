# Wide v1 v3 후보 생성 규칙 PR 보고서

## Summary

- `best_feature_mix_v3` 후보 생성 규칙과 `candidate_count=10` runtime 결과를 실제 작업 트리에서 기록했다.
- observed runtime JSON 기준 best candidate는 `WideV1IterationV3_20260423__cand001`이고 `reference_adjusted_score=13497.662902097409`다.
- 계획서의 decision rule을 그대로 적용하면 `status=ok`이고 `control_reference_adjusted_score`가 비어 있어 `derived_decision=PASS_TO_V3_EXECUTION_RESULT_ANALYSIS`로 분기된다. 이 PASS는 HOLD gate 미발동을 뜻할 뿐 control 초과를 증명하지 않는다.

## Result

```text
status=ok
phase=candidates_evaluated
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

## Runtime Observations

- `python -m cli.main ...`은 `No module named cli.main`으로 실패해 `python .\stom_backtest.py ...`로 동일 인자를 실행했다.
- `backtest/temp/wide_v1_iteration_v3_20260423.json`은 UTF-16 LE BOM 인코딩으로 기록됐다.
- observed JSON의 한국어 feature/expression metadata는 mojibake로 저장됐다.
- top 10 후보가 모두 동일한 `reference_adjusted_score=13497.662902097409`로 tie였고, artifact는 명시적 tie-break key를 노출하지 않는다. observed result에서는 `cand001`이 first-ranked/generated tied entry로 유지됐고 `cleanup_summary`는 loser 9개 삭제로 끝났다.

## Candidate Family Mix

```json
{
  "v3_repair_trade_amount": 3,
  "v3_replace_secondary": 15,
  "v3_tighten_secondary": 15,
  "v3_control_keep_best": 1
}
```

## Test Plan

- `python .\stom_backtest.py discovery research WideV1IterationV3_20260423 ... --run-candidates --candidate-count 10`
- `git diff --check -- docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_iteration_loop_v3.md docs/pr/2026-04-23_wide_v1_v3_candidate_generation_rules_pr.md docs/update_log/2026-04-23_wide_v1_v3_candidate_generation_rules.md`
- `git status --short --untracked-files=all`

## Remaining Risk

- `control_candidate.reference_adjusted_score`가 비어 있어 PASS가 "control score를 초과했다"는 의미로 증명되지는 않았다.
- top 10 tie 상태라서 실제 채택 전에는 candidate rule review나 추가 tie-break 기준이 필요하다.
- promote/WFO 검증은 아직 수행하지 않았다.
