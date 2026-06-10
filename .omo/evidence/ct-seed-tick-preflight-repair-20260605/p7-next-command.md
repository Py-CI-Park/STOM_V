# P7 Next Command

Status: `complete`

## Gate Decision

`BLOCK_LONG_TRAINING_AND_OOS`

Reason: C_T did not produce a passing bounded preflight. The same active window control passed, while C_T warm and cold both timed out/no CSV.

## Next Recommended Command

```text
$ulw-plan C_T seed branch workload isolation plan: use .omo/evidence/ct-seed-tick-preflight-repair-20260605/p6-decision-card.md, p4-ct-bounded-preflight.md, p3-same-window-active-control.md, and p2-strategy-timefilter-inspect.md as primary evidence. Isolate which C_T buy/sell branch or condition family causes the 2025-01-03 09:02..09:05 tick timeout by using diagnostic strategy copies and bounded warm/cold preflights only, without editing official backtest engines, hard gates, protected paths, backtest_graph, final_approval/export_winner/live/V3K paths. Keep new toggles default OFF, require CSV+metrics before any January retry, and keep 2023-2025 training plus 2022/2026 OOS blocked until a repaired C_T preflight passes.
```

## Allowed / Blocked

| Action | Decision | Reason |
|---|---|---|
| C_T branch isolation | allowed | smallest next root-cause step |
| C_T diagnostic strategy copies | allowed as evidence-only | must not be export/final/live |
| January retry | blocked | no passing C_T preflight |
| 2023-2025 training | blocked | no passing C_T preflight |
| 2022/2026 OOS | blocked | no promotion candidate and no preflight |

## Page Progress

| Page Step | Status |
|---|---|
| P0 Safety | complete |
| P1 Coverage preflight | complete |
| P2 Strategy inspect | complete |
| P3 Same-window control | complete |
| P4 C_T preflight | complete |
| P5 Dashboard/context | complete |
| P6 Decision | complete |
| P7 Next command | complete |
| Final verification | complete |

## Notes

- This page improves the system by converting an inconclusive window issue into a specific C_T seed/window workload blocker.
- It does not prove trading quality.
- It does not authorize larger runs.
