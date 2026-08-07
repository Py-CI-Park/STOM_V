# Task 7 CLI and Runbook Consistency Review

## Finding

The roadmap examples for `tmap_sweep` are currently inconsistent with the CLI. The docs use `--out-prefix`, but current `python -m ai_strategy_loop.scripts.tmap_sweep --help` exposes `--run-id` and `--manifest-out`; it does not expose `--out-prefix`.

## Help Output Contract

Current accepted arguments:

```text
--template TEMPLATE
--config-json CONFIG_JSON
--run-id RUN_ID
--params PARAMS
--max-points MAX_POINTS
--manifest-out MANIFEST_OUT
--resume
--grid GRID
--replicate-baseline REPLICATE_BASELINE
```

## Corrected Future Tick Command

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
python -m ai_strategy_loop.scripts.tmap_sweep `
  --template tick_late_0920_0925_continuation `
  --config-json .omo/evidence/tick-min-condition-generation-review-20260613/configs/tick_late_train.json `
  --run-id tick_late_0920_0925_train_20260613 `
  --manifest-out .omo/evidence/tmap-walkforward/tick_late_0920_0925_train_20260613/manifest.json
```

## Corrected Future Min Command

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
python -m ai_strategy_loop.scripts.tmap_sweep `
  --template min_session_0900_1500_rotation `
  --config-json .omo/evidence/tick-min-condition-generation-review-20260613/configs/min_full_train.json `
  --run-id min_0900_1500_train_20260613 `
  --manifest-out .omo/evidence/tmap-walkforward/min_0900_1500_train_20260613/manifest.json
```

## Config Location Recommendation

For future implementation, generate config JSON into `.omo/evidence/.../configs/` during review/smoke work, not `ai_strategy_loop/state`, until the user explicitly approves runtime-state writes. Promotion-grade runs can later use the established `ai_strategy_loop/state/run_*config.json` pattern after the command contract is corrected.

## Scope

No roadmap document was edited in this phase. This file is the correction note for the next development pass.

