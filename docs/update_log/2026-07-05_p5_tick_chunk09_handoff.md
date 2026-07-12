# 2026-07-05 P5 official tick chunk09 handoff

## Scope

This note records the completed chunk09 retry after the original chunk09
stale-start run.

Managed plan: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`.

## Command executed

```powershell
python -u -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk09_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_tick_official_full_warm64_chunk09_retry01_20260705 `
  --fail-fast-timeout
```

The original stale run id `lat_tick_official_full_warm64_chunk09_20260704` was
not reused and was not modified.

## Result

Evidence receipt:
`docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk09_official_full_warm64_20260705_receipt.json`

Observed runtime facts:

- run_id: `lat_tick_official_full_warm64_chunk09_retry01_20260705`
- run status: `complete`
- warm prepare: `status=ok back_count=2424 elapsed=262s`
- elapsed: `2380.991s`
- rows: `24/24`
- status counts: `ok=24`
- gate_passed: `0`
- MDD range: `53.41` to `1061.11`
- profit range: `-372,950,355` to `-2,497,875`
- daily average trade range: `0.1` to `11.1`
- post-run process scan: no live chunk09 retry batch process

## Quant interpretation

Chunk09 is operationally clean and suitable as official P5 coverage-map
evidence. Trading quality remains bad: every row failed either the MDD gate or
the minimum daily trade gate, and no row is a survivor or promotion candidate.

This continues the current P5 conclusion: the lattice grid is producing useful
coverage/failure-regime evidence, not promotion-ready complete strategies.

## Current blocks

Still forbidden:

- Do not use `lat_smoke_tick_full_sanitized_20260704*` for official
  survivor/rejection/P6 decisions.
- Do not run tick 288 as one monolithic run.
- Do not start min before official tick export exists.
- Do not start P6/P7 before official tick outputs exist.
- Do not treat any chunk09 row as survivor or promotion evidence.
- Do not mutate stale `running` rows with DB `UPDATE` or `DELETE`.

Allowed next action:

- Continue with P5 official tick chunk10 only, using `--fail-fast-timeout` and
  the existing official full-period warm64 config.

## Next command shape

```powershell
python -u -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk10_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_tick_official_full_warm64_chunk10_20260705 `
  --fail-fast-timeout
```

Stop on any timeout/error, missing row, warm prepare failure, or lingering
process surface.
