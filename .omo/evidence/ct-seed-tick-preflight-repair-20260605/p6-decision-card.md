# P6 Decision Card

Status: `complete`

## Verdict

`CT_SEED_WINDOW_BLOCKER`

## Evidence Table

| Evidence | Result | Impact |
|---|---|---|
| P1 coverage | `2025-01-03 09:02..09:05` has `181` moneytop rows and `43` distinct codes | window is data-covered |
| P2 static inspect | control buy has `09:02..09:05` hints; C_T has broader early branches | same-window comparison is fair enough for preflight |
| P3 control | `Tick_B_902_905_Update_2/S` succeeds on `2025-01-03 09:02..09:05` | same-window active control exists |
| P4 C_T warm | C_T loads `back_count=43`, then warm backtest timeout at `120s`, `csv=no` | C_T does not pass preflight |
| P4 C_T cold | C_T cold loads `moneytop_rows=181`, `back_count=43`, then timeout after backtest process start | blocker is not warm-only |
| P5 dashboard contract | engine/timeframe/start/end/timeout fields are already covered | no dashboard work needed in this page |

## What Changed Versus Previous Page

Previous page ended as `INCONCLUSIVE_NEEDS_ENGINE_INTERNAL_EVIDENCE` because same-window control also failed in `09:00..09:01`.

This page found the fairer active same-window `09:02..09:05`:

- control passes in that exact window;
- C_T fails in that exact window;
- C_T also fails cold in that exact window.

That narrows the blocker to C_T seed/window workload behavior. It still does not prove overfit, profitability, human-level quality, or OOS readiness.

## Page Progress

| Page Step | Status | Evidence |
|---|---|---|
| P0 Safety | complete | `p0-safety-baseline.md` |
| P1 Coverage preflight | complete | `p1-window-coverage-preflight.md` |
| P2 Strategy inspect | complete | `p2-strategy-timefilter-inspect.md` |
| P3 Same-window control | complete | `p3-same-window-active-control.md` |
| P4 C_T preflight | complete | `p4-ct-bounded-preflight.md` |
| P5 Dashboard/context | complete | `p5-dashboard-ai-context-check.md` |
| P6 Decision | complete | this file |
| P7 Next command | pending | next |
| Final verification | complete | `final-verification.md` |

## Allowed Next Steps

- Build a C_T branch/workload isolation plan for the `09:02..09:05` window.
- Use diagnostic strategy copies or analysis artifacts only; no final/export/live path.
- Keep all new toggles default OFF.
- Keep January retry, 2023-2025 training, and 2022/2026 OOS blocked until a repaired C_T candidate produces CSV+metrics in bounded preflight.

## Blocked Claims

- No human-level strategy claim.
- No seed-superior claim.
- No OOS claim.
- No export/final approval/live/V3K approval.

## Decision

This page achieved its goal: it found a same-window active control and showed C_T still times out. The next page should isolate and repair the C_T branch/workload, not expand training.
