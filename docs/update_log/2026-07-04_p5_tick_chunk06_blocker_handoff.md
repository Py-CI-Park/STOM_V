# P5 Tick Chunk06 Stale Partial Blocker Handoff

Date: 2026-07-04

## Status

`lat_tick_official_full_warm64_chunk06_20260704` is not an official complete chunk. Preserve it as stale/partial evidence.

## Evidence

- run_id: `lat_tick_official_full_warm64_chunk06_20260704`
- DB status: `running`
- recorded rows: `10/24`
- recorded gen_nos: `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]`
- missing gen_nos: `[10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]`
- status_counts: `{'ok': 10}`
- gate_passed: `0`
- MDD range: `305.59~805.16`
- live python batch process: `0`

Receipt: `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk06_blocker_official_full_warm64_20260704_receipt.json`
Supplement manifest: `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk06_supplement10_23_20260704.json`

## Decision

Chunk06 cannot be marked complete from the first attempt because the DB row remains `running`, no live batch process exists, and only 10/24 generation rows were recorded. This is the same stale-partial class as chunk04 and must be handled append-only.

## Next allowed action

Run only the chunk06 supplement manifest with a new run id and `--fail-fast-timeout`:

```powershell
python -u -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk06_supplement10_23_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_tick_official_full_warm64_chunk06_supplement10_23_20260704 `
  --fail-fast-timeout
```

## Still forbidden

- No DB `UPDATE`/`DELETE`.
- No chunk07 until chunk06 has 24 honest official rows.
- No min/P6/P7 until official tick export exists.
- No wrong-profile `lat_smoke_tick_full_sanitized_20260704*` official decisions.
