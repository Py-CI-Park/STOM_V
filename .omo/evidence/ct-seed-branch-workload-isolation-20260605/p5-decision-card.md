# P5 Decision Card

Status: `complete`

## Verdict

`CT_BUY_BRANCH_WORKLOAD`

## Evidence Table

| Evidence | Result | Impact |
|---|---|---|
| Previous same-window control | `Tick_B_902_905_Update_2/S` passed on `2025-01-03 09:02..09:05` | environment/window can produce CSV+metrics |
| Previous C_T original | C_T warm/cold timed out after data load on same window | C_T seed/window workload blocker exists |
| Diagnostic copies | four `CT_DIAG_*_20260605` rows copied hash-identically, then cleaned | mixed pairs are controlled diagnostic runs |
| C_T buy + control sell | timeout at `120s`, `csv=no` | blocker follows C_T buy |
| control buy + C_T sell | success, CSV path present, profit `149,567`, trades `1`, MDD `2.99` | C_T sell alone does not reproduce blocker |
| Static hint | `09:02..09:05` lies in C_T buy's earliest `시분초 < 90500` branch | next page should repair/analyze that branch family |

## Page Progress

| Page Step | Status | Evidence |
|---|---|---|
| P0 Safety | complete | `p0-safety-baseline.md` |
| P1 Branch static map | complete | `p1-branch-static-map.md` |
| P2 Diagnostic copy map | complete | `p2-diagnostic-copy-map.md`, `p2-diagnostic-copy-map.json` |
| P3 Mixed-pair preflights | complete | `p3-mixed-pair-preflights.md` |
| P4 Runtime log review | complete | `p4-runtime-log-review.md` |
| P5 Decision | complete | this file |
| P6 Next command | pending | next |
| Final verification | pending | next |

## Blocked Claims

- No human-level strategy claim.
- No seed-superior claim.
- No 2023-2025 training claim.
- No 2022/2026 OOS claim.
- No final approval/export/live/V3K claim.

## Decision

The next work should not retry larger windows or OOS. It should repair or simplify the C_T buy code path active before `09:05`, then rerun the same bounded `2025-01-03 09:02..09:05` preflight until CSV+metrics are produced.
