# 2026-07-05 P5 official tick chunk09 stale-start handoff

## Scope

This note records the chunk09 stale-start state before rerunning chunk09 with a
new run id. It does not complete chunk09 and does not permit chunk10/min/P6/P7.

Managed plan: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`.

## State audit

Audit time: 2026-07-05 06:24 KST.

| Item | Value |
|---|---|
| Original run id | `lat_tick_official_full_warm64_chunk09_20260704` |
| DB status | `running` |
| Generation rows | `0/24` |
| Recorded gen_nos | `[]` |
| Live batch/backtest process | none |
| Official config | tick DB full period + warm64 |
| Config dates | `20220323` to `20260227` |
| Config time window | `090000` to `092800` |
| Pair manifest | `pairs_tick_official_full_warm64_chunk09_20260704.json` |

Receipt:
`docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk09_stale_start_official_full_warm64_20260705_receipt.json`

## Interpretation

The original chunk09 run is a stale-start record. The GJC wrapper stopped before
warm64 prepare and before any generation row was recorded. This is an execution
management issue, not a trading-quality failure.

Because there are zero generation rows, chunk09 should be rerun as the same
24-pair chunk with a new run id, not as a supplement of missing gen numbers.

## Next allowed action

Run chunk09 with a new run id:

```powershell
python -u -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk09_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_tick_official_full_warm64_chunk09_retry01_20260705 `
  --fail-fast-timeout
```

## Still forbidden

- Do not reuse `lat_tick_official_full_warm64_chunk09_20260704`.
- Do not mutate `loop_runs.db` with `UPDATE` or `DELETE`.
- Do not start chunk10 until chunk09 has 24 honest official rows.
- Do not start min/P6/P7 before official tick export exists.
- Do not use `lat_smoke_tick_full_sanitized_20260704*` for official decisions.
