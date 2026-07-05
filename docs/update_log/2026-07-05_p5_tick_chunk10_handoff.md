# 2026-07-05 P5 official tick chunk10 handoff

## Scope

This note records the completed official tick chunk10 run for Plan B P5.

Managed plan: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`.

## Command executed

```powershell
python -u -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk10_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_tick_official_full_warm64_chunk10_20260705 `
  --fail-fast-timeout
```

## Result

Evidence receipt:
`docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk10_official_full_warm64_20260705_receipt.json`

Observed runtime facts:

- run_id: `lat_tick_official_full_warm64_chunk10_20260705`
- run status: `complete`
- warm prepare: `status=ok back_count=2424 elapsed=312s`
- elapsed: `2519.135s`
- rows: `24/24`
- status counts: `ok=24`
- gate_passed: `0`
- MDD range: `211.98` to `586.81`
- profit range: `-425,621,498` to `-21,242,273`
- daily average trade range: `1.2` to `21.6`
- post-run process scan: no live chunk10 batch process

## Quant interpretation

Chunk10 is operationally clean and suitable as official P5 coverage-map
evidence. Trading quality remains bad: every row failed a performance gate, and
no row is a survivor or promotion candidate.

## Current blocks

Still forbidden in the selected range:

- Do not run tick export.
- Do not start min.
- Do not start P6/P7/Plan D.
- Do not treat any chunk10 row as survivor or promotion evidence.
- Do not mutate stale `running` rows with DB `UPDATE` or `DELETE`.

Allowed next action:

- Continue with P5 official tick chunk11 only, using `--fail-fast-timeout` and
  the existing official full-period warm64 config.
