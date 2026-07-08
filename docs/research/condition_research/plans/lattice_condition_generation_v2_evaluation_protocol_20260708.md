# Lattice Condition Generation V2 Evaluation Protocol

Created: 2026-07-08T09:58:26+09:00

## Primary Split

| Segment | Period | Use |
|---|---|---|
| train/design | 2025-04-07~2025-09-30 | design and parameter sanity only |
| validation | 2025-10-01~2025-12-31 | candidate selection after preregistration |
| blind OOS | 2026-01-01~2026-02-27 | open once per frozen selected batch only |

## Walk-Forward Alternative

| Fold | Design | Validation |
|---|---|---|
| WF1 | 2025-04~2025-06 | 2025-07 |
| WF2 | 2025-05~2025-08 | 2025-09 |
| WF3 | 2025-07~2025-10 | 2025-11 |
| WF4 | 2025-09~2025-12 | 2026-01 |

## Important Boundary

This file defines the protocol only. It does not authorize DB INSERT apply, backtest, OOS, portfolio, Plan D R3, or promotion.
