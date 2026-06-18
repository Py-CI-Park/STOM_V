# P6 Smoke Summary

## Run
- Run ID: `tick_realign_p6_smoke_20260605`
- Config: `.omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-config.json`
- Period: `2025-01-01..2025-03-31`
- Time window: `09:00:00..09:30:00`
- Timeframe: `tick`
- Max generations: `2`
- Wall clock: `504.3s`

## Result
- gen0 seed evaluation timed out: warm backtest exceeded `300s`, CSV not produced.
- gen1 AI generation succeeded and backtest succeeded in `32.2s`.
- gen1 metrics: profit `-4,343,533`, MDD `22.96`, trades `269`, daily average trades `4.6`, payoff `1.17`, max_hold_count `4.0`.
- Loop stop reason: `max_generations` reached.

## Pool Classification
- Evidence: `.omo/evidence/tick-research-direction-realignment-20260605/p6-candidate-pools.json`
- Exploration Pool: `1`
- Research Pool: `1`
- Promotion candidate: `none`
- Structural rejection: gen0, `csv_path missing`, `trade_count < 10`

## Interpretation
The smoke run proves that the loop can generate and backtest at least one TICK candidate under the P6 settings, and the new three-tier selector can classify it without using fixed OOS.

It does not prove human-level, seed-superior, or OOS-robust performance. The only classified candidate is useful as a negative research sample: high trade count but negative profit and high MDD.

## Blockers / Risks
- gen0 seed timeout shows the current warm tick backtest path still needs better progress/log observability and possibly smaller smoke settings.
- A short 2025-only smoke cannot satisfy the Promotion Gate's 2023/2024/2025 yearly checks.
- No fixed 2022/2026 OOS was run.

## Guardrail
- No `final_approval`, `export_winner`, production DB write, live broker action, V3K action, or blanket taskkill was used.
- Official engines and hard-gate semantics were not edited.
