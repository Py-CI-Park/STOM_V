# Wide v1 v3 결과 분석 및 v4 여부 판단

## 1. 판단

```text
decision=HOLD_V3_TIE_REVIEW
next_command=$brainstorming Wide v1 v3 tie-break 및 ranking 보강 설계
```

## 2. 입력

```text
runtime_path=C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json
wide_reference_csv=C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
control_csv=C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv
```

## 3. runtime 요약

```text
status=ok
phase=candidates_evaluated
candidate_count_observed=10
best_candidate=WideV1IterationV3_20260423__cand001
```

## 4. Control Score Gate

```text
status=ok
stored_reference_adjusted_score=None
recomputed_reference_adjusted_score=13497.662902097409
reference_adjusted_score=13497.662902097409
stored_score_status=missing
score_match=None
message=None
```

## 5. Tie Gate

```text
status=rank_metric_tie
score_tie=True
metric_tie=True
row_set_identity_status=not_evaluated
top_count=10
tie_candidate_count=10
```

## 6. Candidate Family Gate

```json
{
  "pool_type_counts": {
    "v3_repair_trade_amount": 3,
    "v3_replace_secondary": 15,
    "v3_tighten_secondary": 15,
    "v3_control_keep_best": 1
  },
  "retention_observed_type_counts": {
    "v3_repair_trade_amount": 3,
    "v3_replace_secondary": 15,
    "v3_tighten_secondary": 15
  },
  "retention_pass_type_counts": {
    "v3_repair_trade_amount": 3,
    "v3_replace_secondary": 15,
    "v3_tighten_secondary": 15
  },
  "retention_fallback_type_counts": {},
  "selected_type_counts": {
    "v3_tighten_secondary": 10
  },
  "executed_type_counts": {
    "v3_tighten_secondary": 10
  },
  "unknown_executed_strategies": [],
  "family_selection_summary": {
    "v3_repair_trade_amount": "retention-pass only",
    "v3_replace_secondary": "retention-pass only",
    "v3_tighten_secondary": "selected/executed"
  }
}
```

## 7. Quant Validity Gate

```json
{
  "blocked": true,
  "reasons": [
    "top_candidates_score_tie",
    "top_candidates_metric_tie"
  ]
}
```

## 8. 다음 단계

```text
$brainstorming Wide v1 v3 tie-break 및 ranking 보강 설계
```
