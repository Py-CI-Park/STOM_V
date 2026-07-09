# 2026-07-09 Lattice V2 Closeout Or New Design Handoff

| Item | Value |
|---|---|
| Decision | `archive_v2_branch_and_stop` |
| DB/replay/OOS/Plan D executed | No |
| Main report | `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md` |
| Corrected sell/risk audit | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_corrected_sell_risk_clause_audit_20260709.md` |
| Decision JSON | `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_closeout_or_new_design_decision_20260709.json` |

## What The Next Agent Should Know

- The v2 body branch is closed by evidence unless the user explicitly opens a separate v3 design-only plan.
- The previous risk/sell table was corrected; old stop/take-profit values like `90` and `120` were threshold extraction artifacts.
- The corrected audit does not change replay outcome: 0 survivor, 0 hold, 8 no_go.
- Do not run DB apply, replay, OOS, portfolio, Plan D, or promotion from this branch without a new user scope.

## Safe Next Options

| Option | Command | When To Use |
|---|---|---|
| Commit/review closeout | user-directed commit or PR review flow | If the user wants to end this research page cleanly |
| New design-only plan | `$ulw-plan docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` | If the user wants another research generation architecture, with no DB/replay in the planning page |
| Manual evidence reconciliation | none recommended now | Only if user disputes the replay evidence |
