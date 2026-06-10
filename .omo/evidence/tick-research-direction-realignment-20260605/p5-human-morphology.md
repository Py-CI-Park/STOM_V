# P5 Human-Reference Morphology Note

## Scope
- Work ID: `tick-research-direction-realignment-20260605`
- Training period context: `2023-01-01..2025-12-31`
- Timeframe context: `tick`
- Reference document: `docs/research/2026-06-04_condition_research_rereview_human_reference_graphs.md`

## Position
Human-reference graph similarity is a research prior, not promotion proof.

The user's concern is valid: good human condition expressions can look overfit because humans iteratively read charts and backtests. Therefore the Exploration Pool and Research Pool should keep human-like, high-train, recent-improving, or near-miss candidates instead of killing them early.

## Morphology Fields For Research Ranking
- Trade density and yearly trade sufficiency.
- MDD corridor and drawdown recovery behavior.
- Payoff ratio.
- Equity smoothness / uptrend R2 proxy.
- Late-period collapse proxy.
- Recent-year improvement, with 2025 weighted more heavily than 2024 and 2023.
- Time-window spread.
- Market-cap segment behavior.
- `max_hold_count` only as `display_only`/annotation until reliability is proven.
- Similarity to human screenshots only as a label/corridor hint.

## Boundaries
- No fixed 2022/2026 OOS was used in P5.
- No human-level or seed-superiority claim is allowed from morphology alone.
- PBO/DSR/slippage and fixed OOS remain Promotion Gate requirements.

## Next Use
After P7 creates candidate CSVs, run correlation/feature/backfinder diagnostics across Research Pool candidates and store the actual ranked signals in `p7-candidate-pools.json` or a follow-up report.
