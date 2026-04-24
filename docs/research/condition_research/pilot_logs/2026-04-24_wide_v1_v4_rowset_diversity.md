# Wide v1 v4 actual row-set diversity

## 1. Decision

```text
decision=HOLD_V4_ROW_SET_REVIEW
next_command=$brainstorming Wide v1 v5 actual row-set diversity selection 보강 설계
```

## 2. Inputs

```text
runtime_path=backtest\temp\wide_v1_iteration_v4_20260424.json
runtime_root=.
top_n=10
```

## 3. Actual Candidate Summary

```text
candidate_count=10
row_set_identity_status=partially_distinct
group_count=9
```

## 4. Row-Set Diversity

```json
{
  "status": "partially_distinct",
  "candidate_count": 10,
  "group_count": 9,
  "groups": [
    {
      "group_id": 1,
      "row_count": 29572,
      "representative": "WideV1IterationV4_20260424__cand002",
      "representative_family": "v4_replace_secondary",
      "members": [
        "WideV1IterationV4_20260424__cand002"
      ],
      "member_families": {
        "WideV1IterationV4_20260424__cand002": "v4_replace_secondary"
      }
    },
    {
      "group_id": 2,
      "row_count": 29792,
      "representative": "WideV1IterationV4_20260424__cand006",
      "representative_family": "v4_relax_trade_amount",
      "members": [
        "WideV1IterationV4_20260424__cand006"
      ],
      "member_families": {
        "WideV1IterationV4_20260424__cand006": "v4_relax_trade_amount"
      }
    },
    {
      "group_id": 3,
      "row_count": 34091,
      "representative": "WideV1IterationV4_20260424__cand009",
      "representative_family": "v4_replace_secondary",
      "members": [
        "WideV1IterationV4_20260424__cand009"
      ],
      "member_families": {
        "WideV1IterationV4_20260424__cand009": "v4_replace_secondary"
      }
    },
    {
      "group_id": 4,
      "row_count": 35286,
      "representative": "WideV1IterationV4_20260424__cand001",
      "representative_family": "v4_repair_trade_amount",
      "members": [
        "WideV1IterationV4_20260424__cand001"
      ],
      "member_families": {
        "WideV1IterationV4_20260424__cand001": "v4_repair_trade_amount"
      }
    },
    {
      "group_id": 5,
      "row_count": 35073,
      "representative": "WideV1IterationV4_20260424__cand003",
      "representative_family": "v4_replace_secondary",
      "members": [
        "WideV1IterationV4_20260424__cand003"
      ],
      "member_families": {
        "WideV1IterationV4_20260424__cand003": "v4_replace_secondary"
      }
    },
    {
      "group_id": 6,
      "row_count": 35700,
      "representative": "WideV1IterationV4_20260424__cand008",
      "representative_family": "v4_replace_secondary",
      "members": [
        "WideV1IterationV4_20260424__cand008"
      ],
      "member_families": {
        "WideV1IterationV4_20260424__cand008": "v4_replace_secondary"
      }
    },
    {
      "group_id": 7,
      "row_count": 35898,
      "representative": "WideV1IterationV4_20260424__cand007",
      "representative_family": "v4_relax_trade_amount",
      "members": [
        "WideV1IterationV4_20260424__cand007"
      ],
      "member_families": {
        "WideV1IterationV4_20260424__cand007": "v4_relax_trade_amount"
      }
    },
    {
      "group_id": 8,
      "row_count": 35942,
      "representative": "WideV1IterationV4_20260424__cand010",
      "representative_family": "v4_replace_secondary",
      "members": [
        "WideV1IterationV4_20260424__cand010"
      ],
      "member_families": {
        "WideV1IterationV4_20260424__cand010": "v4_replace_secondary"
      }
    },
    {
      "group_id": 9,
      "row_count": 36096,
      "representative": "WideV1IterationV4_20260424__cand004",
      "representative_family": "v4_tighten_secondary",
      "members": [
        "WideV1IterationV4_20260424__cand004",
        "WideV1IterationV4_20260424__cand005"
      ],
      "member_families": {
        "WideV1IterationV4_20260424__cand004": "v4_tighten_secondary",
        "WideV1IterationV4_20260424__cand005": "v4_tighten_secondary"
      }
    }
  ],
  "errors": []
}
```

## 5. v4 Family Diagnostics

```json
{
  "pool_type_counts": {
    "v4_relax_trade_amount": 2,
    "v4_repair_trade_amount": 1,
    "v4_replace_secondary": 7,
    "v4_tighten_secondary": 7,
    "v4_control_keep_best": 1
  },
  "selected_type_counts": {
    "v4_repair_trade_amount": 1,
    "v4_replace_secondary": 5,
    "v4_tighten_secondary": 2,
    "v4_relax_trade_amount": 2
  },
  "executed_type_counts": {
    "v4_replace_secondary": 5,
    "v4_relax_trade_amount": 2,
    "v4_repair_trade_amount": 1,
    "v4_tighten_secondary": 2
  },
  "unknown_executed_strategies": []
}
```

## 6. Quant Interpretation

```text
- Some executed candidates collapse into duplicate actual trade row sets.
- Executed candidates span 4 v4 families.
```

## 7. Next Step

```text
$brainstorming Wide v1 v5 actual row-set diversity selection 보강 설계
```
