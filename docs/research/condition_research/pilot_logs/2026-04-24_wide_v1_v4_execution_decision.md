# Wide v1 v4 execution decision

## Decision

```text
decision=HOLD_V4_ROW_SET_REVIEW
next_command=$brainstorming Wide v1 v5 actual row-set diversity selection 보강 설계
```

## Runtime

```text
runtime_path=backtest\temp\wide_v1_iteration_v4_20260424.json
status=ok
phase=candidates_evaluated
best_candidate=WideV1IterationV4_20260424__cand002
```

## Actual Row-Set Gate

```text
row_set_identity_status=partially_distinct
group_count=9
candidate_count=10
```

## Executed v4 Family Distribution

```text
{'v4_replace_secondary': 5, 'v4_relax_trade_amount': 2, 'v4_repair_trade_amount': 1, 'v4_tighten_secondary': 2}
```

## Rule

```text
all_distinct and at least two known executed v4 families -> proceed to promote/WFO planning
all_identical, partially_distinct, not_evaluated, or error -> hold and redesign actual row-set diversity
all_distinct but one known executed family -> hold family concentration review
```
