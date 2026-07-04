# 2026-07-04 P5 official tick pilot12 handoff

## Scope

This note records G009 only: the official DB-full-period + warm64 tick pilot12 run required after the P5 full-run protocol review.

Managed plan: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`.

## Command executed

```powershell
python -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_pilot12_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_tick_official_full_warm64_pilot12_20260704 `
  --fail-fast-timeout
```

## Result

Evidence receipt:
`docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_pilot12_official_full_warm64_20260704_receipt.json`

Observed runtime facts:

- run_id: `lat_tick_official_full_warm64_pilot12_20260704`
- run status: `complete`
- warm prepare: `status=ok back_count=2424 elapsed=336s`
- elapsed: `1575.931s`
- rows: `12/12`
- status counts: `ok=12`
- gate_passed: `0`
- MDD range: `280.14` to `1558.72`
- profit range: `-472,898,110` to `-42,046,738`
- daily average trade range: `1.8` to `13.4`

## Quant interpretation

The run is operationally clean: warm64 prepared, every pilot row recorded an honest `ok` status, and the post-run process surface was clean.

The trading-quality result is bad. Every row failed the effective `mdd_cap=35` gate, and losses/MDD are too large to treat any pilot row as a survivor, promotion candidate, or proof that chart-sulsa/lattice conditions are economically valid as complete strategies.

This does not invalidate the P5 coverage-map objective. P5 success remains coverage-map completion with per-cell trades, gross/net EV, and MDD; `gate_passed=0` is advisory for promotion and decisive against survivor promotion, not a reason to use wrong-profile smoke rows or skip evidence collection.

## Current blocks

Still forbidden:

- Do not use `lat_smoke_tick_full_sanitized_20260704*` for official survivor/rejection/P6 decisions.
- Do not run tick 288 as one monolithic run.
- Do not start min before official tick export exists.
- Do not start P6/P7 before official tick outputs exist.
- Do not treat any pilot12 row as survivor or promotion evidence.

Allowed next action after G009 checkpoint:

- Continue G010 as official tick 24-pair chunked coverage-map execution, starting with chunk01 only, using `--fail-fast-timeout` and warm64 prepare/close per chunk.

## Next command shape

Use the manifest rather than a monolithic 288 run:

```powershell
python -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk01_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_tick_official_full_warm64_chunk01_20260704 `
  --fail-fast-timeout
```

Stop on any timeout/error, missing row, warm prepare failure, or lingering process surface.
