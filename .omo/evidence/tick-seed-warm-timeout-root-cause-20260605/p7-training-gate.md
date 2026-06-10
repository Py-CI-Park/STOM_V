# P7 Training Gate And Next Command

Status: `complete`

## Gate Decision

`BLOCK_LONG_TRAINING_AND_OOS`

Reason: the C_T seed did not produce a passing tiny preflight. Corrected warm W1R and plan-bound same-window cold both loaded data but ended with `csv_path=null` and no metrics. The same-window control also failed no-metrics, while the control seed succeeded in its intended `09:02..09:05` active window. The next page should repair the exact C_T seed/window preflight before any larger run.

## Allowed / Blocked

| Action | Decision | Reason |
|---|---|---|
| 10m C_T diagnostic | blocked for immediate execution | no passing 1m preflight yet |
| January C_T retry | blocked | would repeat the no-metrics seed/window issue at larger cost |
| 2023-2025 training | blocked | no CSV/metrics preflight |
| 2022/2026 OOS | blocked | no promotion candidate and no preflight |
| Exact time-window coverage audit | allowed | needed before each tick diagnostic |
| C_T seed/window repair preflight | allowed | smallest next step |
| Same-window active control search | allowed | needed to separate window/no-trade from seed-specific behavior |
| Control seed active-window sanity check | allowed | diagnostic only, not performance proof |

## Next Recommended Command

```text
$ulw-plan C_T seed tick preflight repair plan: use .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p6-root-cause-decision-card.md, p3-window-coverage-audit.json, p4-cold-warm-compare.md, and p5-control-baseline.md as primary evidence. Build an exact per-day time-window coverage preflight for tick runs, find or construct a same-window active control without editing official engines or hard gates, inspect C_T_900_920_U2_B/S time filters and no-trade behavior, test the smallest corrected windows that can produce CSV/metrics, keep all new toggles default OFF, and keep 2023-2025 training plus 2022/2026 OOS blocked until a passing C_T preflight exists.
```

## Page Progress

| Page Step | Status |
|---|---|
| P0 Safety | complete |
| P1 Seed/config/data audit | complete |
| P2 Probe harness | complete |
| P3 Warm tiny ladder | complete |
| P4 Cold/warm compare | complete |
| P5 Control baseline | complete |
| P6 Root cause decision | complete |
| P7 Training gate | complete |
| Final verification | pending |

## Notes

- This page improved the system by replacing a vague timeout blocker with a narrower exact-window no-metrics-after-data-load diagnosis and by exposing that exact tick time-window coverage must be checked before larger runs.
- It does not prove any human-level condition strategy.
- It does not approve export, final approval, live broker use, V3K gates, hard-gate relaxation, or official engine edits.
