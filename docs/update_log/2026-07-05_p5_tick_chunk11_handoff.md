# 2026-07-05 P5 official tick chunk11 handoff

## Scope

This note records the completed official tick chunk11 run for Plan B P5.

Managed plan: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`.

## Command executed

```powershell
python -u -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk11_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_tick_official_full_warm64_chunk11_20260705 `
  --fail-fast-timeout
```

## Result

Evidence receipt:
`docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk11_official_full_warm64_20260705_receipt.json`

Observed runtime facts:

- run_id: `lat_tick_official_full_warm64_chunk11_20260705`
- run status: `complete`
- warm prepare: `status=ok back_count=2424 elapsed=274s`
- elapsed: `2265.934s`
- rows: `24/24`
- status counts: `ok=24`
- gate_passed: `0`
- MDD range: `16.88` to `621.39`
- profit range: `-198,665,247` to `-899,093`
- daily average trade range: `0.1` to `6.4`
- post-run process scan: no live chunk11 batch process

## Quant interpretation

Chunk11 is operationally clean and suitable as official P5 coverage-map
evidence. Trading quality remains bad: every row failed either the MDD gate or
the minimum daily-trade gate, and no row is a survivor or promotion candidate.

## Current blocks

Still forbidden in the selected range:

- Do not run tick export.
- Do not start min.
- Do not start P6/P7/Plan D.
- Do not treat any chunk11 row as survivor or promotion evidence.
- Do not mutate stale `running` rows with DB `UPDATE` or `DELETE`.

Allowed next action:

- Continue with P5 official tick chunk12 only, using `--fail-fast-timeout` and
  the existing official full-period warm64 config.
