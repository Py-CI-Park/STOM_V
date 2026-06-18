# Draft: TICK Selection Rule Sparse Gen5 Research 20260604

## Requirements (confirmed)
- User requested: proceed with the recommended next command.
- Recommended command: create a plan for TICK candidate selection-rule improvement and sparse-positive gen5-lineage research.
- Canonical inputs: `docs/AGENT_HANDOFF.md`, `.omo/evidence/tick-oos-dashboard-validation-20260604/p6-decision-card.md`, `p4-analysis.md`, and `p5-oos-comparison.md`.
- Constraints: no OOS-after-the-fact reselection, no engine/hard-gate/backtest_graph changes, and every new candidate must be fixed by a predeclared selection rule.

## Technical Decisions
- Plan type: source-plus-research validation plan, with source edits only if needed to make candidate selection explicit and auditable.
- Primary rule direction: penalize training-negative candidates and allow sparse-positive candidates only through a predeclared selector, not post-OOS judgment.
- Promotion stance: no promotion/export; final verdict must be evidence-bound.

## Research Findings
- Prior P6 verdict is `REJECT_CANDIDATE`.
- P3 selected gen4 by graded score, but gen4 was training-negative and gate false.
- P3 gen5 was sparse-positive in training, but was not eligible after the declared P3 rule.
- P5 OOS failed the superiority rule: AI combined profit `-405,285` vs seed `+2,032,445`.
- P4 found weak variable signal and segment feedback observed only on buy prompt.

## Open Questions
- None requiring user decision; default is to produce a plan now.

## Scope Boundaries
- INCLUDE: predeclared selector design, code/test changes if necessary, fresh train/OOS evidence, dashboard/wiki documentation, final decision card.
- EXCLUDE: engine edits, hard-gate weakening, `backtest/graph/`, production export, final approval, live broker/V3K work.
