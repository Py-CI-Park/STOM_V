# P0 Direction Audit

## Scope

- Plan: `.omo/plans/tick-research-direction-realignment-20260605.md`
- Review source: `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
- Evidence baseline: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md`, `.omo/evidence/tick-sparse-positive-oos-robustness-20260604/p7-decision-card.md`
- Branch: `lazycodex/tick-sparse-positive-generation-improvement-20260604`
- Baseline HEAD: `84acb6cbb0478fa1909a19e17ef214501cbd9a74`

## Direction Change

The 2026-06-05 review changes the execution strategy. Strict selectors remain necessary for final claims, but they are no longer allowed to be the first research filter. The reason is practical: human-made good TICK conditions are produced through repeated chart and backtest tuning, so they can look overfit during early discovery. If the system rejects those shapes immediately, it may never learn the human-like condition space.

The revised plan therefore separates candidate handling into three layers:

- **Exploration Pool**: loose, OOS-blind retention. Keeps overfit-looking, high-train, sparse, MDD-risk, and near-miss candidates for analysis.
- **Research Pool**: medium, OOS-blind ranking. Uses human-reference morphology, recent-year improvement, quant diagnostics, and labels to prioritize candidates.
- **Promotion Gate**: strict proof gate. Requires fixed OOS, seed comparison, slippage stress, PBO/DSR, trade sufficiency, and guardrail checks.

## Why Overfit-Looking Candidates Must Remain Analyzable

The previous strict yearly selector correctly blocked weak promotion claims, but it also risked removing candidates that are valuable for research. The documented gen6/gen7 near misses show this directly:

- gen6 had positive training profit and acceptable MDD but missed a strict trade-count floor.
- gen7 had strong training profit but narrowly missed the MDD threshold.

Those candidates should not be promoted, but they should be retained for morphology, market-regime, variable-range, time/market-cap, and max-hold analysis. This distinction is the main correction in the plan.

## Strict Proof Still Required

The final proof standard is unchanged. A research candidate cannot be called human-level, seed-superior, or promotion-worthy unless it passes the Promotion Gate. Human-reference graph similarity, recent-year improvement, and overfit-looking upside are research priors only.

## N1 Priority

The review identifies PBO/CSCV and Deflated Sharpe as high-leverage diagnostics. This plan implements them early as read-only diagnostics. They label exploration and research candidates, but they block only promotion.

## Replacement vs Complement

The plan keeps the decision explicit. The final decision card must recommend whether the next direction is:

- continue AI-alone seed replacement,
- switch to seed+AI complement,
- build regime-expert portfolio,
- or build walk-forward refit workflow.

## P0 Verdict

The system is still moving in a useful direction, but the plan must avoid confusing early rejection with better generation. The revised target is to preserve promising candidate evidence longer while keeping final claims strict.
