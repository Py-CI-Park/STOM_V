# 2026-07-05 P5 official tick chunk12 handoff

## Scope

This note records the completed official tick chunk12 run for Plan B P5.

Managed plan: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`.

## Command executed

```powershell
python -u -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk12_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_tick_official_full_warm64_chunk12_20260705 `
  --fail-fast-timeout
```

## Result

Evidence receipt:
`docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk12_official_full_warm64_20260705_receipt.json`

Observed runtime facts:

- run_id: `lat_tick_official_full_warm64_chunk12_20260705`
- run status: `complete`
- warm prepare: `status=ok back_count=2424 elapsed=282s`
- elapsed: `2368.533s`
- rows: `24/24`
- status counts: `ok=24`
- gate_passed: `0`
- MDD range: `149.78` to `387.60`
- profit range: `-219,558,866` to `-11,642,820`
- daily average trade range: `0.6` to `11.2`
- post-run process scan: no live chunk12 batch process

## Quant interpretation

Chunk12 is operationally clean and suitable as official P5 coverage-map
evidence. Trading quality remains bad: every row failed a performance gate, and
no row is a survivor or promotion candidate.

## Selected-range stop

The selected range asked only for chunk10 through chunk12 and a tick 288/288
completion judgment. Therefore tick export, min, P6, P7, and Plan D remain
unstarted in this session.
