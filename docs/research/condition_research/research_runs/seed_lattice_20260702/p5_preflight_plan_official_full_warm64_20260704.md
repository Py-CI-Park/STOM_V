# Plan B P5 Official Full Warm64 Preflight Plan

## Scope

This is a preflight plan only. Do not run tick/min 288 full smoke from this step.

## Read-first receipts

- Profile audit receipt: `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_profile_audit_official_full_warm64_20260704.json`
- Tick official config: `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json`
- Min official config: `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_min_official_full_warm64_20260704.json`
- Tick preflight pairs: `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_preflight4_official_full_warm64_20260704.json`

## Verified source DB ranges

- tick: `20220323090000` ~ `20260227093000` (date config `20220323`~`20260227`)
- min: `202504070900` ~ `202602271519` (date config `20250407`~`20260227`)

## Required preflight command (not run by this audit)

```powershell
python -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_preflight4_official_full_warm64_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_preflight_tick_official_full_warm64_20260704_retry02 `
  --fail-fast-timeout
```

## Acceptance before any full run

- The command prepares warm64 successfully on the official tick DB-full-period profile.
- All 2~4 preflight pairs record honest `ok`, `no_trades`, or `error` rows with CSV/metrics status preserved.
- Runtime reason strings show effective gates `min_daily_trades 0.5` and `mdd_cap 35` when those gates fail.
- If a timeout streak appears, stop and lower chunk size or increase per-run timeout before any 288 full run.
- Use `--fail-fast-timeout` for preflight runs so a timeout is recorded as an error row instead of spending another full warm-pool recovery/reload cycle.

## Full-run protocol after preflight passes

- Use a new run_id; never reuse `lat_smoke_tick_full_sanitized_20260704*`.
- Split 288 tick pairs into 48-pair chunks; close/restart warm engines between chunks.
- Export tick results normally before min starts.
- Only after official tick export may the min official config be preflighted/run.
- P5 success means coverage-map completion: per-cell trades, gross/net EV, and MDD distribution. `gate_passed` count is advisory.
