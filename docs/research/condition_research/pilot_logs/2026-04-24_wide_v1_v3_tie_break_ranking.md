# Wide v1 v3 tie-break and ranking reinforcement

## 1. Decision

```text
decision=HOLD_ROW_SET_EQUIVALENCE
next_command=$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계
```

## 2. Inputs

```text
runtime_path=C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json
runtime_root=C:\System_Trading\STOM\STOM_V.wt-wide-v3
top_n=10
```

## 3. Tie Candidate Summary

```text
candidate_count=10
row_set_identity_status=all_identical
group_count=1
```

## 4. Row-Set Equivalence

```json
{
  "status": "all_identical",
  "candidate_count": 10,
  "group_count": 1,
  "groups": [
    {
      "group_id": 1,
      "row_count": 36096,
      "representative": "WideV1IterationV3_20260423__cand004",
      "representative_family": "v3_tighten_secondary",
      "members": [
        "WideV1IterationV3_20260423__cand001",
        "WideV1IterationV3_20260423__cand002",
        "WideV1IterationV3_20260423__cand003",
        "WideV1IterationV3_20260423__cand004",
        "WideV1IterationV3_20260423__cand005",
        "WideV1IterationV3_20260423__cand006",
        "WideV1IterationV3_20260423__cand007",
        "WideV1IterationV3_20260423__cand008",
        "WideV1IterationV3_20260423__cand009",
        "WideV1IterationV3_20260423__cand010"
      ],
      "member_families": {
        "WideV1IterationV3_20260423__cand001": "v3_tighten_secondary",
        "WideV1IterationV3_20260423__cand002": "v3_tighten_secondary",
        "WideV1IterationV3_20260423__cand003": "v3_tighten_secondary",
        "WideV1IterationV3_20260423__cand004": "v3_tighten_secondary",
        "WideV1IterationV3_20260423__cand005": "v3_tighten_secondary",
        "WideV1IterationV3_20260423__cand006": "v3_tighten_secondary",
        "WideV1IterationV3_20260423__cand007": "v3_tighten_secondary",
        "WideV1IterationV3_20260423__cand008": "v3_tighten_secondary",
        "WideV1IterationV3_20260423__cand009": "v3_tighten_secondary",
        "WideV1IterationV3_20260423__cand010": "v3_tighten_secondary"
      }
    }
  ],
  "errors": []
}
```

## 5. Representative Selection

```text
rule=fewer conditions, family priority, shorter expression, lower rank, lower index
```

## 6. Family Selection Diagnostics

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

## 7. Quant Interpretation

```text
- Top tied candidates share one executed trade row set.
- The selected winner is not a unique quant winner.
- Selection remains concentrated in one v3 family.
- Executed candidates remain concentrated in one v3 family.
```

## 8. Next Step

```text
$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계
```
