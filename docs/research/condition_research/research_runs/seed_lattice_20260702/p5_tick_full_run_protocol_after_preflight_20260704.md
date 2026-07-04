# P5 Tick Full-Run Protocol After Official Preflight

## Verdict

Do not run tick 288 as one monolithic run. The next allowed action is a 12-pair pilot chunk only.

## Evidence inputs

- Preflight receipt: `p5_tick_preflight_official_full_warm64_20260704_receipt.json`
- Official tick config: `smoke_config_tick_official_full_warm64_20260704.json`
- Chunk manifest: `p5_tick_official_chunk_manifest_full_warm64_20260704.json`
- Pilot pairs: `pairs_tick_official_full_warm64_pilot12_20260704.json`

## Decision

| Item | Decision |
|---|---|
| single run 288 | forbidden |
| next run | pilot12 only |
| pilot command flag | `--fail-fast-timeout` required |
| chunk size after clean pilot | 24 pairs |
| chunk count after clean pilot | 12 |
| warm policy | prepare warm64 before each pilot/chunk, close after each pilot/chunk |
| P5 success criterion | coverage-map completion, not `gate_passed` count |
| min start | forbidden until official tick export exists |

## Pilot command

```powershell
python -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_pilot12_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_tick_official_full_warm64_pilot12_20260704 `
  --fail-fast-timeout
```

## Stop conditions

- warm prepare is not `ok`.
- any pair records `error` or triggers fail-fast timeout.
- process cleanup scan finds lingering preflight/chunk processes.
- pilot/chunk rows are missing honest `ok` / `no_trades` / `error` status.
- any attempt starts min/P6/P7 before official tick export.

## Rationale

The preflight proved official DB-full-period + warm64 can prepare and record rows, but all four preflight rows failed gates and showed severe MDD/profit damage. The wrong-profile gate_passed=0 concern remains a map-building problem, not a promotion signal. Runtime evidence also showed a long warm recovery/reload wait; therefore all larger runs must use fail-fast timeout and smaller 24-pair chunks instead of the earlier 48-pair plan.
