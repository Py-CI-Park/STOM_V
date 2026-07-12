# Plan D Rank01 R3 Context Pack

## Scope

- scope: `plan-d-rank01-r2-survivor-freeze-r3-readiness-no-portfolio-export`
- source receipt: `.omo/evidence/plan-d-rank01-r2-survivor-freeze-r3-readiness-no-portfolio-export-20260706/source_read_receipt.md`
- active parent: `plan_d_r1_rank01_r2_21_l14_rate_floor85_default_tp3_sl3_hold90`
- hard stop: no replay, no OOS, no portfolio, no export/live/final promotion in this page.

## Active Parent Freeze

| field | value |
|---|---:|
| selected OOS profit | 1,174,545 |
| selected OOS MDD | 3.25 |
| selected OOS trades | 17 |
| selected OOS daily trades | 0.50 |
| R2 replay profit | 2,515,910 |
| R2 replay MDD | 15.57 |
| R2 replay trades | 188 |

The parent is frozen because it has the highest selected-OOS profit and lowest selected-OOS MDD among the selected R2 survivors. The caveat is trade support: selected-OOS trade count is 17, so R3 should improve coverage before any portfolio step.

## R3 Design Objective

R3 should preserve the successful `l14_rate_floor85` + `default_tp3_sl3_hold90` profile and test bounded coverage improvements. The next generation should be small and auditable: 8-slot dry-run first, then limited replay only if static and registration dry-run pass.

## Candidate Axes For Next Page

| axis | decision | purpose |
|---|---|---|
| `sell_default_tp3_sl3_hold90` | promote | Keep the R2 axis that produced all selected survivors. |
| `buy_l14_rate_floor85` | promote | Active parent axis with best selected-OOS MDD/profit balance. |
| `buy_l14_amt13000_14000` | watch | Compare against 19-trade watch survivors. |
| `l14_end1445_coverage` | bounded watch | Probe coverage only; full-period profit/MDD was weaker. |
| `protective_sell_tp28_sl25` | deprioritize | Prior replay reduced profit and did not create improved rows. |

## Next Page Guardrails

- Generate at most 8 R3 candidates.
- Research lane only, `hypothesis_seed` label, sanitized names.
- Static gate and DB registration dry-run only.
- No DB INSERT apply until a later explicit replay scope.
- No OOS/portfolio/export/live/final promotion.
